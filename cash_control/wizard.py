# Copyright 2021 ITSur; Odoo 19 adaptation by Sky Demo. AGPL-3.0 or later.
from odoo import _, fields, models
from odoo.exceptions import UserError


class CashOperationMixin(models.AbstractModel):
    _name = "pop.session.cash.mixin"
    _description = "Cash operation fields"

    pop_session_id = fields.Many2one("pop.session", required=True)
    amount = fields.Float(required=True, digits=(16, 2))
    description = fields.Char(string="Reason")

    def _journal(self):
        self.ensure_one()
        journal = self.pop_session_id.cash_register_id
        if not journal:
            raise UserError(_("This session has no cash journal."))
        return journal

    def _movement(self, sign):
        self.ensure_one()
        if self.amount <= 0 or not self.description:
            raise UserError(_("Enter a positive amount and a reason."))
        self.env["pop.session.journal.line"].create({"pop_session_journal_id": self._journal().id, "amount": sign * self.amount, "ref": self.description})
        return {"type": "ir.actions.act_window_close"}


class CashIn(models.TransientModel):
    _name = "pop.session.cash.in"
    _inherit = "pop.session.cash.mixin"
    _description = "Cash in"

    def do_cash_in(self):
        return self._movement(1)


class CashOut(models.TransientModel):
    _name = "pop.session.cash.out"
    _inherit = "pop.session.cash.mixin"
    _description = "Cash out"

    def do_cash_out(self):
        return self._movement(-1)


class CashOpen(models.TransientModel):
    _name = "pop.session.cash.open"
    _inherit = "pop.session.cash.mixin"
    _description = "Opening cash count"

    def do_pop_open(self):
        if self.amount < 0:
            raise UserError(_("The opening count cannot be negative."))
        self._journal().balance_start = self.amount
        return {"type": "ir.actions.act_window_close"}


class CashClose(models.TransientModel):
    _name = "pop.session.cash.close"
    _inherit = "pop.session.cash.mixin"
    _description = "Closing cash count"

    def do_pop_close(self):
        if self.amount < 0:
            raise UserError(_("The closing count cannot be negative."))
        self._journal().balance_end_real = self.amount
        return {"type": "ir.actions.act_window_close"}
