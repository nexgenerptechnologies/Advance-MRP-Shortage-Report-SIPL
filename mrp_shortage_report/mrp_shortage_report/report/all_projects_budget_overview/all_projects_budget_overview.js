frappe.query_reports["All Projects Budget Overview"] = {
	"filters": [],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		if (column.fieldname == "percent_expended" || column.fieldname == "percent_committed") {
			if (data[column.fieldname] > 100) {
				value = "<span style='color:red'>" + value + "</span>";
			} else if (data[column.fieldname] == 100) {
				value = "<span style='color:orange'>" + value + "</span>";
			} else {
				value = "<span style='color:green'>" + value + "</span>";
			}
		}
		
		return value;
	}
};
