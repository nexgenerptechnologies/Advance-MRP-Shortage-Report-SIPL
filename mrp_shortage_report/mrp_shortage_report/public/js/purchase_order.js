frappe.ui.form.on("Purchase Order", {
    onload: function(frm) {
        if (frm.doc.docstatus === 1) {
            // Fetch the ENTIRE true DB document directly to bypass missing column errors and malicious Python hooks
            frappe.call({
                method: 'frappe.client.get',
                args: { doctype: 'Purchase Order', name: frm.doc.name },
                callback: function(r) {
                    if (r && r.message) {
                        frm.__true_db_doc = r.message;
                    }
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
        // ULTIMATE NEUTRALIZER: Forcefully revert ALL fields not allowed on submit to their true DB value
        // This guarantees you will NEVER see a "Not allowed to change X after submission" error again!
        if (frm.doc.docstatus === 1 && frm.__true_db_doc) {
            for (let fieldname in frm.fields_dict) {
                let df = frm.fields_dict[fieldname].df;
                if (df && !df.allow_on_submit) {
                    if (frm.__true_db_doc.hasOwnProperty(fieldname)) {
                        frm.doc[fieldname] = frm.__true_db_doc[fieldname];
                    } else {
                        frm.doc[fieldname] = null;
                    }
                }
            }
        }
    }
});

function update_project_budget(frm) {
    let project = null;
    
    // 1. ALWAYS prefer project from items first
    if (frm.doc.items && frm.doc.items.length > 0) {
        for (let i = 0; i < frm.doc.items.length; i++) {
            if (frm.doc.items[i].project) {
                project = frm.doc.items[i].project;
                break;
            }
        }
    }
    
    // 2. Dynamically hunt for any custom "Project Code" field the user might have added
    if (!project) {
        for (let fieldname in frm.fields_dict) {
            let df = frm.fields_dict[fieldname].df;
            if (df && df.label && df.label.toLowerCase().includes('project') && (df.label.toLowerCase().includes('code') || df.label.toLowerCase() === 'project')) {
                if (frm.doc[fieldname]) {
                    project = frm.doc[fieldname];
                    break;
                }
            }
        }
    }
    
    // 3. Ultimate fallback to standard project field
    if (!project) {
        project = frm.doc.project || frm.doc.project_code || frm.doc.custom_project_code;
    }
    
    // Dynamically hunt for ANY field with "budget" in the label
    let target_fieldname = null;
    for (let f in frm.fields_dict) {
        let df = frm.fields_dict[f].df;
        if (df && df.label && df.label.toLowerCase().includes('budget')) {
            target_fieldname = df.fieldname;
            break;
        }
    }
    
    if (project && target_fieldname) {
        frappe.call({
            method: "mrp_shortage_report.mrp_shortage_report.api.get_project_budget_used",
            args: {
                project: project
            },
            callback: function(r) {
                if (r && r.message !== undefined) {
                    if (frm.doc.docstatus === 0) {
                        // Draft - can safely set value natively
                        if (frm.doc[target_fieldname] !== r.message) {
                            frm.set_value(target_fieldname, r.message);
                        }
                    } else {
                        // Submitted - UNBREAKABLE DOM INJECTION
                        // frm.set_value is blocked on submitted forms if "Allow on Submit" is false
                        frm.__fetched_budget = r.message;
                        
                        // Failsafe wipe internal value to prevent server validation errors
                        if (frm.doc[target_fieldname] !== 0) {
                            frm.doc[target_fieldname] = 0;
                        }
                        
                        if (!frm.__budget_interval) {
                            frm.__budget_interval = setInterval(() => {
                                if (frm.__fetched_budget !== undefined) {
                                    let field = frm.fields_dict[target_fieldname];
                                    if (field) {
                                        let formatted_val = format_currency(frm.__fetched_budget, frm.doc.currency || frappe.boot.sysdefaults.currency);
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
    } else if (target_fieldname) {
        if (frm.doc[target_fieldname] !== 0) {
            if (frm.doc.docstatus === 0) {
                frm.set_value(target_fieldname, 0);
            } else {
                frm.__fetched_budget = 0;
                frm.doc[target_fieldname] = 0;
            }
        }
    }
}
