from odoo import api, models

# Única fuente de los nombres de menús de OTROS módulos que se renombran.
# (La posición —padre y secuencia— se define en views/menus.xml; los menús propios llevan su nombre allí.)
MENU_NAMES = {
    "account.menu_action_account_payments_receivable": "Recibos de clientes",
    "account.menu_action_account_payments_payable": "Pagos a proveedores",
    "account_cashbox.menu_pop_dashboard": "Cajas",
    "l10n_latam_check.menu_third_party_check": "Cheques de terceros",
    "l10n_latam_check.menu_own_check": "Cheques propios",
    "account_reconcile_oca.account_account_reconcile_menu": "Conciliar",
    "account_statement_import_file.account_statement_import_menu": "Importar extracto",
    "account.account_reports_management_menu": "Administración",
    "account_invoice_line_report.menu_action_account_invoice_line_report": "Análisis de líneas de factura",
    "product_margin.menu_action_product_margin": "Márgenes de producto",
    "l10n_ar_fiscal_ws_reports.menu_account_sale_vat_ledger": "Libro IVA Ventas",
    "l10n_ar_fiscal_ws_reports.menu_account_purchase_vat_ledger": "Libro IVA Compras",
    "account_payment_pro_receiptbook.menu_receiptbook_form": "Talonarios de recibos",
    "account_cashbox.menu_account_cashbox": "Gestión de cajas",
    "l10n_ar_withholding.menu_action_afip_earnings_table_scale_line": "Alícuotas y montos Ganancias",
}


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    def _sky_apply_menu_names(self):
        """Aplica los nombres pedidos por el cliente en en_US y en todos los idiomas instalados.

        Se ejecuta en cada instalación/actualización (<function> en views/menus.xml). La carga de datos
        solo escribe en_US y una actualización no sobrescribe traducciones existentes (p. ej. «Pagos» en
        es_AR), por eso se escribe cada idioma explícitamente. Nota: reemplaza cualquier renombrado manual
        de estos menús hecho desde la interfaz.
        """
        langs = [code for code, _name in self.env["res.lang"].get_installed() if code != "en_US"]
        for xmlid, name in MENU_NAMES.items():
            menu = self.env.ref(xmlid).with_context(lang="en_US")
            menu.name = name
            if langs:
                menu.update_field_translations("name", dict.fromkeys(langs, name))
        # Menús propios: el nombre está en el XML (en_US); se replica a los demás idiomas.
        own = self.env["ir.model.data"].search([("module", "=", "sky_account_menu"), ("model", "=", "ir.ui.menu")])
        if langs:
            for menu in self.browse(own.mapped("res_id")).with_context(lang="en_US"):
                menu.update_field_translations("name", dict.fromkeys(langs, menu.name))
