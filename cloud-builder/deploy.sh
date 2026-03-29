#!/bin/bash
# deploy.sh - Deploy the latest (or specified) FrankenPHP build
#
# Usage:
#   ./deploy.sh                    # Deploy latest build
#   ./deploy.sh <timestamp>        # Deploy specific build (e.g. 20260329_143000)
#   ./deploy.sh latest logs -f     # Pass extra docker compose args
#   ./deploy.sh latest ps          # Check status of latest deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_ROOT="$SCRIPT_DIR/dist"

# ---------------------------------------------------------------------------
# Resolve which build to deploy
# ---------------------------------------------------------------------------
resolve_build_dir() {
    local target="${1:-latest}"

    if [ "$target" = "latest" ]; then
        # Find the most recent timestamped build
        local latest
        latest=$(ls -1d "$DIST_ROOT"/*/dist-docker 2>/dev/null | sort -r | head -1)
        if [ -z "$latest" ]; then
            echo "[ERROR] No builds found in $DIST_ROOT/" >&2
            echo "  Run: python3 build.py --skip-deploy" >&2
            exit 1
        fi
        echo "$latest"
    else
        # Specific timestamp provided
        local dir="$DIST_ROOT/$target/dist-docker"
        if [ ! -d "$dir" ]; then
            echo "[ERROR] Build not found: $dir" >&2
            echo "  Available builds:" >&2
            ls -1d "$DIST_ROOT"/*/dist-docker 2>/dev/null | sed 's|.*/dist/||;s|/dist-docker||;s|^|    |' >&2
            exit 1
        fi
        echo "$dir"
    fi
}

# First arg is the build target (or "latest"), remaining args go to docker compose
BUILD_TARGET="${1:-latest}"

# If the first arg looks like a docker compose subcommand, treat it as "latest" + args
case "$BUILD_TARGET" in
    up|down|ps|logs|restart|stop|start|exec|build|pull|config)
        DEPLOY_DIR=$(resolve_build_dir "latest")
        COMPOSE_ARGS=("$@")
        ;;
    *)
        DEPLOY_DIR=$(resolve_build_dir "$BUILD_TARGET")
        shift 2>/dev/null || true
        COMPOSE_ARGS=("$@")
        ;;
esac

COMPOSE_FILE="$DEPLOY_DIR/docker-compose.yaml"
ENV_FILE="$DEPLOY_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    ENV_FILE="$DEPLOY_DIR/.env.example"
fi

echo "Deploying from: $DEPLOY_DIR"
echo ""

if [ ${#COMPOSE_ARGS[@]} -eq 0 ]; then
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build
else
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}"
fi
