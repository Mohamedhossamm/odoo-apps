from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    arabic_amount_words_wrap = fields.Boolean(
        related="company_id.arabic_amount_words_wrap",
        readonly=False,
    )
    arabic_amount_words_bilingual = fields.Boolean(
        related="company_id.arabic_amount_words_bilingual",
        readonly=False,
    )
