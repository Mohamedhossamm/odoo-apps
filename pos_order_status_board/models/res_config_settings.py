from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_order_status_voice = fields.Selection(related="pos_config_id.order_status_voice", readonly=False)
    pos_order_status_repeat = fields.Integer(related="pos_config_id.order_status_repeat", readonly=False)
    pos_order_status_ready_minutes = fields.Integer(
        related="pos_config_id.order_status_ready_minutes", readonly=False
    )
    pos_order_status_url = fields.Char(related="pos_config_id.order_status_url")

    def action_reset_order_status_token(self):
        self.pos_config_id.action_reset_order_status_token()
        return True
