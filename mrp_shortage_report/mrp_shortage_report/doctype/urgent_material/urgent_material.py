# -*- coding: utf-8 -*-
import frappe
from frappe.model.document import Document

class UrgentMaterial(Document):
	def validate(self):
		if not self.items:
			frappe.throw("Please add at least one item or select a valid Purchase Order.")

@frappe.whitelist()
def get_po_details(purchase_order):
	if not purchase_order:
		return {}
		
	po = frappe.get_doc("Purchase Order", purchase_order)
	
	items = []
	project = ""
	
	for item in po.items:
		if not project and item.project:
			project = item.project
			
		received_qty = float(item.received_qty or 0.0)
		qty = float(item.qty or 0.0)
		pending_qty = max(0.0, qty - received_qty)
		
		items.append({
			"item_code": item.item_code,
			"item_name": item.item_name,
			"description": item.description,
			"qty": qty,
			"received_qty": received_qty,
			"pending_qty": pending_qty,
			"uom": item.uom or item.stock_uom,
			"expected_delivery_date": item.schedule_date,
			"remarks": ""
		})
		
	return {
		"supplier": po.supplier,
		"po_date": po.transaction_date,
		"po_creator": po.owner,
		"project": project,
		"items": items
	}
