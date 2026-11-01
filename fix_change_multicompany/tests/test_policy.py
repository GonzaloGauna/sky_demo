from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.tests import tagged, new_test_user


@tagged('post_install', '-at_install')
class TestWaikiAccountingPolicy(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(su=True)
        cls.other = cls.setup_other_company(name='Other accounting policy company')

    def _move(self, selected=True):
        companies = (self.env.company | self.other['company']).ids if selected else self.env.company.ids
        return self.env['account.move'].with_context(allowed_company_ids=companies).new({'company_id': self.env.company.id, 'journal_id': self.other['default_journal_misc'].id})

    def test_native_company_checks_remain_default(self):
        self.assertFalse(self.env.company.waiki_allow_cross_company_accounting)
        with self.assertRaises(UserError):
            self._move()._check_company(['journal_id'])

    def test_opt_in_requires_both_companies_selected(self):
        self.env.company.waiki_allow_cross_company_accounting = True
        self._move()._check_company(['journal_id'])
        with self.assertRaises(ValidationError):
            self._move(selected=False)._check_company(['journal_id'])

    def test_accountant_cannot_enable_policy(self):
        user = new_test_user(self.env, login='waiki_policy_user', groups='account.group_account_manager')
        with self.assertRaises(AccessError):
            self.env.company.with_user(user).write({'waiki_allow_cross_company_accounting': True})
