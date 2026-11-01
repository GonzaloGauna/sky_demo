# License AGPL-3.0 or later. Adapted from Waiki's multicompany extension.
from odoo import _, fields, models
from odoo.exceptions import AccessError, ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    waiki_allow_cross_company_accounting = fields.Boolean(string="Permitir vinculos contables entre empresas seleccionadas", default=False)

    def write(self, vals):
        if "waiki_allow_cross_company_accounting" in vals and not self.env.is_system():
            raise AccessError(_("Only administrators can change the cross-company accounting policy."))
        return super().write(vals)


def cross_company_subset(records, field_names, flag):
    """Do not waive company checks for records outside explicitly selected companies."""
    enabled = records.filtered(lambda r: r.company_id and r.company_id[flag])
    for record in enabled:
        if record.company_id not in records.env.companies:
            raise ValidationError(records.env._("Select the document company before using a cross-company link."))
        names = field_names if field_names is not None else record._fields
        for name in names:
            field = record._fields.get(name)
            if not field or not field.relational or not field.check_company:
                continue
            related = record[name]
            company_field = "company_id" if "company_id" in related._fields else "company_ids" if "company_ids" in related._fields else None
            if company_field and related.mapped(company_field) - records.env.companies:
                raise ValidationError(records.env._("Cross-company links must stay within the selected companies."))
    return enabled


class AccountMove(models.Model):
    _inherit = "account.move"

    def _check_company(self, fnames=None):
        enabled = cross_company_subset(self, fnames, "waiki_allow_cross_company_accounting")
        return super(AccountMove, self - enabled)._check_company(fnames)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _check_company(self, fnames=None):
        enabled = cross_company_subset(self, fnames, "waiki_allow_cross_company_accounting")
        return super(AccountMoveLine, self - enabled)._check_company(fnames)
