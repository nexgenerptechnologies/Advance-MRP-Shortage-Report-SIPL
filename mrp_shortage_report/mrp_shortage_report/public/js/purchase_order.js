frappe.ui.form.on("Purchase Order", {
    refresh: function(frm) {
        update_project_budget(frm);
    },
    project: function(frm) {
        update_project_budget(frm);
    }
});

function update_project_budget(frm) {
    // 1. Get the Project. If the header project is empty, check the items.
    let project = frm.doc.project;
    if (!project && frm.doc.items && frm.doc.items.length > 0) {
        for (let i = 0; i < frm.doc.items.length; i++) {
            if (frm.doc.items[i].project) {
                project = frm.doc.items[i].project;
                break;
            }
        }
    }
    
    // 2. Identify the budget fieldname
    let fieldname = frm.fields_dict.custom_project_budget_used ? "custom_project_budget_used" : 
                    (frm.fields_dict.project_budget_used ? "project_budget_used" : null);

    if (project && fieldname) {
        frappe.call({
            method: "mrp_shortage_report.mrp_shortage_report.api.get_project_budget_used",
            args: {
                project: project
            },
            callback: function(r) {
                if (r.message !== undefined) {
                    // PURE VISUAL UPDATE - Bypasses Frappe's dirty tracking entirely!
                    let field = frm.fields_dict[fieldname];
                    if (field) {
                        let formatted_val = format_currency(r.message, frm.doc.currency);
                        
                        // If document is submitted, the field is rendered as text
                        if (field.$wrapper.find('.control-value').length > 0) {
                            field.$wrapper.find('.control-value').text(formatted_val);
                        } 
                        // If document is draft, it might be an input field
                        else if (field.$input) {
                            field.$input.val(formatted_val);
                        }
                        
                        // We do NOT modify frm.doc[fieldname] so Frappe stays completely unaware.
                    }
                }
            }
        });
    } else if (fieldname) {
        // Clear visually if no project
        let field = frm.fields_dict[fieldname];
        if (field) {
            let formatted_val = format_currency(0, frm.doc.currency);
            if (field.$wrapper.find('.control-value').length > 0) {
                field.$wrapper.find('.control-value').text(formatted_val);
            } else if (field.$input) {
                field.$input.val(formatted_val);
            }
        }
    }
}
