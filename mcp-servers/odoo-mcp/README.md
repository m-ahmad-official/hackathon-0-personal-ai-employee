# Odoo MCP Server

Gold Tier Phase 1 - MCP server for Odoo Community integration. **Now fully compatible with Odoo 19.**

## Overview

This MCP server provides Claude Code with tools to interact with Odoo 19+ via XML-RPC/JSON-RPC API.

## Features

- ✅ Search customers/partners
- ✅ Create invoices with line items
- ✅ Post/validate invoices
- ✅ Record payments
- ✅ Get account balances (computed from move lines)
- ✅ List recent invoices
- ✅ Retry logic with exponential backoff (Phase 3)
- ✅ Circuit breaker protection (Phase 3)
- ✅ Audit logging (Phase 3)

## Status

**Phase 1 + Phase 3 Integration: ✅ COMPLETE**

All tools are functional and tested with Odoo 19. Error recovery and audit logging are fully integrated.

## Prerequisites

1. **Odoo 19+** running locally or remotely (Docker or native)
2. **Accounting module** installed in Odoo
3. **Odoo admin user** (has all permissions by default)

## Installation

```bash
cd mcp-servers/odoo-mcp
pip install -r requirements.txt
```

## Configuration

Set environment variables:

```bash
export ODOO_URL="http://localhost:8069"
export ODOO_DB="odoo"
export ODOO_USERNAME="admin"
export ODOO_PASSWORD="admin"
```

Or create a `.env` file in `mcp-servers/odoo-mcp/`:

```env
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=admin
```

## Starting the Server

```bash
# With environment variables
ODOO_URL=http://localhost:8069 ODOO_DB=odoo ODOO_USERNAME=admin ODOO_PASSWORD=admin python server.py

# Or using .env file (requires python-dotenv)
pip install python-dotenv
python server.py
```

## Integration with Claude Code

Add to `~/.config/claude-code/mcp.json`:

```json
{
  "servers": [
    {
      "name": "odoo-mcp",
      "command": "python",
      "args": ["/path/to/project/mcp-servers/odoo-mcp/server.py"],
      "env": {
        "ODOO_URL": "http://localhost:8069",
        "ODOO_DB": "odoo",
        "ODOO_USERNAME": "admin",
        "ODOO_PASSWORD": "admin"
      }
    }
  ]
}
```

Restart Claude Code. Tools will be available automatically.

## Usage in Claude Code

Once connected, Claude can use tools like:

```
Use odoo-mcp to search_customers with email "test.client@example.com"

Use odoo-mcp to create_invoice with customer_email="client@example.com" and items=[{"name":"Consulting","quantity":1,"price":500}]
```

Behind the scenes, the server:
1. Automatically finds or creates customers
2. Auto-creates products if they don't exist
3. Creates invoices with proper accounting entries
4. Can post invoices and record payments
5. Logs all operations to audit trail (JSON)
6. Retries on transient failures with exponential backoff
7. Opens circuit breaker if Odoo is unavailable

## Tools Reference

### search_customers

Search for customers by email or name.

**Parameters:**
- `email` (string): Email to search for (partial match)
- `name` (string): Name to search for (partial match)
- `limit` (integer): Max results (default 10)

**Example:**
```json
{
  "email": "client@example.com"
}
```

---

### create_invoice

Create a draft invoice for a customer.

**Parameters:**
- `customer_email` (string, **required**): Customer's email
- `customer_name` (string, optional): Customer name if new (defaults to email username)
- `items` (array, **required**): List of line items
  - `name` (string): Product/service name
  - `quantity` (number): Quantity
  - `price` (number): Unit price
- `due_date` (string, optional): Due date (YYYY-MM-DD)

**Example:**
```json
{
  "customer_email": "client@example.com",
  "items": [
    {"name": "Consulting Services", "quantity": 1, "price": 500}
  ],
  "due_date": "2026-03-15"
}
```

**Returns:**
```json
{
  "invoice_id": 123,
  "invoice_number": "INV/2026/001",
  "customer": "Test Client",
  "amount_total": 500.00,
  "state": "draft",
  "invoice_date": "2026-03-09"
}
```

---

### post_invoice

Post/validate an invoice (changes state from draft to posted).

**Parameters:**
- `invoice_id` (integer, **required**): Invoice ID from `create_invoice`

**Returns:**
```json
{
  "success": true,
  "invoice_id": 123,
  "invoice_number": "INV/2026/001",
  "state": "posted"
}
```

---

### record_payment

Record a payment received for an invoice.

**Parameters:**
- `invoice_id` (integer, **required**): Invoice ID
- `amount` (number, **required**): Payment amount
- `payment_date` (string, optional): Payment date (YYYY-MM-DD, default: today)
- `journal` (string, optional): Payment method (default "bank", e.g., "cash", "check")

**Returns:**
```json
{
  "payment_id": 456,
  "invoice_id": 123,
  "amount": 500.00,
  "journal": "bank"
}
```

---

### get_account_balance

Get current balance for an account (computed from posted move lines).

**Parameters:**
- `account_code` (string, **required**): Odoo account code (e.g., "121000" for Accounts Receivable)

**Example:**
```json
{
  "account_code": "121000"
}
```

**Returns:**
```json
{
  "account_code": "121000",
  "account_name": "Accounts Receivable",
  "balance": 15000.00
}
```

**Note:** In Odoo 19, `balance` is not a direct field on `account.account`. It's computed from `account.move.line` records.

---

### list_recent_invoices

List recent invoices with status.

**Parameters:**
- `limit` (integer, optional): Max results (default 10)
- `status` (string, optional): Filter by state ("draft", "posted", "paid")

**Returns:**
```json
{
  "count": 5,
  "invoices": [
    {
      "name": "INV/2026/001",
      "partner_id": [1, "Test Client"],
      "invoice_date": "2026-03-09",
      "amount_total": 500.00,
      "state": "posted",
      "payment_state": "not_paid"
    }
  ]
}
```

---

## Testing

### Test connection:
```bash
python test_connection.py
```

Expected output:
```
✅ Odoo connection test passed (3/3 tests)
```

### Test invoice creation directly:
```bash
python test_invoice.py
```

### Test MCP server import:
```bash
python -c "from server import OdooMCPServer; print('OK')"
```

---

## Odoo 19 Compatibility

This server is fully compatible with Odoo 19. Key adaptations:

1. **Balance calculation**: Instead of reading `account.account.balance` (removed in Odoo 19), we sum `account.move.line.balance` for posted moves.
2. **Search with limit**: Uses `search_read` instead of `read` with limit parameter.
3. **Product lookup**: Dynamically finds or creates products (no hardcoded ID=1).
4. **User groups**: `groups_id` field access handled gracefully (admin has all permissions anyway).

---

## Error Recovery & Audit Logging (Phase 3)

All operations include:
- **Retry**: Automatic retry (3 attempts) with exponential backoff on transient failures
- **Circuit Breaker**: Opens after 5 consecutive Odoo failures to prevent cascade
- **Audit Log**: Every tool call logged to `AI_Employee_Vault/Logs/YYYY-MM-DD.json` with:
  - Timestamp, actor, action, target
  - Input parameters (sanitized)
  - Output result
  - Duration in milliseconds
  - Error details if failed

Example audit entry:
```json
{
  "id": "uuid-here",
  "timestamp": "2026-03-09T01:20:13.890",
  "level": "info",
  "actor": "odoo-mcp",
  "action": "create_invoice",
  "target": 9,
  "parameters": {"customer_email": "...", "items": [...]},
  "result": {"invoice_id": 9, ...},
  "duration_ms": 1350
}
```

---

## Troubleshooting

**Connection refused:**
- Verify Odoo is running: `curl http://localhost:8069`
- Check `ODOO_URL` is correct and Odoo is listening on that interface
- Ensure PostgreSQL is running (Docker: `docker-compose ps`)

**Authentication failed:**
- Verify credentials work in Odoo UI
- Ensure user has Accounting permissions (Settings → Users)
- Check database name matches (`ODOO_DB`)

**Account not found (121000):**
- Chart of Accounts not loaded. In Odoo UI: Accounting → Configuration → Chart of Accounts → Generate
- Use a different account code that exists in your Odoo instance

**Tool not found in Claude Code:**
- Restart Claude Code to reload MCP configuration
- Check `~/.config/claude-code/mcp.json` path is correct
- Look at Claude Code logs for MCP connection errors

---

## Security Notes

- Never commit `.env` or credentials to Git (already in `.gitignore`)
- For production, consider using Odoo's API key authentication instead of password
- MCP server only binds to localhost (via stdio) - no network exposure
- Audit logs may contain sensitive data - store securely and rotate

---

## Gold Tier Integration

This MCP server enables:
- Automated invoicing from email/WhatsApp requests via Claude
- Payment reconciliation
- Financial reporting in CEO Briefing
- Accounts receivable tracking in Dashboard
- Integration with `process_email_requests` and `manage_odoo_accounting` skills

---

## Next Steps (Optional Enhancements)

1. **Error recovery tuning**: Adjust circuit breaker thresholds in `server.py` if needed
2. **Audit log review**: Query logs for compliance reporting
3. **Health monitoring**: Install `psutil` and run `python ../../utils/error_recovery/health_server.py` to enable `/health` endpoint
4. **Skill creation**: Build `manage_odoo_accounting` Agent Skill wrapper
5. **Dashboard integration**: Add real-time Odoo metrics to Dashboard.md

---

*Version: 0.2-Gold (Odoo 19 Compatible)*
*Last Updated: 2026-03-09*
*Status: ✅ Production Ready*
