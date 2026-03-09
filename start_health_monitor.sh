#!/bin/bash
# Health Monitor Launcher - Gold Tier Phase 3
# Starts the health monitoring server in the background

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/utils/error_recovery/health_server.pid"
LOG_FILE="$SCRIPT_DIR/utils/error_recovery/health_server.log"

# Default configuration
PORT=${HEALTH_PORT:-8080}
INTERVAL=${HEALTH_INTERVAL:-30}

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Health monitor already running (PID $PID)"
        exit 1
    else
        echo "Removing stale PID file"
        rm "$PID_FILE"
    fi
fi

# Start health monitor
echo "Starting health monitor on port $PORT (interval: ${INTERVAL}s)"
cd "$SCRIPT_DIR"
python utils/error_recovery/health_server.py --port "$PORT" --interval "$INTERVAL" > "$LOG_FILE" 2>&1 &
PID=$!

# Save PID
echo "$PID" > "$PID_FILE"
echo "Health monitor started with PID $PID"
echo "Log: tail -f $LOG_FILE"
echo "Health endpoint: http://localhost:$PORT/health"
echo ""
echo "To stop: kill $PID && rm $PID_FILE"
