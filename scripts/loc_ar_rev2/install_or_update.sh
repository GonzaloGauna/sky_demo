#!/usr/bin/env bash
# Destino autorizado: sky_demo_ri en el servidor Ubuntu Odoo 19 del usuario.
# Fase 1 de loc_ar_rev2: retira cash_control e instala/actualiza la pila ADHOC/OCA de contabilidad.
# No emite comprobantes: deja ARCA en homologación y desactiva las tareas programadas de negocio.
set -Eeuo pipefail

if [[ $EUID -ne 0 ]]; then
    echo 'Ejecutar con sudo bash.' >&2
    exit 1
fi

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
conf=/etc/odoo19/odoo19.conf
python_bin=/opt/odoo19/venv/bin/python3
odoo_bin=/opt/odoo19/odoo/odoo-bin
database=sky_demo_ri
service=odoo19.service

for path in "$python_bin" "$odoo_bin" "$conf" \
    "$repo/scripts/waiki19/prepare_no_demo.py" \
    "$repo/scripts/loc_ar_rev2/preflight.py" \
    "$repo/scripts/loc_ar_rev2/uninstall_cash_control.py" \
    "$repo/scripts/loc_ar_rev2/verify_install.py" \
    "$repo/docs/loc_ar_rev2/modules.json"; do
    [[ -f "$path" ]] || { echo "Falta el archivo: $path" >&2; exit 1; }
done

modules=$("$python_bin" -c 'import json,sys; print(",".join(json.load(open(sys.argv[1]))))' \
    "$repo/docs/loc_ar_rev2/modules.json")

run_odoo() {
    sudo -u odoo19 "$python_bin" "$odoo_bin" "$@"
}

odoo_shell() {
    run_odoo shell -c "$conf" -d "$database" --no-http --max-cron-threads=0 < "$1"
}

was_active=false
if systemctl is-active --quiet "$service"; then was_active=true; fi

cleanup() {
    result=$?
    trap - EXIT
    if ! run_odoo neutralize -c "$conf" -d "$database"; then
        echo 'AVISO: la neutralización falló; revisar sky_demo_ri antes de usarla.' >&2
        if [[ $result -eq 0 ]]; then result=1; fi
    fi
    if [[ $was_active == true ]]; then
        if ! systemctl start "$service"; then result=1; fi
    fi
    if [[ $result -ne 0 ]]; then
        echo 'La instalación no terminó. Conservar el log: Odoo puede haber confirmado módulos por etapas.' >&2
    fi
    exit "$result"
}

trap cleanup EXIT
echo 'Deteniendo el servicio Odoo compartido. Ambas bases quedarán sin acceso temporalmente.'
systemctl stop "$service"

echo 'Preparando sky_demo_ri (sin cargas demo futuras, ARCA en homologación).'
odoo_shell "$repo/scripts/waiki19/prepare_no_demo.py"
odoo_shell "$repo/scripts/loc_ar_rev2/preflight.py"

echo 'Retirando cash_control (sustituido por account_cashbox).'
odoo_shell "$repo/scripts/loc_ar_rev2/uninstall_cash_control.py"

echo 'Instalando los faltantes y actualizando los instalados.'
run_odoo -c "$conf" -d "$database" -i "$modules" -u "$modules" \
    --without-demo --stop-after-init --no-http --max-cron-threads=0

echo 'Verificando la instalación y la configuración de homologación.'
odoo_shell "$repo/scripts/loc_ar_rev2/verify_install.py"
