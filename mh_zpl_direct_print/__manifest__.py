{
    "name": "Direct Print to Zebra Network Printers | ZPL Labels without PrintNode",
    "summary": "Send ZPL labels straight from Odoo to Zebra, Xprinter, TSC and other network label printers "
    "(raw TCP port 9100). No PrintNode subscription, no agent to install. Works with Arabic Product Labels.",
    "description": "Direct printing of ZPL labels to network label printers from Odoo.",
    "version": "19.0.1.0.0",
    "category": "Inventory/Inventory",
    "author": "Mohamed Hossam",
    "license": "OPL-1",
    "price": 29.0,
    "currency": "USD",
    "depends": ["mh_arabic_zpl_labels"],
    "data": [
        "security/ir.model.access.csv",
        "views/zpl_printer_views.xml",
        "views/arabic_label_wizard_views.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
}
