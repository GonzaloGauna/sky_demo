# ruff: noqa: F821  (script para odoo shell: `env` lo inyecta el shell)
"""Ejecutar con odoo shell. Desinstala cash_control (sustituido por account_cashbox) si está instalado."""
assert env.cr.dbname == "sky_demo_ri", "Solo se autoriza sky_demo_ri"
module = env["ir.module.module"].sudo().search([("name", "=", "cash_control"), ("state", "=", "installed")])
if module:
    module.button_immediate_uninstall()
    print("cash_control desinstalado.")
else:
    print("cash_control no estaba instalado.")
