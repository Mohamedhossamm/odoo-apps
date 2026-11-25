{
    "name": "Arabic Labels from Receipts & Auto Print on Validate | ZPL Stock Labels",
    "summary": "Print Arabic product labels for the quantities of a receipt, delivery or transfer, and print them "
    "automatically on your network label printer when the transfer is validated. For Odoo Community, no IoT box.",
    "description": "Stock labels from transfers and automatic printing on validation for ZPL label printers.",
    "version": "19.0.1.0.0",
    "category": "Inventory/Inventory",
    "author": "Mohamed Hossam",
    "license": "OPL-1",
    "price": 19.0,
    "currency": "USD",
    "depends": ["stock", "mh_zpl_direct_print"],
    "data": [
        "views/stock_picking_type_views.xml",
        "views/stock_picking_views.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
}
