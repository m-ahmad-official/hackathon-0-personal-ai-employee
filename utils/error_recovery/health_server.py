#!/usr/bin/env python3
"""
Health Monitoring Server - Gold Tier Phase 3
Provides HTTP health check endpoints for monitoring and watchdog integration.

Runs a simple HTTP server on localhost:8080 (configurable) exposing:
- /health - Overall system health
- /health/ready - Readiness probe (all critical services up)
- /health/live - Liveness probe (process is alive)
- /metrics - Circuit breaker stats, uptime, error counts
- /status - Detailed component status

Usage:
    python health_server.py --port 8080 --interval 30

Integrates with:
- Circuit breaker stats
- Process monitoring (watchers, MCP servers)
- Watchdog auto-restart
"""

import json
import time
import threading
import socket
import psutil
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Add project root to path for importing utils
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from utils.audit.logger import get_audit_logger, AuditEntry, LogLevel

logger = logging.getLogger(__name__)


@dataclass
class ComponentHealth:
    """Health status of a single component."""
    name: str
    status: str  # healthy, degraded, unhealthy, unknown
    last_check: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding non-serializable fields."""
        result = {
            "name": self.name,
            "status": self.status.value if hasattr(self.status, 'value') else self.status,
            "last_check": self.last_check.isoformat(),
            "error": self.error
        }
        # Copy details but exclude check_function (non-serializable)
        if "check_function" in self.details:
            clean_details = {k: v for k, v in self.details.items() if k != "check_function"}
            result["details"] = clean_details
        else:
            result["details"] = self.details.copy() if self.details else {}
        # Remove None/empty values
        return {k: v for k, v in result.items() if v is not None and v != {}}


class HealthMonitor:
    """
    Central health monitoring for all AI Employee components.

    Tracks:
    - MCP servers (odoo-mcp, social-mcp)
    - Watchers (gmail_watcher, whatsapp_watcher)
    - Scheduler
    - Database connections (PostgreSQL, Odoo)
    - External APIs (Facebook, Twitter, Gmail)
    - Disk space, memory usage

    Provides HTTP endpoints for:
    - Kubernetes probes
    - External monitoring (Grafana, Datadog)
    - Watchdog restart decisions
    """

    def __init__(self, port: int = 8080, interval: int = 30):
        self.port = port
        self.interval = interval
        self.components: Dict[str, ComponentHealth] = {}
        self.start_time = datetime.now()
        self._lock = threading.RLock()
        self._audit_logger = get_audit_logger()

        # Register default components
        self._register_components()

        # Start health check thread
        self._running = True
        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._check_thread = threading.Thread(target=self._run_checks, daemon=True)

    def _register_components(self):
        """Register all components to monitor."""
        components = [
            ("odoo_mcp", self._check_odoo_mcp),
            ("social_mcp", self._check_social_mcp),
            ("gmail_watcher", self._check_gmail_watcher),
            ("whatsapp_watcher", self._check_whatsapp_watcher),
            ("scheduler", self._check_scheduler),
            ("postgresql", self._check_postgresql),
            ("disk_space", self._check_disk_space),
            ("memory", self._check_memory),
        ]

        for name, check_func in components:
            self.components[name] = ComponentHealth(
                name=name,
                status="unknown",
                last_check=datetime.now(),
                details={}
            )
            # Store check function in details
            self.components[name].details["check_function"] = check_func

    def _run_server(self):
        """Run HTTP server in background thread."""
        handler = self._create_request_handler()
        server = HTTPServer(('localhost', self.port), handler)
        logger.info(f"Health server started on http://localhost:{self.port}")
        server.serve_forever()

    def _create_request_handler(self):
        """Create HTTP request handler with closure over health monitor."""
        monitor = self

        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                path = parsed.path
                query = parse_qs(parsed.query)

                response, status_code = monitor._handle_request(path, query)

                self.send_response(status_code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))

            def log_message(self, format, *args):
                """Suppress default logging."""
                pass

        return HealthHandler

    def _handle_request(self, path: str, query: parse_qs) -> tuple[Dict[str, Any], int]:
        """Handle HTTP request and return (response_dict, status_code)."""
        if path == '/health':
            overall = self.get_overall_health()
            response = {
                "status": overall,
                "components": {k: v.to_dict() for k, v in self.components.items()},
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds()
            }
            status = 200 if overall in ('healthy', 'degraded') else 503

        elif path == '/health/ready':
            ready = self.is_ready()
            response = {
                "ready": ready,
                "timestamp": datetime.now().isoformat()
            }
            status = 200 if ready else 503

        elif path == '/health/live':
            live = self.is_live()
            response = {
                "alive": live,
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds()
            }
            status = 200 if live else 503

        elif path == '/metrics':
            response = self.get_metrics()
            status = 200

        elif path == '/status':
            response = {
                "components": {k: v.to_dict() for k, v in self.components.items()},
                "timestamp": datetime.now().isoformat(),
                "uptime": str(datetime.now() - self.start_time)
            }
            status = 200

        else:
            response = {"error": "Not found"}
            status = 404

        return response, status

    def _run_checks(self):
        """Background thread: periodically check all components."""
        while self._running:
            try:
                self._perform_checks()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Health check thread error: {e}")
                time.sleep(self.interval)

    def _perform_checks(self):
        """Perform health checks for all components."""
        with self._lock:
            for name, health in self.components.items():
                check_func = health.details.get("check_function")
                if not check_func:
                    continue

                try:
                    # Run check
                    status, details = check_func()
                    health.status = status
                    health.details.update(details)
                    health.last_check = datetime.now()
                    health.error = None

                    # Log if degraded or unhealthy
                    if status in ('degraded', 'unhealthy'):
                        logger.warning(f"Component {name} is {status}: {details}")
                        self._audit_logger.log(AuditEntry(
                            id=f"health_{int(time.time())}",
                            timestamp=datetime.now().isoformat(),
                            level=LogLevel.WARNING.value,
                            actor="health_monitor",
                            action="component_unhealthy",
                            target=name,
                            context={"status": status, "details": details}
                        ))

                except Exception as e:
                    health.status = "unhealthy"
                    health.error = str(e)
                    health.last_check = datetime.now()
                    logger.error(f"Health check failed for {name}: {e}")

    # === Component Check Functions ===

    def _check_odoo_mcp(self) -> tuple[str, Dict[str, Any]]:
        """Check Odoo MCP server availability."""
        try:
            import requests
            response = requests.get("http://localhost:8069/web", timeout=5)
            if response.status_code in (200, 303, 302):
                return "healthy", {"http_status": response.status_code, "url": "http://localhost:8069"}
            else:
                return "unhealthy", {"http_status": response.status_code, "error": "Bad status"}
        except requests.exceptions.RequestException as e:
            return "unhealthy", {"error": str(e)}

    def _check_social_mcp(self) -> tuple[str, Dict[str, Any]]:
        """Check if social-mcp MCP server is responding."""
        # MCP servers communicate via stdio, hard to check HTTP
        # Check if process is running
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'social-mcp' in ' '.join(proc.info['cmdline'] or []):
                    return "healthy", {"pid": proc.info['pid']}
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return "unhealthy", {"error": "Process not found"}

    def _check_gmail_watcher(self) -> tuple[str, Dict[str, Any]]:
        """Check if gmail_watcher is running."""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'gmail_watcher' in ' '.join(proc.info['cmdline'] or []):
                    return "healthy", {"pid": proc.info['pid']}
            except:
                pass
        # Not unhealthy, just not running - could be offline
        return "unknown", {"error": "Watcher not running"}

    def _check_whatsapp_watcher(self) -> tuple[str, Dict[str, Any]]:
        """Check if whatsapp_watcher is running."""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'whatsapp_watcher' in ' '.join(proc.info['cmdline'] or []):
                    return "healthy", {"pid": proc.info['pid']}
            except:
                pass
        return "unknown", {"error": "Watcher not running"}

    def _check_scheduler(self) -> tuple[str, Dict[str, Any]]:
        """Check if scheduler is running."""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'scheduler/scheduler.py' in ' '.join(proc.info['cmdline'] or []):
                    return "healthy", {"pid": proc.info['pid']}
            except:
                pass
        return "unknown", {"error": "Scheduler not running"}

    def _check_postgresql(self) -> tuple[str, Dict[str, Any]]:
        """Check PostgreSQL database (for Odoo)."""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                user="odoo",
                password="odoo",
                database="odoo",
                connect_timeout=5
            )
            conn.close()
            return "healthy", {"connected": True}
        except Exception as e:
            return "unhealthy", {"error": str(e)}

    def _check_disk_space(self) -> tuple[str, Dict[str, Any]]:
        """Check available disk space."""
        import shutil
        total, used, free = shutil.disk_usage("/")
        free_gb = free // (2**30)
        if free_gb < 5:
            return "unhealthy", {"free_gb": free_gb, "error": "Less than 5GB free"}
        elif free_gb < 10:
            return "degraded", {"free_gb": free_gb, "warning": "Less than 10GB free"}
        else:
            return "healthy", {"free_gb": free_gb}

    def _check_memory(self) -> tuple[str, Dict[str, Any]]:
        """Check system memory."""
        mem = psutil.virtual_memory()
        if mem.percent > 95:
            return "unhealthy", {"percent": mem.percent, "error": "Memory几乎 full"}
        elif mem.percent > 85:
            return "degraded", {"percent": mem.percent, "warning": "High memory usage"}
        else:
            return "healthy", {"percent": mem.percent, "available_gb": mem.available // (2**30)}

    def get_overall_health(self) -> str:
        """Calculate overall health status."""
        statuses = [health.status for health in self.components.values() if health.status != 'unknown']
        if not statuses:
            return "unknown"
        if any(s == 'unhealthy' for s in statuses):
            return "unhealthy"
        elif any(s == 'degraded' for s in statuses):
            return "degraded"
        else:
            return "healthy"

    def is_ready(self) -> bool:
        """Readiness probe: all critical components healthy."""
        critical = ['odoo_mcp', 'postgresql']
        for name in critical:
            if self.components.get(name, ComponentHealth(name, 'unknown', datetime.now(), {})).status not in ('healthy', 'degraded'):
                return False
        return True

    def is_live(self) -> bool:
        """Liveness probe: process is alive."""
        return self._running

    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics in Prometheus-like format (dict)."""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "components": {},
            "circuit_breakers": {}
        }

        # Component metrics
        for name, health in self.components.items():
            metrics["components"][name] = {
                "status": health.status,
                "last_check": health.last_check.isoformat()
            }

        # Circuit breaker metrics
        try:
            from utils.error_recovery.retry_circuit import get_all_circuit_stats
            metrics["circuit_breakers"] = get_all_circuit_stats()
        except ImportError:
            pass

        return metrics

    def start(self):
        """Start health monitoring."""
        logger.info("Starting Health Monitor...")
        self._server_thread.start()
        self._check_thread.start()

    def stop(self):
        """Stop health monitoring."""
        self._running = False


# Global health monitor instance
_health_monitor: Optional[HealthMonitor] = None


def start_health_monitor(port: int = 8080, interval: int = 30) -> HealthMonitor:
    """Start global health monitor."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor(port=port, interval=interval)
        _health_monitor.start()
    return _health_monitor


def get_health_monitor() -> Optional[HealthMonitor]:
    """Get global health monitor instance."""
    return _health_monitor


if __name__ == "__main__":
    import argparse
    import logging

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Health Monitoring Server")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port (default: 8080)")
    parser.add_argument("--interval", type=int, default=30, help="Check interval in seconds (default: 30)")
    args = parser.parse_args()

    monitor = start_health_monitor(port=args.port, interval=args.interval)

    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()
        print("\nHealth monitor stopped")
