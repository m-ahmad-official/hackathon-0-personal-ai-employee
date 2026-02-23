# Process Needs Action Skill

Processes pending items in the `/Needs_Action/` folder and executes them through completion.

## Description

This skill automates the core workflow of the AI Employee:
1. Scans `/Needs_Action/` for unprocessed items
2. Reads each item and understands the requirements
3. Creates a detailed execution plan in `/Plans/`
4. Executes the plan step-by-step
5. Moves completed items to `/Done/`
6. Updates `Dashboard.md` with status
7. Logs all actions to `/Logs/`

## Usage

```
/skill process_needs_action [--all] [--item FILE] [--dry-run]
```

## Parameters

- `--all` (default): Process all pending items
- `--item FILE`: Process a specific file only
- `--dry-run`: Show what would be done without making changes

## Behavior

### When invoked with --all:

1. List all `.md` files in `/Needs_Action/`
2. For each file:
   - Read the full content
   - Parse frontmatter metadata
   - Determine item type (email, file_drop, message, etc.)
   - Check `Company_Handbook.md` for relevant rules
   - Create execution plan in `/Plans/PLAN_<original_name>_<timestamp>.md`
   - Execute plan actions (file operations only)
   - Move original item to `/Done/`
   - Write log entry to `/Logs/YYYY-MM-DD.json`
3. After all items processed:
   - Update `Dashboard.md` statistics
   - Print summary

### When invoked with --item:

Processes only the specified file.

## Plan Template

Plans are created with this structure:

```markdown
---
plan_id: PLAN_<unique_id>
created: <ISO timestamp>
source: <source filename>
status: in_progress
---

# Execution Plan

**Source**: [link to source file]
**Type**: <item type>
**Priority**: <derived or default>

## Objective
<Clear statement of what needs to be done>

## Steps
- [ ] Step 1
- [ ] Step 2
- [ ] Step 3

## Approval Required
<If applicable, list what needs approval>

## Estimated Completion
<time estimate>
```

## Examples

### Process everything:
```
/skill process_needs_action --all
```

### Process one specific item:
```
/skill process_needs_action --item EMAIL_abc123.md
```

### Dry run (preview only):
```
/skill process_needs_action --all --dry-run
```

## Rules from Company Handbook

This skill MUST follow these rules:

1. **Human-in-the-Loop**: If item requires approval, create file in `/Pending_Approval/` and STOP. Do not proceed to `/Done/` until human moves to `/Approved/`

2. **No External APIs**: Bronze tier restricts to file system operations only. No network calls, no email sending, no browser automation.

3. **Move, Don't Copy**: Completed items are MOVED to `/Done/`, never copied.

4. **Audit Logging**: Every file operation must be logged with:
   ```json
   {
     "timestamp": "ISO timestamp",
     "action": "file_moved",
     "source": "path",
     "destination": "path",
     "reason": "executed_plan"
   }
   ```

5. **Dashboard Updates**: After processing batch, update `Dashboard.md`:
   - Increment "Completed Today" count
   - Add entries to "Recent Activity"
   - Update last_updated timestamp

## Error Handling

If an error occurs:
1. Log the full error with traceback to `/Logs/` (today's log)
2. Create `ERROR_<source>_<timestamp>.md` in `/Needs_Action/` with error details
3. Continue with next item (do not crash)
4. Update Dashboard with error count

## Expected Runtime

- Simple items: 10-30 seconds
- Complex multi-step: 1-5 minutes
- Batch of 10 items: 2-10 minutes

## Status Messages

The skill provides interactive feedback:

```
🔍 Scanning /Needs_Action/...
   Found: 3 items

📋 Processing: EMAIL_client_invoice.md
   ✓ Created plan: PLAN_EMAIL_client_invoice_20260224_123456.md
   ✓ Executed 5 steps
   ✓ Moved to Done
   ✓ Logged action

📊 Summary:
   Processed: 3/3
   Plans created: 3
   Errors: 0
   Duration: 45s
```

## Integration with Orchestrator

The `orchestrator.py` script calls this skill automatically for each detected item. In future versions, Claude Code will invoke this skill directly via the `/skill` command.

## Upgrade Path (Silver/Gold)

When upgrading:
- Add external API calls (Gmail, WhatsApp)
- Implement MCP server integration
- Add approval workflow checking
- Support concurrent item processing
- Add retry logic with exponential backoff

## Testing

Run the verification:
```bash
python verify_bronze.py
```

Test with sample files:
```bash
python test_workflow.py --vault .
```

## See Also

- `Company_Handbook.md` - Rules and guidelines
- `CLAUDE.md` - Claude Code integration
- Hackathon documentation - Full architecture
