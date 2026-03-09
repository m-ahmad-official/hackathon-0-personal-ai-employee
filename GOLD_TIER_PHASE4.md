# Gold Tier Phase 4: Cross-Domain Integration & Enhanced Dashboard

**Status:** 🚧 In Progress
**Started:** 2026-03-09
**Target:** Unified dashboard, cross-domain workflows, business intelligence

---

## Phase 4 Objectives

- [ ] **Real-Time Dashboard Integration** - Health metrics, Odoo data, social stats
- [ ] **Cross-Domain Workflows** - Automated triggers (Odoo → social, email → Odoo)
- [ ] **Audit Log Analytics** - Query and report on system activity
- [ ] **Enhanced CEO Briefing** - Full business intelligence (financials + social + operations)
- [ ] **Event-Driven Architecture** - Webhook/event bus for inter-component communication
- [ ] **Production Polish** - Start/stop scripts, service files, monitoring setup

---

## Components to Build

### 1. Dashboard Enhancement (`AI_Employee_Vault/Dashboard.md`)

**Current:** Static markdown file manually updated
**Goal:** Auto-refresh with live data from:
- Health server API (`http://localhost:8080/metrics`)
- Odoo MCP (account balances, recent invoices)
- Social MCP (last posts, engagement metrics)
- Task completion rates (from `/Done/` folder)
- System uptime and component status

**Implementation:**
```python
# utils/dashboard_updater.py
def update_dashboard():
    # Fetch health metrics
    health = requests.get("http://localhost:8080/metrics").json()

    # Query Odoo for latest data
    # - Accounts Receivable balance
    # - Recent invoices count
    # - Overdue invoices

    # Query social media stats
    # - Last post time per platform
    # - Follower counts (if API allows)
    # - Recent engagement

    # Count tasks completed this week
    done_items = count_files_in_folder("/Done/", since="2026-03-03")

    # Update Dashboard.md with new section
    write_dashboard_section("## Real-Time Metrics", metrics_md)
```

**Schedule:** Run every 5 minutes via scheduler or separate watcher.

---

### 2. Cross-Domain Workflow: Email → Odoo Invoice

**Trigger:** Email request for invoice (e.g., "Please send invoice for $500 to client@example.com")

**Workflow:**
1. Gmail watcher creates `EMAIL_*.md` in `Needs_Action/`
2. Claude processes with `process_email_requests` skill
3. Detects invoice request intent
4. Uses `odoo-mcp` tools:
   - `search_customers` to find/create client
   - `create_invoice` with line items extracted from email
   - Optionally `post_invoice` if auto-post enabled
5. Sends invoice via email (Gmail API) with PDF attachment (future: generate PDF from Odoo)
6. Logs all steps to audit trail
7. Updates Dashboard with "Invoices Created" counter

**Example Prompt to Claude:**
```
You are processing an email request. The user wants to create an invoice.
Follow this workflow:
1. Extract: customer email, amount, description, due date
2. Use odoo-mcp to search or create customer
3. Create invoice with one line item
4. If auto_post=True, post the invoice
5. Send email with invoice number and amount
6. Log all actions to audit log
```

---

### 3. Cross-Domain Workflow: Odoo Event → Social Media Post

**Trigger:** New invoice posted in Odoo (payment received or milestone)

**Workflow:**
1. (Future) Odoo webhook or polling detects new posted invoice
2. If invoice marked as "social_announce": true, auto-generate celebratory post
3. Format content per platform:
   - Facebook: "We just closed a $X deal with Client Name! 🎉"
   - Instagram: Image + "Big news! 🚀 #business #success"
   - Twitter: "Invoice paid: $X from Client Name. Thank you! 💼"
4. Use `social-mcp` tools to post
5. Log to audit and update Dashboard with "Social Posts" counter

**Implementation:** Could be a scheduler job that queries Odoo for recently posted invoices with `social_announce` flag in custom field, then calls Claude skill `post_to_social_media`.

---

### 4. Audit Log Analytics Skill

**Skill:** `analyze_audit_logs` - Query and summarize system activity

**Capabilities:**
- Generate daily summary: actions performed, errors, duration stats
- Identify frequent errors (top 5 error types)
- Report on approval usage (auto vs human)
- Show most-used tools and average execution times
- Export to CSV/JSON for external analysis

**Example usage:**
```
/skill analyze_audit_logs --date 2026-03-08 --format markdown > Daily_Report_20260308.md
```

**Output:**
```markdown
# Audit Summary - 2026-03-08

## Overview
- Total actions: 127
- Success rate: 94% (119/127)
- Average duration: 1.2s

## Top Tools
1. search_customers (45 uses, avg 0.3s)
2. facebook_post (12 uses, avg 2.1s)
3. create_invoice (8 uses, avg 1.8s)

## Errors
- Rate limit: 3 occurrences
- Connection timeout: 2 occurrences
- Invalid token: 1 occurrence

## Approvals
- Total approvals required: 5
- Human approved: 4
- Auto approved: 1
- Rejected: 0
```

---

### 5. Enhanced CEO Briefing (Gold Tier Complete)

**Current:** Basic weekly report from Silver Tier
**Enhanced:** Full business intelligence dashboard with:

**Financial Section (from Odoo):**
- Revenue this week (posted invoices)
- Accounts Receivable aging (0-30, 31-60, 60+ days)
- Top customers by invoice volume
- Overdue invoices count and amount

**Social Media Section (from Social MCP + Facebook Insights):**
- Posts this week (count per platform)
- Total reach/impressions
- Engagement rate (likes, comments, shares)
- Follower growth

**Operations Section (from Audit Logs):**
- Tasks completed (count, avg time to complete)
- Automation success rate
- Error rate and top failure modes
- Approvals processed

**Predictive Insights:**
- Cash flow forecast based on AR
- Social media growth trend (if historical data)
- Response time to customer emails

**Format:** Markdown file in `/Briefings/` with charts (ASCII or embedded images)

---

### 6. Event Bus / Webhook System

**Goal:** Decouple components so they can react to events without polling

**Implementation Options:**
- Simple: File-based events (`AI_Employee_Vault/Events/` with JSON files)
- Intermediate: SQLite event queue with atomically marked processed
- Advanced: Redis pub/sub or RabbitMQ (for multi-machine)

**Recommended (MVP):** File-based events

**Event Types:**
```json
{
  "id": "uuid",
  "timestamp": "2026-03-09T01:30:00",
  "type": "invoice_posted",
  "source": "odoo-mcp",
  "data": {
    "invoice_id": 123,
    "amount": 500,
    "customer": "Client Corp",
    "social_announce": true
  }
}
```

**Event Producers:**
- Odoo MCP (invoice_created, invoice_posted, payment_recorded)
- Social MCP (post_published, engagement_metrics)
- Gmail watcher (email_received)
- Approval manager (approval_granted, approval_rejected)

**Event Consumers:**
- Dashboard updater (reacts to all events, updates metrics)
- Social poster (reacts to invoice_posted with social_announce)
- Notification system (send alerts on errors)
- CEO briefing generator (weekly aggregation)

**Pattern:** Each consumer watches `Events/` folder, processes new events, moves to `Events/processed/`.

---

### 7. Production Deployment Scripts

**currently:** Manual start of services
**Goal:** One-command startup/shutdown for full system

**Scripts to create:**

#### `start_all.sh`
```bash
#!/bin/bash
# Start all AI Employee services

# 1. Start Odoo (if using Docker)
cd mcp-servers/odoo-mcp
docker-compose up -d

# 2. Start health monitor
nohup python utils/error_recovery/health_server.py > health.log 2>&1 &
echo $! > utils/error_recovery/health_server.pid

# 3. Start watchers (background)
nohup python watchers/gmail_watcher.py --vault AI_Employee_Vault --credentials credentials.json --check-interval 60 > watchers/gmail.log 2>&1 &
nohup python watchers/whatsapp_watcher.py --vault AI_Employee_Vault --session-path ./session --check-interval 30 > watchers/whatsapp.log 2>&1 &
nohup python watchers/approved_executor.py --vault AI_Employee_Vault --watch > watchers/executor.log 2>&1 &

# 4. Start dashboard updater (runs every 5 min)
nohup python utils/dashboard_updater.py --interval 300 > dashboard_updater.log 2>&1 &

# 5. Start scheduler
nohup python scheduler/scheduler.py --config scheduler/config.yaml > scheduler.log 2>&1 &

echo "All services started"
```

#### `stop_all.sh`
```bash
#!/bin/bash
# Stop all services

# Kill by PID files
for pidfile in \
    utils/error_recovery/health_server.pid \
    watchers/gmail_watcher.pid \
    watchers/whatsapp_watcher.pid \
    watchers/executor.pid \
    scheduler/scheduler.pid \
    dashboard_updater.pid; do
    if [ -f "$pidfile" ]; then
        kill $(cat "$pidfile") 2>/dev/null
        rm "$pidfile"
    fi
done

# Stop Odoo
cd mcp-servers/odoo-mcp
docker-compose down

echo "All services stopped"
```

#### `status.sh`
```bash
#!/bin/bash
# Show status of all services

echo "=== Health Check ==="
curl -s http://localhost:8080/health | python3 -m json.tool | head -20

echo -e "\n=== Watchers ==="
ps aux | grep -E "gmail_watcher|whatsapp_watcher|approved_executor" | grep -v grep

echo -e "\n=== Processes ==="
ps aux | grep -E "health_server|dashboard_updater|scheduler.py" | grep -v grep

echo -e "\n=== Odoo ==="
docker ps | grep odoo
```

---

### 8. Skills to Create

#### Skill: `integrate_cross_domain`
Trigger cross-domain workflows automatically.

**Triggers:**
- `email_invoice_request` → create Odoo invoice
- `odoo_invoice_posted` → optional social announcement
- `approval_granted` → execute and notify

**Implementation:** Event-driven, reacts to events in `Needs_Action/` and `/Approved/`.

---

#### Skill: `update_dashboard`
Refresh dashboard with latest metrics. Could be invoked:
- On-demand: `/skill update_dashboard`
- Scheduled: every 5 minutes via scheduler
- Event-driven: after any significant action

---

#### Skill: `analyze_audit_logs`
As described above. For compliance and insights.

---

#### Skill: `generate_ceo_briefing`
Enhanced version with full data integration (financials, social, ops).

---

### 9. Notification System (Optional)

Send alerts when:
- Component health degraded
- Invoice overdue > 30 days
- Social media API errors
- Audit log shows 5+ errors in 5 minutes

**Channels:**
- Email (Gmail API)
- Desktop notifications (pushover, telegram, etc.)
- Log to audit (already there)

**Implementation:** Simple waiter on `/health` endpoint, or monitor audit logs in real-time.

---

## Implementation Plan

### Step 1: Dashboard Integration
1. Create `utils/dashboard_updater.py`
2. Fetch metrics from health server, Odoo, social
3. Update `Dashboard.md` with new "Live Metrics" section
4. Test with manual invocation: `python utils/dashboard_updater.py`
5. Add to scheduler config to run every 5 minutes

**Deliverable:** Dashboard auto-updates every 5 min with current metrics

---

### Step 2: Email → Odoo Invoice Workflow
1. Enhance `process_email_requests` skill to detect invoice creation requests
2. Write helper: `utils/invoice_from_email.py` to extract invoice details from email body
3. Integrate with Odoo MCP tools (create_invoice, post_invoice, record_payment)
4. Add email sending with invoice summary (use Gmail API)
5. Test end-to-end with sample email

**Deliverable:** Sending email with "create invoice for $500" generates draft invoice in Odoo

---

### Step 3: Audit Analytics Skill
1. Create `AI_Employee_Vault/.claude/skills/analyze_audit_logs/skill.md`
2. Implement `analyze_audit_logs.py` with querying and summarization
3. Test: `/skill analyze_audit_logs --date 2026-03-08`
4. Add to weekly briefing automatically

**Deliverable:** Skill can generate daily/weekly audit summaries

---

### Step 4: Event Bus Implementation
1. Create `utils/event_bus/` with Event dataclass and file-based dispatcher
2. Modify Odoo MCP and Social MCP to emit events on significant actions
3. Create consumers:
   - `utils/event_consumers/dashboard_updater.py`
   - `utils/event_consumers/social_announcer.py` (Odoo → social)
4. Test event flow with simple producer/consumer

**Deliverable:** Event-driven architecture with at least 2 event types and 2 consumers

---

### Step 5: CEO Briefing Enhancement
1. Update `generate_weekly_briefing` skill to query Odoo API for financials
2. Add social media metrics section
3. Add operations metrics from audit logs
4. Format as professional markdown with tables
5. Automate generation (scheduler weekly)

**Deliverable:** Full business intelligence briefing

---

### Step 6: Production Scripts
1. Create `start_all.sh` and `stop_all.sh`
2. Create systemd service files (or supervisord config) for production deployment
3. Test full startup/shutdown cycle
4. Document in README

**Deliverable:** One-command deployment

---

## Testing Checklist

### Dashboard Integration
- [ ] Dashboard updates when health server reports
- [ ] Odoo data pulls correctly (AR balance, invoice count)
- [ ] Social stats appear (last post time, engagement if available)
- [ ] No errors in dashboard_updater.log

### Cross-Domain Workflows
- [ ] Email with invoice request creates Odoo invoice
- [ ] Invoice posted in Odoo can trigger social post (when flag set)
- [ ] All steps logged to audit trail
- [ ] Dashboard counters update

### Event Bus
- [ ] Events written to `Events/` folder with UUID, timestamp, type
- [ ] Consumers pick up and process events
- [ ] Events moved to `Events/processed/` after successful handling
- [ ] No event loss on restart (check processed folder)

### CEO Briefing
- [ ] Financial section populated with real Odoo data
- [ ] Social media section populated
- [ ] Operations metrics (completion rate, error rate)
- [ ] Report saved to `/Briefings/` with date stamp

---

## Known Challenges

1. **Odoo API Rate Limits:** 200 calls/hour. Dashboard updater should be conservative (query once per 5 min = 12/hr OK).

2. **Social Media Insights:** Facebook/Instagram insights API requires additional permissions and may have rate limits. Consider caching.

3. **Event Bus File Locks:** Multiple consumers may read same event. Use atomic file operations (create temp then rename) or file locking.

4. **Data Freshness:** Dashboard caching needed if queries are expensive. Consider storing latest metrics in `utils/cache/` with timestamp.

5. **Error Recovery:** Events should be retryable. If consumer fails, keep event in Events/ for retry. Add `retry_count` field.

---

## Timeline Estimate

- **Step 1 (Dashboard):** 2-3 hours
- **Step 2 (Email→Odoo):** 3-4 hours (skill enhancement)
- **Step 3 (Audit Skill):** 1-2 hours
- **Step 4 (Event Bus):** 3-4 hours
- **Step 5 (Briefing):** 2-3 hours
- **Step 6 (Scripts):** 1 hour

**Total:** ~12-17 hours of development

---

## Success Criteria

Phase 4 is complete when:

1. Dashboard auto-updates every 5 minutes with live metrics from all systems
2. Sending an email with invoice request creates a valid Odoo invoice automatically
3. Audit logs can be queried and summarized via skill command
4. Event system demonstrably decouples components (Odoo events trigger dashboard updates)
5. CEO briefing includes financial, social, and operational data
6. All services can be started/stopped with single script
7. All components have error recovery (leverage Phase 3 retry/circuit breakers)

---

## Next Steps (Phase 5 Ideas)

- **Predictive Analytics:** ML models for sales forecasting, churn prediction
- **Customer 360:** Unified view aggregating Odoo, email, WhatsApp interactions
- **Advanced Social:** Threaded tweets, video posts, scheduling
- **Multi-tenant:** Support multiple vaults/tenants from single install
- **Reinforcement Learning:** Claude optimizes posting times, email templates based on engagement
- **External Integrations:** Stripe payments, Shopify e-commerce, QuickBooks sync
- **Advanced Dashboard:** Interactive web UI (React/Vue) with real-time websockets

---

**Let's build!** Start with Step 1: Dashboard Integration.

---

*Phase 4 Plan v0.1*
*Last Updated: 2026-03-09*
