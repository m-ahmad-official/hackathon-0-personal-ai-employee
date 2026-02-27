#!/usr/bin/env python3
"""
Re-authenticate with Gmail API to get token with SEND scope.
Run this once to generate a new token.json that can send emails.
"""

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
import json

# Scopes needed: read + send
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

print("=== Re-authentication for Email Sending ===\n")
print("This will:")
print("1. Open your browser")
print("2. Ask you to log into Gmail")
print("3. Request permission to:")
print("   - Read your emails")
print("   - Send emails from your account")
print("4. Save a new token.json with these permissions\n")

input("Press Enter to continue...")

# Load client secrets
with open('credentials.json', 'r') as f:
    client_config = json.load(f)

# Create flow
flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

# Run local server
creds = flow.run_local_server(port=0)

# Save token
token_data = {
    'token': creds.token,
    'refresh_token': creds.refresh_token,
    'token_uri': creds.token_uri,
    'client_id': creds.client_id,
    'client_secret': creds.client_secret,
    'scopes': creds.scopes
}

with open('token.json', 'w') as f:
    json.dump(token_data, f, indent=2)

print("\n✅ token.json created/updated with send permission!")
print(f"   Scopes: {', '.join(creds.scopes)}")
print("\nYou can now send emails via Gmail API.")
