from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    arabic_amount_words_wrap = fields.Boolean(
        string="Wrap Arabic amount in words",
        default=True,
        help='Write the Arabic amount as "فقط ... لا غير", as on most Arabic invoices and cheques.',
    )
    arabic_amount_words_bilingual = fields.Boolean(
        string="Arabic amount in words on all invoices",
        help="Also print the amount in Arabic words on invoices printed in another language, "
        "for bilingual invoices.",
    )
