{
    "name": "POS Order Status Screen with Voice Calling",
    "summary": "Show preparing and ready order numbers on a TV and call ready orders out loud, "
    "in Arabic and English. No kitchen display needed.",
    "version": "19.0.1.0.1",
    "category": "Sales/Point of Sale",
    "author": "Mohamed Hossam",
    "license": "OPL-1",
    "depends": ["point_of_sale"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/order_status_board_templates.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_order_status_board/static/src/pos/**/*",
        ],
    },
    "images": ["static/description/banner.png"],
    "post_init_hook": "_post_init_hook",
    "installable": True,
}
