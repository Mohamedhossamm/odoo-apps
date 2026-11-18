{
    "name": "AI Vendor Bill Reader | Arabic & English Invoice OCR with Claude, ChatGPT or Gemini",
    "summary": "Upload a vendor bill PDF or photo and AI fills the bill: vendor, tax ID, number, dates, "
    "lines, quantities, prices and VAT. Built for Arabic invoices (Egypt, Saudi Arabia, UAE) and English. "
    "Works on Odoo Community. Use your own Claude, OpenAI or Gemini API key.",
    "description": "Read vendor bills with AI: invoice OCR and data extraction for Arabic and English bills.",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "Mohamed Hossam",
    "license": "OPL-1",
    "price": 89.0,
    "currency": "USD",
    "depends": ["account"],
    "data": [
        "data/ir_actions_server.xml",
        "views/res_config_settings_views.xml",
        "views/account_move_views.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
}
