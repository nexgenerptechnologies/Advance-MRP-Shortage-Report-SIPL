import frappe

def run():
    frappe.init(site="erp.simpleintegral.in")
    frappe.connect()

    # Test the API
    from mrp_shortage_report.mrp_shortage_report.api import get_project_budget_used

    print("\n--- Testing API ---")
    val = get_project_budget_used("26-27-SIPL-001")
    print(f"API Result for '26-27-SIPL-001': {val}")
    
    val2 = get_project_budget_used("26-27/SIPL-001")
    print(f"API Result for '26-27/SIPL-001': {val2}")

    print("\n--- Testing DB directly ---")
    sql_result = frappe.db.sql("SELECT name FROM `tabProject` WHERE name LIKE %s", ('%26%27%SIPL%001%',))
    print(f"LIKE search result: {sql_result}")
