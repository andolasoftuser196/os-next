#!/bin/bash
# Queue Worker Wrapper with Auto-Restart
# Run OrangeScrum Queue Worker in background with automatic crash recovery
# Usage: ./queue-worker.sh start|stop|restart|status|logs

set +e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables from .env
ENV_FILE=".env"
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

# Configuration
PID_FILE="$SCRIPT_DIR/queue-worker.pid"
LOG_FILE="$SCRIPT_DIR/queue-worker.log"
MAX_RUNTIME="${QUEUE_MAX_RUNTIME:-0}"  # 0 = infinite
RESTART_DELAY="${QUEUE_RESTART_DELAY:-3}"  # seconds to wait before restart
MAX_RESTARTS="${QUEUE_MAX_RESTARTS:-100}"  # max restarts per hour

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if worker is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            return 0
        else
            # PID file exists but process is dead
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Start the queue worker
start_worker() {
    if is_running; then
        log_warn "Queue worker is already running (PID: $(cat $PID_FILE))"
        return 1
    fi

    log_info "Starting queue worker..."
    
    # Create log file if it doesn't exist
    touch "$LOG_FILE"
    
    # Start in background with nohup
    nohup bash -c "
        # Track restart attempts
        RESTART_COUNT=0
        HOUR_START=\$(date +%s)
        
        while true; do
            # Check if we've exceeded max restarts in the last hour
            CURRENT_TIME=\$(date +%s)
            if [ \$((CURRENT_TIME - HOUR_START)) -ge 3600 ]; then
                # Reset counter every hour
                RESTART_COUNT=0
                HOUR_START=\$CURRENT_TIME
            fi
            
            if [ \$RESTART_COUNT -ge $MAX_RESTARTS ]; then
                echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Max restarts ($MAX_RESTARTS) reached in the last hour. Stopping.\" >> \"$LOG_FILE\"
                exit 1
            fi
            
            # Log restart
            if [ \$RESTART_COUNT -gt 0 ]; then
                echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] INFO: Restarting worker (attempt \$RESTART_COUNT)...\" >> \"$LOG_FILE\"
            else
                echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] INFO: Starting queue worker...\" >> \"$LOG_FILE\"
            fi
            
            # Run the queue worker
            if [ $MAX_RUNTIME -eq 0 ]; then
                # Infinite runtime - don't pass max-runtime parameter
                $SCRIPT_DIR/cake.sh bin/cake.php queue worker --verbose >> \"$LOG_FILE\" 2>&1
            else
                # Specific runtime limit
                $SCRIPT_DIR/cake.sh bin/cake.php queue worker --max-runtime $MAX_RUNTIME --verbose >> \"$LOG_FILE\" 2>&1
            fi
            EXIT_CODE=\$?
            
            # Log exit
            echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] WARN: Worker exited with code \$EXIT_CODE\" >> \"$LOG_FILE\"
            
            # If exit code is 0, it's a clean shutdown - don't restart
            if [ \$EXIT_CODE -eq 0 ]; then
                echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] INFO: Clean shutdown detected. Exiting.\" >> \"$LOG_FILE\"
                break
            fi
            
            # Increment restart counter
            RESTART_COUNT=\$((RESTART_COUNT + 1))
            
            # Wait before restarting
            echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] INFO: Waiting ${RESTART_DELAY}s before restart...\" >> \"$LOG_FILE\"
            sleep $RESTART_DELAY
        done
    " > /dev/null 2>&1 &
    
    WRAPPER_PID=$!
    echo $WRAPPER_PID > "$PID_FILE"
    
    log_info "Queue worker started (PID: $WRAPPER_PID)"
    log_info "Logs: $LOG_FILE"
    
    # Show initial log output
    sleep 2
    tail -20 "$LOG_FILE"
}

# Stop the queue worker
stop_worker() {
    if ! is_running; then
        log_warn "Queue worker is not running"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    log_info "Stopping queue worker (PID: $PID)..."
    
    # Kill the wrapper process and all its children
    pkill -P $PID 2>/dev/null
    kill $PID 2>/dev/null
    
    # Wait for graceful shutdown
    for i in {1..10}; do
        if ! ps -p $PID > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    
    # Force kill if still running
    if ps -p $PID > /dev/null 2>&1; then
        log_warn "Forcing worker shutdown..."
        kill -9 $PID 2>/dev/null
        pkill -9 -P $PID 2>/dev/null
    fi
    
    rm -f "$PID_FILE"
    log_info "Queue worker stopped"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: Worker manually stopped" >> "$LOG_FILE"
}

# Restart the queue worker
restart_worker() {
    log_info "Restarting queue worker..."
    stop_worker
    sleep 2
    start_worker
}

# Show worker status
show_status() {
    echo "=========================================="
    echo "Queue Worker Status"
    echo "=========================================="
    
    if is_running; then
        PID=$(cat "$PID_FILE")
        log_info "Running (PID: $PID)"
        
        # Show process info
        ps -p $PID -o pid,ppid,user,%cpu,%mem,etime,cmd
        
        # Count how many actual worker processes
        WORKER_COUNT=$(pgrep -P $PID | wc -l)
        echo ""
        echo "Active worker processes: $WORKER_COUNT"
        
        # Show recent log entries
        if [ -f "$LOG_FILE" ]; then
            echo ""
            echo "Recent log entries (last 15 lines):"
            echo "----------------------------------------"
            tail -15 "$LOG_FILE"
        fi
    else
        log_error "Not running"
        
        # Show last few log entries if available
        if [ -f "$LOG_FILE" ]; then
            echo ""
            echo "Last log entries:"
            echo "----------------------------------------"
            tail -10 "$LOG_FILE"
        fi
    fi
}

# Show logs
show_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        log_error "Log file not found: $LOG_FILE"
        return 1
    fi
    
    # If -f flag is provided, follow the log
    if [ "$1" = "-f" ]; then
        tail -f "$LOG_FILE"
    else
        # Show last 50 lines by default
        tail -50 "$LOG_FILE"
    fi
}

# Main command dispatcher
case "${1:-}" in
    start)
        start_worker
        ;;
    stop)
        stop_worker
        ;;
    restart)
        restart_worker
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    *)
        echo "OrangeScrum Queue Worker Manager"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the queue worker in background"
        echo "  stop     - Stop the queue worker"
        echo "  restart  - Restart the queue worker"
        echo "  status   - Show worker status and recent logs"
        echo "  logs     - Show recent log entries (use -f to follow)"
        echo ""
        echo "Environment Variables:"
        echo "  QUEUE_MAX_RUNTIME      - Max runtime in seconds (default: 0 = infinite)"
        echo "  QUEUE_RESTART_DELAY    - Delay before restart in seconds (default: 3)"
        echo "  QUEUE_MAX_RESTARTS     - Max restarts per hour (default: 100)"
        echo ""
        echo "Files:"
        echo "  PID:  $PID_FILE"
        echo "  LOG:  $LOG_FILE"
        exit 1
        ;;
esac
