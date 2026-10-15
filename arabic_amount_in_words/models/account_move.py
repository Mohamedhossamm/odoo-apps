from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    amount_total_words_ar = fields.Char(
        string="Amount total in Arabic words",
        compute="_compute_amount_total_words_ar",
    )

    @api.depends("amount_total", "currency_id", "company_id.arabic_amount_words_wrap")
    def _compute_amount_total_words_ar(self):
        for move in self:
            move.amount_total_words_ar = move.currency_id.amount_to_arabic_text(
                move.amount_total, company=move.company_id
            )
