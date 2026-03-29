#!/bin/bash
# Caddy/FrankenPHP CLI Wrapper
# Usage: ./caddy.sh <caddy-subcommand> [args...]
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Source shared library
source "$SCRIPT_DIR/lib/frankenphp-common.sh"

load_env_file ".env"
BINARY=$(resolve_binary) || exit 1

"$BINARY" "$@"
