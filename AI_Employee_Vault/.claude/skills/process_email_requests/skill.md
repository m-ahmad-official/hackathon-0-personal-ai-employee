# Process Email Requests Skill

**Silver Tier Agent Skill** - Processes incoming EMAIL_* action items from Gmail watcher, determines appropriate responses, and executes email operations via Email MCP server.

---

## Description

This skill implements the complete email handling workflow:

1. **Read** EMAIL_*.md files from `/Needs_Action/`
2. **Analyze** content and sender (new vs known contact)
3. **Plan** appropriate response (reply, draft, forward, archive)
4. **Execute** via Email MCP server (send_email, create_draft, etc.)
5. **Log** all actions and update Dashboard
6. **Move** completed items to `/Done/`

It follows the Company_Handbook's Task Processing Workflow (lines 69-101) and respects the Approval Thresholds (lines 133-152).

---

## Usage

```
/skill process_email_requests [--all] [--item FILE] [--dry-run] [--force]
```

---

## Behavior

### Process All Email Items (`--all`)

Scans `/Needs_Action/` for all `EMAIL_*.md` files and processes them.

**Example:**
```
/skill process_email_requests --all
```

**Process:**
1. Find all EMAIL_*.md files
2. For each:
   - Read metadata (from, subject, priority)
   - Load full email if needed (via Email MCP `read_email`)
   - Consult `Company_Handbook.md` for rules
   - Check `Business_Goals.md` for context
   - Determine response strategy
   - Create execution plan in `/Plans/`
   - Execute plan with MCP tools
   - Handle approval if needed
   - Move to `/Done/` and log

---

### Process Single Item (`--item FILE`)

Process a specific EMAIL_*.md file.

**Example:**
```
/skill process_email_requests --item EMAIL_client_inquiry_20260224_010000.md
```

---

### Dry Run (`--dry-run`)

Preview what would be done without making changes.

**Example:**
```
/skill process_email_requests --all --dry-run
```

Shows:
- Which emails would be processed
- What actions would be taken (reply, draft, forward)
- Whether approval would be requested
- Plan that would be created

---

### Force (`--force`)

Override certain safety checks:
- Send to new contacts without approval (USE WITH CAUTION)
- Skip duplicate detection
- Bypass rate limits

**Example:**
```
/skill process_email_requests --all --force
```

---

## Decision Logic

### Known vs Unknown Contacts

The skill maintains an implicit "address book" based on:
1. Previous emails in `/Done/` from that sender
2. Address book in `Company_Handbook.md` (if defined)
3. Contact list from Email MCP (if implemented)

**Logic:**
```
IF sender in known_contacts:
    → Can auto-approve reply (if content normal)
ELSE:
    → Must create approval request in /Pending_Approval/
```

---

### Response Strategies by Email Type

#### 1. Client Inquiry (Sales)
**Trigger:** Subject contains "inquiry", "interest", "question about"
**Action:** Send detailed reply with:
- Thank you acknowledgment
- Brief introduction
- Link to resources/proposal
- Call to action (schedule call)

**Approval:** If new contact → approval required

---

#### 2. Invoice/Payment
**Trigger:** Subject contains "invoice", "payment", "billing"
**Action:**
- Acknowledge receipt
- Provide payment link/info
- Set expectations for follow-up

**Approval:** Always requires approval (financial context)

---

#### 3. Support Request
**Trigger:** Keywords: "help", "issue", "problem", "broken"
**Action:**
- Acknowledge and prioritize
- Provide ticket/reference number
- Set expectation for response time
- Escalate if urgent

**Approval:** Not required (but flag if urgent)

---

#### 4. General Business Email
**Trigger:** Any other business-related email
**Action:**
- Polite acknowledgment
- Answer questions
- Forward to relevant person if not in domain

**Approval:** If sender unknown → approval; else auto-approve

---

#### 5. Newsletter/Promotional
**Trigger:** Unsubscribe link, promotional content, marketing
**Action:**
- Archive/delete
- Mark as read
- Possibly unsubscribe via Gmail

**Approval:** Never send replies (archive only)

---

## Plan Template

For each email, a plan is created in `/Plans/`:

```markdown
---
plan_id: PLAN_EMAIL_<timestamp>
created: 2026-02-24T01:05:00Z
source: EMAIL_client_abc123_20260224_010000.md
status: in_progress
---

# Execution Plan: Process Email

**From**: client@example.com
**Subject**: Inquiry about services
**Type**: Client Inquiry
**Priority**: High

## Steps

- [x] Read email metadata and load full content
- [x] Check sender against known contacts → NEW CONTACT
- [ ] Draft reply acknowledging inquiry
- [ ] Include link to proposal document
- [ ] Add call to action: "Schedule a call"
- [ ] Create approval request in /Pending_Approval/
- [ ] Log action and update Dashboard
- [ ] Move source to /Done/ when complete

## Approval Required
YES - New contact requires approval before sending

## Estimated Time
2-3 minutes

---
```

---

## Approval Workflow

If approval required:

1. **Create approval request** in `/Pending_Approval/`:
   ```
   EMAIL_approval_<sender>_<timestamp>.md
   ```

   Content:
   ```markdown
   ---
   type: approval_request
   action: send_email
   to: client@example.com
   subject: Re: Inquiry about services
   requires_approval: true
   created: 2026-02-24T01:05:00Z
   ---

   # Approval Request: Send Email

   **Recipient**: client@example.com (NEW CONTACT)
   **Subject**: Re: Inquiry about services
   **Body Preview**:
   > Thank you for reaching out! ...

   ## Reason
   - ✗ New contact (not in address book)

   ## To Approve
   Move to /Approved/

   ## To Reject
   Move to /Rejected/
   ```

2. **Wait** for human to move file

3. **Orchestrator monitors `/Approved/`**:
   - When file appears, orchestrator reads it
   - Extracts email parameters (to, subject, body)
   - Calls Email MCP `send_email`
   - Logs result
   - Moves approval file and original email to `/Done/`

---

## Integration with Email MCP

This skill uses the Email MCP server tools:

- `read_email` - Fetch full email content by message ID
- `create_draft` - Create draft responses (for approval or review)
- `send_email` - Send final email (after approval)
- `reply_to_email` - Reply in thread (preferred)

---

## Dashboard Updates

After processing batch:

```markdown
## Recent Activity
- ✅ Processed 3 emails (2 sent, 1 archived)
- ⏳ 1 approval request pending (new contact)
- 📧 Total emails processed today: 5
```

---

## Logging

Every email operation logged to `/Logs/YYYY-MM-DD.json`:

```json
{
  "timestamp": "2026-02-24T01:05:00Z",
  "action_type": "email_processed",
  "source_file": "EMAIL_client_abc123_20260224_010000.md",
  "sender": "client@example.com",
  "response_type": "reply",
  "approval_required": true,
  "approval_status": "pending",
  "plan_created": "PLAN_EMAIL_...",
  "result": "pending_approval"
}
```

---

## Error Handling

### Invalid Email Item
- Missing required fields (from, subject) → Log error, move to `/Done/` with error flag

### MCP Server Unavailable
- Retry 3 times with exponential backoff
- If still failing → create approval request for manual handling
- Alert via Dashboard

### Sender Unrecognized
- Flag as new contact → approval required
- Add to `pending_approval` with clear label

---

## Configuration (Optional)

In `Company_Handbook.md`, add:

```yaml
email_processing:
  auto_approve_contacts: []  # List of emails that auto-approve
  default_response_time: "24h"  # SLA for responses
  require_approval_categories: ["new_contact", "financial", "legal"]
  max_length: 500  # Max auto-reply length (words)
  signature: "\n\n—\n[Your Name]\n[Title]\n[Phone]"
```

---

## Testing

### Test 1: Dry run
```
/skill process_email_requests --all --dry-run
```

### Test 2: Process one known contact
```
/skill process_email_requests --item EMAIL_known_sender_20260224_010000.md
```

### Test 3: Process batch
```
/skill process_email_requests --all
```

---

## Dependencies

- **Email MCP Server** - Must be running and configured in Claude Code
- **Gmail Watcher** - Creates EMAIL_*.md files
- **Approval Workflow Skill** - For HITL on sensitive emails

---

## Security Notes

- Never auto-send to unknown contacts (always approval)
- Don't include sensitive financial info in auto-replies
- Validate reply-to matches sender
- Log all actions for audit
- Rate limit: max 10 emails/minute to avoid Gmail limits

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No emails processed | Check `/Needs_Action/` for EMAIL_*.md files |
| MCP connection failed | Start email-mcp server: `node mcp-servers/email-mcp/index.js` |
| Approval not created | Verify `/Pending_Approval/` exists and is writable |
| Emails sent but not logged | Check `/Logs/` write permissions |
| Replies not threading | Use `reply_to_email` with threadId |

---

## Future Enhancements (Gold)

- Email categorization with ML
- Smart reply suggestions
- Template library with variables
- Integration with CRM
- Attachment handling
- Email threading and conversation tracking
- Sentiment analysis for prioritization

---

## References

- Company_Handbook.md - Task processing, approval thresholds
- Email MCP Server - Tools for email operations
- Gmail Watcher - Creates EMAIL_*.md action items
- Hackathon: Silver Tier - All AI functionality as Agent Skills

---

*Skill: process_email_requests*
*Version: 1.0-Silver*
*Last Updated: 2026-02-24*
