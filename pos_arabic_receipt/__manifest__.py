{
    "name": "POS Arabic & English Receipt",
    "summary": "Bilingual Point of Sale receipts: Arabic product names, Arabic labels, "
    "the total in Arabic words and the customer's name",
    "version": "19.0.1.0.0",
    "category": "Sales/Point of Sale",
    "author": "Mohamed Hossam",
    "license": "OPL-1",
    "depends": ["point_of_sale"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_arabic_receipt/static/src/app/**/*",
        ],
    },
    "images": ["static/description/banner.png"],
    "installable": True,
}
