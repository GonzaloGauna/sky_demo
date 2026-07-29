from odoo import _, fields, models
from odoo.exceptions import ValidationError


class SkySocioCategoria(models.Model):
    _name = "sky.socio.categoria"
    _description = "Categoría de socio"
    _order = "sequence, name, id"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Nombre", required=True, tracking=True)
    code = fields.Char(string="Código", tracking=True)
    edad_minima = fields.Integer(string="Edad mínima", tracking=True)
    edad_maxima = fields.Integer(string="Edad máxima", tracking=True)
    descripcion = fields.Text(string="Descripción", tracking=True)
    active = fields.Boolean(string="Activa", default=True, tracking=True)
    sequence = fields.Integer(string="Secuencia", default=10, tracking=True)
    color = fields.Integer(string="Color", default=0, tracking=True)

    _sql_constraints = [
        ("sky_socio_categoria_name_unique", "unique(name)", "La categoría debe tener un nombre único."),
    ]

    def _check_code_unique(self):
        for category in self.filtered("code"):
            duplicate = self.search([("id", "!=", category.id), ("code", "=", category.code)], limit=1)
            if duplicate:
                raise ValidationError(_("El código de la categoría debe ser único si se completa."))

    def create(self, vals_list):
        categories = super().create(vals_list)
        categories._check_code_unique()
        return categories

    def write(self, vals):
        result = super().write(vals)
        self._check_code_unique()
        return result
