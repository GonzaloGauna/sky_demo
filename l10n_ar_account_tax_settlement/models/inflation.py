# Copyright ADHOC SA; Odoo 19 adaptation by Sky Demo. LGPL-3.0 or later.
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError, ValidationError


class InflationIndex(models.Model):
    _name = "inflation.adjustment.index"
    _description = "Monthly inflation-adjustment index"
    _order = "date desc"
    _rec_name = "date"

    date = fields.Date(required=True, index=True)
    value = fields.Float(required=True, digits=(16, 4))
    xml_id = fields.Char(compute="_compute_xml_id")
    _unique_month = models.Constraint("UNIQUE(date)", "An index already exists for this month.")

    @api.constrains("date", "value")
    def _check_index(self):
        for index in self:
            if index.date.day != 1 or index.value <= 0:
                raise ValidationError(_("Use the first day of the month and a strictly positive index."))

    def _compute_xml_id(self):
        ids = self.get_external_id()
        for index in self:
            index.xml_id = ids.get(index.id) or False

    @api.model
    def find(self, date, closest=False):
        if not date:
            return self.browse()
        month = fields.Date.to_date(date).replace(day=1)
        return self.search([("date", "<=" if closest else "=", month)], order="date desc", limit=1)

    def get_dates(self, date=None):
        date = self.date if self else fields.Date.to_date(date)
        start = date.replace(day=1)
        return {"date_from": fields.Date.to_string(start), "date_to": fields.Date.to_string(start + relativedelta(months=1, days=-1))}


class AccountMove(models.Model):
    _inherit = "account.move"

    waiki_inflation_date_from = fields.Date(copy=False, readonly=True, index=True)
    waiki_inflation_date_to = fields.Date(copy=False, readonly=True)


class InflationAdjustment(models.TransientModel):
    _name = "inflation.adjustment"
    _description = "Inflation adjustment"
    _check_company_auto = True

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    journal_id = fields.Many2one("account.journal", check_company=True, required=True, domain="[('company_id','=',company_id),('type','=','general')]")
    account_id = fields.Many2one("account.account", check_company=True, required=True, string="Adjustment counterpart", domain="[('company_ids','in',company_id)]")
    start_index = fields.Float(compute="_compute_index", digits=(16, 4))
    end_index = fields.Float(compute="_compute_index", digits=(16, 4))
    open_cloure_entry = fields.Selection([("no", "No"), ("yes", "Yes")], default="no", required=True)
    closure_move_id = fields.Many2one("account.move", check_company=True)
    open_move_id = fields.Many2one("account.move", check_company=True)

    @api.model
    def default_get(self, names):
        vals = super().default_get(names)
        fiscal = self.env.company.compute_fiscalyear_dates(fields.Date.context_today(self) - relativedelta(years=1))
        vals.update({key: value for key, value in fiscal.items() if key in names})
        return vals

    @api.depends("date_from", "date_to")
    def _compute_index(self):
        for wizard in self:
            wizard.start_index = self.env["inflation.adjustment.index"].find(wizard.date_from).value
            wizard.end_index = self.env["inflation.adjustment.index"].find(wizard.date_to).value

    @api.constrains("date_from", "date_to", "journal_id", "company_id", "open_cloure_entry", "closure_move_id", "open_move_id")
    def _check_configuration(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise ValidationError(_("The start date cannot follow the end date."))
            if wizard.journal_id.company_id != wizard.company_id or wizard.journal_id.type != "general":
                raise ValidationError(_("Choose a miscellaneous journal in the adjustment company."))
            if wizard.open_cloure_entry == "yes" and (not wizard.open_move_id or not wizard.closure_move_id):
                raise ValidationError(_("Identify both closing and opening entries to exclude."))

    def get_periods(self, start_date=None, end_date=None):
        self.ensure_one()
        start = fields.Date.to_date(start_date or self.date_from)
        end = fields.Date.to_date(end_date or self.date_to)
        indexes = self.env["inflation.adjustment.index"]
        closing = indexes.find(end)
        if not closing:
            raise UserError(_("The closing month's inflation index is missing."))
        periods = []
        current = start
        while current <= end:
            index = indexes.find(current)
            if not index:
                raise UserError(_("The inflation index for %s is missing.", current.strftime("%Y-%m")))
            last = min(end, current.replace(day=1) + relativedelta(months=1, days=-1))
            periods.append({"date_from": current, "date_to": last, "index": index, "factor": closing.value / index.value - 1})
            current = current.replace(day=1) + relativedelta(months=1)
        return periods

    def get_move_line_domain(self):
        self.ensure_one()
        tag = self.env.ref("l10n_ar_ux.no_monetaria_tag")
        return [("company_id", "=", self.company_id.id), ("parent_state", "=", "posted"), ("account_id.tag_ids", "in", tag.ids), ("account_id", "!=", self.account_id.id), ("move_id", "not in", (self.open_move_id | self.closure_move_id).ids if self.open_cloure_entry == "yes" else [])]

    def confirm(self):
        self.ensure_one()
        if self.company_id not in self.env.companies or self.company_id not in self.account_id.company_ids:
            raise ValidationError(_("Use accounts and a selected company belonging to this adjustment."))
        self.company_id.lock_for_update()
        existing = self.env["account.move"].search([("company_id", "=", self.company_id.id), ("waiki_inflation_date_from", "=", self.date_from), ("waiki_inflation_date_to", "=", self.date_to), ("state", "!=", "cancel")], limit=1)
        if existing:
            raise UserError(_("An adjustment already exists for this period: %s.", existing.display_name))
        periods = self.get_periods()
        if not self.start_index:
            raise UserError(_("The opening month's inflation index is missing."))
        domain = self.get_move_line_domain()
        model = self.env["account.move.line"]
        currency = self.company_id.currency_id
        values = []

        def add_lines(lines, factor, label):
            for account, group in lines.grouped("account_id").items():
                adjustment = currency.round(sum(group.mapped("balance")) * factor)
                if not currency.is_zero(adjustment):
                    values.append({"account_id": account.id, "name": label, "debit": max(adjustment, 0), "credit": max(-adjustment, 0)})

        opening = model.search(domain + [("date", "<", self.date_from), ("account_id.include_initial_balance", "=", True)])
        add_lines(opening, self.end_index / self.start_index - 1, _("Inflation adjustment: opening balances"))
        for period in periods:
            lines = model.search(domain + [("date", ">=", period["date_from"]), ("date", "<=", period["date_to"])])
            add_lines(lines, period["factor"], _("Inflation adjustment: %s", period["date_from"].strftime("%Y-%m")))
        if not values:
            raise UserError(_("No non-monetary balances require an adjustment in this period."))
        balance = currency.round(sum(value["debit"] - value["credit"] for value in values))
        if not currency.is_zero(balance):
            values.append({"account_id": self.account_id.id, "name": _("Inflation adjustment counterpart"), "debit": max(-balance, 0), "credit": max(balance, 0)})
        move = self.env["account.move"].with_company(self.company_id).create({"journal_id": self.journal_id.id, "date": self.date_to, "ref": _("Inflation adjustment %s - %s", self.date_from, self.date_to), "waiki_inflation_date_from": self.date_from, "waiki_inflation_date_to": self.date_to, "line_ids": [Command.create(value) for value in values]})
        return {"type": "ir.actions.act_window", "res_model": "account.move", "view_mode": "form", "res_id": move.id}
