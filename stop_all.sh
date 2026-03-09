#!/bin/bash
#
# Stop All AI Employee Services
# Gold Tier Phase 4 - Production Deployment
#
# Gracefully stops all running services by PID files.
#
# Usage: ./stop_all.sh
#

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "Stopping AI Employee Services"
echo "=========================================="
echo ""

PID_FILES=(
    "utils/error_recovery/health_server.pid"
    "utils/dashboard_updater.pid"
    "utils/event_bus/dashboard_consumer.pid"
    "utils/event_bus/email_odoo_consumer.pid"
    "watchers/gmail_watcher.pid"
    "watchers/whatsapp_watcher.pid"
    "watchers/approved_executor.pid"
    "scheduler/scheduler.pid"
)

STOPPED=0
FAILED=0

for pidfile in "${PID_FILES[@]}"; do
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile" 2>/dev/null || echo "")
        if [ -n "$pid" ]; then
            echo "Stopping $(basename "$pidfile") (PID $pid)..."
            kill "$pid" 2>/dev/null && rm -f "$pidfile" && echo "  ✅ Stopped" && STOPPED=$((STOPPED+1)) || echo "  ⚠ Already stopped or failed" && FAILED=$((FAILED+1))
        else
            echo "  ⚠ Empty PID file: $pidfile"
        fi
    else
        echo "  ⚠ No PID file: $pidfile (not running?)"
    fi
done

# Stop Odoo Docker container
echo ""
echo "Stopping Odoo (Docker)..."
if command -v docker &> /dev/null; then
    cd mcp-servers/odoo-mcp
    if docker-compose ps | grep -q "odoo"; then
        docker-compose down
        echo "  ✅ Odoo container stopped"
    else
        echo "  ⚠ Odoo container not running"
    fi
    cd "$PROJECT_ROOT"
else
    echo "  ⚠ Docker not found"
fi

echo ""
echo "=========================================="
echo "Stop complete: $STOPPED services stopped, $FAILED had issues"
echo "=========================================="
echo ""
