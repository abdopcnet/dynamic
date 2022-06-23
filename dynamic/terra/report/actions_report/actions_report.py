# Copyright (c) 2022, Dynamic and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	columns = get_columns()
	return columns, data


def get_data(filters):
	conditions = " where 1=1 "
	if filters.get("from_date"):
		conditions += " and date >= '%s'"%filters.get("from_date")
	if filters.get("to_date"):
		conditions += " and date <= '%s'"%filters.get("to_date")
	if filters.get("type"):
		conditions += " and type = '%s'"%filters.get("type")
	if filters.get("actions"):
		conditions += " and action = '%s'"%filters.get("actions")
	if filters.get("customer_type"):
		conditions += " and customer_type = '%s'"%filters.get("customer_type")
	if filters.get("branch"):
		conditions += " and branch = '%s'"%filters.get("branch")

	sql = f"""
	select * from tabActions 
		{conditions}
	"""

	result = frappe.db.sql(sql,as_dict=1)
	return result

def get_columns():
	columns = [
		{
            "label": _("Type"),
            "fieldname": "type",
            "fieldtype": "Data",
            "width": 150
        },
		{
            "label": _("Action"),
            "fieldname": "action",
            "fieldtype": "Data",
            "width": 150
        },
		{
            "label": _("Description"),
            "fieldname": "description",
            "fieldtype": "Data",
            "width": 150
        },
		{
            "label": _("Customer Type"),
            "fieldname": "customer_type",
            "fieldtype": "Data",
            "width": 150
        },
		{
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Data",
            "width": 150
        },
		{
            "label": _("Branch"),
            "fieldname": "branch",
            "fieldtype": "Data",
            "width": 150
        }
	]
	return columns