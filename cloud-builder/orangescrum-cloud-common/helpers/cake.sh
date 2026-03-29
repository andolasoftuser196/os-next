#!/bin/bash
# CakePHP CLI Wrapper
# Usage: ./helpers/cake.sh bin/cake.php migrations migrate
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

# Source shared library for load_env_file and resolve_binary
source "$SCRIPT_DIR/lib/frankenphp-common.sh"

load_env_file ".env"
BINARY=$(resolve_binary) || exit 1

"$BINARY" php-cli "$@"
