frappe.ui.form.on("Purchase Order", {
    refresh: function(frm) {
        if (frm.doc.docstatus === 0) {
            update_project_budget(frm);
        }
    },
    project: function(frm) {
        if (frm.doc.docstatus === 0) {
            update_project_budget(frm);
        }
    }
});

frappe.ui.form.on("Purchase Order Item", {
    project: function(frm, cdt, cdn) {
        update_project_budget(frm);
    }
});

function update_project_budget(frm) {
    let project = null;
    
    // Always prefer project from items first, as header project might be incorrectly populated
    if (frm.doc.items && frm.doc.items.length > 0) {
        for (let i = 0; i < frm.doc.items.length; i++) {
            if (frm.doc.items[i].project) {
                project = frm.doc.items[i].project;
                break;
            }
        }
    }
    
    // Fallback to header project
    if (!project) {
        project = frm.doc.project;
    }
    
    if (project) {
        frappe.call({
            method: "mrp_shortage_report.mrp_shortage_report.api.get_project_budget_used",
            args: { project: project },
            callback: function(r) {
                if (r.message !== undefined) {
                    let fieldname = null;
                    if (frm.fields_dict.custom_project_budget_used) {
                        fieldname = "custom_project_budget_used";
                    } else if (frm.fields_dict.project_budget_used) {
                        fieldname = "project_budget_used";
                    }
                    
                    if (fieldname) {
                        if (frm.doc.docstatus === 0) {
                            // Draft - can safely set value and make it dirty
                            frm.set_value(fieldname, r.message);
                        } else {
                            // Submitted/Cancelled - just update UI without making form dirty
                            frm.doc[fieldname] = r.message;
                            frm.refresh_field(fieldname);
                        }
                        
                        // Only show alert if the value was updated to something > 0
                        if (r.message > 0) {
                            frappe.show_alert({
                                message: __('Project Budget Used: ' + format_currency(r.message)),
                                indicator: 'green'
                            });
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
