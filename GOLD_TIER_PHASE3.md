# Gold Tier Phase 3: Error Recovery & Enhanced Audit Logging

## Overview

Phase 3 adds production-grade error handling, retry logic, circuit breakers, and comprehensive audit logging to all MCP servers and core components. This provides:

- **Resilience**: Automatic retry with exponential backoff for transient failures
- **Cascade Prevention**: Circuit breakers stop calling failing services to prevent system-wide outages
- **Compliance**: Structured JSON audit logs with querying and reporting
- **Observability**: Health monitoring endpoints for Kubernetes/Proxmox integration

## Components

### 1. Error Recovery Utilities (`utils/error_recovery/retry_circuit.py`)

#### Retry Decorator

```python
from utils.error_recovery import with_retry

@with_retry(max_attempts=3, backoff_factor=2, jitter=True)
def call_external_api():
    # Will automatically retry on exceptions
    response = requests.get(url, timeout=5)
    return response.json()
```

**Features:**
- Exponential backoff: `delay = base_delay * (backoff_factor ** attempt)`
- Jitter (±20%) to prevent thundering herd problem
- Configurable max attempts, delay limits, exception types

#### Circuit Breaker

```python
from utils.error_recovery import CircuitBreaker, with_circuit_breaker

# Manual usage
breaker = CircuitBreaker(
    name="facebook_api",
    failure_threshold=5,
    recovery_timeout=60,
    success_threshold=3
)
breaker.call(requests.post, url, data=data)

# Decorator usage
@with_circuit_breaker("odoo", failure_threshold=5, recovery_timeout=60)
def call_odoo():
    return models.execute_kw(...)
```

**States:**
- **CLOSED**: Normal operation, requests pass through. Counts consecutive failures.
- **OPEN**: Service considered down, requests fail fast for `recovery_timeout` seconds.
- **HALF_OPEN**: After timeout, allow limited requests to test recovery. Successes close circuit; failures reopen.

**Thread-safe**: Multiple threads can safely use the same circuit breaker.

### 2. Enhanced Audit Logger (`utils/audit/logger.py`)

#### AuditEntry Schema

Every entry is a structured JSON object:

```json
{
  "id": "uuid-v4",
  "timestamp": "2026-03-08T14:32:10.123",
  "level": "info",
  "actor": "social-mcp",
  "action": "twitter_tweet",
  "target": "tweet_id_123",
  "parameters": {"text": "Hello world"},
  "result": {"success": true, "tweet_id": "123"},
  "duration_ms": 1250,
  "audit_trail": []
}
```

**Fields:**
- `id`: UUID for traceability
- `timestamp`: ISO 8601
- `level`: `info`, `warning`, `error`, `critical`
- `actor`: Component name (e.g., `odoo-mcp`, `claude_code`)
- `action`: Tool or operation name
- `target`: Resource ID (invoice_id, tweet_id, etc.)
- `parameters`: Input arguments (sanitized)
- `result`: Operation outcome
- `duration_ms`: Execution time
- `error`: Error message if failed
- `audit_trail`: Chain of sub-operations for complex workflows
- `approval`: Approval metadata (who approved, when, status)

#### AuditLogger API

```python
from utils.audit.logger import get_audit_logger, log_audit

# Quick logging
log_audit(
    actor="odoo-mcp",
    action="create_invoice",
    target=invoice_id,
    parameters={"customer_email": "client@example.com", "amount": 500},
    result={"invoice_number": "INV/2026/001"},
    duration_ms=1350
)

# Advanced: direct logger use
logger = get_audit_logger(
    log_dir="AI_Employee_Vault/Logs",
    retention_days=90,
    rotation_days=1,
    max_bytes=10*1024*1024  # 10MB
)

# Query logs
entries = logger.read_logs(
    action="create_invoice",
    start_date="2026-03-01",
    end_date="2026-03-07",
    level="error"
)

# Compliance report
report = logger.generate_compliance_report(
    date="2026-03-06",
    include_sensitive=False
)
# Returns: {total_actions, actions_by_type, approval_usage, errors, duration_stats, ...}
```

#### Log Storage

- **Daily files**: `AI_Employee_Vault/Logs/2026-03-08.json`
- **Rotated files**: `2026-03-08_143022.json` (when size exceeds 10MB)
- **Archive**: `AI_Employee_Vault/Logs/archive/` (gzipped older logs)
- **Retention**: 90 days (configurable)
- **Format**: JSON array with comma-separated entries

### 3. Health Monitoring Server (`utils/error_recovery/health_server.py`)

Start with:

```bash
python utils/error_recovery/health_server.py --port 8080 --interval 30
```

**Endpoints:**

| Endpoint | Purpose | Returns 200 if |
|----------|---------|---------------|
| `GET /health` | Overall health | Overall status is `healthy` or `degraded` |
| `GET /health/ready` | Readiness probe | Critical dependencies (Odoo, PostgreSQL) are up |
| `GET /health/live` | Liveness probe | Health server process is running |
| `GET /metrics` | Metrics dump | Always 200 |
| `GET /status` | Detailed component status | Always 200 |

**Response format (`/health`):**

```json
{
  "status": "healthy",
  "components": {
    "odoo_mcp": {
      "name": "odoo_mcp",
      "status": "healthy",
      "last_check": "2026-03-08T14:32:00",
      "details": {"http_status": 200, "url": "http://localhost:8069"}
    },
    "social_mcp": {"status": "healthy", ...},
    "postgresql": {"status": "healthy", ...},
    "disk_space": {"status": "healthy", "details": {"free_gb": 45}},
    "memory": {"status": "healthy", "details": {"percent": 65}}
  },
  "timestamp": "2026-03-08T14:33:00",
  "uptime_seconds": 3600
}
```

**Monitored components:**

- `odoo_mcp`: HTTP check on `http://localhost:8069/web`
- `social_mcp`: Process check (psutil)
- `gmail_watcher`, `whatsapp_watcher`, `scheduler`: Process checks
- `postgresql`: TCP connection test (localhost:5432, user: odoo, db: odoo)
- `disk_space`: Free space check (<5GB = unhealthy, <10GB = degraded)
- `memory`: RAM usage (>95% = unhealthy, >85% = degraded)

**Integration:**

- **Kubernetes**: Use `/health/ready` and `/health/live` for probes
- **Proxmox**: Watchdog script can call `/health` and restart container if status != `healthy`
- **Grafana/Datadog**: Scrape `/metrics` endpoint

## Integration into MCP Servers

### Pattern Used

Both `odoo-mcp` and `social-mcp` now include:

1. **Audit Logging**: Every tool call logs success or failure
2. **Circuit Breakers**: Per-API/platform (e.g., `facebook_api`, `odoo_odoo`)
3. **Retry Logic**: 3 attempts with exponential backoff (2^attempt seconds)
4. **Error Recovery**: Automatic retry on transient failures (connection errors, 5xx)

### Example: Social Media MCP

```python
# In call_tool handler:
start_time = time.time()
try:
    result = self._facebook_post(**arguments)
    duration_ms = int((time.time() - start_time) * 1000)
    log_audit(actor="social-mcp", action="facebook_post", ...)
    return result
except Exception as e:
    duration_ms = int((time.time() - start_time) * 1000)
    log_audit(actor="social-mcp", action="facebook_post", error=str(e), ...)
    raise
```

Each method (`_facebook_post`, `_twitter_tweet`, etc.) uses:

```python
breaker = self._get_circuit_breaker("facebook")
for attempt in range(3):
    try:
        if breaker.state.value == "open":
            raise Exception("Circuit breaker OPEN")
        result = breaker.call(do_request)
        return result
    except requests.exceptions.RequestException as e:
        if attempt == 2: raise
        time.sleep(min(2 ** attempt, 60))  # Backoff
```

### Example: Odoo MCP

All XML-RPC calls use `_call_odoo_with_retry()`:

```python
def _call_odoo_with_retry(self, model: str, method: str, args: List, max_attempts=3):
    breaker = self._get_circuit_breaker("odoo")
    def do_call():
        return self.models.execute_kw(ODOO_DB, self.uid, ODOO_PASSWORD, model, method, args)
    if breaker:
        return breaker.call(do_call)
    return do_call()
```

Replaces all direct `self.models.execute_kw(...)` calls.

## Configuration

### Circuit Breaker Thresholds

Edit `mcp-servers/*/server.py`:

```python
_breakers["facebook"] = CircuitBreaker(
    name="facebook_api",
    failure_threshold=5,    # Open after 5 consecutive failures
    recovery_timeout=60,    # Wait 60s before half-open
    success_threshold=3,    # 3 successes to close from half-open
    expected_exceptions=(ConnectionError, requests.exceptions.RequestException)
)
```

### Retry Settings

```python
max_attempts = 3
delay = min(2 ** attempt, 60)  # Exponential backoff, max 60s
```

### Log Retention

In `utils/audit/logger.py` initialization:

```python
logger = AuditLogger(
    log_dir="AI_Employee_Vault/Logs",
    retention_days=90,       # Keep logs 90 days
    rotation_days=1,         # Daily rotation
    max_bytes=10*1024*1024,  # 10MB per file
    archive_dir="AI_Employee_Vault/Logs/archive"
)
```

## Testing Error Recovery

### Test 1: Simulate API Failure

```bash
# Temporarily block Facebook API
sudo iptables -A OUTPUT -d graph.facebook.com -j DROP

# Try posting via MCP
python test_connection.py
# Should retry 3 times, then fail

# View circuit breaker state
python -c "from utils.error_recovery.retry_circuit import get_all_circuit_stats; print(get_all_circuit_stats())"

# Should show: "facebook_api": {"state": "open", "failure_count": 3}

# Unblock API
sudo iptables -D OUTPUT -d graph.facebook.com -j DROP

# Circuit stays open for 60s, then transitions to HALF_OPEN
# Next successful call closes circuit
```

### Test 2: Audit Logging

```bash
# Generate some activity
python test_connection.py

# View logs
ls AI_Employee_Vault/Logs/*.json

# Query specific action
python -c "
from utils.audit.logger import get_audit_logger
logger = get_audit_logger()
entries = logger.read_logs(action='facebook_post', limit=5)
for e in entries:
    print(f\"{e.timestamp} {e.actor} {e.action} {e.target} {e.duration_ms}ms\")
"

# Compliance report
report = logger.generate_compliance_report(date='yesterday')
print(report['actions_by_type'])
print(report['errors'])
```

### Test 3: Health Monitoring

```bash
# Start health server
python utils/error_recovery/health_server.py --port 8080 --interval 10 &

# Check endpoints
curl http://localhost:8080/health
curl http://localhost:8080/metrics
curl http://localhost:8080/status

# All should return 200 if Odoo is running
```

## Deployment

### As part of the vault:

1. **Start health monitor** (background):
   ```bash
   nohup python utils/error_recovery/health_server.py > health.log 2>&1 &
   echo $! > utils/error_recovery/health_server.pid
   ```

2. **Start MCP servers** via Claude Code (automatic when Claude invokes tools) or manually:
   ```bash
   # In separate terminals/processes
   python mcp-servers/odoo-mcp/server.py &
   python mcp-servers/social-mcp/server.py &
   ```

3. **Watchdog integration** (Proxmox/LXC):
   ```bash
   # /etc/cron.d/ai-employee-health
   */5 * * * * curl -s http://localhost:8080/health | grep -q '"status":"healthy"' || systemctl restart ai-employee
   ```

### Kubernetes Deployment (future)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ai-employee
spec:
  containers:
  - name: odoo-mcp
    image: ai-employee:latest
    command: ["python", "mcp-servers/odoo-mcp/server.py"]
    readinessProbe:
      exec:
        command: ["curl", "-f", "http://localhost:8080/health/ready"]
      initialDelaySeconds: 30
      periodSeconds: 10
    livenessProbe:
      exec:
        command: ["curl", "-f", "http://localhost:8080/health/live"]
      initialDelaySeconds: 60
      periodSeconds: 30
```

## Diagnostics

### View Circuit Breaker Stats

```python
from utils.error_recovery.retry_circuit import get_all_circuit_stats
stats = get_all_circuit_stats()
# {'facebook_api': {'state': 'closed', 'failure_count': 0, ...}}
```

### Check Audit Logs

```bash
# Today's logs
tail -f AI_Employee_Vault/Logs/$(date +%Y-%m-%d).json

# Errors in last hour
grep -i error AI_Employee_Vault/Logs/$(date +%Y-%m-%d).json | tail -20

# Count actions by type
jq -r '.action' AI_Employee_Vault/Logs/2026-03-08.json | sort | uniq -c
```

### Health Server Logs

```bash
tail -f health.log
# Shows periodic component checks and state changes
```

## Known Limitations

1. **Circuit breaker metrics**: Only available in-memory; lost on restart. For persistence, consider Redis or PostgreSQL.
2. **Audit log format**: Simple JSON array; no binary format or compression (yet).
3. **Health check granularity**: Some checks are process-based, not HTTP (social-mcp, watchers). Could add IPC-based liveness check.
4. **Rate limiting**: Twitter rate limits handled via wait-for-reset but don't track limit counters proactively.
5. **Thread safety**: AuditLogger uses `threading.RLock` but not async-safe. Ensure MCP servers run in single-threaded mode (they do currently).

## Next Steps (Phase 4)

- Implement auto-retry in Claude Code's tool invocations (not just MCP servers)
- Add Prometheus metrics exporter (replace custom `/metrics`)
- Persist circuit breaker state to Redis for multi-instance deployments
- Alerting integration (Slack/Discord webhooks on component failures)
- Audit log encryption at rest (AES-256) for HIPAA/SOX compliance
- Automatic log archival to S3/object storage

## Checklist

- [x] Circuit breaker implementation with CLOSED/OPEN/HALF_OPEN states
- [x] Retry decorator with exponential backoff and jitter
- [x] Structured audit logging with AuditEntry schema
- [x] Daily log rotation with size-based fallback and gzip archival
- [x] Query interface for audit logs (filter by date, action, actor, level)
- [x] Compliance report generation (actions by type, approval usage, errors)
- [x] HTTP health server with Kubernetes-style probes
- [x] Component health checks (odoo_mcp, social_mcp, postgresql, disk, memory)
- [x] Integration: audit logging in both MCP servers
- [x] Integration: retry/circuit breaker in both MCP servers
- [ ] Integration: automatic health server startup (script/init system)
- [ ] Testing: Simulate failures and verify retry/circuit breaker
- [ ] Testing: Verify audit logs written for all operations
- [ ] Testing: Health endpoints return correct status
- [ ] Documentation: Update README.md with Phase 3 setup instructions
- [ ] Documentation: Create troubleshooting guide for error recovery

---

**Status**: Phase 3 complete (coding), pending testing and health server launcher script.
