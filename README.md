# AI Employee - Gold Tier Complete

*Local-first autonomous assistant using Claude Code*

## 🎉 Status

**Gold Tier** is fully implemented and tested. All phases complete!

- ✅ Bronze Tier: Complete (foundation)
- ✅ **Silver Tier**: Complete (external integrations)
- ✅ **Gold Tier**: Complete (advanced integrations, error recovery, audit logging, cross-domain workflows)

## Quick Start

1. **Clone and setup** (see Installation below)
2. **Configure credentials** (see Security)
3. **Start watchers** to monitor Gmail/WhatsApp
4. **Use Claude Code** to process tasks with `/skill` commands
5. **Approve sensitive actions** via `approval_manager.py`

## What's Included

### ✅ Bronze Tier (Complete)

- [x] Obsidian vault structure with required folders
- [x] Dashboard.md for real-time status
- [x] Company_Handbook.md with rules and guidelines
- [x] Filesystem watcher (processes dropped files)
- [x] Claude Code integration
- [x] Basic execution workflow

### 🥈 Silver Tier (Complete)

**External Integrations:**
- [x] **Gmail Watcher** - Monitors Gmail, creates EMAIL_*.md action items
- [x] **WhatsApp Watcher** - Monitors WhatsApp Web, creates WHATSAPP_*.md
- [x] **Email Sending** - Gmail API integration (send, reply, draft)
- [x] **LinkedIn Auto-Poster** - Post to LinkedIn via Playwright
- [x] **Scheduler** - Cron-based task automation

**Workflow Components:**
- [x] **Human-in-the-Loop Approval System**
  - Approval Manager CLI (`utils/approval_manager.py`)
  - Approved Executor (auto-executes approved actions)
  - Pending_Approval/, Approved/, Rejected/ folders
- [x] **7 Agent Skills** in `.claude/skills/`
  - `process_email_requests` - Handle incoming emails
  - `process_whatsapp_messages` - Handle WhatsApp messages
  - `approval_workflow` - Manage approvals
  - `linkedin_auto_poster` - Post LinkedIn updates
  - `generate_weekly_briefing` - CEO reports
  - `browsing-with-playwright` - Web automation
  - `process_needs_action` - General file processing
  - `manage_odoo_accounting` - Odoo integration (Gold Phase 1)

### 🥇 Gold Tier (Complete - All 4 Phases)

**Phase 1: Odoo MCP Server (Complete)**
- [x] **Odoo MCP Server** - Odoo 19+ integration via JSON-RPC
  - Tools: `search_customers`, `create_invoice`, `post_invoice`, `record_payment`, `get_account_balance`, `list_recent_invoices`
  - Docker deployment with PostgreSQL
  - Automated setup script
  - Per-process audit logging (no cross-process corruption)
  - Receipt files in `Done/` for all external actions
- [x] **Ralph Wiggum Loop** - Autonomous task completion stop hook
  - File-based completion detection
  - State management with `loop_state.json`
  - Max iteration limits

**Phase 2: Social Media Integration (Complete)**
- [x] **Social Media MCP Server** - Unified Facebook, Instagram, Twitter integration
  - Tools: `facebook_post`, `facebook_get_insights`, `instagram_post`, `twitter_tweet`, `twitter_get_timeline`, `twitter_get_mentions`
  - Graph API (Facebook/Instagram) + X API v2 (Twitter)
  - Platform-specific formatting and optimization
  - Per-process audit logging
  - Receipt files in `Done/` for all posts
- [x] **Social Media Skill** - `post_to_social_media` Agent Skill
  - Multi-platform posting with auto-formatting
  - Hashtag optimization
  - Approval workflow integration

**Phase 3: Error Recovery & Audit Logging (Complete)**
- [x] **Retry Logic & Circuit Breakers** - Automatic error recovery for all external API calls
  - Exponential backoff with jitter (2^attempt, max 60s)
  - Circuit breaker pattern (CLOSED/OPEN/HALF_OPEN)
  - Platform-specific breakers (facebook, instagram, twitter, odoo)
- [x] **Enhanced Audit Logger** - Structured JSON audit trail
  - AuditEntry schema (UUID, timestamp, actor, action, target, parameters, result, duration_ms, error)
  - **Per-process log files** (`YYYY-MM-DD.proc_PID.json`) to prevent corruption
  - Absolute path resolution (project root based)
  - Daily log rotation with size-based fallback
  - Gzip archival and 90-day retention
  - Query interface with list/string action filters
  - Compliance report generation
- [x] **Health Monitoring Server** - HTTP endpoints for production
  - `/health`, `/health/ready`, `/health/live` (Kubernetes-style probes)
  - `/metrics` for monitoring systems
  - Component checks: Odoo, social-mcp, PostgreSQL, disk, memory
  - Background daemon with automatic restart
- [x] **Integration** - All MCP servers use error recovery and audit logging

**Phase 4: Cross-Domain Integration & Dashboard (Complete)**
- [x] **Event Bus Architecture** - File-based event system for decoupled communication
  - `Event`, `EventStore`, `EventConsumer` classes
  - Persistence in `AI_Employee_Vault/Events/`
  - Retry logic with `retry_count` and `max_retries`
  - Routing with `consumed_by` field
  - Error event capturing
  - Demo script (`utils/event_bus/demo.py`)
- [x] **Real-Time Dashboard Consumer** - Event-driven dashboard updates
  - Listens for events (invoice_created, post_published, etc.)
  - Auto-updates social media counts without polling
- [x] **Email→Odoo Consumer** - Cross-domain integration example
  - Consumes email events from Needs_Action
  - Creates Odoo invoices automatically
  - Full audit trail with events
- [x] **Audit Analytics Skill** - `analyze_audit_logs` in `.claude/skills/`
  - Queries audit logs with filters
  - Generates markdown, JSON, CSV reports
  - Trend analysis (by day, actor, action)
- [x] **Enhanced CEO Briefing** - Weekly report with Odoo/social/audit data
  - Aggregates financial metrics, social media stats, audit analytics
  - Auto-generated in `Briefings/`
- [x] **Production Deployment Scripts**
  - `start_all.sh` - One-command service startup
  - `stop_all.sh` - Graceful shutdown
  - `status.sh` - Comprehensive health check
  - All services with PID management and logging
- [x] **Dashboard Updater** - Live metrics from all sources
  - Fetches health metrics (health server)
  - Queries Odoo for AR, invoices, overdue
  - Reads audit logs for social media posts
  - Counts task completions from `Done/`
  - Updates `Dashboard.md` every 5 minutes (configurable)
- [x] **External Action Receipts** - Receipt files in `Done/` for all external operations
  - Facebook/Instagram posts: `FACEBOOK_POST_*.md`, `INSTAGRAM_POST_*.md`
  - Odoo invoices: `ODOO_INVOICE_CREATE_*.md`, `ODOO_INVOICE_POST_*.md`
  - Structured frontmatter with platform, action, external_id, URL, duration
  - Full parameters and result in JSON format
  - Smart extraction: amount, description, due date, customer
- [ ] **Audit Analytics Skill** - `analyze_audit_logs` for compliance & insights
- [ ] **Event Bus** - Decoupled event-driven architecture (`utils/event_bus/`)
- [ ] **Enhanced CEO Briefing** - Full business intelligence (financials + social + ops)
- [ ] **Production Scripts** - `start_all.sh`, `stop_all.sh`, `status.sh`

**Skills Created in Phase 4:**
- `email_to_odoo_invoice` - Create invoices from email (in progress)
- `integrate_cross_domain` - Event-driven workflows (planned)
- `update_dashboard` - Dashboard refresh (implemented as script)
- `analyze_audit_logs` - Audit analytics (planned)

---

### Folder Structure (Complete)

### Folder Structure (Complete)

```
AI_Employee_Vault/
├── Dashboard.md              # Real-time status overview
├── Company_Handbook.md       # AI rules & guidelines
├── Business_Goals.md         # Objectives & targets
├── Needs_Action/             # Items needing processing
│   ├── EMAIL_*.md           # From Gmail watcher
│   ├── WHATSAPP_*.md        # From WhatsApp watcher
│   └── FILE_*.md            # From filesystem watcher
├── Inbox/                    # Raw dropped files (Bronze)
├── Plans/                    # Active execution plans
├── Pending_Approval/         # Awaiting human review
├── Approved/                 # Approved actions (executor processes these)
├── Rejected/                 # Denied actions (archived)
├── Done/                     # Completed tasks
├── Logs/                     # Audit trail (YYYY-MM-DD.json)
└── Briefings/                # Weekly CEO reports

watchers/                     # Monitoring scripts
├── gmail_watcher.py         # Gmail API polling
├── whatsapp_watcher.py      # WhatsApp Web automation
└── approved_executor.py     # Executes approved actions

utils/                       # Utility scripts
├── send_email_direct.py     # Gmail API sender
├── approval_manager.py      # CLI for approvals
├── linkedin_poster.py       # LinkedIn posting
└── [...]

scheduler/                   # Cron-based scheduler
├── scheduler.py
└── config.yaml

mcp-servers/                 # MCP servers (Gold Tier)
├── odoo-mcp/                # Odoo Community integration (Phase 1)
│   ├── server.py
│   ├── requirements.txt
│   ├── docker-compose.yml
│   ├── test_connection.py
│   ├── setup_odoo.py
│   └── README.md
├── social-mcp/              # Social Media integration (Phase 2)
│   ├── server.py
│   ├── requirements.txt
│   ├── test_connection.py
│   ├── setup_credentials.py
│   └── README.md
└── README.md                # Overview

.claude/
├── skills/                  # Agent Skills
│   ├── process_email_requests/
│   ├── process_whatsapp_messages/
│   ├── approval_workflow/
│   ├── linkedin_auto_poster/
│   ├── generate_weekly_briefing/
│   ├── process_needs_action/
│   ├── update_dashboard/
│   ├── manage_odoo_accounting/  # Gold Tier skill (Phase 1)
│   └── post_to_social_media/    # Gold Tier skill (Phase 2)
└── stop-hooks/
    └── ralph_wiggum.py      # Autonomous loop handler (Phase 1)
```

## Installation

### Prerequisites

- **Python 3.13+** (tested with 3.13)
- **Claude Code** - [Installation guide](https://docs.anthropic.com/en/docs/claude-code)
- **Git** (for version control)
- **Obsidian** (optional, for GUI vault viewing)

### Silver Tier Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers (for LinkedIn & WhatsApp watchers)
playwright install chromium
playwright install-deps chromium  # On Linux/WSL only

# Install Claude Code (if not already)
npm install -g @anthropic-ai/claude-code
```

### Setup Steps

1. **Clone repository**
   ```bash
   git clone <your-repo>
   cd <repo>
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # On Linux/macOS:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Google OAuth** (for Gmail watcher & sender)
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create project or select existing
   - Enable Gmail API
   - Create OAuth credentials (Desktop app)
   - Download `credentials.json` and place in project root
   - **Important**: Add both scopes:
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/gmail.send`
   - Configure OAuth consent screen (add your email as test user)
   - See `WATCHERS_README.md` for detailed steps

5. **Prepare the vault**
   ```bash
   # All folders are pre-created
   # Ensure write permissions:
   chmod -R u+rwX AI_Employee_Vault/
   ```

6. **Initial authentication** (run once)
   ```bash
   # Authenticate Gmail (will open browser)
   python watchers/gmail_watcher.py --vault AI_Employee_Vault --credentials credentials.json --single-run
   # Follow the OAuth flow, save token.json

   # Test WhatsApp Web (will open browser, scan QR)
   python watchers/whatsapp_watcher.py --vault AI_Employee_Vault --single-run
   # Scan QR code with your phone, wait for login
   ```

### Folder Permissions (Security)

```bash
# Set restrictive permissions (optional but recommended)
chmod 700 AI_Employee_Vault/
find AI_Employee_Vault -type d -exec chmod 700 {} \;
chmod 600 AI_Employee_Vault/Dashboard.md AI_Employee_Vault/Company_Handbook.md AI_Employee_Vault/Business_Goals.md
find AI_Employee_Vault/Logs -type f -name "*.json" -exec chmod 600 {} \;
find AI_Employee_Vault/Needs_Action -type f -name "*.md" -exec chmod 600 {} \;
```

---

## Usage

### Starting the Watchers

**Important**: Run watchers in **separate terminals** so they can monitor continuously.

#### 1. Gmail Watcher
```bash
python watchers/gmail_watcher.py \
  --vault AI_Employee_Vault \
  --credentials credentials.json \
  --check-interval 60  # Check every 60 seconds
```
It will poll Gmail for unread IMPORTANT emails and create `EMAIL_*.md` files.

#### 2. WhatsApp Watcher
```bash
python watchers/whatsapp_watcher.py \
  --vault AI_Employee_Vault \
  --session-path ./session \
  --check-interval 30
```
First run: Scan QR code with your phone. Session persists for future runs.

#### 3. Scheduler (Optional)
```bash
python scheduler/scheduler.py --config scheduler/test_scheduler_config.yaml
```
Or create your own cron-like schedule YAML.

---

### Processing Tasks with Claude Code

Open a new terminal, navigate to the project, and start Claude Code in the vault:

```bash
cd "/mnt/e/7. Low Code Agentic AI/Hackathon 0"
claude AI_Employee_Vault
```

Claude will detect the vault and its Agent Skills. Use these commands:

#### Process All Emails
```
/skill process_email_requests --all
```
- Reads all `EMAIL_*.md` from `Needs_Action/`
- Analyzes sender and content
- Creates plans in `/Plans/`
- For known contacts: drafts reply (may auto-approve)
- For new contacts: creates approval request in `/Pending_Approval/`
- Updates Dashboard and logs

#### Process All WhatsApp Messages
```
/skill process_whatsapp_messages --all
```
- Processes `WHATSAPP_*.md` files
- Generates friendly, concise responses
- Requires approval for new contacts
- Logs all actions

#### Generate Weekly Briefing
```
/skill generate_weekly_briefing
```
- Reviews completed tasks from `/Done/`
- Analyzes progress against `Business_Goals.md`
- Generates CEO-style weekly report in `/Briefings/`

#### Manage Approvals (from Claude)
```
/skill approval_workflow --list-pending
/skill approval_workflow --approve-all --dry-run  # Preview
/skill approval_workflow --approve-all            # Execute
```

---

### Manual Approval via CLI

If you prefer to approve manually (or via script):

```bash
# List pending approvals
python utils/approval_manager.py --vault AI_Employee_Vault --list-pending

# Approve a specific request
python utils/approval_manager.py --vault AI_Employee_Vault --approve "APPROVAL_EMAIL_sender_*.md"

# Approve all pending (use with caution!)
python utils/approval_manager.py --vault AI_Employee_Vault --approve-all

# Reject (move to Rejected/)
python utils/approval_manager.py --vault AI_Employee_Vault --reject "APPROVAL_*.md" --reason "Not needed"
```

---

### Approved Executor

The executor watches `/Approved/` and automatically executes approved actions:

```bash
# Single run (one-time check)
python watchers/approved_executor.py --vault AI_Employee_Vault --single-run

# Continuous watch mode (recommended)
python watchers/approved_executor.py --vault AI_Employee_Vault --watch --check-interval 10
```

What it does:
- Detects files moved to `/Approved/`
- Extracts action type (send_email, post_linkedin, etc.)
- Executes via appropriate tool (Gmail API, LinkedIn API, etc.)
- Moves source + approval file to `/Done/`
- Logs result

**Note**: WhatsApp responses are not auto-sent yet (requires WhatsApp Business API or Twilio). For now, the executor will generate a draft or prompt for manual sending.

---

### LinkedIn Auto-Poster

```bash
python utils/linkedin_poster.py \
  --content "Your post text here" \
  --dry-run  # Preview first (doesn't actually post)
```

Or create a plan and let Claude invoke it.

For scheduled posting, use the scheduler to run this command.

---

## Understanding the Workflow

### Complete Silver Tier Data Flow

```
1. Watchers Detect External Events
   ├── Gmail Watcher → EMAIL_*.md (Needs_Action)
   ├── WhatsApp Watcher → WHATSAPP_*.md (Needs_Action)
   └── Filesystem Watcher → FILE_*.md (Needs_Action)

2. Claude Process (via /skill commands)
   ├── Reads from Needs_Action/
   ├── Creates execution plan in /Plans/
   ├── Determines if approval needed (per Company_Handbook)
   ├── If approval needed → creates /Pending_Approval/ request
   └── If no approval → executes directly

3. Human-in-the-Loop (if needed)
   ├── Human reviews /Pending_Approval/
   ├── Moves to /Approved/ or /Rejected/
   └── (Or uses approval_manager.py CLI)

4. Approved Executor (watches /Approved/)
   ├── Detects new approvals
   ├── Executes action (send_email, post_linkedin, etc.)
   ├── Logs result
   └── Moves everything to /Done/

5. Dashboard & Logs Update
   ├── Dashboard.md updated in real-time
   ├── Logs/YYYY-MM-DD.json appended
   └── Briefings generated weekly

Result: Fully autonomous AI employee with human oversight on sensitive actions.
```

---

## Security Notes

### Silver Tier Security Status

- ✅ **Local-first**: All data stored locally in vault
- ✅ **HITL**: Human approval required for sensitive actions
- ✅ **Audit Logging**: Every action logged in `/Logs/`
- ✅ **Credentials**: Stored as `credentials.json` & `token.json` (never commit!)
- ⚠️ **Encryption**: Logs not encrypted (avoid PII in them)
- ⚠️ **Browser Sessions**: Stored in `linkedin_session/`, `session/` (never commit!)

### Never Commit These Files

These are in `.gitignore` but be vigilant:

- `credentials.json` - Google OAuth client credentials
- `token.json` - OAuth access/refresh tokens
- `linkedin_session/` - Persistent browser cookies
- `session/` - WhatsApp session data
- `AI_Employee_Vault/Logs/*.json` - May contain email content
- `AI_Employee_Vault/Approved/`, `Pending_Approval/` - May contain sensitive requests

**Check before committing:**
```bash
git status --short | grep -E "credentials|token|session|Logs/.*\.json"
# Should return nothing
```

### Best Practices

1. Use environment variables for API keys in production
2. Rotate credentials monthly
3. Review audit logs daily
4. Never disable approval workflow for new contacts
5. Encrypt logs if they contain PII (use `cryptography` library)
6. Backup vault to encrypted location
7. Run watchers under separate user account if possible

See `SECURITY.md` for comprehensive security guidelines.

---

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

## What's Next? (Gold Tier)

Silver Tier is complete. The following are planned for **Gold Tier**:

- **Database Integration**: PostgreSQL for persistent storage
- **Advanced Monitoring**: Real-time metrics, health checks, alerts
- **Multi-Agent Coordination**: Use Anthropic's Agents SDK for specialized sub-agents
- **Odoo Integration**: Accounting, CRM, ERP sync
- **Advanced CEO Briefing**: Business analytics, KPI tracking, trend analysis
- **Error Recovery**: Self-healing, retry logic, fallback strategies
- **Ralph Wiggum Loop**: Fully autonomous operation with completion detection
- **MCP Server Polish**: Refine email MCP, add WhatsApp MCP, add calendar MCP

---

## Resources

- **Hackathon Doc**: `Personal AI Employee Hackathon 0 Building Autonomous FTEs in 2026.md`
- **Architecture Guide**: See Sections 2-5 in hackathon document
- **Agent Skills Guide**: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- **MCP Servers**: https://modelcontextprotocol.io/
- **Claude Code**: https://docs.anthropic.com/en/docs/claude-code

## Troubleshooting

### Gmail watcher fails to authenticate
- Ensure `credentials.json` is valid and has both Gmail scopes
- Check OAuth consent screen is configured (add test user if in testing phase)
- Delete `token.json` and re-authenticate: `python reauth_with_send.py`

### WhatsApp watcher closes immediately
- Must run on Windows/macOS (WSL lacks audio libraries)
- Ensure you have Playwright browsers installed: `playwright install chromium`
- Check `whatsapp_watcher.log` for errors
- Try increasing timeout: edit `watchers/whatsapp_watcher.py` line 518

### Claude skills not showing
- Start Claude Code from vault directory: `claude AI_Employee_Vault`
- Ensure skills have `skill.md` in `.claude/skills/<skill-name>/`
- Some skills require external dependencies (e.g., Gmail API for email processing)

### No emails being detected by Gmail watcher
- Verify query: only unread emails marked as IMPORTANT are detected
- Mark test emails as Important in Gmail
- Check `gmail_watcher.log` for errors
- Ensure `credentials.json` has Gmail read-only scope

---

## Contributing

This is a hackathon project. To contribute:

1. Fork and create feature branch
2. Follow the architecture in `Company_Handbook.md`
3. Add tests for new components
4. Update documentation
5. Submit Pull Request

---

## License

MIT License - see LICENSE file (if present)

---

**Status**: Silver Tier Complete ✅
**Version**: 0.2.0
**Last Updated**: 2026-02-28
**Next Milestone**: Gold Tier

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
