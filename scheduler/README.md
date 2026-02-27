# Scheduler - Silver Tier

Cron-based scheduling system for AI Employee automated workflows.

---

## 📋 Overview

The scheduler enables time-based automation of AI Employee tasks:

- ✅ **Cron expressions** - Standard scheduling syntax
- ✅ **Multiple triggers** - Run skills, commands, or orchestrator
- ✅ **Flexible configuration** - YAML-based, easy to edit
- ✅ **Daemon mode** - Continuous background operation
- ✅ **Logging** - Full audit trail of scheduled executions
- ✅ **Error handling** - Timeouts, retries, alerts

---

## 🚀 Quick Start

### 1. Install PyYAML

```bash
pip install pyyaml
```

### 2. Configure Schedule

Edit `scheduler/config.yaml`:

```yaml
default_working_dir: AI_Employee_Vault
check_interval: 60

tasks:
  - name: "morning_processing"
    schedule:
      minute: "0"
      hour: "9"      # 9:00 AM daily
      day: "*"
      month: "*"
      weekday: "*"
    action:
      type: "orchestrator"
      vault: "AI_Employee_Vault"
```

### 3. Test Configuration

```bash
# Test config syntax
python scheduler/scheduler.py --config scheduler/config.yaml --once

# Expected: Shows tasks due now and exits
```

### 4. Run as Daemon

```bash
# Terminal 1: Start daemon
python scheduler/scheduler.py --config scheduler/config.yaml --daemon

# You'll see: "Scheduler daemon started, checking every 60 seconds"
```

### 5. Add to System Startup (Optional)

**Using crontab (simpler):**
```bash
# Add to crontab with `crontab -e`
@reboot cd /path/to/vault && python scheduler/scheduler.py --config scheduler/config.yaml --daemon >> scheduler/scheduler.log 2>&1
```

**Using systemd** (advanced, more robust):
Create `/etc/systemd/system/ai-employee-scheduler.service` (see below).

---

## 📅 Cron Syntax

The scheduler uses standard cron fields:

```
┌───────── minute (0 - 59)
│ ┌─────── hour (0 - 23)
│ │ ┌───── day of month (1 - 31)
│ │ │ ┌─── month (1 - 12)
│ │ │ │ ┌─ day of week (0 - 6) (Sunday=0 or 7)
│ │ │ │ │
* * * * *
```

**Examples:**

| Cron | Description |
|------|-------------|
| `* * * * *` | Every minute |
| `*/5 * * * *` | Every 5 minutes |
| `0 */2 * * *` | Every 2 hours |
| `0 9 * * *` | Daily at 9:00 AM |
| `30 14 * * 1` | Monday at 2:30 PM |
| `0 0 * * 0` | Sunday at midnight |
| `0 9-17 * * 1-5` | Weekdays 9 AM - 5 PM hourly |

---

## ⚙️ Task Configuration

Each task in `config.yaml` has:

```yaml
- name: "task_name"                    # Unique identifier
  schedule:                            # Cron-like dict
    minute: "0"
    hour: "9"
    day: "*"
    month: "*"
    weekday: "*"
  action:                              # What to execute
    type: "orchestrator" | "claude_skill" | "command"
    vault: "AI_Employee_Vault"        # For orchestrator/skills
    skill: "process_needs_action"     # For claude_skill
    arguments: ["--all"]              # For claude_skill
    command: "python script.py"       # For command
    working_dir: "."                  # Working directory
```

---

## 🔧 Action Types

### 1. Orchestrator

Runs the main orchestrator to process all pending tasks.

```yaml
action:
  type: "orchestrator"
  vault: "AI_Employee_Vault"
```

**Equivalent CLI:** `python orchestrator.py --vault AI_Employee_Vault --process-now`

---

### 2. Claude Skill

Executes an Agent Skill via Claude Code.

```yaml
action:
  type: "claude_skill"
  skill: "process_email_requests"
  arguments: ["--all", "--dry-run"]  # Optional
  working_dir: "AI_Employee_Vault"
```

**Equivalent CLI:** (inside vault) `claude . -c "/skill process_email_requests --all"`

**Note:** Requires Claude Code to be installed and in PATH.

---

### 3. Command

Runs arbitrary shell command.

```yaml
action:
  type: "command"
  command: "ls -la AI_Employee_Vault/Done/"
  working_dir: "."
```

**Equivalent CLI:** `cd . && ls -la AI_Employee_Vault/Done/`

---

## 📊 Default Schedule

The provided `config.yaml` includes:

| Task | Schedule | Action |
|------|----------|--------|
| `process_needs_action_morning` | Daily 9:00 AM | Orchestrator |
| `process_needs_action_evening` | Daily 6:00 PM | Orchestrator |
| `health_check_gmail_watcher` | Every 30 min | Check if watcher running |
| `weekly_briefing_monday` | Monday 8:00 AM | `generate_weekly_briefing` skill |
| `update_dashboard_midnight` | Daily midnight | `update_dashboard` skill |
| `check_urgent_emails` | Hourly | `process_email_requests --all` |
| `linkedin_post_quarterly` | Every 4 hours | `linkedin_auto_poster --create-post` |
| `cleanup_logs_weekly` | Sunday 2:00 AM | Delete logs older than 30 days |

You can customize by editing `config.yaml`.

---

## 🐛 Monitoring & Logs

### View Scheduler Log

```bash
tail -f scheduler.log
```

Log shows:
- When scheduler checks tasks
- Which tasks are due
- Execution results (success/failure)
- Errors and timeouts

### Check Task History

The scheduler doesn't persist history (for that, see logs). To track:

```bash
grep "Task due:" scheduler/logs/scheduler.log
```

---

## 🔄 Integration with Orchestrator

The scheduler triggers the orchestrator, which:
1. Checks `/Needs_Action/` for pending items
2. Invokes appropriate Agent Skills
3. Executes plans
4. Updates Dashboard
5. Logs all actions

**Workflow:**
```
Scheduler (cron)
  ↓ runs at 9:00 AM
Orchestrator
  ↓ processes all Needs_Action
Agent Skills (email, whatsapp, etc.)
  ↓ execute via MCP
Done/ + Dashboard updated
```

---

## 🛠️ Running as Systemd Service (Linux)

Create `/etc/systemd/system/ai-employee-scheduler.service`:

```ini
[Unit]
Description=AI Employee Scheduler
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/vault
ExecStart=/usr/bin/python3 /path/to/vault/scheduler/scheduler.py --config scheduler/config.yaml --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-employee-scheduler
sudo systemctl start ai-employee-scheduler
sudo systemctl status ai-employee-scheduler
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| No tasks executing | Check `--config` path, verify tasks defined |
| Scheduler not starting | Install pyyaml: `pip install pyyaml` |
| Cron expressions not matching | Use online cron tester to verify syntax |
| Task fails repeatedly | Check logs, test command manually |
| Daemon won't stop | `pkill -f scheduler.py` or kill process |

---

## 📈 Monitoring Tasks

Add a health check task:

```yaml
- name: "heartbeat"
  schedule:
    minute: "*/10"
    hour: "*"
    day: "*"
    month: "*"
    weekday: "*"
  action:
    type: "command"
    command: "date > AI_Employee_Vault/Logs/scheduler_heartbeat.txt"
    working_dir: "."
```

Then monitor:
```bash
tail -f AI_Employee_Vault/Logs/scheduler_heartbeat.txt
```

---

## 🔐 Security

- Scheduler runs with user permissions only
- No external network access required
- All actions are logged for audit
- Time-based execution prevents overlap (won't run same task twice within interval)

---

## 🎯 Silver Tier Completion

This scheduler fulfills Silver Tier requirement #7:
> Basic scheduling via cron or Task Scheduler

It provides:
- ✅ Cron-based scheduling
- ✅ Task configuration via YAML
- ✅ Daemon mode for 24/7 operation
- ✅ Integration with orchestrator and Agent Skills
- ✅ Logging and monitoring
- ✅ Error handling and timeouts

---

## 📚 Advanced Configuration

### Task Dependencies

Currently not supported, but you can sequence by time:

```yaml
# Run B 5 minutes after A
- name: "task_b"
  schedule:
    minute: "5"  # At minute 5
    hour: "9"
    ...
```

### Environment Variables

Set env vars before schedule:

```bash
export PATH=/usr/local/bin:$PATH
python scheduler/scheduler.py --daemon
```

### Email Alerts on Failures

Add post-execution hook (not yet implemented) or check logs via cron.

---

## 🚀 Production Deployment

For production use:

1. **Use virtualenv**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install pyyaml watchdog
   ```

2. **Use systemd** (or PM2 for Node, supervisord for Python)

3. **Monitor logs**:
   ```bash
   journalctl -u ai-employee-scheduler -f
   ```

4. **Set up alerting**:
   - Parse scheduler.log for "failed"
   - Send email on repeated failures

5. **Backup config**:
   - Keep `config.yaml` in git
   - Use separate production config if needed

---

## 🎓 Examples

### Example 1: Run a skill every weekday at 8 AM

```yaml
- name: "daily_briefing"
  schedule:
    minute: "0"
    hour: "8"
    weekday: "1-5"  # Monday-Friday
  action:
    type: "claude_skill"
    skill: "update_dashboard"
    working_dir: "AI_Employee_Vault"
```

### Example 2: Run a shell script with arguments

```yaml
- name: "backup_vault"
  schedule:
    minute: "30"
    hour: "2"
    day: "*"
    month: "*"
    weekday: "*"
  action:
    type: "command"
    command: "tar -czf backup_$(date +%Y%m%d).tar.gz AI_Employee_Vault/"
    working_dir: "."
```

### Example 3: Health check every 10 minutes

```yaml
- name: "orchestrator_health"
  schedule:
    minute: "*/10"
    hour: "*"
  action:
    type: "command"
    command: "python orchestrator.py --vault AI_Employee_Vault --process-now"
    working_dir: "."
```

---

## 📖 References

- [Cron Syntax Guide](https://crontab.guru/)
- Company_Handbook.md - Monitoring & Maintenance (lines 198-216)
- Hackathon: Silver Tier Requirement #7

---

*Scheduler v1.0-Silver*
*Last Updated: 2026-02-24*
