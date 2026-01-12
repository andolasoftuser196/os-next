#!/bin/bash
# Generate self-signed SSL certificates for local development
# Domain: ossiba.online
# Generated: 2026-01-12 12:10:01

CERT_DIR="./certs"
DOMAIN="ossiba.online"

echo "Generating self-signed SSL certificate for *.$DOMAIN and $DOMAIN..."

# Create certificate directory if it doesn't exist
mkdir -p "$CERT_DIR"

# Generate private key
openssl genrsa -out "$CERT_DIR/$DOMAIN.key" 2048

# Create OpenSSL config for SAN (Subject Alternative Names)
cat > "$CERT_DIR/openssl.cnf" <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C=US
ST=State
L=City
O=Organization
OU=Development
CN=*.$DOMAIN

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = $DOMAIN
DNS.2 = *.$DOMAIN
DNS.3 = v4.$DOMAIN
DNS.4 = mail.$DOMAIN
DNS.5 = www.$DOMAIN
DNS.6 = app.$DOMAIN
EOF

# Generate certificate signing request and self-signed certificate
openssl req -new -x509 -key "$CERT_DIR/$DOMAIN.key" \
    -out "$CERT_DIR/$DOMAIN.crt" \
    -days 365 \
    -config "$CERT_DIR/openssl.cnf" \
    -extensions v3_req

# Set proper permissions
chmod 644 "$CERT_DIR/$DOMAIN.crt"
chmod 600 "$CERT_DIR/$DOMAIN.key"

echo "✓ SSL certificate generated successfully!"
echo "  Certificate: $CERT_DIR/$DOMAIN.crt"
echo "  Private Key: $CERT_DIR/$DOMAIN.key"
echo ""
echo "To trust this certificate in your browser:"
echo "  - Chrome/Edge: Import $CERT_DIR/$DOMAIN.crt to 'Trusted Root Certification Authorities'"
echo "  - Firefox: Settings -> Privacy & Security -> Certificates -> Import"
echo ""
