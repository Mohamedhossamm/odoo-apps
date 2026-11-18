import logging
import re

from markupsafe import Markup, escape

from odoo import Command, _, fields, models
from odoo.exceptions import UserError

from .ai_bill_extractor import SUPPORTED_MIMETYPES

_logger = logging.getLogger(__name__)


def _clean_vat(vat):
    return re.sub(r"[^0-9A-Za-z]", "", vat or "")


def _to_date(value):
    if not value:
        return False
    try:
        return fields.Date.to_date(value)
    except (TypeError, ValueError):
        return False


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_mh_ai_read_bill(self):
        if len(self) == 1:
            self._mh_ai_read_bill()
            return True
        done, failed = 0, 0
        for move in self:
            try:
                with self.env.cr.savepoint():
                    move._mh_ai_read_bill()
                done += 1
            except UserError as e:
                failed += 1
                move.message_post(body=_("AI could not read this bill: %s", e.args[0]))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Read with AI"),
                "message": _("%(done)s bills filled, %(failed)s skipped (see the reason in each bill's chatter).",
                             done=done, failed=failed),
                "type": "success" if not failed else "warning",
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }

    def _mh_ai_get_bill_attachment(self):
        self.ensure_one()
        main = self.message_main_attachment_id
        if main and main.mimetype in SUPPORTED_MIMETYPES:
            return main
        return self.env["ir.attachment"].search([
            ("res_model", "=", "account.move"),
            ("res_id", "=", self.id),
            ("mimetype", "in", list(SUPPORTED_MIMETYPES)),
        ], order="id desc", limit=1)

    def _mh_ai_read_bill(self):
        self.ensure_one()
        if not self.is_purchase_document(include_receipts=True):
            raise UserError(_("AI reading works on vendor bills and refunds only."))
        if self.state != "draft":
            raise UserError(_("Reset the bill %s to draft before reading it with AI.", self.display_name))
        if self.invoice_line_ids:
            raise UserError(_("The bill %s already has lines. Delete them first if you want AI to read the file.",
                              self.display_name))
        attachment = self._mh_ai_get_bill_attachment()
        if not attachment:
            raise UserError(_("Attach the bill PDF or photo first, then click Read with AI."))
        data = self.env["mh.ai.bill.extractor"].extract(attachment)
        self._mh_ai_apply_bill_data(data)
        return data

    # ------------------------------------------------------------------
    # Fill the bill
    # ------------------------------------------------------------------

    def _mh_ai_find_partner(self, name, vat):
        Partner = self.env["res.partner"].with_context(active_test=False)
        company_domain = ["|", ("company_id", "=", False), ("company_id", "=", self.company_id.id)]
        vat = _clean_vat(vat)
        if vat:
            partner = Partner.search(company_domain + [("vat", "ilike", vat)], limit=1)
            if partner:
                return partner, False
        name = (name or "").strip()
        if name:
            partner = Partner.search(company_domain + [("name", "=ilike", name)], limit=1)
            if partner:
                return partner, False
            partner = Partner.create({"name": name, "vat": vat or False, "is_company": True,
                                      "company_id": self.company_id.id})
            return partner, True
        return Partner, False

    def _mh_ai_find_product(self, code, description):
        Product = self.env["product.product"]
        company_domain = ["|", ("company_id", "=", False), ("company_id", "=", self.company_id.id)]
        code = (code or "").strip()
        if code:
            product = Product.search(company_domain + ["|", ("default_code", "=", code), ("barcode", "=", code)],
                                     limit=1)
            if product:
                return product
        description = (description or "").strip()
        if description:
            return Product.search(company_domain + [("name", "=ilike", description)], limit=1)
        return Product

    def _mh_ai_find_tax(self, percent):
        if not percent:
            return self.env["account.tax"]
        return self.env["account.tax"].search([
            ("company_id", "parent_of", self.company_id.id),
            ("type_tax_use", "=", "purchase"),
            ("amount_type", "=", "percent"),
            ("price_include", "=", False),
            ("amount", "=", float(percent)),
        ], limit=1)

    def _mh_ai_apply_bill_data(self, data):
        self.ensure_one()
        notes = []
        vals = {}

        partner, created = self._mh_ai_find_partner(data.get("vendor_name"), data.get("vendor_vat"))
        if partner:
            vals["partner_id"] = partner.id
            if created:
                notes.append(_("New vendor created: %s", partner.name))
        if data.get("invoice_number"):
            vals["ref"] = data["invoice_number"]
        if _to_date(data.get("invoice_date")):
            vals["invoice_date"] = _to_date(data["invoice_date"])
        currency_code = (data.get("currency") or "").strip().upper()
        if currency_code:
            currency = self.env["res.currency"].with_context(active_test=False).search(
                [("name", "=", currency_code)], limit=1)
            if currency and currency.active:
                vals["currency_id"] = currency.id
            elif currency_code != self.currency_id.name:
                notes.append(_("The bill is in %s, which is not active in Odoo.", currency_code))
        if vals:
            self.write(vals)
        due_date = _to_date(data.get("due_date"))
        if due_date and not self.invoice_payment_term_id:
            self.invoice_date_due = due_date

        include_tax = bool(data.get("prices_include_tax"))
        line_cmds = []
        for line in data.get("lines") or []:
            description = (line.get("description") or "").strip() or _("Bill line")
            tax_percent = float(line.get("tax_percent") or 0.0)
            price = float(line.get("unit_price") or 0.0)
            if include_tax and tax_percent:
                price = price / (1 + tax_percent / 100.0)
            tax = self._mh_ai_find_tax(tax_percent)
            if tax_percent and not tax:
                notes.append(_("No purchase tax of %s%% found for line: %s", tax_percent, description))
            product = self._mh_ai_find_product(line.get("product_code"), description)
            line_vals = {
                "name": description,
                "quantity": float(line.get("quantity") or 1.0),
                "price_unit": price,
                "discount": float(line.get("discount_percent") or 0.0),
                "tax_ids": [Command.set(tax.ids)],
            }
            if product:
                line_vals["product_id"] = product.id
            line_cmds.append(Command.create(line_vals))
        if line_cmds:
            self.write({"invoice_line_ids": line_cmds})
            # The product onchange sets its own name and taxes; keep what the bill says.
            for line, cmd in zip(self.invoice_line_ids.sorted("sequence"), line_cmds):
                values = cmd[2]
                line.write({"name": values["name"], "price_unit": values["price_unit"],
                            "tax_ids": values["tax_ids"]})

        total = data.get("total")
        if total is not None and abs(self.amount_total - float(total)) > 0.05:
            notes.append(_("Check the amounts: the bill total is %(bill)s but Odoo computed %(odoo)s.",
                           bill=total, odoo=self.amount_total))

        body = escape(_("Bill filled by AI. Please review it before you confirm."))
        if notes:
            body += Markup("<ul>%s</ul>") % Markup("").join(Markup("<li>%s</li>") % escape(n) for n in notes)
        self.message_post(body=body)
        return True
