# Update Dashboard Skill

Refreshes the main dashboard with current statistics.

## Description

This skill scans all vault folders and updates `Dashboard.md` with:
- Current counts in each folder
- Recent activity from `/Done/`
- System health status
- Quick links and statistics

## Usage

```
/skill update_dashboard [--verbose]
```

## Parameters

- `--verbose`: Show detailed statistics

## What It Does

1. Counts files in:
   - `/Needs_Action/` - pending items
   - `/Plans/` - active plans
   - `/Done/` - completed (today, this week)
   - `/Pending_Approval/` - awaiting human review

2. Calculates:
   - Completion rate (Done vs Needs_Action)
   - Average processing time (if data available)
   - Uptime estimate

3. Updates sections:
   - "Quick Stats"
   - "System Health"
   - "Recent Activity" (last 7 items from Done)
   - "Last Updated" timestamp

4. Preserves:
   - Manual human notes
   - Quick links section
   - Any custom additions

## Example Output

```
📊 Dashboard updated:

   Pending: 5
   Processing: 2
   Completed (today): 12
   Awaiting approval: 1

✅ Done
```

## Integration

This skill is called:
- Automatically after `process_needs_action` completes
- Can be invoked manually at any time
- Should be part of regular maintenance (daily)

## Notes

- Dashboard.md uses markdown with frontmatter
- Keep formatting consistent for best viewing in Obsidian
- Do not delete existing content - only update Stat sections

## See Also

- `Dashboard.md` - The file this skill updates
- `process_needs_action` skill - Often calls this automatically
