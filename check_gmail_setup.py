#!/usr/bin/env python3
import json
from pathlib import Path

print("=== Gmail Setup Checker ===\n")

# Check credentials.json exists
creds_path = Path('credentials.json')
if not creds_path.exists():
    print("❌ credentials.json NOT FOUND")
    print("   Download from Google Cloud Console")
else:
    print("✅ credentials.json exists")
    creds = json.loads(creds_path.read_text())
    client_id = creds.get('installed', creds.get('web', {})).get('client_id', 'NOT FOUND')
    project_id = creds.get('installed', creds.get('web', {})).get('project_id', 'NOT FOUND')
    print(f"   Client ID: {client_id[:20]}...")
    print(f"   Project ID: {project_id}")

# Check token.json
token_path = Path('token.json')
if token_path.exists():
    print("✅ token.json exists (already authenticated)")
else:
    print("⚠️  token.json NOT FOUND (first run needs browser)")

# Check vault
vault = Path('AI_Employee_Vault')
if vault.exists():
    print(f"✅ Vault exists: {vault}")
else:
    print(f"❌ Vault NOT FOUND: {vault}")

print("\n=== Next Steps ===")
print("""
1. Verify OAuth consent screen configured in Google Cloud Console
2. Add your Gmail address as a test user (if in Testing mode)
3. Enable Gmail API
4. Run watcher again:
   python watchers/gmail_watcher.py --vault AI_Employee_Vault --credentials credentials.json
""")
