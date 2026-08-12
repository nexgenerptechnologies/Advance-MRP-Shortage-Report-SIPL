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
                    let fieldname = frm.fields_dict.custom_project_budget_used ? "custom_project_budget_used" : 
                                    (frm.fields_dict.project_budget_used ? "project_budget_used" : null);
                                    
                    if (fieldname) {
                        if (frm.doc.docstatus === 0) {
                            // Draft - can safely set value
                            frm.set_value(fieldname, r.message);
                        } else {
                            // Submitted - update memory and refresh without making it dirty
                            frm.doc[fieldname] = r.message;
                            frm.refresh_field(fieldname);
                        }
                    }
                }
            }
        });
    } else {
        let fieldname = frm.fields_dict.custom_project_budget_used ? "custom_project_budget_used" : 
                        (frm.fields_dict.project_budget_used ? "project_budget_used" : null);
        if (fieldname && frm.doc[fieldname] !== 0) {
            if (frm.doc.docstatus === 0) {
                frm.set_value(fieldname, 0);
            } else {
                frm.doc[fieldname] = 0;
                frm.refresh_field(fieldname);
            }
        }
    }
}
