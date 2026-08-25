import frappe

@frappe.whitelist()
def get_project_budget_used(project):
    if not project:
        return 0.0
        
    try:
        project = str(project).strip()
        # Smartly resolve project name if a custom field value (like project_code) was passed
        if not frappe.db.exists("Project", project):
            found = frappe.db.get_value("Project", {"project_name": project}, "name")
            if found:
                project = found
            else:
                candidates = [
                    project.replace("-", "/", 1), # e.g. 26/27-SIPL-001
                    project.replace("-", "/")     # e.g. 26/27/SIPL/001
                ]
                parts = project.split("-", 2)
                if len(parts) >= 3:
                    candidates.append(f"{parts[0]}-{parts[1]}/{parts[2]}")
                    
                search_term = project.replace("-", "%").replace("/", "%")
                candidates.append(f"LIKE:%{search_term}%")
                    
                for alt_project in candidates:
                    if alt_project.startswith("LIKE:"):
                        res = frappe.db.sql("SELECT name FROM `tabProject` WHERE name LIKE %s LIMIT 1", (alt_project[5:],))
                        if res:
                            project = res[0][0]
                            break
                    else:
                        if frappe.db.exists("Project", alt_project):
                            project = alt_project
                            break
        
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
            
        total_val = actual_expenditures + pending_po_value
        
        if total_val == 0.0:
            # Fallback to total PO value if pending is exactly 0 (e.g. all billed but PI not linked)
            budget = frappe.db.sql("""
                SELECT sum(IFNULL(base_net_amount, amount))
                FROM `tabPurchase Order Item`
                WHERE project = %s 
                AND parenttype = 'Purchase Order'
                AND parent IN (SELECT name FROM `tabPurchase Order` WHERE docstatus = 1)
            """, project)
            if budget and budget[0][0]:
                total_val = budget[0][0]
                
        return total_val
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
    
    # 2. Forcefully bypass Frappe's allow_on_submit validation to write directly to DB
    # This guarantees the budget appears in the List View for submitted documents
    if not doc.is_new():
        frappe.db.set_value(doc.doctype, doc.name, fieldname, val, update_modified=False)
        frappe.db.commit()

@frappe.whitelist()
def debug_budget(po_name):
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
        "db_custom_fields": custom_fields
    }

@frappe.whitelist()
def get_po_shortage_data(project):
    """
    Server-side function to calculate TRUE shortage by analyzing global demand vs project demand.
    Returns the items that have a true global shortage for the given project.
    """
    from mrp_shortage_report.mrp_shortage_report.report.project_material_tracking_report.project_material_tracking_report import get_data
    import json
    
    # 1. Fetch demand specifically for THIS project
    project_data = get_data({"project": project, "group_by_item": 1})
    
    project_items = [d.get("item_code") for d in project_data if d.get("item_code")]
    if not project_items:
        return []
        
    # 2. Fetch GLOBAL demand across ALL projects, but only for the items this project needs
    global_data = get_data({"group_by_item": 1, "item_code": json.dumps(project_items)})
    
    global_map = {d.get("item_code"): d for d in global_data}
    
    result = []
    for d in project_data:
        item_code = d.get("item_code")
        g = global_map.get(item_code, {})
        
        project_qty = d.get("project_qty") or 0.0
        total_req_qty = g.get("project_qty") or project_qty
        stock_qty = g.get("stock_qty") or 0.0
        pending_po_qty = g.get("balance_qty") or 0.0 # balance_qty represents pending PO qty
        
        # Calculate Global Net Shortage
        global_net_shortage = max(0, total_req_qty - stock_qty - pending_po_qty)
        
        if global_net_shortage > 0 and project_qty > 0:
            # How much to order for THIS project?
            # It should not exceed what the project actually needs, and it shouldn't exceed the global shortage.
            net_shortage_for_project = min(project_qty, global_net_shortage)
            
            result.append({
                "item_code": item_code,
                "item_name": d.get("item_name"),
                "custom_make": d.get("brand"),
                "bom_no": d.get("bom"),
                "project_req_qty": project_qty,
                "total_req_qty": total_req_qty,
                "stock_qty": stock_qty,
                "pending_po_qty": pending_po_qty,
                "global_shortage": global_net_shortage,
                "net_shortage": net_shortage_for_project
            })
            
    return result
