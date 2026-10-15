import secrets

from markupsafe import Markup
from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class OrderStatusBoard(http.Controller):
    def _get_config(self, config_id, token):
        config = request.env["pos.config"].sudo().browse(config_id).exists()
        if not (config and token and config.order_status_token) or not secrets.compare_digest(
            config.order_status_token, token
        ):
            raise NotFound()
        return config

    @http.route("/pos/order-status/<int:config_id>", type="http", auth="public", methods=["GET"])
    def order_status_page(self, config_id, token=None, **kwargs):
        config = self._get_config(config_id, token)
        return request.render(
            "pos_order_status_board.order_status_page",
            {
                "doctype": Markup("<!DOCTYPE html>"),
                "config": config,
                "data_url": f"/pos/order-status/{config.id}/data?token={token}",
            },
        )

    @http.route("/pos/order-status/<int:config_id>/data", type="http", auth="public", methods=["GET"])
    def order_status_data(self, config_id, token=None, **kwargs):
        config = self._get_config(config_id, token)
        data = config.get_order_status_board()
        data.pop("board_url")  # the screen already has its link
        return request.make_json_response(data, headers={"Cache-Control": "no-store"})
