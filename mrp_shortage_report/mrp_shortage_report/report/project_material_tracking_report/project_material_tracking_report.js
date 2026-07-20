frappe.query_reports["Project Material Tracking Report"] = {
	"filters": [
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
				let project = frappe.query_report.get_filter_value('project');
				return frappe.call({
					method: "mrp_shortage_report.mrp_shortage_report.report.project_material_tracking_report.project_material_tracking_report.get_dynamic_bom_options",
					args: {
						project: project,
						txt: txt
					}
				}).then(r => r.message || []);
			}
		},
		{
			"fieldname": "group_by_item",
			"label": __("Group by Item Code"),
			"fieldtype": "Check",
			"default": 0
		},
		{
			"fieldname": "item_code",
			"label": __("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
			"get_query": function() {
				return {
					query: "mrp_shortage_report.mrp_shortage_report.report.project_material_tracking_report.project_material_tracking_report.get_dynamic_link_options",
					filters: {
						"filter_type": "Item",
						"project": frappe.query_report.get_filter_value('project'),
						"bom": JSON.stringify(frappe.query_report.get_filter_value('bom') || [])
					}
				};
			}
		},
		{
			"fieldname": "po_number",
			"label": __("Purchase Order"),
			"fieldtype": "Link",
			"options": "Purchase Order",
			"get_query": function() {
				return {
					query: "mrp_shortage_report.mrp_shortage_report.report.project_material_tracking_report.project_material_tracking_report.get_dynamic_link_options",
					filters: {
						"filter_type": "Purchase Order",
						"project": frappe.query_report.get_filter_value('project')
					}
				};
			}
		},
		{
			"fieldname": "brand",
			"label": __("Brand"),
			"fieldtype": "Link",
			"options": "Brand",
			"get_query": function() {
				return {
					query: "mrp_shortage_report.mrp_shortage_report.report.project_material_tracking_report.project_material_tracking_report.get_dynamic_link_options",
					filters: {
						"filter_type": "Brand",
						"project": frappe.query_report.get_filter_value('project'),
						"bom": JSON.stringify(frappe.query_report.get_filter_value('bom') || [])
					}
				};
			}
		},
		{
			"fieldname": "item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
			"get_query": function() {
				return {
					query: "mrp_shortage_report.mrp_shortage_report.report.project_material_tracking_report.project_material_tracking_report.get_dynamic_link_options",
					filters: {
						"filter_type": "Item Group",
						"project": frappe.query_report.get_filter_value('project'),
						"bom": JSON.stringify(frappe.query_report.get_filter_value('bom') || [])
					}
				};
			}
		},
		{
			"fieldname": "supplier",
			"label": __("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"get_query": function() {
				return {
					query: "mrp_shortage_report.mrp_shortage_report.report.project_material_tracking_report.project_material_tracking_report.get_dynamic_link_options",
					filters: {
						"filter_type": "Supplier",
						"project": frappe.query_report.get_filter_value('project')
					}
				};
			}
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
			"options": "Warehouse",
			"get_query": function() {
				return {
					query: "mrp_shortage_report.mrp_shortage_report.report.project_material_tracking_report.project_material_tracking_report.get_dynamic_link_options",
					filters: {
						"filter_type": "Warehouse",
						"project": frappe.query_report.get_filter_value('project')
					}
				};
			}
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
