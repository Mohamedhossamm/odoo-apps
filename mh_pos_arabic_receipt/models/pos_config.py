from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    ar_receipt_labels = fields.Boolean(
        string="Arabic receipt labels",
        default=True,
        help="Add the Arabic word next to Total, Change, Discounts and Rounding.",
    )
    ar_receipt_product_names = fields.Boolean(
        string="Arabic product names on receipts",
        default=True,
        help="Print each product's Arabic translation under its name.",
    )
    ar_receipt_amount_words = fields.Boolean(
        string="Total in Arabic words",
        default=True,
        help="Print the total as words, for example: فقط مائة وخمسون جنيهاً لا غير.",
    )
    ar_receipt_customer = fields.Boolean(
        string="Customer phone on receipts",
        default=True,
        help="Print the customer's phone under the name when the order has a customer.",
    )
