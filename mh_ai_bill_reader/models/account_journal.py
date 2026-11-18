import logging

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _create_document_from_attachment(self, attachment_ids):
        moves = super()._create_document_from_attachment(attachment_ids)
        auto = self.env["ir.config_parameter"].sudo().get_param("mh_ai_bill_reader.auto_read")
        if not auto:
            return moves
        for move in moves:
            if not move.is_purchase_document(include_receipts=True) or move.invoice_line_ids or move.state != "draft":
                continue
            try:
                with self.env.cr.savepoint():
                    move._mh_ai_read_bill()
            except UserError as e:
                move.message_post(body=_("AI could not read this bill: %s", e.args[0]))
            except Exception:
                _logger.exception("AI bill reader failed on %s", move.display_name)
                move.message_post(body=_("AI could not read this bill. You can try again with Read with AI."))
        return moves
