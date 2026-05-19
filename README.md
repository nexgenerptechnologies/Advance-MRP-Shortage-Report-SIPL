# MRP Shortage Report (ERPNext)

This repository contains a custom SQL Query Report for ERPNext (v15 and v16) that provides a comprehensive view of material requirements based on open Sales Orders, current Warehouse Stock, and incoming Purchase Orders.

## Features
- **Sales Order Demand:** Displays pending quantities from submitted Sales Orders.
- **Warehouse-Wise Stock:** Dynamically splits items by warehouse if stock exists in multiple locations.
- **Incoming Supply:** Aggregates pending Purchase Order quantities for the item.
- **Net Required Qty Calculation:** Automatically calculates `(Pending SO Qty) - (Available Stock) - (Pending PO Qty)` to show the true shortage.

## Installation in ERPNext
1. Go to the global search bar and type **Report List** -> Add a new Report.
2. **Report Name:** MRP Shortage Report
3. **Ref DocType:** Sales Order
4. **Report Type:** Query Report
5. Check the **Is Standard** box as "No".
6. Copy the entire contents of `mrp_shortage_report.sql` and paste it into the **Query** text box.
7. Save the report.
