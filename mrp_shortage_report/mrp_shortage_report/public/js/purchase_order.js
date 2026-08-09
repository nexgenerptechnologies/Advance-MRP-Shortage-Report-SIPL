frappe.ui.form.on("Purchase Order", {
    refresh: function(frm) {
        update_project_budget(frm);
    },
    project: function(frm) {
        update_project_budget(frm);
    }
});

frappe.ui.form.on("Purchase Order Item", {
    project: function(frm, cdt, cdn) {
        update_project_budget(frm);
    }
});

function update_project_budget(frm) {
    let project = frm.doc.project;
    
    // If no project at header, check first item
    if (!project && frm.doc.items && frm.doc.items.length > 0) {
        for (let i = 0; i < frm.doc.items.length; i++) {
            if (frm.doc.items[i].project) {
                project = frm.doc.items[i].project;
                break;
            }
        }
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
                    
                    if (fieldname && frm.doc[fieldname] !== r.message) {
                        frm.set_value(fieldname, r.message);
                    }
                }
            }
        });
    } else {
        let fieldname = frm.fields_dict.custom_project_budget_used ? "custom_project_budget_used" : 
                        (frm.fields_dict.project_budget_used ? "project_budget_used" : null);
                        
        if (fieldname && frm.doc[fieldname] !== 0) {
            frm.set_value(fieldname, 0);
        }
    }
}
