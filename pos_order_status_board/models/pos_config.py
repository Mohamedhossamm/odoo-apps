import secrets
from datetime import timedelta

from odoo import api, fields, models

VOICE_OPTIONS = [
    ("none", "No voice, chime only"),
    ("ar", "Arabic"),
    ("en", "English"),
    ("both", "Arabic, then English"),
]


class PosConfig(models.Model):
    _inherit = "pos.config"

    order_status_token = fields.Char(
        copy=False,
        groups="point_of_sale.group_pos_user",
        default=lambda self: secrets.token_urlsafe(16),
    )
    order_status_url = fields.Char(
        string="Order Status Screen Link",
        compute="_compute_order_status_url",
        groups="point_of_sale.group_pos_user",
    )
    order_status_voice = fields.Selection(VOICE_OPTIONS, string="Voice Calling", default="both")
    order_status_repeat = fields.Integer(
        string="Call Each Order",
        default=2,
        help="How many times each ready order is called out.",
    )
    order_status_ready_minutes = fields.Integer(
        string="Hide Ready Orders After",
        default=10,
        help="Minutes a ready order stays on the screen. 0 keeps it until it is marked collected.",
    )

    @api.depends("order_status_token")
    def _compute_order_status_url(self):
        for config in self:
            config.order_status_url = (
                f"{config.get_base_url()}/pos/order-status/{config.id}?token={config.order_status_token}"
                if config.id and config.order_status_token
                else False
            )

    def _reset_order_status_token(self):
        for config in self:
            config.order_status_token = secrets.token_urlsafe(16)

    def action_reset_order_status_token(self):
        """Invalidate the current screen link, for example after it was shared by mistake."""
        self._reset_order_status_token()
        return True

    def _order_status_orders(self):
        self.ensure_one()
        sessions = self.env["pos.session"].search(
            [("config_id", "=", self.id), ("state", "in", ("opened", "closing_control"))]
        )
        orders = self.env["pos.order"].search(
            [
                ("session_id", "in", sessions.ids),
                ("state", "in", ("paid", "done", "invoiced")),
                ("amount_total", ">=", 0),  # refunds have nothing to collect
                ("order_status", "in", ("preparing", "ready")),
            ],
            order="date_order asc, id asc",
        )
        preparing = orders.filtered(lambda order: order.order_status == "preparing")
        ready = orders.filtered(lambda order: order.order_status == "ready")
        if self.order_status_ready_minutes > 0:
            cutoff = fields.Datetime.now() - timedelta(minutes=self.order_status_ready_minutes)
            ready = ready.filtered(lambda order: order.order_status_ready_at and order.order_status_ready_at >= cutoff)
        return preparing, ready.sorted(lambda order: order.order_status_ready_at, reverse=True)

    def get_order_status_board(self):
        """Everything the cashier panel and the customer screen display."""
        self.ensure_one()
        preparing, ready = self._order_status_orders()
        return {
            "name": self.name,
            "preparing": [order._order_status_values() for order in preparing],
            "ready": [order._order_status_values() for order in ready],
            "voice": self.order_status_voice,
            "repeat": max(self.order_status_repeat, 1),
            "board_url": self.sudo().order_status_url,
        }
