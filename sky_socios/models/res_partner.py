import html
import re

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import email_normalize


SOCIO_CODE_RE = re.compile(r"^[A-Za-z0-9._/-]+$")


class ResPartner(models.Model):
    _inherit = ["res.partner", "mail.thread", "mail.activity.mixin"]

    tipo_registro = fields.Selection(
        [("socio", "Socio"), ("otra_cuenta", "Otra cuenta")],
        string="Tipo de registro",
        required=True,
        default="otra_cuenta",
        tracking=True,
    )
    apellido = fields.Char(string="Apellido", tracking=True)
    nombre = fields.Char(string="Nombre", tracking=True)
    genero = fields.Selection(
        [
            ("m", "Masculino"),
            ("f", "Femenino"),
            ("x", "Otro"),
            ("nd", "No declara"),
        ],
        string="Género",
        tracking=True,
    )
    fecha_nacimiento = fields.Date(string="Fecha de nacimiento", tracking=True)
    estado_civil = fields.Selection(
        [
            ("soltero", "Soltero/a"),
            ("casado", "Casado/a"),
            ("divorciado", "Divorciado/a"),
            ("viudo", "Viudo/a"),
            ("union", "Unión convivencial"),
            ("otro", "Otro"),
        ],
        string="Estado civil",
        tracking=True,
    )
    activa = fields.Boolean(string="Activa", default=True, tracking=True)
    codigo = fields.Char(string="Código", tracking=True)
    categoria_socio_id = fields.Many2one(
        "sky.socio.categoria",
        string="Categoría de socio",
        tracking=True,
    )
    grupo_familiar = fields.Selection(
        [
            ("jefe", "Jefe"),
            ("conyuge", "Cónyuge"),
            ("hijo", "Hijo/a"),
            ("individual", "Individual"),
        ],
        string="Grupo familiar",
        default="individual",
        tracking=True,
    )
    familia_id = fields.Many2one(
        "sky.familia",
        string="Familia",
        tracking=True,
        ondelete="set null",
    )
    fecha_ingreso = fields.Date(string="Fecha de ingreso", tracking=True)
    fecha_pase = fields.Date(string="Fecha de pase", tracking=True)
    pais_residencia_id = fields.Many2one("res.country", string="País de residencia", tracking=True)
    phone_aux = fields.Char(string="Teléfono auxiliar", tracking=True)
    email_aux = fields.Char(string="E-mail auxiliar", tracking=True)
    fecha_renuncia = fields.Date(string="Fecha de renuncia", tracking=True)
    fecha_cesantia = fields.Date(string="Fecha de cesantía", tracking=True)
    fecha_fallecimiento = fields.Date(string="Fecha de fallecimiento", tracking=True)
    edad = fields.Integer(string="Edad", compute="_compute_age", tracking=True)
    is_categoria_activo = fields.Boolean(string="Categoría activa", compute="_compute_category_flags", tracking=True)
    is_categoria_cadete = fields.Boolean(string="Categoría cadete", compute="_compute_category_flags", tracking=True)

    @api.depends("fecha_nacimiento")
    def _compute_age(self):
        today = fields.Date.context_today(self)
        for partner in self:
            partner.edad = relativedelta(today, partner.fecha_nacimiento).years if partner.fecha_nacimiento else 0

    @api.depends("categoria_socio_id", "categoria_socio_id.name")
    def _compute_category_flags(self):
        for partner in self:
            category_name = partner.categoria_socio_id.name if partner.categoria_socio_id else ""
            partner.is_categoria_activo = category_name == "Activo"
            partner.is_categoria_cadete = category_name.startswith("Cadete")

    def _socio_display_name(self):
        self.ensure_one()
        parts = [part for part in [self.apellido, self.nombre] if part]
        if parts:
            return ", ".join(parts[:2]) if len(parts) > 1 else parts[0]
        return self.name or _("Socio")

    def name_get(self):
        result = []
        for partner in self:
            if partner.tipo_registro == "socio":
                result.append((partner.id, partner._socio_display_name()))
            else:
                result.append((partner.id, partner.name or _("Contact")))
        return result

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = list(args or [])
        if name:
            args = ["|", "|", ("name", operator, name), ("apellido", operator, name), ("nombre", operator, name)] + args
        return self.search(args, limit=limit).name_get()

    @api.depends("apellido", "nombre", "tipo_registro")
    def _compute_display_name(self):
        super()._compute_display_name()
        for partner in self:
            if partner.tipo_registro == "socio":
                partner.display_name = partner._socio_display_name()

    def _sync_socio_name(self, vals):
        vals = dict(vals)
        tipo_registro = vals.get("tipo_registro", self.tipo_registro if self else "otra_cuenta")
        if tipo_registro == "socio":
            apellido = vals.get("apellido", getattr(self, "apellido", False))
            nombre = vals.get("nombre", getattr(self, "nombre", False))
            parts = [part for part in [apellido, nombre] if part]
            if parts:
                vals["name"] = ", ".join(parts[:2]) if len(parts) > 1 else parts[0]
            else:
                vals["name"] = vals.get("name") or (self.name if self else False) or _("Socio")
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._sync_socio_name(vals) for vals in vals_list]
        partners = super().create(vals_list)
        partners._check_partner_constraints()
        return partners

    def write(self, vals):
        vals = self._sync_socio_name(vals)
        old_families = self.mapped("familia_id")
        result = super().write(vals)
        self._check_partner_constraints()
        (old_families | self.mapped("familia_id"))._check_member_role_constraints()
        return result

    def _check_partner_constraints(self):
        for partner in self:
            if partner.tipo_registro != "socio":
                continue
            if partner.codigo:
                same_code = self.search(
                    [
                        ("id", "!=", partner.id),
                        ("tipo_registro", "=", "socio"),
                        ("codigo", "=", partner.codigo),
                    ],
                    limit=1,
                )
                if same_code:
                    raise ValidationError(_("El código de socio debe ser único entre socios."))
                if not SOCIO_CODE_RE.match(partner.codigo):
                    raise ValidationError(_("El código solo puede contener letras, números y los caracteres . _ / -"))
            if partner.email_aux and not email_normalize(partner.email_aux):
                raise ValidationError(_("El e-mail auxiliar no tiene un formato válido."))
            if partner.grupo_familiar == "individual" and partner.familia_id:
                raise ValidationError(_("Un socio individual no puede tener familia asignada."))
            if partner.grupo_familiar != "individual" and not partner.familia_id:
                raise ValidationError(_("Para jefe, cónyuge o hijo/a la familia es obligatoria."))

    @api.constrains("tipo_registro", "codigo", "email_aux", "grupo_familiar", "familia_id")
    def _constrains_partner_data(self):
        self._check_partner_constraints()

    def _get_socio_age(self, ref_date=None):
        self.ensure_one()
        if not self.fecha_nacimiento:
            return False
        ref_date = ref_date or fields.Date.context_today(self)
        return relativedelta(ref_date, self.fecha_nacimiento).years

    def _get_category_by_name(self, name):
        return self.env["sky.socio.categoria"].search([("name", "=", name)], limit=1)

    def _get_category_candidates_for_age(self, age):
        if age is False:
            return self.env["sky.socio.categoria"].search([("active", "=", True)], order="sequence, id")
        domain = [
            ("active", "=", True),
            "|",
            ("edad_minima", "=", False),
            ("edad_minima", "<=", age),
            "|",
            ("edad_maxima", "=", False),
            ("edad_maxima", ">=", age),
        ]
        return self.env["sky.socio.categoria"].search(domain, order="sequence, id")

    def _post_recategorization_message(self, title, observation, reason):
        self.ensure_one()
        body = "<p><strong>%s</strong></p><p>%s</p>" % (
            html.escape(title),
            html.escape(reason or ""),
        )
        if observation:
            body += "<p><strong>Observación:</strong> %s</p>" % html.escape(observation)
        self.message_post(body=body)

    def action_open_recategorizar_hijo_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Pasar hijo/a a Activo"),
            "res_model": "sky.socio.recategorizar.hijo",
            "view_mode": "form",
            "target": "new",
            "context": {"default_partner_id": self.id},
        }

    def action_open_recategorizar_vitalicio_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Pasar a Vitalicio"),
            "res_model": "sky.socio.recategorizar.vitalicio",
            "view_mode": "form",
            "target": "new",
            "context": {"default_partner_id": self.id},
        }

    def action_open_recategorizar_cadete_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Recategorizar por edad"),
            "res_model": "sky.socio.recategorizar.cadete",
            "view_mode": "form",
            "target": "new",
            "context": {"default_partner_id": self.id},
        }

    def action_apply_recategorizar_hijo(self, target_category_id, new_group_familiar, observation=""):
        self.ensure_one()
        target_category = self.env["sky.socio.categoria"].browse(target_category_id)
        if self.categoria_socio_id == target_category and self.grupo_familiar == new_group_familiar:
            self._post_recategorization_message(_("Sin cambios"), observation, _("La ficha ya estaba en el estado destino."))
            return False
        vals = {
            "categoria_socio_id": target_category.id,
            "fecha_pase": fields.Date.context_today(self),
            "grupo_familiar": new_group_familiar,
        }
        if new_group_familiar == "individual":
            vals["familia_id"] = False
        self.write(vals)
        self._post_recategorization_message(
            _("Pasar hijo/a a Activo"),
            observation,
            _("La categoría se actualizó manualmente a Activo."),
        )
        return True

    def action_apply_recategorizar_vitalicio(self, target_category_id, observation="", warning=""):
        self.ensure_one()
        target_category = self.env["sky.socio.categoria"].browse(target_category_id)
        if self.categoria_socio_id == target_category:
            self._post_recategorization_message(_("Sin cambios"), observation, _("La ficha ya estaba en Vitalicio."))
            return False
        self.write({"categoria_socio_id": target_category.id})
        reason = _("La categoría se actualizó manualmente a Vitalicio.")
        if warning:
            reason = "%s %s" % (warning, reason)
        self._post_recategorization_message(_("Pasar a Vitalicio"), observation, reason)
        return True

    def action_apply_recategorizar_cadete(self, target_category_id, observation="", reason=""):
        self.ensure_one()
        target_category = self.env["sky.socio.categoria"].browse(target_category_id)
        if self.categoria_socio_id == target_category:
            self._post_recategorization_message(_("Sin cambios"), observation, _("La ficha ya estaba en la categoría destino."))
            return False
        self.write({"categoria_socio_id": target_category.id})
        self._post_recategorization_message(_("Recategorizar por edad"), observation, reason or _("La categoría se actualizó manualmente."))
        return True

    def _build_family_tree_node(self):
        self.ensure_one()
        category = self.categoria_socio_id
        return {
            "id": self.id,
            "name": self._socio_display_name(),
            "age": self._get_socio_age() or 0,
            "category": {
                "id": category.id,
                "name": category.name,
                "color": category.color or 0,
            }
            if category
            else False,
            "group_familiar": self.grupo_familiar,
            "active": self.activa,
            "has_image": bool(self.image_1920),
            "write_date": self.write_date.isoformat() if self.write_date else False,
            "res_id": self.id,
        }
