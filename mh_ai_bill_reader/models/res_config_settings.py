from odoo import fields, models

PROVIDERS = [
    ("anthropic", "Claude (Anthropic)"),
    ("openai", "ChatGPT (OpenAI)"),
    ("gemini", "Gemini (Google)"),
]


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mh_ai_bill_provider = fields.Selection(
        PROVIDERS,
        string="AI Provider",
        default="anthropic",
        config_parameter="mh_ai_bill_reader.provider",
    )
    mh_ai_bill_api_key = fields.Char(
        string="AI API Key",
        config_parameter="mh_ai_bill_reader.api_key",
        groups="base.group_system",
    )
    mh_ai_bill_model = fields.Char(
        string="AI Model",
        config_parameter="mh_ai_bill_reader.model",
        help="Leave empty to use the default model of the provider.",
    )
    mh_ai_bill_auto_read = fields.Boolean(
        string="Read uploaded bills automatically",
        config_parameter="mh_ai_bill_reader.auto_read",
        help="When you upload a vendor bill file, AI fills the bill right away.",
    )
