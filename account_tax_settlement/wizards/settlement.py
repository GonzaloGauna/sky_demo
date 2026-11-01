# Copyright ADHOC SA; Odoo 19 adaptation by Sky Demo. LGPL-3.0 or later.
import base64
from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError, ValidationError


class SettlementWizard(models.TransientModel):
    _name = "account.tax.settlement.wizard"
    _description = "Tax settlement wizard"
    _check_company_auto = True

    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    settlement_journal_id = fields.Many2one("account.journal", required=True, check_company=True, domain="[('company_id','=',company_id),('tax_settlement','!=',False)]")
    move_line_ids = fields.Many2many("account.move.line")
    report_id = fields.Many2one("account.report")
    account_id = fields.Many2one("account.account", check_company=True)
    report_settlement_allow_unbalanced = fields.Boolean(related="report_id.settlement_allow_unbalanced")

    @api.model
    def default_get(self, names):
        values = super().default_get(names)
        if self.env.context.get("active_model") == "account.move.line":
            lines = self.env["account.move.line"].browse(self.env.context.get("active_ids", [])).exists()
            values["move_line_ids"] = [Command.set(lines.ids)]
            if len(lines.company_id) == 1:
                values["company_id"] = lines.company_id.id
                candidates = self.env["account.journal"]
                for line in lines:
                    candidates |= line._get_tax_settlement_journal()
                if len(candidates) == 1:
                    values["settlement_journal_id"] = candidates.id
        return values

    def confirm(self):
        self.ensure_one()
        journal = self.settlement_journal_id.with_context(entry_date=self.date)
        if journal.company_id != self.company_id or self.company_id not in self.env.companies:
            raise ValidationError(_("Choose a settlement journal from the selected company."))
        move = self.report_id._report_create_settlement_entry(journal, self.env.context.get("account_report_generation_options"), self.account_id) if self.report_id else journal.create_tax_settlement_entry(self.move_line_ids)
        return {"type": "ir.actions.act_window", "res_model": "account.move", "view_mode": "form", "res_id": move.id}


class DownloadFiles(models.TransientModel):
    _name = "download_files_wizard"
    _description = "Download settlement files"

    line_ids = fields.One2many("download_files_wizard_line", "wizard_id", readonly=True)

    @api.model
    def action_get_files(self, values):
        if not values or not any(v.get("txt_content") for v in values):
            raise UserError(_("The export produced no records."))
        wizard = self.create({"line_ids": [Command.create({"txt_filename": v["txt_filename"], "txt_binary": base64.b64encode(v["txt_content"].encode("utf-8"))}) for v in values if v.get("txt_content")]})
        return {"type": "ir.actions.act_window", "res_model": self._name, "res_id": wizard.id, "view_mode": "form", "target": "new"}


class DownloadFile(models.TransientModel):
    _name = "download_files_wizard_line"
    _description = "Settlement export file"

    wizard_id = fields.Many2one("download_files_wizard", required=True, ondelete="cascade")
    txt_filename = fields.Char(required=True)
    txt_binary = fields.Binary(required=True)


class DatesWizard(models.TransientModel):
    _name = "get_dates_wizard"
    _description = "Settlement dates"

    from_date = fields.Date()
    to_date = fields.Date(default=fields.Date.context_today, required=True)

    @api.model
    def open_wizard(self, method):
        if method not in ("action_create_tax_settlement_entry", "action_open_settlement_lines"):
            raise UserError(_("Unsupported settlement action."))
        return {"type": "ir.actions.act_window", "res_model": self._name, "view_mode": "form", "target": "new", "context": dict(self.env.context, method=method)}

    def confirm(self):
        self.ensure_one()
        if self.from_date and self.from_date > self.to_date:
            raise ValidationError(_("The start date cannot follow the end date."))
        method = self.env.context.get("method")
        if method not in ("action_create_tax_settlement_entry", "action_open_settlement_lines") or self.env.context.get("active_model") != "account.journal":
            raise UserError(_("Unsupported settlement action."))
        journal = self.env["account.journal"].browse(self.env.context.get("active_id")).exists().with_context(from_date=self.from_date, to_date=self.to_date)
        return getattr(journal, method)()
