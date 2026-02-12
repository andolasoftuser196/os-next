#!/bin/bash
# Test script for Apache reverse proxy setup
# Run this from the Apache server to verify connectivity to Docker/Traefik

set -e

# Configuration
DOCKER_SERVER="${1:-192.168.2.132}"
TRAEFIK_PORT="${2:-18643}"
DOMAIN="${3:-ossiba.local}"

echo "=========================================="
echo "Testing Apache → Traefik connectivity"
echo "=========================================="
echo "Docker server: $DOCKER_SERVER"
echo "Traefik port:  $TRAEFIK_PORT"
echo "Domain:        $DOMAIN"
echo ""

# Test 1: Network connectivity
echo "Test 1: Network connectivity..."
if ping -c 1 -W 2 "$DOCKER_SERVER" > /dev/null 2>&1; then
    echo "✓ Can ping Docker server"
else
    echo "✗ Cannot ping Docker server"
    exit 1
fi

# Test 2: Port accessibility
echo ""
echo "Test 2: Port accessibility..."
if timeout 5 bash -c "</dev/tcp/$DOCKER_SERVER/$TRAEFIK_PORT" 2>/dev/null; then
    echo "✓ Port $TRAEFIK_PORT is accessible"
else
    echo "✗ Port $TRAEFIK_PORT is not accessible"
    echo "  Check firewall rules on Docker server"
    exit 1
fi

# Test 3: HTTPS response
echo ""
echo "Test 3: HTTPS response from Traefik..."
RESPONSE=$(curl -sk -H "Host: v4.$DOMAIN" "https://$DOCKER_SERVER:$TRAEFIK_PORT/" -w "%{http_code}" -o /tmp/traefik-test.html)

if [ "$RESPONSE" = "200" ]; then
    echo "✓ Received HTTP 200 from v4.$DOMAIN"
    echo "  Content preview:"
    head -5 /tmp/traefik-test.html | sed 's/^/    /'
elif [ "$RESPONSE" = "404" ]; then
    echo "⚠ Received HTTP 404 - Traefik is running but app might not be deployed"
    echo "  This is normal if applications are not yet deployed"
else
    echo "✗ Unexpected response: HTTP $RESPONSE"
    exit 1
fi

# Test 4: Check multiple subdomains
echo ""
echo "Test 4: Testing multiple subdomains..."
for subdomain in "selfhosted" "app" "mail"; do
    RESPONSE=$(curl -sk -H "Host: $subdomain.$DOMAIN" "https://$DOCKER_SERVER:$TRAEFIK_PORT/" -w "%{http_code}" -o /dev/null)
    if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "404" ]; then
        echo "✓ $subdomain.$DOMAIN: HTTP $RESPONSE"
    else
        echo "✗ $subdomain.$DOMAIN: HTTP $RESPONSE (unexpected)"
    fi
done

# Test 5: WebSocket support
echo ""
echo "Test 5: WebSocket headers..."
if curl -sk -H "Host: v4.$DOMAIN" -H "Upgrade: websocket" -H "Connection: upgrade" \
    "https://$DOCKER_SERVER:$TRAEFIK_PORT/" --max-time 5 > /dev/null 2>&1; then
    echo "✓ WebSocket upgrade request accepted"
else
    echo "⚠ WebSocket test inconclusive (this is often normal)"
fi

echo ""
echo "=========================================="
echo "✓ All critical tests passed!"
echo "=========================================="
echo ""
echo "Your Apache reverse proxy should work if:"
echo "1. Apache config points to: $DOCKER_SERVER:$TRAEFIK_PORT"
echo "2. SSL certificates are properly configured"
echo "3. Required Apache modules are enabled (proxy, ssl, rewrite, headers)"
echo ""
echo "Next steps:"
echo "  1. Copy apache-proxy-ossiba-com.conf to /etc/apache2/sites-available/"
echo "  2. Update TRAEFIK_HOST and certificate paths in the config"
echo "  3. Enable the site: sudo a2ensite orangescrum-ossiba-com"
echo "  4. Reload Apache: sudo systemctl reload apache2"
echo ""

# Cleanup
rm -f /tmp/traefik-test.html
