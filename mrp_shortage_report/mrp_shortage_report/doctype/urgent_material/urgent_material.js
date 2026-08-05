// Copyright (c) 2026, Nexgen ERP Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on('Urgent Material', {
	purchase_order: function(frm) {
		if (frm.doc.purchase_order) {
			frappe.call({
				method: "mrp_shortage_report.mrp_shortage_report.doctype.urgent_material.urgent_material.get_po_details",
				args: {
					purchase_order: frm.doc.purchase_order
				},
				freeze: true,
				freeze_message: __("Fetching Purchase Order Details..."),
				callback: function(r) {
					if (r.message) {
						let data = r.message;
						frm.set_value("supplier", data.supplier);
						frm.set_value("po_date", data.po_date);
						frm.set_value("po_creator", data.po_creator);
						frm.set_value("project", data.project);
						
						frm.clear_table("items");
						if (data.items && data.items.length > 0) {
							data.items.forEach(function(item) {
								let child = frm.add_child("items");
								child.item_code = item.item_code;
								child.item_name = item.item_name;
								child.description = item.description;
								child.qty = item.qty;
								child.received_qty = item.received_qty;
								child.pending_qty = item.pending_qty;
								child.uom = item.uom;
								child.expected_delivery_date = item.expected_delivery_date;
								child.remarks = item.remarks;
							});
						}
						frm.refresh_field("items");
					}
				}
			});
		} else {
			frm.set_value("supplier", "");
			frm.set_value("po_date", "");
			frm.set_value("po_creator", "");
			frm.set_value("project", "");
			frm.clear_table("items");
			frm.refresh_field("items");
		}
	}
});
