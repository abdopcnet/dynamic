from __future__ import unicode_literals

data = {
    
    'custom_fields': {
        'Serial No': [
            {
                "fieldname": "serial2",
                "fieldtype": "Data",
                "insert_after": "serial_no",
                "label": "Serial No 2",
                "unique": 1,
                "in_global_search": 1,
                "in_standard_filter": 1,
                "in_preview": 1,
            },
        ],
        'Sales Invoice': [
            {
                "fieldname": "maintenance_template",
                "fieldtype": "Link",
                "options":"Maintenance Template",
                "insert_after": "delivery_note",
                "label": "Maintenance Template",
                "print_hide": 1,
            },
            {
                "fieldname": "maintenance_contract",
                "fieldtype": "Link",
                "options":"Maintenance Contract",
                "insert_after": "maintenance_template",
                "label": "Maintenance Contract",
                "print_hide": 1,
            },
        ],
        'Delivery Note': [
            {
                "fieldname": "maintenance_template",
                "fieldtype": "Link",
                "options":"Maintenance Template",
                "insert_after": "sales_team",
                "label": "Maintenance Template",
                "print_hide": 1,
            },
        ],
        'Stock Entry': [
            {
                "fieldname": "maintenance_template",
                "fieldtype": "Link",
                "options":"Maintenance Template",
                "insert_after": "is_return",
                "label": "Maintenance Template",
                "print_hide": 1,
            },
            {
                "fieldname": "installation_section",
                "fieldtype": "Section Break",
                "insert_after": "apply_putaway_rule",
                "label": "Installation Section",
               
            },
            {
                "fieldname": "installation_request",
                "fieldtype": "Link",
                "options":"Installation Request",
                "insert_after": "installation_section",
                "label": "Installation Request",
                "read_only" : 1
            },
            {
                "fieldname": "install_column_break",
                "fieldtype": "Column Break",
                "insert_after": "installation_request",
                "label": "",
               
            },
            {
                "fieldname": "installation_order",
                "fieldtype": "Link",
                "options":"Installation Order",
                "insert_after": "install_column_break",
                "label": "Installation Order",
                "read_only" : 1
            },
            {
                "fieldname": "car_installation",
                "fieldtype": "Link",
                "options":"Car Installation",
                "insert_after": "installation_order",
                "label": "Car Installation",
                "read_only" : 1
            },
        ],
        'Purchase Receipt Item':[
            {
                "fieldname": "serial2",
                "fieldtype": "Small Text",
                "insert_after": "serial_no",
                "label": "Serial No 2",
                "length": 240,
            },
        ]
    },
    "properties": [

    ],
    "property_setters": [
        {
        "doc_type": "Serial No",
        "doctype_or_field": "DocType",
        "modified_by": "Administrator",
        "name": "Serial No-main-search_fields",
        "property": "search_fields",
        "property_type": "Data",
        "value": "item_code,serial2"
        }
    ],
    'on_setup': 'dynamic.gebco.setup.create_contract_service_item'
    
}
