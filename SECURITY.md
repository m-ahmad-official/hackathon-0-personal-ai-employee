# Security & Privacy Guidelines

*AI Employee - Security Best Practices*

---

## 🥈 Silver Tier Security Status

✅ **Level**: Local-first with external API integrations (Gmail, WhatsApp Web, LinkedIn)
✅ **Data Location**: 100% local vault + cloud API access (read/write)
✅ **Encryption**: TLS for all API calls (HTTPS)
⚠️ **Credentials**: OAuth tokens stored locally (`credentials.json`, `token.json`)
⚠️ **Audit Logging**: Enabled (unencrypted - avoid PII in logs)
✅ **HITL**: Human approval required for sensitive actions

---

## Threat Model (Silver)

With external integrations, new attack surfaces emerge:

| Threat | Risk Level | Mitigation |
|--------|-----------|------------|
| API credential theft | **HIGH** | `.gitignore` + never commit + rotate monthly |
| Unauthorized email sends | **HIGH** | HITL approval for new contacts + audit logs |
| Session hijacking (WhatsApp/LinkedIn) | **MEDIUM** | Persistent sessions stored locally, never commit |
| Data leakage in logs | **MEDIUM** | Sanitize PII before logging, encrypt logs if needed |
| Malicious email attachments | **MEDIUM** | Do not auto-download attachments, manual review |
|自动化误操作 | **MEDIUM** | Approval workflow + dry-run mode + rate limiting |
| Insider threat (AI itself) | **LOW** | Sandboxed operations, read-only by default |

---

## Silver Tier Security Practices

### 1. Credential Management (CRITICAL)

**NEVER commit these files** - they are in `.gitignore`:
- `credentials.json` - Google OAuth client credentials (public ID + secret)
- `token.json` - OAuth access/refresh tokens (full account access!)
- `.env` - Any environment variables with secrets
- `linkedin_session/` - Browser cookies (session hijacking risk)
- `session/` - WhatsApp session data (full message access!)

**Storage best practices:**
```bash
# Store credentials outside project if possible
export AI_EMPLOYEE_CONFIG_DIR="$HOME/.ai-employee"
cp credentials.json $AI_EMPLOYEE_CONFIG_DIR/
# Create symlink: ln -s $AI_EMPLOYEE_CONFIG_DIR/credentials.json ./

# Or use environment variables (preferred for production)
export GMAIL_CLIENT_ID="..."
export GMAIL_CLIENT_SECRET="..."
# Modify code to read from os.getenv()
```

**Rotation schedule:**
- OAuth tokens: Refresh automatically (60-day lifetime)
- Client secrets: Rotate quarterly
- Session data: Delete and re-login if device compromised

### 2. Human-in-the-Loop (HITL) - Required for Sensitive Actions

From `Company_Handbook.md`:

**Auto-Approve (No Human Review):**
- Email replies to **known contacts** (in address book from previous emails)
- File organization and categorization
- Reading data from external sources
- Creating draft responses

**Always Require Approval:**
- ✗ Sending emails to **new recipients** (first-time contact)
- ✗ Any financial transactions (payments, transfers)
- ✗ Posting to social media (LinkedIn, Twitter)
- ✗ Accessing new services for the first time
- ✗ Deleting data from vault
- ✗ Changing system configuration
- ✗ Browser automation beyond monitored sessions

**Approval Workflow:**
1. AI creates request file in `/Pending_Approval/` with full context
2. Human reviews manually (or via `approval_manager.py`)
3. Human moves to `/Approved/` or `/Rejected/`
4. Only then does executor perform the action
5. Result logged with approver identity (future: `approved_by` field)

### 3. Audit Logging (Every Action Must Be Logged)

All actions logged to `/Logs/YYYY-MM-DD.json`:

```json
{
  "timestamp": "2026-02-28T02:44:48.123456",
  "action_type": "email_processed",
  "source_file": "EMAIL_client_abc123_20260228_024304.md",
  "sender": "client@example.com",
  "subject": "Inquiry about services",
  "response_type": "reply",
  "approval_required": true,
  "approval_status": "approved",
  "approver": "human_username",  // Future: track who approved
  "plan_created": "PLAN_EMAIL_...md",
  "executed_at": "2026-02-28T02:50:00Z",
  "result": "success",
  "message_id": "17c9c14f71d777b8"
}
```

**Logging Requirements:**
- Timestamp in ISO 8601 format
- Actor (component that triggered action)
- Action type (email_sent, whatsapp_processed, linkedin_posted)
- Parameters (sanitized - mask API keys, tokens, PII)
- Result (success/failure + error message)
- Approval status (required? granted? by whom?)

**Encryption:**
Currently logs are plain JSON. If logs contain sensitive data (email bodies, phone numbers):
```python
from cryptography.fernet import Fernet
cipher = Fernet(encryption_key)
encrypted_log = cipher.encrypt(json.dumps(entry).encode())
```
Future: Add log encryption at rest.

### 4. Permission Boundaries (What AI Can Do Automatically)

| Action | Auto-Approve? | Requires Approval | Rationale |
|--------|---------------|-------------------|-----------|
| Read files from vault | ✅ | - | Read-only, safe |
| Write files to vault | ✅ | - | Within vault bounds |
| Move files within vault | ✅ | - | Atomic operations |
| Create plans in /Plans/ | ✅ | - | Planning is safe |
| Update Dashboard.md | ✅ | - | Status only |
| Read Gmail (watch only) | ✅ | - | Passive monitoring |
| **Send email to known contact** | ✅ | - | Historical relationship |
| **Send email to NEW contact** | ❌ | ✅ | First contact = risk |
| Reply to WhatsApp (known) | ✅ | - | Existing conversation |
| Reply to WhatsApp (new) | ❌ | ✅ | New contact |
| Post to LinkedIn | ❌ | ✅ | Public-facing, brand risk |
| Delete vault data | ❌ | ✅ | Irreversible |
| Access browser sessions | ❌ | ✅ | Session hijacking risk |
| Execute shell commands | ❌ | ✅ | Arbitrary code exec |

### 5. Communication Security

- **All API calls use HTTPS** (enforced by libraries: Gmail API, etc.)
- **TLS certificate verification** enabled by default (do not disable)
- **Certificate pinning** (future): For critical services, pin certificates
- **No self-signed certs** in production

### 6. Sandbox Development

For Silver/Gold development and testing:

- **Separate test accounts**:
  - Gmail: Use a dedicated test account, not your personal
  - WhatsApp: Use a separate number/device for testing
  - LinkedIn: Use a test profile, not your main

- **DRY_RUN mode**:
  ```python
  if config.DRY_RUN:
      logger.info(f"[DRY_RUN] Would send email to {to}")
      return {"success": True, "dry_run": True}
  else:
      # Actually send
  ```

- **Rate limiting**:
  ```python
  from ratelimiter import RateLimiter
  limiter = RateLimiter(max_calls=10, period=60)  # 10 per minute
  with limiter:
      gmail_api.send_email(...)
  ```

- **Quotas and budget caps**:
  - Gmail: 100 emails/day (adjust as needed)
  - LinkedIn: 10 posts/day (rate limit)
  - WhatsApp: 100 messages/day (Twilio costs)

- **Error handling**:
  - Never leak secrets in error messages
  - Sanitize exceptions: `except Exception as e: logger.error(f"Failed: {str(e)[:100]}")  # Truncate`

---

## Incident Response

If you discover a security incident:

1. **Unauthorized API access** (suspicious emails sent):
   - Revoke OAuth tokens immediately: Google Account → Security → Third-party access
   - Check logs to determine scope of breach
   - Rotate all credentials (new `credentials.json`, `token.json`)
   - Review approval workflow - was it bypassed?

2. **Credential leak** (accidentally committed secrets):
   - **Immediate**: Rotate credentials (new client secret, new tokens)
   - **Git**: Remove from history with `git filter-branch` or `bfg`
   - **GitHub**: Revoke exposed secrets, check GitHub secrets if Actions used
   - **Notify**: If personal data leaked, inform affected parties

3. **AI made unauthorized action** (sent email without approval):
   - Stop all watchers immediately
   - Review logs to identify root cause
   - Fix approval logic (bug in skill?)
   - Consider rolling back to known-good commit
   - Add additional approval gate if needed

4. **Session hijacking** (someone else accessed LinkedIn/WhatsApp session):
   - Delete `linkedin_session/` and `session/` folders
   - Change passwords for those accounts
   - Re-authenticate from secure device

5. **Data breach** (vault accessed by unauthorized party):
   - Assume all data in vault is compromised
   - Move to new vault (new directory, new credentials)
   - Revoke all API access
   - Encrypt backups going forward

---

## Compliance Considerations

- **GDPR**: Data stays local (good), but emails may contain EU personal data
  - If processing EU data, ensure lawful basis (consent, legitimate interest)
  - Provide right to erasure - delete PII from vault on request

- **HIPAA**: **DO NOT** store Protected Health Information (PHI) in vault unless:
  - Vault is encrypted at rest (use `cryptography` library)
  - Access is logged and audited
  - Business Associate Agreement (BAA) in place with AI provider

- **PCI-DSS**: **NEVER** store full credit card numbers, CVV, or track data
  - Tokenize if payment processing needed
  - Use Stripe/Braintree instead of direct card storage

- **Terms of Service**:
  - WhatsApp: Automation may violate ToS - use at your own risk
  - LinkedIn: Automation can get account restricted - use cautiously
  - Gmail: Google has sending limits (500/day for free accounts)

---

## Security Checklist (Before Going Live)

Before using AI Employee with production data:

- [ ] All secrets (`credentials.json`, `token.json`, `.env`) in `.gitignore`
- [ ] `.gitignore` checked for completeness
- [ ] Run `git status --short` - no sensitive files staged
- [ ] Test `git push` - verify no secrets uploaded (GitHub may block)
- [ ] File permissions set: `chmod 700 AI_Employee_Vault/`, `chmod 600 *.md Logs/*.json`
- [ ] Approval workflow tested end-to-end
- [ ] Audit logs reviewed for completeness
- [ ] DRY_RUN mode works for all actions
- [ ] Rate limiting configured (if batch processing)
- [ ] Error handling doesn't log full email bodies (PII)
- [ ] Backup vault to encrypted location (e.g., `gpg --symmetric --cipher-algo AES256 vault.tar.gz`)
- [ ] Incident response plan documented (who to call, how to stop)
- [ ] Separate test credentials (not personal Gmail)
- [ ] 2FA enabled on all integrated accounts (Gmail, LinkedIn)
- [ ] OAuth consent screen published (if in production)
- [ ] `company_approval_email@yourdomain.com` - use dedicated email for approvals
- [ ] Legal review: Are you allowed to automate these communications?

---

## Resources

- **OWASP API Security Top 10** - https://owasp.org/API-Project/
- **Anthropic Responsible AI** - https://www.anthropic.com/responsible-ai
- **Local-first security** - https://www.inkandswitch.com/local-first/
- **MCP Security** - https://modelcontextprotocol.io/docs/security
- **Google OAuth 2.0** - https://developers.google.com/identity/protocols/oauth2
- **NIST Cybersecurity Framework** - https://www.nist.gov/cyberframework

---

## Reporting Security Vulnerabilities

If you discover a security issue in this project:

1. **Do NOT open a public GitHub issue** (do not disclose publicly)
2. Email security@anthropic.com (if issue is in Claude-related code)
3. Or open a private security advisory on GitHub (if repository owner)

---

**Remember**: You are legally responsible for the AI's actions. Understand the security model before processing real data.

*Last updated: 2026-02-28*
*Tier: Silver*
*Audit Date: 2026-02-28 (initial)*

### 3. Sandbox Development

For Silver/Gold tiers, implement:
- Separate test/sandbox accounts
- `DRY_RUN` mode for all actions
- Rate limiting
- Quotas and budget caps

### 4. Audit Logging

Every action is logged to:
```
/Logs/YYYY-MM-DD.json
```

Example log entry:
```json
{
  "timestamp": "2026-02-24T12:34:56Z",
  "action_type": "file_processed",
  "source_file": "FILE_test_20260224_123456.md",
  "plan_created": "PLAN_FILE_test_abc123.md",
  "orchestrator": "bronze-v0.1"
}
```

---

## Upgrading to Silver/Gold: New Security Requirements

When adding external integrations:

### 1. Credential Management

**NEVER** do this:
```python
API_KEY = "sk-abc123..."  # ❌ Hard-coded secret
```

**ALWAYS** do this:
```bash
# .env file (never commit)
GMAIL_CLIENT_ID=your_client_id
GMAIL_CLIENT_SECRET=your_secret
WHATSAPP_SESSION=/secure/path/session
```

```python
import os
from dotenv import load_dotenv

load_dotenv()  # Loads from .env
api_key = os.getenv('API_KEY')  # ✅ Secure
```

### 2. Human-in-the-Loop (HITL)

For sensitive actions, **AI must request approval**:

1. AI creates request file in `/Pending_Approval/`
2. Human reviews manually
3. Human moves to `/Approved/` or `/Rejected/`
4. Only then does MCP server execute

**Sensitive actions requiring approval**:
- Sending emails to new contacts
- Any payment/transfer
- Social media posts
- Deleting vault data
- Accessing credentials

### 3. Permission Boundaries

| Action | Auto-Approve | Require Approval |
|--------|-------------|------------------|
| File read | ✅ | - |
| File write (vault) | ✅ | - |
| Move within vault | ✅ | - |
| Email to known contact | ✅ | - |
| Email to new contact | ❌ | ✅ |
| Any payment | ❌ | ✅ |
| Browser automation | ❌ | ✅ |
| Delete operations | ❌ | ✅ |
| MCP server access | Varies | ✅ |

### 4. Logging Requirements

All actions MUST be logged with:

- Timestamp (ISO 8601)
- Actor (which component triggered it)
- Action type
- Parameters (sanitized - mask PII)
- Result (success/failure)
- Approval status (who approved)

### 5. Secure Communication

- Encrypt logs at rest if containing PII
- Use HTTPS for all API calls
- Verify TLS certificates
- Implement certificate pinning for critical services
- Rotate credentials monthly

---

## Incident Response

If you discover:
- **Unauthorized access**: Revoke all credentials, check logs, rotate keys
- **Data breach**: Assume vault compromised, move to new vault
- **AI made unauthorized action**: Review logs, disable MCP server, fix approval logic
- **Credential leak**: Revoke immediately, rotate everywhere used

---

## Compliance Notes

- **GDPR**: Data stays local, no external processing
- **HIPAA**: Don't store PHI unless encrypted and access-controlled
- **PCI-DSS**: Never store full credit card numbers
- **Terms of Service**: Check WhatsApp/Automation policies

---

## Security Checklist

Before upgrading to Silver/Gold:

- [ ] All secrets in environment variables
- [ ] .env in .gitignore and never committed
- [ ] Approval workflow implemented and tested
- [ ] Comprehensive audit logging active
- [ ] DRY_RUN mode works for all actions
- [ ] Rate limiting configured
- [ ] Error handling doesn't leak secrets
- [ ] Backups encrypted and tested
- [ ] Incident response plan documented

---

## Resources

- OWASP API Security Top 10
- Anthropic's Responsible AI Guidelines
- Local-first security best practices
- Model Context Protocol Security Considerations

---

**Remember**: The AI acts with your credentials. You are legally responsible for its actions. Never deploy without understanding the security model.

*Last updated: 2026-02-24*
*Tier: Bronze*
