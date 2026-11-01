# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.addons.account.models.account_payment import AccountPayment as CorePayment
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestSkyRegistryIsolation(AccountTestInvoicingCommon):
    def test_core_payment_class_is_not_patched(self):
        self.assertEqual(
            CorePayment._compute_available_journal_ids.__module__,
            "odoo.addons.account.models.account_payment",
        )

    def test_journals_follow_each_payment_company_in_a_batch(self):
        other = self.setup_other_company(name="Sky separate legal entity")
        first_company = self.company_data["company"]
        second_company = other["company"]
        payments_model = self.env["account.payment"].with_context(
            allowed_company_ids=[first_company.id, second_company.id]
        )
        first = payments_model.new({"company_id": first_company.id, "payment_type": "inbound"})
        second = payments_model.new({"company_id": second_company.id, "payment_type": "outbound"})
        (first | second)._compute_available_journal_ids()
        self.assertTrue(first.available_journal_ids)
        self.assertTrue(second.available_journal_ids)
        self.assertIn(self.company_data["default_journal_bank"], first.available_journal_ids._origin)
        self.assertIn(other["default_journal_bank"], second.available_journal_ids._origin)
        self.assertNotIn(other["default_journal_bank"], first.available_journal_ids._origin)
        self.assertNotIn(self.company_data["default_journal_bank"], second.available_journal_ids._origin)
