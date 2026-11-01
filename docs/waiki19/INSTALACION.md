# Waiki en sky_demo — Odoo 19 Community

Esta entrega amplía la localización argentina a todos los módulos encontrados en
`waiki-multicompany` y `waikiservicios`. Se instala en **sky_demo_ri**; no convierte
una base de Odoo 13/15/16 ni importa sus movimientos, certificados o configuración.
Los originales se conservan sin cambios.

| Original | Módulo para Odoo 19 | Adaptación |
| --- | --- | --- |
| account_view_localization_ar | account_view_localization_ar | Vista de configuración argentina, incluida en la primera entrega |
| cash_control | cash_control | Cajas, apertura/cierre contado, movimientos manuales y pagos; reversión mediante movimientos compensatorios |
| dolar_update | dolar_update | Cotizaciones de venta BNA, ARCA mediante el servicio fiscal actual y DolarAPI opcional; cotización por empresa e idempotente por fecha |
| partner_debt_info | partner_debt_info | Cuenta corriente sobre apuntes publicados, saldo acumulado y última fecha; empresa activa y moneda de esa empresa |
| account_followup | **waiki_account_followup** | Implementación Community independiente: niveles, pausas, actividades, correo/SMS nativos, historial y carta PDF |
| account_tax_settlement | account_tax_settlement | Liquidaciones de impuestos, borradores balanceados, pago nativo y exportación de auditoría CSV |
| l10n_ar_account_tax_settlement | l10n_ar_account_tax_settlement | Exportadores argentinos adaptados, configuración explícita de diarios e índices/ajuste por inflación |
| fix_change_multicompany | fix_change_multicompany | Excepción contable opcional por empresa, limitada a las empresas seleccionadas |
| stock_eliminate_restrictions | stock_eliminate_restrictions | Excepción logística opcional; modelos de stock de Odoo 19, sin stock.valuation.layer |

`account_followup` original declaraba OEEL-1 y dependía de Enterprise. No se publica
ese código ni se cambia su licencia. El reemplazo Community tiene nombre propio;
no incluye los paneles o manejadores de informes de Enterprise. Los demás módulos
conservan las licencias AGPL-3/LGPL-3 y atribuciones indicadas en sus manifests.

## Decisiones funcionales

- Las opciones multicompañía están **desactivadas** al instalar. Un administrador
  puede habilitarlas en la ficha de cada empresa. Deben estar seleccionadas las
  empresas vinculadas; se mantienen ACL, reglas de acceso y demás restricciones
  nativas. No se garantiza que cualquier flujo cruzado pueda confirmarse: ventas,
  compras, movimientos y valoración conservan sus propias invariantes de Odoo.
- No se desactiva `_check_company_auto` globalmente. La antigua eliminación total
  de controles no se replica. Al habilitar la opción, los selectores de almacén
  de venta y recepción de compra permiten las empresas seleccionadas. Los valores
  predeterminados siguen correspondiendo a la empresa del pedido. Los vínculos
  especiales requieren configuración y pruebas del circuito concreto; las demás
  ubicaciones conservan sus dominios nativos.
- Caja es un **registro auxiliar de tesorería**, distinto de las sesiones del
  Punto de Venta. Entradas/salidas manuales no crean asientos automáticamente;
  los pagos sí conservan su contabilidad nativa. Los movimientos de caja no se
  borran; cancelar un pago añade un movimiento inverso en una sesión abierta.
- El saldo de cuenta corriente combina débitos y créditos de cuentas a cobrar y
  pagar de la empresa activa. No suma monedas de empresas diferentes.
- Las cotizaciones usan el tipo de venta elegido. BNA corresponde a **billetes**,
  no divisas; DolarAPI es un proveedor externo opcional. El programa anterior de
  Dolarsi se reemplaza. No se altera la política nativa de cotización fiscal de
  facturas. La tarea automática queda inactiva.
- Cobranzas se configura por empresa y opera sobre deuda vencida, descontando
  créditos pendientes. No enviar avisos hasta revisar niveles, destinatarios y
  mensajes. El cron queda inactivo y los niveles tienen ejecución automática
  desactivada. Correo y SMS usan los servicios nativos que configure el servidor.
- Las liquidaciones reservan sus apuntes de origen y crean **borradores** para
  revisión. Se usa el asistente nativo para pagar el saldo del asiento publicado.
  El CSV genérico es auditoría, no una presentación impositiva.
- Los once formatos regionales del original se adaptan al ORM de Odoo 19; cada
  retención del pago aporta su propio certificado, base e importe. Sus layouts
  históricos requieren validación en el aplicativo fiscal vigente y con los
  regímenes reales del contribuyente. Una prueba técnica no acredita aceptación
  por ARCA, ARBA, AGIP ni organismos provinciales.
- Los índices históricos mantienen `noupdate` para preservar modificaciones del
  contador. Cargar los índices mensuales del período requerido. Si falta un mes,
  el asistente no genera el ajuste. No se publican automáticamente los asientos.

## Instalación manual en Ubuntu

Descargar el repositorio completo en la rama `migration/argentina-19` y comprobar
que su raíz está en `addons_path`. El conjunto ahora incluye **16 módulos**:
los ocho iniciales y ocho incorporaciones. No copiar las carpetas originales de
Odoo 13/15/16 encima de estos módulos.

Para el checkout ya existente, limpio y correcto:

```bash
git -C /opt/odoo19/custom-addons fetch origin
git -C /opt/odoo19/custom-addons switch migration/argentina-19
git -C /opt/odoo19/custom-addons pull --ff-only origin migration/argentina-19
```

Usar el propietario habitual del checkout para Git. Instalar en la copia
neutralizada existente, sin ejecutar este comando sobre `sky_demo`. El bloque
detiene temporalmente el servicio compartido: ambas bases quedan sin acceso
durante la instalación. Al salir neutraliza la copia y vuelve a iniciar Odoo:

```bash
(
    set -e
    trap 'sudo -u odoo19 /opt/odoo19/venv/bin/python3 /opt/odoo19/odoo/odoo-bin neutralize -c /etc/odoo19/odoo19.conf -d sky_demo_ri; sudo systemctl start odoo19.service' EXIT
    sudo systemctl stop odoo19.service
    sudo -u odoo19 /opt/odoo19/venv/bin/python3 /opt/odoo19/odoo/odoo-bin shell \
        -c /etc/odoo19/odoo19.conf -d sky_demo_ri --no-http --max-cron-threads=0 \
        < /opt/odoo19/custom-addons/scripts/waiki19/preflight.py
    sudo -u odoo19 /opt/odoo19/venv/bin/python3 /opt/odoo19/odoo/odoo-bin shell \
        -c /etc/odoo19/odoo19.conf -d sky_demo_ri --no-http --max-cron-threads=0 <<'PY'
assert env.cr.dbname == 'sky_demo_ri'
assert env['ir.config_parameter'].sudo().get_param('database.is_neutralized') == 'true'
env['ir.config_parameter'].sudo().set_param('l10n_ar_fiscal_ws.env_type', 'homologation')
env.cr.commit()
PY
    sudo -u odoo19 /opt/odoo19/venv/bin/python3 /opt/odoo19/odoo/odoo-bin \
        -c /etc/odoo19/odoo19.conf -d sky_demo_ri \
        -i l10n_ar_fiscal_ws,l10n_ar_tax,account_view_localization_ar,partner_debt_info,dolar_update,cash_control,waiki_account_followup,account_tax_settlement,l10n_ar_account_tax_settlement,fix_change_multicompany,stock_eliminate_restrictions \
        --without-demo --stop-after-init --no-http --max-cron-threads=0
    sudo -u odoo19 /opt/odoo19/venv/bin/python3 /opt/odoo19/odoo/odoo-bin shell \
        -c /etc/odoo19/odoo19.conf -d sky_demo_ri --no-http --max-cron-threads=0 \
        < /opt/odoo19/custom-addons/scripts/argentina19/configure_homologation.py
)
```

Las dependencias completan el conjunto. Si ya están instalados y se actualiza
esta entrega, usar `-u` con esa misma lista. Antes de instalar, comprobar versión
19 de Odoo y que no existen módulos antiguos con los mismos nombres en otra ruta.
No es necesario desinstalar la localización nativa ni borrar datos.

## Configuración y aceptación

1. Seleccionar CLUB ARGENTINO DE SKI, plan `ar_ri`, y revisar impuestos y diarios.
2. Dar al responsable de caja el grupo Waiki cash-session user/manager. Crear un
   punto de pago, diarios de su empresa, abrir sesión y probar cobro/anulación y
   arqueo/cierre. Revisar además los asientos nativos del pago.
3. Elegir proveedor de cotizaciones en Ajustes de Contabilidad. Para ARCA elegir
   un diario fiscal y certificado de homologación. Probar primero el botón manual
   en Monedas. Activar la tarea solo después de revisar importes y empresa.
4. En Cobranzas Waiki crear niveles y revisar una carta/actividad manual antes de
   configurar correo/SMS y ejecución automática.
5. En Configurar liquidaciones AR elegir autoridad y cuenta de contrapartida.
   Revisar impuestos, etiquetas y formato de cada diario. Completar códigos de
   régimen y artículo/jurisdicción en los impuestos según corresponda.
6. Probar un período de liquidación, revisar borrador y archivo. Validar con el
   contador la importación del TXT en el aplicativo fiscal correspondiente.
7. Actualizar índices antes de probar ajuste por inflación. Revisar período,
   cuentas no monetarias, contrapartida y exclusión de cierre/apertura.
8. Las opciones de excepción multicompañía requieren un circuito real acordado;
   no hace falta activarlas para facturación, retenciones, caja o liquidaciones.

## Verificación reproducible

La verificación local usa Odoo Community 19, Python 3.12 y PostgreSQL 17 en una
base aislada. No se ejecuta sobre el servidor del usuario. El detalle y resultado
final están en `waiki19_test_report.json`, junto con el mapeo y procedencia.

En este workspace:

```powershell
py projects/sky_demo/tasks/audit_waiki19.py
.\projects\sky_demo\tasks\run_waiki19.ps1 -Mode test
```

El segundo comando requiere el entorno Docker de prueba ya preparado. En un
servidor de pruebas con dependencias instaladas, Odoo acepta:

```bash
odoo-bin -c /ruta/pruebas.conf -d base_de_pruebas_waiki \
  -u partner_debt_info,dolar_update,cash_control,waiki_account_followup,account_tax_settlement,l10n_ar_account_tax_settlement,fix_change_multicompany,stock_eliminate_restrictions \
  --test-enable --test-tags=/partner_debt_info,/dolar_update,/cash_control,/waiki_account_followup,/account_tax_settlement,/l10n_ar_account_tax_settlement,/fix_change_multicompany,/stock_eliminate_restrictions \
  --stop-after-init --no-http --max-cron-threads=0
```

Fuentes técnicas consultadas: [BNA](https://www.bna.com.ar/Personas),
[DolarAPI](https://dolarapi.com/docs/argentina/), código Community 19 del workspace
y manifests originales inventariados. Los servicios externos se simulan en las
pruebas; quedan pendientes la instalación manual y la aceptación fiscal real.
