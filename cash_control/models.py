# Copyright 2021 ITSur - Juan Pablo Garza; Odoo 19 adaptation by Sky Demo.
# License AGPL-3.0 or later.
from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError, ValidationError


class PopConfig(models.Model):
    _name = "pop.config"
    _description = "Point of payment"
    _check_company_auto = True

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    journal_ids = fields.Many2many("account.journal", "pop_journal_rel", "pop_id", "journal_id", check_company=True, domain="[('company_id', '=', company_id), ('type', 'in', ('bank', 'cash'))]")
    sequence_id = fields.Many2one("ir.sequence", check_company=True, copy=False)
    session_ids = fields.One2many("pop.session", "pop_id")
    current_session_id = fields.Many2one("pop.session", compute="_compute_current_session")
    current_session_state = fields.Char(compute="_compute_current_session")
    last_closed_session_id = fields.Many2one("pop.session", compute="_compute_last_closed")
    cash_control = fields.Boolean(default=True)

    @api.depends("session_ids.state")
    def _compute_current_session(self):
        for config in self:
            config.current_session_id = config.session_ids.filtered(lambda s: s.state != "closed")[:1]
            config.current_session_state = config.current_session_id.state or False

    @api.depends("session_ids.state")
    def _compute_last_closed(self):
        for config in self:
            config.last_closed_session_id = config.session_ids.filtered(lambda s: s.state == "closed")[:1]

    @api.constrains("journal_ids", "company_id")
    def _check_journals(self):
        for config in self:
            if any(j.company_id != config.company_id or j.type not in ("bank", "cash") for j in config.journal_ids):
                raise ValidationError(_("All point-of-payment journals must belong to its company and be bank or cash journals."))
            if len(config.journal_ids.filtered(lambda j: j.type == "cash")) > 1:
                raise ValidationError(_("Use one cash journal per point of payment."))

    @api.model_create_multi
    def create(self, vals_list):
        configs = super().create(vals_list)
        for config in configs.filtered(lambda c: not c.sequence_id):
            config.sequence_id = self.env["ir.sequence"].sudo().create({"name": config.name, "prefix": "POP/", "padding": 5, "company_id": config.company_id.id})
        return configs

    def open_session_cb(self):
        self.ensure_one()
        if self.current_session_id:
            raise UserError(_("This point of payment already has an unclosed session."))
        session = self.env["pop.session"].create({"pop_id": self.id})
        return session._open_action()

    def write(self, vals):
        if 'company_id' in vals and any(config.session_ids and config.company_id.id != vals['company_id'] for config in self):
            raise UserError(_("A cash point with session history cannot change company."))
        if 'journal_ids' in vals and any(config.current_session_id for config in self):
            raise UserError(_("Close the current session before changing its configured journals."))
        return super().write(vals)

    def open_existing_session_cb(self):
        self.ensure_one()
        return self.current_session_id._open_action()


class PopSession(models.Model):
    _name = "pop.session"
    _description = "Cash session"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"
    _check_company_auto = True

    name = fields.Char(default="/", readonly=True, copy=False)
    pop_id = fields.Many2one("pop.config", required=True, ondelete="restrict", check_company=True)
    user_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user)
    company_id = fields.Many2one(related="pop_id.company_id", store=True)
    currency_id = fields.Many2one("res.currency", compute="_compute_currency")
    state = fields.Selection([("opening_control", "Opening count"), ("opened", "Open"), ("closing_control", "Closing count"), ("closed", "Closed")], default="opening_control", required=True, tracking=True, copy=False)
    open_pop_id = fields.Many2one("pop.config", compute="_compute_open_pop", store=True)
    start_at = fields.Datetime(readonly=True)
    stop_at = fields.Datetime(readonly=True)
    journal_ids = fields.Many2many(related="pop_id.journal_ids", string="Enabled journals")
    pop_session_journal_ids = fields.One2many("pop.session.journal", "pop_session_id", copy=False)
    cash_register_id = fields.Many2one("pop.session.journal", compute="_compute_cash", store=True)
    cash_journal_id = fields.Many2one(related="cash_register_id.journal_id", string="Cash journal")
    cash_control = fields.Boolean(related="pop_id.cash_control")
    cash_register_balance_start = fields.Monetary(related="cash_register_id.balance_start")
    cash_register_balance_end = fields.Monetary(related="cash_register_id.balance_end")
    cash_register_balance_end_real = fields.Monetary(related="cash_register_id.balance_end_real")
    cash_register_difference = fields.Monetary(related="cash_register_id.difference")
    _one_open_session = models.Constraint("UNIQUE(open_pop_id)", "A point of payment can only have one unclosed session.")

    @api.depends("cash_register_id.currency_id", "company_id.currency_id")
    def _compute_currency(self):
        for session in self:
            session.currency_id = session.cash_register_id.currency_id or session.company_id.currency_id

    @api.depends("state", "pop_id")
    def _compute_open_pop(self):
        for session in self:
            session.open_pop_id = session.pop_id if session.state != "closed" else False

    @api.depends("pop_session_journal_ids.journal_id.type")
    def _compute_cash(self):
        for session in self:
            session.cash_register_id = session.pop_session_journal_ids.filtered(lambda j: j.journal_id.type == "cash")[:1]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            config = self.env["pop.config"].browse(vals.get("pop_id")).exists()
            if not config or not config.journal_ids:
                raise UserError(_("Configure the point of payment and its journals first."))
            if config.current_session_id:
                raise UserError(_("This point of payment already has an unclosed session."))
            if vals.get("state", "opening_control") != "opening_control":
                raise UserError(_("A cash session must start with an opening count."))
            vals["name"] = "%s %s" % (config.name, config.sequence_id.next_by_id())
        sessions = super().create(vals_list)
        for session in sessions:
            previous = session.pop_id.last_closed_session_id
            session.pop_session_journal_ids = [Command.create({"journal_id": journal.id, "balance_start": sum(previous.pop_session_journal_ids.filtered(lambda j: j.journal_id == journal).mapped("balance_end_real"))}) for journal in session.pop_id.journal_ids]
        return sessions

    def write(self, vals):
        if 'pop_id' in vals and any(session.pop_id.id != vals['pop_id'] for session in self):
            raise UserError(_("A session cannot be moved to another cash point."))
        if any(session.state == "closed" for session in self) and set(vals) - {"message_main_attachment_id"}:
            raise UserError(_("Closed cash sessions cannot be changed."))
        if "state" in vals:
            transitions = {"opening_control": {"opened"}, "opened": {"closing_control"}, "closing_control": {"closed"}}
            if any(vals["state"] != s.state and vals["state"] not in transitions.get(s.state, set()) for s in self):
                raise UserError(_("Invalid cash-session transition."))
            if vals["state"] == "closed":
                self._check_pop_session_balance()
        return super().write(vals)

    def action_pop_session_open(self):
        for session in self:
            if session.state != "opening_control":
                raise UserError(_("The session is not awaiting an opening count."))
            session.write({"state": "opened", "start_at": fields.Datetime.now()})
        return True

    def action_pop_session_closing_control(self):
        self.write({"state": "closing_control"})
        return True

    def _check_pop_session_balance(self):
        for session in self:
            cash = session.cash_register_id
            if cash and session.cash_control and not cash.currency_id.is_zero(cash.difference):
                raise UserError(_("The counted cash must match the theoretical balance. Record an adjustment first."))
            if cash and cash.balance_end_real < 0:
                raise UserError(_("The final cash balance cannot be negative."))

    def action_pop_session_close(self):
        for session in self:
            session.write({"state": "closed", "stop_at": fields.Datetime.now()})
        return True

    def action_pop_session_validate(self):
        return self.action_pop_session_close()

    def _open_action(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": self._name, "res_id": self.id, "view_mode": "form", "target": "current"}

    def _cash_action(self, kind):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": "pop.session.cash." + kind, "view_mode": "form", "target": "new", "context": {"default_pop_session_id": self.id}}

    def pop_cash_in(self):
        return self._cash_action("in")

    def pop_cash_out(self):
        return self._cash_action("out")

    def pop_cash_open(self):
        return self._cash_action("open")

    def pop_cash_close(self):
        return self._cash_action("close")


class PopSessionJournal(models.Model):
    _name = "pop.session.journal"
    _description = "Cash-session journal"
    _check_company_auto = True

    pop_session_id = fields.Many2one("pop.session", required=True, ondelete="restrict", check_company=True)
    journal_id = fields.Many2one("account.journal", required=True, check_company=True, ondelete="restrict")
    name = fields.Char(related="journal_id.name")
    company_id = fields.Many2one(related="pop_session_id.company_id", store=True)
    currency_id = fields.Many2one("res.currency", compute="_compute_currency", store=True, precompute=True, help="Journal currency when the session row was created.")
    date = fields.Date(default=fields.Date.context_today, required=True)
    line_ids = fields.One2many("pop.session.journal.line", "pop_session_journal_id")
    balance_start = fields.Monetary(default=0)
    balance_end_real = fields.Monetary(default=0)
    balance_end = fields.Monetary(compute="_compute_totals")
    total_entry_encoding = fields.Monetary(compute="_compute_totals")
    total_entry_encoding_in = fields.Monetary(compute="_compute_totals")
    total_entry_encoding_out = fields.Monetary(compute="_compute_totals")
    difference = fields.Monetary(compute="_compute_totals")
    _one_journal = models.Constraint("UNIQUE(pop_session_id,journal_id)", "The journal is already included in this session.")

    @api.depends("journal_id", "company_id")
    def _compute_currency(self):
        for journal in self:
            journal.currency_id = journal.journal_id.currency_id or journal.company_id.currency_id

    @api.depends("line_ids.amount", "balance_start", "balance_end_real")
    def _compute_totals(self):
        for journal in self:
            amounts = journal.line_ids.mapped("amount")
            journal.total_entry_encoding = sum(amounts)
            journal.total_entry_encoding_in = sum(a for a in amounts if a > 0)
            journal.total_entry_encoding_out = sum(a for a in amounts if a < 0)
            journal.balance_end = journal.balance_start + sum(amounts)
            journal.difference = journal.balance_end_real - journal.balance_end

    def write(self, vals):
        for journal in self:
            if any(name in vals and vals[name] != journal[name].id for name in ('journal_id', 'pop_session_id')):
                raise UserError(_("A cash-session journal cannot be reassigned. Open a new session instead."))
        if any(j.pop_session_id.state == "closed" for j in self):
            raise UserError(_("Closed session balances cannot be changed."))
        if "balance_start" in vals and any(j.pop_session_id.state != "opening_control" for j in self):
            raise UserError(_("The opening balance is fixed after opening the session."))
        return super().write(vals)


class PopSessionJournalLine(models.Model):
    _name = "pop.session.journal.line"
    _description = "Cash movement"
    _order = "date,id"
    _check_company_auto = True

    name = fields.Char(string="Reason")
    ref = fields.Char()
    date = fields.Date(default=fields.Date.context_today, required=True)
    pop_session_journal_id = fields.Many2one("pop.session.journal", required=True, check_company=True, ondelete="restrict")
    account_payment_id = fields.Many2one("account.payment", check_company=True, ondelete="restrict")
    partner_id = fields.Many2one("res.partner")
    company_id = fields.Many2one(related="pop_session_journal_id.company_id", store=True)
    currency_id = fields.Many2one(related="pop_session_journal_id.currency_id")
    amount = fields.Monetary(required=True)
    anulado = fields.Boolean(default=False, readonly=True)
    event = fields.Selection([("manual", "Cash adjustment"), ("payment", "Payment"), ("reversal", "Payment reversal")], default="manual", required=True)
    cycle = fields.Integer(default=0, required=True)
    _payment_event = models.Constraint("UNIQUE(account_payment_id,event,cycle)", "This payment event was already recorded.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            journal = self.env["pop.session.journal"].browse(vals.get("pop_session_journal_id"))
            if journal.pop_session_id.state != "opened":
                raise UserError(_("Cash movements require an open session."))
            if not vals.get("amount"):
                raise ValidationError(_("A cash movement must have a nonzero amount."))
        return super().create(vals_list)

    def write(self, vals):
        if set(vals) - {"anulado"}:
            raise UserError(_("Cash movements are immutable; record a compensating movement."))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _prevent_deletion(self):
        raise UserError(_("Cash movements cannot be deleted; record a compensating movement."))


class ResUsers(models.Model):
    _inherit = "res.users"

    default_pop_id = fields.Many2one("pop.config", string="Default point of payment")


class AccountPayment(models.Model):
    _inherit = "account.payment"

    pop_id = fields.Many2one("pop.config", check_company=True, ondelete="restrict", default=lambda self: self.env.user.default_pop_id if self.env.user.default_pop_id.company_id == self.env.company else False)
    pop_session_id = fields.Many2one("pop.session", check_company=True, ondelete="restrict", domain="[('pop_id','=',pop_id),('state','=','opened')]")
    pop_session_journal_line_ids = fields.One2many("pop.session.journal.line", "account_payment_id")

    @api.constrains('pop_id', 'pop_session_id')
    def _check_pop_session(self):
        if any(payment.pop_session_id and payment.pop_session_id.pop_id != payment.pop_id for payment in self):
            raise ValidationError(_("The selected session must belong to the payment's cash point."))

    def write(self, vals):
        if {'pop_id', 'pop_session_id'} & vals.keys() and any(payment.state != 'draft' and payment.pop_session_journal_line_ids for payment in self):
            raise UserError(_("Reset the payment to draft before changing its cash point or session."))
        return super().write(vals)

    @api.onchange("pop_id")
    def _onchange_pop_id(self):
        self.pop_session_id = self.env["pop.session"].search([("pop_id", "=", self.pop_id.id), ("state", "=", "opened")], limit=1) if self.pop_id else False

    def _waiki_session_journal(self, session):
        self.ensure_one()
        if not session or session.state != "opened" or session.company_id != self.company_id:
            raise UserError(_("Select an open cash session in the payment company."))
        journal = session.pop_session_journal_ids.filtered(lambda j: j.journal_id == self.journal_id)
        if len(journal) != 1:
            raise UserError(_("The payment journal is not enabled in the selected cash session."))
        return journal

    def action_post(self):
        for payment in self.filtered("pop_id"):
            if not payment.pop_session_id:
                payment.pop_session_id = self.env["pop.session"].search([("pop_id", "=", payment.pop_id.id), ("state", "=", "opened")], limit=1)
            payment._waiki_session_journal(payment.pop_session_id)
        result = super().action_post()
        for payment in self.filtered("pop_id"):
            existing = payment.pop_session_journal_line_ids.filtered(lambda l: l.event == "payment" and not l.anulado)
            if existing:
                continue
            journal = payment._waiki_session_journal(payment.pop_session_id)
            amount = payment.currency_id._convert(payment.amount, journal.currency_id, payment.company_id, payment.date)
            self.env["pop.session.journal.line"].create({"name": payment.name, "ref": payment.memo, "amount": amount if payment.payment_type == "inbound" else -amount, "partner_id": payment.partner_id.id, "account_payment_id": payment.id, "pop_session_journal_id": journal.id, "event": "payment", "cycle": max(payment.pop_session_journal_line_ids.mapped("cycle"), default=0) + 1})
        return result

    def _waiki_reverse_cash_entries(self):
        for payment in self:
            for line in payment.pop_session_journal_line_ids.filtered(lambda l: l.event == "payment" and not l.anulado):
                session = self.env["pop.session"].search([("pop_id", "=", line.pop_session_journal_id.pop_session_id.pop_id.id), ("state", "=", "opened")], limit=1)
                journal = payment._waiki_session_journal(session)
                if journal.currency_id != line.currency_id:
                    raise UserError(_("Reopen the cash point in the original movement currency before reversing this payment."))
                self.env["pop.session.journal.line"].create({"name": payment.name, "ref": _("Cancellation"), "amount": -line.amount, "partner_id": line.partner_id.id, "account_payment_id": payment.id, "pop_session_journal_id": journal.id, "event": "reversal", "cycle": line.cycle})
                line.anulado = True

    def action_draft(self):
        self._waiki_reverse_cash_entries()
        return super().action_draft()

    def action_cancel(self):
        self._waiki_reverse_cash_entries()
        return super().action_cancel()
