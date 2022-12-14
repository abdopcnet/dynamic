

import frappe
from frappe import _
from frappe.utils import getdate
from datetime import datetime
from frappe.utils.background_jobs import  enqueue
from frappe.model.mapper import get_mapped_doc
from erpnext.selling.doctype.quotation.quotation import _make_customer
from frappe.utils import flt, getdate, nowdate
from erpnext.selling.doctype.sales_order.sales_order import make_purchase_order, is_product_bundle, set_delivery_date
from six import string_types
import json


DOMAINS = frappe.get_active_domains()

@frappe.whitelist()
def opportunity_notifiy(self, *args, **kwargs):
    if "IFI" in DOMAINS:
        get_alert_dict(self)
        #reciever
        email_quotation(self, *args, **kwargs)
        
@frappe.whitelist()
def daily_opportunity_notify(self, *args, **kwargs ):
    # date_now =getdate()
    today = datetime.now().strftime('%Y-%m-%d')
    sql = f"""
        select name,contact_by,customer_name,contact_date,'Opportunity' as doctype from tabOpportunity to2 
		where CAST(contact_date AS DATE) ='{today}'
    """
    data = frappe.db.sql(sql,as_dict=1)
    for opprt in data:
        get_alert_dict(opprt)          

@frappe.whitelist()
def get_alert_dict(self):
    owner_name = self.contact_by
    customer_name = self.customer_name
    contact_date = self.contact_date
    notif_doc = frappe.new_doc('Notification Log')
    notif_doc.subject = f"{owner_name} Contact to {customer_name} at {contact_date}"
    notif_doc.for_user = owner_name
    notif_doc.type = "Mention"
    notif_doc.document_type = self.doctype
    notif_doc.document_name = self.name
    notif_doc.from_user = frappe.session.user
    notif_doc.insert(ignore_permissions=True)




@frappe.whitelist()
def email_quotation(self,*args, **kwargs): 
		receiver = frappe.db.get_value("User", self.contact_by, "email")
		if receiver:
			email_args = {
				"recipients": [receiver],
				"message": _("Quotation Appointement"),
				"subject": 'Quotation Appointement At Date'.format(self.contact_date),
                # "message": self.get_message(),
				# "attachments": [frappe.attach_print(self.doctype, self.name, file_name=self.name)],
				"reference_doctype": self.doctype,
				"reference_name": self.name
				}
			enqueue(method=frappe.sendmail, queue="short", timeout=300,now=True, is_async=True,**email_args)
		else:
			frappe.msgprint(_("{0}: Next Contatct By User Has No Mail, hence email not sent").format(self.contact_by))


@frappe.whitelist()
def email_supplier_invoice(self,*args, **kwargs): 
		receiver = frappe.db.get_value("Supplier", self.supplier, "email_id")
		if receiver:
			email_args = {
				"recipients": [receiver],
				"message": _("Please GET Notify "),
				"subject": 'Purchase Receipt - IN'.format(self.posting_date),
				# "attachments": [frappe.attach_print(self.doctype, self.name, file_name=self.name)],
				"reference_doctype": self.doctype,
				"reference_name": self.name
				}
			enqueue(method=frappe.sendmail, queue="short", timeout=300,now=True, is_async=True,**email_args)
		else:
			frappe.msgprint(_("{0}: Supplier ha no mail, hence email not sent").format(self.supplier))

@frappe.whitelist()
def create_furniture_installation_order(source_name, target_doc=None):
    doclist = get_mapped_doc("Sales Order", source_name, {
        "Sales Order": {
            "doctype": "Installations Furniture",
            "field_map": {
                "name": "sales_order",
                "customer": "customer"
            },
            "validation": {
                "docstatus": ["=", 1]
            }
        },
        "Sales Order Item": {
            "doctype": "Installation Furniture Item",
            "field_map": {
                "name":"ref_name",
                "item_code": "item_code",
                "item_name": "item_name",
                "qty": "qty",
                "rate": "rate",
                "amount": "amount",
                "delivery_date":"delivery_date",
            }
        }
    }, target_doc)
    
    return doclist
    

@frappe.whitelist()
def make_sales_order(source_name, target_doc=None):
	quotation = frappe.db.get_value(
		"Quotation", source_name, ["transaction_date", "valid_till"], as_dict=1
	)
	if quotation.valid_till and (
		quotation.valid_till < quotation.transaction_date or quotation.valid_till < getdate(nowdate())
	):
		frappe.throw(_("Validity period of this quotation has ended."))
	return _make_sales_order(source_name, target_doc)


def _make_sales_order(source_name, target_doc=None, ignore_permissions=False):
	customer = _make_customer(source_name, ignore_permissions)

	def set_missing_values(source, target):
		if customer:
			target.customer = customer.name
			target.customer_name = customer.customer_name
		if source.referral_sales_partner:
			target.sales_partner = source.referral_sales_partner
			target.commission_rate = frappe.get_value(
				"Sales Partner", source.referral_sales_partner, "commission_rate"
			)
		target.flags.ignore_permissions = ignore_permissions
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(obj, target, source_parent):
		target.stock_qty = flt(obj.qty) * flt(obj.conversion_factor)

		if obj.against_blanket_order:
			target.against_blanket_order = obj.against_blanket_order
			target.blanket_order = obj.blanket_order
			target.blanket_order_rate = obj.blanket_order_rate

	doclist = get_mapped_doc(
		"Quotation",
		source_name,
		{
			"Quotation": {
                "doctype": "Sales Order",
                "field_map": {
                    "crean": "crean",
                    "crean_amount": "crean_amount",
                },
                "validation": 
                {"docstatus": ["=", 1]}
                },
			"Quotation Item": {
				"doctype": "Sales Order Item",
				"field_map": {"parent": "prevdoc_docname"},
				"postprocess": update_item,
			},
			"Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "add_if_empty": True},
			"Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
			"Payment Schedule": {"doctype": "Payment Schedule", "add_if_empty": True},
		},
		target_doc,
		set_missing_values,
		ignore_permissions=ignore_permissions,
	)

	# postprocess: fetch shipping address, set missing values
	doclist.set_onload("ignore_price_list", True)

	return doclist


@frappe.whitelist()
def override_make_purchase_order(source_name, selected_items=None, target_doc=None):
	if "IFI" in DOMAINS:
		print('\n\n\n\n/////*****from scripy****')
		if not selected_items:
			return

		if isinstance(selected_items, string_types):
			selected_items = json.loads(selected_items)

		items_to_map = [
			item.get("item_code")
			for item in selected_items
			if item.get("item_code") and item.get("item_code")
		]
		items_to_map = list(set(items_to_map))

		def set_missing_values(source, target):
			target.supplier = ""
			target.apply_discount_on = ""
			target.additional_discount_percentage = 0.0
			target.discount_amount = 0.0
			target.inter_company_order_reference = ""
			target.customer = ""
			target.customer_name = ""
			target.run_method("set_missing_values")
			target.run_method("calculate_taxes_and_totals")

		def update_item(source, target, source_parent):
			target.schedule_date = source.delivery_date
			target.qty = flt(source.qty) - (flt(source.ordered_qty) / flt(source.conversion_factor))
			target.stock_qty = flt(source.stock_qty) - flt(source.ordered_qty)
			target.project = source_parent.project

		def update_item_for_packed_item(source, target, source_parent):
			target.qty = flt(source.qty) - flt(source.ordered_qty)

		# po = frappe.get_list("Purchase Order", filters={"sales_order":source_name, "supplier":supplier, "docstatus": ("<", "2")})
		doc = get_mapped_doc(
			"Sales Order",
			source_name,
			{
				"Sales Order": {
					"doctype": "Purchase Order",
					"field_map": {
						"customer":"customer_so",
						
						},
					"field_no_map": [
						"address_display",
						"shipping_rule",
						"contact_display",
						"contact_mobile",
						"contact_email",
						"contact_person",
						"taxes_and_charges",
						"shipping_address",
						"terms",
					],
					"validation": {"docstatus": ["=", 1]},
				},
				"Sales Order Item": {
					"doctype": "Purchase Order Item",
					"field_map": [
						["name", "sales_order_item"],
						["parent", "sales_order"],
						["stock_uom", "stock_uom"],
						["uom", "uom"],
						["conversion_factor", "conversion_factor"],
						["delivery_date", "schedule_date"],
					],
					"field_no_map": [
						"rate",
						"price_list_rate",
						"item_tax_template",
						"discount_percentage",
						"discount_amount",
						"supplier",
						"pricing_rules",
					],
					"postprocess": update_item,
					"condition": lambda doc: doc.ordered_qty < doc.stock_qty
					and doc.item_code in items_to_map
					and not is_product_bundle(doc.item_code),
				},
				"Packed Item": {
					"doctype": "Purchase Order Item",
					"field_map": [
						["name", "sales_order_packed_item"],
						["parent", "sales_order"],
						["uom", "uom"],
						["conversion_factor", "conversion_factor"],
						["parent_item", "product_bundle"],
						["rate", "rate"],
					],
					"field_no_map": [
						"price_list_rate",
						"item_tax_template",
						"discount_percentage",
						"discount_amount",
						"supplier",
						"pricing_rules",
					],
					"postprocess": update_item_for_packed_item,
					"condition": lambda doc: doc.parent_item in items_to_map,
				},
			},
			target_doc,
			set_missing_values,
		)

		set_delivery_date(doc.items, source_name)

		return doc
	make_purchase_order(source_name, selected_items=None, target_doc=None)
	# print('\n\n\n\n/////*********')
	# print(source_name)