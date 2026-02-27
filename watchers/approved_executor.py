#!/usr/bin/env python3
"""
Approved Actions Executor
Monitors /Approved/ folder and executes approved actions automatically.

Silver Tier requirement: Execute actions after human approval.
"""

import argparse
import base64
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('approved_executor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ApprovedExecutor:
    """Executes actions from Approved folder."""

    def __init__(self, vault_path: str, credentials_path: str = 'credentials.json'):
        self.vault = Path(vault_path).resolve()
        self.approved_dir = self.vault / 'Approved'
        self.done_dir = self.vault / 'Done'
        self.logs_dir = self.vault / 'Logs'
        self.credentials_path = Path(credentials_path).resolve()

        # Ensure directories exist
        for folder in [self.done_dir, self.logs_dir]:
            folder.mkdir(parents=True, exist_ok=True)

        # Track processed files (persistent across restarts? could use a state file)
        self.processed = set()

        logger.info(f"ApprovedExecutor initialized:")
        logger.info(f"  Vault: {self.vault}")
        logger.info(f"  Approved: {self.approved_dir}")
        logger.info(f"  Credentials: {self.credentials_path}")

    def parse_frontmatter(self, filepath: Path) -> dict:
        """Parse YAML frontmatter from approval file."""
        content = filepath.read_text()

        if not content.startswith('---'):
            return {'error': 'No frontmatter found'}

        parts = content.split('---', 2)
        if len(parts) < 3:
            return {'error': 'Invalid frontmatter format'}

        frontmatter_str = parts[1]
        try:
            import yaml
            frontmatter = yaml.safe_load(frontmatter_str)
            return frontmatter
        except Exception as e:
            return {'error': f'YAML parse error: {e}'}

    def extract_body(self, filepath: Path) -> str:
        """Extract body content (after frontmatter)."""
        content = filepath.read_text()
        body_start = content.find('---', content.find('---') + 3)
        if body_start != -1:
            body = content[body_start + 3:].strip()
            return body
        return ""

    def log_action(self, action: dict):
        """Log action to daily log file."""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs_dir / f'{today}.json'

        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text())
            except:
                logs = []

        logs.append(action)
        log_file.write_text(json.dumps(logs, indent=2))
        logger.debug(f"Logged action to {log_file}")

    def send_email_via_gmail_api(self, to: str, subject: str, body: str) -> dict:
        """Send email directly via Gmail API."""
        result = {
            'success': False,
            'message_id': None,
            'error': None
        }

        try:
            if not GOOGLE_API_AVAILABLE:
                result['error'] = "Google API libraries not installed"
                return result

            # Load credentials (token.json must include gmail.send scope)
            creds_path = self.credentials_path
            token_path = creds_path.parent / 'token.json'

            if token_path.exists():
                creds = Credentials.from_authorized_user_file(
                    str(token_path),
                    ['https://www.googleapis.com/auth/gmail.send']
                )
            else:
                # Try credentials_path itself
                creds = Credentials.from_authorized_user_file(
                    str(creds_path),
                    ['https://www.googleapis.com/auth/gmail.send']
                )

            # Refresh if needed
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    # Save refreshed token
                    token_path.write_text(json.dumps({
                        'token': creds.token,
                        'refresh_token': creds.refresh_token,
                        'token_uri': creds.token_uri,
                        'client_id': creds.client_id,
                        'client_secret': creds.client_secret,
                        'scopes': creds.scopes
                    }))
                else:
                    raise Exception("No valid credentials and cannot refresh")

            # Build Gmail service
            service = build('gmail', 'v1', credentials=creds)

            # Create MIME message
            from email.mime.text import MIMEText
            message = MIMEText(body, 'plain', 'utf-8')
            message['to'] = to
            message['subject'] = subject

            # Encode
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            # Send
            logger.info(f"Sending email via Gmail API:")
            logger.info(f"  To: {to}")
            logger.info(f"  Subject: {subject}")

            sent = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            result['success'] = True
            result['message_id'] = sent.get('id')
            result['thread_id'] = sent.get('threadId')
            logger.info(f"✅ Email sent! Message ID: {sent.get('id')}")

        except HttpError as error:
            logger.error(f"Gmail API HTTP error: {error}")
            result['error'] = f"HTTP {error.resp.status}: {error.content}"
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            result['error'] = str(e)

        return result

    def process_file(self, filepath: Path):
        """Process a single approved file."""
        logger.info(f"Processing: {filepath.name}")

        # Parse frontmatter
        data = self.parse_frontmatter(filepath)

        if 'error' in data:
            logger.error(f"Failed to parse {filepath.name}: {data['error']}")
            return False

        action = data.get('action', '').lower()
        logger.info(f"Action type: {action}")

        # Handle different action types
        if action == 'send_email':
            return self.execute_send_email(filepath, data)
        else:
            logger.warning(f"Unknown action type: {action}")
            return False

    def execute_send_email(self, filepath: Path, data: dict) -> bool:
        """Execute send_email action."""
        to = data.get('to', '').strip()
        subject = data.get('subject', '').strip()

        if not to or not subject:
            logger.error(f"Missing 'to' or 'subject' in {filepath.name}")
            return False

        # Get body from file content
        body = self.extract_body(filepath)
        if not body:
            body = f"Action: {data.get('action')}\nApproved file: {filepath.name}"

        # Send email
        result = self.send_email_via_gmail_api(to, subject, body)

        if result['success']:
            # Log success
            self.log_action({
                'action_type': 'email_send',
                'to': to,
                'subject': subject,
                'tool': 'gmail_api_direct',
                'message_id': result.get('message_id'),
                'thread_id': result.get('thread_id'),
                'result': 'success',
                'source_file': filepath.name
            })

            # Move to Done
            dest = self.done_dir / filepath.name
            filepath.rename(dest)
            logger.info(f"✅ Email sent & file moved to: {dest}")

            return True
        else:
            # Log failure
            self.log_action({
                'action_type': 'email_send',
                'to': to,
                'subject': subject,
                'result': 'failed',
                'error': result.get('error'),
                'source_file': filepath.name
            })

            # Keep file in Approved? Or move to error folder?
            # For now, leave it so we can retry
            logger.error(f"❌ Failed to send email: {result.get('error')}")
            return False

    def run(self, check_interval: int = 5):
        """Run continuous watcher."""
        logger.info("=" * 60)
        logger.info("APPROVED EXECUTOR STARTED")
        logger.info("=" * 60)
        logger.info(f"Watching: {self.approved_dir}")
        logger.info(f"Check interval: {check_interval} seconds")
        logger.info("Press Ctrl+C to stop\n")

        try:
            while True:
                try:
                    if not self.approved_dir.exists():
                        logger.warning(f"Approved directory does not exist: {self.approved_dir}")
                        time.sleep(check_interval)
                        continue

                    # Find all markdown files
                    files = list(self.approved_dir.glob('*.md'))
                    new_files = [f for f in files if str(f) not in self.processed]

                    if new_files:
                        logger.info(f"Found {len(new_files)} new approved file(s)")

                    for filepath in new_files:
                        try:
                            success = self.process_file(filepath)
                            if success:
                                self.processed.add(str(filepath))
                        except Exception as e:
                            logger.error(f"Error processing {filepath.name}: {e}", exc_info=True)

                    # Cleanup processed set occasionally (to avoid memory growth)
                    if len(self.processed) > 1000:
                        # Keep only files that still exist
                        self.processed = {str(f) for f in self.approved_dir.glob('*.md') if str(f) in self.processed}

                    time.sleep(check_interval)

                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error in watcher loop: {e}", exc_info=True)
                    time.sleep(check_interval)

        except KeyboardInterrupt:
            logger.info("\n👋 Stopping Approved Executor...")
            return 0


def main():
    parser = argparse.ArgumentParser(description="Approved Actions Executor")
    parser.add_argument('--vault', required=True, help='Path to AI Employee vault')
    parser.add_argument('--credentials', default='credentials.json', help='Path to Gmail credentials')
    parser.add_argument('--interval', type=int, default=5, help='Check interval in seconds')

    args = parser.parse_args()

    if not GOOGLE_API_AVAILABLE:
        print("❌ Google API libraries not installed")
        print("   pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
        return 1

    executor = ApprovedExecutor(args.vault, args.credentials)
    return executor.run(check_interval=args.interval)


if __name__ == "__main__":
    sys.exit(main())
