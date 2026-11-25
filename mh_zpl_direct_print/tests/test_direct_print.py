import socket
import threading

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


class FakePrinter:
    """A TCP server on localhost that records what a label printer would receive."""

    def __init__(self):
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.received = b""
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        conn, _addr = self.sock.accept()
        with conn:
            while chunk := conn.recv(65536):
                self.received += chunk

    def close(self):
        self.thread.join(5)
        self.sock.close()


@tagged("post_install", "-at_install")
class TestDirectPrint(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {"name": "أتروبين أمبول ١ مجم", "barcode": "6221234567891", "list_price": 20.0})

    def _printer(self, port):
        return self.env["mh.zpl.printer"].create({"name": "Test Zebra", "host": "127.0.0.1", "port": port,
                                                  "timeout": 3})

    def test_print_labels_to_printer(self):
        fake = FakePrinter()
        printer = self._printer(fake.port)
        wizard = self.env["mh.arabic.label.wizard"].with_context(
            active_model="product.product", active_ids=self.product.ids).create(
            {"output": "printer", "printer_id": printer.id})
        wizard.line_ids.quantity = 2
        action = wizard.action_print()
        fake.close()
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(fake.received.count(b"^XA"), 2)
        self.assertIn(b"^GFA", fake.received)
        self.assertTrue(printer.last_result.startswith("OK"))

    def test_test_label(self):
        fake = FakePrinter()
        self._printer(fake.port).action_test_print()
        fake.close()
        self.assertIn(b"^GFA", fake.received)
        self.assertIn(b"Test Zebra", fake.received)

    def test_printer_offline(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            free_port = s.getsockname()[1]
        printer = self._printer(free_port)
        with self.assertRaisesRegex(UserError, "refused"):
            printer._send(b"^XA^XZ")
        self.assertTrue(printer.last_result.startswith("Failed"))

    def test_validation(self):
        with self.assertRaises(ValidationError):
            self._printer(0)
        with self.assertRaises(ValidationError):
            self.env["mh.zpl.printer"].create({"name": "x", "host": "bad host!"})

    def test_other_outputs_unchanged(self):
        wizard = self.env["mh.arabic.label.wizard"].with_context(
            active_model="product.product", active_ids=self.product.ids).create({"output": "zpl"})
        self.assertEqual(wizard.action_print()["type"], "ir.actions.act_url")
