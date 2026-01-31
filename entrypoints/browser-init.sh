#!/bin/bash
set -e
# Add local CA cert
sudo mkdir -p /usr/local/share/ca-certificates || true
sudo cp /certs/ossiba.local.crt /usr/local/share/ca-certificates/ossiba.local.crt 2>/dev/null || true
sudo update-ca-certificates 2>/dev/null || true
# Setup nssdb
mkdir -p /home/seluser/.pki/nssdb || true
certutil -d sql:/home/seluser/.pki/nssdb -A -t 'C,,' -n 'ossiba.local CA' -i /certs/ossiba.local.crt 2>/dev/null || true
# If read-only config is mounted, copy into user's home and fix ownership
if [ -d /etc/fluxbox-config ]; then
  rm -rf /home/seluser/.fluxbox || true
  cp -a /etc/fluxbox-config /home/seluser/.fluxbox || true
  chown -R seluser:seluser /home/seluser/.fluxbox || true
  chmod 755 /home/seluser/.fluxbox || true
  chmod 644 /home/seluser/.fluxbox/* || true
fi
# Ensure standard fluxbox configs exist as fallback
if [ ! -d /home/seluser/.fluxbox/styles ]; then
  mkdir -p /home/seluser/.fluxbox/styles || true
  ln -sf /usr/share/fluxbox/styles /home/seluser/.fluxbox/styles || true
fi
# Exec the original entrypoint
exec /opt/bin/entry_point.sh
