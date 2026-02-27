#!/usr/bin/env python3
"""
Gmail Watcher - Silver Tier Component

Monitors Gmail inbox for new important unread emails and creates action items.

Requirements:
  pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

Setup:
  1. Enable Gmail API in Google Cloud Console
  2. Download credentials.json (OAuth 2.0 Client ID)
  3. First run will open browser for authorization
  4. Save token.json for subsequent runs

Usage:
  python watchers/gmail_watcher.py --vault AI_Employee_Vault --credentials credentials.json --check-interval 120
"""

import argparse
import logging
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Google API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    logging.warning("Google API libraries not installed. Install with: pip install google-api-python-client")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gmail_watcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GmailWatcher:
    """Watcher for Gmail incoming emails."""

    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    def __init__(self, vault_path: str, credentials_path: str, check_interval: int = 120):
        """
        Initialize Gmail watcher.

        Args:
            vault_path: Path to the AI Employee vault
            credentials_path: Path to OAuth credentials.json
            check_interval: Check interval in seconds (default 120)
        """
        self.vault_path = Path(vault_path).resolve()
        self.credentials_path = Path(credentials_path).resolve()
        self.check_interval = check_interval
        self.needs_action = self.vault_path / 'Needs_Action'
        self.processed_ids = set()
        self.credentials = None

        # Ensure directories exist
        self.needs_action.mkdir(parents=True, exist_ok=True)

        # Authenticate
        self._authenticate()

        logger.info(f"Gmail Watcher initialized:")
        logger.info(f"  Vault: {self.vault_path}")
        logger.info(f"  Check interval: {self.check_interval}s")
        logger.info(f"  Needs_Action: {self.needs_action}")

    def _authenticate(self):
        """Authenticate with Gmail API."""
        if not GOOGLE_API_AVAILABLE:
            raise ImportError("Google API libraries not installed")

        token_path = self.credentials_path.parent / 'token.json'

        if token_path.exists():
            self.credentials = Credentials.from_authorized_user_file(str(token_path), self.SCOPES)

        # If there are no (valid) credentials available, let the user log in.
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), self.SCOPES)
                self.credentials = flow.run_local_server(port=0)

            # Save credentials for next run
            token_path.write_text(json.dumps({
                'token': self.credentials.token,
                'refresh_token': self.credentials.refresh_token,
                'token_uri': self.credentials.token_uri,
                'client_id': self.credentials.client_id,
                'client_secret': self.credentials.client_secret,
                'scopes': self.credentials.scopes
            }))

            logger.info(f"Authentication successful, token saved to {token_path}")

    def check_for_updates(self) -> List[Dict[str, Any]]:
        """
        Check for new unread important emails.

        Returns:
            List of message dictionaries with id, threadId, etc.
        """
        try:
            service = build('gmail', 'v1', credentials=self.credentials)

            # Search for unread important emails
            query = 'is:unread is:important'
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=10
            ).execute()

            messages = results.get('messages', [])

            # Filter out already processed
            new_messages = [
                msg for msg in messages
                if msg['id'] not in self.processed_ids
            ]

            logger.info(f"Found {len(new_messages)} new important emails")
            return new_messages

        except HttpError as error:
            logger.error(f"Gmail API error: {error}")
            return []
        except Exception as e:
            logger.error(f"Error checking emails: {e}")
            return []

    def create_action_file(self, message: Dict[str, Any]) -> Path:
        """
        Create action item from email.

        Args:
            message: Gmail message dictionary

        Returns:
            Path to created action file
        """
        try:
            service = build('gmail', 'v1', credentials=self.credentials)
            msg = service.users().messages().get(userId='me', id=message['id'], format='metadata').execute()

            # Extract headers
            headers = {h['name']: h['value'] for h in msg['payload']['headers']}

            from_email = headers.get('From', 'Unknown')
            subject = headers.get('Subject', 'No Subject')
            date = headers.get('Date', datetime.now().isoformat())

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_subject = "".join(c for c in subject if c.isalnum() or c in (' ', '-', '_')).rstrip()[:50]
            action_filename = f"EMAIL_{safe_subject}_{timestamp}.md"
            action_path = self.needs_action / action_filename

            # Create content
            content = f"""---
type: email
from: {from_email}
subject: {subject}
received: {datetime.now().isoformat()}
message_id: {message['id']}
thread_id: {message.get('threadId', '')}
priority: high
status: pending
---

# Email Received

**From**: {from_email}
**Subject**: {subject}
**Received**: {date}

## Email Preview

*To view full email, use Gmail web interface or Gmail MCP server*

**Message ID**: {message['id']}

## Suggested Actions

- [ ] Read full email content
- [ ] Draft reply (requires approval if new contact)
- [ ] Forward to relevant team member
- [ ] Archive after processing
- [ ] Mark as read in Gmail

## Notes

This email is flagged as IMPORTANT by Gmail.
Watcher detected it via Gmail API.

---

*Processed by Gmail Watcher v1.0-Silver*
*Timestamp: {datetime.now().isoformat()}*
"""

            action_path.write_text(content)
            logger.info(f"Created action item: {action_path}")

            # Mark as processed to avoid duplicates
            self.processed_ids.add(message['id'])

            return action_path

        except Exception as e:
            logger.error(f"Failed to create action for message {message['id']}: {e}")
            raise

    def run(self):
        """Run the watcher continuously."""
        logger.info("Starting Gmail watcher...")
        logger.info("Press Ctrl+C to stop")

        try:
            while True:
                try:
                    new_messages = self.check_for_updates()
                    for msg in new_messages:
                        self.create_action_file(msg)
                except Exception as e:
                    logger.error(f"Error in watcher loop: {e}")

                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.info("Stopping Gmail watcher...")
        except Exception as e:
            logger.error(f"Watcher crashed: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description="Gmail Watcher for AI Employee")
    parser.add_argument(
        '--vault',
        required=True,
        help='Path to the AI Employee vault'
    )
    parser.add_argument(
        '--credentials',
        required=True,
        help='Path to OAuth credentials.json'
    )
    parser.add_argument(
        '--check-interval',
        type=int,
        default=120,
        help='Check interval in seconds (default: 120)'
    )

    args = parser.parse_args()

    if not GOOGLE_API_AVAILABLE:
        print("❌ Google API libraries not installed!")
        print("   Install with: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
        return 1

    watcher = GmailWatcher(args.vault, args.credentials, args.check_interval)
    watcher.run()

    return 0


if __name__ == "__main__":
    exit(main())
