# Localización argentina — Odoo 19 Community

## Alcance de esta entrega

- Proyecto: sky_demo; base autorizada para instalar: **sky_demo_ri**.
- Empresa: 2, CLUB ARGENTINO DE SKI; plan `ar_ri`, IVA Responsable Inscripto.
- Prioridad: facturación electrónica, pagos y retenciones.
- Ocho módulos en la raíz del repositorio; consultar `argentina19_modules.json`.
- Los addons originales recibidos eran principalmente de Odoo 16. Se utilizan
  implementaciones 19.0 de ADHOC y la vista compatible de Waiki. No se migran datos
  ni certificados de una base antigua.
- No se modifica código base de Odoo ni Enterprise.

`l10n_ar_fiscal_ws` reemplaza al conjunto anterior `l10n_ar_afipws` /
`l10n_ar_afipws_fe`. Pagos y retenciones se implementan mediante
`account_payment_pro`, `l10n_ar_tax` y las retenciones nativas de Odoo 19.

El alcance inicial de ocho addons se amplió posteriormente a todos los módulos
de ambas carpetas Waiki. Consultar la [entrega Waiki completa](../waiki19/INSTALACION.md)
para instalar el conjunto de 16 addons y revisar sus diferencias funcionales.

## Adaptaciones

- Reemplazo de parches globales de clases por herencia de modelos en cada registro
  Odoo. Se elimina también el hook que intentaba revertir aquellos parches.
- Selección de diarios por empresa al procesar pagos de varias empresas en un lote.
- Aplicación de la posición fiscal manual al crear el pago, antes de confirmarlo.
  Reescribirla después de conciliar eliminaba las retenciones de pagos agrupados.
- `auto_install=False` en los ocho módulos: instalación explícita solo en la copia.
- Pruebas de regresión y fixtures independientes de demo y empresas preexistentes.
- Descripción reStructuredText de retenciones compatible con el renderizador Odoo.

Los commits y licencias originales se conservan. El parche adjunto permite revisar
las diferencias respecto de los módulos publicados usados como base.

## Pruebas realizadas

59 escenarios únicos validados: 38 de servicios fiscales y 21 de pagos,
retenciones y aislamiento entre empresas. La regresión final de pagos terminó
con **0 fallos y 0 errores**, incluyendo pagos agrupados con posición fiscal manual
y automática. Consultar `argentina19_test_report.json` para los nombres de los casos.

Entorno: Python 3.12.3, PostgreSQL 17 y Odoo Community 19, commit
`e84f15186f4a5fb12366ef11d07df355918224ef`, en una base aislada.
También se validaron Python AST, XML, rutas de archivos de los manifests y RST.

Las llamadas a ARCA fueron simuladas. La instalación sobre el servidor Ubuntu 24.04
y la interacción con los otros addons de esa base aún requieren validación manual.

## Preparación del servidor

Rutas verificadas en el servidor:

```text
/opt/odoo19/venv/bin/python3
/opt/odoo19/odoo/odoo-bin
/etc/odoo19/odoo19.conf
Servicio y usuario: odoo19
addons_path = /opt/odoo19/odoo/addons,/opt/odoo19/custom-addons
```

Verificar que el checkout de este repositorio ocupa `/opt/odoo19/custom-addons`.
Si está en otra ubicación, incluir la raíz real en `addons_path` antes de instalar.
No clonar encima de una carpeta existente ni descartar cambios locales.

Con el checkout correcto y limpio, obtener y seleccionar esta rama:

```bash
git -C /opt/odoo19/custom-addons fetch origin
git -C /opt/odoo19/custom-addons switch migration/argentina-19
```

Consultar permisos y propietario del checkout antes de usar Git: ejecutar como su
propietario habitual. No aplicar cambios recursivos de permisos para resolver
errores de Git sin revisar primero cómo se despliega el proyecto.

La siguiente consulta no guarda cambios y rechaza una base equivocada, sin
neutralizar, sin plan `ar_ri`, con contabilidad de CLUB o con módulos antiguos:

```bash
sudo -u odoo19 /opt/odoo19/venv/bin/python3 /opt/odoo19/odoo/odoo-bin shell -c /etc/odoo19/odoo19.conf -d sky_demo_ri --no-http --max-cron-threads=0 < /opt/odoo19/custom-addons/scripts/argentina19/preflight.py
```

## Instalación

El bloque siguiente interrumpe temporalmente ambas bases al detener el servicio
compartido. Respalda `sky_demo_ri` con sus adjuntos, fija homologación e instala
únicamente en esa base. Al salir, incluso ante un error, neutraliza las tareas
nuevas de la copia y vuelve a iniciar Odoo. No elimina historial ni restaura bases.

```bash
(
    set -e
    trap 'sudo -u odoo19 /opt/odoo19/venv/bin/python3 /opt/odoo19/odoo/odoo-bin neutralize -c /etc/odoo19/odoo19.conf -d sky_demo_ri; sudo systemctl start odoo19.service' EXIT
    sudo systemctl stop odoo19.service

    sudo install -d -m 700 -o odoo19 -g odoo19 /var/lib/odoo19-migration-backups
    backup_path="/var/lib/odoo19-migration-backups/sky_demo_ri_before_ar19_$(date -u +%Y%m%dT%H%M%SZ).zip"
    sudo -u odoo19 /opt/odoo19/venv/bin/python3 /opt/odoo19/odoo/odoo-bin db -c /etc/odoo19/odoo19.conf dump sky_demo_ri "$backup_path"

    sudo -u odoo19 /opt/odoo19/venv/bin/python3 /opt/odoo19/odoo/odoo-bin shell -c /etc/odoo19/odoo19.conf -d sky_demo_ri --no-http --max-cron-threads=0 <<'PY'
assert env.cr.dbname == 'sky_demo_ri'
assert env['ir.config_parameter'].sudo().get_param('database.is_neutralized') == 'true'
env['ir.config_parameter'].sudo().set_param('l10n_ar_fiscal_ws.env_type', 'homologation')
env.cr.commit()
PY

    sudo -u odoo19 /opt/odoo19/venv/bin/python3 /opt/odoo19/odoo/odoo-bin -c /etc/odoo19/odoo19.conf -d sky_demo_ri -i l10n_ar_fiscal_ws,l10n_ar_tax,account_view_localization_ar --without-demo --stop-after-init --no-http --max-cron-threads=0

    sudo -u odoo19 /opt/odoo19/venv/bin/python3 /opt/odoo19/odoo/odoo-bin shell -c /etc/odoo19/odoo19.conf -d sky_demo_ri --no-http --max-cron-threads=0 < /opt/odoo19/custom-addons/scripts/argentina19/configure_homologation.py
)
```

Las instalaciones de Odoo pueden confirmar cambios por etapas. Si falla, conservar
el error y el respaldo; no volver a instalar ni restaurar automáticamente sin
revisar su estado. Comprobar el servicio con `systemctl is-active odoo19.service`.

Para una actualización posterior, con respaldo y servicio detenido, sustituir
`-i` por `-u` y enumerar los ocho módulos en `argentina19_modules.json`. Luego
ejecutar el script de homologación y neutralizar antes de reiniciar. No usar
`-u all` ni seleccionar `sky_demo` como destino.

## Validación pendiente en sky_demo_ri

1. Comprobar los ocho módulos instalados y el plan `ar_ri` de CLUB.
2. Configurar CUIT, domicilio, diario y punto de venta fiscal de homologación.
3. Cargar los certificados correspondientes y verificar una autorización real,
   su CAE, vencimiento, numeración y QR en el PDF.
4. Configurar diarios bancarios/caja, cuentas pendientes, impuestos, posiciones
   fiscales, regímenes y padrones aplicables. Probar una factura de proveedor,
   pago, retención, conciliación y certificado de retención.
5. Recrear el PDV si se necesita: fue eliminado en la limpieza previa. No se
   incluye un puente fiscal específico para Punto de Venta en esta entrega.

Sin certificados, el cliente fiscal admite validación local en homologación con
un código simulado. Eso no equivale a un CAE autorizado por ARCA.
La copia permanece neutralizada; su paso a producción no está incluido.
