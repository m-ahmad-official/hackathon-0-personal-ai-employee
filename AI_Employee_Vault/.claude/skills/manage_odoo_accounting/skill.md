# Manage Odoo Accounting
**Gold Tier Skill** - Integrate Odoo Community for business accounting

---

## Description

This skill provides comprehensive Odoo integration for automated accounting workflows:
- Create and manage customers
- Generate invoices from email requests
- Track payments and accounts receivable
- Update Dashboard with financial metrics
- Feed data to Weekly CEO Briefing

**Gold Tier Capability:** Full business accounting automation with audit trail.

---

## Usage

```
/skill manage_odoo_accounting [--action ACTION] [--dry-run]
```

---

## Actions

### `--action create_invoice`

Create an invoice from a client request.

**Flow:**
1. Read input source (EMAIL_*.md or WHATSAPP_*.md)
2. Extract client email and requested items
3. Search/validate customer in Odoo
4. Create draft invoice with line items
5. Optionally post invoice
6. Log transaction in `/Logs/`
7. Update Dashboard with AR balance

**Example:**
```
/skill manage_odoo_accounting --action create_invoice --from EMAIL_client_request_20260306.md
```

---

### `--action record_payment`

Record a payment received against an invoice.

**Flow:**
1. Parse payment notification (email or manual input)
2. Find matching open invoice
3. Create payment record
4. Reconcile with invoice
5. Update Dashboard: reduce AR, increase cash

**Example:**
```
/skill manage_odoo_accounting --action record_payment --invoice_id 45 --amount 500 --method bank
```

---

### `--action update_dashboard`

Pull latest Odoo data and update Dashboard.md.

**What gets updated:**
- Current AR balance (Account 121000)
- Cash balance (Account 101401)
- Unpaid invoices count and total
- Recent payments (last 7 days)
- Top customers (YTD)

**Example:**
```
/skill manage_odoo_accounting --action update_dashboard
```

---

### `--action generate_monthly_report`

Generate monthly financial summary.

**Output:** Creates `/Briefings/Monthly_Financial_YYYY-MM.md` with:
- Revenue by customer
- Invoice aging (0/30/60/90+ days)
- Top products/services sold
- Cash flow summary

**Example:**
```
/skill manage_odoo_accounting --action generate_monthly_report --month 02 --year 2026
```

---

## Behavior

### Input Processing

The skill can accept input from:
- File path (--from FILE)
- Stdin (pipe)
- Direct parameters (--email, --amount, etc.)

### Validation Steps

1. **Customer Validation:**
   - Must have valid email
   - Must exist in Odoo (or create with --create-customer flag)

2. **Invoice Validation:**
   - Amount must be positive
   - Items must have name, quantity, price
   - Due date must be in future (or today)

3. **Permission Check:**
   - If amount > $1000, require approval
   - If new customer, require approval
   - Auto-approve for existing customers < $500

---

## Integration Points

- **Gmail Watcher**: Detects payment notifications → record_payment
- **process_email_requests**: Can call this skill for billing-related emails
- **generate_weekly_briefing**: Pulls Odoo data for financial section
- **Dashboard**: Updates real-time financial widgets
- **Approval Workflow**: Large invoices require human approval

---

## Error Handling

- **Odoo connection failure**: Log error, retry in 5 minutes (exponential backoff)
- **Customer not found**: Create if --create-customer flag, else error
- **Invoice validation error**: Return detailed message, do not create
- **Rate limit**: If Odoo returns 429, wait and retry

---

## Data Sources

Claude will read from:
- `Business_Goals.md` - Revenue targets, approval thresholds
- `Dashboard.md` - Current metrics
- `/Logs/` - Audit trail
- `/Needs_Action/` - Incoming requests
- Odoo database via MCP tools

---

## Configuration

In `Company_Handbook.md`, add:

```yaml
odoo:
  approval_threshold: 500  # Amount above which approval required
  auto_create_customers: false
  default_payment_journal: "Bank"
  default_due_days: 30
  dashboard_update_frequency: "hourly"
```

---

## Output

- Creates/updates Odoo records via MCP
- Writes audit log entry: `/Logs/YYYY-MM-DD.json`
- Updates Dashboard.md (if requested)
- Moves source files to `/Done/` when complete

---

## Testing

### Test 1: Dry Run
```
/skill manage_odoo_accounting --action create_invoice --dry-run
```
Logs what would be created without calling Odoo.

### Test 2: Real Invoice (Test Customer)
```
/skill manage_odoo_accounting --action create_invoice --customer test.client@example.com --items 'Consulting,1,500'
```

### Test 3: Update Dashboard
```
/skill manage_odoo_accounting --action update_dashboard
```

---

## Gold Tier Requirement

This skill enables:
- ✅ Automatic invoicing from email/WhatsApp
- ✅ Financial tracking in CEO Briefing
- ✅ AR aging and cash position in Dashboard
- ✅ Audit trail of all billing actions

---

## Future Enhancements (Platinum)

- Multi-currency support
- Recurring invoices
- Automated payment reconciliation
- Integration with banking APIs for auto-payment detection
- Tax calculation (VAT, GST)
- Expense tracking and bills

---

*Skill: manage_odoo_accounting*
*Version: 0.1-Gold*
*Last Updated: 2026-03-06*
