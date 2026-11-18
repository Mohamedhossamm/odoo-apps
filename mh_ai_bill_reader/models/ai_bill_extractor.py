import base64
import json
import logging
import re
import time

import requests

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_MODELS = {
    "anthropic": "claude-opus-5-5",
    "openai": "gpt-4.1",
    "gemini": False,  # picked from the models the key can use, see _gemini_models
}
# Models that accept Anthropic's server-side refusal fallback.
FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5", "claude-fable-5-2", "claude-fable-5-1", "claude-opus-5"}

SUPPORTED_MIMETYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE = 20 * 1024 * 1024
TIMEOUT = 90
MAX_GEMINI_MODELS = 8
GEMINI_MODEL_TIMEOUT = 30
GEMINI_BUDGET = 100  # seconds; Odoo stops a request after 120s by default
RETRIES = 3
RETRY_STATUSES = {429, 500, 502, 503, 504}


def _nullable(json_type):
    return {"anyOf": [{"type": json_type}, {"type": "null"}]}


BILL_SCHEMA = {
    "type": "object",
    "properties": {
        "vendor_name": {"type": "string"},
        "vendor_vat": _nullable("string"),
        "invoice_number": _nullable("string"),
        "invoice_date": _nullable("string"),
        "due_date": _nullable("string"),
        "currency": _nullable("string"),
        "prices_include_tax": {"type": "boolean"},
        "lines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "product_code": _nullable("string"),
                    "quantity": {"type": "number"},
                    "unit_price": {"type": "number"},
                    "discount_percent": {"type": "number"},
                    "tax_percent": {"type": "number"},
                },
                "required": ["description", "product_code", "quantity", "unit_price",
                             "discount_percent", "tax_percent"],
                "additionalProperties": False,
            },
        },
        "untaxed_total": _nullable("number"),
        "tax_total": _nullable("number"),
        "total": _nullable("number"),
    },
    "required": ["vendor_name", "vendor_vat", "invoice_number", "invoice_date", "due_date", "currency",
                 "prices_include_tax", "lines", "untaxed_total", "tax_total", "total"],
    "additionalProperties": False,
}

PROMPT = """You read vendor bills (supplier invoices) for an accounting system.
The document can be in Arabic, English or both, from Egypt, Saudi Arabia, the UAE or anywhere else.

Extract the data of this bill into the JSON schema. Rules:
- The vendor is the company that ISSUED the bill (the seller), not the customer it is addressed to.
- vendor_vat: the seller's tax registration number (رقم التسجيل الضريبي / الرقم الضريبي / VAT / TRN), digits only.
- Write every number with Western digits (0-9). Convert Arabic-Indic digits (٠١٢٣٤٥٦٧٨٩) and Arabic decimal separators.
- Dates as YYYY-MM-DD. Read the date format the bill uses; Arabic bills usually write day/month/year.
- currency: ISO 4217 code (EGP for جنيه, SAR for ريال سعودي, AED for درهم, USD...). null if not shown.
- One entry in lines per bill line. Keep the description in the bill's own language.
- unit_price is the price of one unit as printed on the line. Set prices_include_tax to true only when the
  line prices already include VAT.
- tax_percent: the VAT rate applied to the line (for example 14 or 15). 0 when the line has no tax.
- discount_percent: 0 when there is no discount. If the discount is a fixed amount, convert it to a percent.
- untaxed_total, tax_total and total: the totals printed on the bill, null if not printed.
- If a value is not on the bill, use null. Do not guess."""


class MhAiBillExtractor(models.AbstractModel):
    _name = "mh.ai.bill.extractor"
    _description = "AI Vendor Bill Extractor"

    @api.model
    def _get_config(self):
        params = self.env["ir.config_parameter"].sudo()
        provider = params.get_param("mh_ai_bill_reader.provider") or "anthropic"
        api_key = params.get_param("mh_ai_bill_reader.api_key")
        if not api_key:
            raise UserError(_("Add your AI API key first: Accounting > Configuration > Settings > AI Vendor Bill Reader."))
        model = params.get_param("mh_ai_bill_reader.model") or DEFAULT_MODELS[provider]
        return provider, api_key, model

    @api.model
    def extract(self, attachment):
        """Read a bill file (ir.attachment) and return the extracted data as a dict."""
        mimetype = attachment.mimetype
        if mimetype not in SUPPORTED_MIMETYPES:
            raise UserError(_("AI can read PDF and image files only. %(name)s is %(type)s.",
                              name=attachment.name, type=mimetype))
        raw = attachment.raw or b""
        if not raw:
            raise UserError(_("The file %s is empty.", attachment.name))
        if len(raw) > MAX_FILE_SIZE:
            raise UserError(_("The file %s is larger than 20 MB.", attachment.name))
        data_b64 = base64.b64encode(raw).decode()
        provider, api_key, model = self._get_config()
        reader = getattr(self, "_extract_%s" % provider)
        text = reader(api_key, model, mimetype, data_b64, attachment.name)
        try:
            data = json.loads(text)
            if isinstance(data, list) and len(data) == 1:  # some models wrap the object in a list
                data = data[0]
        except (TypeError, ValueError):
            _logger.warning("AI bill reader: invalid JSON from %s: %s", provider, (text or "")[:500])
            raise UserError(_("The AI answer could not be read. Please try again.")) from None
        if not isinstance(data, dict) or not isinstance(data.get("lines"), list):
            raise UserError(_("The AI answer could not be read. Please try again."))
        return data

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------

    def _extract_anthropic(self, api_key, model, mimetype, data_b64, filename):
        try:
            import anthropic
        except ImportError:
            raise UserError(_("The Claude provider needs the Python package 'anthropic'. "
                              "Install it on the server with: pip install anthropic")) from None

        if mimetype == "application/pdf":
            file_block = {"type": "document",
                          "source": {"type": "base64", "media_type": mimetype, "data": data_b64}}
        else:
            file_block = {"type": "image",
                          "source": {"type": "base64", "media_type": mimetype, "data": data_b64}}
        kwargs = {}
        if model in FALLBACK_MODELS:
            kwargs = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}

        client = anthropic.Anthropic(api_key=api_key, timeout=TIMEOUT, max_retries=2)
        try:
            response = client.beta.messages.create(
                model=model,
                max_tokens=16000,
                output_config={"effort": "medium",
                               "format": {"type": "json_schema", "schema": BILL_SCHEMA}},
                messages=[{"role": "user", "content": [file_block, {"type": "text", "text": PROMPT}]}],
                **kwargs,
            )
        except anthropic.AuthenticationError:
            raise UserError(_("Claude rejected the API key. Check it in the settings.")) from None
        except anthropic.PermissionDeniedError:
            raise UserError(_("This Claude API key is not allowed to use model %s.", model)) from None
        except anthropic.NotFoundError:
            raise UserError(_("Claude model %s was not found. Check the model name in the settings.", model)) from None
        except anthropic.RateLimitError:
            raise UserError(_("Claude is busy (rate limit). Please try again in a minute.")) from None
        except anthropic.BadRequestError as e:
            raise UserError(_("Claude could not read this file: %s", e.message)) from None
        except anthropic.APIStatusError as e:
            raise UserError(_("Claude error %(code)s. Please try again later.", code=e.status_code)) from None
        except anthropic.APIConnectionError:
            raise UserError(_("Could not reach Claude. Check the server's internet connection.")) from None

        if response.stop_reason == "refusal":
            raise UserError(_("Claude declined to read this file."))
        if response.stop_reason == "max_tokens":
            raise UserError(_("This bill is too long to read in one go."))
        return next((b.text for b in response.content if b.type == "text"), "")

    def _extract_openai(self, api_key, model, mimetype, data_b64, filename):
        data_url = "data:%s;base64,%s" % (mimetype, data_b64)
        if mimetype == "application/pdf":
            file_part = {"type": "file", "file": {"filename": filename or "bill.pdf", "file_data": data_url}}
        else:
            file_part = {"type": "image_url", "image_url": {"url": data_url}}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": [{"type": "text", "text": PROMPT}, file_part]}],
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "vendor_bill", "strict": True, "schema": BILL_SCHEMA}},
        }
        body = self._post("ChatGPT", "https://api.openai.com/v1/chat/completions",
                          {"Authorization": "Bearer %s" % api_key}, payload)
        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise UserError(_("ChatGPT returned an empty answer. Please try again.")) from None

    def _gemini_models(self, api_key):
        """Flash models this key can use, best first, so the module keeps working when Google
        retires a model or one is overloaded."""
        try:
            resp = requests.get("https://generativelanguage.googleapis.com/v1beta/models",
                                headers={"x-goog-api-key": api_key}, params={"pageSize": 1000}, timeout=30)
        except requests.RequestException:
            raise UserError(_("Could not reach Gemini. Check the server's internet connection.")) from None
        if resp.status_code in (400, 401, 403):
            raise UserError(_("Gemini rejected the API key. Check it in the settings."))
        resp.raise_for_status()
        names = []
        for m in resp.json().get("models", []):
            name = (m.get("name") or "").removeprefix("models/")
            if "generateContent" not in m.get("supportedGenerationMethods", []):
                continue
            if "flash" not in name or any(w in name for w in ("image", "tts", "audio", "live", "omni", "thinking")):
                continue
            names.append(name)

        def sort_key(name):
            head, _sep, tail = name.partition("flash")
            version = [int(x) for x in re.findall(r"\d+", head)]
            return ("lite" not in name, "preview" not in name and "exp" not in name, version, "-" not in tail)

        return sorted(names, key=sort_key, reverse=True)

    def _extract_gemini(self, api_key, model, mimetype, data_b64, filename):
        payload = {
            "contents": [{"parts": [{"inline_data": {"mime_type": mimetype, "data": data_b64}},
                                    {"text": PROMPT + "\n\nAnswer with JSON matching this schema:\n"
                                     + json.dumps(BILL_SCHEMA)}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"
        headers = {"x-goog-api-key": api_key}
        if model:
            body = self._post("Gemini", url % model, headers, payload)
        else:
            params = self.env["ir.config_parameter"].sudo()
            candidates = self._gemini_models(api_key)[:MAX_GEMINI_MODELS]
            last_ok = params.get_param("mh_ai_bill_reader.gemini_last_model")
            if last_ok in candidates:
                candidates.remove(last_ok)
                candidates.insert(0, last_ok)
            if not candidates:
                raise UserError(_("No Gemini Flash model is available for this key. "
                                  "Set the model name in the settings."))
            body = None
            deadline = time.monotonic() + GEMINI_BUDGET
            for name in candidates:
                remaining = deadline - time.monotonic()
                if remaining < 10:
                    break
                try:
                    resp = self._send("Gemini", url % name, headers, payload, retries=0,
                                      timeout=min(GEMINI_MODEL_TIMEOUT, remaining))
                except UserError:
                    _logger.info("AI bill reader: Gemini %s did not answer in time, trying the next model", name)
                    continue
                if resp.status_code in (404, 429, 500, 502, 503, 504):
                    _logger.info("AI bill reader: Gemini %s answered %s, trying the next model",
                                 name, resp.status_code)
                    continue
                body = self._check("Gemini", resp)
                if name != last_ok:
                    params.set_param("mh_ai_bill_reader.gemini_last_model", name)
                break
            if body is None:
                raise UserError(_("All Gemini models are busy or over the free quota right now. "
                                  "Please try again in a few minutes."))
        try:
            return body["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError):
            raise UserError(_("Gemini returned an empty answer. Please try again.")) from None

    def _post(self, label, url, headers, payload):
        return self._check(label, self._send(label, url, headers, payload))

    def _send(self, label, url, headers, payload, retries=RETRIES, timeout=TIMEOUT):
        resp = None
        for attempt in range(retries + 1):
            if attempt:
                time.sleep(2 ** attempt)  # 2s, 4s, 8s
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            except requests.RequestException:
                if attempt < retries:
                    continue
                raise UserError(_("Could not reach %s. Check the server's internet connection.", label)) from None
            if resp.status_code not in RETRY_STATUSES:
                break
            _logger.info("AI bill reader: %s answered %s, retrying", label, resp.status_code)
        return resp

    def _check(self, label, resp):
        if resp.status_code in (500, 502, 503, 504):
            raise UserError(_("%s is overloaded right now. Please try again in a few minutes.", label))
        if resp.status_code in (401, 403):
            raise UserError(_("%s rejected the API key. Check it in the settings.", label))
        if resp.status_code == 429:
            raise UserError(_("%s is busy (rate limit) or the account has no credit. Try again later.", label))
        if resp.status_code >= 400:
            _logger.warning("AI bill reader: %s error %s: %s", label, resp.status_code, resp.text[:500])
            raise UserError(_("%(label)s error %(code)s: %(text)s",
                              label=label, code=resp.status_code, text=resp.text[:300]))
        return resp.json()
