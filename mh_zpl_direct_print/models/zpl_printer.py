import ipaddress
import logging
import re
import socket

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

HOST_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9-]{0,62})(\.[A-Za-z0-9]([A-Za-z0-9-]{0,62}))*$")


class MhZplPrinter(models.Model):
    _name = "mh.zpl.printer"
    _description = "Network Label Printer"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    host = fields.Char("IP Address or Host Name", required=True, help="For example 192.168.1.50")
    port = fields.Integer(default=9100, required=True, help="Raw printing port. Almost all label printers use 9100.")
    timeout = fields.Integer("Timeout (seconds)", default=10)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    last_result = fields.Char(readonly=True)

    @api.constrains("host", "port", "timeout")
    def _check_address(self):
        for printer in self:
            host = (printer.host or "").strip()
            try:
                ipaddress.ip_address(host)
            except ValueError:
                if not HOST_RE.match(host):
                    raise ValidationError(_("%s is not a valid IP address or host name.", host)) from None
            if not 1 <= printer.port <= 65535:
                raise ValidationError(_("The port must be between 1 and 65535."))
            if not 1 <= printer.timeout <= 120:
                raise ValidationError(_("The timeout must be between 1 and 120 seconds."))

    def _send(self, data):
        """Send raw bytes (ZPL) to the printer. Raises UserError with a clear reason when it fails."""
        self.ensure_one()
        if isinstance(data, str):
            data = data.encode()
        address = ((self.host or "").strip(), self.port)
        try:
            with socket.create_connection(address, timeout=self.timeout) as conn:
                conn.sendall(data)
        except socket.timeout:
            reason = _("the printer did not answer in %s seconds. Check that it is on and on the same network "
                       "as the Odoo server.", self.timeout)
        except ConnectionRefusedError:
            reason = _("the printer refused the connection on port %s. Check the port in the printer settings.",
                       self.port)
        except socket.gaierror:
            reason = _("the host name %s could not be found.", self.host)
        except OSError as e:
            reason = _("network error: %s", e.strerror or e)
        else:
            self.sudo().last_result = _("OK: sent %(size)s bytes on %(date)s",
                                        size=len(data), date=fields.Datetime.now())
            return True
        _logger.info("ZPL direct print to %s:%s failed: %s", self.host, self.port, reason)
        self.sudo().last_result = _("Failed: %s", reason)
        raise UserError(_("Could not print on %(name)s: %(reason)s", name=self.name, reason=reason))

    def action_test_print(self):
        self.ensure_one()
        from odoo.addons.mh_arabic_zpl_labels.models import label_render as lr
        from odoo.tools.misc import file_path
        font = file_path("web/static/fonts/google/Tajawal/Tajawal-Bold.ttf")
        try:
            lines, size = lr.wrap("تجربة طباعة عربي - Test print", font, 30, 360, 1)
            text = lr.image_to_gfa(lr.draw_text(lines[0], font, size))
        except lr.ShapingUnavailable:
            text = ""
        zpl = ("^XA^PW400^LL200^FO20,30%s^FS^FO20,100^A0N,28,28^FD%s^FS^FO20,140^A0N,22,22^FD%s:%s^FS^XZ"
               % (text, self.name.replace("^", "")[:30], self.host, self.port))
        self._send(zpl)
        return {"type": "ir.actions.client", "tag": "display_notification",
                "params": {"title": _("Test label sent"), "type": "success",
                           "message": _("A test label was sent to %s.", self.name)}}
