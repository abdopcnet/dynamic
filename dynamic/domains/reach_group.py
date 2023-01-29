
from __future__ import unicode_literals


data = {

    'custom_fields': {
    },
    "properties": [
        {
        "doctype": "Customer",
        "doctype_or_field": "DocField",
        "fieldname": "customer_type",
        "property": "options",
        "property_type": "Text",
        "value": "Cash\nPayments\nPrePaid\nCompany\nIndividual",
        "default_value":"Cash"
        },
        
    ],

  

    'on_setup': 'dynamic.reach_group.setup.setup_reach'
}

