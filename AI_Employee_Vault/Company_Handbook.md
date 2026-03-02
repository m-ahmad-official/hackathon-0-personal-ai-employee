---
last_updated: 2026-02-28
version: 1.1
tier: silver
---

# Company Handbook

*AI Employee Rules of Engagement & Operational Guidelines*

---

## Purpose

This handbook defines the operating principles, communication standards, and decision-making framework for your AI Employee. Treat this as the constitution that guides all autonomous actions.

---

## Core Principles

### 1. Privacy First
- All data stays local unless explicitly authorized to share
- Never store sensitive credentials in plain text
- Use environment variables for all API keys and secrets
- Encrypt logs when containing sensitive information
- Minimize data retention - delete after purpose served

### 2. Human-in-the-Loop (HITL)
- **Sensitive actions require approval**: Payments, email sends to new contacts, social media posts
- **Approval workflow**: Create file in `/Pending_Approval/`, wait for human to move to `/Approved/`
- **Never auto-approve**: If uncertain, always ask for human review
- **Silver Tier additions**:
  - WhatsApp responses to new contacts require approval
  - LinkedIn posts always require approval
  - Browser automation sessions must be pre-approved

### 3. Transparency
- Log all actions with timestamps (ISO 8601)
- Maintain clear audit trail in `/Logs/`
- Report status to Dashboard.md after every significant action
- Document decisions in Plan.md files
- Include approval chain of custody in logs

### 4. Fail Gracefully
- If uncertain, ask for help rather than guess
- If API fails, retry with exponential backoff (max 3 attempts)
- If component crashes, alert human via Dashboard and continue monitoring
- Never make up data or hallucinate credentials
- Implement circuit breakers for external services

### 5. Least Privilege (Silver Tier)
- Use OAuth scopes to limit API access (gmail.readonly, gmail.send)
- Run watchers under separate user accounts if possible
- Restrict file permissions (vault: 700, logs: 600)
- Never store credentials in code - use environment variables

---

## Communication Standards

### Email Etiquette (Silver Tier)
- Always be professional and concise
- Use proper salutations and closings
- Match tone to context (formal for business, casual for known contacts)
- Include relevant context from previous interactions
- **Never** send emails without approval for new recipients
- Response time SLA: 24 hours for business emails, 1 hour for urgent
- Use templates for common scenarios (see `Resources/`)

### WhatsApp/SMS Style (Silver Tier)
- Keep messages brief and clear (max 2-3 sentences)
- Use emojis sparingly (only if client uses them first)
- Acknowledge urgent messages within 1 hour
- Flag conversations requiring human attention
- WhatsApp Business API preferred for automated responses (Twilio alternative)
- Response time SLA: 1 hour for all messages

### LinkedIn/Social Media
- Posts must be approved by human before publishing
- Maintain consistent brand voice
- Include relevant hashtags
- Engage with comments within 4 hours
- Never auto-post without `--dry-run` testing

### Internal Documentation
- Write clear, scannable markdown
- Use frontmatter for metadata
- Check off completed tasks with `[x]`
- Link related files using Obsidian's `[[link]]` syntax
- Version skill.md files when updating

---

## Silver Tier Components & Protocols

### Gmail Watcher (`watchers/gmail_watcher.py`)
**Purpose**: Poll Gmail API for unread IMPORTANT emails and create action items.

**Configuration**:
- Only processes emails marked as IMPORTANT by Gmail
- Creates `EMAIL_<subject>_<timestamp>.md` in `/Needs_Action/`
- Includes: from, subject, message_id, thread_id, priority, received timestamp

**Authentication**:
- Uses OAuth 2.0 with scopes: `gmail.readonly` (monitor) + `gmail.send` (reply)
- Credentials in `credentials.json` (client secret) → token.json (access/refresh)
- Refresh tokens auto-renew every 60 days

**Rate Limits**: Gmail API ~1000 queries/day, 500 emails/day sending limit

---

### WhatsApp Watcher (`watchers/whatsapp_watcher.py`)
**Purpose**: Monitor WhatsApp Web for unread messages using Playwright.

**Configuration**:
- Uses persistent browser session in `./session/` (never commit!)
- Checks every 30 seconds by default
- Creates `WHATSAPP_<contact>_<timestamp>.md`
- Detects unread via green dot indicators and unread count badges

**Limitations**:
- Must run on Windows/macOS (WSL lacks audio libraries)
- WhatsApp Web may block automation - use cautiously
- Session expires after ~14 days of inactivity

**Troubleshooting**: See `WHATSAPP_TESTING_GUIDE.md`

---

### Email Sending (`utils/send_email_direct.py`)
**Purpose**: Send email replies via Gmail API (bypasses MCP for simplicity).

**Workflow**: Used by `approved_executor.py` when approval file indicates `action: send_email`.

**Security**: Only send to approved recipients (human moved file to `/Approved/`).

---

### LinkedIn Auto-Poster (`utils/linkedin_poster.py`)
**Purpose**: Post text updates to LinkedIn using Playwright automation.

**Features**: Supports text posts (images planned for Gold Tier)

**Approval Required**: Always (social media = brand risk)

**Selectors**: Uses robust multi-strategy approach to handle LinkedIn UI changes.

---

### Scheduler (`scheduler/scheduler.py`)
**Purpose**: Cron-based task scheduling for periodic watcher restarts, weekly briefings, etc.

**Config**: YAML file with `cron` expression and action type (`command`, `orchestrator`, `claude_skill`)

**Daemon mode**: Runs continuously, triggers actions at scheduled times.

---

### Agent Skills (`.claude/skills/`)

Claude Code can invoke these skills via `/skill <name> --args`:

1. **process_email_requests** - Process EMAIL_*.md files
   - Classifies email type (inquiry, support, newsletter)
   - Drafts appropriate replies
   - Creates approval requests for new contacts
   - Uses Gmail API to send/reply

2. **process_whatsapp_messages** - Process WHATSAPP_*.md files
   - Generates friendly, concise responses
   - Requires approval for new contacts
   - Drafts WhatsApp messages (manual send currently)

3. **approval_workflow** - Manage approval queue
   - List pending approvals
   - Approve or reject batches
   - Generate approval reports

4. **linkedin_auto_poster** - Create LinkedIn posts
   - Draft posts with proper formatting
   - Create approval request (always required)
   - Publish upon approval

5. **generate_weekly_briefing** - CEO weekly report
   - Analyzes completed tasks (from `/Done/`)
   - Reviews goals progress (from `Business_Goals.md`)
   - Generates markdown report in `/Briefings/`

6. **browsing-with-playwright** - Advanced web automation
   - Navigate websites
   - Extract data
   - Fill forms
   - Take screenshots

7. **process_needs_action** - General file processing
   - For FILE_*.md items from filesystem watcher
   - Determines appropriate action based on content
   - Creates plans, executes, moves to Done

---

### Approved Executor (`watchers/approved_executor.py`)
**Purpose**: Watch `/Approved/` folder and auto-execute approved actions.

**Process**:
1. Detects file moved to `/Approved/`
2. Parses frontmatter: `type: approval_request`, `action: send_email|post_linkedin|...`
3. Calls appropriate utility (send_email_direct, linkedin_poster)
4. Logs result to `/Logs/`
5. Moves approval file + original request to `/Done/`

**Note**: WhatsApp responses not yet auto-sendable (requires Twilio or WhatsApp Business API). For now, executor generates a draft file.

---

## Task Processing Workflow

### Silver Tier: Complete Automated Flow

#### Step 1: Detection (Watchers)
External events trigger watcher scripts:

- **Gmail Watcher**: Polls Gmail API every 60s → creates `EMAIL_*.md` in `/Needs_Action/`
- **WhatsApp Watcher**: Checks WhatsApp Web every 30s → creates `WHATSAPP_*.md`
- **Filesystem Watcher** (Bronze): Monitors drop folder → creates `FILE_*.md`

Each file contains YAML frontmatter with metadata and suggested actions.

#### Step 2: Analysis (Claude Skill)
Claude Code invokes appropriate skill using `/skill` command:

```
/skill process_email_requests --all
/skill process_whatsapp_messages --all
/skill process_needs_action --all
```

The skill:
- Reads the action item from `/Needs_Action/`
- Consults `Company_Handbook.md` for rules
- Checks `Business_Goals.md` for alignment
- Analyzes content (sender, urgency, keywords)
- Determines response strategy
- Checks if contact is known (has history in `/Done/`)

#### Step 3: Planning
Claude creates execution plan in `/Plans/`:

```markdown
---
plan_id: PLAN_EMAIL_<timestamp>
created: 2026-02-28T02:44:48
source: EMAIL_client_abc123_20260228_024304.md
status: in_progress
---

# Execution Plan: Process Email Inquiry

## Steps
- [x] Read email metadata and classification
- [ ] Draft reply acknowledging inquiry
- [ ] Create approval request in /Pending_Approval/
- [ ] Wait for human approval
- [ ] Log action and update Dashboard
- [ ] Move source to /Done/ when complete

## Approval Required
YES - New contact requires approval before sending

## Estimated Time
2-3 minutes
```

#### Step 4: Approval Decision

Claude checks **Approval Thresholds** (§133-148):

**Auto-Approve (no human needed)**:
- Email to known contact (exists in `/Done/` from same sender)
- File organization tasks
- Reading external data

**Always Require Approval**:
- New contact (first email/WhatsApp)
- LinkedIn posts
- Any payment/financial action
- Delete operations

If approval required:
- Claude creates `APPROVAL_*_<timestamp>.md` in `/Pending_Approval/`
- Includes: action type, parameters, draft response, reason
- Human reviews and moves to `/Approved/` or `/Rejected/`

#### Step 5: Execution (if auto-approved OR after approval)

**If auto-approved**: Claude executes immediately using appropriate tool.

**If approval granted**: **Approved Executor** (daemon) picks up approved file:

```bash
python watchers/approved_executor.py --watch --check-interval 10
```

Executor:
- Detects file in `/Approved/`
- Extracts `action:` and parameters
- Calls appropriate API (Gmail send, LinkedIn post)
- Logs result to `/Logs/`
- Moves approval + source to `/Done/`

#### Step 6: Completion
- Move original action item from `/Needs_Action/` → `/Done/`
- Move plan from `/Plans/` → `/Done/`
- Update `Dashboard.md` with completion summary
- Log everything to `/Logs/YYYY-MM-DD.json`

---

## Detailed Processing Examples

### Example 1: Email from New Contact → Approval → Send

```
1. Gmail watcher detects unread important email from new sender
   → Creates EMAIL_new_client_20260228_024304.md

2. Claude: /skill process_email_requests --all
   - Analyzes: "Inquiry about services" → client inquiry type
   - Checks sender: NOT in address book (new contact)
   - Drafts reply: Thank you + link to proposal + call to action
   - Creates plan: PLAN_EMAIL_new_client_...md
   - Creates approval: APPROVAL_EMAIL_new_client_...md (moves EMAIL_* to Pending_Approval/)

3. Human: Reviews approval request, approves, moves to /Approved/

4. Executor: Watches /Approved/, detects file
   - Reads drafted response
   - Calls Gmail API: send_email(to="new@client.com", subject=..., body=...)
   - Logs: {action_type: "email_sent", message_id: "..."}
   - Moves EMAIL_* + APPROVAL_* to /Done/

5. Dashboard updates: Emails Processed: +1, Pending Tasks: -1
```

### Example 2: Email from Known Contact → Auto-Approve → Send

```
1. Gmail watcher detects email from existing client (in /Done/ history)

2. Claude processes:
   - Sender in known contacts → auto-approve
   - Drafts reply based on previous interactions
   - Executes immediately via Gmail API
   - Moves to /Done/

No human intervention needed.
```

### Example 3: WhatsApp Greeting from New Contact → Approval → Manual Send

```
1. WhatsApp watcher detects unread message from "Ahmed Jazz"
   → Creates WHATSAPP_Ahmed Jazz_20260228_022517.md

2. Claude: /skill process_whatsapp_messages --all
   - Analyzes: "Hello! How are you?" → casual greeting
   - Contact not in address book → requires approval
   - Drafts: "Hi! I'm [Name]'s AI Assistant. How can I help?"
   - Creates plan + approval request

3. Human: Approves, moves to /Approved/

4. Executor:
   - Detects approval
   - WhatsApp auto-send not yet implemented (needs WhatsApp Business API)
   - Creates draft response file in /Done/ for manual copy-paste
   - Logs action as "draft_created"

5. Human manually sends via WhatsApp (copies draft)
```

---

## Monitoring & Maintenance

### Daily Checks

1. **Dashboard Review**:
   - Open `AI_Employee_Vault/Dashboard.md`
   - Check: Pending Tasks should be low (<10)
   - Check: System Health - all components green?

2. **Pending Approvals**:
   ```bash
   python utils/approval_manager.py --list-pending
   ```
   - Review all pending items
   - Approve or reject within 24 hours (urgent) or 72 hours (normal)

3. **Watcher Status**:
   ```bash
   ps aux | grep watcher
   ```
   - Ensure gmail_watcher.py, whatsapp_watcher.py running (or use systemd)

4. **Log Review** (optional):
   ```bash
   tail -f AI_Employee_Vault/Logs/$(date +%Y-%m-%d).json
   ```
   - Look for errors: `"result": "error"` or exceptions
   - Verify actions are being logged

### Weekly Tasks

- **Generate Weekly Briefing**:
  ```
  /skill generate_weekly_briefing
  ```
  - Creates `Briefings/YYYY-Www-CEO-Briefing.md`
  - Reviews completed tasks vs Business_Goals.md
  - Highlights metrics, anomalies, recommendations

- **Archive Old Logs**:
  - Move logs older than 30 days to `Logs/Archive/`
  - Compress: `gzip Logs/2026-01-*.json`
  - Optional: Encrypt with GPG if containing PII

- **Clean /Done/** (optional):
  - Archive to external storage after 90 days
  - Keep index for searchability

### Monthly Tasks

- **Rotate credentials**: Generate new `credentials.json` from Google Cloud Console
- **Test backup/restore**: Verify vault can be restored from backup
- **Audit logs**: Search for any unauthorized actions
- **Update dependencies**: `pip install -r requirements.txt --upgrade`
- **Review Handbook**: Update thresholds, add new patterns observed

---

## File Organization

```
/AI_Employee_Vault/
├── Dashboard.md              # Real-time status
├── Company_Handbook.md       # This file
├── Business_Goals.md         # Objectives
├── Inbox/                    # Drop zone for manual items
├── Needs_Action/             # Items requiring processing
│   ├── EMAIL_*.md
│   ├── WHATSAPP_*.md
│   └── FILE_*.md
├── Plans/                    # Active execution plans
│   └── PLAN_*.md
├── Pending_Approval/         # Awaiting human review
├── Approved/                 # Human-approved actions
├── Rejected/                 # Denied actions (logged)
├── Done/                     # Completed tasks
│   ├── EMAIL_*.md
│   ├── WHATSAPP_*.md
│   └── PLAN_*.md
├── Logs/                     # Audit trail
│   └── YYYY-MM-DD.json
├── Briefings/                # Weekly CEO reports
└── Resources/               # Reference materials
```

---

## Approval Thresholds

### Auto-Approve (No Human Review)
- Email replies to known contacts (in address book)
- File organization and categorization
- Reading data from external sources
- Creating draft responses

### Always Require Approval
- Sending emails to new recipients
- Any financial transactions (payments, transfers)
- Posting to social media
- Accessing new services for the first time
- Deleting data from vault
- Changing system configuration

### Context-Dependent
- Email replies to existing contacts but with unusual content → Review
- WhatsApp messages with sensitive keywords → Flag for approval
- Any action involving legal or contractual commitments → Always approve

---

## Security Protocols

### Credential Management
```bash
# NEVER do this:
# API_KEY = "abc123"  # ❌ Hard-coded

# ALWAYS do this:
# import os
# api_key = os.getenv('API_KEY')  # ✅ Environment variable
```

### Sensitive Data Handling
- Mask sensitive information in logs: `card ending in ****1234`
- Never log full API responses containing PII
- Encrypt logs at rest if containing financial data
- Delete temporary files after processing

### Access Control
- All approval files must be manually moved (no automated approval)
- Only human can move files between `/Pending_Approval/` and `/Approved/`
- AI can only read from vault, not modify approval status directly

---

## Quality Standards

### For All Outputs
- ✅ Spelling and grammar checked
- ✅ All placeholders filled
- ✅ Links and references valid
- ✅ Formatting consistent
- ✅ No TODO or FIXME comments in final deliverables

### Error Handling
- Log exceptions with stack traces
- Notify human via Dashboard update
- Retry transient failures (max 3 attempts)
- Quarantine corrupted files to `/Inbox/`

---

## Monitoring & Maintenance

### Daily
- Check Dashboard.md for status
- Review `/Pending_Approval/` folder
- Verify all watchers are running

### Weekly
- Generate Business Handover briefing
- Review `/Logs/` for anomalies
- Clean up `/Done/` folder (archive old items)
- Update `Business_Goals.md`

### Monthly
- Audit all API credentials
- Test backup and restore procedures
- Review and update this handbook
- Verify MCP server health

---

## Escalation Procedures

### When AI Employee Should Pause
1. **API quota exceeded**: Stop external calls, notify human
2. **Credential failure**: Alert immediately, don't retry
3. **Repeated approval rejections**: Flag for rule review
4. **Unusual patterns detected**: Halt and request review
5. **System resource limits**: Pause non-critical tasks

### Human Notification Methods
- Update Dashboard.md prominently
- Create ALERT file in `/Needs_Action/`
- Send email to human (if email MCP available)
- Log to `/Logs/ALERT_*.json`

---

## Continuous Improvement

### Feedback Loop
- Document misunderstandings in `/Resources/Misunderstandings.md`
- Update rules in this handbook when patterns emerge
- Refine Plan templates based on what works
- Share learning in weekly briefings

### A/B Testing
When trying new approaches:
1. Create experimental plan
2. Track success metrics
3. Compare against baseline
4. Adopt if improvement >20%

---

## Definitions

| Term | Meaning |
|------|---------|
| **HITL** | Human-in-the-Loop: Human approval required before sensitive actions |
| **Watcher** | Background script monitoring external sources (Gmail, WhatsApp, filesystem) |
| **MCP** | Model Context Protocol: External action servers (email, web, etc.) |
| **Ralph Wiggum Loop** | Persistent execution via stop-hook until tasks complete |
| **Vault** | The Obsidian knowledge base (this folder) containing all state |
| **Orchestrator** | Master process (Bronze) or Claude Code (Silver) coordinating components |
| **Approval Threshold** | Rules determining when human approval is required |
| **Plan** | Execution plan (`PLAN_*.md`) created by Claude with steps and approval status |
| **Executor** | Daemon that watches `/Approved/` and executes approved actions |
| **Silver Tier** | External integrations + HITL + Agent Skills (current stage) |
| **Gold Tier** | Database persistence + multi-agent + Odoo + advanced monitoring |

---

## Silver Tier Addendum

This section supplements the core principles with Silver-specific implementations.

### New Components Introduced (Silver)

| Component | Purpose | Location |
|-----------|---------|----------|
| Gmail Watcher | Poll Gmail API, create EMAIL_*.md | `watchers/gmail_watcher.py` |
| WhatsApp Watcher | Monitor WhatsApp Web via Playwright | `watchers/whatsapp_watcher.py` |
| Email Sender | Send emails via Gmail API | `utils/send_email_direct.py` |
| Approval Manager | CLI tool for managing approvals | `utils/approval_manager.py` |
| Approved Executor | Auto-execute approved actions | `watchers/approved_executor.py` |
| LinkedIn Poster | Post to LinkedIn via Playwright | `utils/linkedin_poster.py` |
| Scheduler | Cron-based task automation | `scheduler/scheduler.py` |
| Agent Skills | Claude Code capabilities | `.claude/skills/` |
| Process Email | Handle incoming emails | `process_email_requests/` |
| Process WhatsApp | Handle WhatsApp messages | `process_whatsapp_messages/` |
| Approval Workflow | Manage HITL queue | `approval_workflow/` |
| LinkedIn Poster Skill | LinkedIn posting | `linkedin_auto_poster/` |
| Weekly Briefing | CEO reports | `generate_weekly_briefing/` |
| Browsing Skill | Web automation | `browsing-with-playwright/` |

### Silver Tier Security Additions

**Credential Management** (see also §159):
- OAuth tokens stored in `token.json` (refresh automatically)
- Client secrets in `credentials.json` (rotate quarterly)
- Never commit these files (.gitignore enforced)

**Session Management**:
- Browser sessions stored in `linkedin_session/`, `session/` (persistent login)
- These folders contain cookies and localStorage - treat as credentials
- If device compromised, delete these folders and re-authenticate

**Approval Chain of Custody**:
Every approval request must include:
- `source_file`: Original action item
- `plan_file`: Execution plan (if created)
- `action:` type and parameters
- `requires_approval: true`
- `created:` timestamp
- `reason:` human-readable justification

When human approves/rejects:
- Move file to `/Approved/` or `/Rejected/`
- Consider adding `approved_by:` field (future enhancement)
- Executor logs final action with link to approval file

---

## Quality Standards (Silver Tier)

In addition to Bronze standards (§181-195), Silver Tier must meet:

### For Email Responses
- ✅ Use proper email threading (`thread_id` included)
- ✅ Include original message snippet for context
- ✅ Professional tone with correct recipient name
- ✅ No broken links or malformed markdown
- ✅ Test with dry-run before first send

### For WhatsApp Messages
- ✅ Keep under 300 characters
- ✅ Use sender's name if known
- ✅ Acknowledge urgency appropriately
- ✅ Include call to action
- ✅ Don't auto-respond to "delete" or "stop" commands

### For LinkedIn Posts
- ✅ Preview in dry-run mode first
- ✅ Check for broken formatting
- ✅ Verify hashtags are relevant
- ✅ Ensure no confidential information
- ✅ Schedule for optimal engagement time

---

## Compliance Notes (Silver Tier)

With external integrations come additional compliance considerations:

### Data Privacy (GDPR, CCPA)
- Email addresses are personal data - protect them
- Logs may contain message content - encrypt if storing >30 days
- Provide mechanism to delete user data on request
- Document lawful basis for processing (legitimate interest, consent)

### Terms of Service Compliance
- **Gmail**: Sending limit 500/day (free), 2000/day (workspace)
- **WhatsApp**: Automation may violate ToS - use at own risk, consider Business API
- **LinkedIn**: Automation can trigger account restriction - use cautiously, human review required

### Financial Compliance (PCI-DSS)
- Never store full credit card numbers in vault
- If processing payments, use tokenization (Stripe, PayPal)
- Keep audit logs for 7 years minimum for financial actions

---

## Incident Response (Silver Tier Updates)

### New Incident Types

1. **Credential Compromise**:
   - `credentials.json` or `token.json` leaked
   - Immediately revoke OAuth tokens in Google Account → Security → Third-party access
   - Generate new credentials.json from Google Cloud Console
   - Delete `token.json` to force re-auth
   - Check logs for unauthorized API calls
   - Rotate all other service credentials as precaution

2. **Approval Bypass**:
   - AI sent email without human approval when required
   - Stop all watchers immediately
   - Review `/Logs/` to identify scope (which recipients, what content)
   - Fix root cause (bug in skill logic?)
   - Consider rolling back to last known-good commit
   - Add additional approval gate if needed

3. **Rate Limit Exceeded**:
   - Gmail API returns 429 Too Many Requests
   - Watcher will auto-backoff (exponential)
   - Human should be notified via Dashboard
   - Reduce check interval or batch processing

4. **Session Expiration** (WhatsApp/LinkedIn):
   - Browser session fails to load
   - Delete `session/` or `linkedin_session/` folder
   - Re-run watcher to scan QR code fresh
   - Update scheduler to restart session monthly

---

## Resources (Silver Tier)

- **Gmail API**: https://developers.google.com/gmail/api
- **WhatsApp Web**: https://web.whatsapp.com (no official API - automation at own risk)
- **LinkedIn**: https://docs.microsoft.com/linkedin/ (no official automation API)
- **Playwright**: https://playwright.dev/python/docs/intro
- **Claude Code Skills**: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- **OAuth 2.0**: https://developers.google.com/identity/protocols/oauth2

---

*Handbook Version: 1.1-Silver*
*Last Updated: 2026-02-28*
*Next Review: 2026-03-07 (weekly during Silver)*
*Tier: Silver*

## Resources

- [Hackathon Documentation](../Personal\ AI\ Employee\ Hackathon\ 0\ Building\ Autonomous\ FTEs\ in\ 2026.md)
- [Claude Code Documentation](https://agentfactory.panaversity.org/docs/AI-Tool-Landscape/claude-code-features-and-workflows)
- [Obsidian Help](help.obsidian.md/)
- [MCP Specification](https://modelcontextprotocol.io/)

---

*Handbook Version: 1.0-Bronze*
*Last Updated: 2026-02-24*
*Next Review: 2026-03-01*
