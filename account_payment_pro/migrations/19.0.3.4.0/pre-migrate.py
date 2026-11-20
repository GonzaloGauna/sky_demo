"""Pre-migración propia (Avanx, loc_ar_rev2) de account_payment_pro 19.0.3.3.0 → 19.0.3.4.0.

La 3.4.0 elimina el campo `account.payment.reconcile_on_company_currency`, pero la vista heredada
`latam_check_view_account_payment_form_inherited` que queda en la BD (versión 3.3.0) todavía lo usa. Al
actualizar, Odoo valida la vista principal del mismo archivo XML antes de reescribir la heredada y la
actualización falla con «El campo "reconcile_on_company_currency" no existe en el modelo "account.payment"».

ADHOC no incluye migración para esto. Se quitan del arch guardado las dos referencias (el <field> invisible y
el dominio condicional); a continuación la carga del XML reescribe la vista con la versión 3.4.0.
"""

import json
import logging
import re

_logger = logging.getLogger(__name__)

_FIELD_RE = re.compile(r'\s*<field name="reconcile_on_company_currency"[^>]*/>')
_DOMAIN_RE = re.compile(r'\s*domain="[^"]*if reconcile_on_company_currency else \[\]"')


def migrate(cr, version):
    cr.execute(
        """
        SELECT v.id, v.arch_db
          FROM ir_ui_view v
          JOIN ir_model_data d ON d.model = 'ir.ui.view' AND d.res_id = v.id
         WHERE d.module = 'account_payment_pro'
           AND d.name = 'latam_check_view_account_payment_form_inherited'
        """
    )
    for view_id, arch in cr.fetchall():
        if not arch:
            continue
        cleaned = {lang: _DOMAIN_RE.sub("", _FIELD_RE.sub("", value)) for lang, value in arch.items()}
        if cleaned != arch:
            cr.execute("UPDATE ir_ui_view SET arch_db = %s WHERE id = %s", (json.dumps(cleaned), view_id))
            _logger.info("account_payment_pro: quitadas referencias a reconcile_on_company_currency de la vista %s", view_id)
