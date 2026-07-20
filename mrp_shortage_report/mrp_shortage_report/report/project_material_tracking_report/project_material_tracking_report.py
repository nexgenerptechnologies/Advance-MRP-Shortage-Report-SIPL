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
        {"fieldname": "project", "label": _("Project"), "fieldtype": "Link", "options": "Project", "width": 140},
        {"fieldname": "bom", "label": _("BOM"), "fieldtype": "Link", "options": "BOM", "width": 140},
        {"fieldname": "bom_date", "label": _("BOM Upload Date"), "fieldtype": "Date", "width": 120},
        {"fieldname": "bom_modified", "label": _("BOM Last Modified Date"), "fieldtype": "Date", "width": 140},
        {"fieldname": "item_code", "label": _("Item Code"), "fieldtype": "Link", "options": "Item", "width": 140},
        {"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 150},
        {"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 150},
        {"fieldname": "brand", "label": _("Brand"), "fieldtype": "Data", "width": 120},
        {"fieldname": "item_group", "label": _("Item Group"), "fieldtype": "Link", "options": "Item Group", "width": 120},
        {"fieldname": "bom_qty", "label": _("BOM Qty"), "fieldtype": "Float", "width": 100},
        {"fieldname": "project_qty", "label": _("Project Qty (Req. Qty)"), "fieldtype": "Float", "width": 140},
        {"fieldname": "stock_qty", "label": _("Stock Qty"), "fieldtype": "Float", "width": 100},
        {"fieldname": "allocated_qty", "label": _("Allocated Qty"), "fieldtype": "Float", "width": 110},
        {"fieldname": "allocation_name", "label": _("Allocation Name"), "fieldtype": "Data", "width": 140},
        {"fieldname": "shortage_qty", "label": _("Shortage Qty"), "fieldtype": "Float", "width": 110},
        {"fieldname": "po_number", "label": _("PO Number"), "fieldtype": "Data", "width": 140},
        {"fieldname": "po_date", "label": _("PO Date"), "fieldtype": "Data", "width": 110},
        {"fieldname": "po_qty", "label": _("PO Qty"), "fieldtype": "Float", "width": 100},
        {"fieldname": "received_qty", "label": _("Received Qty."), "fieldtype": "Float", "width": 110},
        {"fieldname": "balance_qty", "label": _("Balance Qty"), "fieldtype": "Float", "width": 110},
        {"fieldname": "supplier", "label": _("Supplier Name"), "fieldtype": "Data", "width": 140},
        {"fieldname": "exp_delivery_date", "label": _("Exp. Delivery Date"), "fieldtype": "Data", "width": 130},
        {"fieldname": "actual_delivery_date", "label": _("Actual Delivery Date"), "fieldtype": "Data", "width": 130},
        {"fieldname": "net_shortage", "label": _("Net Shortage"), "fieldtype": "Float", "width": 110},
        {"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 140},
    ]

def get_data(filters):
    data = []
    
    # 1. Fetch Projects/BOM Demand
    demand_data = fetch_demand(filters)
    
    # 2. Fetch Factory Stock (Items in Warehouse not covered by BOM/Project)
    factory_data = fetch_factory_stock(filters, demand_data)
    
    # Combine
    all_rows = demand_data + factory_data
    
    # Apply standard item filters (Item Group, Brand, etc.)
    all_rows = apply_item_filters(all_rows, filters)
    
    # 3. Calculate logical allocations and true shortages per row
    stock_map = {}
    balance_map = {}
    for r in all_rows:
        item = r["item_code"]
        if item not in stock_map:
            stock_map[item] = r["stock_qty"]
        if item not in balance_map:
            balance_map[item] = r["balance_qty"]
            
        req = r.get("project_qty", 0)
        
        # Allocate Stock
        if stock_map[item] >= req:
            r["allocated_qty"] = req
            r["shortage_qty"] = 0
            stock_map[item] -= req
            r["allocation_name"] = r.get("project") or ""
        else:
            r["allocated_qty"] = stock_map[item]
            r["shortage_qty"] = req - stock_map[item]
            if stock_map[item] > 0:
                r["allocation_name"] = r.get("project") or ""
            else:
                r["allocation_name"] = ""
            stock_map[item] = 0
            
        # Allocate PO Balance against Shortage
        shortage = r["shortage_qty"]
        if balance_map[item] >= shortage:
            r["net_shortage"] = 0
            balance_map[item] -= shortage
        else:
            r["net_shortage"] = shortage - balance_map[item]
            balance_map[item] = 0
    
    # Apply PO Filter
    if filters.get("po_number"):
        all_rows = [r for r in all_rows if filters.get("po_number") in (r.get("po_number") or "")]

    # Apply Status Filter
    if filters.get("status"):
        all_rows = [r for r in all_rows if r.get("status") == filters.get("status")]
        
    # Apply Group By
    if filters.get("group_by_item") or filters.get("po_number"):
        grouped = {}
        for r in all_rows:
            item = r.get("item_code")
            if item not in grouped:
                grouped[item] = r.copy()
                grouped[item]["bom"] = "Multiple"
                grouped[item]["bom_date"] = None
                grouped[item]["bom_modified"] = None
            else:
                grouped[item]["bom_qty"] += r.get("bom_qty", 0)
                grouped[item]["project_qty"] += r.get("project_qty", 0)
                grouped[item]["allocated_qty"] += r.get("allocated_qty", 0)
                grouped[item]["shortage_qty"] += r.get("shortage_qty", 0)
                grouped[item]["net_shortage"] += r.get("net_shortage", 0)
                
                if grouped[item].get("allocation_name") != r.get("allocation_name") and r.get("allocation_name"):
                    grouped[item]["allocation_name"] = "Multiple"
                    grouped[item]["project"] = "Multiple"
                    
                grouped[item]["status"] = determine_status(
                    grouped[item]["project_qty"],
                    grouped[item]["stock_qty"],
                    grouped[item]["po_qty"],
                    grouped[item]["received_qty"],
                    grouped[item].get("project"),
                    item
                )
        all_rows = list(grouped.values())
        
    return all_rows

def fetch_demand(filters):
    rows = []
    # Identify how Project Links to BOM. Using similar logic to advanced report
    bom_project_field = "project" if frappe.db.has_column("BOM", "project") else ("custom_project" if frappe.db.has_column("BOM", "custom_project") else None)
    
    conditions = ["docstatus = 1", "is_active = 1"]
    values = {}
    
    if filters.get("project") and bom_project_field:
        conditions.append(f"{bom_project_field} = %(project)s")
        values["project"] = filters.get("project")
    if filters.get("bom"):
        boms = filters.get("bom")
        if isinstance(boms, list):
            conditions.append("name IN %(bom)s")
            values["bom"] = tuple(boms)
        else:
            conditions.append("name = %(bom)s")
            values["bom"] = boms
        
    bom_query = f"SELECT name, item, quantity, creation, modified, {bom_project_field or 'NULL'} as project FROM `tabBOM` WHERE " + " AND ".join(conditions)
    boms = frappe.db.sql(bom_query, values, as_dict=1)
    
    processed_nodes = set()
    
    for bom in boms:
        # Explode BOM to get components
        components = frappe.db.sql("""
            SELECT item_code, item_name, description, qty as bom_qty, qty as req_qty
            FROM `tabBOM Item`
            WHERE parent = %s
        """, bom.name, as_dict=1)
        
        for comp in components:
            row = build_row(
                item_code=comp.item_code,
                project=bom.project,
                bom_name=bom.name,
                bom_date=bom.creation,
                bom_modified=bom.modified,
                bom_qty=comp.bom_qty,
                project_qty=comp.req_qty, # Base required qty
                filters=filters
            )
            if row:
                rows.append(row)
                processed_nodes.add((bom.project, comp.item_code))
                
    return rows

def fetch_factory_stock(filters, demand_data):
    rows = []
    # If a specific warehouse is filtered, we look for items in that warehouse
    wh = filters.get("warehouse")
    if not wh:
        return rows # If no warehouse filter, we only show demand-based items by default unless specified
        
    # Get all items in this warehouse that have stock > 0 OR have pending POs
    items_in_wh = frappe.db.sql("""
        SELECT DISTINCT item_code 
        FROM `tabBin` 
        WHERE warehouse = %s AND actual_qty > 0
    """, wh, as_dict=1)
    
    po_items_in_wh = frappe.db.sql("""
        SELECT DISTINCT poi.item_code 
        FROM `tabPurchase Order Item` poi
        INNER JOIN `tabPurchase Order` po ON poi.parent = po.name
        WHERE poi.warehouse = %s AND po.docstatus = 1 AND poi.qty > poi.received_qty
    """, wh, as_dict=1)
    
    all_factory_items = set([i.item_code for i in items_in_wh] + [i.item_code for i in po_items_in_wh])
    
    # Filter out items already in demand_data if they match the project (or just add them as standalone rows)
    existing_demand_items = set([r.get("item_code") for r in demand_data])
    
    for item_code in all_factory_items:
        if item_code not in existing_demand_items:
            row = build_row(
                item_code=item_code,
                project=None,
                bom_name=None,
                bom_date=None,
                bom_modified=None,
                bom_qty=0,
                project_qty=0,
                filters=filters
            )
            if row:
                rows.append(row)
                
    return rows

def build_row(item_code, project, bom_name, bom_date, bom_modified, bom_qty, project_qty, filters):
    if filters.get("item_code") and item_code != filters.get("item_code"):
        return None
        
    item = frappe.db.get_value("Item", item_code, ["item_name", "description", "brand", "item_group"], as_dict=True) or {}
    
    # 1. Stock Info (Filtered by Warehouse if provided)
    wh_filter = filters.get("warehouse")
    stock_qty = get_stock_qty(item_code, wh_filter)
    
    shortage_qty = max(0, project_qty - stock_qty)
    
    # 2. PO Details
    po_filter = filters.get("po_number")
    po_number, po_date, po_qty, received_qty, supplier, exp_delivery_date, actual_delivery_date = get_po_details(item_code, project, wh_filter, po_filter)
    
    # 3. Calculations
    balance_qty = max(0, po_qty - received_qty)
    net_shortage = max(0, shortage_qty - balance_qty)
    
    # 4. Status Determination
    status = determine_status(project_qty, stock_qty, po_qty, received_qty, project, item_code)
    
    return {
        "project": project,
        "bom": bom_name,
        "bom_date": bom_date.date() if bom_date else None,
        "bom_modified": bom_modified.date() if bom_modified else None,
        "item_code": item_code,
        "item_name": item.get("item_name"),
        "description": item.get("description"),
        "brand": item.get("brand"),
        "item_group": item.get("item_group"),
        "bom_qty": bom_qty,
        "project_qty": project_qty,
        "stock_qty": stock_qty,
        "allocated_qty": 0,
        "allocation_name": project if (stock_qty > 0) else "",
        "shortage_qty": shortage_qty,
        "po_number": po_number,
        "po_date": po_date,
        "po_qty": po_qty,
        "received_qty": received_qty,
        "balance_qty": balance_qty,
        "supplier": supplier,
        "exp_delivery_date": exp_delivery_date,
        "actual_delivery_date": actual_delivery_date,
        "net_shortage": net_shortage,
        "status": status
    }

def get_stock_qty(item_code, warehouse=None):
    if warehouse:
        return frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty") or 0.0
    else:
        bins = frappe.db.get_all("Bin", filters={"item_code": item_code}, fields=["actual_qty"])
        return sum([b.actual_qty for b in bins])

def get_po_details(item_code, project=None, warehouse=None, po_number=None):
    conditions = ["poi.item_code = %(item_code)s", "po.docstatus = 1", "po.status != 'Cancelled'"]
    values = {"item_code": item_code}
    
    if po_number:
        conditions.append("po.name = %(po_number)s")
        values["po_number"] = po_number
        
    if project:
        # Standard ERPNext has project on PO item
        conditions.append("poi.project = %(project)s")
        values["project"] = project
        
    if warehouse:
        conditions.append("poi.warehouse = %(warehouse)s")
        values["warehouse"] = warehouse
        
    query = f"""
        SELECT po.name, po.transaction_date, poi.qty, poi.received_qty, po.supplier, poi.schedule_date
        FROM `tabPurchase Order Item` poi
        INNER JOIN `tabPurchase Order` po ON poi.parent = po.name
        WHERE {" AND ".join(conditions)}
        ORDER BY po.transaction_date DESC
    """
    
    pos = frappe.db.sql(query, values, as_dict=1)
    
    if not pos:
        return "", "", 0.0, 0.0, "", "", ""
        
    po_names = list(set([p.name for p in pos]))
    po_numbers = ", ".join(po_names)
    po_dates = ", ".join(list(set([str(p.transaction_date) for p in pos if p.transaction_date])))
    suppliers = ", ".join(list(set([p.supplier for p in pos if p.supplier])))
    exp_dates = ", ".join(list(set([str(p.schedule_date) for p in pos if p.schedule_date])))
    
    actual_delivery_dates = ""
    if po_names:
        pr_query = f"""
            SELECT DISTINCT pr.posting_date
            FROM `tabPurchase Receipt Item` pri
            INNER JOIN `tabPurchase Receipt` pr ON pri.parent = pr.name
            WHERE pri.purchase_order IN ({', '.join(['%s']*len(po_names))})
            AND pri.item_code = %s
            AND pr.docstatus = 1
        """
        pr_dates = frappe.db.sql(pr_query, tuple(po_names) + (item_code,))
        if pr_dates:
            actual_delivery_dates = ", ".join(list(set([str(r[0]) for r in pr_dates if r[0]])))
    
    total_po_qty = sum([p.qty for p in pos])
    total_received = sum([p.received_qty for p in pos])
    
    return po_numbers, po_dates, total_po_qty, total_received, suppliers, exp_dates, actual_delivery_dates

def determine_status(req_qty, stock_qty, po_qty, received_qty, project=None, item_code=None):
    if project:
        is_project_completed = frappe.db.get_value("Project", project, "status") == "Completed"
        has_invoice = frappe.db.exists("Sales Invoice", {"project": project, "docstatus": 1})
        if is_project_completed or has_invoice:
            return "Project Completed"
            
        if item_code:
            in_production = frappe.db.sql("""
                SELECT 1 
                FROM `tabStock Entry Detail` sed
                INNER JOIN `tabStock Entry` se ON sed.parent = se.name
                WHERE se.docstatus = 1 
                  AND se.purpose IN ('Material Transfer for Manufacture', 'Material Transfer')
                  AND se.project = %s
                  AND sed.item_code = %s
                LIMIT 1
            """, (project, item_code))
            if in_production:
                return "In Production"
            
    if req_qty > 0 and stock_qty >= req_qty:
        return "In Stock"
    if received_qty >= (req_qty - stock_qty) and received_qty > 0:
        return "Fully Received"
    if received_qty > 0:
        return "Partially Received"
    if po_qty > 0:
        return "PO Raised"
        
    return "Pending PO"

@frappe.whitelist()
def get_dynamic_bom_options(project=None, txt=None):
    conditions = ["docstatus = 1", "is_active = 1"]
    values = {}
    
    if txt:
        conditions.append("name LIKE %(txt)s")
        values["txt"] = f"%{txt}%"
        
    if project:
        bom_project_field = "project" if frappe.db.has_column("BOM", "project") else ("custom_project" if frappe.db.has_column("BOM", "custom_project") else None)
        if bom_project_field:
            conditions.append(f"{bom_project_field} = %(project)s")
            values["project"] = project
            
    boms = frappe.db.sql(f"SELECT name as value, name as description FROM `tabBOM` WHERE {' AND '.join(conditions)} LIMIT 50", values, as_dict=1)
    return boms

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_dynamic_link_options(doctype, txt, searchfield, start, page_len, filters):
    filter_type = filters.get("filter_type")
    project = filters.get("project")
    bom_filter = filters.get("bom")
    
    boms = []
    if bom_filter:
        import json
        try:
            boms = json.loads(bom_filter)
        except:
            boms = [bom_filter]
            
    # Fallback to standard
    if not project and not boms:
        return frappe.db.sql(f"SELECT name FROM `tab{doctype}` WHERE name LIKE %s LIMIT %s OFFSET %s", (f"%{txt}%", page_len, start))
        
    txt_cond = f"AND name LIKE '%%{frappe.db.escape(txt)}%%'" if txt else ""
    
    bom_cond = "1=1"
    params = ()
    if boms:
        bom_cond = f"parent IN ({', '.join(['%s']*len(boms))})"
        params = tuple(boms)
    elif project:
        bom_project_field = "project" if frappe.db.has_column("BOM", "project") else ("custom_project" if frappe.db.has_column("BOM", "custom_project") else None)
        if bom_project_field:
            bom_cond = f"parent IN (SELECT name FROM `tabBOM` WHERE {bom_project_field} = %s AND docstatus=1)"
            params = (project,)
            
    if filter_type == "Item":
        query = f"""
            SELECT DISTINCT item_code 
            FROM `tabBOM Item` 
            WHERE {bom_cond} AND item_code LIKE %s
            LIMIT %s OFFSET %s
        """
        return frappe.db.sql(query, params + (f"%{txt}%", page_len, start))
        
    elif filter_type == "Purchase Order":
        proj_cond = "AND poi.project = %s" if project else ""
        query = f"""
            SELECT DISTINCT po.name 
            FROM `tabPurchase Order` po
            INNER JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
            WHERE po.docstatus = 1 {proj_cond} {txt_cond}
            LIMIT %s OFFSET %s
        """
        return frappe.db.sql(query, (project, page_len, start) if project else (page_len, start))
        
    elif filter_type == "Supplier":
        proj_cond = "AND poi.project = %s" if project else ""
        query = f"""
            SELECT DISTINCT po.supplier 
            FROM `tabPurchase Order` po
            INNER JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
            WHERE po.docstatus = 1 {proj_cond} AND po.supplier LIKE %s
            LIMIT %s OFFSET %s
        """
        return frappe.db.sql(query, (project, f"%{txt}%", page_len, start) if project else (f"%{txt}%", page_len, start))
        
    elif filter_type == "Brand":
        query = f"""
            SELECT DISTINCT i.brand 
            FROM `tabBOM Item` bi
            INNER JOIN `tabItem` i ON bi.item_code = i.name
            WHERE {bom_cond} AND i.brand IS NOT NULL AND i.brand LIKE %s
            LIMIT %s OFFSET %s
        """
        return frappe.db.sql(query, params + (f"%{txt}%", page_len, start))
        
    elif filter_type == "Item Group":
        query = f"""
            SELECT DISTINCT i.item_group 
            FROM `tabBOM Item` bi
            INNER JOIN `tabItem` i ON bi.item_code = i.name
            WHERE {bom_cond} AND i.item_group IS NOT NULL AND i.item_group LIKE %s
            LIMIT %s OFFSET %s
        """
        return frappe.db.sql(query, params + (f"%{txt}%", page_len, start))
        
    elif filter_type == "Warehouse":
        proj_cond = "AND poi.project = %s" if project else ""
        query = f"""
            SELECT DISTINCT poi.warehouse 
            FROM `tabPurchase Order Item` poi
            INNER JOIN `tabPurchase Order` po ON poi.parent = po.name
            WHERE po.docstatus = 1 {proj_cond} AND poi.warehouse LIKE %s
            LIMIT %s OFFSET %s
        """
        return frappe.db.sql(query, (project, f"%{txt}%", page_len, start) if project else (f"%{txt}%", page_len, start))
        
    return frappe.db.sql(f"SELECT name FROM `tab{doctype}` WHERE name LIKE %s LIMIT %s OFFSET %s", (f"%{txt}%", page_len, start))

def apply_item_filters(rows, filters):
    if not filters:
        return rows
        
    filtered_rows = []
    for r in rows:
        match = True
        if filters.get("brand") and r.get("brand") != filters.get("brand"):
            match = False
        if filters.get("item_group") and r.get("item_group") != filters.get("item_group"):
            match = False
        if filters.get("supplier") and r.get("supplier") not in (r.get("supplier") or ""):
            match = False
        if filters.get("purchase_order") and filters.get("purchase_order") not in (r.get("po_number") or ""):
            match = False
            
        if filters.get("warehouse"):
            if r.get("stock_qty") == 0 and r.get("po_qty") == 0:
                match = False
            
        if match:
            filtered_rows.append(r)
            
    return filtered_rows
