frappe.query_reports["Project Material Tracking Report"] = {
	"filters": [
		{
			"fieldname": "item_code",
			"label": __("Item"),
			"fieldtype": "Link",
			"options": "Item"
		},
		{
			"fieldname": "project",
			"label": __("Project"),
			"fieldtype": "Link",
			"options": "Project"
		},
		{
			"fieldname": "bom_no",
			"label": __("BOM"),
			"fieldtype": "Link",
			"options": "BOM"
		},
		{
			"fieldname": "brand",
			"label": __("Brand"),
			"fieldtype": "Link",
			"options": "Brand"
		},
		{
			"fieldname": "item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group"
		},
		{
			"fieldname": "supplier",
			"label": __("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier"
		},
		{
			"fieldname": "purchase_order",
			"label": __("Purchase Order"),
			"fieldtype": "Link",
			"options": "Purchase Order"
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nPending PO\nPO Raised\nPartially Received\nFully Received\nIn Production\nCompleted"
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname == "status") {
			if (data.status == "Fully Received" || data.status == "Completed") {
				value = "<span style='color:green'>" + value + "</span>";
			} else if (data.status == "Pending PO") {
				value = "<span style='color:red'>" + value + "</span>";
			} else if (data.status == "PO Raised" || data.status == "Partially Received" || data.status == "In Production") {
				value = "<span style='color:orange'>" + value + "</span>";
			}
		}

		return value;
	}
};
