#!/bin/bash

# Reusable .env file loader
# Usage: source ./load-env.sh path/to/.env

load_env() {
    local ENV_FILE="${1:-.env}"
    
    if [ ! -f "$ENV_FILE" ]; then
        echo "Error: $ENV_FILE file not found" >&2
        return 1
    fi
    
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        
        # Match KEY=VALUE pattern
        if [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
            
            # Strip quotes from value
            if [[ "$value" =~ ^\"(.*)\"$ ]] || [[ "$value" =~ ^\'(.*)\'$ ]]; then
                value="${BASH_REMATCH[1]}"
            fi
            
            # Export the variable
            export "$key=$value"
        fi
    done < "$ENV_FILE"
    
    return 0
}

# If script is sourced with argument, load that file
if [ -n "$1" ]; then
    load_env "$1"
fi
