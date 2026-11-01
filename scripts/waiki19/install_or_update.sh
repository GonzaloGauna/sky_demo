#!/usr/bin/env bash
# Authorized target: sky_demo_ri on the user's Ubuntu Odoo 19 server.
set -Eeuo pipefail

if [[ $EUID -ne 0 ]]; then
    echo 'Run this script with sudo bash.' >&2
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
    "$repo/scripts/waiki19/preflight.py" \
    "$repo/scripts/waiki19/verify_install.py" \
    "$repo/docs/waiki19/waiki19_all_modules.json"; do
    [[ -f "$path" ]] || { echo "Required file is missing: $path" >&2; exit 1; }
done

modules=$("$python_bin" -c 'import json,sys; print(",".join(json.load(open(sys.argv[1]))))' \
    "$repo/docs/waiki19/waiki19_all_modules.json")

run_odoo() {
    sudo -u odoo19 "$python_bin" "$odoo_bin" "$@"
}

was_active=false
if systemctl is-active --quiet "$service"; then was_active=true; fi

cleanup() {
    result=$?
    trap - EXIT
    if ! run_odoo neutralize -c "$conf" -d "$database"; then
        echo 'WARNING: neutralization failed; inspect sky_demo_ri before using it.' >&2
        if [[ $result -eq 0 ]]; then result=1; fi
    fi
    if [[ $was_active == true ]]; then
        if ! systemctl start "$service"; then result=1; fi
    fi
    if [[ $result -ne 0 ]]; then
        echo 'Installation did not finish. Preserve the error log; installed modules may have been committed in stages.' >&2
    fi
    exit "$result"
}

trap cleanup EXIT
echo 'Stopping the shared Odoo service. Both databases will be temporarily unavailable.'
systemctl stop "$service"

echo 'Preparing sky_demo_ri: preserving existing records and disabling future demo loading.'
run_odoo shell -c "$conf" -d "$database" --no-http --max-cron-threads=0 \
    < "$repo/scripts/waiki19/prepare_no_demo.py"
run_odoo shell -c "$conf" -d "$database" --no-http --max-cron-threads=0 \
    < "$repo/scripts/waiki19/preflight.py"

echo 'Installing missing modules and updating installed modules in sky_demo_ri.'
run_odoo -c "$conf" -d "$database" -i "$modules" -u "$modules" \
    --without-demo --stop-after-init --no-http --max-cron-threads=0

echo 'Verifying all 16 modules and the homologation configuration.'
run_odoo shell -c "$conf" -d "$database" --no-http --max-cron-threads=0 \
    < "$repo/scripts/waiki19/verify_install.py"
