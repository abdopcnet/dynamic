# Copyright (c) 2022, Dynamic and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils.background_jobs import  enqueue
import json

class InstallationsFurniture(Document):
	def validate(self):
		self.concat_for_calendar()

	def before_save(self):
		self.update_so_inst_status()
		self.check_employee_busy()

	def on_trash(self):
		self.update_so_inst_status(delete=True)

	def before_submit(self):
		if self.sales_order:
			sales_order_doc = frappe.get_doc('Sales Order',self.sales_order)
			sales_order_sorted_items = sorted(sales_order_doc.items,key=lambda d:d.name)
			installation_sorted_items = sorted(self.items, key=lambda x: x.ref_name)
			for i in range(len(sales_order_sorted_items)): 
				for j in range(i, len(installation_sorted_items)):
					if sales_order_sorted_items[i].get('name') == installation_sorted_items[j].get('ref_name'):
						if sales_order_sorted_items[i].get('qty') != installation_sorted_items[j].get('qty'):
							frappe.throw(f'Not match row no. {installation_sorted_items[j].get("idx")} with SO no. {sales_order_sorted_items[i].get("idx")} -- item code {installation_sorted_items[j].get("item_code")}')
		self.preprare_notify()
	
	def update_so_inst_status(self,delete=False):
		if delete:
			frappe.db.set_value('Sales Order',self.sales_order,'sales_installation','')
		if not delete :
			frappe.db.set_value('Sales Order',self.sales_order,'sales_installation',self.ref_status)
	

	def concat_for_calendar(self):
		self.description= "ID : %s"%self.name + "\n"
		self.description+= "Team : %s"%self.team + "\n"
		self.description+= "Status : %s"%self.ref_status + "\n"
		
	@frappe.whitelist()
	def change_status(self):
		if(self.ref_status=="Pending"):
			self.db_set('ref_status','Start')
			self.update_so_inst_status()
		elif(self.ref_status=="Start"):
			self.db_set('ref_status','Inprogress')
			self.update_so_inst_status()
		elif(self.ref_status=="Inprogress"):
			self.db_set('ref_status','Completed')
			self.update_so_inst_status()
	
	def preprare_notify(self):
		if self.installation_team_detail:
			for employee in self.installation_team_detail:
				if employee.employee_email:
					get_alert_dict(self,employee)
					email_employee_send(self,employee.employee_email)
				if not employee.employee_email:
					frappe.msgprint(f'Employee - {employee.employee} Will not Get Notification Has No Email')

	@frappe.whitelist()
	def check_employee_busy(self):
		for employee in self.installation_team_detail:
			sql_busy = f'''
				select DISTINCT `titd`.`parent`  from `tabInstallation Team Detail` titd 
				INNER JOIN `tabInstallation Furniture Item` insta
				ON insta.parent=titd.parent
				where `titd`.`parent` <> '{self.name}'
				AND '{self.from_time}' <= insta.to_time
				 AND titd.employee='{employee.employee}'
			'''
			sql_data = frappe.db.sql(sql_busy,as_dict=1)
			# frappe.errprint(f'data-->{sql_data}')  AND insta.parent<>'{self.name}' 
			if len(sql_data):
				frappe.throw(f'Exists in interval for employee {employee.employee} In Installation {sql_data[0].parent}')

	@frappe.whitelist()
	def get_team(self):
		if self.team:
			team_doc = frappe.get_doc('Installation Team', self.team)
			# self.team = []
			for row in team_doc.employees:
				self.append('installation_team_detail', {
					"employee": row.employee,
					"employee_name": row.employee_name,
					"employee_email": row.employee_email,
				})

@frappe.whitelist()
def get_events(start, end, filters=None):
	print("-----------------------------starttttttt",start,end)
	"""Returns events for Gantt / Calendar view rendering.
	frappe
	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	from erpnext.controllers.queries import get_match_cond
	from frappe.desk.calendar import get_event_conditions
	filters = json.loads(filters)
	conditions = get_event_conditions("Installations Furniture", filters)
	events = []
	data = frappe.db.sql("""
		select
			`tabInstallations Furniture`.name as name,
			 `tabInstallations Furniture`.customer_name,
			  `tabInstallations Furniture`.ref_status,
			  concat(name,'-team:',`tabInstallations Furniture`.team )as team,
			  `tabInstallations Furniture`.customer as customer,
			`tabInstallations Furniture`.from_time as start,
			 `tabInstallations Furniture`.to_time as end,
			 description

		from
			`tabInstallations Furniture`
			
			{conditions}
		""".format(conditions=conditions), {
			"start": start,
			"end": end
		}, as_dict=True,
		update={"allDay": 0},)
		
	# for row in data:
	# 	job_card_data = {
    #         "start": row.start,
    #         "planned_end_date": row.end,
    #         "name": row.name,
    #         "subject": row.customer,
    #         "color":'#D3D3D3',
    #     }
	# 	events.append(job_card_data)

	return data

@frappe.whitelist()
def get_alert_dict(self,employee):
	child_row_employee = employee.employee #employee_name
	child_row_employee_email = employee.employee_email #employee_email
	customer_name = self.customer_name
	from_date = self.from_time
	to_date = self.to_time
	notif_doc = frappe.new_doc('Notification Log')
	notif_doc.subject = f"{child_row_employee} has installation {customer_name} between {from_date} and {to_date}"
	notif_doc.for_user = child_row_employee_email
	notif_doc.type = "Mention"
	notif_doc.document_type = self.doctype
	notif_doc.document_name = self.name
	notif_doc.from_user = frappe.session.user
	notif_doc.insert(ignore_permissions=True)

@frappe.whitelist()
def email_employee_send(self,receiver=None): 
		receiver = receiver
		if receiver:
			email_args = {
				"recipients": [receiver],
				"message": _("Installation Notification"),
				"subject": 'Installation Date between Date {} to {}'.format(self.from_time,self.to_time),
                # "message": self.get_message(),
				# "attachments": [frappe.attach_print(self.doctype, self.name, file_name=self.name)],
				"reference_doctype": self.doctype,
				"reference_name": self.name
				}
			enqueue(method=frappe.sendmail, queue="short", timeout=300,now=True, is_async=True,**email_args)
		else:
			frappe.msgprint(_("{0}: Next Employee By User Has No Mail, hence email not sent").format(self.contact_by))




