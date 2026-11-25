from odoo import _, fields, models
from odoo.exceptions import UserError


class MhArabicLabelWizard(models.TransientModel):
    _inherit = "mh.arabic.label.wizard"

    output = fields.Selection(selection_add=[("printer", "Print now on a network printer")],
                              ondelete={"printer": "set default"})
    printer_id = fields.Many2one("mh.zpl.printer", string="Printer",
                                 default=lambda self: self.env["mh.zpl.printer"].search([], limit=1))

    def action_print(self):
        self.ensure_one()
        if self.output != "printer":
            return super().action_print()
        if not self.printer_id:
            raise UserError(_("Choose a printer, or add one in Settings > Technical > Label Printers."))
        data = self._zpl_document()
        self.printer_id._send(data)
        count = len(self._products())
        return {"type": "ir.actions.client", "tag": "display_notification",
                "params": {"title": _("Labels sent"), "type": "success",
                           "message": _("%(count)s labels sent to %(printer)s.", count=count,
                                        printer=self.printer_id.name),
                           "next": {"type": "ir.actions.act_window_close"}}}
