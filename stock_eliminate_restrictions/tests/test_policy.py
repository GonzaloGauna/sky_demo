from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestWaikiStockPolicy(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(su=True)
        cls.other = cls.setup_other_company(name='Other stock policy company')
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.other['company'].id)], limit=1)

    def _move(self, selected=True):
        companies = (self.env.company | self.other['company']).ids if selected else self.env.company.ids
        return self.env['stock.move'].with_context(allowed_company_ids=companies).new({'company_id': self.env.company.id, 'location_id': self.warehouse.lot_stock_id.id, 'location_dest_id': self.env.ref('stock.stock_location_customers').id})

    def test_stock_checks_remain_default(self):
        self.assertFalse(self.env.company.waiki_allow_cross_company_stock)
        with self.assertRaises(UserError):
            self._move()._check_company(['location_id'])

    def test_opt_in_stock_links_are_limited_to_selected_companies(self):
        self.env.company.waiki_allow_cross_company_stock = True
        self._move()._check_company(['location_id'])
        with self.assertRaises(ValidationError):
            self._move(selected=False)._check_company(['location_id'])

    def test_no_retired_valuation_layer_model_required(self):
        self.assertIn('value', self.env['stock.move']._fields)
        self.assertNotIn('stock.valuation.layer', self.env)

    def test_opt_in_does_not_change_default_receipt_company(self):
        company = self.other['company']
        company.waiki_allow_cross_company_stock = True
        model = self.env['purchase.order'].with_context(allowed_company_ids=(self.env.company | company).ids)
        self.assertEqual(model._get_picking_type(company.id).company_id, company)

    def test_order_selectors_expand_only_with_explicit_opt_in(self):
        company = self.env.company
        selected = company | self.other['company']
        for name in ('sale.order', 'purchase.order'):
            order = self.env[name].with_context(allowed_company_ids=selected.ids).create({'company_id': company.id, 'partner_id': self.partner_a.id})
            self.assertEqual(order.waiki_stock_company_ids, company)
            company.waiki_allow_cross_company_stock = True
            self.assertEqual(order.waiki_stock_company_ids, selected)
            company.waiki_allow_cross_company_stock = False
