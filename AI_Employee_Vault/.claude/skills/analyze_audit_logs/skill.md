# Analyze Audit Logs

**Gold Tier Phase 4** - Query, analyze, and report on audit log activity for compliance and business intelligence.

---

## Overview

This skill provides powerful audit log analytics capabilities:

- **Daily/Weekly Summaries** - Action counts, success rates, error trends
- **Compliance Reports** - Approval usage, sensitive operations, policy violations
- **Performance Metrics** - Average durations, slowest operations, P95/P99
- **Usage Patterns** - Most active components, peak hours, frequent actors
- **Error Analysis** - Top failure modes, affected services, recurrence patterns

**Output formats:** Markdown (human-readable), JSON (machine-readable), CSV (spreadsheet import)

---

## Usage

```
/skill analyze_audit_logs [--date YYYY-MM-DD] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--format markdown|json|csv] [--output FILE]
```

**Parameters:**
- `--date` - Single date to analyze (default: yesterday)
- `--start-date` / `--end-date` - Date range (inclusive)
- `--format` - Output format (default: markdown)
- `--output` - Write to file instead of stdout (optional)
- `--actor` - Filter by specific actor (e.g., "odoo-mcp", "social-mcp")
- `--action` - Filter by action type (e.g., "facebook_post", "create_invoice")

---

## Examples

### Daily Summary Report (Markdown)

```
/skill analyze_audit_logs --date 2026-03-08
```

Output:
```markdown
# Audit Log Analysis - 2026-03-08

## Summary
- Total Actions: 127
- Success Rate: 94% (119/127)
- Error Rate: 6% (8/127)

## Actions by Type
| Action | Count | Success Rate | Avg Duration |
|--------|-------|--------------|--------------|
| search_customers | 45 | 100% | 320ms |
| facebook_post | 12 | 92% | 2.1s |
| create_invoice | 8 | 100% | 1.8s |

## Errors (Top 3)
1. RateLimitError - 3 occurrences
2. ConnectionTimeout - 2 occurrences
3. InvalidToken - 1 occurrence

## Approvals
- Total approvals required: 5
- Human approved: 4 (80%)
- Auto approved: 1 (20%)
- Rejected: 0

## Performance
- Overall avg duration: 1.2s
- Slowest operation: facebook_post (max 4.2s)
- P95 duration: 2.8s

## Timeline
| Hour | Actions | Errors |
|------|---------|--------|
| 00:00 | 3 | 0 |
| 01:00 | 12 | 1 |
| 02:00 | 8 | 0 |
| ... | ... | ... |
```

---

### Filter by Actor

```
/skill analyze_audit_logs --start-date 2026-03-01 --end-date 2026-03-07 --actor social-mcp --format json
```

Returns JSON with only social-mcp actions in that date range.

---

### Compliance Report (CSV)

```
/skill analyze_audit_logs --date 2026-03-08 --format csv --output compliance_20260308.csv
```

CSV columns:
```csv
timestamp,actor,action,target,level,duration_ms,error
2026-03-08T01:20:13,social-mcp,facebook_post,123456_789,info,1250,
2026-03-08T01:21:45,odoo-mcp,create_invoice,INV/2026/001,error,450,"Connection timeout"
```

---

### Most Frequent Errors (Custom Query)

```
/skill analyze_audit_logs --start-date 2026-03-01 --level error | grep -i "rate\|timeout"
```

Or use the `--action` filter to focus on specific operations.

---

## Report Sections

### 1. Summary Statistics
- Total actions
- Success vs error count and percentage
- Unique actors, actions, targets

### 2. Actions by Type
- Count per action (e.g., `facebook_post`, `create_invoice`)
- Success rate per action
- Average duration per action
- P50/P95/P99 latencies

### 3. Errors Analysis
- Top error types (by count)
- Affected components
- Time distribution
- Recurrence patterns (same error every hour?)

### 4. Approval Workflow
- Total approvals required
- Auto-approved vs human-approved
- Rejection rate
- Average approval wait time (from request to execution)

### 5. Sensitive Operations
- Customer data access
- Financial operations (invoices, payments)
- External integrations (social posting, email sending)
- Configuration changes

### 6. Performance Metrics
- Fastest/slowest operations
- Duration percentiles (P50, P95, P99)
- Components by avg duration
- Outliers (> 3x normal duration)

### 7. Timeline Heatmap
- Actions per hour (busiest times)
- Error rate per hour
- Peak usage windows

### 8. Anomalies
- Sudden spikes in errors
- Unusual actors (not typically seen)
- Actions outside business hours (if configured)
- Failed approval workflows

---

## Integration with CEO Briefing

The `generate_weekly_briefing` skill automatically calls `analyze_audit_logs` to include:

- **Operations Summary** - Tasks automated, success rate
- **Error Trends** - Week-over-week comparison
- **Approval Efficiency** - Human intervention needed
- **Performance Scorecard** - System health indicators

This provides data-driven insights for management.

---

## Data Sources

The skill reads from:
- `AI_Employee_Vault/Logs/YYYY-MM-DD.json` (daily log files)
- Can query across date ranges (scans multiple files)
- Uses `utils.audit.logger.AuditLogger` for parsing

**Note:** If logs are rotated/gzipped, the logger handles decompression transparently.

---

## Filtering Options

| Filter | Description |
|--------|-------------|
| `--date` | Single specific date |
| `--start-date` / `--end-date` | Inclusive date range |
| `--actor` | Filter by actor (e.g., "odoo-mcp", "claude_code") |
| `--action` | Filter by action type (e.g., "create_invoice") |
| `--level` | Filter by level: info, warning, error, critical |
| `--target` | Filter by target resource ID |

Multiple filters can be combined:
```
/skill analyze_audit_logs --start-date 2026-03-01 --end-date 2026-03-07 --level error --actor odoo-mcp
```

---

## Output Formats

### Markdown (default)
Human-readable, formatted with headings, tables, and emphasis. Suitable for:
- Pasting into emails
- Including in Briefings
- Quick review in terminal

**Sample:**
```markdown
# Audit Analysis - 2026-03-08

## Stats
- Total: 127
- Success: 119 (94%)
- Errors: 8 (6%)

## Top Actions
1. search_customers: 45
2. facebook_post: 12
3. create_invoice: 8
```

---

### JSON
Machine-readable, structured data for:
- API consumption
- Programmatic analysis
- Integration with external BI tools

**Structure:**
```json
{
  "date_range": {"start": "2026-03-01", "end": "2026-03-07"},
  "summary": {"total_actions": 754, "success_rate": 0.94},
  "actions": [{"name": "search_customers", "count": 234, "success_rate": 0.99}],
  "errors": [{"type": "RateLimitError", "count": 12, "actor": "social-mcp"}],
  "timeline": [{"hour": "2026-03-01T14:00:00", "count": 45}]
}
```

---

### CSV
Spreadsheet-friendly, comma-separated values:
- One row per log entry (if no filters) or aggregated
- Can be opened in Excel, Google Sheets
- Good for ad-hoc analysis with pivot tables

**Example:**
```csv
date,actor,action,count,success_rate,avg_duration_ms
2026-03-08,odoo-mcp,search_customers,45,1.0,320
2026-03-08,social-mcp,facebook_post,12,0.92,2100
```

---

## Implementation Details

The skill is implemented as a Python script:

```python
#!/usr/bin/env python3
import argparse
from utils.audit.logger import AuditLogger
from datetime import datetime, timedelta

def analyze_logs(date=None, start_date=None, end_date=None, actor=None, action=None, level=None):
    logger = AuditLogger()
    entries = logger.read_logs(
        start_date=start_date or date,
        end_date=end_date or date,
        actor=actor,
        action=action,
        level=level,
        limit=100000
    )

    # Compute statistics
    stats = compute_stats(entries)
    return stats

def generate_markdown_report(stats):
    # Format as markdown
    return report_md

def generate_json_report(stats):
    import json
    return json.dumps(stats, indent=2)

def generate_csv_report(stats):
    # Convert to CSV
    return csv_string

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Analysis date (YYYY-MM-DD, default: yesterday)")
    parser.add_argument("--start-date", help="Start date (inclusive)")
    parser.add_argument("--end-date", help="End date (inclusive)")
    parser.add_argument("--format", choices=["markdown", "json", "csv"], default="markdown")
    parser.add_argument("--output", help="Output file (default: stdout)")
    parser.add_argument("--actor", help="Filter by actor")
    parser.add_argument("--action", help="Filter by action")
    parser.add_argument("--level", help="Filter by level")
    args = parser.parse_args()

    stats = analyze_logs(...)

    if args.format == "markdown":
        report = generate_markdown_report(stats)
    elif args.format == "json":
        report = generate_json_report(stats)
    else:
        report = generate_csv_report(stats)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
    else:
        print(report)
```

---

## Example: Code Implementation Skeleton

```python
# AI_Employee_Vault/.claude/skills/analyze_audit_logs/analyze.py

def analyze_logs(date=None, start_date=None, end_date=None, filters=None):
    from utils.audit.logger import AuditLogger
    logger = AuditLogger()

    entries = logger.read_logs(
        start_date=start_date or date,
        end_date=end_date or date,
        actor=filters.get('actor'),
        action=filters.get('action'),
        level=filters.get('level'),
        limit=100000
    )

    stats = {
        "date_range": {
            "start": start_date or date,
            "end": end_date or date
        },
        "summary": compute_summary(entries),
        "actions": group_by_action(entries),
        "errors": top_errors(entries),
        "approvals": analyze_approvals(entries),
        "performance": compute_percentiles(entries),
        "timeline": timeline_by_hour(entries)
    }

    return stats

def compute_summary(entries):
    total = len(entries)
    errors = sum(1 for e in entries if e.level == 'error')
    return {
        "total_actions": total,
        "success_count": total - errors,
        "error_count": errors,
        "success_rate": (total - errors) / total if total > 0 else 0
    }

def group_by_action(entries):
    action_counts = {}
    for entry in entries:
        action = entry.action
        if action not in action_counts:
            action_counts[action] = {"count": 0, "durations": [], "errors": 0}
        stats = action_counts[action]
        stats["count"] += 1
        if entry.duration_ms:
            stats["durations"].append(entry.duration_ms)
        if entry.error:
            stats["errors"] += 1

    # Compute derived metrics
    result = []
    for action, data in action_counts.items():
        durations = sorted(data["durations"])
        result.append({
            "action": action,
            "count": data["count"],
            "success_rate": 1 - (data["errors"] / data["count"]) if data["count"] > 0 else 0,
            "avg_duration_ms": sum(durations) // len(durations) if durations else 0,
            "p95_duration_ms": durations[int(len(durations) * 0.95)] if durations else 0
        })
    return sorted(result, key=lambda x: x["count"], reverse=True)

# Similar functions: top_errors(), analyze_approvals(), compute_percentiles(), timeline_by_hour()
```

---

## Testing

### Test 1: Daily Summary

```bash
# Assuming logs exist for 2026-03-08
/skill analyze_audit_logs --date 2026-03-08
```

Expected:
- Summary showing total actions, success rate
- Top actions table
- Error breakdown
- Output in readable markdown

---

### Test 2: Date Range Query

```
/skill analyze_audit_logs --start-date 2026-03-01 --end-date 2026-03-07 --format json > weekly_report.json
```

Expected:
- JSON file with aggregated stats across 7 days
- Can compare day-by-day trends

---

### Test 3: Filter by Error Level

```
/skill analyze_audit_logs --start-date 2026-03-01 --level error --format csv > errors_20260301_07.csv
```

Expected:
- CSV with only error entries
- Columns: timestamp, actor, action, error message

---

## Dependencies

- **Audit Logger** - Must be available (`utils/audit/logger.py`)
- **Log Files** - Must exist in `AI_Employee_Vault/Logs/`
- **Sufficient Permissions** - Read access to log directory

---

## Performance Considerations

- Querying large date ranges (months) can be slow (scan many large JSON files)
- Recommend limiting to 90 days (retention period)
- Use specific filters (`--actor`, `--action`) to narrow scope
- Consider adding index/cache for frequent queries (future)

---

## Security Notes

- Audit logs may contain sensitive data (email addresses, invoice amounts, customer names)
- `--format json` or `--output FILE` should be used cautiously (file may persist)
- Avoid writing reports to world-readable locations
- Consider redacting PII for external sharing (future enhancement)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No logs found | Check `AI_Employee_Vault/Logs/` exists and contains `.json` files |
| Parse errors | Log file may be incomplete/corrupt. Check file format. |
| Slow performance | Narrow date range or add filters (`--actor`, `--action`) |
| Memory error | Reduce date range; logs are loaded into memory for analysis |
| Empty report | Date range may have no logs, or filters too restrictive |

---

## Future Enhancements

- [ ] Anomaly detection (flag unusual spikes)
- [ ] Scheduled reports (auto-generate daily at 8am)
- [ ] Email delivery of reports
- [ ] Web dashboard for interactive exploration
- [ ] Compare periods (week-over-week, month-over-month)
- [ ] Export to PDF with charts (using matplotlib)
- [ ] Integration with external BI (Metabase, Grafana)
- [ ] PII redaction mode for compliance
- [ ] Real-time streaming analysis (tail mode)

---

## Integration with Dashboard

The dashboard updater can pull a summary from this skill:

```python
# In utils/dashboard_updater.py
def fetch_audit_summary():
    # Could call analyze.py with --format json and parse
    # Or directly import and call function
    from skills.analyze_audit_logs.analyze import analyze_logs
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    stats = analyze_logs(date=yesterday)
    return {
        "audited_actions_yesterday": stats["summary"]["total_actions"],
        "error_rate_yesterday": stats["summary"]["error_rate"],
        "top_action": stats["actions"][0]["action"] if stats["actions"] else None
    }
```

---

**Skill: analyze_audit_logs**
**Version: 0.1-Phase4**
**Last Updated: 2026-03-09**
