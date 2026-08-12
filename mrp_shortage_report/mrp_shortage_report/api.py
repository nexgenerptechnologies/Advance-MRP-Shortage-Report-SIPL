import frappe

@frappe.whitelist()
def get_project_budget_used(project):
    if not project:
        return 0.0
        
    try:
        # Smartly resolve project name if a custom field value (like project_code) was passed
        if not frappe.db.exists("Project", project):
            found = frappe.db.get_value("Project", {"project_name": project}, "name")
            if found:
                project = found
            else:
                # Use robust SQL LIKE search to overcome dash/slash mismatches
                search_term = project.replace("-", "%").replace("/", "%")
                sql_result = frappe.db.sql("SELECT name FROM `tabProject` WHERE name LIKE %s", (f"%{search_term}%",))
                if sql_result:
                    project = sql_result[0][0]
        
        from mrp_shortage_report.mrp_shortage_report.report.project_document_summary.project_document_summary import (
            get_purchase_invoices, get_journal_entries, get_purchase_orders
        )
        
        actual_expenditures = 0.0
        for row in get_purchase_invoices(project):
            actual_expenditures += row.get("basic_value", 0.0)
            
        for row in get_journal_entries(project):
            actual_expenditures += row.get("basic_value", 0.0)
            
        pending_po_value = 0.0
        for row in get_purchase_orders(project, only_pending=True):
            pending_po_value += row.get("basic_value", 0.0)
            
        return actual_expenditures + pending_po_value
    except Exception as e:
        frappe.log_error(f"Error calculating project budget: {e}", "MRP Shortage Report")
        return 0.0

def set_budget_on_load(doc, method):
    # Dynamically find the exact fieldname based on label
    fieldname = None
    for df in doc.meta.fields:
        label = (df.label or "").lower()
        if "budget" in label and "used" in label:
            fieldname = df.fieldname
            break
            
    if not fieldname:
        # Fallbacks just in case
        if doc.meta.has_field("custom_project_budget_used"):
            fieldname = "custom_project_budget_used"
        elif doc.meta.has_field("project_budget_used"):
            fieldname = "project_budget_used"
            
    if not fieldname:
        return
        
    project = None
    if doc.get("items"):
        for item in doc.get("items"):
            if item.project:
                project = item.project
                break
                
    if not project:
        project = doc.get("project")
                
    val = 0.0
    if project:
        try:
            from mrp_shortage_report.mrp_shortage_report.report.project_document_summary.project_document_summary import (
                get_purchase_invoices, get_journal_entries, get_purchase_orders
            )
            
            actual_expenditures = 0.0
            for row in get_purchase_invoices(project):
                actual_expenditures += row.get("basic_value", 0.0)
                
            for row in get_journal_entries(project):
                actual_expenditures += row.get("basic_value", 0.0)
                
            pending_po_value = 0.0
            for row in get_purchase_orders(project, only_pending=True):
                pending_po_value += row.get("basic_value", 0.0)
                
            val = actual_expenditures + pending_po_value
        except Exception as e:
            frappe.log_error(f"Error calculating project budget on load: {e}", "MRP Shortage Report")
        
    # 1. Update the document object in memory
    doc.set(fieldname, val)

@frappe.whitelist()
def debug_budget(po_name):
    # Debug tool to figure out what's wrong
    doc = frappe.get_doc("Purchase Order", po_name)
    
    fields = []
    for f in frappe.get_meta("Purchase Order").fields:
        if "budget" in (f.label or "").lower():
            fields.append({"fieldname": f.fieldname, "label": f.label})
            
    custom_fields = frappe.db.sql("SELECT fieldname, label FROM `tabCustom Field` WHERE dt='Purchase Order' AND label LIKE '%budget%'", as_dict=1)
    
    project = None
    if doc.get("items"):
        for item in doc.get("items"):
            if item.project:
                project = item.project
                break
                
    if not project:
        project = doc.get("project")
                
    budget_val = 0.0
    if project:
        budget = frappe.db.sql("""
            SELECT sum(IFNULL(base_net_amount, amount))
            FROM `tabPurchase Order Item`
            WHERE project = %s 
            AND parenttype = 'Purchase Order'
            AND parent IN (SELECT name FROM `tabPurchase Order` WHERE docstatus = 1)
        """, project)
        budget_val = budget[0][0] if budget and budget[0][0] else 0.0
        
    return {
        "po_name": po_name,
        "found_project": project,
        "calculated_budget": budget_val,
        "meta_fields": fields,
        "db_custom_fields": custom_fields
    }
