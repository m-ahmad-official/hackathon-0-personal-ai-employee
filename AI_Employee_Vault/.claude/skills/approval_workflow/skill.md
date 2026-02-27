# Approval Workflow Skill

**Silver Tier Agent Skill** - Manages Human-in-the-Loop (HITL) approval system for sensitive actions.

---

## Description

This skill implements the approval workflow defined in `Company_Handbook.md` (lines 27-30, 141-152, 438-468). It ensures that sensitive operations require explicit human approval before execution.

**Key Principle**: The AI can **request** approval but cannot **grant** it. Only human movement of files between `/Pending_Approval/` and `/Approved/` constitutes approval.

---

## Usage

```
/skill approval_workflow [--list-pending] [--approve FILE] [--reject FILE] [--auto-check]
```

---

## Behavior

### 1. List Pending Approvals (`--list-pending`)

Scans `/Pending_Approval/` folder and displays all items awaiting approval.

**Example:**
```
/skill approval_workflow --list-pending
```

**Output:**
```
⏳ Pending Approvals (3):

  1. PAYMENT_Client_A_20260224_010000.md
     Type: payment
     Amount: $500.00
     To: Client A (Bank: XXXX1234)
     Reason: Invoice #1234 payment
     Created: 2026-02-24 01:00

  2. EMAIL_new_contact_20260224_010500.md
     Type: send_email
     To: new.client@example.com
     Subject: Proposal
     Reason: New contact - requires approval
     Created: 2026-02-24 01:05

  3. SOCIAL_Post_20260224_011000.md
     Type: social_post
     Platform: LinkedIn
     Content: "Announcing our new product..."
     Created: 2026-02-24 01:10

To approve: Move file to /Approved/
To reject: Move file to /Rejected/
```

---

### 2. Check for New Approval Requests (`--auto-check`)

Automatically scans for new items and notifies human. Use in cron for periodic checks.

**Example:**
```
/skill approval_workflow --auto-check
```

**Behavior:**
1. Scan `/Pending_Approval/` for files modified in last 5 minutes
2. If new items found, update `Dashboard.md` with alert
3. Log check to `/Logs/`
4. Exit with code 0 (no items) or 1 (items found)

**Cron usage:**
```
*/5 * * * * cd /path/to/vault && /skill approval_workflow --auto-check
```

---

### Manual Approval/Reject (via file movement)

The skill **does not** auto-approve. Humans must manually move files:

```bash
# Approve
mv AI_Employee_Vault/Pending_Approval/PAYMENT_Client_A_*.md AI_Employee_Vault/Approved/

# Reject
mv AI_Employee_Vault/Pending_Approval/EMAIL_new_contact_*.md AI_Employee_Vault/Rejected/
```

---

### 3. Approval Types & Thresholds

Based on `Company_Handbook.md` lines 133-152, the skill recognizes:

#### Auto-Approve (No Human Needed)
- File operations (create, read, move within vault)
- Email replies to **known contacts** (in address book)
- Draft creation (not sending)

#### Always Require Approval
- Sending emails to **new contacts**
- **Any financial transaction** (payments, transfers)
- **Social media posting**
- Accessing new services for first time
- Deleting vault data
- Changing system configuration

#### Context-Dependent
- Unusual content in emails → flag for review
- WhatsApp messages with sensitive keywords → flag
- Legal/contractual commitments → always approve

---

## Workflow Integration

### Complete Approval Flow:

1. **AI detects sensitive action needed**
   - Reads item from `/Needs_Action/`
   - Creates plan
   - Determines approval required

2. **AI creates approval request file** in `/Pending_Approval/`

   Example file:
   ```markdown
   ---
   type: approval_request
   action: send_email
   to: new.client@example.com
   subject: Proposal Q1 2026
   requires_approval: true
   created: 2026-02-24T01:05:00Z
   expires: 2026-02-25T01:05:00Z
   status: pending
   ---

   # Approval Request: Send Email

   ## Details
   - **Recipient**: new.client@example.com
   - **Subject**: Proposal Q1 2026
   - **Body Preview**: "Dear [Client], please find attached..."

   ## Reason for Approval
   - ✗ New contact (not in address book)
   - ✗ Contains proposal attachment

   ## To Approve
   Move this file to `/Approved/`

   ## To Reject
   Move this file to `/Rejected/`
   ```

3. **Human reviews** and moves file

4. **Orchestrator watches `/Approved/`** and executes via MCP

5. **Orchestrator moves** processed request to `/Done/`

6. **Dashboard updated** with approval decision

---

## File Naming Convention

Approval request files follow pattern:

```
{ACTION_TYPE}_{TARGET}_{YYYYMMDD_HHMMSS}.md
```

Examples:
- `PAYMENT_Client_A_20260224_010000.md`
- `EMAIL_john.doe_20260224_011500.md`
- `SOCIAL_LinkedIn_20260224_012000.md`

---

## Dashboard Integration

The skill updates `Dashboard.md` with:

```
## Pending Approvals
- PAYMENT_Client_A - $500.00 (needs approval)
- EMAIL_new_contact - Send to new.client@example.com

## Recent Approvals
- ✅ EMAIL_known_contact - Approved (2026-02-24 01:30)
- ❌ PAYMENT_vendor - Rejected (2026-02-24 01:15)
```

---

## Audit Logging

All approval events are logged to `/Logs/YYYY-MM-DD.json`:

```json
{
  "timestamp": "2026-02-24T01:30:00Z",
  "action_type": "approval",
  "request_file": "EMAIL_john.doe_20260224_011500.md",
  "decision": "approved",
  "decided_by": "human",
  "action_taken": "email_sent_via_mcp",
  "result": "success"
}
```

---

## Error Handling

### Missing Folders
If `/Pending_Approval/`, `/Approved/`, or `/Rejected/` don't exist, create them.

### Stale Approvals
Requests older than 24 hours are flagged as `expired` and moved to `/Rejected/` with note.

### Concurrent Access
Use file locking when moving files to prevent race conditions (simple lock file approach).

---

## Dependencies

None beyond Claude Code's built-in file operations. This is pure file-based workflow.

---

## Integration with Other Skills

This skill works with:
- `process_email_requests` - Creates approval requests for emails to new contacts
- `process_whatsapp_messages` - Creates approval for sensitive WhatsApp responses
- `linkedin_auto_poster` - Requires approval before posting
- `orchestrator.py` - Monitors `/Approved/` and triggers MCP actions

---

## Configuration

No configuration needed. Uses default paths:

```
/AI_Employee_Vault/
├── Pending_Approval/
├── Approved/
├── Rejected/
└── Dashboard.md
```

---

## Testing

### Test 1: Create approval request manually

```bash
cat > AI_Employee_Vault/Pending_Approval/TEST_approval_$(date +%s).md << 'EOF'
---
type: approval_request
action: test_action
created: 2026-02-24T01:00:00Z
status: pending
---

# Test Approval Request

This is a test. Move to /Approved/ to approve, /Rejected/ to reject.
EOF

/skill approval_workflow --list-pending
```

### Test 2: Approve it

```bash
mv AI_Employee_Vault/Pending_Approval/TEST_*.md AI_Employee_Vault/Approved/
/skill approval_workflow --list-pending  # Should show empty
```

---

## Security Notes

⚠️ **Critical**: The `/Approved/` folder is the **only** trigger for external actions.

- Only human can move files to `/Approved/`
- AI must **never** move its own requests to Approved
- Orchestrator should verify file source before executing
- All approval decisions are audited in logs

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Skill not loading | Ensure directory: `AI_Employee_Vault/.claude/skills/approval_workflow/` with `skill.md` |
| No approvals listed | Check `/Pending_Approval/` exists and has `.md` files |
| Stale requests not expiring | Check system clock, log file permissions |
| Dashboard not updating | Run `/skill update_dashboard` |

---

## Future Enhancements (Gold Tier)

- Email notifications for new approvals
- Mobile approval via WhatsApp command
- Multi-level approval (requires 2 approvers)
- Time-based auto-approval for low-risk items
- Approval statistics dashboard

---

## References

- Company_Handbook.md (lines 27-30, 141-152, 438-468)
- Hackathon: Silver Tier Requirement #6
- MCP Server integration for actual actions

---

*Skill: approval_workflow*
*Version: 1.0-Silver*
*Last Updated: 2026-02-24*
