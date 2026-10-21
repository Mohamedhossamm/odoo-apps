{
    "name": "Search in One2many and Many2many Lists",
    "summary": "A search bar like Odoo's search view above every one2many and many2many list in forms: "
    "search all columns or one column, combine filters, Arabic-aware",
    "version": "16.0.1.0.0",
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
