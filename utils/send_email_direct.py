#!/usr/bin/env python3
"""
Direct Email Sender using Gmail API
Simplified alternative to MCP server for Silver Tier demo
"""

import argparse
import base64
import json
import logging
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    GOOGLE_API_AVAILABLE = True
except ImportError:
    print("❌ Google API libraries not installed")
    print(
        "   Run: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
    )
    exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def send_email(
    credentials_path: str, to: str, subject: str, body: str, reply_to: str = None
) -> dict:
    """
    Send an email using Gmail API.

    Args:
        credentials_path: Path to OAuth credentials.json (or token.json)
        to: Recipient email address
        subject: Email subject
        body: Email body (plain text)
        reply_to: Optional reply-to address

    Returns:
        Dictionary with result

    Usage:
        python utils/send_email_direct.py --credentials credentials.json --to "aq320647@gmail.com" --subject "Test Email from AI Employee" --body "Hello! This email was sent by the AI Employee system using direct Gmail API. Timestamp: $(date)"
    """
    result = {"success": False, "message_id": None, "error": None}

    try:
        # Load credentials (token.json will be in same dir as credentials.json)
        creds_path = Path(credentials_path)
        token_path = creds_path.parent / "token.json"

        if token_path.exists():
            creds = Credentials.from_authorized_user_file(
                str(token_path), ["https://www.googleapis.com/auth/gmail.send"]
            )
        else:
            # If no token, credentials_path might be token.json itself
            creds = Credentials.from_authorized_user_file(
                str(creds_path), ["https://www.googleapis.com/auth/gmail.send"]
            )

        # Refresh if needed
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save updated token
                token_path.write_text(
                    json.dumps(
                        {
                            "token": creds.token,
                            "refresh_token": creds.refresh_token,
                            "token_uri": creds.token_uri,
                            "client_id": creds.client_id,
                            "client_secret": creds.client_secret,
                            "scopes": creds.scopes,
                        }
                    )
                )
            else:
                raise Exception("No valid credentials and cannot refresh")

        # Build Gmail service
        service = build("gmail", "v1", credentials=creds)

        # Create message
        message = MIMEText(body, "plain", "utf-8")
        message["to"] = to
        message["subject"] = subject
        if reply_to:
            message["reply-to"] = reply_to

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        # Send
        logger.info(f"Sending email to {to}")
        logger.info(f"Subject: {subject}")

        sent_message = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw_message})
            .execute()
        )

        result["success"] = True
        result["message_id"] = sent_message.get("id")
        result["thread_id"] = sent_message.get("threadId")
        logger.info(f"✅ Email sent! Message ID: {sent_message.get('id')}")

    except HttpError as error:
        logger.error(f"Gmail API error: {error}")
        result["error"] = str(error)
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        result["error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(description="Send email via Gmail API")
    parser.add_argument(
        "--credentials", required=True, help="Path to credentials.json or token.json"
    )
    parser.add_argument("--to", required=True, help="Recipient email")
    parser.add_argument("--subject", required=True, help="Email subject")
    parser.add_argument("--body", required=True, help="Email body (plain text)")
    parser.add_argument("--reply-to", help="Reply-to address")

    args = parser.parse_args()

    if not GOOGLE_API_AVAILABLE:
        print("❌ Google API not available")
        return 1

    result = send_email(
        credentials_path=args.credentials,
        to=args.to,
        subject=args.subject,
        body=args.body,
        reply_to=args.reply_to,
    )

    if result["success"]:
        print(f"✅ Email sent successfully!")
        print(f"   Message ID: {result.get('message_id')}")
        return 0
    else:
        print(f"❌ Failed to send email")
        print(f"   Error: {result.get('error')}")
        return 1


if __name__ == "__main__":
    exit(main())
