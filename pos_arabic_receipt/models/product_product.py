from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    pos_arabic_name = fields.Char(
        string="Arabic Name for POS Receipts",
        compute="_compute_pos_arabic_name",
        help="The product name's Arabic translation, empty when there is none.",
    )

    @api.model
    def _pos_arabic_lang(self):
        lang = self.env["res.lang"].search([("code", "=like", "ar%"), ("active", "=", True)], limit=1)
        return lang.code

    @api.depends("name")
    def _compute_pos_arabic_name(self):
        lang = self._pos_arabic_lang()
        if not lang:
            self.pos_arabic_name = False
            return
        arabic = {product.id: product.name for product in self.with_context(lang=lang)}
        english = {product.id: product.name for product in self.with_context(lang="en_US")}
        for product in self:
            name = arabic.get(product.id)
            # Without an Arabic translation Odoo returns the English name: print nothing then.
            product.pos_arabic_name = name if name and name != english.get(product.id) else False

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ["pos_arabic_name"]
