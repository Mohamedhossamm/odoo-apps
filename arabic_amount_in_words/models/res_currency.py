from odoo import models, tools

from ..tools.tafqeet import CURRENCIES, DEFAULT_PREFIX, DEFAULT_SUFFIX, amount_to_arabic


class ResCurrency(models.Model):
    _inherit = "res.currency"

    def amount_to_arabic_text(self, amount, company=None):
        """The amount in Arabic words, or False when this currency has no Arabic wording."""
        self.ensure_one()
        if self.name not in CURRENCIES or amount < 0:
            return False
        company = company or self.env.company
        wrap = company.arabic_amount_words_wrap
        return amount_to_arabic(
            self.round(amount),
            self.name,
            prefix=DEFAULT_PREFIX if wrap else "",
            suffix=DEFAULT_SUFFIX if wrap else "",
        )

    def amount_to_text(self, amount):
        # Odoo's own Arabic text comes from num2words, which gets the grammar wrong
        # (مليونا, خمسون قرش) and knows nothing about the counted currency noun.
        if tools.get_lang(self.env).code.startswith("ar"):
            text = self.amount_to_arabic_text(amount)
            if text:
                return text
        return super().amount_to_text(amount)
