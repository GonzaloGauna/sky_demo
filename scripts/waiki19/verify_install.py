"""Verify the complete installation and keep the authorized copy in homologation."""
import json
from odoo.modules.module import get_module_path

assert env.cr.dbname == 'sky_demo_ri', 'Only sky_demo_ri is authorized'
parameters = env['ir.config_parameter'].sudo()
assert parameters.get_param('database.is_neutralized') == 'true'
company = env['res.company'].sudo().browse(2).exists()
assert company and company.chart_template == 'ar_ri'
assert company.l10n_ar_afip_responsibility_type_id.code == '1'
module_path = get_module_path('cash_control')
from pathlib import Path
with (Path(module_path).parent / 'docs/waiki19/waiki19_all_modules.json').open() as file:
    names = json.load(file)
states = {module.name: module.state for module in env['ir.module.module'].sudo().search([('name', 'in', names)])}
missing = [name for name in names if states.get(name) != 'installed']
assert not missing, 'Modules not installed: ' + ', '.join(missing)
assert not env['ir.module.module'].sudo().with_context(active_test=False).search_count([('demo', '=', True)])
parameters.set_param('l10n_ar_fiscal_ws.env_type', 'homologation')
maintenance = env.ref('base.autovacuum_job', raise_if_not_found=False)
env['ir.cron'].sudo().with_context(active_test=False).search([
    ('id', 'not in', maintenance.ids if maintenance else []),
]).write({'active': False})
assert env['res.company']._get_environment_type() == 'homologation'
env.cr.commit()
for name in names:
    print(name + ' => ' + states[name])
print('WAIKI_OK: %s/%s modules installed; homologation; business cron jobs disabled.' % (len(names), len(names)))
