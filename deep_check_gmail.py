#!/usr/bin/env python3
"""Deep check: are these emails really unread and important?"""

import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Load token
token_path = Path('token.json')
creds = Credentials.from_authorized_user_file(str(token_path), ['https://www.googleapis.com/auth/gmail.readonly'])
if not creds.valid:
    creds.refresh(Request())

service = build('gmail', 'v1', credentials=creds)

print("="*70)
print("DETAILED GMAIL CHECK")
print("="*70)

# Query 1: is:unread is:important
print("\n1. Query: 'is:unread is:important'")
results1 = service.users().messages().list(userId='me', q='is:unread is:important', maxResults=50).execute()
msgs1 = results1.get('messages', [])
print(f"   Found: {len(msgs1)} messages")

# Query 2: just is:unread
print("\n2. Query: 'is:unread' (all unread)")
results2 = service.users().messages().list(userId='me', q='is:unread', maxResults=50).execute()
msgs2 = results2.get('messages', [])
print(f"   Found: {len(msgs2)} messages")

# Query 3: just is:important
print("\n3. Query: 'is:important' (all important, read or unread)")
results3 = service.users().messages().list(userId='me', q='is:important', maxResults=50).execute()
msgs3 = results3.get('messages', [])
print(f"   Found: {len(msgs3)} messages")

# Let's inspect the first few messages from the unread important set
if msgs1:
    print("\n4. Detailed inspection of first unread important message:")
    msg = service.users().messages().get(userId='me', id=msgs1[0]['id'], format='minimal').execute()
    
    # Check internal Gmail labels
    label_ids = msg.get('labelIds', [])
    print(f"   Labels: {label_ids}")
    
    # Check if it truly has UNREAD and IMPORTANT
    has_unread = 'UNREAD' in label_ids
    has_important = 'IMPORTANT' in label_ids
    
    print(f"   Has UNREAD label: {has_unread}")
    print(f"   Has IMPORTANT label: {has_important}")
    
    # Also get snippet
    print(f"   Snippet: {msg.get('snippet', '')[:100]}...")

# Compare sets: intersection of unread AND important?
if msgs1 and msgs2 and msgs3:
    ids1 = set(m['id'] for m in msgs1)
    ids2 = set(m['id'] for m in msgs2)
    ids3 = set(m['id'] for m in msgs3)
    
    print("\n5. Set analysis:")
    print(f"   Unread only (not important): {len(ids2 - ids3)}")
    print(f"   Important only (already read): {len(ids3 - ids2)}")
    print(f"   Both unread AND important: {len(ids1)}")
    
    # Show a few that are unread but NOT important
    unread_not_important = ids2 - ids3
    if unread_not_important:
        print("\n   Sample unread but NOT important:")
        for msg_id in list(unread_not_important)[:3]:
            m = service.users().messages().get(userId='me', id=msg_id, format='metadata').execute()
            headers = {h['name']: h['value'] for h in m['payload']['headers']}
            print(f"   - {headers.get('Subject', 'No Subject')[:50]}")
            print("     (Mark this email as IMPORTANT to test watcher)")

print("\n" + "="*70)
print("CONCLUSION:")
print("="*70)
print(f"Total truly UNREAD+IMPORTANT: {len(msgs1)}")
if len(msgs1) > 0:
    print("✅ There ARE unread important emails - watcher should detect them")
    print("❌ Why is watcher finding 0? Let's check the watcher code logic...")
else:
    print("⚠️  No emails match BOTH unread AND important")
    print("   Solution: Mark an email as BOTH unread AND important (yellow flag)")
