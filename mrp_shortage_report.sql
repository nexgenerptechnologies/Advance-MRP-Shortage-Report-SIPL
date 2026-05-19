SELECT
    soi.parent AS "Sales Order:Link/Sales Order:120",
    so.customer AS "Customer:Data:150",
    so.delivery_date AS "Delivery Date:Date:100",
    soi.item_code AS "Item Code:Link/Item:120",
    soi.item_name AS "Item Name:Data:150",
    bin.warehouse AS "Warehouse:Link/Warehouse:120",
    (soi.qty - soi.delivered_qty) AS "Pending SO Qty:Float:120",
    IFNULL(bin.actual_qty, 0) AS "Available Stock:Float:120",
    
    /* Fetch all pending PO numbers for this item */
    (SELECT GROUP_CONCAT(po.name SEPARATOR ', ') 
     FROM `tabPurchase Order Item` po_i 
     JOIN `tabPurchase Order` po ON po.name = po_i.parent 
     WHERE po_i.item_code = soi.item_code 
     AND po.docstatus = 1 
     AND po.status != 'Closed' 
     AND po_i.qty > po_i.received_qty) AS "Pending POs:Data:150",
     
    /* Fetch total pending PO quantity for this item */
    (SELECT SUM(po_i.qty - po_i.received_qty) 
     FROM `tabPurchase Order Item` po_i 
     JOIN `tabPurchase Order` po ON po.name = po_i.parent 
     WHERE po_i.item_code = soi.item_code 
     AND po.docstatus = 1 
     AND po.status != 'Closed' 
     AND po_i.qty > po_i.received_qty) AS "Pending PO Qty:Float:120",
     
    /* Calculate Net Required: Pending SO - Stock - Pending PO */
    (
        (soi.qty - soi.delivered_qty) - 
        IFNULL(bin.actual_qty, 0) - 
        IFNULL((SELECT SUM(po_i.qty - po_i.received_qty) 
                FROM `tabPurchase Order Item` po_i 
                JOIN `tabPurchase Order` po ON po.name = po_i.parent 
                WHERE po_i.item_code = soi.item_code 
                AND po.docstatus = 1 
                AND po.status != 'Closed' 
                AND po_i.qty > po_i.received_qty), 0)
    ) AS "Net Required Qty:Float:120"

FROM
    `tabSales Order Item` soi
INNER JOIN
    `tabSales Order` so ON soi.parent = so.name
LEFT JOIN
    `tabBin` bin ON soi.item_code = bin.item_code AND bin.actual_qty > 0

WHERE
    so.docstatus = 1
    AND so.status NOT IN ('Closed', 'Completed')
    AND soi.qty > soi.delivered_qty

ORDER BY
    so.delivery_date ASC, soi.parent ASC;
