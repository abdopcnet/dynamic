# Copyright (c) 2022, Dynamic and contributors
# For license information, please see license.txt

from tabnanny import check
import frappe
from frappe import _
from frappe.client import attach_file
from frappe.model.document import Document
from frappe.utils.data import flt, get_link_to_form, nowdate




validate_reference_dict = {
	"Supplier" :["Purchase Invoice" , "Purchase Order"] ,
	"Customer" :["Sales Invoice" , "Sales Order"] ,
}

class Cheque(Document):

	def on_submit(self):
		self.create_payment_entries()
	def validate (self):
		self.validate_references()
	def validate_references (self):
		if (self.reference_type and self.party_type) :
			if self.reference_type not in validate_reference_dict.get(self.party_type) or [] :
				frappe.throw(_("Invalid Reference Type {} For Party Type {}").format(self.reference_type,self.party_type))
			if self.party :
				party_name = frappe.db.get_value(self.reference_type,self.reference_name,self.party_type.lower())
				if not party_name or party_name != self.party :
					frappe.throw(_("Invalid {} {} For {} {}").format(self.reference_type,self.reference_name,self.party_type,self.party))
		else :
			self.party_type = ""
			self.party = ""
			self.reference_type = ""
			self.reference_name = ""




	@frappe.whitelist()
	def create_payment_entries(self):
		for row in self.items:
			payment_entry = frappe.new_doc("Payment Entry")
			payment_entry.payment_type = self.payment_type
			payment_entry.posting_date = self.posting_date
			payment_entry.company = self.company
			payment_entry.mode_of_payment = self.mode_of_payment
			payment_entry.party_type = self.party_type
			payment_entry.party = self.party
			payment_entry.cheque = self.name
			payment_entry.cheque_status = self.status
			payment_entry.paid_from = self.account_paid_from
			payment_entry.paid_to = self.account_paid_to
			payment_entry.paid_amount = row.amount
			payment_entry.received_amount = row.amount
			payment_entry.reference_no = row.cheque_no
			payment_entry.reference_date = row.cheque_date
			payment_entry.cheque_type = row.cheque_type
			payment_entry.first_benefit = row.first_benefit
			payment_entry.drawn_bank = row.bank
			payment_entry.person_name = row.person_name
			if self.reference_type :
				ref = payment_entry.append("references")
				ref.reference_doctype =  self.reference_type
				ref.reference_name =  self.reference_name
				ref.allocated_amount = row.amount
			payment_entry.save()
			if row.attachment:
				attachment_name = frappe.db.get_value(
					"File", {"file_url": row.attachment}, 'name')
				if attachment_name:
					attachment = frappe.get_doc("File", attachment_name)
					attached_file = frappe.copy_doc(attachment)
					attached_file.attached_to_doctype = payment_entry.doctype
					attached_file.attached_to_name = payment_entry.name
					attached_file.save()
					# print("attachment.attachment  ===> ", attachment.file_name)
					# attach_file(
					# 	filename=attachment.file_name,
					# 	doctype=payment_entry.doctype,
					# 	docname=payment_entry.name,
					# 	folder=attachment.folder,
					# 	decode_base64=attachment.content,
					# 	is_private=attachment.is_private
					# )

			lnk = get_link_to_form(payment_entry.doctype, payment_entry.name)
			frappe.msgprint(_("{} {} was Created").format(
				payment_entry.doctype, lnk))


@frappe.whitelist()
def make_cheque_endorsement(payment_entry):
    payment_entry = frappe.get_doc("Payment Entry", payment_entry)
    if not payment_entry.drawn_bank_account:
        frappe.throw(_("Please Set Bank Account"))
    if not payment_entry.endorsed_party_type:
        frappe.throw(_("Please Set Endorsed Party Type"))
    if not payment_entry.endorsed_party_name:
        frappe.throw(_("Please Set Endorsed Party Name"))
    if not payment_entry.endorsed_party_account:
        frappe.throw(_("Please Set Endorsed Party Account"))
    je = frappe.new_doc("Journal Entry")
    je.posting_date = payment_entry.posting_date
    je.voucher_type = 'Bank Entry'
    je.company = payment_entry.company
    je.cheque_status = "Endorsed"
    je.cheque = payment_entry.cheque
    je.payment_entry = payment_entry.name
    je.cheque_no = payment_entry.reference_no
    je.cheque_date = payment_entry.reference_date
    #je.remark = f'Journal Entry against Insurance for {self.doctype} : {self.name}'
    # credit
    je.append("accounts", {
        "account": payment_entry.paid_to,
        "credit_in_account_currency": flt(payment_entry.paid_amount),
        "reference_type": payment_entry.doctype,
        "reference_name": payment_entry.name,
    })
    # debit
    je.append("accounts", {
        "account":   payment_entry.endorsed_party_account,
        "debit_in_account_currency": flt(payment_entry.paid_amount),
        "party_type": payment_entry.endorsed_party_type,
        "party": payment_entry.endorsed_party_name
    })

    je.save()
    return je


@frappe.whitelist()
def deposite_cheque_under_collection(payment_entry):
    payment_entry = frappe.get_doc("Payment Entry", payment_entry)
    company = frappe.get_doc("Company", payment_entry.company)
    if not payment_entry.drawn_bank_account:
        frappe.throw(_("Please Set Bank Account"))
    if not payment_entry.drawn_account:
        frappe.throw(_("Bank Account is not Company Account"))
    je = frappe.new_doc("Journal Entry")
    je.posting_date = payment_entry.posting_date
    je.voucher_type = 'Bank Entry'
    je.company = payment_entry.company
    je.cheque = payment_entry.cheque
    je.cheque_status = "Under Collect"
    je.payment_entry = payment_entry.name
    je.cheque_no = payment_entry.reference_no
    je.cheque_date = payment_entry.reference_date
    #je.remark = f'Journal Entry against Insurance for {self.doctype} : {self.name}'

    # credit

    je.append("accounts", {
        "account": payment_entry.paid_to,
        "credit_in_account_currency": flt(payment_entry.paid_amount),
        "reference_type": payment_entry.doctype,
        "reference_name": payment_entry.name,
    })
    # debit
    je.append("accounts", {
        "account":   payment_entry.cheques_receivable_account,
        "debit_in_account_currency": flt(payment_entry.paid_amount),
        "reference_type": payment_entry.doctype,
        "reference_name": payment_entry.name
    })
    if payment_entry.collect_cheque_commission:
        if not company.bank_expenses_account:
            frappe.throw(_("Please Set Bank Expenses Account in Company"))

        je.append("accounts", {
            "account": company.bank_expenses_account,
            "debit_in_account_currency": flt(payment_entry.collect_cheque_commission),
            "reference_type": payment_entry.doctype,
            "reference_name": payment_entry.name,
        })
        # debit
        je.append("accounts", {
            "account":   payment_entry.drawn_account,
            "credit_in_account_currency": flt(payment_entry.collect_cheque_commission),
            "reference_type": payment_entry.doctype,
            "reference_name": payment_entry.name
        })

    je.save()
    return je


@frappe.whitelist()
def collect_cheque_now(payment_entry):
    return collect_cheque_under_collection()
    payment_entry = frappe.get_doc("Payment Entry", payment_entry)
    company = frappe.get_doc("Company", payment_entry.company)
    if not payment_entry.drawn_bank_account:
        frappe.throw(_("Please Set Bank Account"))
    if not payment_entry.drawn_account:
        frappe.throw(_("Bank Account is not Company Account"))
    je = frappe.new_doc("Journal Entry")
    je.posting_date = payment_entry.posting_date
    je.cheque_status = "Collected"
    je.voucher_type = 'Bank Entry'
    je.company = payment_entry.company
    je.cheque = payment_entry.cheque
    je.payment_entry = payment_entry.name
    je.cheque_no = payment_entry.reference_no
    je.cheque_date = payment_entry.reference_date

    je.append("accounts", {
        "account": payment_entry.drawn_account,
        "debit_in_account_currency": flt(payment_entry.paid_amount),

    })
    # debit
    je.append("accounts", {
        "account":   payment_entry.cheques_receivable_account,
        "credit_in_account_currency": flt(payment_entry.paid_amount),
        "reference_type": payment_entry.doctype,
        "reference_name": payment_entry.name
    })
    if payment_entry.reject_cheque_commission:
        if not company.bank_expenses_account:
            frappe.throw(_("Please Set Bank Expenses Account in Company"))

        je.append("accounts", {
            "account": company.bank_expenses_account,
            "debit_in_account_currency": flt(payment_entry.reject_cheque_commission),
            "reference_type": payment_entry.doctype,
            "reference_name": payment_entry.name,
        })
        # debit
        je.append("accounts", {
            "account":   payment_entry.drawn_account,
            "credit_in_account_currency": flt(payment_entry.reject_cheque_commission),
            "reference_type": payment_entry.doctype,
            "reference_name": payment_entry.name
        })

    je.save()
    return je


@frappe.whitelist()
def collect_cheque_under_collection(payment_entry):
    payment_entry = frappe.get_doc("Payment Entry", payment_entry)
    company = frappe.get_doc("Company", payment_entry.company)
    if not payment_entry.drawn_bank_account:
        frappe.throw(_("Please Set Bank Account"))
    if not payment_entry.drawn_account:
        frappe.throw(_("Bank Account is not Company Account"))
    je = frappe.new_doc("Journal Entry")
    je.posting_date = payment_entry.posting_date
    je.cheque_status = "Collected"
    je.voucher_type = 'Bank Entry'
    je.company = payment_entry.company
    je.cheque = payment_entry.cheque
    je.payment_entry = payment_entry.name
    je.cheque_no = payment_entry.reference_no
    je.cheque_date = payment_entry.reference_date

    je.append("accounts", {
        "account": payment_entry.drawn_account,
        "debit_in_account_currency": flt(payment_entry.paid_amount),

    })
    # debit
    je.append("accounts", {
        "account":   payment_entry.cheques_receivable_account,
        "credit_in_account_currency": flt(payment_entry.paid_amount),
        "reference_type": payment_entry.doctype,
        "reference_name": payment_entry.name
    })
    if payment_entry.reject_cheque_commission:
        if not company.bank_expenses_account:
            frappe.throw(_("Please Set Bank Expenses Account in Company"))

        je.append("accounts", {
            "account": company.bank_expenses_account,
            "debit_in_account_currency": flt(payment_entry.reject_cheque_commission),
            "reference_type": payment_entry.doctype,
            "reference_name": payment_entry.name,
        })
        # debit
        je.append("accounts", {
            "account":   payment_entry.drawn_account,
            "credit_in_account_currency": flt(payment_entry.reject_cheque_commission),
            "reference_type": payment_entry.doctype,
            "reference_name": payment_entry.name
        })

    je.save()
    return je


@frappe.whitelist()
def reject_cheque_under_collection(payment_entry):
    payment_entry = frappe.get_doc("Payment Entry", payment_entry)
    company = frappe.get_doc("Company", payment_entry.company)
    if not payment_entry.drawn_bank_account:
        frappe.throw(_("Please Set Bank Account"))
    if not payment_entry.drawn_account:
        frappe.throw(_("Bank Account is not Company Account"))
    if not company.rejected_cheques_bank_account:
        frappe.throw(_("Please Set Rejected Cheques Bank Account in Company"))
    je = frappe.new_doc("Journal Entry")
    je.posting_date = payment_entry.posting_date
    je.cheque_status = "Rejected in Bank"
    je.voucher_type = 'Bank Entry'
    je.company = payment_entry.company
    je.cheque = payment_entry.cheque
    je.payment_entry = payment_entry.name
    je.cheque_no = payment_entry.reference_no
    je.cheque_date = payment_entry.reference_date
    #je.remark = f'Journal Entry against Insurance for {self.doctype} : {self.name}'

    # credit

    je.append("accounts", {
        "account": company.rejected_cheques_bank_account,
        "debit_in_account_currency": flt(payment_entry.paid_amount),
        "reference_type": payment_entry.doctype,
        "reference_name": payment_entry.name,
    })
    # debit
    je.append("accounts", {
        "account":   payment_entry.cheques_receivable_account,
        "credit_in_account_currency": flt(payment_entry.paid_amount),
        "reference_type": payment_entry.doctype,
        "reference_name": payment_entry.name
    })
    if payment_entry.reject_cheque_commission:
        if not company.bank_expenses_account:
            frappe.throw(_("Please Set Bank Expenses Account in Company"))

        je.append("accounts", {
            "account": company.bank_expenses_account,
            "debit_in_account_currency": flt(payment_entry.reject_cheque_commission),
            "reference_type": payment_entry.doctype,
            "reference_name": payment_entry.name,
        })
        # debit
        je.append("accounts", {
            "account":   payment_entry.drawn_account,
            "credit_in_account_currency": flt(payment_entry.reject_cheque_commission),
            "reference_type": payment_entry.doctype,
            "reference_name": payment_entry.name
        })

    je.save()
    return je


cheque_status = [
    "New",
    "Under Collect",
    "Rejected in Bank",
    "Collected",
    "Endorsed"
]


@frappe.whitelist()
def make_cheque_doc(dt, dn):
	ref_doc = frappe.get_doc(dt, dn)
	cheque = frappe.new_doc("Cheque")
	cheque.company = ref_doc.company
	cheque.mode_of_payment = "Cheque"
	cheque.status = "New"
	cheque.posting_date = nowdate()
	cheque.reference_type = dt
	cheque.reference_name = dn
	payment_type = "Pay" if dt in ["Purchase Invoice","Purchase Order"] else "Receive"
	cheque.payment_type = payment_type
	cheque.party_type = "Supplier" if payment_type =="Pay" else "Customer"
	cheque.party = ref_doc.supplier if payment_type =="Pay" else ref_doc.customer
	row = cheque.append('items')
	if hasattr(ref_doc,'outstanding_amount'):
		row.amount = ref_doc.outstanding_amount
	else :
		row.amount = ref_doc.base_rounded_total or  ref_doc.base_grand_total
	return cheque
