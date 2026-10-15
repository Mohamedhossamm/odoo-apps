from odoo import _, fields, models
from odoo.exceptions import UserError

ORDER_STATUSES = [
    ("preparing", "Preparing"),
    ("ready", "Ready"),
    ("collected", "Collected"),
]


class PosOrder(models.Model):
    _inherit = "pos.order"

    order_status = fields.Selection(
        ORDER_STATUSES,
        string="Order Status",
        default="preparing",
        copy=False,
        index=True,
        help="Shown to customers on the order status screen.",
    )
    order_status_ready_at = fields.Datetime(string="Ready Since", copy=False)

    def set_order_status(self, status):
        if status not in dict(ORDER_STATUSES):
            raise UserError(_("Unknown order status: %s", status))
        values = {"order_status": status}
        if status == "ready":
            values["order_status_ready_at"] = fields.Datetime.now()
        self.write(values)
        return True

    def _order_status_values(self):
        self.ensure_one()
        return {"id": self.id, "number": self.tracking_number}
