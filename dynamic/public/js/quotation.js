frappe.ui.form.on("Quotation",{
    // onload:function(frm) {
    //     frm.events.refresh(frm)
    // },
    refresh:function(frm){
        frappe.call({
            method: "dynamic.api.get_active_domains",
            callback: function (r) {
              if (r.message && r.message.length) {
                if (r.message.includes("Terra")) {
                    if (frm.doc.docstatus == 1) {
                        if (frm.doc.quotation_to == "Lead"){
                            frappe.db.get_value("Customer", {"lead_name": frm.doc.party_name}, "name", (r) => {
                                if(!r.name){
                                cur_frm.add_custom_button(__('Customer'),function(){
                                    frappe.call({
                                        method:"dynamic.terra.doctype.quotation.quotation.make_customer",
                                        args:{
                                            source_name:frm.doc.name,
                                        },
                                        callback:function(r){
                                            frm.refresh()
                                        }
        
                                    })
                                }
                                , __('Create'));	
                                }						
                            });
                            }
                        cur_frm.add_custom_button(__('Payment Entry'),
                                cur_frm.cscript['Make Payment Entry'], __('Create'));
                       
                    }
                }
                if (r.message.includes("IFI")) {
                    if (frm.doc.docstatus == 1 && frm.doc.status !== "Rejected") {
                        frm.add_custom_button(__('Reject'),()=>{
                            frappe.confirm('Are you sure you want to Reject',
                                () => {
                                    frm.events.reject_quotation(frm)
                                }, () => {
                                    // action to perform if No is selected
                                })
                        },__('Create'))

                    //     frm.add_custom_button(__('Reject2'),()=>{                    
                    //                 frm.events.reject_quotation2(frm)
                               
                    //     },__('Create'))
                    // }};
                   
            }
        }
    })
    },
    reject_quotation(frm){
        frappe.call({
            method:"dynamic.ifi.api.reject_quotation_ifi",
            args:{
                source_name:frm.doc.name, 
            },
            callback:function(r){
                frm.reload_doc()

            }

        })
    },

    reject_quotation2(frm){
        frappe.call({
            method:"dynamic.ifi.api.reject_quotation_ifi",
            args:{
                source_name:frm.doc.name, 
            },
            callback:function(r){
                frm.reload_doc()

            }

        })
    },
})



const QuotationController_Extend = erpnext.selling.QuotationController.extend({
  
	refresh: function(doc, dt, dn) {
		this._super(doc);
        frappe.call({
            method: "dynamic.api.get_active_domains",
            callback: function (r) {
              if (r.message && r.message.length) {
                if (r.message.includes("IFI")) {
                    if(doc.docstatus == 1 && doc.status!=='Lost') {
                        if(!doc.valid_till || frappe.datetime.get_diff(doc.valid_till, frappe.datetime.get_today()) >= 0) {
                            cur_frm.page.remove_inner_button('Sales Order','Create')
                            cur_frm.add_custom_button(__('Sales Order'),
                                cur_frm.cscript['Make Sales Order'], __('Create'));
                        }
                    }
                }
              }
            }
            })
        

	},
})

$.extend(
	cur_frm.cscript,
	new QuotationController_Extend({frm: cur_frm}),
);

cur_frm.cscript['Make Sales Order'] = function() {
	frappe.model.open_mapped_doc({
		method: "dynamic.ifi.api.make_sales_order",
		frm: cur_frm
	})
}

cur_frm.cscript['Make Payment Entry'] = function() {
    frappe.model.open_mapped_doc({
        method:
        "dynamic.terra.api.get_payment_entry_quotation",
        frm: cur_frm,
      });
}
