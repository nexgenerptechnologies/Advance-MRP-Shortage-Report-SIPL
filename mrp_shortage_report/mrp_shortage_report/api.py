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
