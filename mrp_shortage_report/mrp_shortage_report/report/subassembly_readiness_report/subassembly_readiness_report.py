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
        {"fieldname": "bom", "label": _("BOM"), "fieldtype": "Link", "options": "BOM", "width": 180},
        {"fieldname": "item_code", "label": _("Subassembly Item Code"), "fieldtype": "Link", "options": "Item", "width": 180},
        {"fieldname": "item_name", "label": _("Subassembly Item Name"), "fieldtype": "Data", "width": 200},
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
    
    top_boms = []
    if filters.get("fg_bom"):
        top_boms = [filters.get("fg_bom")]
    elif filters.get("project"):
        conditions = ["docstatus = 1", "is_active = 1", "is_default = 1"]
        if bom_project_field:
            conditions.append(f"{bom_project_field} = %(project)s")
        else:
            conditions.append("EXISTS (SELECT 1 FROM `tabWork Order` wo WHERE wo.bom_no = name AND wo.project = %(project)s)")
        
        top_boms = frappe.db.sql_list(f"SELECT name FROM `tabBOM` WHERE {' AND '.join(conditions)}", {"project": filters.get("project")})
    elif filters.get("subassembly"):
        subs = filters.get("subassembly")
        if not isinstance(subs, list):
            subs = [subs]
        top_boms = subs
    else:
        conditions = ["docstatus = 1", "is_active = 1", "is_default = 1", "name NOT IN (SELECT bom_no FROM `tabBOM Item` WHERE bom_no IS NOT NULL)"]
        top_boms = frappe.db.sql_list(f"SELECT name FROM `tabBOM` WHERE {' AND '.join(conditions)} LIMIT 50")

    bom_list = []
    visited_boms = set()
    
    def explode_boms(bom_name, project_val, multiplier=1.0, is_top=True):
        if bom_name in visited_boms:
            return
        visited_boms.add(bom_name)
        
        bom_doc = frappe.db.get_value("BOM", bom_name, ["name", "item", "quantity", "creation", "modified"], as_dict=1)
        if not bom_doc:
            return
            
        bom_list.append({
            "bom": bom_doc.name,
            "item_code": bom_doc.item,
            "bom_upload_date": bom_doc.creation,
            "bom_last_modified_date": bom_doc.modified,
            "bom_quantity": float(bom_doc.quantity or 1.0),
            "project": project_val,
            "multiplier": multiplier,
            "is_top": is_top
        })
        
        # Child subassemblies
        child_items = frappe.db.sql("""
            SELECT item_code, qty, bom_no
            FROM `tabBOM Item`
            WHERE parent = %s
        """, (bom_name,), as_dict=1)
        
        for c in child_items:
            child_bom = c.bom_no
            if not child_bom:
                child_bom = frappe.db.get_value("BOM", {"item": c.item_code, "is_active": 1, "is_default": 1, "docstatus": 1})
            
            if child_bom:
                child_multiplier = multiplier * (float(c.qty) / float(bom_doc.quantity or 1.0))
                explode_boms(child_bom, project_val, multiplier=child_multiplier, is_top=False)

    for tb in top_boms:
        proj = filters.get("project") or (frappe.db.get_value("BOM", tb, bom_project_field) if bom_project_field else "")
        explode_boms(tb, proj, multiplier=1.0, is_top=True)
        
    data = []
    import json
    
    for b in bom_list:
        # Subassembly filter
        if filters.get("subassembly"):
            subs = filters.get("subassembly")
            if isinstance(subs, str):
                subs = [subs]
            if b["bom"] not in subs:
                continue
                
        project = b["project"] or filters.get("project") or ""
        item_name = frappe.db.get_value("Item", b["item_code"], "item_name") or b["item_code"]
        
        required_qty = b["multiplier"] * b["bom_quantity"]
        stock_qty = get_stock_qty(b["item_code"])
        shortage = max(0.0, required_qty - stock_qty)
        
        missing_count = 0
        missing_items = []
        
        bom_items = frappe.db.sql("""
            SELECT bi.item_code, bi.item_name, bi.qty, i.item_group 
            FROM `tabBOM Item` bi
            LEFT JOIN `tabItem` i ON bi.item_code = i.name
            WHERE bi.parent=%s
        """, (b["bom"],), as_dict=1)
        
        for child in bom_items:
            child_stock = get_stock_qty(child.item_code)
            child_req = (float(child.qty) / b["bom_quantity"]) * required_qty
            if child_stock < child_req:
                missing_count += 1
                missing_items.append({
                    "item_code": child.item_code,
                    "item_name": child.item_name,
                    "item_group": child.item_group,
                    "shortage": child_req - child_stock
                })
                
        missing_items_json = json.dumps(missing_items) if missing_items else ""
        
        status = calculate_status(shortage, missing_count, stock_qty, required_qty, project)
            
        if filters.get("status") and status != filters.get("status"):
            continue
            
        data.append({
            "project": project,
            "bom": b["bom"],
            "item_code": b["item_code"],
            "item_name": item_name,
            "bom_upload_date": b["bom_upload_date"].date() if b["bom_upload_date"] else None,
            "bom_last_modified_date": b["bom_last_modified_date"].date() if b["bom_last_modified_date"] else None,
            "required_qty": required_qty,
            "shortage": shortage,
            "missing_components": missing_count,
            "missing_items_json": missing_items_json,
            "status": status
        })
        
    return data

def calculate_status(shortage, missing_count, stock_qty, required_qty, project=None):
    if project:
        is_project_completed = frappe.db.get_value("Project", project, "status") == "Completed"
        if is_project_completed:
            return "Completed"
            
    if missing_count > 0:
        return "Material Shortage"
    
    if shortage > 0 or stock_qty < required_qty:
        return "Ready for Production"
        
    return "Completed"

def get_stock_qty(item_code):
    bins = frappe.db.get_all("Bin", filters={"item_code": item_code}, fields=["actual_qty"])
    return sum([b.actual_qty for b in bins])

@frappe.whitelist()
def get_fg_boms(doctype, txt, searchfield, start, page_len, filters):
    if isinstance(filters, str):
        import json
        filters = json.loads(filters)
        
    project = filters.get("project") if filters else None
    conditions = ["docstatus = 1", "is_active = 1", "is_default = 1", "name NOT IN (SELECT bom_no FROM `tabBOM Item` WHERE bom_no IS NOT NULL)"]
    if project:
        if frappe.db.has_column("BOM", "project"):
            conditions.append(f"project = '{project}'")
    query = f"SELECT name, item FROM `tabBOM` WHERE {' AND '.join(conditions)} AND name LIKE %s LIMIT {start}, {page_len}"
    return frappe.db.sql(query, (f"%{txt}%",))

@frappe.whitelist()
def get_subassembly_boms(doctype, txt, searchfield, start, page_len, filters):
    if isinstance(filters, str):
        import json
        filters = json.loads(filters)
        
    project = filters.get("project") if filters else None
    fg_bom = filters.get("fg_bom") if filters else None
    conditions = ["docstatus = 1", "is_active = 1", "name IN (SELECT bom_no FROM `tabBOM Item` WHERE bom_no IS NOT NULL)"]
    if fg_bom:
        conditions.append(f"name IN (SELECT bom_no FROM `tabBOM Item` WHERE parent = '{fg_bom}' AND bom_no IS NOT NULL)")
    elif project:
        if frappe.db.has_column("BOM", "project"):
            conditions.append(f"project = '{project}'")
    query = f"SELECT name as value, item as description FROM `tabBOM` WHERE {' AND '.join(conditions)} AND name LIKE %s LIMIT {start}, {page_len}"
    return frappe.db.sql(query, (f"%{txt}%",), as_dict=1)
