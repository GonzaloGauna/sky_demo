from odoo import _, api, fields, models


class SkySocioRecategorizarCadete(models.TransientModel):
    _name = "sky.socio.recategorizar.cadete"
    _description = "Recategorizar por edad"

    partner_id = fields.Many2one("res.partner", required=True, readonly=True)
    current_category_id = fields.Many2one(related="partner_id.categoria_socio_id", readonly=True)
    age = fields.Integer(readonly=True)
    candidate_category_ids = fields.Many2many("sky.socio.categoria", readonly=True)
    target_category_id = fields.Many2one("sky.socio.categoria", string="Categoría destino")
    message = fields.Char(readonly=True)
    observation = fields.Text(string="Observación")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        partner = self.env["res.partner"].browse(res.get("partner_id") or self.env.context.get("default_partner_id"))
        if partner and partner.exists():
            age = partner._get_socio_age()
            if age is False:
                candidates = self.env["sky.socio.categoria"].search([("active", "=", True)], order="sequence, id")
                message = _("No hay fecha de nacimiento; seleccione la categoría manualmente.")
            else:
                candidates = partner._get_category_candidates_for_age(age)
                if len(candidates) == 1:
                    message = _("Se encontró una única categoría candidata.")
                elif len(candidates) > 1:
                    message = _("Hay varias categorías candidatas; elija una manualmente.")
                else:
                    message = _("No se encontró una categoría exacta; elija manualmente.")
            res.update(
                {
                    "partner_id": partner.id,
                    "age": age or 0,
                    "candidate_category_ids": [(6, 0, candidates.ids)],
                    "target_category_id": candidates[:1].id if candidates else False,
                    "message": message,
                }
            )
        return res

    def action_confirm(self):
        self.ensure_one()
        if not self.target_category_id:
            return {"type": "ir.actions.act_window_close"}
        if self.partner_id.categoria_socio_id == self.target_category_id:
            self.partner_id.message_post(body=_("Sin cambios: la categoría ya coincide con la seleccionada."))
            return {"type": "ir.actions.act_window_close"}
        self.partner_id.action_apply_recategorizar_cadete(
            self.target_category_id.id,
            self.observation or "",
            self.message or "",
        )
        return {"type": "ir.actions.act_window_close"}
