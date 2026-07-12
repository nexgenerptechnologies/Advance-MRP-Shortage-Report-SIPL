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
        
        # 2. Calculate Expenditures
        actual_expenditures = 0.0
        pending_po_value = 0.0
        
        # Calculate PI expenditures
        pi_summary = get_purchase_invoices(project)
        for row in pi_summary:
            actual_expenditures += row.get("basic_value", 0.0)
            
        # Calculate JE expenditures
        je_summary = get_journal_entries(project)
        for row in je_summary:
            actual_expenditures += row.get("basic_value", 0.0)
            
        # Calculate Pending PO Value
        pending_po_summary = get_purchase_orders(project, only_pending=True)
        for row in pending_po_summary:
            pending_po_value += row.get("basic_value", 0.0)
            
        total_committed = actual_expenditures + pending_po_value
        
        percent_expended = (actual_expenditures / estimated_cost * 100) if estimated_cost > 0 else 0.0
        percent_committed = (total_committed / estimated_cost * 100) if estimated_cost > 0 else 0.0
        
        # Add to global totals
        total_budget_all += estimated_cost
        total_expenditures_all += actual_expenditures
        total_pending_po_all += pending_po_value
        
        data.append({
            "project": project,
            "project_name": proj.project_name,
            "project_budget": estimated_cost,
            "actual_expenditures": actual_expenditures,
            "pending_po_value": pending_po_value,
            "total_committed": total_committed,
            "percent_expended": percent_expended,
            "percent_committed": percent_committed
        })
        
    # Sort data by project name
    data = sorted(data, key=lambda x: x.get("project_name") or "")
    
    # Prepare Summary
    total_committed_all = total_expenditures_all + total_pending_po_all
    balance_all = total_budget_all - total_committed_all
    percent_expended_all = (total_expenditures_all / total_budget_all * 100) if total_budget_all > 0 else 0.0
    
    currency = frappe.defaults.get_global_default("default_currency") or "INR"
    
    report_summary = [
        {"value": total_budget_all, "indicator": "Blue", "label": _("Total Budget"), "datatype": "Currency", "currency": currency},
        {"value": total_expenditures_all, "indicator": "Orange", "label": _("Total Actual Exp"), "datatype": "Currency", "currency": currency},
        {"value": total_pending_po_all, "indicator": "Red", "label": _("Total Pending POs"), "datatype": "Currency", "currency": currency},
        {"value": balance_all, "indicator": "Green" if balance_all >= 0 else "Red", "label": _("Total Balance"), "datatype": "Currency", "currency": currency},
        {"value": f"{percent_expended_all:.2f}%", "indicator": "Orange", "label": _("% Total Expended")}
    ]
    
    # Generate Donut Chart
    chart = {
        "data": {
            "labels": [_("Actual Expenditures"), _("Pending PO Value"), _("Balance Remaining")],
            "datasets": [
                {
                    "name": _("Global Budget Breakdown"),
                    "values": [total_expenditures_all, total_pending_po_all, balance_all if balance_all > 0 else 0]
                }
            ]
        },
        "type": "donut",
        "colors": ["#fd8c00", "#ff0000", "#28a745"]
    }
    
    return columns, data, None, chart, report_summary

def get_columns():
    return [
        {"fieldname": "project", "label": _("Project"), "fieldtype": "Link", "options": "Project", "width": 200},
        {"fieldname": "project_name", "label": _("Project Name"), "fieldtype": "Data", "width": 250},
        {"fieldname": "project_budget", "label": _("Project Budget"), "fieldtype": "Currency", "width": 140},
        {"fieldname": "actual_expenditures", "label": _("Actual Expenditures"), "fieldtype": "Currency", "width": 150},
        {"fieldname": "pending_po_value", "label": _("Pending PO Value"), "fieldtype": "Currency", "width": 140},
        {"fieldname": "total_committed", "label": _("Total Committed"), "fieldtype": "Currency", "width": 140},
        {"fieldname": "percent_expended", "label": _("% Budget Expended"), "fieldtype": "Percent", "width": 150},
        {"fieldname": "percent_committed", "label": _("% Budget Committed"), "fieldtype": "Percent", "width": 150}
    ]
