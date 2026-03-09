# Security & Privacy Guidelines

*AI Employee - Security Best Practices*

---

## 🥇 Gold Tier Security Status

✅ **Level**: Local-first with external API integrations (Odoo, Facebook, Instagram, Twitter, Gmail, WhatsApp, LinkedIn)
✅ **Data Location**: 100% local vault + cloud API access (read/write)
✅ **Encryption**: TLS for all API calls (HTTPS)
⚠️ **Credentials**: OAuth tokens & API keys stored locally (`.env`, `mcp-servers/*/.env`)
⚠️ **Audit Logging**: Enhanced with per-process files, receipts in `Done/`, event bus
✅ **HITL**: Human approval required for sensitive actions
✅ **Error Recovery**: Circuit breakers prevent cascade failures
✅ **Observability**: Health monitoring, metrics, audit trails

---

## Threat Model (Gold)

With multiple external integrations and automated workflows:

| Threat | Risk Level | Mitigation |
|--------|-----------|------------|
| API credential theft | **HIGH** | `.gitignore` + per-process `.env` + never commit + rotate monthly |
| Unauthorized social posts | **HIGH** | HITL approval + audit logs + receipts in `Done/` |
| Unauthorized financial actions | **HIGH** | HITL approval + Odoo audit + receipt files |
| Event bus tampering | **MEDIUM** | File-based events in vault (protected by filesystem perms) |
| Data leakage in logs | **MEDIUM** | Per-process logs (no cross-contamination) + sanitization |
| Circuit breaker bypass | **LOW** | Separate breakers per platform, fail-safe defaults |
| Health monitor spoofing | **LOW** | Read-only HTTP endpoints, localhost only |
| Approval bypass | **HIGH** | File system permissions, separate executor process |

---

## Gold Tier Security Practices

### 1. Credential Management (CRITICAL)

**NEVER commit these files** - they are in `.gitignore`:
- `credentials.json` - Google OAuth client credentials
- `token.json` - Google OAuth access/refresh tokens
- `.env` - Root environment variables
- `mcp-servers/odoo-mcp/.env` - Odoo API keys
- `mcp-servers/social-mcp/.env` - Facebook/Instagram/Twitter API keys
- `mcp-servers/*/.env` - Any MCP server credentials
- `session/` - WhatsApp Web session data
- `linkedin_session/` - LinkedIn browser cookies

**Storage best practices:**
```bash
# Store all credentials outside project if possible
export AI_EMPLOYEE_CONFIG_DIR="$HOME/.ai-employee"
cp credentials.json $AI_EMPLOYEE_CONFIG_DIR/
cp -r mcp-servers/*/.env $AI_EMPLOYEE_CONFIG_DIR/
# Create symlinks
ln -s $AI_EMPLOYEE_CONFIG_DIR/credentials.json ./
ln -s $AI_EMPLOYEE_CONFIG_DIR/.env ./
```

**Per-service credentials:**
- **Odoo**: URL, DB, username, password in `mcp-servers/odoo-mcp/.env`
- **Facebook**: Page ID, Page Access Token in `mcp-servers/social-mcp/.env`
- **Instagram**: Business Account ID (uses Facebook token)
- **Twitter**: API key, secret, access token, access secret, bearer token
- **Gmail**: OAuth 2.0 client credentials (`credentials.json`) + token (`token.json`)
- **WhatsApp**: Session files (encrypted by WhatsApp)
- **LinkedIn**: Browser session cookies (`linkedin_session/`)

**Rotation schedule:**
- OAuth tokens: Refresh automatically (Google: 1 hour, but refresh token lasts 60 days)
- Facebook Page Access Tokens: 60 days (set to long-lived token)
- Twitter API keys: Rotate quarterly or if compromise suspected
- Client secrets: Rotate quarterly
- Session data: Delete and re-login if device compromised

### 2. Human-in-the-Loop (HITL) - Required for Sensitive Actions

**Auto-Approve (No Human Review):**
- Email replies to **known contacts** (in address book)
- File organization and categorization
- Reading data from external sources
- Creating draft responses
- Invoice creation from verified email requests (if configured)

**Always Require Approval:**
- ✗ Sending emails to **new recipients**
- ✗ **Any financial transactions** (create/post invoices, record payments)
- ✗ **Posting to social media** (Facebook, Instagram, Twitter, LinkedIn)
- ✗ Accessing new services for the first time
- ✗ Deleting data from vault
- ✗ Changing system configuration
- ✗ Browser automation beyond monitored sessions
- ✗ MCP server configuration changes

**Approval Workflow:**
1. AI creates request file in `/Pending_Approval/` with full context, parameters, and estimated impact
2. Human reviews manually (or via `utils/approval_manager.py`)
3. Human moves to `/Approved/` or `/Rejected/`
4. Only then does `watchers/approved_executor.py` perform the action
5. Result logged with approver identity (future: `approved_by` field)
6. Receipt file created in `/Done/` with full details

### 3. Audit Logging - Complete Immutable Trail

**Per-Process Logs** (prevents corruption):
- Format: `AI_Employee_Vault/Logs/YYYY-MM-DD.proc_PID.json`
- Each process writes to its own file (no cross-process locking needed)
- Absolute path resolution ensures all processes write to same vault location

**Log content** (AuditEntry):
```json
{
  "id": "uuid",
  "timestamp": "2026-03-09T04:49:06.706623",
  "level": "info",
  "actor": "social-mcp",
  "action": "facebook_post",
  "target": "558039920729813_122179418222791659",
  "parameters": {"message": "...", "link": "..."},
  "result": {"post_id": "..."},
  "duration_ms": 5575,
  "error": null,
  "audit_trail": []
}
```

**Receipt Files** in `Done/` for external actions:
- Facebook: `FACEBOOK_POST_YYYYMMDD_HHMMSS_MS.md`
- Instagram: `INSTAGRAM_POST_YYYYMMDD_HHMMSS_MS.md`
- Odoo Invoice Create: `ODOO_INVOICE_CREATE_YYYYMMDD_HHMMSS_MS.md`
- Odoo Invoice Post: `ODOO_INVOICE_POST_YYYYMMDD_HHMMSS_MS.md`
- Includes full frontmatter, parameters, result, duration, URL to external resource

**Event Bus** (real-time notifications):
- Events stored in `AI_Employee_Vault/Events/` with UUID filenames
- Contains: `id`, `timestamp`, `type`, `source`, `priority`, `data`, `retry_count`, `consumed_by`
- Processed events moved to `Events/processed/` with consumer suffix
- Error events saved to `Events/error/`

**Retention & Rotation:**
- Daily rotation (midnight) with size-based fallback (10MB max)
- Gzip archival after 1 day (`Logs/archive/`)
- Auto-delete after 90 days (configurable)
- Receipt files and events are **never deleted** (permanent archive)

**Query Interface** (`utils/audit/logger.py`):
```python
entries = logger.read_logs(
    date="2026-03-09",
    start_date="2026-03-01",
    end_date="2026-03-09",
    action="facebook_post",  # or ["facebook_post", "instagram_post"]
    actor="social-mcp",
    level="info",
    limit=1000
)
```

**Compliance Reports**:
- Total actions by type, by actor
- Approval usage statistics
- Error rate and duration statistics
- Sensitive data access tracking

### 4. Error Recovery - Fail-Safe Defaults

**Circuit Breakers** (per platform):
- States: CLOSED (normal) → OPEN (after 5 failures) → HALF_OPEN (test after 60s)
- Breakers: `facebook_api`, `instagram_api`, `odoo`, `twitter_api`
- Auto-recovery after `recovery_timeout` with `success_threshold` of 3

**Retry Logic**:
- Exponential backoff: `min(2 ** attempt, 60)` seconds
- jitter (randomized) to prevent stampeding herd
- Max attempts: 3 (configurable)
- Retries only on network errors (ConnectionError, TimeoutError, ProtocolError)

**Health Monitoring** (`utils/error_recovery/health_server.py`):
- HTTP server on port 8080 (configurable)
- Endpoints:
  - `GET /health` - overall status (healthy/degraded/unhealthy)
  - `GET /health/ready` - readiness probe (all dependencies ready)
  - `GET /health/live` - liveness probe (process is running)
  - `GET /metrics` - JSON metrics for monitoring systems
  - `GET /status` - detailed component status
- Monitors: Odoo, social-mcp, PostgreSQL, disk space, memory usage
- Background daemon (PID file: `utils/error_recovery/health_server.pid`)

**Production Scripts**:
- `start_all.sh` - Starts all services in order with health checks
- `stop_all.sh` - Graceful shutdown, stops Docker containers
- `status.sh` - Comprehensive status report (processes, Docker, health, events)

### 5. Event Bus - Decoupled Integration

**Architecture**:
- File-based events in `AI_Employee_Vault/Events/`
- Atomic writes: write to `.tmp` then rename (no partial reads)
- Consumers (`utils/event_bus/consumers/`):
  - `dashboard_consumer.py` - Updates dashboard on events
  - `email_odoo_consumer.py` - Creates invoices from emails
- Producers: MCP servers (social-mcp, odoo-mcp) emit events on actions

**Event Types**:
- `invoice.created` - Odoo invoice created
- `invoice.posted` - Invoice validated/posted
- `social.post.published` - Facebook/Instagram/Twitter post
- `email.received` - New email in Needs_Action
- `workflow.completed` - Task finished

**Retry & Error Handling**:
- Events have `retry_count` and `max_retries` (default 3)
- Failed events moved to `Events/error/` after max retries
- Consumers acknowledge by moving to `processed/` with `{consumer}_` suffix

### 6. Permission Boundaries (What AI Can Do Automatically)

| Action | Auto-Approve? | Requires Approval | Notes |
|--------|---------------|-------------------|-------|
| Read files from vault | ✅ | - | Read-only, safe |
| Write files to vault | ✅ | - | Within vault bounds |
| Move files within vault | ✅ | - | Atomic operations |
| Create plans in /Plans/ | ✅ | - | Planning is safe |
| Update Dashboard.md | ✅ | - | Status only |
| Read Odoo (search_customers, get_balance) | ✅ | - | Read-only financial data |
| Create draft invoice (via skill) | ⚠️ | Configurable | Depends on email intent detection |
| Post invoice (validate) | ❌ | ✅ | Financial action |
| Record payment | ❌ | ✅ | Financial transaction |
| Post to Facebook/Instagram | ❌ | ✅ | Public-facing, brand risk |
| Tweet | ❌ | ✅ | Public-facing |
| Delete vault data | ❌ | ✅ | Irreversible |
| Access browser sessions | ❌ | ✅ | Session hijacking risk |
| Execute shell commands | ❌ | ✅ | Arbitrary code execution |

### 7. Communication Security

- **All API calls use HTTPS** (enforced by libraries: Facebook Graph API, Instagram API, Twitter API, Odoo, Gmail API)
- **TLS certificate verification** enabled by default (do not disable)
- **Certificate pinning** (future): For critical services, implement pinning
- **No self-signed certs** in production (reject invalid certificates)

**OAuth scopes** (principle of least privilege):
- Gmail: `https://mail.google.com/` (full access) - consider narrower scopes if possible
- Facebook: `pages_manage_posts`, `pages_read_engagement`
- Instagram: `instagram_content_publish`, `instagram_basic`
- Twitter: `tweet.write`, `users.read`, `tweets.read`

### 8. Sandbox Development

**Separate test accounts** (never use production):
- Gmail: Dedicated test account (not personal)
- WhatsApp: Separate number/device for testing
- LinkedIn: Test profile (not main)
- Facebook/Instagram: Test page/business account
- Twitter: Test account
- Odoo: Development database (not production)

**DRY_RUN mode** (implement in all MCP servers):
```python
if config.DRY_RUN:
    logger.info(f"[DRY_RUN] Would post to {platform}: {message[:50]}")
    return {"success": True, "dry_run": True, "message": "Skipped in DRY_RUN mode"}
else:
    # Actually execute
```

**Rate limiting** (implement per service):
```python
from ratelimiter import RateLimiter
limiter = RateLimiter(max_calls=10, period=60)  # 10 per minute
with limiter:
    gmail_api.send_email(...)
```

**Quotas and budget caps**:
- Gmail: 100 emails/day (adjust as needed)
- Facebook/Instagram: Platform rate limits vary, monitor usage
- Twitter: 300 tweets/3 hours (standard limit)
- Odoo: No external API limits, but respect server resources

**Error handling**:
- Never leak secrets in error messages
- Sanitize exceptions: `except Exception as e: logger.error(f"Failed: {type(e).__name__}")`
- Don't expose full tracebacks to end users (log only)

---

## Incident Response

### 1. Unauthorized API Access (suspicious posts/emails sent)

1. **Immediate**: Revoke OAuth tokens immediately
   - Google: https://myaccount.google.com/permissions
   - Facebook: Business Settings → System Users → Revoke
   - Instagram: Same as Facebook (linked)
   - Twitter: Settings → Apps and sessions → Revoke access
2. **Investigate**: Check logs to determine scope (which services, what actions, when)
3. **Rotate**: Generate new credentials for all services
4. **Review**: Audit approval workflow - was it bypassed? Fix any bugs
5. **Notify**: Inform affected parties if PII was sent

### 2. Credential Leak (accidentally committed secrets)

**Immediate actions**:
1. Revoke exposed credentials immediately (all services)
2. Generate new credentials (new API keys, OAuth client secrets)
3. Update all `.env` files with new values
4. **Git cleanup** (remove from history):
   ```bash
   # If not yet pushed
   git rm --cached credentials.json token.json mcp-servers/*/.env
   git commit -m "Remove secrets from tracking"
   # If already pushed, use BFG or git filter-branch to rewrite history
   # Then force push (coordinate with team)
   ```
5. **GitHub**: If using GitHub, check Security → Secret scanning (may auto-revoke)
6. **Rotate**: All services that used those credentials

### 3. AI Made Unauthorized Action (approval bypass bug)

1. **Stop all services**: `./stop_all.sh`
2. **Review logs**: Identify what happened, which skill/MCP server, parameters
3. **Root cause**: Was approval logic bypassed? Did executor run unchecked?
4. **Fix**: Patch the bug (approval check, move to /Approved/ validation)
5. **Rollback**: Consider rolling back to last known-good commit
6. **Test**: Comprehensive testing of approval workflow before restarting
7. **Add safeguards**: Additional approval gates, dry-run mode, rate limits

### 4. Session Hijacking (LinkedIn/WhatsApp session stolen)

1. **Delete sessions**:
   ```bash
   rm -rf linkedin_session/
   rm -rf session/
   ```
2. **Change passwords** for those accounts
3. **Re-authenticate** from secure device
4. **Check logs**: Look for suspicious activity timestamps
5. **Review**: How were sessions exposed? File permissions? Backup to cloud?

### 5. Data Breach (vault accessed by unauthorized party)

1. **Assume all data in vault is compromised** (emails, messages, financial data)
2. **Stop all services** immediately
3. **Revoke all API access** (Gmail, Odoo, social media)
4. **Create new vault** (new directory, new credentials)
5. **Notify**: Legal counsel, affected parties if PII/PHI involved
6. **Forensics**: Determine access vector (compromised device? stolen credentials?)
7. **Encrypt**: Future backups must be encrypted (`gpg --symmetric --cipher-algo AES256`)

### 6. Log Tampering (someone modified/deleted logs)

1. **Check receipts**: Receipt files in `Done/` and events in `Events/` are append-only
2. **File integrity**: Implement hash chaining or digital signatures (future)
3. **Restore** from backup if needed
4. **Investigate**: Who had filesystem access? Review audit trails (system logs, not vault logs)

---

## Compliance Considerations

- **GDPR**: Data stays local (good), but emails may contain EU personal data
  - If processing EU data, ensure lawful basis (consent, legitimate interest)
  - Provide right to erasure - delete PII from vault on request
  - Data Processing Agreement (DPA) may be needed with Anthropic

- **HIPAA**: **DO NOT** store Protected Health Information (PHI) in vault unless:
  - Vault is encrypted at rest (use `cryptography.fernet.Fernet`)
  - Access is logged and audited (audit logger is good start)
  - Business Associate Agreement (BAA) in place with AI provider (Anthropic)
  - Consider using HIPAA-compliant MCP servers

- **PCI-DSS**: **NEVER** store full credit card numbers, CVV, or track data
  - Tokenize if payment processing needed (Stripe/Braintree tokens)
  - Use Odoo's payment integration (token-based) instead of storing cards
  - Quarterly vulnerability scans if processing payments

- **Terms of Service**:
  - WhatsApp: Automation may violate ToS - use at your own risk, risk of ban
  - LinkedIn: Automation can get account restricted - use cautiously, rate limit
  - Gmail: Google has sending limits (500/day for free accounts, 2000 for Workspace)
  - Facebook/Instagram: Must comply with Platform Policy, no spam

---

## Security Checklist (Before Going Live with Production Data)

Before using AI Employee with production data:

- [ ] All secrets (`.env`, `credentials.json`, `token.json`, `mcp-servers/*/.env`) in `.gitignore`
- [ ] `.gitignore` checked for completeness (run `git status --short` to verify)
- [ ] Test `git push` - verify no secrets uploaded (GitHub may block)
- [ ] File permissions set: `chmod 700 AI_Employee_Vault/`, `chmod 600 *.md Logs/*.json`
- [ ] Approval workflow tested end-to-end (email, social, financial)
- [ ] Audit logs reviewed for completeness (no PII leakage, all actions logged)
- [ ] DRY_RUN mode works for all MCP servers
- [ ] Rate limiting configured (if batch processing)
- [ ] Error handling doesn't log full email bodies (sanitize PII)
- [ ] Backup vault to encrypted location: `gpg --symmetric --cipher-algo AES256 vault.tar.gz`
- [ ] Incident response plan documented (who to call, how to stop services)
- [ ] Separate test credentials (not personal Gmail/LinkedIn)
- [ ] 2FA enabled on all integrated accounts (Google, Facebook, Twitter, LinkedIn)
- [ ] OAuth consent screen published (if in production, Google may require)
- [ ] `company_approval_email@yourdomain.com` - use dedicated email for approvals
- [ ] Legal review: Are you allowed to automate these communications? (Check ToS, get legal)
- [ ] Health monitoring enabled and alerts configured (if production)
- [ ] Circuit breaker thresholds tuned appropriately for your load
- [ ] Event bus consumers running without errors (check `utils/event_bus/consumers/*.log`)

---

## Additional Gold Tier Security Features

### Event Bus Security
- Events stored in vault (inherits vault permissions)
- No external network access required
- Consumers run as separate processes (isolated)
- Failed events preserved for debugging

### Receipt Immutability
- Receipt files in `Done/` are never modified or deleted
- Full audit trail: What was done, by whom (which service), with what parameters
- Linked to external resources (post URLs, Odoo forms)

### Health Monitoring
- Localhost-only access (bind to 127.0.0.1)
- No authentication (assumes localhost is trusted)
- Read-only metrics endpoint (no state changes)

### Dashboard Auto-Update
- Runs every 5 minutes (configurable)
- Read-only queries (no writes to external systems)
- Failed updates logged, don't stop service

---

## Resources

- **OWASP API Security Top 10** - https://owasp.org/API-Project/
- **Anthropic Responsible AI** - https://www.anthropic.com/responsible-ai
- **Local-first security** - https://www.inkandswitch.com/local-first/
- **MCP Security** - https://modelcontextprotocol.io/docs/security
- **Google OAuth 2.0** - https://developers.google.com/identity/protocols/oauth2
- **Facebook Graph API** - https://developers.facebook.com/docs/graph-api/security
- **NIST Cybersecurity Framework** - https://www.nist.gov/cyberframework
- **Odoo Security** - https://www.odoo.com/documentation/master/developer/security.html

---

## Reporting Security Vulnerabilities

If you discover a security issue in this project:

1. **Do NOT open a public GitHub issue** (do not disclose publicly)
2. Email security@anthropic.com (if issue is in Claude-related code)
3. Or open a private security advisory on GitHub (if repository owner)

---

**Remember**: You are legally responsible for the AI's actions. Understand the security model before processing real data. All external API actions are attributed to your credentials.

*Last updated: 2026-03-09*
*Tier: Gold (Complete)*
*Audit Date: 2026-03-09 (Gold Tier completion)*
