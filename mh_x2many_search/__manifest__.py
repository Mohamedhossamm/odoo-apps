{
    "name": "One2many & Many2many Search | Search Order Lines, Invoice Lines and Any x2many List",
    "summary": "Search bar like Odoo's search view on every one2many and many2many list: search and filter "
    "sale order lines, purchase lines, invoice lines, stock moves and BoM lines by product, label, quantity "
    "or any column. Combine filters, searches all lines, Arabic-aware.",
    "version": "19.0.1.0.1",
    "category": "Productivity",
    "author": "Mohamed Hossam",
    "license": "OPL-1",
    "price": 25.0,
    "currency": "USD",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "mh_x2many_search/static/src/**/*",
        ],
    },
    "images": ["static/description/banner.png"],
    "installable": True,
}
