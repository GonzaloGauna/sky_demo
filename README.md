# sky_demo — addons para Odoo 19 Community

Addons del proyecto sky_demo. Cada módulo se encuentra directamente en la raíz
del repositorio; esa raíz debe estar incluida en `addons_path`.

La localización argentina preparada en la rama `migration/argentina-19` incluye:

| Módulo | Función |
| --- | --- |
| `l10n_ar_fiscal_ws` | Facturación electrónica y web services fiscales de ARCA |
| `l10n_ar_ux` | Mejoras de la localización argentina |
| `l10n_ar_tax` | Retenciones y percepciones |
| `account_payment_pro` | Pagos y recibos |
| `account_ux` | Mejoras contables |
| `account_internal_transfer` | Transferencias internas |
| `account_background_post` | Confirmación de asientos en segundo plano |
| `account_view_localization_ar` | Vista de configuración argentina de Waiki |
| `cash_control` | Cajas, arqueos y movimientos de tesorería |
| `partner_debt_info` | Cuenta corriente y saldos por empresa |
| `dolar_update` | Cotizaciones de venta por empresa |
| `waiki_account_followup` | Cobranzas Community, historial y carta |
| `account_tax_settlement` | Liquidaciones contables de impuestos |
| `l10n_ar_account_tax_settlement` | Exportadores argentinos y ajuste por inflación |
| `fix_change_multicompany` | Excepción contable multicompañía opcional |
| `stock_eliminate_restrictions` | Selección logística multicompañía opcional |

[Alcance, pruebas e instalación en sky_demo_ri](docs/argentina19/INSTALACION.md).

Los módulos fiscales y sus dependencias provienen de ramas 19.0 de ADHOC con
adaptaciones propias mediante herencia Odoo. Los commits originales se fijan en
[argentina19_sources.lock.json](docs/argentina19/argentina19_sources.lock.json) y
los cambios están en [argentina19_local_changes.patch](docs/argentina19/argentina19_local_changes.patch).

La validación local inicial abarcó 59 escenarios únicos; las llamadas fiscales se simularon.
El despliegue en el servidor y una autorización real de homologación requieren
validación adicional. No se incluyen certificados ni claves privadas del contribuyente.

## Extensión Waiki completa

La misma rama ahora incluye **todos los módulos de waiki-multicompany y
waikiservicios**: caja, cuenta corriente, cotizaciones, cobranzas Community,
liquidaciones argentinas y excepciones multicompañía opcionales. Son 16 addons
en total. `account_followup` se sustituye por `waiki_account_followup`, una
implementación Community independiente.

[Módulos, diferencias funcionales, pruebas e instalación](docs/waiki19/INSTALACION.md).
[Resultado de pruebas Waiki](docs/waiki19/waiki19_test_report.json).

Esta ampliación validó **69 pruebas únicas**, con cero fallos y cero errores.

Las opciones multicompañía y tareas automáticas quedan desactivadas.
No se migra una base antigua ni se incluyen implementaciones Enterprise.
Los archivos fiscales conservan los layouts históricos recibidos; validar su
aceptación en los aplicativos vigentes antes de utilizarlos para presentar.
