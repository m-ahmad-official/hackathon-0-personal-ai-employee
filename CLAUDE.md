# Claude Code Integration Guide

*How to connect Claude Code to your AI Employee vault*

---

## Overview

Claude Code is the reasoning engine that processes items from `/Needs_Action/`, creates plans, and executes tasks. This guide shows you how to set up Claude Code for optimal integration with your AI Employee.

---

## Quick Start

### 1. Navigate to Vault

```bash
cd /path/to/your/vault
claude .
```

Or within Claude Code:
```
cd /path/to/vault
```

### 2. Grant File System Access

When Claude starts, it needs access to your vault. Allow it to:
- ✅ Read all files in the vault
- ✅ Write to `/Plans/`, `/Done/`, `/Logs/`, and `Dashboard.md`
- ✅ Read from `/Needs_Action/` and `/Company_Handbook.md`

### 3. Initial Prompt

Give Claude this context:

```
You are my AI Employee working from this Obsidian vault.

YOUR FILESYSTEM STRUCTURE:
- /Needs_Action/ contains items that need processing
- /Plans/ is where you create execution plans
- /Done/ is for completed tasks
- /Logs/ stores audit trails
- Dashboard.md is your status dashboard
- Company_Handbook.md contains your rules

YOUR WORKFLOW:
1. Read all files in /Needs_Action/
2. For each item, create a detailed plan in /Plans/
3. Execute the plan step by step
4. Move completed items to /Done/
5. Update Dashboard.md

RULES FROM COMPANY_HANDBOOK:
[summarize key rules here]

START BY:
- Checking what's in /Needs_Action/
- Reading Company_Handbook.md
- Creating your first plan

PROCEED?
```

---

## Agent Skills Configuration

### What Are Agent Skills?

Agent Skills are reusable, composable capabilities you can give Claude. They're defined in the `.claude/skills/` directory.

### Creating a Skill

1. Create skill directory:
```bash
mkdir -p .claude/skills/process_needs_action
```

2. Create `skill.md`:
```markdown
# Process Needs Action

Processes pending items in /Needs_Action/ and moves them to /Done/.

## Usage

```
/skill process_needs_action [--all] [--item FILE]
```

## Behavior

1. Reads all markdown files from /Needs_Action/
2. For each file:
   - Understand the content
   - Check Company_Handbook.md for relevant rules
   - Create detailed plan in /Plans/
   - Execute plan (file operations only)
   - Move original to /Done/
3. Update Dashboard.md with summary
4. Log all actions to /Logs/YYYY-MM-DD.json

## Parameters

- `--all`: Process all items (default)
- `--item FILE`: Process specific item only

## Examples

```
/skill process_needs_action --all
/skill process_needs_action --item EMAIL_abc123.md
```

## Notes

- Only performs file operations (read/write/move)
- No external API calls (Bronze tier limitation)
- Always check for approval requirements
```

3. Claude Code will auto-detect skills in `.claude/skills/`

### Available Skills for Bronze

1. **process_needs_action** - Process pending items
2. **update_dashboard** - Refresh dashboard statistics
3. **generate_daily_report** - Create daily summary
4. **audit_logs** - Review log entries

---

## Ralph Wiggum Loop (Persistence)

Use the Ralph Wiggum Stop hook to keep Claude working autonomously until tasks complete.

### Simple Implementation

Create `.claude/stop-hooks/ralph_wiggum.py`:

```python
# Ralph Wiggum Stop Hook
import os
from pathlib import Path

def on_stop(params):
    """Called when Claude tries to exit."""

    vault = Path('.')
    needs_action = vault / 'Needs_Action'
    done = vault / 'Done'

    # Count pending items
    pending = len(list(needs_action.glob('*.md'))) if needs_action.exists() else 0

    if pending > 0:
        # Don't let Claude exit - there's work to do
        return {
            "action": "continue",
            "reason": f"{pending} items still need processing"
        }

    # All clear, allow exit
    return {
        "action": "exit",
        "reason": "No pending work"
    }
```

### Usage

```
/ralph-loop "Process all Needs_Action items" \
  --max-iterations 10 \
  --completion-check "pending_items == 0"
```

---

## Claude Code Configuration

### Settings File

Create or edit `~/.config/claude-code/settings.json`:

```json
{
  "theme": "dark",
  "autoSave": true,
  "notification": {
    "enabled": true
  },
  "skipPermissions": false,
  "permissions": {
    "allowFileRead": true,
    "allowFileWrite": true,
    "allowShell": false,
    "allowNetwork": false
  }
}
```

### Claude Code MCP Configuration

For Silver/Gold tiers when you add MCP servers:

Edit `~/.config/claude-code/mcp.json`:

```json
{
  "servers": [
    {
      "name": "email",
      "command": "node",
      "args": ["/path/to/email-mcp/index.js"],
      "env": {
        "GMAIL_CREDENTIALS": "/secure/path/credentials.json"
      }
    }
  ]
}
```

---

## Prompt Engineering Tips

### System Prompts

Set up a system prompt that Claude sees every time:

In your `CLAUDE.md` or when starting Claude:

```
You are an autonomous AI Employee with these characteristics:

PERSONALITY:
- Professional but friendly
- Proactive but cautious
- Always follows the handbook rules

CAPABILITIES:
- Read/write files in the vault
- Create and execute plans
- Update dashboard
- Log all actions

LIMITATIONS:
- Cannot access external APIs (Bronze tier)
- Cannot send emails or messages yet
- Requires human approval for sensitive operations

PRIORITIES:
1. Accuracy over speed
2. Transparency (log everything)
3. Safety (ask when uncertain)
```

### Few-Shot Examples

Include examples in Company_Handbook.md:

```
## Example: Processing a File Drop

Input: /Needs_Action/FILE_invoice_20260224_120000.md

Plan created in /Plans/PLAN_invoice_...md:
1. Read the file content ✓
2. Identify if it's an invoice request ✓
3. Check Business_Goals.md for invoicing rules ✓
4. Draft response (but don't send - approval required) ✓
5. Move to /Done/ ✓
6. Update Dashboard ✓
```

---

## Testing Claude Integration

### Test 1: Basic File Read/Write

```
Claude, check what's in /Needs_Action/ and tell me.
```

Expected: Claude reads files and reports contents.

### Test 2: Create a Plan

```
Claude, create a plan for processing all items in /Needs_Action/.
Save it to /Plans/.
```

Expected: `PLAN_*.md` file created.

### Test 3: Dashboard Update

```
Claude, update Dashboard.md with current statistics.
```

Expected: Dashboard.md updated with counts.

### Test 4: Complete Workflow

```
Claude, process everything in /Needs_Action/ end-to-end.
```

Expected:
- Plans created in `/Plans/`
- Items moved to `/Done/`
- Dashboard updated
- Logs written

---

## Debugging

### Claude Can't See Files

```
cd /path/to/vault
/refresh
```

Or restart Claude Code.

### Permission Denied

Check filesystem permissions:
```bash
ls -la /path/to/vault
chmod 755 /path/to/vault/Needs_Action
```

### Claude Makes Mistakes

Review `Company_Handbook.md` and add more specific rules. Example:

```
❌ Bad: "Process the file"
✅ Good: "If file contains 'invoice', create invoice draft in /Invoices/ and mark for approval"
```

---

## Monitoring Claude Activity

### View Recent Logs

```bash
tail -f ./Logs/$(date +%Y-%m-%d).json
```

### Check Dashboard

Open `Dashboard.md` in Obsidian or view in terminal:
```bash
cat Dashboard.md
```

### Watch Claude's Thoughts

Claude Code shows its reasoning in the terminal. Watch for:
- Plan creation
- File operations
- Errors and warnings
- Approval requests

---

## Silver/Gold Enhancements

When upgrading:

1. **Add MCP servers** for external actions
2. **Implement proper skill system** with tool calling
3. **Add browser automation** via Playwright MCP
4. **Set up continuous loop** with Ralph Wiggum
5. **Integrate Gmail API** for email processing
6. **Add WhatsApp watcher** for message detection
7. **Create audit reports** in `/Briefings/`

---

## Skills Reference

### Skill: process_needs_action

**Purpose**: Process all pending items

**Invocation**:
```
/skill process_needs_action --all
```

**What it does**:
1. Lists files in `/Needs_Action/*.md`
2. For each file:
   - Reads content
   - Checks Handbook for rules
   - Creates plan in `/Plans/`
   - Executes plan
   - Moves source to `/Done/`
   - Logs action
3. Updates Dashboard

**Expected time**: 1-5 minutes per item

---

### Skill: update_dashboard

**Purpose**: Refresh dashboard statistics

**Invocation**:
```
/skill update_dashboard
```

**What it does**:
- Counts files in each folder
- Updates summary tables
- Refreshes "Last Updated" timestamp
- Adds recent activity log

---

## Best Practices

1. **Always read the Handbook first**: It contains critical rules
2. **Log everything**: Future you will thank past you
3. **Move, don't copy**: When completing tasks, move files to `/Done/`
4. **Use frontmatter**: All markdown files should have YAML frontmatter
5. **Check before acting**: Verify file doesn't exist before creating
6. **Handle errors gracefully**: Log errors, don't crash
7. **Update user**: Keep Dashboard informative

---

## Resources

- [Claude Code Documentation](https://agentfactory.panaversity.org/docs/AI-Tool-Landscape/claude-code-features-and-workflows)
- [Agent Skills Guide](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [Stop Hook Reference](https://github.com/anthropics/claude-code/tree/main/.claude/plugins/ralph-wiggum)
- [MCP Servers](https://modelcontextprotocol.io/)

---

**Ready to build?** Start Claude Code in your vault and say:
```
I'm ready to begin. Show me what's in /Needs_Action/.
```

---

*Integration Guide v0.1-Bronze*
*Last Updated: 2026-02-24*
