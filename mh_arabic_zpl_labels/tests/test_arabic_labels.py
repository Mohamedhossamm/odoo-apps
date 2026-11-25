import base64
import re

from odoo.tests import TransactionCase, tagged

from odoo.addons.mh_arabic_zpl_labels.models import label_render as lr


@tagged("post_install", "-at_install")
class TestArabicLabels(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create({
            "name": "أتروبين أمبول ١ مجم", "barcode": "6221234567891", "list_price": 20.0, "default_code": "ATR-1"})
        cls.product_latin = cls.env["product.product"].create({"name": "Paper A4", "barcode": "PA-500"})

    def _wizard(self, products, **vals):
        return self.env["mh.arabic.label.wizard"].with_context(
            active_model="product.product", active_ids=products.ids).create(vals)

    def _download(self, action):
        att_id = int(re.search(r"/web/content/(\d+)", action["url"]).group(1))
        return self.env["ir.attachment"].browse(att_id).raw

    def test_shaping_joins_arabic(self):
        self.assertTrue(lr.HAS_RAQM or lr.ShapingUnavailable)
        font = self.env["mh.arabic.label.wizard"].new({"font_weight": "bold"})._font_path()
        joined = lr.text_width("سعر", font, 40)
        separated = sum(lr.text_width(c, font, 40) for c in "سعر")
        self.assertLess(joined, separated, "Arabic letters must be joined, so the word is narrower than its letters")

    def test_gfa_encoding(self):
        from PIL import Image
        img = Image.new("1", (10, 2), 1)
        img.putpixel((0, 0), 0)
        img.putpixel((9, 1), 0)
        self.assertEqual(lr.image_to_gfa(img), "^GFA,4,4,2,80000040")

    def test_barcodes(self):
        self.assertIn("^BEN", lr.barcode_zpl("6221234567891", 2, 50))
        self.assertIn("^FD622123456789^FS", lr.barcode_zpl("6221234567891", 2, 50))
        self.assertIn("^BCN", lr.barcode_zpl("6221234567890", 2, 50), "wrong EAN check digit -> Code 128")
        self.assertIn("^BCN", lr.barcode_zpl("PA-500", 2, 50))
        self.assertEqual(lr.barcode_modules("6221234567890"), 11 * 8 + 35, "invalid EAN is Code 128, not 95")
        self.assertEqual(lr.barcode_modules("6221234567891"), 95)

    def test_zpl_file(self):
        wizard = self._wizard(self.product | self.product_latin)
        self.assertEqual(len(wizard.line_ids), 2)
        wizard.line_ids[0].quantity = 3
        zpl = self._download(wizard.action_print()).decode()
        self.assertEqual(zpl.count("^XA"), 4)
        self.assertNotIn("أتروبين", zpl, "Arabic must be sent as a graphic, not as text")
        self.assertIn("^GFA", zpl)
        self.assertIn("^PW400^LL200", zpl)  # 50 x 25 mm at 203 dpi

    def test_pdf_and_sizes(self):
        wizard = self._wizard(self.product, output="pdf", label_size="40x30")
        wizard._onchange_label_size()
        self.assertEqual((wizard.width_mm, wizard.height_mm), (40.0, 30.0))
        pdf = self._download(wizard.action_print())
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_from_template_and_300dpi(self):
        wizard = self.env["mh.arabic.label.wizard"].with_context(
            active_model="product.template", active_ids=self.product.product_tmpl_id.ids).create(
            {"dpi": "300", "show_code": True})
        zpl = self._download(wizard.action_print()).decode()
        self.assertIn("^PW591^LL295", zpl)
