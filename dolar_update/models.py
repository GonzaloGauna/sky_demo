# License AGPL-3.0 or later. Migration of Waiki's currency updater.
import logging
import math
import re

import requests
from lxml import html
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)
BNA_URL = "https://www.bna.com.ar/Personas"
DOLARAPI_URL = "https://dolarapi.com/v1/"


def parse_bna_quotes(content):
    """Read official banknote selling quotations, not derivatives or buying rates."""
    document = html.fromstring(content)
    quotes = {"ARS": 1.0}
    for row in document.xpath("//tr"):
        cells = [" ".join(cell.itertext()).strip() for cell in row.xpath("./td")]
        if len(cells) < 3:
            continue
        label = re.sub(r"\s+", " ", cells[0]).lower()
        code = "USD" if label.startswith(("dolar u.s.a", "dólar u.s.a")) else "EUR" if label == "euro" else None
        if code and code not in quotes:
            number = re.sub(r"[^0-9,.]", "", cells[2]).replace(".", "").replace(",", ".")
            if number:
                quotes[code] = float(number)
    if not {"USD", "EUR"}.issubset(quotes) or any(value <= 0 for value in quotes.values()):
        raise UserError(_("BNA did not return valid USD and EUR selling rates. No rates were changed."))
    return quotes


class ResCompany(models.Model):
    _inherit = "res.company"

    dolar_update_type = fields.Selection([("afip", "ARCA"), ("bna", "Banco Nacion (billetes venta)"), ("dolarapi", "DolarAPI (informal/financial quotes)")], string="Waiki rate provider")
    waiki_rate_journal_id = fields.Many2one("account.journal", check_company=True, domain="[('company_id', '=', id), ('type', '=', 'sale')]", string="ARCA quotation journal")


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    dolar_update_type = fields.Selection(related="company_id.dolar_update_type", readonly=False)
    waiki_rate_journal_id = fields.Many2one(related="company_id.waiki_rate_journal_id", readonly=False, domain="[('company_id','=',company_id)]")


class ResCurrency(models.Model):
    _inherit = "res.currency"

    def _waiki_fetch_quotes(self, company):
        provider = company.dolar_update_type
        if provider == "bna":
            try:
                response = requests.get(BNA_URL, timeout=20)
                response.raise_for_status()
                return parse_bna_quotes(response.content)
            except requests.RequestException as error:
                raise UserError(_("Unable to read BNA quotations: %s", error)) from error
        quotes = {"ARS": 1.0}
        currencies = self | company.currency_id
        if provider == "afip":
            journal = company.waiki_rate_journal_id
            if not journal or not journal.l10n_ar_fiscal_ws_id or journal.company_id != company:
                raise UserError(_("Configure a fiscal journal for this company's ARCA quotation requests."))
            for currency in currencies.filtered(lambda c: c.name != "ARS"):
                if not currency.l10n_ar_afip_code:
                    raise UserError(_("Currency %s has no ARCA code.", currency.name))
                response = journal._l10n_ar_call("currency_rate", {"currency_code": currency.l10n_ar_afip_code})
                errors = getattr(getattr(response, "Errors", None), "Err", []) or []
                if errors:
                    raise UserError("\n".join(str(error.Msg) for error in errors))
                quotes[currency.name] = float(response.ResultGet.MonCotiz)
            return quotes
        if provider == "dolarapi":
            routes = {"USD": "dolares/oficial", "EUR": "cotizaciones/eur", "BLU": "dolares/blue", "CCL": "dolares/contadoconliqui", "MEP": "dolares/bolsa", "UST": "dolares/cripto"}
            for currency in currencies.filtered(lambda c: c.name != "ARS"):
                if currency.name not in routes:
                    raise UserError(_("DolarAPI is not configured for %s.", currency.name))
                try:
                    response = requests.get(DOLARAPI_URL + routes[currency.name], timeout=20)
                    response.raise_for_status()
                    quotes[currency.name] = float(response.json()["venta"])
                except (requests.RequestException, ValueError, KeyError, TypeError) as error:
                    raise UserError(_("Unable to read the quotation for %s.", currency.name)) from error
            return quotes
        raise UserError(_("Select a Waiki currency provider for this company."))

    def _waiki_update_for_company(self, company):
        currencies = self.filtered(lambda c: c.active and c != company.currency_id)
        if company.dolar_update_type == "bna":
            currencies = currencies.filtered(lambda c: c.name in ("USD", "EUR"))
        if not currencies:
            return 0
        quotes = currencies.with_company(company)._waiki_fetch_quotes(company)
        base = quotes.get(company.currency_id.name)
        if not base or not math.isfinite(base) or base <= 0:
            raise UserError(_("The provider has no valid quote for the company currency."))
        planned = []
        for currency in currencies:
            quote = quotes.get(currency.name)
            if not quote or not math.isfinite(quote) or quote <= 0:
                raise UserError(_("Invalid quotation for %s. No rates were changed.", currency.name))
            planned.append((currency, quote / base))
        today = fields.Date.context_today(self)
        rates = self.env["res.currency.rate"].with_company(company)
        for currency, quotation in planned:
            rate = rates.search([("company_id", "=", company.id), ("currency_id", "=", currency.id), ("name", "=", today)], limit=1)
            values = {"inverse_company_rate": quotation}
            if rate:
                rate.write(values)
            else:
                rates.create(dict(values, company_id=company.id, currency_id=currency.id, name=today))
        return len(planned)

    def update_dolar_button(self):
        if not self.env.user.has_group("account.group_account_manager"):
            raise UserError(_("Only accounting managers can update quotations."))
        count = self._waiki_update_for_company(self.env.company)
        return {"type": "ir.actions.client", "tag": "display_notification", "params": {"message": _("Updated %s quotations.", count), "type": "success"}}

    @api.model
    def update_dolar(self):
        # Disabled by default; a failing provider must not corrupt other companies.
        for company in self.env["res.company"].search([("dolar_update_type", "!=", False)]):
            try:
                with self.env.cr.savepoint():
                    self.search([]).with_company(company)._waiki_update_for_company(company)
            except UserError as error:
                _logger.warning("Waiki quotation update failed for company %s: %s", company.id, error)
