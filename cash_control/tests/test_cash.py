from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, new_test_user
from odoo.exceptions import UserError, AccessError, ValidationError


@tagged("post_install", "-at_install")
class TestWaikiCash(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(su=True)
        cls.cash = cls.company_data["default_journal_cash"]
        cls.config = cls.env["pop.config"].create({"name": "Test cash point", "company_id": cls.env.company.id, "journal_ids": [Command.set(cls.cash.ids)]})

    def _session(self):
        session = self.env["pop.session"].create({"pop_id": self.config.id})
        session.action_pop_session_open()
        return session

    def _payment(self, session, amount=50):
        return self.env["account.payment"].create({"company_id": self.env.company.id, "journal_id": self.cash.id, "partner_id": self.partner_a.id, "payment_type": "inbound", "partner_type": "customer", "amount": amount, "pop_id": self.config.id, "pop_session_id": session.id})

    def test_zero_opening_count_and_cash_counted_close(self):
        session = self._session()
        wizard = self.env["pop.session.cash.in"].create({"pop_session_id": session.id, "amount": 25, "description": "Float"})
        wizard.do_cash_in()
        self.env["pop.session.cash.out"].create({"pop_session_id": session.id, "amount": 5, "description": "Withdrawal"}).do_cash_out()
        self.assertEqual(session.cash_register_balance_end, 20)
        session.action_pop_session_closing_control()
        with self.assertRaises(UserError):
            session.action_pop_session_close()
        session.cash_register_id.balance_end_real = 20
        session.action_pop_session_validate()
        self.assertEqual(session.state, "closed")
        self.assertEqual(self.config.last_closed_session_id, session)
        with self.assertRaises(UserError):
            session.cash_register_id.balance_end_real = 100

    def test_only_one_unclosed_session(self):
        self._session()
        with self.assertRaises(UserError):
            self.env["pop.session"].create({"pop_id": self.config.id})

    def test_session_cannot_be_moved_or_reassigned_to_another_cash_point(self):
        session = self._session()
        other = self.config.copy({'name': 'Other cash point'})
        with self.assertRaises(UserError):
            session.pop_id = other
        with self.assertRaises(ValidationError):
            self.env['account.payment'].create({'partner_id': self.partner_a.id, 'amount': 1, 'journal_id': self.cash.id, 'pop_id': other.id, 'pop_session_id': session.id})

    def test_cash_point_company_is_immutable_after_a_session_exists(self):
        self._session()
        other = self.setup_other_company(name='Other cash point company')
        with self.assertRaises(UserError):
            self.config.company_id = other['company']

    def test_session_journal_keeps_its_currency_and_cannot_be_reassigned(self):
        session = self._session()
        currency = session.cash_register_id.currency_id
        euro = self.env.ref('base.EUR')
        euro.active = True
        self.cash.currency_id = euro
        self.assertEqual(session.cash_register_id.currency_id, currency)
        with self.assertRaises(UserError):
            session.cash_register_id.journal_id = self.company_data['default_journal_bank']

    def test_payment_reset_and_repost_preserves_audit_trail(self):
        session = self._session()
        payment = self._payment(session)
        payment.action_post()
        payment.action_post()
        self.assertEqual(len(payment.pop_session_journal_line_ids), 1)
        self.assertEqual(session.cash_register_balance_end, 50)
        payment.action_draft()
        self.assertEqual(session.cash_register_balance_end, 0)
        self.assertEqual(len(payment.pop_session_journal_line_ids), 2)
        payment.action_post()
        self.assertEqual(session.cash_register_balance_end, 50)
        self.assertEqual(len(payment.pop_session_journal_line_ids), 3)
        with self.assertRaises(UserError):
            payment.pop_session_journal_line_ids[:1].unlink()

    def test_closed_session_needs_new_session_before_payment_reset(self):
        session = self._session()
        payment = self._payment(session)
        payment.action_post()
        session.action_pop_session_closing_control()
        session.cash_register_id.balance_end_real = 50
        session.action_pop_session_close()
        with self.assertRaises(UserError):
            payment.action_draft()
        new_session = self._session()
        self.assertEqual(new_session.cash_register_balance_start, 50)
        payment.action_draft()
        self.assertEqual(new_session.cash_register_balance_end, 0)

    def test_nonpositive_manual_operation_is_rejected(self):
        session = self._session()
        with self.assertRaises(UserError):
            self.env["pop.session.cash.in"].create({"pop_session_id": session.id, "amount": -1, "description": "Invalid"}).do_cash_in()

    def test_cross_company_cash_configuration_is_rejected(self):
        other = self.setup_other_company(name="Other cash company")
        with self.assertRaises(UserError):
            self.config.journal_ids = [Command.set(other["default_journal_cash"].ids)]

    def test_accounting_user_cannot_read_an_unselected_cash_company(self):
        user = new_test_user(self.env, login="waiki_cash_user", groups="cash_control.group_pop_user", company_id=self.env.company.id, company_ids=[Command.set(self.env.company.ids)])
        other = self.setup_other_company(name="Private cash company")
        config = self.env["pop.config"].with_company(other["company"]).create({"name": "Private cash", "company_id": other["company"].id, "journal_ids": [Command.set(other["default_journal_cash"].ids)]})
        with self.assertRaises(AccessError):
            config.with_user(user).with_context(allowed_company_ids=self.env.company.ids).read(["name"])
