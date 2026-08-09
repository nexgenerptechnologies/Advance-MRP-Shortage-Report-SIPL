import frappe

@frappe.whitelist()
def get_project_budget_used(project):
    if not project:
        return 0.0
        
    budget = frappe.db.sql("""
        SELECT sum(IFNULL(base_net_amount, amount))
        FROM `tabPurchase Order Item`
        WHERE project = %s 
        AND parenttype = 'Purchase Order'
        AND parent IN (SELECT name FROM `tabPurchase Order` WHERE docstatus = 1)
    """, project)
    
    return budget[0][0] if budget and budget[0][0] else 0.0

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
        
    project = doc.get("project")
    if not project and doc.get("items"):
        for item in doc.get("items"):
            if item.project:
                project = item.project
                break
                
    val = 0.0
    if project:
        # Query total budget used by this project across all submitted POs
        budget = frappe.db.sql("""
            SELECT sum(IFNULL(base_net_amount, amount))
            FROM `tabPurchase Order Item`
            WHERE project = %s 
            AND parenttype = 'Purchase Order'
            AND parent IN (SELECT name FROM `tabPurchase Order` WHERE docstatus = 1)
        """, project)
        val = budget[0][0] if budget and budget[0][0] else 0.0
        
    # 1. Update the document object in memory
    doc.set(fieldname, val)
    
    # 2. Directly update the database to ensure it persists and appears immediately on refresh
    if not doc.is_new():
        frappe.db.set_value(doc.doctype, doc.name, fieldname, val, update_modified=False)
