from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError, UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestWaikiSettlement(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(su=True)
        cls.journal = cls.env['account.journal'].create({
            'name': 'Tax settlement test', 'code': 'WTST', 'type': 'general',
            'company_id': cls.env.company.id, 'tax_settlement': 'allow_per_line',
            'settlement_tax': 'generic', 'settlement_partner_id': cls.partner_a.id,
            'settlement_account_id': cls.company_data['default_account_payable'].id,
            'settlement_tax_ids': [Command.set(cls.tax_sale_a.ids)],
        })

    def _tax_lines(self):
        invoice = self.init_invoice('out_invoice', amounts=[100], taxes=self.tax_sale_a, post=True)
        return invoice.line_ids.filtered('tax_line_id')

    def test_settlement_reverses_tax_and_creates_balanced_draft(self):
        lines = self._tax_lines()
        move = self.journal.create_tax_settlement_entry(lines)
        self.assertEqual(move.state, 'draft')
        self.assertAlmostEqual(sum(move.line_ids.mapped('balance')), 0)
        reversal = move.line_ids.filtered(lambda l: l.account_id in lines.account_id)
        self.assertAlmostEqual(sum(reversal.mapped('balance')), -sum(lines.mapped('balance')))
        self.assertEqual(lines.tax_settlement_move_id, move)
        with self.assertRaises(ValidationError):
            self.journal.create_tax_settlement_entry(lines)
        move.action_post()
        self.assertEqual(lines.tax_state, 'to_pay')
        self.assertEqual(lines.action_pay_tax_settlement()['res_model'], 'account.payment.register')

    def test_draft_and_cross_company_sources_are_rejected(self):
        lines = self._tax_lines()
        lines.move_id.button_draft()
        with self.assertRaises(ValidationError):
            self.journal.create_tax_settlement_entry(lines)
        other = self.setup_other_company(name='Other settlement company')
        invoice = self.init_invoice('out_invoice', amounts=[100], company=other['company'], post=True)
        with self.assertRaises(ValidationError):
            self.journal.create_tax_settlement_entry(invoice.line_ids)

    def test_audit_csv_and_download_wizard(self):
        lines = self._tax_lines()
        files = self.journal.get_tax_settlement_files_values(lines)
        self.assertEqual(files[0]['txt_filename'], 'settlement_audit.csv')
        self.assertIn('company_currency', files[0]['txt_content'])
        action = lines.get_tax_settlement_file(self.journal)
        self.assertEqual(action['res_model'], 'download_files_wizard')

    def test_report_domain_closure_is_company_and_date_scoped(self):
        lines = self._tax_lines()
        report = self.env['account.report'].create({
            'name': 'Test closure', 'allow_settlement': True, 'settlement_allow_unbalanced': True,
            'line_ids': [Command.create({'name': 'Taxes', 'expression_ids': [Command.create({
                'label': 'balance', 'engine': 'domain', 'formula': repr([('id', 'in', lines.ids)]), 'subformula': 'sum',
            })]})],
        })
        with self.assertRaises(UserError):
            report._report_create_settlement_entry(self.journal)
        move = report._report_create_settlement_entry(self.journal, account=self.company_data['default_account_payable'])
        self.assertEqual(move.state, 'draft')
        self.assertAlmostEqual(sum(move.line_ids.mapped('balance')), 0)

    def test_dates_wizard_rejects_arbitrary_methods(self):
        wizard = self.env['get_dates_wizard'].with_context(active_model='account.journal', active_id=self.journal.id, method='unlink').create({})
        with self.assertRaises(UserError):
            wizard.confirm()
