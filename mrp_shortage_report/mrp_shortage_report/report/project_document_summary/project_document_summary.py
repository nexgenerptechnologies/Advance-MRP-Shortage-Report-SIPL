import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}
        
    project = filters.get("project")
    if not project:
        return [], []
        
    doc_type_filter = filters.get("document_type", "Purchase Invoice + JEs + Pending POs")
    
    columns = get_columns()
    data = []
    
    # Track KPIs
    actual_expenditures = 0.0
    pending_po_value = 0.0
    
    # 1. Fetch Budget
    estimated_cost = frappe.db.get_value("Project", project, "estimated_cost") or 0.0
    
    # Determine what to fetch based on filter
    fetch_pi = doc_type_filter in ["Purchase Invoice + Journal Entries", "Purchase Invoice + JEs + Pending POs"]
    fetch_je = doc_type_filter in ["Purchase Invoice + Journal Entries", "Purchase Invoice + JEs + Pending POs"]
    fetch_pending_po = doc_type_filter == "Purchase Invoice + JEs + Pending POs"
    fetch_all_po = doc_type_filter == "Purchase Order Only"
    
    # 2. Fetch Purchase Invoices
    if fetch_pi:
        pi_data = get_purchase_invoices(project)
        for row in pi_data:
            actual_expenditures += row.get("basic_value", 0.0)
            data.append(row)
            
    # 3. Fetch Journal Entries
    if fetch_je:
        je_data = get_journal_entries(project)
        for row in je_data:
            actual_expenditures += row.get("basic_value", 0.0)
            data.append(row)
            
    # 4. Fetch Purchase Orders (Pending or All)
    if fetch_pending_po or fetch_all_po:
        only_pending = not fetch_all_po
        po_data = get_purchase_orders(project, only_pending)
        for row in po_data:
            if fetch_pending_po:
                pending_po_value += row.get("basic_value", 0.0)
            data.append(row)
            
    # Sort data by Date descending
    data = sorted(data, key=lambda x: x.get("date") or "", reverse=True)
    
    # Prepare Summary
    total_committed = actual_expenditures + pending_po_value
    balance = estimated_cost - total_committed
    percent_used = (total_committed / estimated_cost * 100) if estimated_cost > 0 else 0.0
    
    currency = frappe.defaults.get_global_default("default_currency") or "INR"
    
    report_summary = [
        {"value": estimated_cost, "indicator": "Blue", "label": _("Total Budget"), "datatype": "Currency", "currency": currency},
        {"value": actual_expenditures, "indicator": "Orange", "label": _("Actual Expenditures"), "datatype": "Currency", "currency": currency},
        {"value": pending_po_value, "indicator": "Red", "label": _("Pending PO Value"), "datatype": "Currency", "currency": currency},
        {"value": total_committed, "indicator": "Purple", "label": _("Total Committed"), "datatype": "Currency", "currency": currency},
        {"value": balance, "indicator": "Green" if balance >= 0 else "Red", "label": _("Balance"), "datatype": "Currency", "currency": currency},
        {"value": f"{percent_used:.2f}%", "indicator": "Red" if percent_used > 100 else "Green", "label": _("% Budget Used")}
    ]
    
    return columns, data, None, None, None, report_summary

def get_columns():
    return [
        {"fieldname": "type", "label": _("Type"), "fieldtype": "Data", "width": 140},
        {"fieldname": "document_no", "label": _("Document No."), "fieldtype": "Dynamic Link", "options": "type", "width": 200},
        {"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 110},
        {"fieldname": "party_name", "label": _("Party Name"), "fieldtype": "Data", "width": 200},
        {"fieldname": "basic_value", "label": _("Basic Value"), "fieldtype": "Currency", "width": 140},
        {"fieldname": "gst", "label": _("GST"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "total", "label": _("Total"), "fieldtype": "Currency", "width": 140}
    ]

def get_purchase_invoices(project):
    query = """
        SELECT
            'Purchase Invoice' as type,
            pi.name as document_no,
            pi.posting_date as date,
            pi.supplier_name as party_name,
            SUM(pii.base_net_amount) as basic_value
        FROM `tabPurchase Invoice Item` pii
        INNER JOIN `tabPurchase Invoice` pi ON pii.parent = pi.name
        WHERE pii.project = %(project)s
        AND pi.docstatus = 1
        GROUP BY pi.name
    """
    res = frappe.db.sql(query, {"project": project}, as_dict=1)
    
    for r in res:
        doc = frappe.db.get_value("Purchase Invoice", r.document_no, ["base_net_total", "base_taxes_and_charges_added"], as_dict=1)
        if doc and doc.base_net_total:
            ratio = r.basic_value / doc.base_net_total if doc.base_net_total > 0 else 0
            r.gst = (doc.base_taxes_and_charges_added or 0.0) * ratio
        else:
            r.gst = 0.0
        r.total = r.basic_value + r.gst
        
    return res

def get_journal_entries(project):
    query = """
        SELECT
            'Journal Entry' as type,
            je.name as document_no,
            je.posting_date as date,
            jea.account as party_name,
            SUM(jea.debit_in_account_currency) as basic_value,
            SUM(jea.credit_in_account_currency) as credit_val
        FROM `tabJournal Entry Account` jea
        INNER JOIN `tabJournal Entry` je ON jea.parent = je.name
        WHERE jea.project = %(project)s
        AND je.docstatus = 1
        GROUP BY je.name, jea.account
    """
    res = frappe.db.sql(query, {"project": project}, as_dict=1)
    
    final_res = []
    for r in res:
        # Net expense in this account for this JE
        val = (r.basic_value or 0.0) - (r.credit_val or 0.0)
        
        # We only want to show the net expense or income for the project from this JE account row.
        # Often JEs have multiple rows for the same project. Grouping by account helps.
        if val != 0:
            r.basic_value = val
            r.gst = 0.0
            r.total = val
            final_res.append(r)
            
    return final_res

def get_purchase_orders(project, only_pending):
    query = """
        SELECT
            'Purchase Order' as type,
            po.name as document_no,
            po.transaction_date as date,
            po.supplier_name as party_name,
            SUM(
                CASE WHEN %(only_pending)s = 1 THEN 
                    (CASE WHEN (poi.qty - poi.received_qty) > 0 THEN (poi.qty - poi.received_qty) * poi.base_rate ELSE 0 END)
                ELSE 
                    poi.base_net_amount 
                END
            ) as basic_value
        FROM `tabPurchase Order Item` poi
        INNER JOIN `tabPurchase Order` po ON poi.parent = po.name
        WHERE poi.project = %(project)s
        AND po.docstatus = 1
        AND po.status NOT IN ('Closed', 'Completed')
    """
    
    if only_pending:
        query += " AND poi.qty > poi.received_qty"
        
    query += " GROUP BY po.name"
    
    res = frappe.db.sql(query, {"project": project, "only_pending": 1 if only_pending else 0}, as_dict=1)
    
    for r in res:
        doc = frappe.db.get_value("Purchase Order", r.document_no, ["base_net_total", "base_taxes_and_charges_added"], as_dict=1)
        if doc and doc.base_net_total:
            ratio = r.basic_value / doc.base_net_total if doc.base_net_total > 0 else 0
            r.gst = (doc.base_taxes_and_charges_added or 0.0) * ratio
        else:
            r.gst = 0.0
        r.total = r.basic_value + r.gst
        
    return res
