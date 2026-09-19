frappe.query_reports["Project Document Summary"] = {
	"filters": [
		{
			"fieldname": "project",
			"label": __("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"reqd": 1
		},
		{
			"fieldname": "document_type",
			"label": __("Document Type"),
			"fieldtype": "Select",
			"options": "Purchase Invoice + Journal Entries\nPurchase Invoice + JEs + Pending POs\nPurchase Order Only",
			"default": "Purchase Invoice + JEs + Pending POs",
			"reqd": 1
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.type) {
			if (data.type === "Purchase Order") {
				if (column.fieldname == "type") {
					value = "<span style='color:blue'>" + value + "</span>";
				}
			} else if (data.type === "Purchase Invoice") {
				if (column.fieldname == "type") {
					value = "<span style='color:green'>" + value + "</span>";
				}
			} else if (data.type === "Journal Entry") {
				if (column.fieldname == "type") {
					value = "<span style='color:orange'>" + value + "</span>";
				}
			}
		}
		
		// Make Linked Documents clickable
		if (column.fieldname === "linked_documents" && value) {
			let docs = value.split(",").map(d => d.trim());
			let doctype = "";
			if (data.type === "Purchase Order") {
				doctype = "Purchase Invoice";
			} else if (data.type === "Purchase Invoice") {
				doctype = "Purchase Order";
			}
			
			if (doctype) {
				value = docs.map(d => `<a href="/app/${frappe.router.slug(doctype)}/${d}" style="font-weight: 500;">${d}</a>`).join(", ");
			}
		}
		
		return value;
	}
};
