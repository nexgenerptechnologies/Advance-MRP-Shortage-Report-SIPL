frappe.ui.form.on("Purchase Order", {
    onload: function(frm) {
        if (frm.doc.docstatus === 1) {
            frm.__true_db_values = {};
            // Fetch TRUE DB values directly per field to avoid missing column errors on custom fields
            let fields_to_check = ['project', 'project_code', 'custom_project_code', 'custom_project'];
            fields_to_check.forEach(f => {
                if (frm.fields_dict[f]) {
                    frappe.db.get_value('Purchase Order', frm.doc.name, f).then(r => {
                        if (r && r.message) {
                            frm.__true_db_values[f] = r.message[f];
                        }
                    });
                }
            });
        }
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
        // Forcefully revert fields to their true DB value right before sending to server
        // This prevents the "Not allowed to change Project Code" validation error.
        if (frm.doc.docstatus === 1 && frm.__true_db_values) {
            let fields_to_check = ['project', 'project_code', 'custom_project_code', 'custom_project'];
            fields_to_check.forEach(f => {
                if (frm.fields_dict[f] && frm.__true_db_values.hasOwnProperty(f)) {
                    frm.doc[f] = frm.__true_db_values[f];
                }
            });
        }
    }
});

function update_project_budget(frm) {
    let project = null;
    
    // 1. ALWAYS prefer project from items first, because the header might have a display name instead of the code
    if (frm.doc.items && frm.doc.items.length > 0) {
        for (let i = 0; i < frm.doc.items.length; i++) {
            if (frm.doc.items[i].project) {
                project = frm.doc.items[i].project;
                break;
            }
        }
    }
    
    // 2. Fallback to header project or project_code
    if (!project) {
        project = frm.doc.project_code || frm.doc.project;
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
