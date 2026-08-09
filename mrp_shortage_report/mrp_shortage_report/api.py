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
    project = doc.get("project")
    if not project and doc.get("items"):
        for item in doc.get("items"):
            if item.project:
                project = item.project
                break
                
    val = 0.0
    if project:
        budget = frappe.db.sql("""
            SELECT sum(IFNULL(base_net_amount, amount))
            FROM `tabPurchase Order Item`
            WHERE project = %s 
            AND parenttype = 'Purchase Order'
            AND parent IN (SELECT name FROM `tabPurchase Order` WHERE docstatus = 1)
        """, project)
        val = budget[0][0] if budget and budget[0][0] else 0.0
        
    if doc.meta.has_field("custom_project_budget_used"):
        doc.set("custom_project_budget_used", val)
    elif doc.meta.has_field("project_budget_used"):
        doc.set("project_budget_used", val)
