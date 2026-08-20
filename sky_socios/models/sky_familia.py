from datetime import date
from html import escape

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SkyFamilia(models.Model):
    _name = "sky.familia"
    _description = "Familia"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name, id"

    name = fields.Char(string="Código", required=True, tracking=True)
    jefe_id = fields.Many2one(
        "res.partner",
        string="Jefe",
        domain=[("tipo_registro", "=", "socio")],
        tracking=True,
    )
    member_ids = fields.One2many("res.partner", "familia_id", string="Miembros")
    member_count = fields.Integer(string="Cantidad de miembros", compute="_compute_member_count", store=True, tracking=True)
    notas = fields.Text(string="Notas", tracking=True)
    member_preview_html = fields.Html(string="Vista previa", compute="_compute_member_preview_html", sanitize=False, tracking=True)

    @api.depends("member_ids")
    def _compute_member_count(self):
        for family in self:
            family.member_count = len(family.member_ids)

    @api.depends("member_ids", "member_ids.image_1920", "member_ids.write_date", "member_ids.apellido", "member_ids.nombre")
    def _compute_member_preview_html(self):
        placeholder = "/web/static/img/placeholder.png"
        for family in self:
            images = []
            for member in family._get_ordered_members()[:4]:
                image_url = (
                    f"/web/image/res.partner/{member.id}/image_1920?unique={member.write_date.isoformat() if member.write_date else member.id}"
                    if member.image_1920
                    else placeholder
                )
                member_label = member._socio_display_name() if hasattr(member, "_socio_display_name") else (member.name or "")
                images.append(
                    '<span class="o_sky_family_preview_member"><img src="%s" alt="%s"/><span>%s</span></span>'
                    % (image_url, escape(member.name or ""), escape(member_label))
                )
            family.member_preview_html = '<div class="o_sky_family_preview">%s</div>' % "".join(images)

    def _check_member_role_constraints(self):
        for family in self:
            socio_members = family.member_ids.filtered(lambda partner: partner.tipo_registro == "socio")
            if len(socio_members.filtered(lambda partner: partner.grupo_familiar == "jefe")) > 1:
                raise ValidationError(_("Solo puede existir un jefe por familia."))
            if len(socio_members.filtered(lambda partner: partner.grupo_familiar == "conyuge")) > 1:
                raise ValidationError(_("Solo puede existir un cónyuge por familia."))

    @api.constrains("member_ids", "jefe_id")
    def _constrains_member_roles(self):
        self._check_member_role_constraints()

    def _get_ordered_members(self):
        self.ensure_one()
        return self.member_ids.sorted(
            key=lambda partner: (
                partner.grupo_familiar_sequence or 99,
                partner.fecha_nacimiento or date.max,
                partner.id,
            )
        )

    def unlink(self):
        members = self.member_ids
        if members:
            members.write({"familia_id": False, "grupo_familiar": "individual"})
        return super().unlink()

    def action_open_tree(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "sky_socios_family_tree",
            "name": _("Árbol familiar"),
            "params": {"family_id": self.id},
        }

    def get_family_tree_data(self):
        self.ensure_one()
        members = self._get_ordered_members().filtered(lambda partner: partner.tipo_registro == "socio")
        chiefs = members.filtered(lambda partner: partner.grupo_familiar == "jefe")
        spouses = members.filtered(lambda partner: partner.grupo_familiar == "conyuge")
        children = members.filtered(lambda partner: partner.grupo_familiar == "hijo").sorted(
            key=lambda partner: partner.fecha_nacimiento or date.max
        )
        invalid = len(chiefs) > 1 or len(spouses) > 1
        top_members = list(chiefs[:1]) + list(spouses[:1])
        return {
            "family": {
                "id": self.id,
                "name": self.name,
                "jefe": self.jefe_id and {
                    "id": self.jefe_id.id,
                    "name": self.jefe_id._socio_display_name(),
                },
                "member_count": self.member_count,
            },
            "invalid": invalid,
            "warning": (
                _("La estructura familiar no es representable. Revise los datos de jefe/cónyuge.")
                if invalid
                else False
            ),
            "top": [member._build_family_tree_node() for member in top_members],
            "children": [member._build_family_tree_node() for member in children],
        }
