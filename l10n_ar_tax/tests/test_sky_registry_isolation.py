# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.addons.l10n_ar_withholding.models.account_payment import AccountPayment as CoreWithholdingPayment
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSkyWithholdingRegistryIsolation(TransactionCase):
    def test_standard_withholding_class_is_not_patched(self):
        self.assertEqual(
            CoreWithholdingPayment._synchronize_to_moves.__module__,
            "odoo.addons.l10n_ar_withholding.models.account_payment",
        )
