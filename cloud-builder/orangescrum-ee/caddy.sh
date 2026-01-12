#!/bin/bash
# CakePHP CLI Wrapper with Environment Variables
# Usage: ./cake.sh bin/cake.php migrations migrate
#        ./cake.sh bin/cake.php cache clear_all

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Auto-detect binary path
if [ -f "./bin/orangescrum" ]; then
    BINARY="./bin/orangescrum"
elif [ -f "./orangescrum-app/orangescrum-ee" ]; then
    BINARY="./orangescrum-app/orangescrum-ee"
else
    echo "❌ Binary not found"
    exit 1
fi

ENV_FILE=".env"

# Load environment variables from .env
if [ -f "$ENV_FILE" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        if [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
            if [[ "$value" =~ ^\"(.*)\"$ ]] || [[ "$value" =~ ^\'(.*)\'$ ]]; then
                value="${BASH_REMATCH[1]}"
            fi
            export "$key=$value"
        fi
    done < "$ENV_FILE"
fi

# Run the command with all arguments
"$BINARY" "$@"
