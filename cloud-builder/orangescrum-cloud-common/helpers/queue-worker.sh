#!/bin/bash
# Queue Worker Manager with Auto-Restart
# Usage: ./helpers/queue-worker.sh start|stop|restart|status|logs
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

# Source shared library
source "$SCRIPT_DIR/lib/frankenphp-common.sh"

load_env_file ".env"
BINARY=$(resolve_binary) || exit 1

# Configuration (all from env, with sane defaults)
PID_FILE="$SCRIPT_DIR/queue-worker.pid"
LOG_FILE="$SCRIPT_DIR/queue-worker.log"
MAX_RUNTIME="${QUEUE_MAX_RUNTIME:-0}"
RESTART_DELAY="${QUEUE_RESTART_DELAY:-3}"
MAX_RESTARTS="${QUEUE_MAX_RESTARTS:-100}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
is_running() {
    [ -f "$PID_FILE" ] || return 1
    local pid
    pid=$(cat "$PID_FILE")
    kill -0 "$pid" 2>/dev/null && return 0
    rm -f "$PID_FILE"
    return 1
}

get_pid() {
    cat "$PID_FILE" 2>/dev/null
}

# ---------------------------------------------------------------------------
# Worker loop (runs in foreground — backgrounded by start_worker)
# ---------------------------------------------------------------------------
worker_loop() {
    local restart_count=0
    local hour_start
    hour_start=$(date +%s)

    while true; do
        # Reset counter every hour
        local now
        now=$(date +%s)
        if [ $((now - hour_start)) -ge 3600 ]; then
            restart_count=0
            hour_start=$now
        fi

        if [ "$restart_count" -ge "$MAX_RESTARTS" ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Max restarts ($MAX_RESTARTS/hour) reached. Stopping."
            exit 1
        fi

        if [ "$restart_count" -gt 0 ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Restarting worker (attempt $restart_count)..."
        else
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Starting queue worker..."
        fi

        # Build the command
        local cmd=("$BINARY" php-cli bin/cake.php queue worker --verbose)
        if [ "$MAX_RUNTIME" -gt 0 ] 2>/dev/null; then
            cmd+=(--max-runtime "$MAX_RUNTIME")
        fi

        # Run worker (blocks until it exits)
        "${cmd[@]}" 2>&1
        local exit_code=$?

        echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARN: Worker exited with code $exit_code"

        # Clean exit = don't restart
        if [ "$exit_code" -eq 0 ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Clean shutdown. Exiting."
            break
        fi

        restart_count=$((restart_count + 1))
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Waiting ${RESTART_DELAY}s before restart..."
        sleep "$RESTART_DELAY"
    done
}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
start_worker() {
    if is_running; then
        echo "[WARN] Queue worker already running (PID: $(get_pid))"
        return 1
    fi

    echo "[INFO] Starting queue worker..."
    touch "$LOG_FILE"

    # Run the worker loop in background, redirect to log file
    worker_loop >> "$LOG_FILE" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_FILE"

    echo "[OK] Queue worker started (PID: $pid)"
    echo "[INFO] Log: $LOG_FILE"

    sleep 2
    tail -20 "$LOG_FILE"
}

stop_worker() {
    if ! is_running; then
        echo "[WARN] Queue worker is not running"
        return 1
    fi

    local pid
    pid=$(get_pid)
    echo "[INFO] Stopping queue worker (PID: $pid)..."

    # Kill the worker loop and its children
    kill "$pid" 2>/dev/null || true
    pkill -P "$pid" 2>/dev/null || true

    # Wait for graceful shutdown (up to 10s)
    local i
    for i in {1..10}; do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
    done

    # Force kill if still alive
    if kill -0 "$pid" 2>/dev/null; then
        echo "[WARN] Force killing..."
        kill -9 "$pid" 2>/dev/null || true
        pkill -9 -P "$pid" 2>/dev/null || true
    fi

    rm -f "$PID_FILE"
    echo "[OK] Queue worker stopped"
}

show_status() {
    echo "=========================================="
    echo "Queue Worker Status"
    echo "=========================================="

    if is_running; then
        local pid
        pid=$(get_pid)
        echo "[OK] Running (PID: $pid)"
        ps -p "$pid" -o pid,ppid,user,%cpu,%mem,etime,cmd 2>/dev/null || true
    else
        echo "[--] Not running"
    fi

    if [ -f "$LOG_FILE" ]; then
        echo ""
        echo "Recent log (last 15 lines):"
        echo "------------------------------------------"
        tail -15 "$LOG_FILE"
    fi
}

show_logs() {
    [ -f "$LOG_FILE" ] || { echo "[ERROR] No log file: $LOG_FILE"; return 1; }
    if [ "${1:-}" = "-f" ]; then
        tail -f "$LOG_FILE"
    else
        tail -50 "$LOG_FILE"
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
case "${1:-}" in
    start)   start_worker ;;
    stop)    stop_worker ;;
    restart) stop_worker; sleep 2; start_worker ;;
    status)  show_status ;;
    logs)    show_logs "${2:-}" ;;
    *)
        echo "OrangeScrum Queue Worker Manager"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs [-f]}"
        echo ""
        echo "Environment:"
        echo "  QUEUE_MAX_RUNTIME    Max runtime in seconds (0=infinite, default: 0)"
        echo "  QUEUE_RESTART_DELAY  Delay before restart (default: 3s)"
        echo "  QUEUE_MAX_RESTARTS   Max restarts per hour (default: 100)"
        echo ""
        echo "Files:"
        echo "  PID: $PID_FILE"
        echo "  Log: $LOG_FILE"
        exit 1
        ;;
esac
