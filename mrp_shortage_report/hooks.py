app_name = "mrp_shortage_report"
app_title = "MRP Shortage Report"
app_publisher = "Nexgen ERP Technologies"
app_description = "MRP Shortage Report for ERPNext"
app_email = "info@nexgenerptechnologies.com"
app_license = "mit"

doc_events = {
    "Purchase Order": {
        "onload": "mrp_shortage_report.mrp_shortage_report.api.set_budget_on_load"
    }
}

doctype_js = {
    "Purchase Order": "public/js/purchase_order.js"
}
