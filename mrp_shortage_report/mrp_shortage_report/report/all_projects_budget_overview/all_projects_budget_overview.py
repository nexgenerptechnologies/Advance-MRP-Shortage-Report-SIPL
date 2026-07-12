import frappe
from frappe import _
from mrp_shortage_report.mrp_shortage_report.report.project_document_summary.project_document_summary import (
    get_purchase_invoices, get_journal_entries, get_purchase_orders
)

def execute(filters=None):
    if not filters:
        filters = {}
        
    columns = get_columns()
    data = []
    
    projects = frappe.get_all("Project", fields=["name", "project_name"])
    
    total_budget_all = 0.0
    total_expenditures_all = 0.0
    total_pending_po_all = 0.0
    
    for proj in projects:
        project = proj.name
        
        # 1. Fetch Budget Gracefully
        proj_doc = frappe.get_cached_doc("Project", project)
        estimated_cost = (
            proj_doc.get("estimated_costing") or 
            proj_doc.get("estimated_cost") or 
            proj_doc.get("project_value") or 
            0.0
        )
        
        # 2. Calculate Actual Expenditures (Invoices & JEs)
        actual_expenditures = 0.0
        
        pi_summary = get_purchase_invoices(project)
        for row in pi_summary:
            actual_expenditures += row.get("basic_value", 0.0)
            
        je_summary = get_journal_entries(project)
        for row in je_summary:
            actual_expenditures += row.get("basic_value", 0.0)
            
        # 3. Calculate PO Expenditures (Matching Old Report Logic exactly)
        po_expenditures = 0.0
        all_po_summary = get_purchase_orders(project, only_pending=False)
        for row in all_po_summary:
            po_expenditures += row.get("basic_value", 0.0)
            
        percent_expended = (actual_expenditures / estimated_cost * 100) if estimated_cost > 0 else 0.0
        percent_po_used = (po_expenditures / estimated_cost * 100) if estimated_cost > 0 else 0.0
        
        # Add to global totals
        total_budget_all += estimated_cost
        total_expenditures_all += actual_expenditures
        total_pending_po_all += po_expenditures
        
        data.append({
            "project": project,
            "project_name": proj.project_name,
            "project_budget": estimated_cost,
            "actual_expenditures": actual_expenditures,
            "po_expenditures": po_expenditures,
            "percent_expended": percent_expended,
            "percent_po_used": percent_po_used
        })
        
    # Sort data by project ID to match the exact order of the old report
    data = sorted(data, key=lambda x: x.get("project") or "")
    
    # Prepare Summary
    balance_all = total_budget_all - total_pending_po_all
    percent_expended_all = (total_expenditures_all / total_budget_all * 100) if total_budget_all > 0 else 0.0
    
    currency = frappe.defaults.get_global_default("default_currency") or "INR"
    
    report_summary = [
        {"value": total_budget_all, "indicator": "Blue", "label": _("Total Budget"), "datatype": "Currency", "currency": currency},
        {"value": total_expenditures_all, "indicator": "Orange", "label": _("Total Actual Exp"), "datatype": "Currency", "currency": currency},
        {"value": total_pending_po_all, "indicator": "Purple", "label": _("Total PO Expenditures"), "datatype": "Currency", "currency": currency},
        {"value": balance_all, "indicator": "Green" if balance_all >= 0 else "Red", "label": _("Total PO Balance"), "datatype": "Currency", "currency": currency},
        {"value": f"{percent_expended_all:.2f}%", "indicator": "Orange", "label": _("% Total Expended")}
    ]
    
    # User requested NO graphics
    chart = None
    
    return columns, data, None, chart, report_summary

def get_columns():
    return [
        {"fieldname": "project", "label": _("Project"), "fieldtype": "Link", "options": "Project", "width": 200},
        {"fieldname": "project_name", "label": _("Project Name"), "fieldtype": "Data", "width": 250},
        {"fieldname": "project_budget", "label": _("Project Budget"), "fieldtype": "Currency", "width": 140},
        {"fieldname": "actual_expenditures", "label": _("Actual Exp. (Invoices)"), "fieldtype": "Currency", "width": 160},
        {"fieldname": "po_expenditures", "label": _("PO Expenditures"), "fieldtype": "Currency", "width": 140},
        {"fieldname": "percent_expended", "label": _("% Budget Expended"), "fieldtype": "Percent", "width": 150},
        {"fieldname": "percent_po_used", "label": _("% PO Budget Used"), "fieldtype": "Percent", "width": 150}
    ]
