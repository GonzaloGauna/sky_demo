from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestWaikiLedger(AccountTestInvoicingCommon):
    def test_current_account_uses_posted_receivables_and_actual_payments(self):
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[100], post=True)
        self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=False)
        self.partner_a.invalidate_recordset()
        self.assertAlmostEqual(self.partner_a.debt_balance, invoice.amount_total)
        self.assertEqual(self.partner_a.ultima_fecha_comprobante, invoice.date)
        self.assertEqual(self.partner_a.moves_cuentacorriente.move_id, invoice)

    def test_current_account_excludes_other_company_even_if_both_selected(self):
        other = self.setup_other_company(name="Other ledger company")
        first = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[100], post=True)
        self.init_invoice("out_invoice", partner=self.partner_a, company=other["company"], amounts=[900], post=True)
        partner = self.partner_a.with_context(allowed_company_ids=[self.env.company.id, other["company"].id])
        partner.invalidate_recordset()
        self.assertAlmostEqual(partner.debt_balance, first.amount_total)

    def test_running_balance_is_stable_for_same_day_entries(self):
        invoices = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[100], post=True) | self.init_invoice("out_invoice", partner=self.partner_a, amounts=[50], post=True)
        lines = invoices.line_ids.filtered(lambda l: l.account_id.account_type == "asset_receivable").sorted(lambda l: (l.date, l.id))
        self.assertAlmostEqual(lines[0].waiki_running_balance, lines[0].balance)
        self.assertAlmostEqual(lines[-1].waiki_running_balance, sum(lines.mapped("balance")))

    def test_view_action_does_not_create_transient_snapshots(self):
        action = self.partner_a.action_view_cuenta_corriente()
        self.assertEqual(action["res_model"], "account.move.line")
        self.assertIn(("company_id", "=", self.env.company.id), action["domain"])
