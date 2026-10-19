from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPosArabicReceipt(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.lang"]._activate_lang("ar_001")
        cls.env["res.lang"]._activate_lang("en_US")
        cls.coffee = cls.env["product.product"].with_context(lang="en_US").create({"name": "Coffee"})
        cls.coffee.with_context(lang="ar_001").name = "قهوة"
        cls.tea = cls.env["product.product"].with_context(lang="en_US").create({"name": "Tea"})

    def test_arabic_name_comes_from_the_translation(self):
        self.assertEqual(self.coffee.pos_arabic_name, "قهوة")

    def test_no_translation_gives_no_arabic_name(self):
        self.assertFalse(self.tea.pos_arabic_name)

    def test_arabic_name_is_sent_to_the_pos(self):
        config = self.env["pos.config"].create({"name": "Arabic Receipt Shop"})
        self.assertIn("pos_arabic_name", self.env["product.product"]._load_pos_data_fields(config.id))

    def test_receipt_options_are_on_by_default(self):
        config = self.env["pos.config"].create({"name": "Defaults Shop"})
        self.assertTrue(
            config.ar_receipt_labels
            and config.ar_receipt_product_names
            and config.ar_receipt_amount_words
            and config.ar_receipt_customer
        )
