# Process WhatsApp Messages Skill

**Silver Tier Agent Skill** - Processes incoming WHATSAPP_* action items from WhatsApp watcher, drafts appropriate responses, and manages WhatsApp communications.

---

## Description

This skill handles WhatsApp messages detected by the WhatsApp watcher. It analyzes message content, determines appropriate responses, and either drafts replies or creates approval requests for sensitive messages.

**Key differences from email processing:**
- WhatsApp is more immediate/urgent
- Messages are shorter (concise responses needed)
- Tone should be more casual but professional
- Emoji use may be appropriate (per Company_Handbook)
- May require faster response time (1 hour vs 24h)

---

## Usage

```
/skill process_whatsapp_messages [--all] [--item FILE] [--draft-only] [--dry-run]
```

---

## Behavior

### Process All Messages (`--all`)

Scans `/Needs_Action/` for all `WHATSAPP_*.md` files and processes them.

**Example:**
```
/skill process_whatsapp_messages --all
```

**Process:**
1. Find all WHATSAPP_*.md files
2. For each message/chat:
   - Read content and metadata (contact, priority, message count)
   - Analyze tone and urgency
   - Check if contact is known
   - Determine response strategy
   - Create execution plan in `/Plans/`
   - Draft response or create approval request
   - Log actions and update Dashboard
   - Move to `/Done/`

---

### Process Single Message (`--item FILE`)

Process a specific WHATSAPP_*.md file.

**Example:**
```
/skill process_whatsapp_messages --item WHATSAPP_john_doe_20260224_010000.md
```

---

### Draft Only (`--draft-only`)

Create response drafts but don't send or request approval. Useful for review.

**Example:**
```
/skill process_whatsapp_messages --all --draft-only
```

Creates response drafts in `/Plans/` for human to review and manually send via WhatsApp.

---

### Dry Run (`--dry-run`)

Preview actions without executing.

**Example:**
```
/skill process_whatsapp_messages --all --dry-run
```

---

## Message Analysis

### Priority Detection

The skill reads `priority` field from action item (set by watcher):
- **high**: Contains urgent keywords (urgent, asap, emergency, help)
- **medium**: Normal message

Additionally analyzes:
- Message content for urgency indicators
- Time of day (after hours → higher priority)
- Sender importance (known client vs unknown)

---

### Contact Classification

**Known Contacts:**
- Previously messaged (exists in `/Done/` tasks)
- Listed in `Company_Handbook.md` address book
- Recognized as client or partner

**Unknown Contacts:**
- First-time message
- Number not in any previous record
- Requires approval for sensitive responses

---

### Message Type Classification

#### 1. **Urgent Request**
**Trigger:** Keywords: urgent, asap, emergency, help, now, critical
**Priority:** High
**Action:** Create immediate approval request (HITL)
**Response window:** < 1 hour

---

#### 2. **Client Inquiry**
**Trigger:** Questions about services, pricing, availability
**Action:** Provide information, link to resources, suggest call
**Approval:** New contacts → approval required

---

#### 3. **Project Update**
**Trigger:** Status updates, coordination questions
**Action:** Acknowledge, provide details, next steps
**Approval:** Usually not needed if known contact

---

#### 4. **Personal/Casual**
**Trigger:** Greetings, social messages (hi, how are you)
**Action:** Friendly acknowledgment, brief response
**Approval:** Never needed

---

#### 5. **Spam/Promotional**
**Trigger:** Marketing messages, bulk sends, suspicious links
**Action:** Ignore/block, no response
**Approval:** N/A

---

## Response Templates

Per Company_Handbook (lines 55-59): WhatsApp style should be:
- Brief and clear
- Emojis sparingly (only if client uses first)
- Acknowledge urgent within 1 hour

### Template: Client Inquiry

```
Hi [Name]! 👋

Thanks for reaching out regarding [topic].

[Answer question / provide info]

Would you like to schedule a call to discuss further?
You can book here: [calendar link]

Best,
[Your Name]
```

---

### Template: Urgent Request

```
[Name], I've received your urgent message.

[Quick acknowledgment of issue]

I'm looking into this now and will update you within [timeframe].

If this is critical, please call me at [phone].

—
[Your Name]
```

---

### Template: Project Coordination

```
Got it, [Name]! ✅

[Status update / answer]

Next steps: [next action]

Let me know if you need anything else!

—
[Your Name]
```

---

### Template: New Contact (approval required)

The skill **does not** auto-respond to new contacts. Instead:

1. Creates approval request in `/Pending_Approval/`:

```
---
type: approval_request
action: whatsapp_reply
contact: New Client
phone: +1234567890
message_preview: "Hi, I'm interested in your services..."
requires_approval: true
created: 2026-02-24T01:05:00Z
---

# Approval Request: WhatsApp Reply

**Contact**: New Client (first-time message)
**Phone**: +1234567890
**Original Message**:
> Hi, I'm interested in your services. Can you tell me more?

**Proposed Response**:
> Hi there! Thanks for reaching out. I'd be happy to tell you more about our services. Would you like to schedule a brief call this week? You can book here: [link]

**Reason for Approval**:
- ✗ New contact (not in address book)
- ✓ Business inquiry (appropriate to respond)

**To Approve**:
Move this file to `/Approved/` → Response will be sent via WhatsApp MCP

**To Reject**:
Move to `/Rejected/` → No response sent
```

2. If approved, orchestrator sends via WhatsApp MCP (when available)
3. For now, human manually sends from draft

---

## Plan Template

```markdown
---
plan_id: PLAN_WHATSAPP_<timestamp>
created: 2026-02-24T01:05:00Z
source: WHATSAPP_john_doe_20260224_010000.md
status: in_progress
---

# Execution Plan: Process WhatsApp Messages

**Contact**: John Doe
**Message Count**: 3
**Priority**: High (urgent keywords detected)
**Type**: Urgent Request

## Steps

- [x] Load message content and analyze
- [x] Check sender → KNOWN contact (previous interactions)
- [ ] Draft urgent acknowledgment response
- [ ] Create approval request (required for urgent messages)
- [ ] Log action to /Logs/
- [ ] Update Dashboard
- [ ] Mark source as processed (move to /Done/)

## Approval Required
YES - Urgent messages require immediate human review

## Estimated Completion
5-10 minutes

---
```

---

## Integration with WhatsApp MCP

When WhatsApp MCP is available (Silver/Gold), this skill can use:

- `whatsapp_send_message` - Send text response
- `whatsapp_send_media` - Send images/documents
- `whatsapp_mark_read` - Mark message as read

For now (Bronze/Silver early), it creates drafts/approval requests that humans execute manually.

---

## Dashboard Updates

```markdown
## Recent WhatsApp Activity
- ✅ Urgent request from John Doe - approved & responded (2026-02-24 01:30)
- ⏳ New client inquiry - awaiting approval (2026-02-24 01:15)
- 📱 5 messages processed today

## Pending Actions
- 1 WhatsApp approval needed (URGENT)
```

---

## Logging

```json
{
  "timestamp": "2026-02-24T01:05:00Z",
  "action_type": "whatsapp_processed",
  "source_file": "WHATSAPP_john_doe_20260224_010000.md",
  "contact": "John Doe",
  "message_count": 3,
  "priority": "high",
  "response_type": "acknowledgment",
  "approval_required": true,
  "approval_status": "pending",
  "result": "approval_request_created"
}
```

---

## Error Handling

- **Invalid action item** (missing contact/messages) → Log error, move to Done with error
- **WhatsApp MCP unavailable** → Create approval request for manual send
- **High volume** (50+ messages) → Flag for review, don't auto-respond to all
- **Suspicious content** → Block response, create alert

---

## Configuration (in Company_Handbook.md)

```yaml
whatsapp_processing:
  auto_approve_contacts: []  # Whitelist (phone numbers or names)
  urgent_response_time: "1h"  # Must respond within 1 hour
  max_messages_per_contact: 5  # Rate limit to avoid spam
  emoji_use: true  # Allow emojis in responses
  signature: true  # Include signature
  working_hours: "09:00-17:00"  # Only auto-respond during these hours
```

---

## Testing

### Test 1: Dry run
```
/skill process_whatsapp_messages --all --dry-run
```

### Test 2: Process single message
```
/skill process_whatsapp_messages --item WHATSAPP_test_contact_20260224_010000.md
```

### Test 3: Draft only (review before sending)
```
/skill process_whatsapp_messages --all --draft-only
```
Check `/Plans/` for response drafts.

---

## Security & Privacy

- **Never** auto-respond to unknown contacts (approval required)
- **Never** share sensitive information via WhatsApp
- **Validate** contact identity before sharing business details
- **Log** all outgoing responses for audit
- **Rate limit** to avoid being flagged as spam

---

## Dependencies

- **WhatsApp Watcher** - Creates WHATSAPP_*.md action items
- **Approval Workflow Skill** - For HITL on sensitive responses
- **Company_Handbook** - For communication standards and rules
- (Future) WhatsApp MCP - For automated sending

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No messages processed | Check `/Needs_Action/` for WHATSAPP_*.md files |
| All messages flagged urgent | Check keyword detection logic |
| Approval requests not created | Verify `/Pending_Approval/` exists |
| Responses too formal | Adjust templates to be more casual (per Handbook) |
| Emoji not appearing | Check `emoji_use` config in Handbook |

---

## Best Practices

1. **Keep responses concise** (WhatsApp is for quick messages)
2. **Use emojis judiciously** (only if client uses them)
3. **Acknowledge within 1 hour** for high priority (Handbook line 58)
4. **Always get approval** for new contacts
5. **Log everything** for audit trail
6. **Move processed items** to `/Done/` promptly

---

## Future Enhancements (Gold)

- Real-time WhatsApp MCP sending (fully automated)
- Quick reply templates with variables
- Message threading and context tracking
- Auto-translation for international clients
- Sentiment analysis for tone adjustment
- Integration with CRM to show client history
- Voice message transcription and response

---

## References

- Company_Handbook.md lines 55-59 (WhatsApp style)
- Company_Handbook.md lines 133-152 (Approval thresholds)
- WhatsApp Watcher - Creates action items
- Approval Workflow Skill - HITL system
- Hackathon: Silver Tier - All functionality as Agent Skills

---

*Skill: process_whatsapp_messages*
*Version: 1.0-Silver*
*Last Updated: 2026-02-24*
