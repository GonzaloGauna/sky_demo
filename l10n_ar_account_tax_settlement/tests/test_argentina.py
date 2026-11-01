from datetime import date
from odoo import Command
from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from ..models.export_compat import ExportRecords


@tagged('post_install', '-at_install')
class TestWaikiArgentina(TestArCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(su=True)
        cls.journal = cls.company_data['default_journal_misc']
        cls.journal.write({'tax_settlement': 'allow_per_line', 'settlement_partner_id': cls.partner_afip.id, 'settlement_account_id': cls.company_data['default_account_payable'].id})
        cls.tax = cls.env.ref('account.%i_ex_tax_withholding_iibb_caba_applied' % cls.env.company.id)
        cls.tax.write({'amount': 3, 'l10n_ar_withholding_sequence_id': cls.env['ir.sequence'].create({'name': 'Export test', 'padding': 8}).id,
                       'codigo_regimen': '001',
                       'regimen_retencion': '001', 'regimen_percepcion': '001',
                       'api_articulo_inciso_calculo_retencion': '001', 'api_codigo_articulo_retencion': '001',
                       'api_articulo_inciso_calculo_percepcion': '001', 'api_codigo_articulo_percepcion': '001'})
        cls.res_partner_adhoc.write({'l10n_ar_gross_income_type': 'local', 'l10n_ar_gross_income_number': '90121885123'})

    def _withholdings(self):
        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice', 'partner_id': self.res_partner_adhoc.id,
            'company_id': self.env.company.id, 'invoice_date': '2026-01-15',
            'l10n_latam_document_number': '00001-00000123',
            'invoice_line_ids': [Command.create({'name': 'Export test invoice', 'account_id': self.company_data['default_account_expense'].id, 'quantity': 1, 'price_unit': 1000, 'tax_ids': [Command.set(self.tax_21.ids)]})],
        })
        invoice.action_post()
        tax2 = self.tax.copy({'name': 'Second export withholding', 'amount': 2})
        payment = self.env['account.payment'].create({'payment_type': 'outbound', 'partner_type': 'supplier', 'partner_id': invoice.partner_id.id,
            'amount': 1160, 'date': invoice.date, 'journal_id': self.company_data['default_journal_bank'].id,
            'to_pay_move_line_ids': [Command.set(invoice.line_ids.filtered(lambda l: l.account_type == 'liability_payable').ids)],
            'l10n_ar_withholding_line_ids': [Command.create({'tax_id': tax.id, 'base_amount': 1000}) for tax in (self.tax, tax2)],
        })
        payment.l10n_ar_withholding_line_ids._compute_amount()
        payment.amount = payment.to_pay_amount - payment.withholdings_amount
        payment.action_post()
        return payment, payment.move_id.line_ids.filtered('tax_line_id')

    def test_native_payment_with_multiple_withholdings_has_separate_export_amounts(self):
        payment, lines = self._withholdings()
        self.assertEqual(len(lines), 2)
        amounts = []
        for line in ExportRecords(lines):
            self.assertAlmostEqual(line.payment_id.amount, abs(line.balance))
            self.assertEqual(line.payment_id.withholdable_base_amount, 1000)
            self.assertTrue(line.payment_id.withholding_number)
            amounts.append(line.payment_id.amount)
        self.assertAlmostEqual(sum(amounts), 50)
        self.assertNotEqual(sum(amounts), payment.amount)

    def test_regional_withholding_serializers_execute_on_native_payment(self):
        payment, lines = self._withholdings()
        layouts = ['misiones', 'drei_aplicado', 'iibb_sufrido', 'iibb_aplicado', 'iibb_aplicado_act_7',
                   'iibb_aplicado_agip', 'iibb_aplicado_api', 'iibb_aplicado_sircar', 'iibb_aplicado_dgr_mendoza', 'retenciones_iva']
        for layout in layouts:
            with self.subTest(layout=layout):
                self.journal.settlement_tax = layout
                values = self.journal.get_tax_settlement_files_values(lines)
                self.assertTrue(values)
                self.assertTrue(any(value['txt_content'] for value in values))

    def test_sicore_requires_supported_classification(self):
        _, lines = self._withholdings()
        self.journal.settlement_tax = 'sicore_aplicado'
        with self.assertRaises(ValidationError):
            self.journal.get_tax_settlement_files_values(lines)
        # The fixture uses a real posted withholding. Change export classification
        # only, to exercise SICORE's separate Ganancias branch deterministically.
        lines.tax_line_id.write({'l10n_ar_tax_type': 'earnings', 'codigo_regimen': '078'})
        result = self.journal.get_tax_settlement_files_values(lines)
        self.assertEqual(len(result[0]['txt_content'].splitlines()), 2)
        self.assertIn('0217078', result[0]['txt_content'])

    def test_setup_is_explicit_and_idempotent(self):
        setup = self.env['waiki.tax.settlement.setup'].create({'company_id': self.env.company.id, 'partner_id': self.partner_afip.id, 'account_id': self.company_data['default_account_payable'].id})
        first = setup.confirm()
        self.assertEqual(setup.confirm()['domain'], first['domain'])
        self.assertEqual(len(first['domain'][0][2]), 5)

    def test_perception_metadata_is_not_hidden_by_withholding_field_domain(self):
        perception = self.tax.copy({'name': 'Export perception', 'l10n_ar_withholding_payment_type': False, 'type_tax_use': 'sale'})
        self.env['l10n_ar.partner.tax'].create({'partner_id': self.res_partner_adhoc.id, 'tax_id': perception.id, 'regimen_percepcion': '999'})
        values = ExportRecords(perception).get_partner_alicuot(self.res_partner_adhoc, '2026-01-15')
        self.assertEqual(values.regimen_percepcion, '999')

    def test_inflation_indexes_validate_month_and_positive_value(self):
        with self.assertRaises(ValidationError):
            self.env['inflation.adjustment.index'].create({'date': '2090-01-02', 'value': 100})
        with self.assertRaises(ValidationError):
            self.env['inflation.adjustment.index'].create({'date': '2090-01-01', 'value': 0})

    def _inflation_wizard(self):
        return self.env['inflation.adjustment'].create({'company_id': self.env.company.id, 'date_from': '2090-01-01', 'date_to': '2090-02-28', 'journal_id': self.journal.id, 'account_id': self.company_data['default_account_expense'].id})

    def test_missing_inflation_index_prevents_entry(self):
        with self.assertRaises(UserError):
            self._inflation_wizard().confirm()

    def test_inflation_creates_balanced_draft_and_prevents_duplicate_period(self):
        self.env['inflation.adjustment.index'].create([{'date': '2090-01-01', 'value': 100}, {'date': '2090-02-01', 'value': 120}])
        account = self.company_data['default_account_assets'].copy({'name': 'Non monetary test asset', 'code': 'WA999', 'tag_ids': [Command.link(self.env.ref('l10n_ar_ux.no_monetaria_tag').id)]})
        entry = self.env['account.move'].create({'journal_id': self.journal.id, 'date': '2090-01-15', 'line_ids': [
            Command.create({'account_id': account.id, 'debit': 100}), Command.create({'account_id': self.company_data['default_account_expense'].id, 'credit': 100})]})
        entry.action_post()
        wizard = self._inflation_wizard()
        action = wizard.confirm()
        move = self.env['account.move'].browse(action['res_id'])
        self.assertEqual(move.state, 'draft')
        self.assertAlmostEqual(sum(move.line_ids.mapped('balance')), 0)
        self.assertAlmostEqual(move.line_ids.filtered(lambda l: l.account_id == account).balance, 20)
        with self.assertRaises(UserError):
            wizard.confirm()
