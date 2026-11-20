import ast

from odoo.tests import TransactionCase, tagged

from ..models.ir_ui_menu import MENU_NAMES

# (xml id del menú, xml id del padre esperado, nombre esperado)
EXPECTED = [
    ("account.menu_action_account_payments_receivable", "account.menu_finance_receivables", "Recibos de clientes"),
    ("account.menu_action_account_payments_payable", "account.menu_finance_payables", "Pagos a proveedores"),
    ("account_cashbox.menu_pop_dashboard", "account_internal_transfer.menu_finance_bank_and_cash", "Cajas"),
    ("sky_account_menu.menu_cashbox_sessions", "account_internal_transfer.menu_finance_bank_and_cash", "Sesiones"),
    ("l10n_latam_check.menu_third_party_check", "account_internal_transfer.menu_finance_bank_and_cash",
     "Cheques de terceros"),
    ("l10n_latam_check.menu_own_check", "account_internal_transfer.menu_finance_bank_and_cash", "Cheques propios"),
    ("sky_account_menu.menu_accounting_actions", "account.menu_finance_entries", "Acciones"),
    ("account_reconcile_oca.account_account_reconcile_menu", "sky_account_menu.menu_accounting_actions", "Conciliar"),
    ("account_statement_import_file.account_statement_import_menu", "sky_account_menu.menu_accounting_actions",
     "Importar extracto"),
    ("account.account_reports_management_menu", "account.menu_finance_reports", "Administración"),
    ("account_invoice_line_report.menu_action_account_invoice_line_report", "account.account_reports_management_menu",
     "Análisis de líneas de factura"),
    ("product_margin.menu_action_product_margin", "account.account_reports_management_menu", "Márgenes de producto"),
    ("l10n_ar_fiscal_ws_reports.menu_account_sale_vat_ledger", "l10n_ar.account_reports_ar_statements_menu",
     "Libro IVA Ventas"),
    ("l10n_ar_fiscal_ws_reports.menu_account_purchase_vat_ledger", "l10n_ar.account_reports_ar_statements_menu",
     "Libro IVA Compras"),
    ("sky_account_menu.menu_config_payments", "account.menu_finance_configuration", "Pagos"),
    ("sky_account_menu.menu_withholding_tax", "sky_account_menu.menu_config_payments", "Impuestos de retención"),
    ("account_payment_pro_receiptbook.menu_receiptbook_form", "sky_account_menu.menu_config_payments",
     "Talonarios de recibos"),
    ("account_cashbox.menu_account_cashbox", "sky_account_menu.menu_config_payments", "Gestión de cajas"),
    ("l10n_ar_withholding.menu_action_afip_earnings_table_scale_line", "l10n_ar.menu_afip_config",
     "Alícuotas y montos Ganancias"),
]

BANK_AND_CASH_ORDER = [
    "account_cashbox.menu_pop_dashboard",
    "sky_account_menu.menu_cashbox_sessions",
    "l10n_latam_check.menu_third_party_check",
    "l10n_latam_check.menu_own_check",
    "account_internal_transfer.menu_action_account_payments_transfer",
]


@tagged("post_install", "-at_install")
class TestSkyAccountMenu(TransactionCase):
    def test_menu_structure(self):
        """Cada menú pedido por el cliente cuelga del padre correcto y con el nombre acordado."""
        for menu_xmlid, parent_xmlid, name in EXPECTED:
            with self.subTest(menu=menu_xmlid):
                menu = self.env.ref(menu_xmlid)
                self.assertEqual(menu.parent_id, self.env.ref(parent_xmlid))
                for lang in ("en_US", "es_AR"):
                    self.assertEqual(menu.with_context(lang=lang).name, name, lang)

    def test_bank_and_cash_order(self):
        """Banco y Caja: Cajas, Sesiones, Cheques de terceros, Cheques propios, Transferencias."""
        menus = [self.env.ref(x) for x in BANK_AND_CASH_ORDER]
        self.assertEqual([m.sequence for m in menus], sorted(m.sequence for m in menus))
        self.assertEqual(len({m.sequence for m in menus}), len(menus))

    def test_menu_actions_load(self):
        """Las acciones de los menús movidos o nuevos se pueden abrir (modelo y vista existen)."""
        for menu_xmlid, _parent, _name in EXPECTED:
            menu = self.env.ref(menu_xmlid)
            if not menu.action or menu.action._name != "ir.actions.act_window":
                continue
            with self.subTest(menu=menu_xmlid):
                action = menu.action
                model = self.env[action.res_model]
                view_type = action.view_mode.split(",")[0]
                model.get_views([(False, view_type)])

    def test_withholding_tax_action(self):
        """«Impuestos de retención» solo devuelve impuestos de retención."""
        action = self.env.ref("sky_account_menu.action_withholding_tax")
        domain = ast.literal_eval(action.domain)
        taxes = self.env["account.tax"].with_context(active_test=False).search(domain)
        self.assertTrue(all(taxes.mapped("l10n_ar_withholding_payment_type")))
        others = self.env["account.tax"].with_context(active_test=False).search(
            [("l10n_ar_withholding_payment_type", "=", False)], limit=1
        )
        self.assertNotIn(others, taxes)

    def test_menu_names_single_source(self):
        """Todo menú ajeno renombrado está en MENU_NAMES (única fuente) y con el nombre de la spec."""
        foreign = {x: name for x, _parent, name in EXPECTED if not x.startswith("sky_account_menu.")}
        self.assertEqual(MENU_NAMES, foreign)
