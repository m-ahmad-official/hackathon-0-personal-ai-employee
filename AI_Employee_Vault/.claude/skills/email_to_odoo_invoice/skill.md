# Email to Odoo Invoice

**Gold Tier Phase 4** - Automatically creates Odoo invoices from email requests.

---

## Overview

This skill processes incoming `EMAIL_*.md` action items, detects invoice creation requests, and automatically generates invoices in Odoo. It bridges email communication with accounting automation.

**Workflow:**
1. Detect invoice intent in email subject/body
2. Extract: customer email, amount, description, due date
3. Find or create customer in Odoo
4. Create draft invoice (and optionally post)
5. Send confirmation email with invoice details
6. Log all actions and update Dashboard

---

## Usage

```
/skill email_to_odoo_invoice [--all] [--item FILE] [--dry-run] [--auto-post]
```

**Parameters:**
- `--all`: Process all EMAIL_*.md files in `/Needs_Action/`
- `--item FILE`: Process specific email item only
- `--dry-run`: Preview without making changes
- `--auto-post`: Automatically post invoices after creation (default: draft only)

---

## Behavior

### Processing Mode (`--all`)

Scans `/Needs_Action/` for all `EMAIL_*.md` files and processes them sequentially.

**Example:**
```
/skill email_to_odoo_invoice --all --auto-post
```

**Process:**
1. Read each EMAIL_*.md file
2. Analyze content to detect invoice request
3. Extract invoice details (amount, description, customer)
4. Determine if approval required:
   - NEW contact → approval needed
   - Known contact → auto-approve if amount < threshold (configurable)
5. Create execution plan in `/Plans/`
6. If approval needed → create `/Pending_Approval/` request
7. If approved (or auto) → create Odoo invoice
8. Send confirmation email
9. Update dashboard metrics
10. Move completed files to `/Done/`

---

### Single Item (`--item FILE`)

Process a specific email file.

**Example:**
```
/skill email_to_odoo_invoice --item EMAIL_invoice_request_20260309_010000.md --dry-run
```

---

### Dry Run (`--dry-run`)

Preview actions without executing:
- What invoice details would be extracted
- What Odoo operations would be performed
- Whether approval would be required
- Plan that would be created

---

## Invoice Detection Logic

The skill uses multi-signal detection to identify invoice requests:

**Primary Triggers:**
- Subject contains: "invoice", "billing", "payment request", "pay now"
- Body contains: "send invoice", "create invoice", "bill me", "how much"
- Amount mentioned with dollar sign: "$500", "500 USD"

**Secondary Signals:**
- Customer explicitly states they're ready to proceed
- Follow-up to proposal/quote
- Payment terms requested

**Exclusions (not invoice requests):**
- "Where is my invoice?" (status inquiry)
- "Dispute invoice" (support ticket)
- "Pay invoice" (payment, not creation)

---

## Data Extraction

From email body, extract:

1. **Amount** - First occurrence of $X or "X USD"
   - Example: "$500" → 500.00
   - Format: Decimal number with optional currency

2. **Customer Email** - From email `from` field (primary) or body "for [email]"
   - Prefer `from:` field as recipient
   - If body says "send to client@example.com", use that as invoice recipient

3. **Description/Item** - From subject or first sentence
   - Example: "Web development services" → "Web Development Services"
   - Default: Subject line with "Invoice" removed

4. **Due Date** - Relative (e.g., "net 30", "due in 2 weeks") or absolute ("March 15")
   - Parse: "net 30" → today + 30 days
   - Parse: "March 15, 2026" → 2026-03-15
   - Default: today + 30 days

5. **Quantity** - Default 1 (unless "10 hours", "5 units" detected)

---

## Odoo Integration

### Customer Lookup/Creud

**Step 1: Search by email**
```python
# Use odoo-mcp tool: search_customers
results = search_customers(email="client@example.com")
if results:
    customer = results[0]
else:
    # Create new customer
    # - name: extract from email or use "Client" + email prefix
    # - email: from email
    # - company_type: 'person' (default)
    # - customer_rank: 1
```

**Step 2: Product Auto-Lookup**
```python
# Try to find existing product by description
product_id = find_product_by_name(description)
if not found:
    # Create service product on-the-fly
    product_id = create_product(
        name=description,
        type='service',
        list_price=amount,
        tax_ids=[]  # no tax by default
    )
```

---

### Invoice Creation

**Tool:** `create_invoice` from odoo-mcp

**Parameters:**
```python
{
  "customer_email": "client@example.com",
  "customer_name": "Client Name (optional)",
  "items": [
    {
      "name": "Web Development Services",  # extracted description
      "quantity": 1,  # or extracted quantity
      "price": 500.00  # extracted amount
    }
  ],
  "due_date": "2026-04-15"  # extracted or default (+30 days)
}
```

**On Success:**
- Get invoice_id, invoice_number, amount_total
- If `--auto-post` flag: call `post_invoice(invoice_id)`
- Log to audit with target=invoice_id

---

## Cross-Domain: Email Confirmation

After invoice creation, send confirmation email:

**Tool:** `send_email` (from Email MCP)

**Email Content:**
```
Subject: Invoice [INVOICE_NUMBER] Created

Dear [Customer Name],

Your invoice has been created:

Invoice Number: INV/2026/001
Amount: $500.00
Due Date: April 15, 2026

[PDF attachment if Odoo can generate]

Payment instructions:
[Bank details or payment link]

Questions? Reply to this email.

Thank you!
```

**Approval:** Sending email may require approval if new contact.

---

## Decision Logic

### When is Approval Required?

| Condition | Threshold | Approval Required |
|-----------|-----------|-------------------|
| New contact (never seen before) | Any amount | ✅ YES |
| Known contact | Amount > $1000 | ✅ YES |
| Known contact | Amount ≤ $1000 | ❌ No |
| Email from non-business domain (gmail, yahoo) | Any amount | ✅ YES |

**Configurable:** Modify `company_handbook` rules or skill parameters.

---

### Amount Extraction Order

1. Look for `$X.XX` pattern (e.g., "$500", "$1,250.50")
2. Look for `X USD` pattern
3. Look for "amount of X" phrasing
4. **If not found:** Cannot create invoice → mark for manual review

---

## Plan Template

For each email processed, a plan is created in `/Plans/`:

```markdown
---
plan_id: PLAN_EMAIL_INVOICE_<timestamp>
created: 2026-03-09T01:30:00Z
source: EMAIL_invoice_request_20260309_010000.md
status: in_progress
---

# Execution Plan: Create Odoo Invoice from Email

**From**: client@example.com
**Subject**: Please send invoice for $500
**Detected Amount**: $500.00
**Customer**: New contact

## Steps

- [x] Read email content and metadata
- [x] Detect invoice intent → CONFIRMED
- [x] Extract: amount=$500, description="Web Development", due_date=2026-04-08
- [ ] Search Odoo for existing customer
- [ ] Customer not found → CREATE NEW
- [ ] Create product (service) if not exists
- [ ] Create draft invoice in Odoo
- [ ] Post invoice (auto-post enabled)
- [ ] Send confirmation email to client@example.com
- [ ] Log all actions to audit
- [ ] Update Dashboard with invoice count
- [ ] Move source to /Done/

## Approval Required

**YES** - New contact requires approval before creating invoice and sending email

## Estimated Time

3-5 minutes

---

```

---

## Approval Workflow

If approval required (new contact or high amount):

1. **Create approval request** in `/Pending_Approval/`:

   `INVOICE_approval_client@example.com_20260309_010000.md`

   Content:

   ```markdown
   ---
   type: approval_request
   action: create_invoice
   customer_email: client@example.com
   amount: 500.00
   description: Web Development Services
   requires_approval: true
   created: 2026-03-09T01:30:00Z
   ---

   # Approval Request: Create Invoice

   **Customer**: client@example.com (NEW CONTACT)
   **Amount**: $500.00
   **Description**: Web Development Services
   **Due Date**: April 15, 2026

   ## Actions
   - Customer will be created in Odoo
   - Invoice INV/2026/XXX will be generated
   - Confirmation email will be sent

   ## Reason
   - ✗ New contact (not in address book)

   ## To Approve
   Move to /Approved/

   ## To Reject
   Move to /Rejected/
   ```

2. **Wait** for human review

3. **Approved Executor** picks up:
   - Extracts invoice data from approval file
   - Calls Odoo MCP `create_invoice`, `post_invoice`
   - Sends confirmation email
   - Logs result
   - Moves approval + source EMAIL_*.md to `/Done/`

---

## Dashboard Updates

After processing batch (all or single):

Add to `Dashboard.md` "Recent Activity" section:

```markdown
## Recent Activity
- ✅ Processed 3 emails → 2 invoices created ($1,250 total)
- ⏳ 1 approval request pending (new contact)
- 📊 Invoices created this week: 5
```

Also increment "Invoices Created" counter in metrics.

---

## Logging

Every operation logged to `/Logs/YYYY-MM-DD.json`:

```json
{
  "id": "uuid-here",
  "timestamp": "2026-03-09T01:30:00.123",
  "level": "info",
  "actor": "email_to_odoo_invoice",
  "action": "invoice_created",
  "target": "INV/2026/001",
  "parameters": {
    "customer_email": "client@example.com",
    "amount": 500.00,
    "description": "Web Development"
  },
  "result": {
    "invoice_id": 123,
    "invoice_number": "INV/2026/001",
    "posted": true
  },
  "duration_ms": 3450
}
```

On errors:

```json
{
  "actor": "email_to_odoo_invoice",
  "action": "extract_invoice_details",
  "error": "Could not find amount in email body",
  "level": "error"
}
```

---

## Error Handling

### Amount Not Found
- Log error
- Create approval request for manual review (amount missing)
- Mark email as needing clarification

### Odoo Connection Failed
- Retry 3 times with exponential backoff (leveraging circuit breaker)
- If still failing → create approval request for offline handling
- Alert via dashboard

### Customer Creation Failed
- Log error with details
- Request approval to manually create customer first
- Or reject with reason

### Email Send Failed
- Invoice already created in Odoo (that's source of truth)
- Log email failure but don't rollback invoice
- Create approval to send email manually later

---

## Configuration

Skill can be configured via environment or Company_Handbook:

```yaml
# In Company_Handbook.md → email_to_odoo_invoice:
email_to_odoo_invoice:
  auto_approve_amount_threshold: 1000.00  # Amount below which known contacts auto-approve
  default_due_days: 30
  default_quantity: 1
  product_type: "service"  # or "consu"
  send_confirmation_email: true
  require_approval_new_contacts: true
  domain_whitelist: ["company.com", "client.org"]  # Auto-approve if from these domains
```

---

## Testing

### Test 1: Dry Run Detection

```
/skill email_to_odoo_invoice --all --dry-run
```

Expected output:
- Lists emails found
- For each: "Invoice detected: $500 for client@example.com"
- Shows whether approval required
- Shows planned Odoo actions

### Test 2: Create Test Email

Create test EMAIL_*.md:

```markdown
---
from: test.client@example.com
subject: Invoice request for $500
date: 2026-03-09
---

Hi,

Please send an invoice for $500 for web development services.

Thanks,
Test Client
```

Place in `/Needs_Action/` and run:
```
/skill email_to_odoo_invoice --item EMAIL_invoice_request_test_*.md --auto-post
```

Expected:
- Plan created in `/Plans/`
- If new contact → approval request in `/Pending_Approval/`
- If approved → Odoo invoice created
- Confirmation email sent
- Files moved to `/Done/`

---

## Dependencies

- **Odoo MCP Server** - Must be running and configured in Claude Code (`odoo-mcp`)
- **Email MCP Server** - For sending confirmations (email-mcp)
- **Approval Workflow Skill** - For HITL on new contacts/high amounts
- **Audit Logger** - For compliance tracking (Phase 3)

---

## Security Notes

- ✅ All invoice creations logged to audit trail
- ✅ New contacts require human approval (configurable threshold)
- ✅ Amount extraction verified before Odoo call
- ✅ Customer data handled per GDPR (local storage only)
- ⚠️ Auto-approve thresholds should be conservative
- ⚠️ Product auto-creation could be abused - validate descriptions

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Invoice not detected | Check email contains recognizable amount pattern ($X) or words "invoice" |
| Customer not created | Verify Odoo MCP connection and permissions |
| Amount wrong | Ensure clear "$500.00" format, not "five hundred dollars" |
| Approval not created | Check /Pending_Approval/ folder exists and is writable |
| No confirmation email | Verify Email MCP server is running, check logs |

---

## Future Enhancements

- [ ] Parse email attachments (PDF quotes) for amount/description
- [ ] Smart product suggestion based on description keywords
- [ ] Multi-currency support (detect EUR, GBP)
- [ ] Tax calculation integration
- [ ] Discount/early payment terms detection
- [ ] Recurring invoice pattern detection
- [ ] Customer credit check (query AR balance before creating)
- [ ] Integration with payment gateways (Stripe, PayPal) to auto-send payment link

---

**Skill: email_to_odoo_invoice**
**Version: 0.1-Phase4**
**Last Updated: 2026-03-09**
