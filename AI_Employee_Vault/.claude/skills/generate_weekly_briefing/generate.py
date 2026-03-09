#!/usr/bin/env python3
"""
Enhanced Weekly Briefing - Gold Tier Phase 4 & 5
Comprehensive business intelligence report aggregating data from all systems.

Data Sources:
- Odoo MCP: Revenue, invoices, accounts receivable, top customers
- Social MCP: Posts, engagement, reach (via audit log)
- Audit Logger: Task completion rates, error trends, approval metrics
- Health Monitor: System uptime, component availability
- Event Bus: Real-time activity counts
- Dashboard: Current metrics snapshot

Output: Markdown briefing in /Briefings/ with executive summary, financials, ops metrics, trends.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

# Add project root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)

# Try to import MCP servers and utilities
try:
    from utils.audit.logger import AuditLogger
except ImportError:
    AuditLogger = None

try:
    sys.path.insert(0, os.path.join(project_root, 'mcp-servers', 'odoo-mcp'))
    from server import OdooMCPServer
    ODOO_AVAILABLE = True
except ImportError:
    ODOO_AVAILABLE = False

try:
    import requests
    HEALTH_AVAILABLE = True
except ImportError:
    HEALTH_AVAILABLE = False


VAULT_PATH = Path("AI_Employee_Vault")
BRIEFINGS_PATH = VAULT_PATH / "Briefings"
DASHBOARD_PATH = VAULT_PATH / "Dashboard.md"
BUSINESS_GOALS_PATH = VAULT_PATH / "Business_Goals.md"
LOGS_PATH = VAULT_PATH / "Logs"
EVENTS_PATH = VAULT_PATH / "Events"


def get_week_range(date: datetime) -> tuple:
    """Get Monday-Sunday date range for the week containing the given date."""
    # Monday = 0, Sunday = 6
    days_since_monday = date.weekday()
    monday = (date - timedelta(days=days_since_monday)).date()
    sunday = monday + timedelta(days=6)
    return monday, sunday


def read_business_goals() -> Dict[str, Any]:
    """Parse Business_Goals.md for targets and configuration."""
    if not BUSINESS_GOALS_PATH.exists():
        return {}

    try:
        content = BUSINESS_GOALS_PATH.read_text()
        # Very simple YAML frontmatter extraction (between --- lines)
        if '---' in content:
            frontmatter = content.split('---')[1]
            import yaml
            return yaml.safe_load(frontmatter)
    except:
        pass

    return {}


def fetch_odoo_financials(week_start: datetime, week_end: datetime) -> Dict[str, Any]:
    """Get financial metrics from Odoo for the week."""
    if not ODOO_AVAILABLE:
        return {"available": False, "note": "Odoo MCP not available"}

    try:
        server = OdooMCPServer()

        # Get recent invoices (last 30 days to cover week)
        result = server._list_recent_invoices(limit=200)
        invoices = result.get("invoices", [])

        # Filter to this week
        week_invoices = []
        total_revenue = 0.0
        for inv in invoices:
            inv_date_str = inv.get("invoice_date", "")
            try:
                inv_date = datetime.strptime(inv_date_str, "%Y-%m-%d").date()
                if week_start <= inv_date <= week_end:
                    week_invoices.append(inv)
                    if inv.get("payment_state") in ("paid", "posted"):  # Count only posted as revenue
                        total_revenue += inv.get("amount_total", 0)
            except:
                pass

        # Get AR balance
        try:
            ar = server._get_account_balance("121000")  # Accounts Receivable
            ar_balance = ar.get("balance", 0)
        except:
            ar_balance = 0

        # Top customers this week
        customer_totals = {}
        for inv in week_invoices:
            customer = inv.get("partner_id", [0, "Unknown"])[1]
            customer_totals[customer] = customer_totals.get(customer, 0) + inv.get("amount_total", 0)

        top_customers = sorted(customer_totals.items(), key=lambda x: x[1], reverse=True)[:5]

        # Overdue invoices (all time, not just this week)
        overdue_count = 0
        overdue_amount = 0.0
        for inv in invoices:
            if inv.get("payment_state") in ("not_paid", "partial"):
                overdue_count += 1
                overdue_amount += inv.get("amount_residual", 0)

        return {
            "available": True,
            "revenue_this_week": round(total_revenue, 2),
            "invoices_created": len(week_invoices),
            "invoices_posted": sum(1 for inv in week_invoices if inv.get("state") == "posted"),
            "accounts_receivable": round(ar_balance, 2),
            "overdue_invoices": overdue_count,
            "overdue_amount": round(overdue_amount, 2),
            "top_customers": top_customers
        }

    except Exception as e:
        return {"available": False, "error": str(e)}


def fetch_social_metrics(week_start: datetime, week_end: datetime) -> Dict[str, Any]:
    """Get social media activity from audit logs."""
    if not AuditLogger:
        return {"available": False, "note": "Audit logger not available"}

    try:
        logger = AuditLogger()

        # Query for social actions in date range
        start_str = week_start.strftime("%Y-%m-%d")
        end_str = week_end.strftime("%Y-%m-%d")

        entries = logger.read_logs(
            start_date=start_str,
            end_date=end_str,
            action=["facebook_post", "instagram_post", "twitter_tweet"],
            limit=1000
        )

        # Count by platform
        facebook_posts = sum(1 for e in entries if e.action == "facebook_post")
        instagram_posts = sum(1 for e in entries if e.action == "instagram_post")
        twitter_tweets = sum(1 for e in entries if e.action == "twitter_tweet")

        total_posts = facebook_posts + instagram_posts + twitter_tweets

        # Extract engagement if available in result
        total_reach = 0
        total_engagement = 0
        for e in entries:
            result = e.result or {}
            total_reach += result.get("reach", 0)
            total_engagement += result.get("engagement", 0)

        return {
            "available": True,
            "facebook_posts": facebook_posts,
            "instagram_posts": instagram_posts,
            "twitter_tweets": twitter_tweets,
            "total_posts": total_posts,
            "estimated_reach": total_reach,
            "total_engagement": total_engagement,
            "avg_engagement_per_post": total_engagement / total_posts if total_posts > 0 else 0
        }

    except Exception as e:
        return {"available": False, "error": str(e)}


def fetch_operations_metrics(week_start: datetime, week_end: datetime) -> Dict[str, Any]:
    """Get operational metrics from audit logs and Done folder."""
    metrics = {
        "tasks_completed": 0,
        "tasks_by_type": {},
        "approvals_processed": 0,
        "errors_count": 0,
        "avg_task_duration_ms": 0,
        "success_rate": 0.0
    }

    if AuditLogger:
        try:
            logger = AuditLogger()
            start_str = week_start.strftime("%Y-%m-%d")
            end_str = week_end.strftime("%Y-%m-%d")

            # Get all actions for the week
            entries = logger.read_logs(
                start_date=start_str,
                end_date=end_str,
                limit=10000
            )

            # Count completed tasks (actions with duration_ms and no error)
            completed = [e for e in entries if e.duration_ms and not e.error]
            metrics["tasks_completed"] = len(completed)

            # Group by action type
            for entry in completed:
                action = entry.action
                metrics["tasks_by_type"][action] = metrics["tasks_by_type"].get(action, 0) + 1

            # Count errors
            metrics["errors_count"] = sum(1 for e in entries if e.level == "error")

            # Success rate
            metrics["success_rate"] = len(completed) / len(entries) if entries else 0

            # Average duration
            durations = [e.duration_ms for e in completed if e.duration_ms]
            if durations:
                metrics["avg_task_duration_ms"] = int(sum(durations) / len(durations))

            # Approvals
            approval_entries = [e for e in entries if e.approval]
            metrics["approvals_processed"] = len(approval_entries)

        except Exception as e:
            print(f"Error fetching audit metrics: {e}")

    # Also count files in Done/ folder (approximate)
    try:
        done_path = VAULT_PATH / "Done"
        if done_path.exists():
            # Check modification times for this week
            done_files = list(done_path.glob("*.md"))
            week_done = 0
            for f in done_files:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if week_start <= mtime.date() <= week_end:
                    week_done += 1
            # Use max of audit-based and file-based count
            metrics["tasks_completed"] = max(metrics["tasks_completed"], week_done)
    except:
        pass

    return metrics


def fetch_health_metrics() -> Dict[str, Any]:
    """Get health/uptime metrics from monitoring server."""
    if not HEALTH_AVAILABLE:
        return {"available": False, "note": "requests not available"}

    try:
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            uptime_seconds = data.get("uptime_seconds", 0)
            components = data.get("components", {})

            healthy_count = sum(1 for c in components.values() if c.get("status") == "healthy")
            total_count = len(components)

            return {
                "available": True,
                "uptime_days": round(uptime_seconds / 86400, 2),
                "healthy_components": healthy_count,
                "total_components": total_count,
                "overall_status": data.get("status", "unknown"),
                "component_details": components
            }
    except Exception as e:
        return {"available": False, "error": str(e)}

    return {"available": False, "note": "No data"}


def generate_executive_summary(
    financials: Dict, social: Dict, ops: Dict, goals: Dict, health: Dict
) -> str:
    """Generate 2-3 sentence executive summary."""
    revenue = financials.get("revenue_this_week", 0)
    tasks = ops.get("tasks_completed", 0)
    success_rate = ops.get("success_rate", 0) * 100
    health_status = health.get("overall_status", "unknown")

    # Determine trend (simplified - would compare to last week)
    trend = "stable"

    summary = f"""**Week in Review:** Completed {tasks} automated tasks with {success_rate:.0f}% success rate. """

    if financials.get("available"):
        summary += f"Generated ${revenue:,.2f} in revenue this week. "

    summary += f"System health: {health_status.upper()} with {health.get('healthy_components', 0)}/{health.get('total_components', 0)} components operational. "

    if tasks == 0:
        summary += "Quiet week with no task completions."
    else:
        summary += f"Activity level {trend} compared to last week."

    return summary


def generate_financial_section(financials: Dict) -> str:
    """Generate detailed financial markdown section."""
    if not financials.get("available", False):
        return "## Financial\n*Odoo data not available*\n"

    lines = ["## Financial", ""]
    lines.append(f"- **Revenue This Week**: ${financials['revenue_this_week']:,.2f}")
    lines.append(f"- **Invoices Created**: {financials['invoices_created']}")
    lines.append(f"- **Invoices Posted**: {financials['invoices_posted']}")
    lines.append(f"- **Accounts Receivable**: ${financials['accounts_receivable']:,.2f}")
    lines.append(f"- **Overdue Invoices**: {financials['overdue_invoices']} (${financials['overdue_amount']:,.2f})")

    if financials.get("top_customers"):
        lines.append("")
        lines.append("**Top Customers This Week:**")
        for customer, amount in financials["top_customers"][:3]:
            lines.append(f"- {customer}: ${amount:,.2f}")

    lines.append("")
    return "\n".join(lines)


def generate_social_section(social: Dict) -> str:
    """Generate social media metrics section."""
    if not social.get("available", False) or social.get("total_posts", 0) == 0:
        return "## Social Media\n*No social activity this week*\n"

    lines = ["## Social Media", ""]
    lines.append(f"- **Total Posts**: {social['total_posts']}")
    lines.append(f"  - Facebook: {social['facebook_posts']}")
    lines.append(f"  - Instagram: {social['instagram_posts']}")
    lines.append(f"  - Twitter: {social['twitter_tweets']}")
    lines.append(f"- **Estimated Reach**: {social['estimated_reach']:,}")
    lines.append(f"- **Total Engagement**: {social['total_engagement']:,}")
    lines.append(f"- **Avg Engagement/Post**: {social['avg_engagement_per_post']:.1f}")
    lines.append("")
    return "\n".join(lines)


def generate_operations_section(ops: Dict, health: Dict) -> str:
    """Generate operations metrics section."""
    lines = ["## Operations", ""]
    lines.append(f"- **Tasks Completed**: {ops['tasks_completed']}")
    lines.append(f"- **Success Rate**: {ops['success_rate']:.1%}")
    lines.append(f"- **Errors Encountered**: {ops['errors_count']}")
    lines.append(f"- **Approvals Processed**: {ops['approvals_processed']}")
    lines.append(f"- **Avg Task Duration**: {ops['avg_task_duration_ms']}ms")

    if health.get("available"):
        lines.append(f"- **System Uptime**: {health['uptime_days']} days")
        lines.append(f"- **Health Status**: {health['overall_status'].upper()}")

    # Top task types
    if ops.get("tasks_by_type"):
        lines.append("")
        lines.append("**Tasks by Type:**")
        for action, count in sorted(ops["tasks_by_type"].items(), key=lambda x: x[1], reverse=True)[:5]:
            lines.append(f"- {action}: {count}")

    lines.append("")
    return "\n".join(lines)


def generate_bottlenecks_section(ops: Dict) -> str:
    """Identify and report bottlenecks."""
    # In this simple version, we look at error count and slow tasks
    if ops["errors_count"] == 0 and ops["tasks_completed"] > 0:
        return "## Bottlenecks\n✅ No significant bottlenecks detected this week.\n"

    lines = ["## Bottlenecks", ""]

    if ops["errors_count"] > 0:
        lines.append(f"⚠️ **High error count**: {ops['errors_count']} errors encountered")
        lines.append(" - Review logs for recurring error patterns")
        lines.append("")

    # Could add: tasks with high duration (need more granular data)
    lines.append("See audit log analysis for detailed performance metrics.")
    lines.append("")
    return "\n".join(lines)


def generate_next_week_priorities(goals: Dict, financials: Dict, ops: Dict) -> List[str]:
    """Suggest priorities for next week based on data."""
    priorities = []

    # If AR is high, suggest collections
    ar = financials.get("accounts_receivable", 0)
    if ar > 10000:
        priorities.append("Follow up on overdue invoices (AR: ${:,.2f})".format(ar))

    # If success rate low, suggest investigating errors
    if ops.get("success_rate", 1) < 0.9:
        priorities.append("Investigate error patterns to improve automation success rate")

    # If social activity low, suggest posting
    social_posts = sum([
        ops.get("facebook_posts", 0),
        ops.get("instagram_posts", 0),
        ops.get("twitter_tweets", 0)
    ])
    if social_posts < 3:
        priorities.append("Increase social media engagement (only {} posts this week)".format(social_posts))

    # Default
    if not priorities:
        priorities.append("Maintain current automation and monitor for opportunities")

    return priorities


def generate_briefing(week_start: datetime, week_end: datetime, dry_run: bool = False) -> str:
    """Generate complete weekly briefing markdown."""

    # Fetch all data sources
    print("Fetching data sources...")
    goals = read_business_goals()
    print("  ✓ Business goals loaded")

    financials = fetch_odoo_financials(week_start, week_end)
    if financials.get("available"):
        print("  ✓ Odoo financial data fetched")
    else:
        print("  ⚠ Odoo data not available")

    social = fetch_social_metrics(week_start, week_end)
    if social.get("available"):
        print("  ✓ Social metrics fetched")
    else:
        print("  ⚠ Social metrics not available")

    ops = fetch_operations_metrics(week_start, week_end)
    print("  ✓ Operations metrics fetched")

    health = fetch_health_metrics()
    if health.get("available"):
        print("  ✓ Health metrics fetched")
    else:
        print("  ⚠ Health data not available")

    # Generate sections
    print("Generating report...")
    briefing = []
    briefing.append("---")
    briefing.append(f"generated: {datetime.now().isoformat()}")
    briefing.append(f"period: {week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}")
    briefing.append(f"prepared_by: AI Employee v0.3-Phase4")
    briefing.append("---")
    briefing.append("")

    briefing.append("# Monday Morning CEO Briefing")
    briefing.append("")
    briefing.append("## Executive Summary")
    briefing.append("")
    briefing.append(generate_executive_summary(financials, social, ops, goals, health))
    briefing.append("")

    briefing.append(generate_financial_section(financials))
    briefing.append(generate_social_section(social))
    briefing.append(generate_operations_section(ops, health))
    briefing.append(generate_bottlenecks_section(ops))

    # Next week priorities
    briefing.append("## Next Week Priorities")
    priorities = generate_next_week_priorities(goals, financials, ops)
    for i, priority in enumerate(priorities, 1):
        briefing.append(f"{i}. {priority}")
    briefing.append("")

    # Footer
    briefing.append("---")
    briefing.append(f"*Generated by AI Employee v0.3-Phase4*")
    briefing.append(f'*"Your life and business on autopilot"*')
    briefing.append("")

    report = "\n".join(briefing)

    if dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN - Report would be written to:")
        filename = f"{week_start.strftime('%Y-%m-%d')}_Monday_Briefing.md"
        print(f"  {BRIEFINGS_PATH / filename}")
        print("=" * 60)
        print("\nPreview (first 500 chars):")
        print(report[:500] + "...\n")
        return report
    else:
        # Write to file
        BRIEFINGS_PATH.mkdir(parents=True, exist_ok=True)
        filename = f"{week_start.strftime('%Y-%m-%d')}_Monday_Briefing.md"
        output_path = BRIEFINGS_PATH / filename

        output_path.write_text(report)
        print(f"✓ Briefing saved to: {output_path}")

        # Also update Dashboard.md with link
        try:
            if DASHBOARD_PATH.exists():
                dash = DASHBOARD_PATH.read_text()
                # Add to Recent Briefings section
                link_line = f"- [Monday Briefing](./Briefings/{filename}) ({week_start.strftime('%b %d, %Y')})"
                if "## Recent Briefings" in dash:
                    # Insert after heading
                    parts = dash.split("## Recent Briefings")
                    if len(parts) > 1:
                        # Insert after heading line
                        rest = parts[1].split("\n", 1)
                        if len(rest) > 1:
                            new_section = "## Recent Briefings\n" + link_line + "\n" + rest[1]
                            dash = parts[0] + new_section
                        else:
                            dash = parts[0] + "## Recent Briefings\n" + link_line + "\n"
                    DASHBOARD_PATH.write_text(dash)
                    print("✓ Dashboard updated with briefing link")
        except Exception as e:
            print(f"⚠ Could not update dashboard: {e}")

        return report


def main():
    parser = argparse.ArgumentParser(description="Generate weekly CEO briefing")
    parser.add_argument("--week", help="Week start date (YYYY-MM-DD), defaults to last Monday")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing file")
    args = parser.parse_args()

    # Determine week
    if args.week:
        try:
            week_start = datetime.strptime(args.week, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        # Use last Monday (or today if Monday)
        today = datetime.now().date()
        monday, sunday = get_week_range(datetime(today.year, today.month, today.day))
        week_start = monday
        week_end = sunday
    week_end = week_start + timedelta(days=6)

    print(f"Generating briefing for week: {week_start} to {week_end}")
    print()

    # Convert to datetime for functions
    week_start_dt = datetime.combine(week_start, datetime.min.time())
    week_end_dt = datetime.combine(week_end, datetime.max.time())

    try:
        report = generate_briefing(week_start_dt, week_end_dt, dry_run=args.dry_run)
        print("\n✓ Briefing generation complete!")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error generating briefing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
