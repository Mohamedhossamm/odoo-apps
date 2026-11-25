import base64
import io

from PIL import Image

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import file_path

from ..models import label_render as lr

FONTS = {
    "bold": "web/static/fonts/google/Tajawal/Tajawal-Bold.ttf",
    "regular": "web/static/fonts/google/Tajawal/Tajawal-Medium.ttf",
}
SIZES = [
    ("50x25", "50 x 25 mm"),
    ("40x30", "40 x 30 mm"),
    ("38x25", "38 x 25 mm"),
    ("58x40", "58 x 40 mm"),
    ("100x50", "100 x 50 mm"),
    ("custom", "Custom size"),
]


class MhArabicLabelWizard(models.TransientModel):
    _name = "mh.arabic.label.wizard"
    _description = "Print Arabic Product Labels"

    line_ids = fields.One2many("mh.arabic.label.wizard.line", "wizard_id", string="Products")
    label_size = fields.Selection(SIZES, default="50x25", required=True)
    width_mm = fields.Float("Width (mm)", default=50.0)
    height_mm = fields.Float("Height (mm)", default=25.0)
    dpi = fields.Selection([("203", "203 dpi (8 dots/mm)"), ("300", "300 dpi (12 dots/mm)")],
                           string="Printer Resolution", default="203", required=True)
    output = fields.Selection([("zpl", "ZPL file (Zebra and compatible printers)"), ("pdf", "PDF")],
                              default="zpl", required=True)
    font_weight = fields.Selection([("bold", "Bold"), ("regular", "Regular")], default="bold", required=True)
    show_price = fields.Boolean("Price", default=True)
    price_prefix = fields.Char("Price Text", default="السعر:")
    currency_text = fields.Char("Currency Text", default=lambda self: self.env.company.currency_id.symbol)
    show_code = fields.Boolean("Internal Reference", default=False)
    show_barcode = fields.Boolean("Barcode", default=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        model = self.env.context.get("active_model")
        ids = self.env.context.get("active_ids") or []
        if model == "product.template":
            products = self.env["product.template"].browse(ids).product_variant_ids
        elif model == "product.product":
            products = self.env["product.product"].browse(ids)
        else:
            products = self.env["product.product"]
        if "line_ids" in fields_list and products:
            res["line_ids"] = [(0, 0, {"product_id": p.id, "quantity": 1}) for p in products]
        return res

    @api.onchange("label_size")
    def _onchange_label_size(self):
        if self.label_size and self.label_size != "custom":
            w, h = self.label_size.split("x")
            self.width_mm, self.height_mm = float(w), float(h)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _dpi(self):
        # PDF is printed by office printers: render it finer than a thermal printer would.
        return 300 if self.output == "pdf" else int(self.dpi)

    def _font_path(self):
        return file_path(FONTS[self.font_weight])

    def _price_text(self, product):
        amount = self.env.company.currency_id.round(product.lst_price)
        text = "%.2f" % amount
        return " ".join(p for p in ((self.price_prefix or "").strip(), text, (self.currency_text or "").strip()) if p)

    def _layout(self, product):
        """Positions of every element of one label, in printer dots.

        Returns (width, height, [("text", img, x, y) | ("barcode", value, x, y, module, height)]).
        """
        self.ensure_one()
        dpi = self._dpi()
        W, H = lr.mm_to_dots(self.width_mm, dpi), lr.mm_to_dots(self.height_mm, dpi)
        if W < 80 or H < 50:
            raise UserError(_("The label is too small."))
        margin = lr.mm_to_dots(1.5, dpi)
        inner = W - 2 * margin
        font = self._font_path()
        items = []

        barcode = (product.barcode or "").strip() if self.show_barcode else ""
        bc_h = int(H * 0.28) if barcode else 0
        bc_text = int(dpi / 203 * 22) if barcode else 0
        text_bottom = H - margin - (bc_h + bc_text + margin if barcode else 0)

        rows = []
        name_size = max(12, int(H * 0.15))
        name = product.with_context(display_default_code=False).display_name
        lines, size = lr.wrap(name, font, name_size, inner, 2)
        rows += [(line, size) for line in lines]
        if self.show_code and product.default_code:
            rows.append((product.default_code, max(10, int(size * 0.8))))
        if self.show_price:
            price_lines, psize = lr.wrap(self._price_text(product), font, max(12, int(H * 0.14)), inner, 1)
            rows += [(l, psize) for l in price_lines]

        images = [lr.draw_text(text, font, size) for text, size in rows]
        gap = max(2, int(H * 0.02))
        total = sum(img.height for img in images) + gap * (len(images) - 1)
        available = text_bottom - margin
        if total > available and images:
            scale = available / total
            images = [img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))
                      for img in images]
            total = sum(img.height for img in images) + gap * (len(images) - 1)
        y = margin + max(0, (available - total) // 2)
        for img in images:
            items.append(("text", img, (W - img.width) // 2, y))
            y += img.height + gap

        if barcode:
            module = max(1, dpi // 203 * 2)
            while module > 1 and self._barcode_width(barcode, module) > inner:
                module -= 1
            bw = self._barcode_width(barcode, module)
            items.append(("barcode", barcode, max(margin, (W - bw) // 2), H - margin - bc_text - bc_h, module, bc_h))
        return W, H, items

    @staticmethod
    def _barcode_width(value, module):
        return lr.barcode_modules(value) * module

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def _label_zpl(self, product):
        W, H, items = self._layout(product)
        parts = ["^XA^PW%d^LL%d^LH0,0" % (W, H)]
        for item in items:
            if item[0] == "text":
                _kind, img, x, y = item
                parts.append("^FO%d,%d%s^FS" % (x, y, lr.image_to_gfa(img)))
            else:
                _kind, value, x, y, module, height = item
                parts.append("^FO%d,%d%s" % (x, y, lr.barcode_zpl(value, module, height)))
        parts.append("^XZ")
        return "".join(parts)

    def _label_image(self, product):
        W, H, items = self._layout(product)
        page = Image.new("1", (W, H), 1)
        for item in items:
            if item[0] == "text":
                _kind, img, x, y = item
                page.paste(img, (x, y))
            else:
                _kind, value, x, y, module, height = item
                width = self._barcode_width(value, module)
                png = self.env["ir.actions.report"].barcode(
                    "auto", value, width=width, height=height, humanreadable=0, quiet=0)
                bars = Image.open(io.BytesIO(png)).convert("L").point(lambda p: 0 if p < 128 else 255, "1")
                page.paste(bars, (x, y))
                digits = lr.draw_text(value, self._font_path(), int(self._dpi() / 203 * 18))
                page.paste(digits, (x + (width - digits.width) // 2, y + height + 2))
        return page

    def _images_to_pdf(self, images):
        """One label per page, at the label's real size. reportlab keeps the bars sharp (lossless)."""
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import mm

        buf = io.BytesIO()
        size = (self.width_mm * mm, self.height_mm * mm)
        pdf = canvas.Canvas(buf, pagesize=size)
        readers = {}
        for img in images:
            reader = readers.setdefault(id(img), ImageReader(img.convert("L")))  # "L": no dithering
            pdf.drawImage(reader, 0, 0, width=size[0], height=size[1])
            pdf.showPage()
        pdf.save()
        return buf.getvalue()

    def _products(self):
        result = []
        for line in self.line_ids.filtered(lambda l: l.product_id and l.quantity > 0):
            result += [line.product_id] * line.quantity
        if not result:
            raise UserError(_("Add at least one product with a quantity."))
        return result

    def _zpl_document(self):
        """All the labels to print, as one ZPL document (bytes). Each product's label is built once."""
        self.ensure_one()
        labels, chunks = {}, []
        try:
            for product in self._products():
                if product.id not in labels:
                    labels[product.id] = self._label_zpl(product)
                chunks.append(labels[product.id])
        except lr.ShapingUnavailable:
            raise UserError(_("This server's Pillow library cannot join Arabic letters. Install libraqm "
                              "(apt install libraqm0) or: pip install arabic-reshaper python-bidi")) from None
        return "\n".join(chunks).encode()

    def action_print(self):
        self.ensure_one()
        products = self._products()
        try:
            if self.output == "zpl":
                data, name, mimetype = self._zpl_document(), "arabic_labels.zpl", "text/plain"
            else:
                pages = {}
                images = []
                for product in products:
                    if product.id not in pages:
                        pages[product.id] = self._label_image(product)
                    images.append(pages[product.id])
                data, name, mimetype = self._images_to_pdf(images), "arabic_labels.pdf", "application/pdf"
        except lr.ShapingUnavailable:
            raise UserError(_("This server's Pillow library cannot join Arabic letters. Install libraqm "
                              "(apt install libraqm0) or: pip install arabic-reshaper python-bidi")) from None
        attachment = self.env["ir.attachment"].create({
            "name": name, "raw": data, "mimetype": mimetype,
            "res_model": self._name, "res_id": self.id,
        })
        return {"type": "ir.actions.act_url", "url": "/web/content/%d?download=true" % attachment.id,
                "target": "self"}


class MhArabicLabelWizardLine(models.TransientModel):
    _name = "mh.arabic.label.wizard.line"
    _description = "Arabic Label Line"

    wizard_id = fields.Many2one("mh.arabic.label.wizard", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.product", required=True)
    quantity = fields.Integer("Labels", default=1)
