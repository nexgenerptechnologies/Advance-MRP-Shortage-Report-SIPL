import frappe
from frappe import _
from mrp_shortage_report.mrp_shortage_report.report.project_document_summary.project_document_summary import (
    get_purchase_invoices, get_journal_entries, get_purchase_orders, get_payment_entries
)
from frappe.utils import getdate, nowdate, date_diff

def execute(filters=None):
    if not filters:
        filters = {}
        
    columns = get_columns()
    data = []
    
    # Pre-fetch Sales Orders
    so_data = frappe.db.sql("""
        SELECT project, GROUP_CONCAT(name SEPARATOR ', ') as so_no, SUM(base_net_total) as so_value
        FROM `tabSales Order`
        WHERE docstatus = 1 AND project IS NOT NULL AND project != ''
        GROUP BY project
    """, as_dict=1)
    so_map = {row.project: row for row in so_data}
    
    # Pre-fetch Sales Invoices
    si_data = frappe.db.sql("""
        SELECT project, GROUP_CONCAT(name SEPARATOR ', ') as si_no, GROUP_CONCAT(posting_date SEPARATOR ', ') as si_date
        FROM `tabSales Invoice`
        WHERE docstatus = 1 AND project IS NOT NULL AND project != ''
        GROUP BY project
    """, as_dict=1)
    si_map = {row.project: row for row in si_data}
    
    projects = frappe.get_all("Project", fields=["name", "project_name"])
    
    for proj in projects:
        project = proj.name
        
        # 1. Fetch Budget Gracefully
        proj_doc = frappe.get_cached_doc("Project", project)
        estimated_cost = (
            proj_doc.get("estimated_costing") or 
            proj_doc.get("estimated_cost") or 
            proj_doc.get("project_value") or 
            0.0
        )
        project_days = 0
        if proj_doc.creation:
            project_days = date_diff(nowdate(), getdate(proj_doc.creation))
        
        # 2. Calculate Actual Expenditures (Invoices & JEs)
        actual_expenditures = 0.0
        
        pi_summary = get_purchase_invoices(project)
        for row in pi_summary:
            actual_expenditures += row.get("basic_value", 0.0)
            
        je_summary = get_journal_entries(project)
        for row in je_summary:
            actual_expenditures += row.get("basic_value", 0.0)
            
        # 3. Calculate Pending PO Value (pure item-level logic)
        pending_po_value = 0.0
        pending_po_summary = get_purchase_orders(project, only_pending=True)
        for row in pending_po_summary:
            pending_po_value += row.get("basic_value", 0.0)
            
        # 4. Calculate Payment Received
        payment_received = 0.0
        payment_entries = get_payment_entries(project)
        for row in payment_entries:
            payment_received += row.get("basic_value", 0.0)
            
        total_committed = actual_expenditures + pending_po_value
            
        percent_expended = (actual_expenditures / estimated_cost * 100) if estimated_cost > 0 else 0.0
        percent_committed = (total_committed / estimated_cost * 100) if estimated_cost > 0 else 0.0
        percent_payment_received = (payment_received / estimated_cost * 100) if estimated_cost > 0 else 0.0

        so_info = so_map.get(project, {})
        si_info = si_map.get(project, {})
        
        data.append({
            "project": project,
            "project_name": proj.project_name,
            "sales_order_no": so_info.get("so_no"),
            "sales_order_value": so_info.get("so_value", 0.0),
            "sales_invoice_no": si_info.get("si_no"),
            "sales_invoice_date": si_info.get("si_date"),
            "project_budget": estimated_cost,
            "payment_received": payment_received,
            "actual_expenditures": actual_expenditures,
            "pending_po_value": pending_po_value,
            "total_committed": total_committed,
            "percent_payment_received": percent_payment_received,
            "percent_expended": percent_expended,
            "percent_committed": percent_committed,
            "project_days": project_days
        })
        
    # Sort data by project ID to match the exact order of the old report
    data = sorted(data, key=lambda x: x.get("project") or "")
    
    # User requested NO graphics and NO KPI blocks
    chart = None
    report_summary = None
    
    return columns, data, None, chart, report_summary

def get_columns():
    return [
        {"fieldname": "project", "label": _("Project"), "fieldtype": "Link", "options": "Project", "width": 200},
        {"fieldname": "project_name", "label": _("Project Name"), "fieldtype": "Data", "width": 250},
        {"fieldname": "sales_order_no", "label": _("Sales Order No"), "fieldtype": "Data", "width": 150},
        {"fieldname": "sales_order_value", "label": _("Sales Order Value"), "fieldtype": "Currency", "width": 140},
        {"fieldname": "sales_invoice_no", "label": _("Sales Invoice No"), "fieldtype": "Data", "width": 150},
        {"fieldname": "sales_invoice_date", "label": _("Sales Invoice Date"), "fieldtype": "Data", "width": 150},
        {"fieldname": "project_days", "label": _("Project Days"), "fieldtype": "Int", "width": 110},
        {"fieldname": "project_budget", "label": _("Project Budget"), "fieldtype": "Currency", "width": 140},
        {"fieldname": "payment_received", "label": _("Payment Received"), "fieldtype": "Currency", "width": 140},
        {"fieldname": "percent_payment_received", "label": _("% Payment Received"), "fieldtype": "Percent", "width": 150},
        {"fieldname": "actual_expenditures", "label": _("Actual Exp. (Invoices)"), "fieldtype": "Currency", "width": 160},
        {"fieldname": "pending_po_value", "label": _("Pending PO Value"), "fieldtype": "Currency", "width": 140},
        {"fieldname": "total_committed", "label": _("Total Committed"), "fieldtype": "Currency", "width": 140},
        {"fieldname": "percent_expended", "label": _("% Budget Expended"), "fieldtype": "Percent", "width": 150},
        {"fieldname": "percent_committed", "label": _("% Budget Committed"), "fieldtype": "Percent", "width": 150}
    ]
