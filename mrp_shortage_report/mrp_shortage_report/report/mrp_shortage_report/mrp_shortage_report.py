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
        {"fieldname": "name", "label": _("ID"), "fieldtype": "Data", "hidden": 1},
        {"fieldname": "parent", "label": _("Parent"), "fieldtype": "Data", "hidden": 1},
        {"fieldname": "sales_order", "label": _("Sales Order"), "fieldtype": "Link", "options": "Sales Order", "width": 140},
        {"fieldname": "customer", "label": _("Customer"), "fieldtype": "Data", "width": 140},
        {"fieldname": "delivery_date", "label": _("Delivery Date"), "fieldtype": "Date", "width": 110},
        {"fieldname": "item_code", "label": _("Item Code"), "fieldtype": "Link", "options": "Item", "width": 160},
        {"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 180},
        {"fieldname": "pending_qty", "label": _("Required Qty"), "fieldtype": "Float", "width": 110},
        {"fieldname": "stock_qty", "label": _("Available Stock (Global)"), "fieldtype": "Float", "width": 170},
        {"fieldname": "po_qty", "label": _("Pending PO Qty"), "fieldtype": "Float", "width": 130},
        {"fieldname": "net_qty", "label": _("Net Shortage"), "fieldtype": "Float", "width": 110}
    ]

def get_data(filters):
    data = []
    
    query = """
        SELECT
            soi.name, soi.parent as sales_order, so.customer, so.delivery_date,
            soi.item_code, soi.item_name, soi.qty, soi.delivered_qty
        FROM
            `tabSales Order Item` soi
        INNER JOIN
            `tabSales Order` so ON soi.parent = so.name
        WHERE
            so.docstatus = 1
            AND so.status NOT IN ('Closed', 'Completed')
            AND soi.qty > soi.delivered_qty
    """
    
    conditions = []
    values = {}
    
    if filters.get("company"):
        conditions.append("so.company = %(company)s")
        values["company"] = filters.get("company")
        
    if filters.get("project"):
        conditions.append("so.project = %(project)s")
        values["project"] = filters.get("project")
        
    if conditions:
        query += " AND " + " AND ".join(conditions)
        
    query += " ORDER BY so.delivery_date ASC, soi.parent ASC"
    
    so_items = frappe.db.sql(query, values, as_dict=1)
    
    for row in so_items:
        pending_qty = row.qty - row.delivered_qty
        stock_qty = get_actual_qty(row.item_code)
        po_qty = get_pending_po_qty(row.item_code, filters)
        net_qty = pending_qty - stock_qty - po_qty
        
        # Append FG Row (Level 0)
        data.append({
            "name": row.name,
            "parent": "",
            "sales_order": row.sales_order,
            "customer": row.customer,
            "delivery_date": row.delivery_date,
            "item_code": row.item_code,
            "item_name": row.item_name,
            "pending_qty": pending_qty,
            "stock_qty": stock_qty,
            "po_qty": po_qty,
            "net_qty": net_qty
        })
        
        # If there is a net shortage, check for BOM and explode components
        if net_qty > 0:
            default_bom = frappe.db.get_value("Item", row.item_code, "default_bom")
            if default_bom:
                components = frappe.db.get_all(
                    "BOM Item", 
                    filters={"parent": default_bom},
                    fields=["item_code", "item_name", "qty", "stock_qty as bom_stock_qty"],
                    order_by="idx asc"
                )
                
                # Fetch BOM base qty
                bom_qty = frappe.db.get_value("BOM", default_bom, "quantity") or 1.0
                
                for comp in components:
                    # Required qty of component = (Shortage of FG * Qty of comp in BOM) / BOM Base Qty
                    comp_req_qty = (net_qty * comp.bom_stock_qty) / bom_qty
                    comp_stock = get_actual_qty(comp.item_code)
                    comp_po = get_pending_po_qty(comp.item_code, filters)
                    comp_net = comp_req_qty - comp_stock - comp_po
                    
                    data.append({
                        "name": f"{row.name}_{comp.item_code}",
                        "parent": row.name, # Links to FG row
                        "sales_order": row.sales_order,
                        "customer": "",
                        "delivery_date": None,
                        "item_code": comp.item_code,
                        "item_name": comp.item_name,
                        "pending_qty": comp_req_qty,
                        "stock_qty": comp_stock,
                        "po_qty": comp_po,
                        "net_qty": comp_net
                    })
                    
    return data

def get_actual_qty(item_code):
    return frappe.db.sql("""
        SELECT SUM(actual_qty) 
        FROM `tabBin` 
        WHERE item_code = %s
    """, item_code)[0][0] or 0

def get_pending_po_qty(item_code, filters):
    query = """
        SELECT SUM(poi.qty - poi.received_qty)
        FROM `tabPurchase Order Item` poi
        INNER JOIN `tabPurchase Order` po ON poi.parent = po.name
        WHERE poi.item_code = %(item_code)s
        AND po.docstatus = 1
        AND po.status NOT IN ('Closed', 'Completed')
        AND poi.qty > poi.received_qty
    """
    values = {"item_code": item_code}
    
    if filters.get("company"):
        query += " AND po.company = %(company)s"
        values["company"] = filters.get("company")
        
    if filters.get("project"):
        query += " AND po.project = %(project)s"
        values["project"] = filters.get("project")
        
    return frappe.db.sql(query, values)[0][0] or 0
