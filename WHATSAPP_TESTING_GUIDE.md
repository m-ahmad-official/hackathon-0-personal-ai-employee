# WhatsApp Watcher - Testing Guide

## What Was Fixed

### 1. Selector Modernization
- **Before**: Relied on `data-testid` attributes which no longer exist on modern WhatsApp Web
- **After**: Uses modern selectors:
  - `[role="grid"]` for chat list container
  - `div[aria-label*="Chat"]` as fallback
  - `[role="row"]` for individual chat items
  - `[role="article"]` for message elements
  - Multiple fallback strategies for robustness

### 2. Unread Detection Logic
- **Before**: Only checked for `[title*="unread"]` which doesn't exist
- **After**: Multi-method detection:
  - Checks `aria-label` for words like "unread", "new", or numbers in parentheses
  - Looks for unread badges/indicators within chat elements
  - Detects small circular icons (unread indicator dots)
  - Extracts unread counts from badge text or aria-labels

### 3. Message Extraction
- **Before**: Relied on `data-testid="msg-text"` and similar
- **After**:
  - Uses `.selectable-text` and `.copyable-text` classes
  - Falls back to getting all text and taking the longest line
  - Detects outgoing messages via `message-out` class
  - Extracts timestamps from `time[datetime]` elements

### 4. Encoding Fix
- **Before**: Log file used system default encoding (Windows: cp1252)
- **After**: Explicit UTF-8 encoding for log file handler
- **Result**: No more `UnicodeEncodeError` when logging emojis or special characters

### 5. Login Timeout
- **Before**: 30 seconds - too short for QR code scanning
- **After**: 60 seconds total (two 20s selector waits)
- **Result**: Gives enough time for manual QR scan

### 6. Single-Run Mode
- **New**: `--single-run` flag for testing
- **Usage**: Run once, create any action files, then exit
- **Benefit**: Easy to test and verify before running continuously

### 7. Improved Error Handling
- Better fallback when persistent context fails (can run in non-persistent mode)
- Graceful handling of missing elements
- Detailed debug logging to understand what's happening
- Traceback logging for unexpected errors

### 8. Robust Button/Close Handling
- Multiple methods to close chat (Escape key + fallback button click)
- Prevents getting stuck in open chat state

---

## How to Test

### Prerequisites
1. Playwright installed and browsers installed:
   ```bash
   pip install playwright
   playwright install chromium
   ```

2. WhatsApp Web accessible (no VPN/blocking)

3. Vault folder exists: `AI_Employee_Vault/` with `Needs_Action/` subfolder

### Test Command

```bash
# From project root (Hackathon 0 folder)
python watchers/whatsapp_watcher.py \
  --vault AI_Employee_Vault \
  --session-path ./session \
  --single-run
```

### Expected Behavior

1. **First Run**:
   - Browser opens to https://web.whatsapp.com
   - If NOT logged in: Show QR code
     - Scan with your phone's WhatsApp
     - Wait for chat list to appear
     - Watcher detects login and proceeds
   - If already logged in (session exists): Go straight to chat list

2. **Detection Phase**:
   - Log shows: "Looking for chat list container..."
   - Log shows: "Found chat list container: [role="grid"]" ✓
   - Log shows: "Found X chat items in list"
   - Log shows: "Found N unread chat(s)" ✓

3. **Processing**:
   - For each unread chat:
     - Log shows: "Extracted M incoming messages from Contact Name"
     - Log shows: "Created action item: AI_Employee_Vault/Needs_Action/WHATSAPP_Contact_YYYYMMDD_HHMMSS.md"

4. **Exit**:
   - Browser closes
   - Script exits (single-run mode)

### Verify Output

Check that a file was created:
```bash
ls AI_Employee_Vault/Needs_Action/WHATSAPP_*.md
```

View the created file:
```bash
cat AI_Employee_Vault/Needs_Action/WHATSAPP_*.md
```

It should contain:
- YAML frontmatter (type, contact, message_count, received, priority, status)
- Message content with timestamps and text
- Suggested actions checklist

---

## Testing Scenarios

### Scenario 1: Fresh Login (No Session)
```bash
# Delete old session if exists
rm -rf ./session
python watchers/whatsapp_watcher.py --vault AI_Employee_Vault --single-run
```
- Browser opens
- Scan QR code
- Wait for chat list to load
- Should detect unread chats (if any) or log "No unread messages"
- Creates session for future use

### Scenario 2: Reuse Existing Session
```bash
python watchers/whatsapp_watcher.py --vault AI_Employee_Vault --single-run
```
- Should NOT show QR code (uses cached session)
- Should log in within a few seconds
- Check for new messages

### Scenario 3: Continuous Mode
```bash
python watchers/whatsapp_watcher.py --vault AI_Employee_Vault --check-interval 60
```
- Runs forever, checking every 60 seconds
- Press Ctrl+C to stop
- Useful for production monitoring

### Scenario 4: WSL / Headless Environment
> **Warning**: WhatsApp Web may not work in WSL due to missing audio/video libraries.
> If you see `libasound.so.2: cannot open shared object file`, you must run on Windows/macOS.

**Workaround**: Use Windows native PowerShell or CMD, not WSL.

---

## Troubleshooting

### Issue: "Not logged in" error persists
**Symptoms**: After scanning QR code, still see "Not logged in after 60s wait!"

**Possible causes**:
1. QR code not fully scanned - ensure phone shows "Connected" notification
2. WhatsApp Web not fully loaded - wait for chat list to be visible before running watcher
3. Browser automation detection - WhatsApp may block Playwright

**Solutions**:
- Manually log in first: Open browser to https://web.whatsapp.com, scan QR, wait for full load
- Then run watcher - it should detect existing session immediately
- Add more launch args if needed: `--disable-infobars`, `--window-size=1200,800`

### Issue: "Found 0 chat items"
**Symptoms**: Log shows "Found 0 chat items in list"

**Possible causes**:
1. Selectors not matching current WhatsApp DOM
2. Chat list container found but elements are nested differently
3. WhatsApp Web version updated

**Solutions**:
- Run `python debug_whatsapp_selectors.py` to see current DOM structure
- Update selectors in `get_unread_chats()` based on findings
- Share output so I can adjust selectors

### Issue: "UnicodeEncodeError" still appears
**Symptoms**: Logging errors with emoji characters in chat messages

**Solution**: Already fixed in this version - encoding set to UTF-8 in FileHandler

### Issue: Browser closes immediately after opening
**Possible causes**:
1. Persistent context path issue
2. Permission issues on session directory
3. WSL missing libraries

**Check**:
```bash
ls -la ./session
# Should be writable
```

If on WSL, switch to Windows native.

### Issue: Action files created but messages are empty
**Possible causes**:
1. Message extraction selectors not matching
2. Message container not found
3. All messages are outgoing (sent by you)

**Solutions**:
- Add more debug logging to see what's being extracted
- Ensure there are actual incoming messages (not just sent messages)
- Check that chat was actually opened (element.click() succeeded)

---

## Debug Mode

To see more detailed output, change log level in the script:

```python
# Line 29-36, change level:
logging.basicConfig(
    level=logging.DEBUG,  # Instead of INFO
    ...
)
```

Or use environment variable:
```bash
export PYTHONLOGLEVEL=DEBUG  # Not automatic, need code change
```

---

## Integration with AI Employee

Once tested and working:

1. **Add as skill**: Create `AI_Employee_Vault/.claude/skills/process_whatsapp_messages/skill.md`

2. **Or run as service**:
   ```bash
   # Start in background
   nohup python watchers/whatsapp_watcher.py --vault AI_Employee_Vault --check-interval 60 > whatsapp.log 2>&1 &
   ```

3. **Or use scheduler**: Add to `scheduler/config.yaml`:
   ```yaml
   tasks:
     - name: "Check WhatsApp"
       schedule: "*/5 * * * *"  # Every 5 minutes
       action:
           type: "command"
           command: "python watchers/whatsapp_watcher.py --vault AI_Employee_Vault --single-run"
   ```

---

## Next Steps After Testing

1. Confirm watcher detects at least 1 unread message and creates file
2. Check the WHATSAPP_*.md file content is correct
3. Test that Claude can process these files (via `/skill process_needs_action`)
4. If needed, adjust selectors based on actual WhatsApp Web DOM

---

## Current Known Limitations

1. **WSL**: Doesn't work due to missing `libasound.so.2` (audio library). Use Windows/macOS.
2. **Message Count**: Only processes last 10 messages per chat (configurable in code)
3. **Attachments**: Only extracts text, not images/files (future enhancement)
4. **Reply Detection**: Based on class names which may change
5. **Continuous Mode**: Browser opens/closes each cycle - could use single long-running session

---

**Ready to test?** Run:

```bash
python watchers/whatsapp_watcher.py --vault AI_Employee_Vault --single-run
```

Send yourself a WhatsApp message first to have an unread chat to detect!
