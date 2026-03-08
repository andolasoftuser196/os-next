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
certutil -N -d "$NSS_DB" --empty-password 2>/dev/null || true
# Remove old entry if it exists, then re-add fresh
certutil -D -n 'ossiba.local CA' -d "$NSS_DB" 2>/dev/null || true
certutil -A -n 'ossiba.local CA' -t 'CT,,' -i "$CERT_SRC" -d "$NSS_DB"
# Ensure the abc user (linuxserver default) can access the NSS db
chown -R abc:abc /config/.pki 2>/dev/null || true
