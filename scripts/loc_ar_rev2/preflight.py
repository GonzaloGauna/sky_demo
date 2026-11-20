# ruff: noqa: F821  (script para odoo shell: `env` lo inyecta el shell)
"""Ejecutar con odoo shell. Valida la copia autorizada sin guardar cambios."""
import json
from pathlib import Path

from odoo import release
from odoo.modules.module import get_module_path

assert release.version_info[0] == 19, "Requiere Odoo 19"
assert env.cr.dbname == "sky_demo_ri", "Solo se autoriza sky_demo_ri"
assert env["ir.config_parameter"].sudo().get_param("database.is_neutralized") == "true", "Neutralizar la copia antes"
company = env["res.company"].sudo().browse(2).exists()
assert company and company.chart_template == "ar_ri", "Revisar empresa CLUB y plan contable"
names = json.loads((Path(get_module_path("sky_account_menu")).parent / "docs/loc_ar_rev2/modules.json").read_text())
missing = [name for name in names if not get_module_path(name)]
assert not missing, "Faltan addons en addons_path: " + ", ".join(missing)
cash_control_module = env["ir.module.module"].sudo().search([("name", "=", "cash_control"), ("state", "=", "installed")])
if cash_control_module:
    # Por SQL: tras el git pull el código de cash_control ya no existe y sus modelos no están en el registro.
    counts = []
    for table in ("pop_config", "pop_session"):
        env.cr.execute("SELECT to_regclass(%s) IS NOT NULL", (table,))
        if env.cr.fetchone()[0]:
            env.cr.execute(f"SELECT count(*) FROM {table}")  # nombre fijo de la tupla anterior
            counts.append(env.cr.fetchone()[0])
        else:
            counts.append(0)
    configs, open_sessions = counts
    assert not open_sessions and not configs, (
        "cash_control tiene %s cajas y %s sesiones: revisar migración de datos antes de desinstalar" % (configs, open_sessions)
    )
assert not env["ir.module.module"].sudo().with_context(active_test=False).search_count([("demo", "=", True)]), (
    "Ejecutar antes scripts/waiki19/prepare_no_demo.py"
)
print("LOC_AR_REV2_PREFLIGHT_OK: Odoo 19, sky_demo_ri, empresa 2, ar_ri, %s módulos disponibles." % len(names))
env.cr.rollback()
