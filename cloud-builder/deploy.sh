#!/bin/bash
# deploy.sh - SaaS/app-only deployment wrapper

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORANGESCRUM_EE_DIR="$SCRIPT_DIR/orangescrum-cloud"
COMPOSE_FILE="$ORANGESCRUM_EE_DIR/docker-compose.yaml"

ENV_FILE="$ORANGESCRUM_EE_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    ENV_FILE="$ORANGESCRUM_EE_DIR/.env.example"
fi

if [ "$#" -eq 0 ]; then
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build
else
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"
fi
