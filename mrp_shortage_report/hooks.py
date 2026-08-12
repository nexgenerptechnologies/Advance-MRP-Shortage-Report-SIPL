app_name = "mrp_shortage_report"
app_title = "MRP Shortage Report"
app_publisher = "Nexgen ERP Technologies"
app_description = "MRP Shortage Report for ERPNext"
app_email = "info@nexgenerptechnologies.com"
app_license = "mit"

doctype_js = {
    "Purchase Order": "public/js/purchase_order.js"
}

doc_events = {
    "Purchase Order": {
        "onload": "mrp_shortage_report.mrp_shortage_report.api.set_budget_on_load",
        "on_update": "mrp_shortage_report.mrp_shortage_report.api.set_budget_on_load"
    }
}
