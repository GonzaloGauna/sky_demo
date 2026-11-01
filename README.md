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

[Alcance, pruebas e instalación en sky_demo_ri](docs/argentina19/INSTALACION.md).

Los módulos fiscales y sus dependencias provienen de ramas 19.0 de ADHOC con
adaptaciones propias mediante herencia Odoo. Los commits originales se fijan en
[argentina19_sources.lock.json](docs/argentina19/argentina19_sources.lock.json) y
los cambios están en [argentina19_local_changes.patch](docs/argentina19/argentina19_local_changes.patch).

La validación local abarcó 59 escenarios únicos; las llamadas fiscales se simularon.
El despliegue en el servidor y una autorización real de homologación requieren
validación adicional. No se incluyen certificados ni claves privadas del contribuyente.
