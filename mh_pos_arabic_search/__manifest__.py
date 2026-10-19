{
    "name": "POS Arabic Smart Search",
    "summary": "Find products and customers in the Point of Sale however Arabic is typed: "
    "أحمد = احمد, قهوة = قهوه, مستشفى = مستشفي, ٠١٠٠ = 0100, with or without tashkeel",
    "version": "18.0.1.0.0",
    "category": "Sales/Point of Sale",
    "author": "Mohamed Hossam",
    "license": "OPL-1",
    "depends": ["point_of_sale"],
    "assets": {
        "point_of_sale._assets_pos": [
            "mh_pos_arabic_search/static/src/app/**/*",
        ],
    },
    "images": ["static/description/banner.png"],
    "installable": True,
}
