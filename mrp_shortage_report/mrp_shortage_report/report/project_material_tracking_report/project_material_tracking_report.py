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
        {"fieldname": "item_code", "label": _("Item Code"), "fieldtype": "Link", "options": "Item", "width": 150},
        {"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 200},
        {"fieldname": "brand", "label": _("Brand"), "fieldtype": "Link", "options": "Brand", "width": 120},
        {"fieldname": "item_group", "label": _("Item Group"), "fieldtype": "Link", "options": "Item Group", "width": 120},
        {"fieldname": "is_fg_sfg", "label": _("Is FG/SFG"), "fieldtype": "Data", "width": 100},
        {"fieldname": "project", "label": _("Project"), "fieldtype": "Link", "options": "Project", "width": 150},
        {"fieldname": "allocated_name", "label": _("Allocated Name"), "fieldtype": "Data", "width": 200},
        {"fieldname": "bom_no", "label": _("BOM"), "fieldtype": "Link", "options": "BOM", "width": 150},
        {"fieldname": "required_qty", "label": _("Required Qty"), "fieldtype": "Float", "width": 120},
        {"fieldname": "ordered_qty", "label": _("Ordered Qty"), "fieldtype": "Float", "width": 120},
        {"fieldname": "received_qty", "label": _("Received Qty"), "fieldtype": "Float", "width": 120},
        {"fieldname": "purchase_order", "label": _("Purchase Order"), "fieldtype": "Link", "options": "Purchase Order", "width": 150},
        {"fieldname": "supplier", "label": _("Supplier"), "fieldtype": "Link", "options": "Supplier", "width": 150},
        {"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 130}
    ]

def get_data(filters):
    data = []
    
    # Track unique rows to avoid duplicates
    processed_keys = set()
    
    # 1. Fetch from Purchase Orders
    po_conditions = "po.docstatus = 1"
    po_values = {}
    
    if filters.get("project"):
        po_conditions += " AND poi.project = %(project)s"
        po_values["project"] = filters.get("project")
    if filters.get("item_code"):
        po_conditions += " AND poi.item_code = %(item_code)s"
        po_values["item_code"] = filters.get("item_code")
    if filters.get("brand"):
        po_conditions += " AND poi.brand = %(brand)s"
        po_values["brand"] = filters.get("brand")
    if filters.get("item_group"):
        po_conditions += " AND poi.item_group = %(item_group)s"
        po_values["item_group"] = filters.get("item_group")
    if filters.get("supplier"):
        po_conditions += " AND po.supplier = %(supplier)s"
        po_values["supplier"] = filters.get("supplier")
    if filters.get("purchase_order"):
        po_conditions += " AND po.name = %(purchase_order)s"
        po_values["purchase_order"] = filters.get("purchase_order")
        
    po_query = f"""
        SELECT 
            poi.item_code, poi.item_name, poi.brand, poi.item_group,
            poi.project, po.name as purchase_order, po.supplier,
            poi.qty as ordered_qty, poi.received_qty, poi.bom as bom_no
        FROM `tabPurchase Order Item` poi
        JOIN `tabPurchase Order` po ON poi.parent = po.name
        WHERE {po_conditions}
    """
    po_items = frappe.db.sql(po_query, po_values, as_dict=True)
    
    for row in po_items:
        # Determine Status
        status = ""
        if row.received_qty >= row.ordered_qty and row.ordered_qty > 0:
            status = "Fully Received"
        elif row.received_qty > 0 and row.received_qty < row.ordered_qty:
            status = "Partially Received"
        elif row.received_qty == 0 and row.ordered_qty > 0:
            status = "PO Raised"
            
        # Check Work Orders for In Production / Completed status
        wo = frappe.db.get_value("Work Order", {"production_item": row.item_code, "project": row.project, "docstatus": 1}, ["status"], as_dict=True)
        if wo:
            if wo.status == "In Process":
                status = "In Production"
            elif wo.status == "Completed":
                status = "Completed"
                
        # FG / SFG Check
        has_bom = frappe.db.exists("BOM", {"item": row.item_code, "is_active": 1})
        is_fg_sfg = "Yes" if has_bom else "No"
        
        # Allocated Name
        allocated_name = f"{row.project} - {row.ordered_qty}" if row.project else ""
        
        row_dict = {
            "item_code": row.item_code,
            "item_name": row.item_name,
            "brand": row.brand,
            "item_group": row.item_group,
            "is_fg_sfg": is_fg_sfg,
            "project": row.project,
            "allocated_name": allocated_name,
            "bom_no": row.bom_no,
            "required_qty": row.ordered_qty, # Fallback
            "ordered_qty": row.ordered_qty,
            "received_qty": row.received_qty,
            "purchase_order": row.purchase_order,
            "supplier": row.supplier,
            "status": status
        }
        
        if filters.get("bom") and filters.get("bom") != row.bom_no:
            continue
            
        if filters.get("status") and filters.get("status") != status:
            continue
            
        key = (row.item_code, row.project, row.purchase_order)
        processed_keys.add(key)
        data.append(row_dict)
        
    # 2. Fetch from Material Requests for Pending POs
    mr_conditions = "mr.docstatus = 1 AND mr.material_request_type = 'Purchase' AND mri.ordered_qty < mri.qty"
    mr_values = {}
    
    if filters.get("project"):
        mr_conditions += " AND mri.project = %(project)s"
        mr_values["project"] = filters.get("project")
    if filters.get("item_code"):
        mr_conditions += " AND mri.item_code = %(item_code)s"
        mr_values["item_code"] = filters.get("item_code")
    if filters.get("brand"):
        mr_conditions += " AND mri.brand = %(brand)s"
        mr_values["brand"] = filters.get("brand")
    if filters.get("item_group"):
        mr_conditions += " AND mri.item_group = %(item_group)s"
        mr_values["item_group"] = filters.get("item_group")
        
    # If a specific PO or Supplier is filtered, Pending POs won't match, so skip
    if not filters.get("purchase_order") and not filters.get("supplier"):
        mr_query = f"""
            SELECT 
                mri.item_code, mri.item_name, mri.brand, mri.item_group,
                mri.project, (mri.qty - mri.ordered_qty) as pending_qty, mri.qty as required_qty
            FROM `tabMaterial Request Item` mri
            JOIN `tabMaterial Request` mr ON mri.parent = mr.name
            WHERE {mr_conditions}
        """
        mr_items = frappe.db.sql(mr_query, mr_values, as_dict=True)
        
        for row in mr_items:
            status = "Pending PO"
            
            # FG / SFG Check
            has_bom = frappe.db.exists("BOM", {"item": row.item_code, "is_active": 1})
            is_fg_sfg = "Yes" if has_bom else "No"
            
            allocated_name = f"{row.project} - {row.pending_qty}" if row.project else ""
            
            row_dict = {
                "item_code": row.item_code,
                "item_name": row.item_name,
                "brand": row.brand,
                "item_group": row.item_group,
                "is_fg_sfg": is_fg_sfg,
                "project": row.project,
                "allocated_name": allocated_name,
                "bom_no": "",
                "required_qty": row.required_qty,
                "ordered_qty": 0,
                "received_qty": 0,
                "purchase_order": "",
                "supplier": "",
                "status": status
            }
            
            if filters.get("status") and filters.get("status") != status:
                continue
                
            key = (row.item_code, row.project, "Pending")
            if key not in processed_keys:
                processed_keys.add(key)
                data.append(row_dict)
                
    return data
