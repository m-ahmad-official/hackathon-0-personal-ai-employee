#!/usr/bin/env python3
"""Test Gmail API query manually to see what's found"""

import json
from pathlib import Path
from datetime import datetime

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    print("❌ Google API libraries not installed")
    exit(1)

# Load credentials.json
creds_path = Path('credentials.json')
if not creds_path.exists():
    print(f"❌ credentials.json not found")
    exit(1)

creds_data = json.loads(creds_path.read_text())
# Get client_id and project_id from JSON
client_info = creds_data.get('installed', creds_data.get('web', {}))
print(f"Credentials for project: {client_info.get('project_id', 'unknown')}")
print(f"Client ID: {client_info.get('client_id', 'unknown')[:30]}...")

# Check token.json
token_path = Path('token.json')
if not token_path.exists():
    print("❌ token.json not found - need to authenticate first")
    print("   Run: python watchers/gmail_watcher.py --vault AI_Employee_Vault --credentials credentials.json")
    exit(1)

creds = Credentials.from_authorized_user_file(str(token_path), ['https://www.googleapis.com/auth/gmail.readonly'])

if not creds.valid:
    if creds.expired and creds.refresh_token:
        print("🔄 Refreshing expired token...")
        creds.refresh(Request())
    else:
        print("❌ Token invalid and can't refresh")
        exit(1)

# Build Gmail service
service = build('gmail', 'v1', credentials=creds)
print("✅ Authenticated successfully\n")

# Test query
query = 'is:unread is:important'
print(f"Searching with query: {query}")
print("-" * 50)

try:
    results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=10
    ).execute()
    
    messages = results.get('messages', [])
    print(f"Found {len(messages)} messages\n")
    
    if messages:
        print("First 3 messages:")
        for i, msg in enumerate(messages[:3], 1):
            try:
                msg_detail = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata'
                ).execute()
                
                headers = {h['name']: h['value'] for h in msg_detail['payload']['headers']}
                subject = headers.get('Subject', 'No Subject')
                from_email = headers.get('From', 'Unknown')
                date = headers.get('Date', '')
                
                print(f"{i}. From: {from_email}")
                print(f"   Subject: {subject}")
                print(f"   Date: {date}")
                print(f"   ID: {msg['id']}")
                print()
            except Exception as e:
                print(f"{i}. Error fetching message: {e}\n")
    else:
        print("No messages found with this query.")
        print("\nPossible reasons:")
        print("1. No unread emails marked as Important")
        print("2. All important emails are already read")
        print("3. Emails are in a label/folder, not inbox")
        print("4. Wrong Gmail account being accessed")
        
        print("\n" + "="*50)
        print("Let's check ALL unread emails (not just important):")
        print("="*50 + "\n")
        
        query2 = 'is:unread'
        results2 = service.users().messages().list(userId='me', q=query2, maxResults=5).execute()
        messages2 = results2.get('messages', [])
        print(f"Found {len(messages2)} TOTAL unread emails")
        
        if messages2:
            print("These unread emails exist but are NOT marked as Important:")
            for i, msg in enumerate(messages2[:3], 1):
                try:
                    msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='metadata').execute()
                    headers = {h['name']: h['value'] for h in msg_detail['payload']['headers']}
                    print(f"{i}. From: {headers.get('From', 'Unknown')}")
                    print(f"   Subject: {headers.get('Subject', 'No Subject')}")
                    is_important = 'X-GM-IMPORTANT' in msg_detail.get('payload', {}).get('headers', [])
                    print(f"   Important flag: Mark the email as Important in Gmail to trigger watcher")
                    print()
                except:
                    continue
            print("\n⚠️ SOLUTION: Mark one of these emails as Important (yellow flag)")
            print("Then the watcher will detect it within 10-30 seconds")
        else:
            print("No unread emails at all.")
            print("Send yourself a test email and keep it unread.")
            
except Exception as e:
    print(f"❌ Error querying Gmail: {e}")
    import traceback
    traceback.print_exc()
