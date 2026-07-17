import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}
        
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data

def get_columns():
    return [
        {"fieldname": "project", "label": _("Project"), "fieldtype": "Link", "options": "Project", "width": 150},
        {"fieldname": "item_code", "label": _("Subassembly Item Code"), "fieldtype": "Link", "options": "Item", "width": 180},
        {"fieldname": "item_name", "label": _("Subassembly Item Name"), "fieldtype": "Data", "width": 200},
        {"fieldname": "bom", "label": _("BOM"), "fieldtype": "Link", "options": "BOM", "width": 150},
        {"fieldname": "bom_upload_date", "label": _("BOM Upload Date"), "fieldtype": "Date", "width": 120},
        {"fieldname": "bom_last_modified_date", "label": _("BOM Last Modified Date"), "fieldtype": "Date", "width": 160},
        {"fieldname": "required_qty", "label": _("Required Qty"), "fieldtype": "Float", "width": 120},
        {"fieldname": "shortage", "label": _("Shortage"), "fieldtype": "Float", "width": 120},
        {"fieldname": "missing_components", "label": _("Missing Components"), "fieldtype": "Data", "width": 150},
        {"fieldname": "missing_items_json", "label": _("Missing Items JSON"), "fieldtype": "Data", "hidden": 1},
        {"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 150}
    ]

def get_data(filters):
    bom_project_field = "project" if frappe.db.has_column("BOM", "project") else None
    
    conditions = ["b.docstatus = 1", "b.is_active = 1"]
    values = {}
    
    if filters.get("project"):
        if bom_project_field:
            conditions.append(f"b.{bom_project_field} = %(project)s")
        else:
            conditions.append("EXISTS (SELECT 1 FROM `tabWork Order` wo WHERE wo.bom_no = b.name AND wo.project = %(project)s)")
        values["project"] = filters.get("project")
        
    if filters.get("item_code"):
        conditions.append("b.item = %(item_code)s")
        values["item_code"] = filters.get("item_code")
        
    if filters.get("bom"):
        boms = filters.get("bom")
        if isinstance(boms, list):
            conditions.append("b.name IN %(bom)s")
            values["bom"] = tuple(boms)
        else:
            conditions.append("b.name = %(bom)s")
            values["bom"] = boms
            
    query = f"""
        SELECT 
            b.name as bom, 
            b.item as item_code, 
            b.creation as bom_upload_date, 
            b.modified as bom_last_modified_date, 
            b.quantity,
            {f"b.{bom_project_field}" if bom_project_field else "NULL"} as project_from_bom
        FROM `tabBOM` b
        WHERE {" AND ".join(conditions)}
        ORDER BY b.creation DESC
    """
    
    boms = frappe.db.sql(query, values, as_dict=1)
    
    data = []
    for b in boms:
        project = b.project_from_bom or filters.get("project") or ""
        item_name = frappe.db.get_value("Item", b.item_code, "item_name")
        
        required_qty = b.quantity
        if project:
            parent_bom = frappe.db.get_value("BOM", {bom_project_field: project}, "name") if bom_project_field else None
            if parent_bom:
                req_qty_in_project = frappe.db.sql("SELECT sum(qty) FROM `tabBOM Item` WHERE parent=%s AND item_code=%s", (parent_bom, b.item_code))
                if req_qty_in_project and req_qty_in_project[0][0]:
                    required_qty = req_qty_in_project[0][0]
                    
        stock_qty = get_stock_qty(b.item_code)
        shortage = max(0, required_qty - stock_qty)
        
        import json
        missing_count = 0
        missing_items = []
        
        bom_items = frappe.db.sql("SELECT item_code, item_name, qty FROM `tabBOM Item` WHERE parent=%s", (b.bom,), as_dict=1)
        for child in bom_items:
            child_stock = get_stock_qty(child.item_code)
            child_req = (child.qty / b.quantity) * required_qty
            if child_stock < child_req:
                missing_count += 1
                missing_items.append({
                    "item_code": child.item_code,
                    "item_name": child.item_name,
                    "shortage": child_req - child_stock
                })
                
        missing_items_json = json.dumps(missing_items) if missing_items else ""
                
        status = "Completed"
        if project:
            is_project_completed = frappe.db.get_value("Project", project, "status") == "Completed"
            if is_project_completed:
                status = "Completed"
            else:
                status = calculate_status(shortage, missing_count, b.bom, project)
        else:
            status = calculate_status(shortage, missing_count, b.bom, project)
            
        if filters.get("status") and status != filters.get("status"):
            continue
            
        data.append({
            "project": project,
            "item_code": b.item_code,
            "item_name": item_name,
            "bom": b.bom,
            "bom_upload_date": b.bom_upload_date.date() if b.bom_upload_date else None,
            "bom_last_modified_date": b.bom_last_modified_date.date() if b.bom_last_modified_date else None,
            "required_qty": required_qty,
            "shortage": shortage,
            "missing_components": missing_count,
            "missing_items_json": missing_items_json,
            "status": status
        })
        
    return data

def calculate_status(shortage, missing_count, bom_no, project):
    if shortage <= 0:
        return "Completed"
    
    if missing_count == 0:
        return "Ready for Production"
        
    return "Material Shortage"

def get_stock_qty(item_code):
    bins = frappe.db.get_all("Bin", filters={"item_code": item_code}, fields=["actual_qty"])
    return sum([b.actual_qty for b in bins])
