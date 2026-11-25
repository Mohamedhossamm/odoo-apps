from odoo import fields, models

from odoo.addons.mh_arabic_zpl_labels.wizard.arabic_label_wizard import SIZES


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    mh_label_auto_print = fields.Boolean(
        "Print Arabic labels on validation",
        help="When a transfer of this type is validated, its product labels are sent to the label printer.")
    mh_label_printer_id = fields.Many2one("mh.zpl.printer", string="Label Printer")
    mh_label_size = fields.Selection(SIZES, string="Label Size", default="50x25")
    mh_label_show_price = fields.Boolean("Price on Labels", default=True)
