#!/usr/bin/env bash
set -e

CERT_SRC="/certs/ossiba.local.crt"
CERT_DST="/usr/local/share/ca-certificates/ossiba.local.crt"

if [ -f "$CERT_SRC" ]; then
  cp "$CERT_SRC" "$CERT_DST"
  update-ca-certificates >/dev/null 2>&1 || true
fi
