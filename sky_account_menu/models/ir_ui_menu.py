from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    def _sky_apply_menu_names(self):
        """Fija en todos los idiomas instalados el nombre en_US definido en views/menus.xml.

        La carga de datos solo escribe en_US y una actualización no sobrescribe traducciones
        existentes (p. ej. «Pagos» en es_AR), así que se replica explícitamente.
        """
        langs = [code for code, _name in self.env["res.lang"].get_installed() if code != "en_US"]
        if not langs:
            return
        xmlids = self.env["ir.model.data"].sudo().search(
            [("module", "=", "sky_account_menu"), ("model", "=", "ir.ui.menu")]
        )
        # Menús propios y menús de otros módulos renombrados aquí (registrados en ir.model.data
        # del módulo origen): se identifican por la lista del propio XML.
        menus = self.browse(xmlids.mapped("res_id")) | self._sky_renamed_menus()
        for menu in menus.with_context(lang="en_US"):
            menu.update_field_translations("name", dict.fromkeys(langs, menu.name))

    @api.model
    def _sky_renamed_menus(self):
        return self.browse(
            self.env.ref(xmlid).id
            for xmlid in (
                "account.menu_action_account_payments_receivable",
                "account.menu_action_account_payments_payable",
                "account_cashbox.menu_pop_dashboard",
                "l10n_latam_check.menu_third_party_check",
                "l10n_latam_check.menu_own_check",
                "account_reconcile_oca.account_account_reconcile_menu",
                "account_statement_import_file.account_statement_import_menu",
                "account.account_reports_management_menu",
                "account_invoice_line_report.menu_action_account_invoice_line_report",
                "product_margin.menu_action_product_margin",
                "l10n_ar_fiscal_ws_reports.menu_account_sale_vat_ledger",
                "l10n_ar_fiscal_ws_reports.menu_account_purchase_vat_ledger",
                "account_payment_pro_receiptbook.menu_receiptbook_form",
                "account_cashbox.menu_account_cashbox",
                "l10n_ar_withholding.menu_action_afip_earnings_table_scale_line",
            )
        )
