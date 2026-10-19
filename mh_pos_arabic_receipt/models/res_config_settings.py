from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_ar_receipt_labels = fields.Boolean(related="pos_config_id.ar_receipt_labels", readonly=False)
    pos_ar_receipt_product_names = fields.Boolean(related="pos_config_id.ar_receipt_product_names", readonly=False)
    pos_ar_receipt_amount_words = fields.Boolean(related="pos_config_id.ar_receipt_amount_words", readonly=False)
    pos_ar_receipt_customer = fields.Boolean(related="pos_config_id.ar_receipt_customer", readonly=False)
