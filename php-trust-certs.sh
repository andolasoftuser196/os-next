#!/bin/bash
# Trust the custom SSL certificate in the container and setup DNS resolution
# Domain: ossiba.online
# Generated: 2026-01-12 13:25:51

set -e

# Add the certificate to the system CA bundle
if [ -f /usr/local/share/ca-certificates/ossiba.online.crt ]; then
    echo "Adding custom certificate to CA bundle..."
    
    # For Alpine-based images with update-ca-certificates
    if command -v update-ca-certificates >/dev/null 2>&1; then
        update-ca-certificates
    fi
    
    # Also copy to PHP's certificate bundle locations
    if [ -f /etc/ssl/certs/ca-certificates.crt ]; then
        cat /usr/local/share/ca-certificates/ossiba.online.crt >> /etc/ssl/certs/ca-certificates.crt
    fi
    
    # For php.ini openssl default_cert_file
    if [ -f /etc/ssl/certs/ca-bundle.crt ]; then
        cat /usr/local/share/ca-certificates/ossiba.online.crt >> /etc/ssl/certs/ca-bundle.crt
    fi
    
    echo "Certificate added successfully"
fi

# Add hostname resolution for ossiba.online domains to traefik container IP
# All ossiba.online domains route through traefik for HTTPS
TRAEFIK_IP="172.25.0.10"

if grep -q "v4.ossiba.online" /etc/hosts 2>/dev/null; then
    echo "Hostname entries already exist in /etc/hosts"
else
    echo "Adding hostname resolution for ossiba.online domains..."
    {
        echo "$TRAEFIK_IP v4.ossiba.online"
        echo "$TRAEFIK_IP app.ossiba.online"
        echo "$TRAEFIK_IP mail.ossiba.online"
    } >> /etc/hosts
    echo "Hostname entries added successfully"
fi

# Execute the original command
exec "$@"
