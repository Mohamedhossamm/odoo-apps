import base64
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

EXTRACTOR = "odoo.addons.mh_ai_bill_reader.models.ai_bill_extractor.MhAiBillExtractor.extract"

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


@tagged("post_install", "-at_install")
class TestAiBillReader(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tax_14 = cls.env["account.tax"].create({
            "name": "VAT 14% purchase", "amount": 14.0, "amount_type": "percent",
            "type_tax_use": "purchase", "company_id": cls.company_data["company"].id,
        })
        cls.vendor = cls.env["res.partner"].create({"name": "شركة النور للتوريدات", "vat": "123456789"})
        cls.product = cls.env["product.product"].create({"name": "ورق تصوير A4", "default_code": "A4-500"})

    def _bill_with_file(self):
        bill = self.env["account.move"].create({"move_type": "in_invoice"})
        attachment = self.env["ir.attachment"].create({
            "name": "bill.pdf", "datas": base64.b64encode(PDF), "mimetype": "application/pdf",
            "res_model": "account.move", "res_id": bill.id,
        })
        return bill, attachment

    def _data(self, **kw):
        data = {
            "vendor_name": "شركة النور للتوريدات", "vendor_vat": "123-456-789",
            "invoice_number": "INV-2026-77", "invoice_date": "2026-11-10", "due_date": None,
            "currency": None, "prices_include_tax": False,
            "lines": [
                {"description": "ورق تصوير A4", "product_code": "A4-500", "quantity": 10,
                 "unit_price": 200.0, "discount_percent": 0, "tax_percent": 14},
                {"description": "خدمة توصيل", "product_code": None, "quantity": 1,
                 "unit_price": 50.0, "discount_percent": 0, "tax_percent": 0},
            ],
            "untaxed_total": 2050.0, "tax_total": 280.0, "total": 2330.0,
        }
        data.update(kw)
        return data

    def test_fill_bill(self):
        bill, _att = self._bill_with_file()
        with patch(EXTRACTOR, return_value=self._data()):
            bill.action_mh_ai_read_bill()
        self.assertEqual(bill.partner_id, self.vendor, "vendor matched by tax ID with dashes removed")
        self.assertEqual(bill.ref, "INV-2026-77")
        self.assertEqual(str(bill.invoice_date), "2026-11-10")
        self.assertEqual(len(bill.invoice_line_ids), 2)
        paper, delivery = bill.invoice_line_ids.sorted("sequence")
        self.assertEqual(paper.product_id, self.product)
        self.assertEqual(paper.name, "ورق تصوير A4")
        self.assertEqual(paper.tax_ids, self.tax_14)
        self.assertFalse(delivery.product_id)
        self.assertFalse(delivery.tax_ids)
        self.assertAlmostEqual(bill.amount_total, 2330.0)
        self.assertNotIn("Check the amounts", bill.message_ids[0].body)

    def test_prices_include_tax_and_new_vendor(self):
        bill, _att = self._bill_with_file()
        data = self._data(vendor_name="مكتبة جديدة", vendor_vat=None, prices_include_tax=True, total=999.0,
                          lines=[{"description": "حبر طابعة", "product_code": None, "quantity": 1,
                                  "unit_price": 114.0, "discount_percent": 0, "tax_percent": 14}])
        with patch(EXTRACTOR, return_value=data):
            bill.action_mh_ai_read_bill()
        self.assertEqual(bill.partner_id.name, "مكتبة جديدة")
        self.assertAlmostEqual(bill.invoice_line_ids.price_unit, 100.0)
        self.assertAlmostEqual(bill.amount_total, 114.0)
        body = bill.message_ids[0].body
        self.assertIn("New vendor created", body)
        self.assertIn("Check the amounts", body)

    def test_guards(self):
        bill = self.env["account.move"].create({"move_type": "in_invoice"})
        with self.assertRaises(UserError):
            bill.action_mh_ai_read_bill()  # no file
        invoice = self.env["account.move"].create({"move_type": "out_invoice"})
        with self.assertRaises(UserError):
            invoice.action_mh_ai_read_bill()  # customer invoice

    def test_missing_api_key(self):
        bill, _att = self._bill_with_file()
        self.env["ir.config_parameter"].sudo().set_param("mh_ai_bill_reader.api_key", False)
        with self.assertRaisesRegex(UserError, "API key"):
            bill.action_mh_ai_read_bill()

    def test_batch_and_auto_read(self):
        bill_ok, _a = self._bill_with_file()
        bill_empty = self.env["account.move"].create({"move_type": "in_invoice"})
        with patch(EXTRACTOR, return_value=self._data()):
            action = (bill_ok | bill_empty).action_mh_ai_read_bill()
        self.assertEqual(action["params"]["type"], "warning")
        self.assertEqual(len(bill_ok.invoice_line_ids), 2)
        self.assertIn("AI could not read", bill_empty.message_ids[0].body)

        self.env["ir.config_parameter"].sudo().set_param("mh_ai_bill_reader.auto_read", True)
        attachment = self.env["ir.attachment"].create({
            "name": "upload.pdf", "datas": base64.b64encode(PDF), "mimetype": "application/pdf"})
        journal = self.company_data["default_journal_purchase"]
        with patch(EXTRACTOR, return_value=self._data()):
            moves = journal.with_context(default_move_type="in_invoice")._create_document_from_attachment(
                attachment.ids)
        self.assertEqual(len(moves.invoice_line_ids), 2)
        self.assertEqual(moves.partner_id, self.vendor)
