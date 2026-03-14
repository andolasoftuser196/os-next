#!/usr/bin/env bash
set -e

CERT_SRC="/certs/ossiba.local.crt"
CERT_DST="/usr/local/share/ca-certificates/ossiba.local.crt"

if [ ! -f "$CERT_SRC" ]; then
  echo "[browser-trust-certs] Certificate not found at $CERT_SRC, skipping"
  exit 0
fi

# certutil is pre-installed in the custom Dockerfile (docker/browser/Dockerfile)

# Add to system trust store
cp "$CERT_SRC" "$CERT_DST"
update-ca-certificates

# Add to Chromium's NSS database
# linuxserver/chromium uses /config as the user home directory
NSS_DB="sql:/config/.pki/nssdb"
mkdir -p /config/.pki/nssdb
# Redirect stdin from /dev/null to prevent certutil from hanging waiting for input
timeout 10 certutil -N -d "$NSS_DB" --empty-password </dev/null 2>/dev/null || true
# Remove old entry if it exists, then re-add fresh
timeout 10 certutil -D -n 'ossiba.local CA' -d "$NSS_DB" </dev/null 2>/dev/null || true
timeout 10 certutil -A -n 'ossiba.local CA' -t 'CT,,' -i "$CERT_SRC" -d "$NSS_DB" </dev/null
# Ensure the browser user can access the NSS db (linuxserver uses abc or CUSTOM_USER)
chown -R 1000:1000 /config/.pki 2>/dev/null || true
