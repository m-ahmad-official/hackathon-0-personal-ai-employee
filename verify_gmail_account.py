#!/usr/bin/env python3
"""Verify which Gmail account we're actually accessing"""

import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Load token
token_path = Path('token.json')
if not token_path.exists():
    print("No token.json - need to authenticate first")
    exit(1)

creds = Credentials.from_authorized_user_file(str(token_path), ['https://www.googleapis.com/auth/gmail.readonly'])

if not creds.valid:
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        print("Invalid credentials")
        exit(1)

# Build service and get profile
service = build('gmail', 'v1', credentials=creds)

# Get user profile
profile = service.users().getProfile(userId='me').execute()

print("="*60)
print("GMAIL ACCOUNT INFORMATION")
print("="*60)
print(f"Email address: {profile.get('emailAddress', 'UNKNOWN')}")
print(f"Messages total: {profile.get('messagesTotal', 0)}")
print(f"Threads total: {profile.get('threadsTotal', 0)}")
print(f"History ID: {profile.get('historyId', 'N/A')}")
print()

# Also check token info
token_data = json.loads(token_path.read_text())
print("Token information:")
print(f"  Client ID: {token_data.get('client_id', 'N/A')[:50]}...")
print(f"  Scopes: {', '.join(token_data.get('scopes', []))}")
print(f"  Expiry: {token_data.get('token_uri', 'N/A')}")
print("="*60)
