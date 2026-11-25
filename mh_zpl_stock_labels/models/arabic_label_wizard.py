from odoo import api, models


class MhArabicLabelWizard(models.TransientModel):
    _inherit = "mh.arabic.label.wizard"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get("active_model") != "stock.picking":
            return res
        pickings = self.env["stock.picking"].browse(self.env.context.get("active_ids") or [])
        counts = pickings._mh_label_quantities()
        if "line_ids" in fields_list:
            res["line_ids"] = [(0, 0, {"product_id": p.id, "quantity": q}) for p, q in counts.items()]
        ptype = pickings[:1].picking_type_id
        if ptype.mh_label_printer_id and "output" in fields_list:
            res.update({"output": "printer", "printer_id": ptype.mh_label_printer_id.id})
        if ptype.mh_label_size and "label_size" in fields_list:
            w, _sep, h = ptype.mh_label_size.partition("x")
            res["label_size"] = ptype.mh_label_size
            if ptype.mh_label_size != "custom":
                res.update({"width_mm": float(w), "height_mm": float(h)})
        if ptype and "show_price" in fields_list:
            res["show_price"] = ptype.mh_label_show_price
        return res
