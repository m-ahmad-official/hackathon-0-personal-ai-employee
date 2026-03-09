#!/bin/bash
#
# Start All AI Employee Services
# Gold Tier Phase 4 - Production Deployment
#
# This script starts all components:
# - Odoo Docker container (PostgreSQL + Odoo)
# - Health Monitor (port 8080)
# - Dashboard Updater (auto-refresh)
# - Event Bus Consumers (dashboard, email-odoo)
# - Gmail Watcher (if configured)
# - WhatsApp Watcher (if configured)
# - Approved Executor
# - Scheduler (if configured)
#
# Usage: ./start_all.sh
# Logs: Each service logs to its own file in logs/
#

set -e  # Exit on error

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "Starting AI Employee Services"
echo "=========================================="
echo ""

# Create log directory
mkdir -p logs

# 1. Start Odoo (Docker)
echo "[1/9] Starting Odoo..."
if command -v docker &> /dev/null; then
    cd mcp-servers/odoo-mcp
    docker-compose up -d
    cd "$PROJECT_ROOT"
    echo "  ✅ Odoo started (docker-compose up -d)"
    # Wait for Odoo to be ready
    echo "  Waiting for Odoo to initialize..."
    sleep 10
else
    echo "  ⚠ Docker not found, skipping Odoo"
fi

# 2. Start Health Monitor
echo "[2/9] Starting Health Monitor..."
if [ ! -f "utils/error_recovery/health_server.py" ]; then
    echo "  ⚠ Health server not found"
else
    nohup python utils/error_recovery/health_server.py --port 8080 --interval 30 > logs/health_monitor.log 2>&1 &
    echo $! > utils/error_recovery/health_server.pid
    echo "  ✅ Health monitor started (PID $(cat utils/error_recovery/health_server.pid 2>/dev/null || echo ?))"
fi

# 3. Start Dashboard Updater
echo "[3/9] Starting Dashboard Updater..."
nohup python utils/dashboard_updater.py --interval 300 > logs/dashboard_updater.log 2>&1 &
echo $! > utils/dashboard_updater.pid
echo "  ✅ Dashboard updater started (PID $(cat utils/dashboard_updater.pid 2>/dev/null || echo ?))"

# 4. Start Event Bus Dashboard Consumer
echo "[4/9] Starting Event Bus Dashboard Consumer..."
nohup python utils/event_bus/consumers/dashboard_consumer.py > logs/dashboard_consumer.log 2>&1 &
echo $! > utils/event_bus/dashboard_consumer.pid
echo "  ✅ Dashboard consumer started (PID $(cat utils/event_bus/dashboard_consumer.pid 2>/dev/null || echo ?))"

# 5. Start Event Bus Email-Odoo Consumer
echo "[5/9] Starting Event Bus Email→Odoo Consumer..."
nohup python utils/event_bus/consumers/email_odoo_consumer.py > logs/email_odoo_consumer.log 2>&1 &
echo $! > utils/event_bus/email_odoo_consumer.pid
echo "  ✅ Email-Odoo consumer started (PID $(cat utils/event_bus/email_odoo_consumer.pid 2>/dev/null || echo ?))"

# 6. Start Gmail Watcher (if credentials exist)
echo "[6/9] Starting Gmail Watcher..."
if [ -f "credentials.json" ]; then
    nohup python watchers/gmail_watcher.py --vault AI_Employee_Vault --credentials credentials.json --check-interval 60 > logs/gmail_watcher.log 2>&1 &
    echo $! > watchers/gmail_watcher.pid
    echo "  ✅ Gmail watcher started (PID $(cat watchers/gmail_watcher.pid 2>/dev/null || echo ?))"
else
    echo "  ⚠ No credentials.json found, skipping Gmail watcher"
fi

# 7. Start WhatsApp Watcher (if session exists)
echo "[7/9] Starting WhatsApp Watcher..."
if [ -d "session" ]; then
    nohup python watchers/whatsapp_watcher.py --vault AI_Employee_Vault --session-path ./session --check-interval 30 > logs/whatsapp_watcher.log 2>&1 &
    echo $! > watchers/whatsapp_watcher.pid
    echo "  ✅ WhatsApp watcher started (PID $(cat watchers/whatsapp_watcher.pid 2>/dev/null || echo ?))"
else
    echo "  ⚠ No session directory found, skipping WhatsApp watcher"
fi

# 8. Start Approved Executor
echo "[8/9] Starting Approved Executor..."
nohup python watchers/approved_executor.py --vault AI_Employee_Vault --watch > logs/approved_executor.log 2>&1 &
echo $! > watchers/approved_executor.pid
echo "  ✅ Approved executor started (PID $(cat watchers/approved_executor.pid 2>/dev/null || echo ?))"

# 9. Start Scheduler (if config exists)
echo "[9/9] Starting Scheduler..."
if [ -f "scheduler/config.yaml" ]; then
    nohup python scheduler/scheduler.py --config scheduler/config.yaml > logs/scheduler.log 2>&1 &
    echo $! > scheduler/scheduler.pid
    echo "  ✅ Scheduler started (PID $(cat scheduler/scheduler.pid 2>/dev/null || echo ?))"
else
    echo "  ⚠ No scheduler config found, skipping"
fi

echo ""
echo "=========================================="
echo "All services started!"
echo "=========================================="
echo ""
echo "Running services:"
echo "  - Odoo (Docker)            : http://localhost:8069"
echo "  - Health Monitor           : http://localhost:8080"
echo "  - Dashboard Updater        : Every 5 minutes"
echo "  - Event Bus Consumers      : Running"
echo "  - Gmail Watcher (optional) : Polling every 60s"
echo "  - WhatsApp Watcher (opt)   : Polling every 30s"
echo "  - Approved Executor        : Watching /Approved/"
echo "  - Scheduler (optional)     : As configured"
echo ""
echo "Log files in logs/ directory:"
ls -lh logs/
echo ""
echo "To stop all services: ./stop_all.sh"
echo "To check status: ./status.sh"
echo ""
