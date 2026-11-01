"""Disable future demo loading on the authorized copy, preserving business data."""
from odoo import release


def disable_future_demo(env):
    modules = env['ir.module.module'].sudo().with_context(active_test=False).search([('demo', '=', True)])
    count = len(modules)
    modules.write({'demo': False})
    env.flush_all()
    assert not env['ir.module.module'].sudo().with_context(active_test=False).search_count([('demo', '=', True)])
    return count


def prepare(env):
    assert env.cr.dbname == 'sky_demo_ri', 'Only sky_demo_ri is authorized'
    assert release.version_info[0] == 19, 'Requires Odoo 19'
    parameters = env['ir.config_parameter'].sudo()
    assert parameters.get_param('database.is_neutralized') == 'true', 'Neutralize the copy first'
    company = env['res.company'].sudo().browse(2).exists()
    assert company and company.chart_template == 'ar_ri', 'Check CLUB company and chart'
    count = disable_future_demo(env)
    parameters.set_param('l10n_ar_fiscal_ws.env_type', 'homologation')
    env.cr.commit()
    print('WAIKI_NO_DEMO_OK: disabled future demo loading for %s module flags.' % count)
    print('Existing demo and business records were preserved. ARCA: homologation.')


if 'env' in globals():
    prepare(env)
