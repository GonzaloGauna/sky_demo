from odoo import _, api, fields, models


class SkySocioRecategorizarHijo(models.TransientModel):
    _name = "sky.socio.recategorizar.hijo"
    _description = "Recategorizar hijo/a a activo"

    partner_id = fields.Many2one("res.partner", required=True, readonly=True)
    current_category_id = fields.Many2one(related="partner_id.categoria_socio_id", readonly=True)
    suggested_category_id = fields.Many2one("sky.socio.categoria", readonly=True)
    new_group_familiar = fields.Selection(
        [("jefe", "Jefe"), ("individual", "Individual")],
        string="Nuevo grupo familiar",
        required=True,
        default="jefe",
    )
    reason = fields.Char(readonly=True)
    observation = fields.Text(string="Observación")
    can_confirm = fields.Boolean(compute="_compute_can_confirm")

    @api.depends("suggested_category_id")
    def _compute_can_confirm(self):
        for wizard in self:
            wizard.can_confirm = bool(wizard.suggested_category_id)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        partner = self.env["res.partner"].browse(res.get("partner_id") or self.env.context.get("default_partner_id"))
        if partner and partner.exists():
            active = self.env["sky.socio.categoria"].search([("name", "=", "Activo")], limit=1)
            res.update(
                {
                    "partner_id": partner.id,
                    "suggested_category_id": active.id if active else False,
                    "reason": _("Cambio manual para pasar de hijo/a a Activo."),
                }
            )
        return res

    def action_confirm(self):
        self.ensure_one()
        if not self.suggested_category_id:
            return {"type": "ir.actions.act_window_close"}
        self.partner_id.action_apply_recategorizar_hijo(
            self.suggested_category_id.id,
            self.new_group_familiar,
            self.observation or "",
        )
        return {"type": "ir.actions.act_window_close"}
