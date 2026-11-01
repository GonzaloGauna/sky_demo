"""Finalize only the authorized neutralized copy after installation."""
assert env.cr.dbname == "sky_demo_ri"
parameters = env["ir.config_parameter"].sudo()
assert parameters.get_param("database.is_neutralized") == "true"
modules = [
    "l10n_ar_fiscal_ws", "account_internal_transfer", "l10n_ar_ux",
    "account_background_post", "account_ux", "account_payment_pro",
    "l10n_ar_tax", "account_view_localization_ar",
]
for name in modules:
    module = env["ir.module.module"].sudo().search([("name", "=", name)])
    assert module.state == "installed", name
parameters.set_param("l10n_ar_fiscal_ws.env_type", "homologation")
maintenance = env.ref("base.autovacuum_job", raise_if_not_found=False)
env["ir.cron"].sudo().with_context(active_test=False).search([
    ("id", "not in", maintenance.ids if maintenance else []),
]).write({"active": False})
company = env["res.company"].sudo().browse(2).exists()
assert company and company.chart_template == "ar_ri"
assert company.l10n_ar_afip_responsibility_type_id.code == "1"
assert env["res.company"]._get_environment_type() == "homologation"
env.cr.commit()
print("INSTALACION_OK: ocho modulos instalados en sky_demo_ri.")
print("ARCA: homologacion. Tareas de negocio desactivadas.")
print("Pendiente: certificados de homologacion, punto de venta fiscal y prueba real de CAE.")
