# Copyright ADHOC SA; Odoo 19 Community adaptation by Sky Demo.
# License LGPL-3.0 or later.
import ast
import csv
import io

from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain


class AccountJournal(models.Model):
    _inherit = "account.journal"

    tax_settlement = fields.Selection([("yes", "Yes"), ("allow_per_line", "Yes, allow per line")])
    settlement_tax = fields.Selection([("generic", "Audit CSV (not a fiscal filing)")], string="Settlement export")
    settlement_partner_id = fields.Many2one("res.partner", string="Tax authority")
    settlement_account_tag_ids = fields.Many2many("account.account.tag", "account_journal_account_tag", string="Settlement tags")
    settlement_tax_ids = fields.Many2many("account.tax", check_company=True, string="Settlement taxes")
    settlement_account_id = fields.Many2one("account.account", check_company=True, domain="[('company_ids','in',company_id),('account_type','in',('asset_receivable','liability_payable'))]", string="Settlement counterpart")
    unsettled_count = fields.Integer(compute="_compute_unsettled")
    settlement_currency_id = fields.Many2one(related="company_id.currency_id", string="Settlement company currency")
    unsettled_amount = fields.Monetary(compute="_compute_unsettled", currency_field="settlement_currency_id")

    @api.constrains("tax_settlement", "type", "settlement_partner_id", "settlement_account_id", "company_id")
    def _check_settlement_configuration(self):
        for journal in self.filtered("tax_settlement"):
            if journal.type != "general" or not journal.settlement_partner_id or not journal.settlement_account_id:
                raise ValidationError(_("Settlement journals need type Miscellaneous, a tax-authority partner and a counterpart account."))
            if journal.company_id not in journal.settlement_account_id.company_ids:
                raise ValidationError(_("The settlement account must belong to the journal company."))
            if journal.settlement_account_id.account_type not in ("asset_receivable", "liability_payable"):
                raise ValidationError(_("Use a receivable or payable settlement counterpart."))

    def _get_tax_settlement_lines_domain_by_tags(self):
        self.ensure_one()
        domain = [("company_id", "=", self.company_id.id), ("parent_state", "=", "posted"), ("tax_line_id", "!=", False), "|", ("tax_tag_ids", "in", self.settlement_account_tag_ids.ids), ("tax_line_id", "in", self.settlement_tax_ids.ids)]
        for key, op in (("from_date", ">="), ("to_date", "<=")):
            if self.env.context.get(key):
                domain.append(("date", op, self.env.context[key]))
        return domain

    def _get_tax_settlement_move_lines_by_tags(self):
        return self.env["account.move.line"].search(self._get_tax_settlement_lines_domain_by_tags() + [("tax_settlement_move_id", "=", False)])

    @api.depends("settlement_account_tag_ids", "company_id")
    def _compute_unsettled(self):
        for journal in self:
            lines = journal._get_tax_settlement_move_lines_by_tags() if journal.tax_settlement else self.env["account.move.line"]
            journal.unsettled_count = len(lines)
            journal.unsettled_amount = -sum(lines.mapped("balance"))

    def _get_tax_settlement_entry_lines_vals(self, domain=None):
        self.ensure_one()
        lines = self.env["account.move.line"].search(list(domain or []) + [("company_id", "=", self.company_id.id), ("parent_state", "=", "posted")])
        values = []
        for account, group in lines.grouped("account_id").items():
            balance = self.company_id.currency_id.round(sum(group.mapped("balance")))
            if self.company_id.currency_id.is_zero(balance):
                continue
            value = {"name": self.name, "account_id": account.id, "debit": max(-balance, 0), "credit": max(balance, 0)}
            if account.currency_id:
                if any(line.currency_id != account.currency_id for line in group):
                    raise ValidationError(_("The account's fixed currency does not match the source tax lines."))
                value.update(currency_id=account.currency_id.id, amount_currency=-sum(group.mapped("amount_currency")))
            values.append(value)
        return values

    def _get_tax_settlement_entry_vals(self, lines_vals):
        self.ensure_one()
        vals = list(lines_vals)
        balance = self.company_id.currency_id.round(sum(v.get("debit", 0) - v.get("credit", 0) for v in vals))
        if not self.company_id.currency_id.is_zero(balance):
            if not self.settlement_account_id:
                raise ValidationError(_("Configure the settlement counterpart account."))
            vals.append({"name": self.name, "account_id": self.settlement_account_id.id, "partner_id": self.settlement_partner_id.id, "debit": max(-balance, 0), "credit": max(balance, 0)})
        return {"company_id": self.company_id.id, "journal_id": self.id, "date": self.env.context.get("entry_date") or fields.Date.context_today(self), "ref": self.env.context.get("entry_ref") or self.name, "line_ids": [Command.create(value) for value in vals]}

    def create_tax_settlement_entry(self, move_lines):
        self.ensure_one()
        if not self.tax_settlement or not move_lines:
            raise ValidationError(_("Choose a configured settlement journal and at least one posted tax line."))
        move_lines.check_access("write")
        move_lines.lock_for_update()
        move_lines.invalidate_recordset(["tax_settlement_move_id"])
        if any(line.company_id != self.company_id for line in move_lines):
            raise ValidationError(_("A settlement cannot mix companies."))
        if any(line.parent_state != "posted" or not line.tax_line_id for line in move_lines):
            raise ValidationError(_("Only posted tax lines can be settled."))
        if move_lines.filtered("tax_settlement_move_id"):
            raise ValidationError(_("Some tax lines already belong to a settlement."))
        values = self._get_tax_settlement_entry_lines_vals([("id", "in", move_lines.ids)])
        if not values:
            raise UserError(_("The selected tax balances cancel out; no settlement entry is needed."))
        move = self.env["account.move"].with_company(self.company_id).create(self._get_tax_settlement_entry_vals(values))
        move_lines.tax_settlement_move_id = move
        return move

    def action_create_tax_settlement_entry(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": _("Tax settlement"), "res_model": "account.tax.settlement.wizard", "view_mode": "form", "target": "new", "context": {"default_settlement_journal_id": self.id, "default_company_id": self.company_id.id, "default_move_line_ids": [Command.set(self._get_tax_settlement_move_lines_by_tags().ids)]}}

    def action_open_settlement_lines(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": _("Tax lines"), "res_model": "account.move.line", "view_mode": "list,form", "domain": self._get_tax_settlement_lines_domain_by_tags()}

    def action_create_payment(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": _("Tax payment"), "res_model": "account.payment", "view_mode": "form", "context": {"default_partner_id": self.settlement_partner_id.id, "default_partner_type": "supplier", "default_payment_type": "outbound", "default_company_id": self.company_id.id}}

    def get_tax_settlement_files_values(self, move_lines):
        self.ensure_one()
        if not move_lines or any(line.company_id != self.company_id or line.parent_state != "posted" for line in move_lines):
            raise ValidationError(_("Export posted lines from the journal company only."))
        if not self.settlement_tax:
            raise UserError(_("Choose an export format on the settlement journal."))
        method = getattr(self, self.settlement_tax + "_files_values", None)
        if not method:
            raise UserError(_("The selected export format is not available."))
        return method(move_lines)

    def generic_files_values(self, move_lines):
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(["date", "document", "partner", "tax", "balance", "company_currency"])
        for line in move_lines.sorted(lambda l: (l.date, l.id)):
            writer.writerow([line.date, line.move_id.name, line.partner_id.display_name, line.tax_line_id.display_name, line.balance, self.company_id.currency_id.name])
        return [{"txt_filename": "settlement_audit.csv", "txt_content": stream.getvalue()}]


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    tax_settlement_move_id = fields.Many2one("account.move", check_company=True, copy=False, ondelete="set null", index=True)
    tax_state = fields.Selection([("to_settle", "To settle"), ("to_pay", "To pay"), ("paid", "Paid")], compute="_compute_tax_state", store=True)

    @api.depends("tax_line_id", "tax_settlement_move_id.state", "tax_settlement_move_id.line_ids.reconciled")
    def _compute_tax_state(self):
        for line in self:
            settlement = line.tax_settlement_move_id
            payable = settlement.line_ids.filtered(lambda l: l.account_id.account_type in ("asset_receivable", "liability_payable"))
            line.tax_state = False if not line.tax_line_id else "to_settle" if not settlement else "paid" if settlement.state == "posted" and all(payable.mapped("reconciled")) else "to_pay"

    def _get_tax_settlement_journal(self):
        self.ensure_one()
        return self.env["account.journal"].search([("company_id", "=", self.company_id.id), ("tax_settlement", "!=", False), "|", ("settlement_account_tag_ids", "in", self.tax_tag_ids.ids), ("settlement_tax_ids", "in", self.tax_line_id.ids)])

    def get_tax_settlement_journal(self):
        journals = self.env["account.journal"]
        for line in self:
            candidates = line._get_tax_settlement_journal()
            if len(candidates) != 1:
                raise ValidationError(_("Each tax line must match exactly one settlement journal."))
            journals |= candidates
        if len(journals) != 1:
            raise ValidationError(_("Choose lines for one settlement journal and company."))
        return journals

    def create_tax_settlement_entry(self):
        return self.get_tax_settlement_journal().create_tax_settlement_entry(self)

    def button_create_tax_settlement_entry(self):
        move = self.create_tax_settlement_entry()
        move.action_post()
        return move

    def action_open_tax_settlement_entry(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": "account.move", "view_mode": "form", "res_id": self.tax_settlement_move_id.id}

    def action_pay_tax_settlement(self):
        self.ensure_one()
        debt = self.tax_settlement_move_id.line_ids.filtered(lambda l: l.account_id.account_type in ("asset_receivable", "liability_payable") and not l.reconciled)
        return {"type": "ir.actions.act_window", "res_model": "account.payment.register", "view_mode": "form", "target": "new", "context": {"active_model": "account.move.line", "active_ids": debt.ids, "payment_pro": True}}

    def get_tax_settlement_file(self, journal=None):
        journal = journal or self.get_tax_settlement_journal()
        return self.env["download_files_wizard"].action_get_files(journal.get_tax_settlement_files_values(self))


class AccountMove(models.Model):
    _inherit = "account.move"

    settled_line_ids = fields.One2many("account.move.line", "tax_settlement_move_id", readonly=True)

    def download_tax_settlement_file(self):
        self.ensure_one()
        return self.settled_line_ids.get_tax_settlement_file(self.journal_id)


class AccountReport(models.Model):
    _inherit = "account.report"

    allow_settlement = fields.Boolean()
    settlement_title = fields.Char(translate=True)
    settlement_allow_unbalanced = fields.Boolean()

    def action_closure_journal_entry(self, options):
        self.ensure_one()
        if not self.allow_settlement:
            raise UserError(_("Enable settlement on this report first."))
        return {"type": "ir.actions.act_window", "res_model": "account.tax.settlement.wizard", "view_mode": "form", "target": "new", "context": {"default_report_id": self.id, "default_company_id": self.env.company.id, "account_report_generation_options": options}}

    def _report_create_settlement_entry(self, journal, options=None, account=None):
        self.ensure_one()
        if not self.allow_settlement or not journal.tax_settlement:
            raise UserError(_("Configure settlement on both report and journal."))
        options = options or {}
        dates = options.get("date", {})
        scope = Domain([("company_id", "=", journal.company_id.id), ("parent_state", "=", "posted")])
        if dates.get("date_from"):
            scope &= Domain("date", ">=", dates["date_from"])
        if dates.get("date_to"):
            scope &= Domain("date", "<=", dates["date_to"])
        expressions = self.line_ids.expression_ids.filtered(lambda e: e.engine == "domain")
        if not expressions:
            raise UserError(_("This report has no domain expressions to settle."))
        domains = []
        for expression in expressions:
            try:
                domains.append(Domain(ast.literal_eval(expression.formula)))
            except (ValueError, SyntaxError, TypeError) as error:
                raise ValidationError(_("Invalid report domain expression.")) from error
        lines = self.env["account.move.line"].search(scope & Domain.OR(domains))
        if not lines or any(line.tax_settlement_move_id for line in lines):
            raise UserError(_("There are no eligible unsettled report lines."))
        # Report closures may include non-tax accounts. Keep the same company scope
        # and reserve their source lines exactly like tax settlements.
        lines.check_access("write")
        lines.lock_for_update()
        lines.invalidate_recordset(["tax_settlement_move_id"])
        if lines.filtered("tax_settlement_move_id"):
            raise ValidationError(_("Report lines were settled by another transaction."))
        values = journal._get_tax_settlement_entry_lines_vals([("id", "in", lines.ids)])
        if not values:
            raise UserError(_("There are no balances to close."))
        balance = sum(v.get("debit", 0) - v.get("credit", 0) for v in values)
        if not journal.company_id.currency_id.is_zero(balance) and (not self.settlement_allow_unbalanced or not account):
            raise UserError(_("Choose and authorize a counterpart account for this unbalanced report."))
        if account and journal.company_id not in account.company_ids:
            raise ValidationError(_("The counterpart must belong to the settlement company."))
        if not journal.company_id.currency_id.is_zero(balance):
            values.append({"account_id": account.id, "name": self.settlement_title or self.name, "debit": max(-balance, 0), "credit": max(balance, 0)})
        move = self.env["account.move"].with_company(journal.company_id).create(journal._get_tax_settlement_entry_vals(values))
        lines.tax_settlement_move_id = move
        return move
