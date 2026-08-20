from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    familia_id = fields.Many2one(
        "sky.familia",
        string="Familia",
        related="partner_id.familia_id",
        store=True,
        readonly=True,
    )
