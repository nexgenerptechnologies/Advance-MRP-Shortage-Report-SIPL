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
                if (r.message !== undefined && frm.doc.custom_project_budget_used !== r.message) {
                    frm.set_value("custom_project_budget_used", r.message);
                }
            }
        });
    } else {
        if (frm.doc.custom_project_budget_used !== 0) {
            frm.set_value("custom_project_budget_used", 0);
        }
    }
}
