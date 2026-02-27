# Silver Tier Watchers

These scripts provide external integration for the AI Employee system.

---

## 📧 Gmail Watcher

Monitors Gmail for important unread emails and creates action items.

### Setup

1. **Enable Gmail API**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project or select existing
   - Enable "Gmail API"
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
   - Application type: **Desktop app**
   - Download credentials JSON
   - Rename to `credentials.json` and place in secure location

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **First run** (authorization):
   ```bash
   python watchers/gmail_watcher.py \
     --vault AI_Employee_Vault \
     --credentials /path/to/credentials.json
   ```
   This will open a browser window for you to authorize access. After successful auth, `token.json` will be created.

4. **Run as daemon**:
   ```bash
   # Using PM2 (recommended for production)
   pm2 start watchers/gmail_watcher.py --interpreter python3 -- --vault AI_Employee_Vault --credentials /path/to/credentials.json

   # Or using nohup
   nohup python watchers/gmail_watcher.py --vault AI_Employee_Vault --credentials /path/to/credentials.json > gmail_watcher.log 2>&1 &
   ```

### Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--vault` | (required) | Path to AI_Employee_Vault |
| `--credentials` | (required) | Path to OAuth credentials.json |
| `--check-interval` | 120 | Check interval in seconds |

### What it does

1. Checks Gmail every 2 minutes (configurable)
2. Finds unread emails marked as IMPORTANT
3. Creates action item in `/Needs_Action/EMAIL_<subject>_<timestamp>.md`
4. Marks message as processed (avoids duplicates)
5. Logs all activity to `gmail_watcher.log`

### Filtering

Currently uses Gmail search query: `is:unread is:important`

To customize, modify line 130 in `gmail_watcher.py`:
```python
query = 'is:unread is:important'  # Change this
```

---

## 📱 WhatsApp Watcher

Monitors WhatsApp Web for new messages using Playwright.

### Setup

1. **Install Playwright**:
   ```bash
   pip install playwright
   playwright install chromium
   ```

2. **Prepare WhatsApp Web session**:
   - First run will open Chrome
   - Scan QR code with your phone
   - Session is saved to `./session` (or custom path)
   - Subsequent runs use saved session (no QR needed)

3. **Run the watcher**:
   ```bash
   python watchers/whatsapp_watcher.py \
     --vault AI_Employee_Vault \
     --session-path ./session
   ```

4. **Run as daemon** (background):
   ```bash
   # Note: Must run non-headless (headless=False) for WhatsApp Web
   # Use screen/tmux or PM2 with appropriate config

   pm2 start watchers/whatsapp_watcher.py --interpreter python3 -- \
     --vault AI_Employee_Vault \
     --session-path ./session
   ```

### Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--vault` | (required) | Path to AI_Employee_Vault |
| `--session-path` | `./session` | Browser session storage (persistent login) |
| `--check-interval` | 30 | Check interval in seconds |

### How it works

1. Launches Chromium with persistent user data (keeps WhatsApp login)
2. Navigates to https://web.whatsapp.com
3. Waits for chat list to load (verifies login)
4. Scans for unread chats (green badges)
5. For each unread chat:
   - Opens the chat
   - Extracts last 10 messages
   - Filters for incoming messages only
   - Creates action item with full conversation
6. Closes browser
7. Sleeps for interval, repeats

### Message Format

Action items created include:
- Contact name
- All incoming messages with timestamps
- Urgent keyword detection (urgent, asap, invoice, payment, help, important, emergency)
- Priority flag (high/medium)
- Suggested actions

---

## 🔧 Testing

### Test Gmail Watcher (dry-run mode not implemented yet)

```bash
# Run once and exit (modify code to add single-run mode)
timeout 1 python watchers/gmail_watcher.py --vault AI_Employee_Vault --credentials credentials.json
```

### Test WhatsApp Watcher

```bash
# Will scan once and exit (you need to add a run_once() method)
# Currently runs continuously. Use Ctrl+C to stop.
python watchers/whatsapp_watcher.py --vault AI_Employee_Vault --session-path ./session
```

---

## 📁 Output Structure

Both watchers create files in `AI_Employee_Vault/Needs_Action/`:

```
Needs_Action/
├── EMAIL_<subject>_<timestamp>.md
├── WHATSAPP_<contact>_<timestamp>.md
└── ...
```

Each action item includes:
- YAML frontmatter with metadata
- Clear description of the item
- Suggested actions (checkboxes)
- Priority level
- Timestamp

---

## 🔒 Security Notes

- **credentials.json** and **token.json** contain OAuth tokens. Keep them secure!
- Add to `.gitignore`:
  ```gitignore
  credentials.json
  token.json
  session/
  ```
- Use environment variables for credential paths in production
- Never share or commit Google OAuth credentials

---

## 🐛 Troubleshooting

### Gmail Watcher

| Issue | Solution |
|-------|----------|
| `ImportError: No module named google...` | Install deps: `pip install google-api-python-client` |
| `Invalid credentials` | Delete `token.json` and re-run to re-authorize |
| `403 Forbidden` | Check Gmail API enabled in Google Cloud Console |
| `No emails detected` | Verify you have unread emails marked as IMPORTANT in Gmail |
| `token.json not created` | Ensure you can open browser for OAuth flow; use `--no-auth-local-ports` if needed |

### WhatsApp Watcher

| Issue | Solution |
|-------|----------|
| `Playwright not installed` | Run: `pip install playwright && playwright install chromium` |
| `Not logged in` | Delete `session/` folder and re-run, scan QR code |
| `Chat list not found` | WhatsApp Web UI changed - update selectors |
| `Browser crashes` | Try reducing `--check-interval` or check Chrome version |
| `Headless mode doesn't work` | WhatsApp Web **requires** visible browser (headless=False) |

---

## 📊 Logging

Both watchers log to:
- `gmail_watcher.log` (for Gmail)
- `whatsapp_watcher.log` (for WhatsApp)
- Also output to stdout/stderr

Logs include:
- Start/stop events
- Detected items
- Errors and exceptions
- Authentication status

---

## 🔄 Integration with Claude

Once action items are created in `/Needs_Action/`, Claude Code can:

1. Read the files
2. Understand the context
3. Create execution plans
4. Execute via MCP servers (email, etc.)
5. Update dashboard and move to `/Done/`

---

## 🎯 Silver Tier Completion Checklist

- [ ] Gmail watcher installed and authenticated
- [ ] WhatsApp watcher installed and session created
- [ ] Both watchers running continuously
- [ ] Test email received and processed
- [ ] Test WhatsApp message received and processed
- [ ] Action items created in `/Needs_Action/`
- [ ] No duplicate processing
- [ ] Logs rotating properly

---

## Next Steps

After watchers are working:
1. Create **Email MCP Server** to actually send emails
2. Create **LinkedIn Auto-Poster** skill
3. Implement **Approval Workflow** skill
4. Add **Scheduled Tasks** integration
5. Document everything in READMEs

---

*Version: 1.0-Silver*
*Last Updated: 2026-02-24*
