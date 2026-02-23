# Security & Privacy Guidelines

*AI Employee - Security Best Practices*

---

## Bronze Tier Security Status

✅ **Level**: Local-only (no external integrations)
✅ **Data Location**: 100% local, no cloud
✅ **Encryption**: Not required (no external transmission)
⚠️ **Credentials**: None stored yet (no APIs used)

---

## Threat Model (Bronze)

Since this tier only processes local files:

| Threat | Risk Level | Mitigation |
|--------|-----------|------------|
| Unauthorized file access | Medium | File system permissions |
| Accidental data exposure | Low | .gitignore prevents commits |
| Malware in dropped files | Medium | Manual review required |
| Insider threat | Low | Physical access control |

---

## Security Practices

### 1. File System Permissions

```bash
# Set restrictive permissions
chmod 700 .
chmod 600 Dashboard.md Company_Handbook.md Business_Goals.md
chmod 700 Needs_Action Inbox Plans Done Logs
chmod 600 Needs_Action/*.md Logs/*.json
```

### 2. Never Commit Sensitive Data

The `.gitignore` prevents these files from being committed:
- `Inbox/*` - Raw dropped files
- `Logs/*.json` - May contain PII
- `credentials.json` - Would contain API keys
- `.env` - Environment secrets
- `drops/` - Drop folder contents

**Before committing**: Review with `git status` to ensure no sensitive files are staged.

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
