import logging
import math

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _mh_label_quantities(self):
        """{product: number of labels}: one label per unit, in the product's unit of measure."""
        counts = {}
        for move in self.move_ids.filtered(lambda m: m.state != "cancel" and m.product_id.type != "service"):
            qty = move.quantity or (move.product_uom_qty if move.picking_id.state != "done" else 0)
            if move.product_uom and move.product_uom != move.product_id.uom_id:
                qty = move.product_uom._compute_quantity(qty, move.product_id.uom_id, rounding_method="HALF-UP")
            labels = int(math.ceil(qty - 1e-6)) if qty > 0 else 0
            if labels:
                counts[move.product_id] = counts.get(move.product_id, 0) + labels
        return counts

    def action_mh_print_arabic_labels(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Print Arabic Labels"),
            "res_model": "mh.arabic.label.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"active_model": "stock.picking", "active_ids": self.ids},
        }

    def _action_done(self):
        res = super()._action_done()
        for picking in self.filtered(lambda p: p.state == "done" and p.picking_type_id.mh_label_auto_print):
            picking._mh_auto_print_labels()
        return res

    def _mh_auto_print_labels(self):
        self.ensure_one()
        ptype = self.picking_type_id
        if not ptype.mh_label_printer_id:
            self.message_post(body=_("Arabic labels were not printed: choose a label printer on the operation type %s.",
                                     ptype.display_name))
            return
        counts = self._mh_label_quantities()
        if not counts:
            return
        try:
            wizard = self.env["mh.arabic.label.wizard"].create({
                "output": "printer",
                "printer_id": ptype.mh_label_printer_id.id,
                "label_size": ptype.mh_label_size or "50x25",
                "show_price": ptype.mh_label_show_price,
                "line_ids": [(0, 0, {"product_id": p.id, "quantity": q}) for p, q in counts.items()],
            })
            wizard._onchange_label_size()
            ptype.mh_label_printer_id._send(wizard._zpl_document())
        except UserError as e:
            # Never block the validation because of a printer: tell the user in the chatter instead.
            self.message_post(body=_("Arabic labels could not be printed: %s", e.args[0]))
            return
        self.message_post(body=_("%(count)s Arabic labels sent to %(printer)s.",
                                 count=sum(counts.values()), printer=ptype.mh_label_printer_id.name))
