# Copyright ADHOC SA; Odoo 19 adaptation by Sky Demo. LGPL-3.0 or later.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    agip_padron_type = fields.Selection([("regimenes_generales", "General regimes"), ("other", "Other")], default="regimenes_generales")


class AccountTax(models.Model):
    _inherit = "account.tax"

    codigo_regimen = fields.Char(string="Fiscal regime code", size=3)
    porcentaje_exclusion = fields.Float(string="Exclusion percentage")
    jurisdiction_code = fields.Char(related="l10n_ar_state_id.jurisdiction_code")
    regimen_retencion = fields.Char(string="SIRCAR withholding regime")
    regimen_percepcion = fields.Char(string="SIRCAR perception regime")
    api_articulo_inciso_calculo_retencion = fields.Char(string="API withholding calculation article")
    api_codigo_articulo_retencion = fields.Char(string="API withholding article")
    api_articulo_inciso_calculo_percepcion = fields.Char(string="API perception calculation article")
    api_codigo_articulo_percepcion = fields.Char(string="API perception article")


class PartnerTax(models.Model):
    _inherit = "l10n_ar.partner.tax"

    regimen_retencion = fields.Char()
    regimen_percepcion = fields.Char()
    api_articulo_inciso_calculo_retencion = fields.Char()
    api_codigo_articulo_retencion = fields.Char()
    api_articulo_inciso_calculo_percepcion = fields.Char()
    api_codigo_articulo_percepcion = fields.Char()
