# Copyright (c) 2022, Dynamic and contributors
# For license information, please see license.txt

from dynamic.hardware_installations.doctype.installation_request.installation_request import update_installation_request_qty
from erpnext import get_default_company
from erpnext.stock.get_item_details import get_valuation_rate
import frappe
from frappe.model.document import Document
import datetime
from frappe import _
from frappe.utils.data import flt


class CarInstallation(Document):
    # def before_save(self):
    # 	self.create_stock_entry()

    def on_submit(self):
        if self.installation_order:
            self.update_installation_order()
            self.create_delivery_note()
        self.create_stock_entry()

    def on_cancell(self):
        if self.installation_order:
            self.update_installation_order(cancel=1)

    def validate(self):
        self.validate_qty()

    def validate_qty(self):
        if self.installation_order:
            installation_order = frappe.get_doc(
                "Installation Order", self.installation_order)
            total_order_qty = frappe.db.sql(f"""
			select COUNT(name) as total_cars  from `tabCar Installation`
			where docstatus = 1 and name <> '{self.name}' and installation_order = '{self.installation_order}'
				""", as_dict=1) or 0
            if total_order_qty:
                total_order_qty = total_order_qty[0].total_cars or 0
            else:
                total_order_qty = 0

            if (installation_order.total_cars-total_order_qty) < 1:
                frappe.throw(_("""Order {} has {}/{} car is Already Requested""").format(
                    self.installation_order, total_order_qty, flt(
                        installation_order.total_cars)
                ))

        # self.pending_cars = self.total_cars - self.completed_cars

    def update_installation_order(self, cancel=0):
        installation_order = frappe.get_doc(
            "Installation Order", self.installation_order)
        factor = -1 if cancel else 1
        installation_order.completed_cars += factor * 1
        installation_order.validate()
        installation_order.save()
        if installation_order.installation_request:
            update_installation_request_qty(
                installation_order.installation_request,self.sales_order)

    def create_stock_entry(self):
        if self.gps_type == 'Internal' or self.accessories_type == 'Internal':
            stock_entry_doc = frappe.new_doc('Stock Entry')
            stock_entry_doc.set("items", [])
            stock_entry_doc.stock_entry_type = "Material Issue"
            if self.accessories_type == 'Internal':
                # for Accesoreies
                # git_bin_qty = frappe.db.get_list('Bin',
                # 				filters={
                # 					'item_code': self.accessories
                # 				},
                # 				fields=['actual_qty', 'reserved_qty','valuation_rate'],
                # 			)
                # if(git_bin_qty):
                # 	if(git_bin_qty[0].actual_qty - git_bin_qty[0].reserved_qty > 0):
                stock_entry_doc.append("items", {
                    's_warehouse': self.accessories_warehouse,
                    'item_code': self.accessories,
                    'qty': self.accessories_qty,
                    'basic_rate': get_valuation_rate(self.accessories, get_default_company(), warehouse=self.accessories_warehouse)
                })
            if self.gps_type == 'Internal':
                # for Accesoreies
                # git_bin_qty = frappe.db.get_list('Bin',
                # 				filters={
                # 					'item_code': self.gps_item_code
                # 				},
                # 				fields=['actual_qty', 'reserved_qty','valuation_rate'],
                # 			)
                # if(git_bin_qty):
                # 	if(git_bin_qty[0].actual_qty - git_bin_qty[0].reserved_qty > 0):
                stock_entry_doc.append("items", {
                    's_warehouse': self.gps_warehouse,
                    'item_code': self.gps_item_code,
                    'qty': 1,
                    'basic_rate': get_valuation_rate(self.gps_item_code, get_default_company(), warehouse=self.gps_warehouse),
                    'serial_no': self.gps_series
                })
            stock_entry_doc.installation_request = self.installation_request
            stock_entry_doc.installation_order = self.installation_order
            stock_entry_doc.car_installation = self.name
            stock_entry_doc.submit()

    def create_delivery_note(self):
        delivery_note_doc = frappe.new_doc('Delivery Note')
        delivery_note_doc.customer = self.customer
        sales_order_name = frappe.db.get_value('Installation Request',self.installation_request,"sales_order")
        sales_order_doc = frappe.get_doc('Sales order',sales_order_name)
        delivery_note_doc.set_warehouse = sales_order_doc.set_warehouse
        pass

    @frappe.whitelist()
    def get_car_data(self):
        if self.car:
            car_doc = frappe.get_doc("Car", self.car)
            # car_model = frappe
            self.db_set("car_type", car_doc.get('car_type'))
            self.db_set("car_model", car_doc.get('car_model'))
            self.db_set("car_brand", car_doc.get('car_brand'))

    @frappe.whitelist()
    def get_cst_delgate(self):
        if self.installation_order:
            install_ord = frappe.get_doc(
                "Installation Order", self.installation_order)
            self.db_set("customer", install_ord.get('customer'))
            self.db_set("customer_name", install_ord.get('customer_name'))
            self.db_set("customer_phone_number",
                        install_ord.get('customer_phone_number'))
            self.db_set("delegate", install_ord.get('delegate'))
            self.db_set("delegate_name", install_ord.get('delegate_name'))
            self.db_set("delegate_phone_number",
                        install_ord.get('delegate_phone_number'))
            if install_ord.installation_team_detail:
                self.team = install_ord.team
                self.installation_team_detail = []
                for row in install_ord.installation_team_detail:
                    self.append('installation_team_detail', {
                        'employee': row.employee,
                        'employee_name': row.employee_name,
                    })

    @frappe.whitelist()
    def get_serial_gps(self):
        if self.gps_type == "Internal":
            serial_doc = frappe.get_doc("Serial No", self.gps_serial_number)
            # self.db_set("device_name",serial_doc.get('item_code'))
            self.db_set("gps_serial_number2", serial_doc.get('serial2'))
            self.db_set("gps_series", serial_doc.get('name'))

    @frappe.whitelist()
    def get_team(self):
        if self.team:
            team_doc = frappe.get_doc('Installation Team', self.team)
            # self.team = []
            for row in team_doc.employees:
                self.append('installation_team_detail', {
                    "employee": row.employee,
                    "employee_name": row.employee_name
                })
