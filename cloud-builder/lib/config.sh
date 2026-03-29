#!/bin/bash
# Shared configuration loader for shell scripts.
# Source this file: source "$(dirname "$0")/../lib/config.sh"
#
# Provides:
#   load_version    — sets $VERSION from the VERSION file
#   load_build_conf — sets build variables from build.conf
#   BUILDER_ROOT    — absolute path to cloud-builder/

# Resolve BUILDER_ROOT (cloud-builder/ directory)
if [ -z "$BUILDER_ROOT" ]; then
    # Walk up from this script's location (lib/config.sh -> cloud-builder/)
    BUILDER_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

# ---------------------------------------------------------------------------
# load_version — read VERSION file into $VERSION
# ---------------------------------------------------------------------------
load_version() {
    local version_file="$BUILDER_ROOT/VERSION"
    if [ -f "$version_file" ]; then
        VERSION="$(cat "$version_file" | tr -d '[:space:]')"
    else
        VERSION="${VERSION:-v0.0.0-unknown}"
    fi
    export VERSION
}

# ---------------------------------------------------------------------------
# load_build_conf — read build.conf into shell variables
# ---------------------------------------------------------------------------
load_build_conf() {
    local conf_file="$BUILDER_ROOT/build.conf"
    [ -f "$conf_file" ] || return 0

    # Use a small Python one-liner to parse the INI file.
    # Python's configparser is the right tool — no awk gymnastics.
    eval "$(python3 -c "
import configparser, sys
cp = configparser.ConfigParser()
cp.read(sys.argv[1])
for section in cp.sections():
    for key, val in cp.items(section):
        val = val.strip()
        print(f\"export CONF_{key.upper()}='{val}'\")
" "$conf_file")"

    # Promote commonly used values to short names (env overrides conf)
    export FRANKENPHP_VERSION="${FRANKENPHP_VERSION:-$CONF_FRANKENPHP_VERSION}"
    export PHP_VERSION="${PHP_VERSION:-$CONF_PHP_VERSION}"
    export BASE_IMAGE_NAME="${BASE_IMAGE_NAME:-$CONF_BASE_IMAGE_NAME}"
    export APP_IMAGE_NAME="${APP_IMAGE_NAME:-$CONF_APP_IMAGE_NAME}"
    export BINARY_NAME="${BINARY_NAME:-${CONF_BINARY_NAME:-osv4-prod}}"
}
