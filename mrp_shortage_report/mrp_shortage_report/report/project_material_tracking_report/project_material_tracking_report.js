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
			"fieldname": "bom",
			"label": __("BOM"),
			"fieldtype": "MultiSelectList",
			"get_data": function(txt) {
				return frappe.db.get_link_options("BOM", txt);
			}
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
			"options": "\nPending PO\nPO Raised\nPartially Received\nFully Received\nIn Stock\nProject Completed\nIn Production"
		},
		{
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse"
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname == "status" && data && data.status) {
			let color = "red";
			if (data.status == "Pending PO") color = "red";
			else if (data.status == "PO Raised") color = "orange";
			else if (data.status == "Partially Received") color = "blue";
			else if (data.status == "Fully Received") color = "green";
			else if (data.status == "In Stock") color = "darkgreen";
			else if (data.status == "Project Completed") color = "purple";
			else if (data.status == "In Production") color = "yellow";
			
			value = `<span class='indicator ${color}'>${data.status}</span>`;
		}
		return value;
	}
};
