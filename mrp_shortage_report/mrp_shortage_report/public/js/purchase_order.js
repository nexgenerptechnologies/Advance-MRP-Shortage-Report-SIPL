frappe.ui.form.on("Purchase Order", {
    onload: function(frm) {
        // Save the true DB value of Project Code before any rogue scripts modify it
        frm.__true_project = frm.doc.project;
    },
    refresh: function(frm) {
        update_project_budget(frm);
        
        // Neutralize rogue scripts visually
        if (frm.doc.docstatus === 1) {
            setTimeout(() => {
                if (frm.is_dirty()) {
                    frm.doc.__unsaved = 0;
                    frm.refresh_header();
                }
            }, 1000);
        }
    },
    project: function(frm) {
        update_project_budget(frm);
    },
    before_save: function(frm) {
        // Forcefully revert Project Code to its true DB value right before sending to server
        // This prevents the "Not allowed to change Project Code" validation error.
        if (frm.doc.docstatus === 1 && frm.__true_project !== undefined) {
            frm.doc.project = frm.__true_project;
        }
    }
});

function update_project_budget(frm) {
    let project = frm.doc.project;
    
    if (!project && frm.doc.items && frm.doc.items.length > 0) {
        for (let i = 0; i < frm.doc.items.length; i++) {
            if (frm.doc.items[i].project) {
                project = frm.doc.items[i].project;
                break;
            }
        }
    }
    
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
                    if (frm.doc.docstatus === 0) {
                        // Draft - can safely set value
                        frm.set_value(fieldname, r.message);
                    } else {
                        // Submitted - UNBREAKABLE DOM INJECTION
                        frm.__fetched_budget = r.message;
                        
                        // Failsafe wipe
                        if (frm.doc[fieldname] !== 0) {
                            frm.doc[fieldname] = 0;
                        }
                        
                        if (!frm.__budget_interval) {
                            frm.__budget_interval = setInterval(() => {
                                if (frm.__fetched_budget !== undefined) {
                                    let field = frm.fields_dict[fieldname];
                                    if (field) {
                                        let formatted_val = format_currency(frm.__fetched_budget, frm.doc.currency);
                                        if (field.$wrapper && field.$wrapper.find('.control-value').length > 0) {
                                            if (field.$wrapper.find('.control-value').text() !== formatted_val) {
                                                field.$wrapper.find('.control-value').text(formatted_val);
                                            }
                                        } else if (field.$input) {
                                            if (field.$input.val() !== formatted_val) {
                                                field.$input.val(formatted_val);
                                            }
                                        }
                                    }
                                }
                            }, 500); // Enforce visually every 500ms
                        }
                    }
                }
            }
        });
    } else if (fieldname) {
        if (frm.doc[fieldname] !== 0) {
            if (frm.doc.docstatus === 0) {
                frm.set_value(fieldname, 0);
            } else {
                frm.__fetched_budget = 0;
            }
        }
    }
}
