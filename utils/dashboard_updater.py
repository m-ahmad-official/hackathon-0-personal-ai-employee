#!/usr/bin/env python3
"""
Dashboard Updater - Gold Tier Phase 4
Automatically updates Dashboard.md with live metrics from all system components.

Fetches data from:
- Health server (http://localhost:8080/metrics)
- Odoo MCP (via tools)
- Social MCP (via tools or last audit entries)
- Audit logs (task completion stats)

Usage:
    python utils/dashboard_updater.py [--interval SECONDS] [--once]

    --interval: Run continuously, updating every N seconds (default: 300)
    --once: Run single update and exit (default)
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

try:
    import requests
except ImportError:
    print("Error: requests library required. Install: pip install requests")
    sys.exit(1)

# Import audit logger
try:
    from utils.audit.logger import get_audit_logger
except ImportError:
    print("Warning: Audit logger not available, audit metrics will be skipped")
    get_audit_logger = None

# Import Odoo MCP tools (we'll import server module)
try:
    sys.path.insert(0, os.path.join(project_root, 'mcp-servers', 'odoo-mcp'))
    from server import OdooMCPServer
    ODOO_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Odoo MCP not available: {e}")
    ODOO_AVAILABLE = False

VAULT_PATH = Path("AI_Employee_Vault")
DASHBOARD_PATH = VAULT_PATH / "Dashboard.md"
HEALTH_URL = "http://localhost:8080/metrics"


def fetch_health_metrics() -> Dict[str, Any]:
    """Fetch health metrics from monitoring server."""
    try:
        response = requests.get(HEALTH_URL, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Failed to fetch health metrics: {e}")
    return {}


def fetch_odoo_metrics() -> Dict[str, Any]:
    """Query Odoo for key financial metrics."""
    if not ODOO_AVAILABLE:
        return {}

    try:
        server = OdooMCPServer()
        metrics = {
            "accounts_receivable": None,
            "recent_invoices_count": 0,
            "overdue_invoices": 0,
            "total_invoices_amount": 0.0
        }

        # Get AR balance (account code typically 121000)
        try:
            ar_balance = server._get_account_balance("121000")
            metrics["accounts_receivable"] = ar_balance.get("balance", 0)
        except Exception as e:
            print(f"  Could not fetch AR balance: {e}")

        # Get recent invoices (last 7 days)
        try:
            # Use list_recent_invoices with limit
            result = server._list_recent_invoices(limit=50)
            invoices = result.get("invoices", [])
            today = datetime.now().date()
            week_ago = today - timedelta(days=7)

            recent_invoices = []
            for inv in invoices:
                inv_date_str = inv.get("invoice_date", "")
                try:
                    inv_date = datetime.strptime(inv_date_str, "%Y-%m-%d").date()
                    if inv_date >= week_ago:
                        recent_invoices.append(inv)
                except:
                    pass

            metrics["recent_invoices_count"] = len(recent_invoices)
            metrics["total_invoices_amount"] = sum(inv.get("amount_total", 0) for inv in recent_invoices)

            # Count overdue (invoice_date in past, state not paid)
            overdue_count = 0
            for inv in invoices:
                state = inv.get("payment_state", "")
                if state in ("not_paid", "partial"):
                    overdue_count += 1
            metrics["overdue_invoices"] = overdue_count

        except Exception as e:
            print(f"  Could not fetch recent invoices: {e}")

        return metrics

    except Exception as e:
        print(f"Odoo connection failed: {e}")
        return {}


def fetch_social_metrics() -> Dict[str, Any]:
    """Get social media stats from audit log or direct API calls."""
    # For now, get from audit log: last 24h posts
    if not get_audit_logger:
        return {}

    try:
        logger = get_audit_logger()
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        entries = logger.read_logs(
            start_date=yesterday,
            action=["facebook_post", "instagram_post", "twitter_tweet"],
            limit=100
        )

        metrics = {
            "facebook_posts": 0,
            "instagram_posts": 0,
            "twitter_tweets": 0,
            "last_facebook": None,
            "last_instagram": None,
            "last_twitter": None
        }

        for entry in entries:
            action = entry.action
            timestamp = entry.timestamp

            if action == "facebook_post":
                metrics["facebook_posts"] += 1
                if not metrics["last_facebook"]:
                    metrics["last_facebook"] = timestamp
            elif action == "instagram_post":
                metrics["instagram_posts"] += 1
                if not metrics["last_instagram"]:
                    metrics["last_instagram"] = timestamp
            elif action == "twitter_tweet":
                metrics["twitter_tweets"] += 1
                if not metrics["last_twitter"]:
                    metrics["last_twitter"] = timestamp

        return metrics

    except Exception as e:
        print(f"Could not fetch social metrics: {e}")
        return {}


def fetch_task_metrics() -> Dict[str, Any]:
    """Count tasks completed today and this week."""
    metrics = {
        "completed_today": 0,
        "completed_this_week": 0,
        "avg_completion_time_minutes": 0.0
    }

    try:
        done_path = VAULT_PATH / "Done"
        if not done_path.exists():
            return metrics

        today = datetime.now().date()
        week_ago = today - timedelta(days=7)

        completion_times = []
        for filepath in done_path.glob("*.md"):
            # Parse date from filename: ITEM_YYYYMMDD_HHMMSS.md or PLAN_...
            # Could also check file modification time
            try:
                mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                if mtime.date() == today:
                    metrics["completed_today"] += 1
                if mtime.date() >= week_ago:
                    metrics["completed_this_week"] += 1
                    # Rough estimate: if file has duration in audit log, use that
                    # For now skip
            except:
                pass

        if completion_times:
            metrics["avg_completion_time_minutes"] = sum(completion_times) / len(completion_times)

    except Exception as e:
        print(f"Could not count tasks: {e}")

    return metrics


def generate_metrics_section(health: Dict, odoo: Dict, social: Dict, tasks: Dict) -> str:
    """Generate markdown section for live metrics."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    section = f"""## 🔄 Live Metrics (Last Updated: {timestamp})

**System Health**
- Overall Status: {health.get("status", "unknown").upper()}
- Uptime: {health.get("uptime_seconds", 0) / 60:.1f} minutes
- Odoo: {'✅' if health.get('components', {}).get('odoo_mcp', {}).get('status') == 'healthy' else '❌'}
- PostgreSQL: {'✅' if health.get('components', {}).get('postgresql', {}).get('status') == 'healthy' else '❌'}

**Financial (Odoo)**
- Accounts Receivable: ${odoo.get('accounts_receivable', 0):,.2f}
- Invoices (Last 7 Days): {odoo.get('recent_invoices_count', 0)}
- Overdue Invoices: {odoo.get('overdue_invoices', 0)}
- Total Invoiced (7D): ${odoo.get('total_invoices_amount', 0):,.2f}

**Social Media (Last 24h)**
- Facebook Posts: {social.get('facebook_posts', 0)}
- Instagram Posts: {social.get('instagram_posts', 0)}
- Twitter Tweets: {social.get('twitter_tweets', 0)}

**Task Automation**
- Completed Today: {tasks.get('completed_today', 0)}
- Completed This Week: {tasks.get('completed_this_week', 0)}

---

"""
    return section


def update_dashboard(metrics_section: str):
    """Update Dashboard.md with new metrics section."""
    if not DASHBOARD_PATH.exists():
        print(f"Dashboard not found at {DASHBOARD_PATH}")
        return False

    try:
        content = DASHBOARD_PATH.read_text()

        # Remove old metrics section if exists
        if "## 🔄 Live Metrics" in content:
            # Find start of metrics section and remove until next ## or end
            lines = content.split('\n')
            new_lines = []
            in_metrics = False
            for line in lines:
                if line.startswith("## 🔄 Live Metrics"):
                    in_metrics = True
                    continue
                if in_metrics and line.startswith("##"):
                    in_metrics = False
                    new_lines.append(line)
                    continue
                if not in_metrics:
                    new_lines.append(line)
            content = '\n'.join(new_lines)

        # Insert new metrics section after first heading or at start
        lines = content.split('\n')
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('# '):
                insert_idx = i + 2  # After title and blank line
                break
            if line.startswith('## '):
                insert_idx = i + 1
                break

        lines.insert(insert_idx, metrics_section.strip())
        content = '\n'.join(lines)

        DASHBOARD_PATH.write_text(content)
        print(f"Dashboard updated successfully at {datetime.now()}")
        return True

    except Exception as e:
        print(f"Failed to update dashboard: {e}")
        return False


def run_once():
    """Single update cycle."""
    print(f"[{datetime.now()}] Updating dashboard...")

    # Fetch all metrics
    print("  Fetching health metrics...")
    health = fetch_health_metrics()

    print("  Fetching Odoo metrics...")
    odoo = fetch_odoo_metrics() if ODOO_AVAILABLE else {}

    print("  Fetching social metrics...")
    social = fetch_social_metrics()

    print("  Fetching task metrics...")
    tasks = fetch_task_metrics()

    # Generate section
    section = generate_metrics_section(health, odoo, social, tasks)

    # Update dashboard
    update_dashboard(section)

    print(f"[{datetime.now()}] Dashboard update complete")


def run_continuous(interval: int):
    """Run continuously with interval in seconds."""
    print(f"Starting continuous dashboard updater (interval: {interval}s)")
    try:
        while True:
            run_once()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nDashboard updater stopped")


def main():
    parser = argparse.ArgumentParser(description="Dashboard Updater")
    parser.add_argument("--interval", type=int, default=300,
                        help="Update interval in seconds (default: 300)")
    parser.add_argument("--once", action="store_true",
                        help="Run single update and exit (default)")
    args = parser.parse_args()

    if args.once:
        run_once()
    else:
        run_continuous(args.interval)


if __name__ == "__main__":
    main()
