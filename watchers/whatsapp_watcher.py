#!/usr/bin/env python3
"""
WhatsApp Watcher - Silver Tier Component

Monitors WhatsApp Web for new messages using Playwright.

Requirements:
  pip install playwright
  playwright install chromium

Usage:
  python watchers/whatsapp_watcher.py --vault AI_Employee_Vault --session-path ./session --check-interval 30
"""

import argparse
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('whatsapp_watcher.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WhatsAppWatcher:
    """Watcher for WhatsApp messages via WhatsApp Web."""

    def __init__(self, vault_path: str, session_path: str, check_interval: int = 30, single_run: bool = False):
        """
        Initialize WhatsApp watcher.

        Args:
            vault_path: Path to the AI Employee vault
            session_path: Path to store browser session (for persistent login)
            check_interval: Check interval in seconds (default 30)
            single_run: If True, run once and exit (for testing)
        """
        self.vault_path = Path(vault_path).resolve()
        self.session_path = Path(session_path).resolve()
        self.check_interval = check_interval
        self.single_run = single_run
        self.needs_action = self.vault_path / 'Needs_Action'
        self.processed_chats = set()

        # Ensure directories exist
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self.session_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"WhatsApp Watcher initialized:")
        logger.info(f"  Vault: {self.vault_path}")
        logger.info(f"  Session path: {self.session_path}")
        logger.info(f"  Check interval: {self.check_interval}s")
        logger.info(f"  Single run: {self.single_run}")

    def get_unread_chats(self, page) -> List[Dict[str, Any]]:
        """
        Get list of unread chat elements.

        Args:
            page: Playwright page object

        Returns:
            List of chat dictionaries
        """
        try:
            # Wait for chat list to load
            logger.info("Looking for chat list container...")
            chat_list_selectors = [
                '[role="grid"]',  # Modern WhatsApp Web
                'div[aria-label*="Chat"]',  # Chat list with aria-label
                '[data-testid="infinite-list"]',  # List component
            ]

            chat_list = None
            for selector in chat_list_selectors:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    chat_list = page.query_selector(selector)
                    if chat_list:
                        logger.info(f"Found chat list container: {selector}")
                        break
                except PlaywrightTimeoutError:
                    continue

            if not chat_list:
                logger.warning("Could not find chat list container - WhatsApp UI may have changed")
                return []

            # Get all chat rows - WhatsApp uses role=row for each chat
            # Also try to find any clickable list items
            logger.info("Finding chat items...")
            chat_items = page.query_selector_all('[role="row"]')

            if not chat_items:
                # Fallback: look for any elements that look like chat items
                chat_items = chat_list.query_selector_all('li, div[class*="chat"], div[class*="conversation"]')

            logger.info(f"Found {len(chat_items)} chat items in list")

            unread_chats = []
            for idx, chat_element in enumerate(chat_items):
                try:
                    # Log progress periodically
                    if idx % 20 == 0:
                        logger.debug(f"Processing chat item {idx+1}/{len(chat_items)}")

                    # Method 1: Check aria-label for unread indicators
                    aria_label = chat_element.get_attribute('aria-label') or ''
                    aria_label_lower = aria_label.lower()

                    # Method 2: Look for unread badge/indicator within the chat element
                    # WhatsApp typically shows a green dot or a small badge with unread count
                    unread_badge = None
                    selectors_for_badge = [
                        'span[title*="unread"]',
                        'span[aria-label*="unread"]',
                        'div[class*="unread"]',
                        'div[class*="badge"]',
                        'div[class*="count"]',
                        '[data-testid*="unread"]',
                    ]
                    for badge_sel in selectors_for_badge:
                        badge = chat_element.query_selector(badge_sel)
                        if badge:
                            unread_badge = badge
                            break

                    # Method 3: Check if any child has unread text
                    has_unread_text = 'unread' in aria_label_lower or 'new' in aria_label_lower

                    # Determine if this chat is unread
                    is_unread = (
                        unread_badge is not None or
                        has_unread_text or
                        ('(' in aria_label and any(c.isdigit() for c in aria_label))  # e.g., "John (3)"
                    )

                    if not is_unread:
                        # Also check for the typical unread visual: a small green circle
                        # This appears as a div with specific background color (but we can't check color in CSS)
                        # However, elements with role=img sometimes serve as icons
                        has_indicator = chat_element.query_selector('[role="img"]') is not None
                        if has_indicator:
                            # Could be an unread indicator - check if it's small (approx 10-12px)
                            # We'll assume it's unread if there's an icon and aria-label mentions count
                            if any(char.isdigit() for char in aria_label):
                                is_unread = True

                    if not is_unread:
                        continue

                    # Extract chat name
                    chat_name = ""
                    if aria_label:
                        # Clean up aria-label - often contains "Chat with John" or "John, 3 unread messages"
                        chat_name = aria_label
                        # Try to extract just the name before comma or parenthesis
                        if ',' in chat_name:
                            chat_name = chat_name.split(',')[0].strip()
                        # Remove "Chat with" prefix
                        if chat_name.lower().startswith('chat with '):
                            chat_name = chat_name[9:]
                    else:
                        # Get from text content - first line usually has the contact name
                        text = chat_element.inner_text()
                        if text:
                            chat_name = text.split('\n')[0].strip()

                    chat_name = chat_name[:100] if chat_name else "Unknown"

                    # Extract unread count
                    count = "1"  # Default
                    if unread_badge:
                        badge_text = unread_badge.inner_text() or unread_badge.get_attribute('aria-label') or ''
                        import re
                        match = re.search(r'(\d+)', badge_text)
                        if match:
                            count = match.group(1)
                    else:
                        # Try to extract from aria-label
                        match = re.search(r'(\d+)\s+unread', aria_label_lower)
                        if match:
                            count = match.group(1)

                    logger.debug(f"Unread chat detected: {chat_name} ({count} messages)")

                    unread_chats.append({
                        'name': chat_name,
                        'count': count,
                        'element': chat_element
                    })

                except Exception as e:
                    logger.debug(f"Error parsing chat item {idx}: {e}")
                    continue

            logger.info(f"✅ Found {len(unread_chats)} unread chat(s)")
            return unread_chats

        except PlaywrightTimeoutError:
            logger.warning("Chat list not found - may not be logged in")
            return []
        except Exception as e:
            logger.error(f"Error getting unread chats: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def open_chat_and_get_messages(self, page, chat_element) -> List[Dict[str, Any]]:
        """
        Open a chat and extract messages.

        Args:
            page: Playwright page object
            chat_element: Chat element to open

        Returns:
            List of message dictionaries
        """
        messages = []

        try:
            # Click on chat to open
            chat_element.click()
            page.wait_for_timeout(2000)  # Wait for chat to load

            # Get chat header info - try multiple selectors
            header_selectors = [
                '[data-testid="chat-header"]',
                'header[role="banner"]',
                'div[aria-label*="Chat"]',  # Header often has chat name in aria-label
                'span[title]',  # Contact name may be in title attribute
            ]

            contact_name = "Unknown"
            for selector in header_selectors:
                header = page.query_selector(selector)
                if header:
                    contact_name = header.inner_text().split('\n')[0].strip()
                    if contact_name and contact_name != "Unknown":
                        break

            # Wait a bit longer for chat to fully load
            page.wait_for_timeout(3000)

            # Debug: Take a screenshot to see what's happening
            # Uncomment next 2 lines if you want screenshots
            # screenshot_path = self.session_path / f"debug_chat_{datetime.now().strftime('%H%M%S')}.png"
            # page.screenshot(path=str(screenshot_path))

            # Get message container - modern WhatsApp structure
            logger.debug(f"Current URL: {page.url}")
            messages_container_selectors = [
                '[data-testid="msg-container"]',  # Common in WhatsApp Web
                '[data-testid="message-list"]',
                'div[role="region"]',  # Main content region
                'div[class*="conversation"]',  # Conversation container
                'div[class*="msg-container"]',
                'div[class*="message-container"]',
                'main',  # Sometimes messages are directly in main
                'div[aria-label*="Message"]',  # Container with message label
                'div[data-testid*="conversation"]',
            ]

            messages_container = None
            for selector in messages_container_selectors:
                try:
                    container = page.query_selector(selector)
                    if container:
                        # Verify this container actually has messages by checking for message-like children
                        msg_candidates = container.query_selector_all('[role="article"], div[class*="message"], div[class*="msg"]')
                        if len(msg_candidates) > 0:
                            messages_container = container
                            logger.debug(f"Found message container with: {selector} ({len(msg_candidates)} messages)")
                            break
                        else:
                            logger.debug(f"Selector {selector} matched but no messages found inside")
                except Exception as e:
                    logger.debug(f"Error checking selector {selector}: {e}")
                    continue

            if not messages_container:
                # Emergency fallback: Try to find ANY message on page
                logger.warning("Primary container not found, trying emergency message detection...")
                all_possible_msgs = page.query_selector_all('[role="article"], div[class*="message"], div[class*="msg"]')
                if all_possible_msgs and len(all_possible_msgs) > 0:
                    logger.info(f"Found {len(all_possible_msgs)} messages directly on page, using them")
                    message_elements = all_possible_msgs
                    # Skip normal container parsing, go straight to message processing
                    # But we need to set a fake container for consistency
                    messages_container = page
                else:
                    logger.warning("Message container not found - cannot extract messages")
                    logger.warning(f"Debug: Page has {len(page.query_selector_all('*'))} total elements")
                    page.keyboard.press('Escape')
                    page.wait_for_timeout(500)
                    return messages

            # Get message elements
            message_selectors = [
                '[data-testid*="msg-"]',  # Legacy: data-testid="msg-0", etc.
                '[role="article"]',  # Each message is often an article
                'div[class*="message"]',  # Modern: class contains "message"
                'div[class*="msg"]',  # Alternative class pattern
                'div[class*="text"][dir="ltr"]',  # Message text spans
            ]

            message_elements = []
            for selector in message_selectors:
                try:
                    elems = messages_container.query_selector_all(selector)
                    if elems and len(elems) > 0:
                        message_elements = elems
                        logger.debug(f"Found {len(elems)} message elements with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Error querying selector {selector}: {e}")
                    continue

            if not message_elements:
                logger.warning("No message elements found in container")
                page.keyboard.press('Escape')
                page.wait_for_timeout(500)
                return messages

            # Process in reverse order (newest first) - take last 5-10
            recent_messages = message_elements[-10:] if len(message_elements) > 10 else message_elements
            logger.info(f"Processing {len(recent_messages)} recent messages (from {len(message_elements)} total)")

            for msg_elem in reversed(recent_messages):
                try:
                    # Check if message is outgoing (sent by us)
                    # Modern WhatsApp uses classes like "message-out" or "outgoing"
                    msg_class = msg_elem.get_attribute('class') or ''
                    is_outgoing = (
                        'message-out' in msg_class or
                        'outgoing' in msg_class or
                        'sent' in msg_class
                    )

                    # Check data attributes
                    data_testid = msg_elem.get_attribute('data-testid') or ''
                    if 'out' in data_testid.lower():
                        is_outgoing = True

                    # Skip outgoing messages
                    if is_outgoing:
                        continue

                    # Extract text content
                    # Message text is usually in a span with selectable-text or copyable-text
                    text_selectors = [
                        '[data-testid="msg-text"]',
                        '.selectable-text',
                        '.copyable-text',
                        'span[dir="ltr"]',
                        'div[class*="text"]',
                    ]

                    text_content = ""
                    for sel in text_selectors:
                        text_elem = msg_elem.query_selector(sel)
                        if text_elem:
                            text_content = text_elem.inner_text().strip()
                            if text_content:
                                break

                    if not text_content:
                        # Fallback: get all text from the message element
                        text_content = msg_elem.inner_text().strip()
                        # Remove sender name/timestamp if present in the text
                        # WhatsApp messages often include metadata in separate spans
                        lines = text_content.split('\n')
                        if len(lines) > 1:
                            # Take the longest line (usually the message)
                            text_content = max(lines, key=len)

                    text = text_content if text_content else "[No text content]"

                    # Extract timestamp
                    # Look for time element
                    time_elem = msg_elem.query_selector('time[datetime], span[title*="/"]')
                    timestamp = datetime.now().isoformat()
                    if time_elem:
                        dt_attr = time_elem.get_attribute('datetime')
                        if dt_attr:
                            timestamp = dt_attr
                        else:
                            # Try to parse from title or text
                            time_text = time_elem.inner_text().strip()
                            # If it looks like a time like "10:30 AM" we'll use current date + that time
                            # For simplicity, just use current timestamp
                            pass

                    messages.append({
                        'contact': contact_name,
                        'text': text,
                        'timestamp': timestamp,
                        'is_incoming': True
                    })

                except Exception as e:
                    logger.debug(f"Error parsing message: {e}")
                    continue

            # Close chat - try multiple methods
            try:
                page.keyboard.press('Escape')
            except:
                # Fallback: click close button if exists
                close_btn = page.query_selector('button[aria-label="Close"], [data-testid="close"]')
                if close_btn:
                    close_btn.click()
            page.wait_for_timeout(500)

            logger.info(f"✓ Extracted {len(messages)} incoming messages from {contact_name}")
            return messages

        except Exception as e:
            logger.error(f"Error opening chat {contact_name if 'contact_name' in locals() else '?'}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Try to recover by closing any open dialogs
            try:
                page.keyboard.press('Escape')
            except:
                pass
            return messages

    def create_action_file(self, contact: str, messages: List[Dict[str, Any]]) -> Path:
        """
        Create action item from WhatsApp messages.

        Args:
            contact: Contact name/number
            messages: List of message dictionaries

        Returns:
            Path to created action file
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_contact = "".join(c for c in contact if c.isalnum() or c in (' ', '-', '_')).rstrip()[:30]
            action_filename = f"WHATSAPP_{safe_contact}_{timestamp}.md"
            action_path = self.needs_action / action_filename

            # Build message content
            messages_text = "\n\n".join([
                f"**{msg['timestamp']}**: {msg['text']}"
                for msg in messages
            ])

            # Check for urgent keywords (simple heuristic)
            urgent_keywords = ['urgent', 'asap', 'invoice', 'payment', 'help', 'important', 'emergency']
            is_urgent = any(keyword in messages_text.lower() for keyword in urgent_keywords)

            priority = "high" if is_urgent else "medium"

            content = f"""---
type: whatsapp
contact: {contact}
message_count: {len(messages)}
received: {datetime.now().isoformat()}
priority: {priority}
status: pending
---

# WhatsApp Message{'s' if len(messages) > 1 else ''} from {contact}

**Priority**: {priority.upper()}
**Messages**: {len(messages)}
**Received**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Messages

{messages_text}

## Suggested Actions

- [ ] Review messages and respond appropriately
- [ ] Check if this relates to any existing task
- [ ] Draft response (requires approval if sensitive)
- [ ] Update contact information if needed

{"⚠️ **URGENT**: Contains urgent keywords" if is_urgent else ""}

## Notes

Detected via WhatsApp Web watcher.
To reply, use WhatsApp MCP or manual response.

---

*Processed by WhatsApp Watcher v1.0-Silver*
*Timestamp: {datetime.now().isoformat()}*
"""

            action_path.write_text(content)
            logger.info(f"Created action item: {action_path}")
            return action_path

        except Exception as e:
            logger.error(f"Failed to create action file for {contact}: {e}")
            raise

    def run(self):
        """Run the watcher continuously or once."""
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not installed! Install with: pip install playwright && playwright install chromium")
            return

        logger.info("Starting WhatsApp watcher...")
        logger.info("⚠️  Make sure you're logged into WhatsApp Web in the session!")
        if self.single_run:
            logger.info("Single-run mode: will exit after one check")
        else:
            logger.info(f"Continuous mode: checking every {self.check_interval}s")

        run_count = 0
        max_runs = 1 if self.single_run else float('inf')

        while run_count < max_runs:
            run_count += 1
            logger.info(f"--- Check #{run_count} ---")

            try:
                with sync_playwright() as p:
                    # Launch persistent context (keeps login session)
                    # Add additional args for better compatibility
                    launch_args = [
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                    ]
                    try:
                        browser = p.chromium.launch_persistent_context(
                            user_data_dir=str(self.session_path),
                            headless=False,  # Must be non-headless for WhatsApp Web
                            args=launch_args
                        )
                    except Exception as launch_error:
                        # If persistent context fails, try with a regular launch
                        logger.warning(f"Persistent context failed: {launch_error}")
                        logger.info("Trying regular browser launch (session will not persist)...")
                        browser = p.chromium.launch(headless=False, args=launch_args)
                        page = browser.new_page()
                        page.goto('https://web.whatsapp.com', timeout=60000)
                        logger.warning("Using non-persistent mode - you'll need to log in each time!")

                    # Get page
                    if 'page' not in locals():
                        page = browser.pages[0] if browser.pages else browser.new_page()

                    # Navigate to WhatsApp Web if needed
                    if page.url == 'about:blank':
                        page.goto('https://web.whatsapp.com', timeout=60000)
                    logger.info("Loaded WhatsApp Web")

                    # Wait for login with longer timeout (60s) for QR code scanning
                    try:
                        login_selectors = [
                            '[role="grid"]',
                            'div[aria-label*="Chat"]',
                            '[data-testid="chat-list"]',
                        ]
                        logged_in = False
                        for selector in login_selectors:
                            try:
                                page.wait_for_selector(selector, timeout=20000)
                                logged_in = True
                                logger.info(f"✓ WhatsApp Web logged in (detected: {selector})")
                                break
                            except PlaywrightTimeoutError:
                                continue

                        if not logged_in:
                            logger.error("✗ Not logged in after 60s wait!")
                            logger.error("  1. Open WhatsApp on your phone")
                            logger.error("  2. Scan the QR code if shown")
                            logger.error("  3. Wait until you see your chat list")
                            logger.error("  4. The watcher will exit now")
                            browser.close()
                            if self.single_run:
                                return
                            continue

                    except Exception as e:
                        logger.error(f"Login check failed: {e}")
                        browser.close()
                        if self.single_run:
                            return
                        continue

                    # Check for unread chats
                    unread_chats = self.get_unread_chats(page)

                    if unread_chats:
                        logger.info(f"Processing {len(unread_chats)} unread chat(s)")

                        for chat in unread_chats:
                            try:
                                messages = self.open_chat_and_get_messages(page, chat['element'])
                                if messages:
                                    self.create_action_file(chat['name'], messages)
                            except Exception as e:
                                logger.error(f"Error processing chat {chat['name']}: {e}")
                                continue
                    else:
                        logger.info("✓ No unread messages")

                    browser.close()

            except Exception as e:
                logger.error(f"Watcher error: {e}")
                import traceback
                logger.error(traceback.format_exc())

            if self.single_run:
                logger.info("Single run completed - exiting")
                break

            logger.info(f"Sleeping for {self.check_interval}s before next check...")
            time.sleep(self.check_interval)


def main():
    parser = argparse.ArgumentParser(description="WhatsApp Watcher for AI Employee")
    parser.add_argument(
        '--vault',
        required=True,
        help='Path to the AI Employee vault'
    )
    parser.add_argument(
        '--session-path',
        default='./session',
        help='Path to store browser session (default: ./session)'
    )
    parser.add_argument(
        '--check-interval',
        type=int,
        default=30,
        help='Check interval in seconds (default: 30)'
    )
    parser.add_argument(
        '--single-run',
        action='store_true',
        help='Run once and exit (for testing)'
    )

    args = parser.parse_args()

    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright not installed!")
        print("   Install with: pip install playwright && playwright install chromium")
        return 1

    watcher = WhatsAppWatcher(args.vault, args.session_path, args.check_interval, args.single_run)
    watcher.run()

    return 0


if __name__ == "__main__":
    exit(main())
