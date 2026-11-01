from types import SimpleNamespace
from unittest.mock import patch

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import UserError
from ..models import parse_bna_quotes


@tagged("post_install", "-at_install")
class TestWaikiRates(AccountTestInvoicingCommon):
    def test_bna_parser_reads_selling_values(self):
        values = parse_bna_quotes('<table><tr><td>Dolar U.S.A</td><td>990,00</td><td>1.000,00</td></tr><tr><td>Euro</td><td>1.100,00</td><td>1.200,00</td></tr></table>')
        self.assertEqual(values, {"ARS": 1, "USD": 1000, "EUR": 1200})

    def test_bna_parser_refuses_changed_or_incomplete_page(self):
        with self.assertRaises(UserError):
            parse_bna_quotes('<html><p>Unavailable</p></html>')

    def test_update_is_idempotent_and_company_specific(self):
        self.env = self.env(su=True)
        company = self.env.company
        company.dolar_update_type = "bna"
        euro = self.env.ref("base.EUR")
        euro.active = True
        with patch.object(type(euro), "_waiki_fetch_quotes", return_value={"ARS": 1, "USD": 1000, "EUR": 1200}):
            euro._waiki_update_for_company(company)
            euro._waiki_update_for_company(company)
        rates = self.env["res.currency.rate"].with_company(company).search([("currency_id", "=", euro.id), ("company_id", "=", company.id), ("name", "=", fields.Date.context_today(self.env["res.currency"]))])
        self.assertEqual(len(rates), 1)
        expected = 1200 / ({"USD": 1000, "ARS": 1, "EUR": 1200}[company.currency_id.name])
        self.assertAlmostEqual(rates.inverse_company_rate, expected)

    def test_invalid_quote_does_not_write_a_rate(self):
        self.env = self.env(su=True)
        self.env.company.dolar_update_type = "bna"
        euro = self.env.ref("base.EUR")
        euro.active = True
        before = self.env["res.currency.rate"].search_count([("company_id", "=", self.env.company.id), ("currency_id", "=", euro.id)])
        with patch.object(type(euro), "_waiki_fetch_quotes", return_value={"USD": 1000, "EUR": -10}), self.assertRaises(UserError):
            euro._waiki_update_for_company(self.env.company)
        self.assertEqual(self.env["res.currency.rate"].search_count([("company_id", "=", self.env.company.id), ("currency_id", "=", euro.id)]), before)

    def test_schedule_is_disabled_on_installation(self):
        self.assertFalse(self.env.ref("dolar_update.ir_cron_update_exchange_rate_dolar").active)

    def test_dolarapi_uses_documented_route_and_selling_quote(self):
        self.env = self.env(su=True)
        company = self.env.company
        company.dolar_update_type = 'dolarapi'
        currency = self.env.ref('base.EUR')
        response = SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'venta': 1200})
        with patch('odoo.addons.dolar_update.models.requests.get', return_value=response) as request:
            quotes = currency._waiki_fetch_quotes(company)
        self.assertEqual(quotes['EUR'], 1200)
        self.assertTrue(any(call.args[0].endswith('cotizaciones/eur') for call in request.call_args_list))

    def test_arca_uses_current_fiscal_service_mapping(self):
        self.env = self.env(su=True)
        company = self.env.company
        journal = self.company_data['default_journal_sale']
        company.write({'dolar_update_type': 'afip', 'waiki_rate_journal_id': journal.id})
        journal.l10n_ar_fiscal_ws_id = self.env.ref('l10n_ar_fiscal_ws.fiscal_ws_fe')
        currency = self.env.ref('base.EUR')
        currency.l10n_ar_afip_code = '060'
        response = SimpleNamespace(ResultGet=SimpleNamespace(MonCotiz=1200), Errors=None)
        with patch.object(type(journal), '_l10n_ar_call', return_value=response) as request:
            quotes = currency._waiki_fetch_quotes(company)
        self.assertEqual(quotes['EUR'], 1200)
        self.assertEqual(request.call_args.args[0], 'currency_rate')
