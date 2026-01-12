#!/bin/bash
# Install Apache configuration on host machine (192.168.2.132)

set -e

echo "=== Apache Configuration Installation for ossiba.online ==="
echo

# Check if running on correct machine
CURRENT_IP=$(hostname -I | awk '{print $1}')
if [[ "$CURRENT_IP" != "192.168.2.132" ]]; then
    echo "⚠️  Warning: This script should run on the host machine (192.168.2.132)"
    echo "   Current IP: $CURRENT_IP"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root" 
   exit 1
fi

echo "Step 1: Copying configuration file..."
cp -v apache-config-host/001-orangescrum-online-vm.conf /etc/apache2/sites-available/

echo
echo "Step 2: Enabling required Apache modules..."
a2enmod ssl || true
a2enmod proxy || true
a2enmod proxy_http || true
a2enmod headers || true
a2enmod rewrite || true

echo
echo "Step 3: Testing Apache configuration..."
if apachectl configtest; then
    echo "✓ Configuration syntax is valid"
else
    echo "❌ Configuration has errors. Please fix before continuing."
    exit 1
fi

echo
echo "Step 4: Checking VirtualHost order..."
echo "Looking for correct order: v4.ossiba.online before *.ossiba.online wildcard"
apachectl -S 2>&1 | grep -A 10 "443.*NameVirtualHost"

echo
echo "Step 5: Enabling site..."
a2ensite 001-orangescrum-online-vm.conf

echo
echo "Step 6: Reloading Apache..."
systemctl reload apache2

echo
echo "✅ Installation complete!"
echo
echo "Verify with:"
echo "  curl -I https://v4.ossiba.online/"
echo "  curl -I https://ossiba.online/"
echo
echo "Watch logs:"
echo "  tail -f /var/log/apache2/ossiba-online-v4-access.log"
echo "  tail -f /var/log/apache2/ossiba-online-v2-access.log"
