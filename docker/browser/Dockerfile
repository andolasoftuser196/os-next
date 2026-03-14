FROM lscr.io/linuxserver/chromium:latest

USER root

# Pre-install certutil so trust-cert scripts work without network access at runtime
RUN apt-get update -qq \
  && apt-get install -y --no-install-recommends libnss3-tools ca-certificates \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Copy trust-certs script into image owned by root (s6-overlay security requirement)
COPY --chown=root:root entrypoints/browser-trust-certs.sh /custom-cont-init.d/10-browser-trust-certs.sh
RUN chmod 755 /custom-cont-init.d/10-browser-trust-certs.sh
