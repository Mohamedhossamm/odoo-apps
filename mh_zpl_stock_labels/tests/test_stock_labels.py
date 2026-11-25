import socket

from odoo.tests import TransactionCase, tagged

from odoo.addons.mh_zpl_direct_print.tests.test_direct_print import FakePrinter


@tagged("post_install", "-at_install")
class TestStockLabels(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.receipt_type = cls.env.ref("stock.picking_type_in")
        cls.stock = cls.env.ref("stock.stock_location_stock")
        cls.supplier = cls.env.ref("stock.stock_location_suppliers")
        cls.ampoule = cls.env["product.product"].create(
            {"name": "أتروبين أمبول ١ مجم", "is_storable": True, "barcode": "6221234567891"}
            if "is_storable" in cls.env["product.product"]._fields else
            {"name": "أتروبين أمبول ١ مجم", "type": "product", "barcode": "6221234567891"})
        cls.paper = cls.env["product.product"].create({"name": "Paper A4", "barcode": "PA-500"})
        cls.dozen = cls.env.ref("uom.product_uom_dozen")

    def _move(self, product, qty, uom):
        vals = {"name": product.name, "product_id": product.id, "product_uom_qty": qty, "product_uom": uom.id,
                "location_id": self.supplier.id, "location_dest_id": self.stock.id}
        fields = self.env["stock.move"]._fields
        return (0, 0, {k: v for k, v in vals.items() if k in fields})

    def _receipt(self):
        picking = self.env["stock.picking"].create({
            "picking_type_id": self.receipt_type.id,
            "location_id": self.supplier.id, "location_dest_id": self.stock.id,
            "move_ids": [self._move(self.ampoule, 3, self.ampoule.uom_id), self._move(self.paper, 1, self.dozen)],
        })
        picking.action_confirm()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
            if "picked" in move._fields:
                move.picked = True
        return picking

    def test_quantities_and_wizard(self):
        picking = self._receipt()
        counts = picking._mh_label_quantities()
        self.assertEqual(counts[self.ampoule], 3)
        self.assertEqual(counts[self.paper], 12, "1 dozen = 12 labels")
        action = picking.action_mh_print_arabic_labels()
        wizard = self.env["mh.arabic.label.wizard"].with_context(**action["context"]).create({})
        self.assertEqual(sorted(wizard.line_ids.mapped("quantity")), [3, 12])

    def test_auto_print_on_validate(self):
        fake = FakePrinter()
        printer = self.env["mh.zpl.printer"].create({"name": "Receiving Zebra", "host": "127.0.0.1",
                                                     "port": fake.port, "timeout": 3})
        self.receipt_type.write({"mh_label_auto_print": True, "mh_label_printer_id": printer.id,
                                 "mh_label_size": "40x30"})
        picking = self._receipt()
        picking.button_validate()
        fake.close()
        self.assertEqual(picking.state, "done")
        self.assertEqual(fake.received.count(b"^XA"), 15)
        self.assertIn(b"^PW320^LL240", fake.received)  # 40 x 30 mm at 203 dpi
        self.assertIn("15 Arabic labels sent", picking.message_ids[0].body)

    def test_printer_down_does_not_block_validation(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        printer = self.env["mh.zpl.printer"].create({"name": "Off", "host": "127.0.0.1", "port": port, "timeout": 2})
        self.receipt_type.write({"mh_label_auto_print": True, "mh_label_printer_id": printer.id})
        picking = self._receipt()
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        self.assertIn("could not be printed", picking.message_ids[0].body)

    def test_no_auto_print_by_default(self):
        picking = self._receipt()
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        self.assertFalse(any("Arabic labels" in (m.body or "") for m in picking.message_ids))
