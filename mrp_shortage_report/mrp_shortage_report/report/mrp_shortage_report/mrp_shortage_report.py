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
        {"fieldname": "name", "label": _("Order / Component"), "fieldtype": "Data", "width": 250},
        {"fieldname": "parent", "label": _("Parent"), "fieldtype": "Data", "hidden": 1},
        {"fieldname": "sales_order", "label": _("Sales Order"), "fieldtype": "Link", "options": "Sales Order", "width": 140},
        {"fieldname": "so_date", "label": _("SO Date"), "fieldtype": "Date", "width": 100},
        {"fieldname": "customer", "label": _("Customer"), "fieldtype": "Data", "width": 140},
        {"fieldname": "delivery_date", "label": _("Delivery Date"), "fieldtype": "Date", "width": 110},
        {"fieldname": "item_group", "label": _("Item Group"), "fieldtype": "Link", "options": "Item Group", "width": 120},
        {"fieldname": "item_code", "label": _("Item Code"), "fieldtype": "Link", "options": "Item", "width": 150},
        {"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 180},
        {"fieldname": "warehouse_str", "label": _("Warehouse Details"), "fieldtype": "Data", "width": 200},
        {"fieldname": "pending_qty", "label": _("Required Qty"), "fieldtype": "Float", "width": 110},
        {"fieldname": "stock_qty", "label": _("Available Stock"), "fieldtype": "Float", "width": 120},
        {"fieldname": "po_dates", "label": _("PO Date"), "fieldtype": "Data", "width": 110},
        {"fieldname": "po_qty", "label": _("Pending PO Qty"), "fieldtype": "Float", "width": 130},
        {"fieldname": "exp_dates", "label": _("Expected Delivery"), "fieldtype": "Data", "width": 130},
        {"fieldname": "suppliers", "label": _("Supplier Name"), "fieldtype": "Data", "width": 150},
        {"fieldname": "net_qty", "label": _("Net Shortage"), "fieldtype": "Float", "width": 110}
    ]

def get_data(filters):
    data = []
    
    query = """
        SELECT
            soi.name as soi_name, soi.parent as sales_order, so.transaction_date as so_date, 
            so.customer, so.delivery_date,
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
        
    if filters.get("bom"):
        # Find the item for this BOM
        bom_item = frappe.db.get_value("BOM", filters.get("bom"), "item")
        if bom_item:
            conditions.append("soi.item_code = %(bom_item)s")
            values["bom_item"] = bom_item
        
    if conditions:
        query += " AND " + " AND ".join(conditions)
        
    query += " ORDER BY so.delivery_date ASC, soi.parent ASC"
    
    so_items = frappe.db.sql(query, values, as_dict=1)
    
    for row in so_items:
        pending_qty = row.qty - row.delivered_qty
        
        explode_node(
            item_code=row.item_code,
            item_name=row.item_name,
            req_qty=pending_qty,
            parent_node="",
            base_node_name=f"{row.sales_order} | {row.item_code}",
            so_data=row,
            filters=filters,
            data=data
        )
                    
    return data

def explode_node(item_code, item_name, req_qty, parent_node, base_node_name, so_data, filters, data):
    item_group = frappe.db.get_value("Item", item_code, "item_group")
    stock_qty, warehouse_str = get_warehouse_stock(item_code)
    po_qty, po_dates, exp_dates, suppliers = get_pending_po_details(item_code, filters)
    
    net_qty = req_qty - stock_qty - po_qty
    
    if parent_node == "":
        node_name = base_node_name
    else:
        node_name = f"{parent_node} -> {item_code}"
        
    data.append({
        "name": node_name,
        "parent": parent_node,
        "sales_order": so_data.sales_order,
        "so_date": so_data.so_date,
        "customer": so_data.customer if parent_node == "" else "",
        "delivery_date": so_data.delivery_date if parent_node == "" else None,
        "item_group": item_group,
        "item_code": item_code,
        "item_name": item_name,
        "warehouse_str": warehouse_str,
        "pending_qty": req_qty,
        "stock_qty": stock_qty,
        "po_dates": po_dates,
        "po_qty": po_qty,
        "exp_dates": exp_dates,
        "suppliers": suppliers,
        "net_qty": net_qty
    })
    
    # Recursive explosion if shortage exists
    if net_qty > 0:
        default_bom = frappe.db.get_value("Item", item_code, "default_bom")
        if default_bom:
            bom_base_qty = frappe.db.get_value("BOM", default_bom, "quantity") or 1.0
            components = frappe.db.get_all(
                "BOM Item", 
                filters={"parent": default_bom}, 
                fields=["item_code", "item_name", "qty as bom_qty"], 
                order_by="idx asc"
            )
            for comp in components:
                comp_req_qty = (net_qty * comp.bom_qty) / bom_base_qty
                explode_node(
                    item_code=comp.item_code,
                    item_name=comp.item_name,
                    req_qty=comp_req_qty,
                    parent_node=node_name,
                    base_node_name="",
                    so_data=so_data,
                    filters=filters,
                    data=data
                )

def get_warehouse_stock(item_code):
    bins = frappe.db.sql("""
        SELECT warehouse, actual_qty 
        FROM `tabBin` 
        WHERE item_code = %s AND actual_qty > 0
    """, item_code, as_dict=1)
    
    if not bins:
        return 0, ""
        
    total_qty = sum([b.actual_qty for b in bins])
    wh_strings = [f"{b.warehouse} ({b.actual_qty:g})" for b in bins]
    return total_qty, " | ".join(wh_strings)

def get_pending_po_details(item_code, filters):
    query = """
        SELECT 
            po.transaction_date, 
            poi.schedule_date, 
            po.supplier, 
            (poi.qty - poi.received_qty) as pending_qty
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
        
    res = frappe.db.sql(query, values, as_dict=1)
    
    if not res:
        return 0, "", "", ""
        
    total_po_qty = sum([r.pending_qty for r in res])
    po_dates = ", ".join(list(set([str(r.transaction_date) for r in res if r.transaction_date])))
    exp_dates = ", ".join(list(set([str(r.schedule_date) for r in res if r.schedule_date])))
    suppliers = ", ".join(list(set([r.supplier for r in res if r.supplier])))
    
    return total_po_qty, po_dates, exp_dates, suppliers
