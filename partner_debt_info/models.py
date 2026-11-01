# Copyright 2021 Neri Cervin; adapted for Odoo 19 by Sky Demo.
# License AGPL-3.0 or later.
from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    debt_balance = fields.Monetary(compute="_compute_waiki_debt", currency_field="currency_id", groups="account.group_account_invoice", string="Saldo de cuenta corriente")
    ultima_fecha_comprobante = fields.Date(compute="_compute_waiki_debt", groups="account.group_account_invoice", string="Ultimo comprobante")
    moves_cuentacorriente = fields.One2many("account.move.line", "partner_id", compute="_compute_waiki_lines", groups="account.group_account_invoice", string="Cuenta corriente")

    def _waiki_ledger_domain(self):
        self.ensure_one()
        return [
            ("partner_id", "child_of", self.commercial_partner_id.id),
            ("company_id", "=", self.env.company.id),
            ("parent_state", "=", "posted"),
            ("account_id.account_type", "in", ("asset_receivable", "liability_payable")),
        ]

    @api.depends_context("company", "allowed_company_ids")
    def _compute_waiki_debt(self):
        for partner in self:
            lines = self.env["account.move.line"].search(partner._waiki_ledger_domain())
            partner.debt_balance = sum(lines.mapped("balance"))
            partner.ultima_fecha_comprobante = max(lines.mapped("date"), default=False)

    @api.depends_context("company", "allowed_company_ids")
    def _compute_waiki_lines(self):
        for partner in self:
            partner.moves_cuentacorriente = self.env["account.move.line"].search(partner._waiki_ledger_domain(), order="date,id")

    def action_view_cuenta_corriente(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": _("Cuenta corriente"), "res_model": "account.move.line", "view_mode": "list,form", "domain": self._waiki_ledger_domain(), "context": {"create": False, "edit": False, "waiki_ledger_partner": self.commercial_partner_id.id}}

    def action_view_debt_balance_detail(self):
        return self.action_view_cuenta_corriente()


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    waiki_running_balance = fields.Monetary(compute="_compute_waiki_running_balance", currency_field="company_currency_id", groups="account.group_account_invoice", string="Saldo acumulado")

    @api.depends_context("company", "waiki_ledger_partner")
    def _compute_waiki_running_balance(self):
        for line in self:
            partner = line.partner_id.commercial_partner_id
            if not partner or line.parent_state != "posted":
                line.waiki_running_balance = 0
                continue
            domain = partner._waiki_ledger_domain() + ["|", ("date", "<", line.date), "&", ("date", "=", line.date), ("id", "<=", line.id)]
            line.waiki_running_balance = sum(self.env["account.move.line"].search(domain).mapped("balance"))
