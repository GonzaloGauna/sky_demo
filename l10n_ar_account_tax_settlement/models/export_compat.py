# Copyright 2026 Sky Demo. License LGPL-3.0 or later.
# Typed, read-only adapter for the existing fiscal serializers. No ORM class patching.
from functools import wraps
from types import SimpleNamespace
import re

from odoo import _, fields
from odoo.exceptions import ValidationError
from odoo.orm.models import BaseModel


class ExportRecords:
    def __init__(self, records, source=None):
        self.records = records
        self.source = source

    def __bool__(self):
        return bool(self.records)

    def __len__(self):
        return len(self.records)

    def __eq__(self, other):
        return self.records == (other.records if isinstance(other, ExportRecords) else other)

    def __contains__(self, record):
        return (record.records if isinstance(record, ExportRecords) else record) in self.records

    def __iter__(self):
        for record in self.records:
            source = record if record._name == "account.move.line" and record.tax_line_id else self.source
            yield ExportRecords(record, source)

    def __getitem__(self, key):
        return ExportRecords(self.records[key], self.source)

    def _wrap(self, value):
        return ExportRecords(value, self.source) if isinstance(value, BaseModel) else value

    def _withholding(self):
        payment = self.records if self.records._name == "account.payment" else self.source.payment_id if self.source else self.records.env["account.payment"]
        if not payment or not self.source:
            return self.records.env["l10n_ar.payment.withholding"]
        return payment.l10n_ar_withholding_line_ids.filtered(lambda w: w.tax_id == self.source.tax_line_id)[:1]

    def sorted(self, key=None, reverse=False):
        if callable(key):
            records = self.records.sorted(lambda r: key(ExportRecords(r, r if r._name == "account.move.line" and r.tax_line_id else self.source)), reverse=reverse)
        else:
            records = self.records.sorted(key, reverse=reverse)
        return ExportRecords(records, self.source)

    def filtered(self, predicate):
        if callable(predicate):
            return ExportRecords(self.records.filtered(lambda r: predicate(ExportRecords(r, self.source))), self.source)
        return ExportRecords(self.records.filtered(predicate), self.source)

    def mapped(self, path):
        if callable(path):
            return [path(record) for record in self]
        values = list(self)
        for name in path.split("."):
            next_values = []
            for value in values:
                value = getattr(value, name)
                next_values.extend(value if isinstance(value, ExportRecords) else [value])
            values = next_values
        if values and all(isinstance(value, ExportRecords) for value in values):
            records = values[0].records.browse()
            for value in values:
                records |= value.records
            return ExportRecords(records, self.source)
        return values

    def __getattr__(self, name):
        record = self.records
        if record._name == "account.payment":
            withholding = self._withholding()
            if name in ("payment_group_id", "payment_ids"):
                return self
            if name in ("withholding_number", "name") and withholding:
                return withholding.name or record.name
            if name in ("withholdable_base_amount", "withholding_base_amount"):
                if not withholding:
                    raise ValidationError(_("The payment has no withholding line for this tax."))
                return withholding.base_amount
            if name in ("amount", "computed_withholding_amount") and self.source:
                return abs(self.source.balance) if record == self.source.payment_id else withholding.amount
            if name == "payments_amount":
                # The filing uses company currency and the historical posted
                # counterpart, including withholdings, rather than today's rate.
                counterpart = record.move_id.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
                return abs(sum(counterpart.mapped('balance')))
            if name == "payment_date":
                return record.date
            if name == "tax_withholding_id":
                return ExportRecords(withholding.tax_id, self.source)
            if name == "regimen_ganancias_id":
                code = self.source.tax_line_id.codigo_regimen or self.source.tax_line_id.l10n_ar_code
                return SimpleNamespace(codigo_de_regimen=code) if code else False
        if record._name == "account.move":
            if name == "type":
                return record.move_type
            if name in ("document_number", "l10n_latam_document_number"):
                return record.l10n_latam_document_number or (ExportRecords(record.origin_payment_id, self.source).withholding_number if record.origin_payment_id and self.source else record.name)
            if name == "payment_group_ids":
                return ExportRecords(record.reconciled_payment_ids | record.matched_payment_ids, self.source)
            if name == "_found_related_invoice":
                return lambda: ExportRecords(record.reversed_entry_id or record.debit_origin_id, self.source)
            if name == "_l10n_ar_get_document_number_parts":
                def number_parts(number, code=None):
                    parts = str(number or "").split("-")
                    return {"point_of_sale": int(re.sub(r"\D", "", parts[0]) or 0) if len(parts) > 1 else 0, "invoice_number": int(re.sub(r"\D", "", parts[-1]) or 0)}
                return number_parts
            if name == "_l10n_ar_get_amounts":
                def amounts(company_currency=False):
                    values = record._l10n_ar_get_amounts(base_lines=record._get_rounded_base_and_tax_lines()[0])
                    if company_currency and record.currency_id != record.company_id.currency_id:
                        if not record.invoice_currency_rate:
                            raise ValidationError(_("The invoice has no historical currency rate."))
                        values = {key: record.company_id.currency_id.round(value / record.invoice_currency_rate) for key, value in values.items()}
                    return values
                return amounts
        if record._name == "account.move.line":
            if name == "l10n_latam_document_type_id":
                return ExportRecords(record.move_id.l10n_latam_document_type_id, self.source)
        if record._name == "account.tax":
            if name == "type_tax_use":
                return record.l10n_ar_withholding_payment_type or record.type_tax_use
            if name in ("amount_type", "withholding_type"):
                return "partner_tax"  # Existing serializers branch by invoice/payment tax, not the calculation engine.
            if name == "get_partner_alicuot":
                return lambda partner, date: self._aliquot(partner.records if isinstance(partner, ExportRecords) else partner, date)
            if name == "_get_rule":
                return lambda payment: SimpleNamespace(percentage=(self._withholding().amount / self._withholding().base_amount if self._withholding() and self._withholding().base_amount else record.amount / 100))
        value = getattr(record, name)
        if callable(value):
            def call(*args, **kwargs):
                args = tuple(a.records if isinstance(a, ExportRecords) else a for a in args)
                kwargs = {key: value.records if isinstance(value, ExportRecords) else value for key, value in kwargs.items()}
                return self._wrap(value(*args, **kwargs))
            return call
        return self._wrap(value)

    def _aliquot(self, partner, date):
        tax = self.records
        date = fields.Date.to_date(date)
        # The partner's withholding One2many deliberately excludes perceptions.
        # Search the native model so provincial export metadata works for both.
        entries = tax.env['l10n_ar.partner.tax'].search([
            ('partner_id', '=', partner.commercial_partner_id.id),
            ('company_id', '=', tax.company_id.id),
            ('tax_id.tax_group_id', '=', tax.tax_group_id.id),
            ('tax_id.l10n_ar_state_id', '=', tax.l10n_ar_state_id.id),
            ('tax_id.l10n_ar_withholding_payment_type', '=', tax.l10n_ar_withholding_payment_type),
            '|', ('from_date', '=', False), ('from_date', '<=', date),
            '|', ('to_date', '=', False), ('to_date', '>=', date),
        ])
        selected = entries[:1]
        effective_tax = selected.tax_id or tax
        values = {"alicuota_retencion": abs(effective_tax.amount), "alicuota_percepcion": abs(effective_tax.amount)}
        if self.source:
            withholding = self._withholding()
            base = withholding.base_amount if withholding else self.source.tax_base_amount
            if base:
                percentage = abs(self.source.balance / base) * 100
                values.update(alicuota_retencion=percentage, alicuota_percepcion=percentage)
        for name in ("regimen_retencion", "regimen_percepcion", "api_articulo_inciso_calculo_retencion", "api_codigo_articulo_retencion", "api_articulo_inciso_calculo_percepcion", "api_codigo_articulo_percepcion"):
            values[name] = (selected[name] if selected else False) or tax[name] or ""
        return SimpleNamespace(**values)


def legacy_export(method):
    @wraps(method)
    def adapted(self, lines, *args, **kwargs):
        raw = lines.records if isinstance(lines, ExportRecords) else lines
        raw.check_access("read")
        if not raw or any(line.company_id != self.company_id or line.parent_state != "posted" or not line.tax_line_id for line in raw):
            raise ValidationError(_("Fiscal exports require posted tax lines from the journal company."))
        return method(self, lines if isinstance(lines, ExportRecords) else ExportRecords(lines), *args, **kwargs)
    return adapted
