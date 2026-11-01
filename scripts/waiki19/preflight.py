"""Execute with Odoo shell; validates the authorized target without saving data."""
from odoo import release
from odoo.modules.module import get_module_path

assert release.version_info[0] == 19, 'Requires Odoo 19'
assert env.cr.dbname == 'sky_demo_ri', 'Only sky_demo_ri is authorized'
assert env['ir.config_parameter'].sudo().get_param('database.is_neutralized') == 'true', 'Neutralize the copy first'
company = env['res.company'].sudo().browse(2).exists()
assert company and company.chart_template == 'ar_ri', 'Check CLUB company and chart'
for name in ('cash_control', 'dolar_update', 'partner_debt_info', 'waiki_account_followup',
             'account_tax_settlement', 'l10n_ar_account_tax_settlement',
             'fix_change_multicompany', 'stock_eliminate_restrictions'):
    assert get_module_path(name), 'Missing addon: ' + name
legacy = env['ir.module.module'].sudo().search([
    ('name', 'in', ['account_followup', 'l10n_ar_afipws', 'l10n_ar_afipws_fe', 'account_payment_group']),
    ('state', '=', 'installed'),
])
assert not legacy, 'Legacy modules require a separate data-migration review: ' + ', '.join(legacy.mapped('name'))
print('WAIKI_PREFLIGHT_OK: Odoo 19, sky_demo_ri, company 2, ar_ri. No changes saved.')
env.cr.rollback()
