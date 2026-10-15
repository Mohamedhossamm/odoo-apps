from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestArabicAmountWords(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.lang"]._activate_lang("ar_001")
        cls.egp = cls.env.ref("base.EGP")
        cls.egp.active = True
        cls.kwd = cls.env.ref("base.KWD")
        cls.kwd.active = True

    def test_amount_to_text_in_arabic(self):
        self.assertEqual(
            self.egp.with_context(lang="ar_001").amount_to_text(1234.50),
            "فقط ألف ومائتان وأربعة وثلاثون جنيهاً وخمسون قرشاً لا غير",
        )
        self.assertEqual(
            self.kwd.with_context(lang="ar_001").amount_to_text(1.25),
            "فقط دينار واحد ومائتان وخمسون فلساً لا غير",
        )

    def test_other_languages_keep_odoo_text(self):
        text = self.egp.with_context(lang="en_US").amount_to_text(1234.50)
        self.assertNotIn("فقط", text)

    def test_unsupported_currency_falls_back(self):
        jpy = self.env.ref("base.JPY")
        self.assertFalse(jpy.amount_to_arabic_text(100))
        self.assertNotIn("فقط", jpy.with_context(lang="ar_001").amount_to_text(100))

    def test_wrap_setting(self):
        self.env.company.arabic_amount_words_wrap = False
        self.assertEqual(self.egp.amount_to_arabic_text(200), "مائتا جنيه")

    def test_invoice_arabic_total(self):
        invoice = self.init_invoice(
            "out_invoice", amounts=[1000.0], taxes=[], currency=self.egp, post=True
        )
        self.assertEqual(invoice.amount_total_words_ar, "فقط ألف جنيه لا غير")
        self.assertEqual(
            invoice.with_context(lang="ar_001").amount_total_words,
            "فقط ألف جنيه لا غير",
        )
