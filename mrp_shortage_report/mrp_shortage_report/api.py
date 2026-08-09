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
