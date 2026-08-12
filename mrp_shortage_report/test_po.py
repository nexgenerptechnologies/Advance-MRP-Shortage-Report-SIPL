import frappe

def run():
    frappe.init(site="erp.simpleintegral.in")
    frappe.connect()

    po = frappe.get_doc("Purchase Order", "PO/SIPL/26-27/ER/0995")
    print("=== PO 0995 Data ===")
    print("project:", po.get("project"))
    print("project_code:", po.get("project_code"))
    print("custom_project_code:", po.get("custom_project_code"))

    for item in po.items:
        print(f"Item {item.item_code} project: {item.project}, project_code: {item.get('project_code')}, custom_project_code: {item.get('custom_project_code')}")

    print("\n=== All fields with 'project' ===")
    for f in po.meta.fields:
        if "project" in f.fieldname or (f.label and "project" in f.label.lower()):
            print(f"Fieldname: {f.fieldname}, Label: {f.label}, Type: {f.fieldtype}")
