from datetime import timedelta
from unittest.mock import patch
from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestWaikiFollowup(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(su=True)
        cls.level = cls.env['waiki.followup.level'].create({'name': 'First reminder', 'delay': 1, 'company_id': cls.env.company.id})

    def _overdue(self, amount=100, move_type='out_invoice'):
        date = fields.Date.today() - timedelta(days=10)
        return self.init_invoice(move_type, partner=self.partner_a, invoice_date=date, amounts=[amount], taxes=self.env['account.tax'], post=True)

    def test_manual_activity_history_and_duplicate_prevention(self):
        invoice = self._overdue()
        self.partner_a.action_waiki_followup()
        history = self.env['waiki.followup.history'].search([('partner_id', '=', self.partner_a.id)])
        self.assertEqual(history.amount, invoice.amount_total)
        self.assertTrue(history.activity_created)
        self.assertEqual(history.company_id, self.env.company)
        with self.assertRaises(UserError):
            self.partner_a.action_waiki_followup()

    def test_credits_offset_debt_and_exclusions_are_respected(self):
        invoice = self._overdue()
        self._overdue(move_type='out_refund')
        self.partner_a.invalidate_recordset()
        self.assertFalse(self.partner_a.waiki_followup_overdue)
        with self.assertRaises(UserError):
            self.partner_a.action_waiki_followup()
        invoice.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable').waiki_followup_excluded = True
        self.assertFalse(self.partner_a._waiki_overdue_lines())

    def test_pause_prevents_followup(self):
        self._overdue()
        self.partner_a.waiki_followup_pause = True
        with self.assertRaises(UserError):
            self.partner_a.action_waiki_followup()

    def test_email_and_sms_use_native_apis_without_external_delivery(self):
        self._overdue()
        self.partner_a.email = 'test@example.invalid'
        self.level.write({'send_email': True, 'send_sms': True, 'create_activity': False})
        with patch.object(type(self.partner_a), 'message_post') as email, patch.object(type(self.partner_a), '_message_sms') as sms:
            self.partner_a.action_waiki_followup()
        email.assert_called_once()
        sms.assert_called_once()

    def test_letter_renders_in_community(self):
        self._overdue()
        report = self.env.ref('waiki_account_followup.action_report_followup')
        html, _ = report._render_qweb_html(report.report_name, self.partner_a.ids)
        self.assertIn(self.partner_a.name.encode(), html)

    def test_cron_disabled_and_other_company_debt_excluded(self):
        self.assertFalse(self.env.ref('waiki_account_followup.cron_followup').active)
        other = self.setup_other_company(name='Other follow-up company')
        date = fields.Date.today() - timedelta(days=10)
        self.init_invoice('out_invoice', partner=self.partner_a, company=other['company'], invoice_date=date, amounts=[900], post=True)
        self.partner_a.invalidate_recordset()
        self.assertFalse(self.partner_a.waiki_followup_overdue)
