# Copyright 2026 Sky Demo. License AGPL-3.0 or later.
# Independent Community implementation; no Enterprise account_reports dependency.
import logging
from datetime import timedelta

from markupsafe import Markup, escape
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class FollowupLevel(models.Model):
    _name = "waiki.followup.level"
    _description = "Collection follow-up level"
    _order = "delay, id"
    _check_company_auto = True

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    delay = fields.Integer(string="Days after maturity", required=True, default=1)
    repeat_days = fields.Integer(default=7, required=True)
    auto_execute = fields.Boolean(default=False)
    send_email = fields.Boolean(default=False)
    send_sms = fields.Boolean(default=False)
    create_activity = fields.Boolean(default=True)
    mail_template_id = fields.Many2one("mail.template", domain="[('model', '=', 'res.partner')]")
    message = fields.Html(default="<p>Please review the outstanding invoices listed in your account.</p>")
    activity_user_id = fields.Many2one("res.users")
    _one_delay = models.Constraint("UNIQUE(company_id,delay)", "Only one follow-up level per delay and company is allowed.")

    @api.constrains("repeat_days")
    def _check_repeat(self):
        if any(level.repeat_days < 1 for level in self):
            raise ValidationError(_("The repeat interval must be at least one day."))


class FollowupHistory(models.Model):
    _name = "waiki.followup.history"
    _description = "Collection follow-up history"
    _order = "date desc,id desc"
    _check_company_auto = True

    partner_id = fields.Many2one("res.partner", required=True, ondelete="restrict")
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    level_id = fields.Many2one("waiki.followup.level", required=True, check_company=True, ondelete="restrict")
    date = fields.Date(default=fields.Date.context_today, required=True)
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, required=True)
    email_queued = fields.Boolean()
    sms_requested = fields.Boolean()
    activity_created = fields.Boolean()
    amount = fields.Monetary()
    currency_id = fields.Many2one(related="company_id.currency_id")
    _one_daily = models.Constraint("UNIQUE(partner_id,company_id,level_id,date)", "This follow-up level was already processed today.")


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    waiki_followup_excluded = fields.Boolean(string="Exclude from collection follow-up", copy=False)


class ResPartner(models.Model):
    _inherit = "res.partner"

    waiki_followup_pause = fields.Boolean(company_dependent=True, default=False, string="Pause collections", groups="account.group_account_invoice")
    waiki_followup_next_date = fields.Date(company_dependent=True, string="Next collection action", groups="account.group_account_invoice")
    waiki_followup_responsible_id = fields.Many2one("res.users", company_dependent=True, string="Collection officer", groups="account.group_account_invoice")
    waiki_followup_level_id = fields.Many2one("waiki.followup.level", compute="_compute_waiki_followup", string="Collection level", groups="account.group_account_invoice")
    waiki_followup_overdue = fields.Monetary(compute="_compute_waiki_followup", currency_field="currency_id", string="Overdue receivables", groups="account.group_account_invoice")

    def _waiki_overdue_lines(self):
        self.ensure_one()
        return self.env["account.move.line"].search([
            ("partner_id", "child_of", self.commercial_partner_id.id),
            ("company_id", "=", self.env.company.id),
            ("parent_state", "=", "posted"),
            ("account_id.account_type", "=", "asset_receivable"),
            ("reconciled", "=", False),
            ("amount_residual", ">", 0),
            ("date_maturity", "<=", fields.Date.context_today(self)),
            ("waiki_followup_excluded", "=", False),
        ], order="date_maturity,id")

    @api.depends_context("company", "allowed_company_ids")
    def _compute_waiki_followup(self):
        today = fields.Date.context_today(self)
        levels = self.env["waiki.followup.level"].search([("company_id", "=", self.env.company.id)], order="delay desc,id desc")
        for partner in self:
            lines = partner._waiki_overdue_lines()
            credit = self.env["account.move.line"].search([
                ("partner_id", "child_of", partner.commercial_partner_id.id),
                ("company_id", "=", self.env.company.id), ("parent_state", "=", "posted"),
                ("account_id.account_type", "=", "asset_receivable"), ("amount_residual", "<", 0),
                ("waiki_followup_excluded", "=", False),
            ])
            due = max(0, sum(lines.mapped("amount_residual")) + sum(credit.mapped("amount_residual")))
            partner.waiki_followup_overdue = due
            oldest = min(lines.mapped("date_maturity"), default=today)
            partner.waiki_followup_level_id = levels.filtered(lambda level: level.delay <= (today - oldest).days)[:1] if due else False

    def _waiki_followup_message(self, level):
        self.ensure_one()
        rows = Markup("").join(Markup("<li>%s: %s</li>") % (escape(line.move_id.name), escape(str(line.amount_residual))) for line in self._waiki_overdue_lines())
        return Markup("<div>%s<ul>%s</ul><p>%s</p></div>") % (Markup(level.message or ""), rows, escape(self.env.company.name))

    def action_waiki_followup(self):
        for partner in self:
            if not self.env.user.has_group("account.group_account_invoice"):
                raise UserError(_("Only accounting users can run collection follow-up."))
            commercial = partner.commercial_partner_id
            commercial.lock_for_update()
            commercial.invalidate_recordset(["waiki_followup_pause", "waiki_followup_next_date"])
            today = fields.Date.context_today(self)
            if commercial.waiki_followup_pause:
                raise UserError(_("Collection follow-up is paused for %s.", commercial.display_name))
            if commercial.waiki_followup_next_date and commercial.waiki_followup_next_date > today:
                raise UserError(_("The next action for %s is scheduled for a later date.", commercial.display_name))
            commercial.invalidate_recordset(["waiki_followup_level_id", "waiki_followup_overdue"])
            level = commercial.waiki_followup_level_id
            if not level:
                raise UserError(_("There are no overdue receivables or applicable follow-up levels."))
            if not (level.send_email or level.send_sms or level.create_activity):
                raise UserError(_("Configure an email, SMS or activity for this level."))
            history = self.env["waiki.followup.history"].search([("partner_id", "=", commercial.id), ("company_id", "=", self.env.company.id), ("level_id", "=", level.id), ("date", "=", today)])
            if history:
                raise UserError(_("This collection action was already processed today."))
            body = commercial._waiki_followup_message(level)
            if level.send_email:
                if not commercial.email:
                    raise UserError(_("The customer has no email address."))
                if level.mail_template_id:
                    level.mail_template_id.with_context(company_id=self.env.company.id).send_mail(commercial.id, force_send=False)
                else:
                    commercial.message_post(body=body, subject=_("Outstanding invoices - %s", self.env.company.name), partner_ids=commercial.ids, message_type="comment", subtype_xmlid="mail.mt_comment")
            if level.send_sms:
                commercial._message_sms(body=_("%s: please review your outstanding invoices.", self.env.company.name), partner_ids=commercial.ids)
            if level.create_activity:
                officer = commercial.waiki_followup_responsible_id or level.activity_user_id or self.env.user
                summary = "%s - %s" % (self.env.company.name, level.name)
                existing = self.env["mail.activity"].search([("res_model", "=", "res.partner"), ("res_id", "=", commercial.id), ("summary", "=", summary), ("user_id", "=", officer.id)], limit=1)
                if not existing:
                    commercial.activity_schedule("mail.mail_activity_data_call", user_id=officer.id, summary=summary, note=body, date_deadline=today)
            self.env["waiki.followup.history"].create({"partner_id": commercial.id, "company_id": self.env.company.id, "level_id": level.id, "email_queued": level.send_email, "sms_requested": level.send_sms, "activity_created": level.create_activity, "amount": commercial.waiki_followup_overdue})
            commercial.waiki_followup_next_date = today + timedelta(days=level.repeat_days)
        return True

    def action_waiki_followup_letter(self):
        return self.env.ref("waiki_account_followup.action_report_followup").report_action(self.commercial_partner_id)

    @api.model
    def _cron_waiki_followup(self):
        for company in self.env["res.company"].search([]):
            model = self.with_company(company).with_context(allowed_company_ids=[company.id])
            if not model.env["waiki.followup.level"].search_count([("company_id", "=", company.id), ("auto_execute", "=", True)]):
                continue
            lines = model.env["account.move.line"].search([("company_id", "=", company.id), ("parent_state", "=", "posted"), ("account_id.account_type", "=", "asset_receivable"), ("date_maturity", "<=", fields.Date.context_today(model)), ("amount_residual", ">", 0), ("waiki_followup_excluded", "=", False)], limit=1000)
            for partner in lines.partner_id.commercial_partner_id:
                if partner.waiki_followup_pause or (partner.waiki_followup_next_date and partner.waiki_followup_next_date > fields.Date.context_today(model)) or not partner.waiki_followup_level_id.auto_execute:
                    continue
                try:
                    with self.env.cr.savepoint():
                        partner.action_waiki_followup()
                except UserError as error:
                    _logger.warning("Waiki follow-up skipped for company %s partner %s: %s", company.id, partner.id, error)
