#!/usr/bin/env python3
"""
Analyze Audit Logs - Phase 4 Skill Implementation
Queries and analyzes audit log data for compliance, insights, and reporting.
"""

import argparse
import json
import csv
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
# Go up 4 levels: analyze_audit_logs -> skills -> .claude -> AI_Employee_Vault -> project root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
sys.path.insert(0, project_root)

from utils.audit.logger import AuditLogger, AuditEntry


def analyze_logs(
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    actor: Optional[str] = None,
    action: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = 100000
) -> Dict[str, Any]:
    """
    Analyze audit logs and return statistics.

    Args:
        date: Single date (YYYY-MM-DD), defaults to yesterday
        start_date: Start of range (inclusive)
        end_date: End of range (inclusive)
        actor: Filter by actor name
        action: Filter by action type
        level: Filter by level (info/warning/error/critical)
        limit: Maximum entries to fetch

    Returns:
        Dictionary with aggregated statistics
    """
    logger = AuditLogger()

    # Parse dates
    if date is None and start_date is None:
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # Fetch entries
    entries = logger.read_logs(
        start_date=start_date or date,
        end_date=end_date or date,
        actor=actor,
        action=action,
        level=level,
        limit=limit
    )

    # Compute statistics
    stats = {
        "date_range": {
            "start": start_date or date,
            "end": end_date or date
        },
        "summary": compute_summary(entries),
        "actions": group_by_action(entries),
        "errors": top_errors(entries),
        "approvals": analyze_approvals(entries),
        "performance": compute_performance(entries),
        "timeline": timeline_by_hour(entries),
        "actors": top_actors(entries)
    }

    return stats


def compute_summary(entries: List[AuditEntry]) -> Dict[str, Any]:
    """Compute high-level summary statistics."""
    total = len(entries)
    errors = sum(1 for e in entries if e.level == 'error')
    warnings = sum(1 for e in entries if e.level == 'warning')

    # Unique counts
    unique_actors = set(e.actor for e in entries)
    unique_actions = set(e.action for e in entries)

    return {
        "total_actions": total,
        "success_count": total - errors,
        "error_count": errors,
        "warning_count": warnings,
        "success_rate": (total - errors) / total if total > 0 else 0,
        "unique_actors": len(unique_actors),
        "unique_actions": len(unique_actions)
    }


def group_by_action(entries: List[AuditEntry]) -> List[Dict[str, Any]]:
    """Group entries by action type and compute metrics."""
    action_data = {}

    for entry in entries:
        action = entry.action
        if action not in action_data:
            action_data[action] = {
                "count": 0,
                "errors": 0,
                "durations": [],
                "approvals": 0
            }

        stats = action_data[action]
        stats["count"] += 1

        if entry.level == 'error':
            stats["errors"] += 1

        if entry.duration_ms:
            stats["durations"].append(entry.duration_ms)

        if entry.approval:
            stats["approvals"] += 1

    # Build result list
    result = []
    for action, data in action_data.items():
        durations = sorted(data["durations"])
        result.append({
            "action": action,
            "count": data["count"],
            "success_rate": 1 - (data["errors"] / data["count"]) if data["count"] > 0 else 1.0,
            "avg_duration_ms": int(sum(durations) / len(durations)) if durations else 0,
            "p50_duration_ms": durations[int(len(durations) * 0.5)] if durations else 0,
            "p95_duration_ms": durations[int(len(durations) * 0.95)] if durations else 0,
            "p99_duration_ms": durations[int(len(durations) * 0.99)] if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
            "approval_count": data["approvals"]
        })

    return sorted(result, key=lambda x: x["count"], reverse=True)


def top_errors(entries: List[AuditEntry], top_n: int = 10) -> List[Dict[str, Any]]:
    """Find most frequent error types and actors."""
    error_counts = {}

    for entry in entries:
        if entry.level != 'error' or not entry.error:
            continue

        error_type = entry.error if isinstance(entry.error, str) else type(entry.error).__name__
        key = f"{entry.actor}:{error_type}"

        if key not in error_counts:
            error_counts[key] = {
                "count": 0,
                "actor": entry.actor,
                "error": error_type,
                "examples": []
            }

        error_counts[key]["count"] += 1
        if len(error_counts[key]["examples"]) < 3:
            error_counts[key]["examples"].append(entry.timestamp)

    # Sort and return top N
    sorted_errors = sorted(error_counts.values(), key=lambda x: x["count"], reverse=True)
    return sorted_errors[:top_n]


def analyze_approvals(entries: List[AuditEntry]) -> Dict[str, Any]:
    """Analyze approval workflow usage."""
    total_with_approvals = 0
    auto_approved = 0
    human_approved = 0
    rejected = 0
    approval_durations = []

    for entry in entries:
        if not entry.approval:
            continue

        total_with_approvals += 1
        status = entry.approval.get("status", "")

        if status == "auto_approved":
            auto_approved += 1
        elif status == "approved":
            human_approved += 1
        elif status == "rejected":
            rejected += 1

        # If we had timestamps for when approval was requested vs granted, we'd compute wait time
        # For now, skip

    return {
        "total_approvals_required": total_with_approvals,
        "auto_approved": auto_approved,
        "human_approved": human_approved,
        "rejected": rejected,
        "auto_approval_rate": auto_approved / total_with_approvals if total_with_approvals > 0 else 0
    }


def compute_performance(entries: List[AuditEntry]) -> Dict[str, Any]:
    """Compute performance statistics across all actions."""
    durations = [e.duration_ms for e in entries if e.duration_ms]

    if not durations:
        return {
            "avg_ms": 0,
            "p50_ms": 0,
            "p95_ms": 0,
            "p99_ms": 0,
            "max_ms": 0,
            "total_operations": 0
        }

    durations.sort()
    total_ops = len(durations)

    return {
        "avg_ms": int(sum(durations) / total_ops),
        "p50_ms": durations[int(total_ops * 0.5)],
        "p95_ms": durations[int(total_ops * 0.95)],
        "p99_ms": durations[int(total_ops * 0.99)],
        "max_ms": max(durations),
        "total_operations": total_ops
    }


def timeline_by_hour(entries: List[AuditEntry]) -> List[Dict[str, int]]:
    """Distribution of actions by hour of day."""
    hour_counts = {f"{h:02d}:00": 0 for h in range(24)}
    error_by_hour = {f"{h:02d}:00": 0 for h in range(24)}

    for entry in entries:
        try:
            dt = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00'))
            hour_key = f"{dt.hour:02d}:00"
            if hour_key in hour_counts:
                hour_counts[hour_key] += 1
                if entry.level == 'error':
                    error_by_hour[hour_key] += 1
        except:
            pass

    result = []
    for hour in sorted(hour_counts.keys()):
        result.append({
            "hour": hour,
            "actions": hour_counts[hour],
            "errors": error_by_hour[hour]
        })

    return result


def top_actors(entries: List[AuditEntry], top_n: int = 10) -> List[Dict[str, Any]]:
    """Most active actors (components/systems)."""
    actor_counts = {}

    for entry in entries:
        actor = entry.actor
        if actor not in actor_counts:
            actor_counts[actor] = {"count": 0, "actions": set()}

        actor_counts[actor]["count"] += 1
        actor_counts[actor]["actions"].add(entry.action)

    result = []
    for actor, data in sorted(actor_counts.items(), key=lambda x: x[1]["count"], reverse=True)[:top_n]:
        result.append({
            "actor": actor,
            "count": data["count"],
            "unique_actions": len(data["actions"])
        })

    return result


def generate_markdown_report(stats: Dict[str, Any]) -> str:
    """Generate human-readable markdown report."""
    lines = []
    dr = stats["date_range"]
    lines.append(f"# Audit Log Analysis - {dr['start']}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    s = stats["summary"]
    lines.append(f"- **Total Actions**: {s['total_actions']:,}")
    lines.append(f"- **Success Rate**: {s['success_rate']:.1%} ({s['success_count']:,}/{s['total_actions']:,})")
    lines.append(f"- **Errors**: {s['error_count']:,}")
    lines.append(f"- **Warnings**: {s['warning_count']:,}")
    lines.append(f"- **Unique Actors**: {s['unique_actors']}")
    lines.append(f"- **Unique Actions**: {s['unique_actions']}")
    lines.append("")

    # Top Actions
    lines.append("## Top Actions")
    lines.append("| Action | Count | Success Rate | Avg Duration | P95 Duration |")
    lines.append("|--------|-------|--------------|--------------|--------------|")
    for action in stats["actions"][:10]:
        lines.append(f"| {action['action']} | {action['count']:,} | {action['success_rate']:.1%} | {action['avg_duration_ms']}ms | {action['p95_duration_ms']}ms |")
    lines.append("")

    # Errors
    lines.append("## Top Errors")
    lines.append("| Error | Count | Actor |")
    lines.append("|-------|-------|-------|")
    for err in stats["errors"][:10]:
        lines.append(f"| {err['error']} | {err['count']} | {err['actor']} |")
    lines.append("")

    # Approvals
    lines.append("## Approval Workflow")
    a = stats["approvals"]
    lines.append(f"- **Total approvals required**: {a['total_approvals_required']:,}")
    lines.append(f"- **Auto approved**: {a['auto_approved']:,} ({a['auto_approval_rate']:.1%})")
    lines.append(f"- **Human approved**: {a['human_approved']:,}")
    lines.append(f"- **Rejected**: {a['rejected']:,}")
    lines.append("")

    # Performance
    lines.append("## Performance Metrics")
    p = stats["performance"]
    lines.append(f"- **Total operations with timing**: {p['total_operations']:,}")
    lines.append(f"- **Average duration**: {p['avg_ms']}ms")
    lines.append(f"- **P50 (median)**: {p['p50_ms']}ms")
    lines.append(f"- **P95**: {p['p95_ms']}ms")
    lines.append(f"- **P99**: {p['p99_ms']}ms")
    lines.append(f"- **Max**: {p['max_ms']}ms")
    lines.append("")

    # Timeline
    lines.append("## Hourly Activity")
    lines.append("| Hour | Actions | Errors |")
    lines.append("|------|---------|--------|")
    for hour_data in stats["timeline"]:
        if hour_data["actions"] > 0:
            lines.append(f"| {hour_data['hour']} | {hour_data['actions']:,} | {hour_data['errors']:,} |")
    lines.append("")

    # Top Actors
    lines.append("## Most Active Components")
    lines.append("| Actor | Actions | Unique Tools |")
    lines.append("|-------|---------|--------------|")
    for actor in stats["actors"][:5]:
        lines.append(f"| {actor['actor']} | {actor['count']:,} | {actor['unique_actions']} |")

    return "\n".join(lines)


def generate_json_report(stats: Dict[str, Any]) -> str:
    """Generate JSON report."""
    return json.dumps(stats, indent=2)


def generate_csv_report(stats: Dict[str, Any]) -> str:
    """Generate CSV report (flattened)."""
    output = []

    # Summary row
    s = stats["summary"]
    output.append(["metric", "value"])
    output.append(["total_actions", s["total_actions"]])
    output.append(["success_count", s["success_count"]])
    output.append(["error_count", s["error_count"]])
    output.append(["success_rate", s["success_rate"]])
    output.append(["", ""])

    # Actions table
    output.append(["action", "count", "success_rate", "avg_duration_ms", "p95_duration_ms"])
    for action in stats["actions"]:
        output.append([
            action["action"],
            action["count"],
            f"{action['success_rate']:.4f}",
            action["avg_duration_ms"],
            action["p95_duration_ms"]
        ])

    # Convert to CSV string
    lines = [",".join(map(str, row)) for row in output]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze audit logs for compliance and insights")
    parser.add_argument("--date", help="Analysis date (YYYY-MM-DD, default: yesterday)")
    parser.add_argument("--start-date", help="Start date (inclusive)")
    parser.add_argument("--end-date", help="End date (inclusive)")
    parser.add_argument("--format", choices=["markdown", "json", "csv"], default="markdown",
                        help="Output format (default: markdown)")
    parser.add_argument("--output", help="Output file (default: stdout)")
    parser.add_argument("--actor", help="Filter by actor")
    parser.add_argument("--action", help="Filter by action type")
    parser.add_argument("--level", help="Filter by level (info/warning/error/critical)")
    args = parser.parse_args()

    try:
        # Analyze logs
        stats = analyze_logs(
            date=args.date,
            start_date=args.start_date,
            end_date=args.end_date,
            actor=args.actor,
            action=args.action,
            level=args.level
        )

        # Generate report
        if args.format == "markdown":
            report = generate_markdown_report(stats)
        elif args.format == "json":
            report = generate_json_report(stats)
        else:  # csv
            report = generate_csv_report(stats)

        # Output
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"Report written to {args.output}")
        else:
            print(report)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
