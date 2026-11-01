# License LGPL-3.0 or later. Odoo 19 replacement for the retired chart-template hook.
from odoo import _, fields, models, Command
from odoo.exceptions import UserError, ValidationError


class SettlementSetup(models.TransientModel):
    _name = "waiki.tax.settlement.setup"
    _description = "Set up Argentine tax settlement journals"
    _check_company_auto = True

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    partner_id = fields.Many2one("res.partner", required=True, string="Tax authority")
    account_id = fields.Many2one("account.account", check_company=True, required=True, domain="[('company_ids','in',company_id),('account_type','in',('asset_receivable','liability_payable'))]", string="Settlement counterpart")

    def confirm(self):
        self.ensure_one()
        if not self.env.user.has_group("account.group_account_manager"):
            raise UserError(_("Only accounting managers can configure tax settlement journals."))
        if self.company_id not in self.env.companies or self.company_id.country_id.code != "AR":
            raise ValidationError(_("Select an Argentine company."))
        taxes = self.env["account.tax"].search([("company_id", "=", self.company_id.id)])
        vat = taxes.filtered(lambda t: t.tax_group_id.l10n_ar_vat_afip_code and not t.l10n_ar_withholding_payment_type)
        suffered = taxes.filtered(lambda t: (t.l10n_ar_withholding_payment_type == "customer" or t.type_tax_use == "purchase") and t.l10n_ar_state_id)
        applied = taxes.filtered(lambda t: t.l10n_ar_withholding_payment_type == "supplier" and t.l10n_ar_tax_type in ("earnings", "earnings_scale"))
        applied_iibb = taxes.filtered(lambda t: t.l10n_ar_state_id and (t.l10n_ar_withholding_payment_type == "supplier" or t.type_tax_use == "sale"))
        journals = self.env["account.journal"]
        definitions = [("WIVA", "Liquidacion de IVA", "generic", vat), ("WIIBB", "Liquidacion IIBB sufrido", "iibb_sufrido", suffered), ("WGAN", "Liquidacion de Ganancias", "generic", taxes.browse()), ("WSIC", "Liquidacion SICORE aplicado", "sicore_aplicado", applied), ("WIBA", "Liquidacion IIBB aplicado", "generic", applied_iibb)]
        for code, name, layout, selected in definitions:
            journal = self.env["account.journal"].search([("company_id", "=", self.company_id.id), ("code", "=", code)], limit=1)
            if journal and not journal.tax_settlement:
                raise UserError(_("Journal code %s is already used by a non-settlement journal.", code))
            if not journal:
                journal = self.env["account.journal"].with_company(self.company_id).create({"name": name, "code": code, "type": "general", "company_id": self.company_id.id, "tax_settlement": "allow_per_line", "settlement_tax": layout, "settlement_partner_id": self.partner_id.id, "settlement_account_id": self.account_id.id, "settlement_tax_ids": [Command.set(selected.ids)]})
            journals |= journal
        return {"type": "ir.actions.act_window", "res_model": "account.journal", "view_mode": "list,form", "domain": [("id", "in", journals.ids)]}
