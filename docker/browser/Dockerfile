FROM lscr.io/linuxserver/chromium:latest

USER root

# Pre-install certutil so trust-cert scripts work without network access at runtime
RUN apt-get update -qq \
  && apt-get install -y --no-install-recommends libnss3-tools ca-certificates \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# linuxserver s6-overlay entrypoint requires root; image handles user switching internally
