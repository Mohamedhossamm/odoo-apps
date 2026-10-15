from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged("post_install", "-at_install")
class TestOrderStatus(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.burger = self.create_product("Burger", self.categ_basic, 10.0)
        self.open_new_session()

    def _paid_orders(self, count):
        created = self._create_orders([{"pos_order_lines_ui_args": [(self.burger, 1)]} for _ in range(count)])
        return self.env["pos.order"].browse([order.id for order in created.values()]).sorted("id")

    def _board_ids(self):
        board = self.config.get_order_status_board()
        return [o["id"] for o in board["preparing"]], [o["id"] for o in board["ready"]]

    def test_order_moves_through_the_board(self):
        first, second = self._paid_orders(2)
        self.assertEqual(self._board_ids(), ([first.id, second.id], []))

        first.set_order_status("ready")
        self.assertEqual(self._board_ids(), ([second.id], [first.id]))
        board = self.config.get_order_status_board()
        self.assertEqual(board["ready"][0]["number"], first.tracking_number)

        first.set_order_status("collected")
        self.assertEqual(self._board_ids(), ([second.id], []))

    def test_ready_orders_hide_after_the_delay(self):
        order = self._paid_orders(1)
        order.set_order_status("ready")
        order.order_status_ready_at = fields.Datetime.now() - timedelta(minutes=11)
        self.config.order_status_ready_minutes = 10
        self.assertEqual(self._board_ids(), ([], []))

        self.config.order_status_ready_minutes = 0
        self.assertEqual(self._board_ids(), ([], [order.id]))

    def test_unknown_status_is_refused(self):
        order = self._paid_orders(1)
        with self.assertRaises(UserError):
            order.set_order_status("cooking")


@tagged("post_install", "-at_install")
class TestOrderStatusScreen(HttpCase):
    def test_screen_needs_the_right_token(self):
        config = self.env["pos.config"].create({"name": "Order Status Test"})
        other = self.env["pos.config"].create({"name": "Other Shop"})
        token = config.sudo().order_status_token
        self.assertNotEqual(token, other.sudo().order_status_token)

        self.assertEqual(self.url_open(f"/pos/order-status/{config.id}?token=wrong").status_code, 404)
        self.assertEqual(self.url_open(f"/pos/order-status/{other.id}?token={token}").status_code, 404)

        page = self.url_open(f"/pos/order-status/{config.id}?token={token}")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Preparing", page.text)

        data = self.url_open(f"/pos/order-status/{config.id}/data?token={token}").json()
        self.assertEqual(data["preparing"], [])
        self.assertEqual(data["ready"], [])
        self.assertNotIn("board_url", data)
