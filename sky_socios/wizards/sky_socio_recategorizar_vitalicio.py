from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models


class SkySocioRecategorizarVitalicio(models.TransientModel):
    _name = "sky.socio.recategorizar.vitalicio"
    _description = "Recategorizar a vitalicio"

    partner_id = fields.Many2one("res.partner", required=True, readonly=True)
    current_category_id = fields.Many2one(related="partner_id.categoria_socio_id", readonly=True)
    suggested_category_id = fields.Many2one("sky.socio.categoria", readonly=True)
    years_from_pase = fields.Integer(string="Años desde el pase", readonly=True)
    warning = fields.Char(readonly=True)
    observation = fields.Text(string="Observación")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        partner = self.env["res.partner"].browse(res.get("partner_id") or self.env.context.get("default_partner_id"))
        if partner and partner.exists():
            vitalicio = self.env["sky.socio.categoria"].search([("name", "=", "Vitalicio")], limit=1)
            years = 0
            warning = ""
            if partner.fecha_pase:
                years = relativedelta(fields.Date.context_today(self), partner.fecha_pase).years
                if years < 40:
                    warning = _("Aún no llega a 40 años de actividad; el cambio sigue siendo manual.")
            else:
                warning = _("No hay fecha de pase informada; revise el dato antes de confirmar.")
            res.update(
                {
                    "partner_id": partner.id,
                    "suggested_category_id": vitalicio.id if vitalicio else False,
                    "years_from_pase": years,
                    "warning": warning,
                }
            )
        return res

    def action_confirm(self):
        self.ensure_one()
        if not self.suggested_category_id:
            return {"type": "ir.actions.act_window_close"}
        self.partner_id.action_apply_recategorizar_vitalicio(
            self.suggested_category_id.id,
            self.observation or "",
            self.warning or "",
        )
        return {"type": "ir.actions.act_window_close"}
