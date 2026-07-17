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
			"options": "\nMaterial Shortage\nReady for Production\nCompleted"
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname == "status" && data && data.status) {
			let color = "red";
			if (data.status == "Material Shortage") color = "red";
			else if (data.status == "Ready for Production") color = "darkgreen";
			else if (data.status == "Completed") color = "purple";
			
			value = `<span class='indicator ${color}'>${data.status}</span>`;
		}
		if (column.fieldname == "missing_components" && value > 0 && data.missing_items_json) {
            let encoded_json = encodeURIComponent(data.missing_items_json);
            value = `<a href="#" onclick="window.show_missing_items_dialog('${encoded_json}'); return false;" style="color: blue; text-decoration: underline;">${value}</a>`;
		}
		return value;
	}
};

window.show_missing_items_dialog = function(encoded_json) {
    let items = JSON.parse(decodeURIComponent(encoded_json));
    let html = "<div style='max-height: 400px; overflow-y: auto; overflow-x: hidden;'><table class='table table-bordered table-hover'><thead><tr><th>Item Code</th><th>Item Name</th><th>Shortage Qty</th></tr></thead><tbody>";
    let csv = "Item Code,Item Name,Shortage Qty\n";
    
    items.forEach(item => {
        html += `<tr><td>${item.item_code}</td><td>${item.item_name}</td><td>${item.shortage}</td></tr>`;
        let esc_name = (item.item_name || "").toString().replace(/"/g, '""');
        csv += `"${item.item_code}","${esc_name}","${item.shortage}"\n`;
    });
    html += "</tbody></table></div>";
    
    let blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    let url = URL.createObjectURL(blob);
    
    let d = new frappe.ui.Dialog({
        title: __('Missing Components'),
        size: 'large',
        fields: [
            {
                fieldname: 'items_html',
                fieldtype: 'HTML',
                options: html
            }
        ],
        primary_action_label: __('Download as Excel'),
        primary_action(values) {
            let a = document.createElement('a');
            a.href = url;
            a.download = "missing_components.csv";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
    });
    
    d.show();
};
