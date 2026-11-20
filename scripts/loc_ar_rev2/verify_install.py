"""Verifica la instalación y deja la copia autorizada en homologación y sin tareas de negocio."""
import json
from pathlib import Path

from odoo.modules.module import get_module_path

assert env.cr.dbname == "sky_demo_ri", "Solo se autoriza sky_demo_ri"
parameters = env["ir.config_parameter"].sudo()
assert parameters.get_param("database.is_neutralized") == "true"
names = json.loads((Path(get_module_path("sky_account_menu")).parent / "docs/loc_ar_rev2/modules.json").read_text())
states = {m.name: m.state for m in env["ir.module.module"].sudo().search([("name", "in", names + ["cash_control"])])}
missing = [name for name in names if states.get(name) != "installed"]
assert not missing, "Módulos no instalados: " + ", ".join(missing)
assert states.get("cash_control", "uninstalled") != "installed", "cash_control sigue instalado"
parameters.set_param("l10n_ar_fiscal_ws.env_type", "homologation")
maintenance = env.ref("base.autovacuum_job", raise_if_not_found=False)
env["ir.cron"].sudo().with_context(active_test=False).search([
    ("id", "not in", maintenance.ids if maintenance else []),
]).write({"active": False})
assert env["res.company"]._get_environment_type() == "homologation"
env.cr.commit()
print("LOC_AR_REV2_OK: %s/%s módulos instalados; cash_control retirado; ARCA en homologación; crons desactivados."
      % (len(names), len(names)))
