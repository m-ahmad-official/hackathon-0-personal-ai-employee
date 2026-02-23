# AI Employee - Bronze Tier

*Local-first autonomous assistant using Claude Code*

## Overview

This is a Bronze Tier implementation of the Personal AI Employee hackathon project. It provides the foundational components for an autonomous system that monitors folders and processes files.

## What's Included

### ✅ Bronze Tier Requirements

- [x] Obsidian vault structure with required folders
- [x] Dashboard.md for real-time status
- [x] Company_Handbook.md with rules and guidelines
- [x] One working Watcher script (filesystem monitoring)
- [x] Claude Code can read from and write to vault
- [x] Basic folder structure: `/Inbox`, `/Needs_Action`, `/Done`
- [x] All functionality implemented as Agent Skills ready

### Folder Structure

```
.
├── Dashboard.md              # Main dashboard (status overview)
├── Company_Handbook.md       # AI rules and guidelines
├── Needs_Action/             # Items needing processing
├── Inbox/                    # Drop zone for files
├── Plans/                    # Execution plans
├── Done/                     # Completed tasks
├── Logs/                     # Audit trail
├── Pending_Approval/         # Awaiting human review
├── Approved/                 # Approved actions
├── Rejected/                 # Denied actions
└── watcher.py                # Filesystem monitoring script
```

## Installation

### Prerequisites

- Python 3.13+
- Claude Code (installed and configured)
- Obsidian (optional, for GUI)

### Setup Steps

1. **Create virtual environment** (Python)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Prepare the vault**
   ```bash
   # The folder structure is already created
   # Just ensure you have write permissions
   ```

## Usage

### Starting the Filesystem Watcher

The watcher monitors a folder called `drops` (or any folder you specify) for new files.

```bash
# Create a drops folder
mkdir drops

# Start the watcher
python watcher.py --vault . --drop-folder ./drops
```

**In another terminal**, test it by dropping a file:

```bash
# Copy any file to trigger
cp /path/to/your/file.txt ./drops/
```

The watcher will:
1. Detect the new file
2. Copy it to `/Inbox/`
3. Create an action item in `/Needs_Action/FILE_<name>_<timestamp>.md`
4. Update the Dashboard

### Interacting with Claude Code

To have Claude process pending tasks:

```bash
# Navigate to vault directory
cd /path/to/vault

# Start Claude Code
claude .

# Claude should see the vault files and be able to:
# - Read from /Needs_Action
# - Write Plans to /Plans
# - Update Dashboard.md
# - Move completed tasks to /Done
```

Example prompt to Claude:
```
Process all items in /Needs_Action folder. For each file:
1. Read and understand the content
2. Create a detailed plan in /Plans/
3. Execute the plan (read/write operations only)
4. Move completed items to /Done/
5. Update the dashboard with status
```

### Understanding the Workflow

1. **Drop a file** into the watched folder → `drops/`
2. **Watcher detects** it and creates metadata in `/Needs_Action/`
3. **File is copied** to `/Inbox/` for safe keeping
4. **Claude Code** processes items (manual or automated trigger)
5. **Claude creates** a Plan.md in `/Plans/` with steps
6. **Claude executes** the plan (file operations only for Bronze)
7. **Claude moves** completed items to `/Done/`
8. **Dashboard is updated** with completion status

## Claude Code Integration

### As Agent Skills

All AI functionality should be implemented as Claude Agent Skills:

1. **Skill: Process Needs Action**
   - Read all files in `/Needs_Action/`
   - Generate plans
   - Execute plans
   - Update dashboard

2. **Skill: Generate Weekly Briefing**
   - Review completed tasks
   - Analyze progress against goals
   - Generate CEO briefing report

To create skills, see: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

### Ralph Wiggum Loop

For autonomous operation, use the Ralph Wiggum Stop hook to keep Claude working until tasks are complete:

```bash
# Claude will loop until all tasks in Needs_Action are processed
/ralph-loop "Process all tasks in /Needs_Action" \
  --completion-promise "TASKS_COMPLETE" \
  --max-iterations 10
```

## Security Notes

⚠️ **Bronze Tier Security**:
- No external integrations yet (only local files)
- All data remains on your machine
- No API keys or credentials required
- Human approval not automated (manual review required)

When upgrading to Silver/Gold:
- Implement HITL approval system
- Use environment variables for secrets
- Add audit logging
- Never auto-approve sensitive actions

See `Company_Handbook.md` for full security guidelines.

## Testing

### Test 1: Basic Drop

```bash
# Create test file
echo "Test content $(date)" > test.txt

# Drop it
cp test.txt ./drops/

# Check results:
# - Should see FILE_test_*.md in /Needs_Action/
# - Should see test.txt copied to /Inbox/
# - Should see log entry in watcher.log
```

### Test 2: Claude Processing

```bash
# Start Claude
claude .

# Prompt:
"""
Process the action item in /Needs_Action/.
Create a plan in /Plans/, then move the file to /Done/.
Finally, update Dashboard.md.
"""

# Verify:
# - Plan created in /Plans/
# - Action item moved to /Done/
# - Dashboard updated
```

## Troubleshooting

### Watcher not starting
- Ensure Python 3.13+ is installed: `python --version`
- Install dependencies: `pip install -r requirements.txt`
- Check folder paths exist

### No files being detected
- Verify you're dropping files in the correct `--drop-folder`
- Check watcher.log for errors
- Ensure you have read/write permissions

### Claude can't see the vault
- Start Claude from the vault directory: `claude .`
- Or navigate to vault in Claude Code: `cd /path/to/vault`
- Check file permissions

## Next Steps (Silver/Gold Tier)

To upgrade your AI Employee:

1. **Silver Tier**:
   - Add Gmail/WhatsApp watchers
   - Implement MCP servers for external actions
   - Add HITL approval workflow
   - Enable LinkedIn auto-posting

2. **Gold Tier**:
   - Integrate Odoo accounting
   - Add business audit & CEO briefing
   - Implement Ralph Wiggum autonomous loop
   - Add error recovery

3. **Platinum Tier**:
   - Deploy to cloud 24/7
   - Set up cloud/local hybrid
   - Multi-agent delegation

## Resources

- Full Hackathon Doc: `Personal AI Employee Hackathon 0 Building Autonomous FTEs in 2026.md`
- Architecture Guide: See Section 2-5 in hackathon doc
- Claude Code Skills: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- MCP Servers: https://modelcontextprotocol.io/

## Support

- Issues: Check `watcher.log` and Claude Code output
- Questions: Review `Company_Handbook.md`
- Ideas: See hackathon document's troubleshooting section

---

**Status**: Bronze Tier Complete ✅
**Version**: 0.1.0
**Last Updated**: 2026-02-24
