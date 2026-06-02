import frappe

def execute():
    if frappe.db.exists('Report', 'MRP Shortage Report'):
        frappe.db.set_value('Report', 'MRP Shortage Report', 'report_type', 'Script Report')
        frappe.db.set_value('Report', 'MRP Shortage Report', 'query', '')
        frappe.db.commit()
