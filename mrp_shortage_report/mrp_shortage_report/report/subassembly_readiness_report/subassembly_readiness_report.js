frappe.query_reports["Subassembly Readiness Report"] = {
	"filters": [
		{
			"fieldname": "project",
			"label": __("Project"),
			"fieldtype": "Link",
			"options": "Project"
		},
		{
			"fieldname": "item_code",
			"label": __("Subassembly Item"),
			"fieldtype": "Link",
			"options": "Item"
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
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nMaterial Shortage\nReady for Production\nIn Production\nCompleted"
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname == "status" && data && data.status) {
			let color = "red";
			if (data.status == "Material Shortage") color = "red";
			else if (data.status == "Ready for Production") color = "darkgreen";
			else if (data.status == "In Production") color = "orange";
			else if (data.status == "Completed") color = "purple";
			
			value = `<span class='indicator ${color}'>${data.status}</span>`;
		}
		return value;
	}
};
