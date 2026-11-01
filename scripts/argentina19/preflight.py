"""Run through the server's Odoo shell, before installing anything."""
import importlib
from odoo import release
from odoo.modules.module import get_module_path

assert release.version_info[0] == 19, "Requires Odoo 19"
assert env.cr.dbname == "sky_demo_ri", "Only sky_demo_ri is authorized"
assert env["ir.config_parameter"].sudo().get_param("database.is_neutralized") == "true"
company = env["res.company"].sudo().browse(2).exists()
assert company and company.chart_template == "ar_ri"
assert not env["account.move"].sudo().search_count([("company_id", "=", company.id)])
assert not env["pos.session"].sudo().search_count([("company_id", "=", company.id)])
for name in ("l10n_ar_withholding", "l10n_latam_check", "account_debit_note"):
    assert get_module_path(name), "Server core dependency missing: " + name
for name in ("cryptography", "zeep", "requests", "lxml", "dateutil", "pytz"):
    importlib.import_module(name)
legacy = env["ir.module.module"].sudo().search([
    ("name", "in", ["l10n_ar_afipws", "l10n_ar_afipws_fe", "account_payment_group"]),
    ("state", "=", "installed"),
])
assert not legacy, "Legacy modules already installed: " + ", ".join(legacy.mapped("name"))
print("PREFLIGHT_OK: Odoo 19 Community, sky_demo_ri, empresa 2, ar_ri.")
env.cr.rollback()
