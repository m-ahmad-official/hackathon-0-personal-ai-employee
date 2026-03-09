#!/bin/bash
# Status Check for AI Employee Services
# Gold Tier Phase 4

cd "$(dirname "$0")"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "AI Employee Services Status"
echo "=========================================="
echo ""

# 1. Process Status
echo "## Process Status"
echo ""

services=(
    "utils/error_recovery/health_server.pid:Health Monitor"
    "utils/dashboard_updater.pid:Dashboard Updater"
    "utils/event_bus/dashboard_consumer.pid:Event Dashboard Consumer"
    "utils/event_bus/email_odoo_consumer.pid:Event Email-Odoo Consumer"
    "watchers/gmail_watcher.pid:Gmail Watcher"
    "watchers/whatsapp_watcher.pid:WhatsApp Watcher"
    "watchers/approved_executor.pid:Approved Executor"
    "scheduler/scheduler.pid:Scheduler"
)

RUNNING=0
STOPPED=0

for entry in "${services[@]}"; do
    IFS=':' read -r pidfile name <<< "$entry"
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile" 2>/dev/null || echo "")
        if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
            echo "  [RUNNING] $name (PID $pid)"
            RUNNING=$((RUNNING+1))
        else
            echo "  [STOPPED] $name (PID file but process not running)"
            STOPPED=$((STOPPED+1))
        fi
    else
        echo "  [STOPPED] $name (no PID file)"
        STOPPED=$((STOPPED+1))
    fi
done

echo ""

# 2. Docker Containers
echo "## Docker Containers"
echo ""
if command -v docker > /dev/null; then
    if docker ps --format '{{.Names}}' | grep -q 'odoo'; then
        echo "  [RUNNING] Odoo container"
        docker ps --filter "name=odoo" --format "    Name: {{.Names}}\n    Status: {{.Status}}\n    Ports: {{.Ports}}"
    else
        echo "  [STOPPED] Odoo container"
    fi
else
    echo "  Docker not available"
fi

echo ""

# 3. Health Check
echo "## Health Check"
echo ""
if command -v curl > /dev/null; then
    health=$(curl -s http://localhost:8080/health 2>/dev/null || echo '{"status":"unreachable"}')
    status=$(echo "$health" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")
    if [ "$status" = "healthy" ]; then
        echo "  [HEALTHY] Overall system health"
    elif [ "$status" != "unreachable" ]; then
        echo "  [DEGRADED] System status: $status"
    else
        echo "  [UNHEALTHY] Health server unreachable"
    fi
    echo "    Raw status: $status"
else
    echo "  Curl not available"
fi

echo ""

# 4. Event Bus Status
echo "## Event Bus"
echo ""
EVENTS_DIR="AI_Employee_Vault/Events"
if [ -d "$EVENTS_DIR" ]; then
    pending=$(ls -1 "$EVENTS_DIR"/*.json 2>/dev/null | wc -l)
    processed=$(ls -1 "$EVENTS_DIR"/processed/*.json 2>/dev/null | wc -l)
    echo "  Pending events: $pending"
    echo "  Processed events: $processed"
else
    echo "  Events directory not found"
fi

echo ""
echo "=========================================="
echo "Summary: $RUNNING running, $STOPPED stopped"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  curl http://localhost:8080/health"
echo "  tail -f logs/*.log"
echo "  ./stop_all.sh"
echo ""
