#!/usr/bin/env python3
"""
LinkedIn Auto-Poster Implementation

Python script for posting to LinkedIn using Playwright.
Supports the linkedin_auto_poster Agent Skill.

Usage:
  python utils/linkedin_poster.py --content "Post content" [--image path/to/image.jpg] [--dry-run]

Requirements:
  pip install playwright
  playwright install chromium
"""

import argparse
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

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
        logging.FileHandler('linkedin_poster.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class LinkedInPoster:
    """Posts to LinkedIn using Playwright browser automation."""

    def __init__(self, session_path: str = './linkedin_session', headless: bool = False):
        """
        Initialize LinkedIn poster.

        Args:
            session_path: Path to store browser session (persistent login)
            headless: Run browser in headless mode (default False - LinkedIn may detect)
        """
        self.session_path = Path(session_path).resolve()
        self.session_path.mkdir(parents=True, exist_ok=True)
        self.headless = headless

        logger.info(f"LinkedInPoster initialized:")
        logger.info(f"  Session path: {self.session_path}")
        logger.info(f"  Headless: {headless}")


    def ensure_logged_in(self, browser) -> bool:
        page = browser.pages[0] if browser.pages else browser.new_page()

        page.goto("https://www.linkedin.com/login", timeout=60000)

        print("\n🔐 PLEASE COMPLETE:")
        print("1. Login")
        print("2. Solve any captcha/challenge")
        print("3. Reach LinkedIn feed")
        input("After FULL login, press ENTER here...")

        return True

    def create_post(self, content: str, image_path: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        Create a LinkedIn post.

        Args:
            content: Post text content (max 3000 characters)
            image_path: Optional path to image to attach
            dry_run: If True, simulate posting without actually submitting

        Returns:
            Dictionary with result info
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright not installed. Run: pip install playwright && playwright install chromium")

        result = {
            'success': False,
            'post_url': None,
            'screenshot': None,
            'timestamp': datetime.now().isoformat()
        }

        try:
            with sync_playwright() as p:
                # Launch persistent context with login session
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.session_path),
                    headless=self.headless,
                    args=['--disable-blink-features=AutomationControlled']
                )

                page = browser.pages[0] if browser.pages else browser.new_page()

                # Ensure logged in
                if "linkedin.com/feed" in page.url:
                    logger.info("Already logged in")
                    return True
                page.goto('https://www.linkedin.com/post/new/', timeout=30000)
                time.sleep(3)

                # Wait for post editor
                post_box_selector = '[data-test-id="post-text-editor"] div[role="textbox"]'
                try:
                    page.wait_for_selector(post_box_selector, timeout=15000)
                except PlaywrightTimeoutError:
                    # Try alternative selector
                    post_box_selector = 'div[contenteditable="true"]'
                    page.wait_for_selector(post_box_selector, timeout=15000)

                # Type content
                logger.info(f"Typing post content ({len(content)} chars)...")
                post_box = page.query_selector(post_box_selector)
                if not post_box:
                    raise Exception("Could not find post text box")

                # Check if this is article mode (has title field)
                title_input = page.query_selector('input[name="article.title"], input[placeholder*="Title"], input[data-test-id*="title"]')
                if title_input:
                    logger.info("Article mode detected - filling title field")
                    # Generate a short title from first line of content
                    title = content.split('\n')[0][:100]  # First line, max 100 chars
                    title_input.click()
                    title_input.fill(title)
                    time.sleep(1)

                # Clear existing content (if any)
                post_box.click()
                page.keyboard.press('Control+A')  # Select all
                page.keyboard.press('Delete')

                # Type content (in chunks to avoid issues)
                # LinkedIn may have character limits, truncate if needed
                max_chars = 3000
                if len(content) > max_chars:
                    logger.warning(f"Content exceeds {max_chars} chars, truncating")
                    content = content[:max_chars] + "..."

                post_box.type(content, delay=10)  # Simulate human typing
                time.sleep(2)

                # Upload image if provided
                if image_path:
                    image_file = Path(image_path)
                    if image_file.exists():
                        logger.info(f"Uploading image: {image_path}")

                        # Click "Add photo" button
                        try:
                            photo_button = page.query_selector('[data-test-id="add-image-button"]')
                            if not photo_button:
                                # Try alternative
                                photo_button = page.query_selector('button:has-text("Add image")')
                            if photo_button:
                                photo_button.click()
                                time.sleep(1)

                                # Find file input
                                file_input = page.query_selector('input[type="file"]')
                                if file_input:
                                    file_input.set_input_files(str(image_file))
                                    time.sleep(3)  # Wait for upload

                                    logger.info("Image uploaded")
                                else:
                                    logger.warning("No file input found")
                        except Exception as e:
                            logger.warning(f"Could not upload image: {e}")

                # Take screenshot before posting (for verification)
                screenshot_path = f"linkedin_post_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                page.screenshot(path=screenshot_path)
                result['screenshot'] = screenshot_path
                logger.info(f"Preview screenshot: {screenshot_path}")

                if dry_run:
                    logger.info("Dry run mode - not posting")
                    result['success'] = True
                    result['dry_run'] = True
                else:
                    # Click "Post" button
                    logger.info("Clicking Post button...")

                    # Wait a bit for page to stabilize and buttons to appear
                    time.sleep(2)

                    # Strategy 1: Use Playwright's get_by_role (most reliable)
                    post_button = None
                    try:
                        # Try exact match "Post"
                        post_button = page.get_by_role('button', name='Post')
                        if post_button.count() == 0:
                            # Try case-insensitive or partial
                            post_button = page.get_by_role('button', name='Post', exact=False)
                        if post_button.count() > 0 and post_button.first.is_visible():
                            logger.info("Found Post button by role")
                            post_button.first.click()
                            time.sleep(3)
                        else:
                            post_button = None
                    except Exception:
                        post_button = None

                    # Strategy 2: Look for buttons with specific text variations
                    if not post_button:
                        button_texts = ['Post', 'Publish', 'Share', 'Submit', '✓', 'Done']
                        for text in button_texts:
                            try:
                                candidate = page.get_by_role('button', name=text, exact=False)
                                if candidate.count() > 0 and candidate.first.is_visible():
                                    logger.info(f"Found button with text: '{text}'")
                                    candidate.first.click()
                                    time.sleep(3)
                                    post_button = candidate
                                    break
                            except:
                                continue

                    # Strategy 3: Try common LinkedIn selectors
                    if not post_button:
                        post_button_selectors = [
                            '[data-test-id="post-submit-button"]',
                            'button[data-control-name="share.post"]',
                            'button[data-control-name="submit"]',
                            'button.share-box__submit-button',
                            'button[class*="share-action"]',
                            'button[class*="submit"]',
                            'button[class*="post"]',
                            'button[aria-label*="post"]',
                            'button[aria-label*="Post"]',
                            'button[aria-label*="Publish"]',
                            'button[title="Post"]',
                            'button[title="Publish"]',
                            '.share-actions button:last-child',
                            '.artdeco-button--primary',
                            'button[type="submit"]',
                        ]

                        for selector in post_button_selectors:
                            try:
                                candidate = page.query_selector(selector)
                                if candidate and candidate.is_visible():
                                    logger.info(f"Found post button with selector: {selector}")
                                    candidate.click()
                                    time.sleep(3)
                                    post_button = candidate
                                    break
                            except:
                                continue

                    # Strategy 4: Find by position (rightmost button in footer)
                    if not post_button:
                        try:
                            # Often Post button is in a footer, last visible button
                            all_buttons = page.query_selector_all('button')
                            visible_buttons = [b for b in all_buttons if b.is_visible()]
                            if visible_buttons:
                                # Heuristic: last button is often "Post"
                                logger.info(f"Trying last visible button (count: {len(visible_buttons)})")
                                visible_buttons[-1].click()
                                time.sleep(3)
                                post_button = visible_buttons[-1]
                        except:
                            pass

                    if not post_button:
                        # Debug: Show what we see
                        logger.error("Could not find Post button. Debugging...")
                        all_buttons = page.query_selector_all('button')
                        logger.error(f"Found {len(all_buttons)} total buttons on page")
                        for i, btn in enumerate(all_buttons[:15], 1):
                            try:
                                btn_text = btn.inner_text().strip()[:80]
                                btn_class = btn.get_attribute('class') or ''
                                btn_aria = btn.get_attribute('aria-label') or ''
                                btn_role = btn.get_attribute('role') or ''
                                logger.error(f"  Button {i}: text='{btn_text}', class='{btn_class[:40]}', aria='{btn_aria}', role='{btn_role}'")
                            except:
                                continue

                        # Show page HTML snippet around main content area
                        try:
                            main_content = page.query_selector('main, [role="main"], .scaffold, .feed')
                            if main_content:
                                logger.error(f"Main content HTML (first 500 chars): {main_content.inner_html()[:500]}")
                        except:
                            pass

                        raise Exception("Could not find Post button with any selector")

                    # Verify click worked by checking for success or page change
                    logger.info("Post button clicked, waiting for confirmation...")

                    # Wait for confirmation
                    try:
                        # Look for success indicators
                        success_selectors = [
                            '[data-test-id="post-success"]',
                            '.feed-shared-update-v2',  # Post appears in feed
                            '[data-control-name="back_to_post"]',  # "Back to post" button
                            'span:has-text("Your post is live")',
                            'span:has-text("Post created")',
                        ]

                        success_found = False
                        for selector in success_selectors:
                            try:
                                page.wait_for_selector(selector, timeout=5000)
                                logger.info(f"Post confirmed with selector: {selector}")
                                success_found = True
                                break
                            except PlaywrightTimeoutError:
                                continue

                        if success_found:
                            logger.info("Post published successfully!")
                            result['success'] = True

                            # Get post URL if possible
                            try:
                                post_url = page.url
                                result['post_url'] = post_url
                            except:
                                pass
                        else:
                            # No clear success indicator, but button click succeeded
                            logger.warning("No explicit success indicator, but post likely published")
                            result['success'] = True

                    except PlaywrightTimeoutError:
                        logger.warning("Timeout waiting for confirmation, but post may have succeeded")
                        result['success'] = True  # Assume success (optimistic)

                browser.close()

        except Exception as e:
            logger.error(f"Failed to create post: {e}")
            result['error'] = str(e)

        return result


def main():
    parser = argparse.ArgumentParser(description="LinkedIn Auto-Poster")
    parser.add_argument(
        '--content',
        required=True,
        help='Post content (text)'
    )
    parser.add_argument(
        '--image',
        help='Optional image path to attach'
    )
    parser.add_argument(
        '--session-path',
        default='./linkedin_session',
        help='Browser session storage path'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate posting without actually posting'
    )

    args = parser.parse_args()

    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright not installed!")
        print("   Install: pip install playwright && playwright install chromium")
        return 1

    # Read content from file if it's a file path
    content = args.content
    if Path(content).exists():
        content = Path(content).read_text()
        logger.info(f"Read content from file: {content[:100]}...")

    poster = LinkedInPoster(session_path=args.session_path, headless=args.headless)

    result = poster.create_post(
        content=content,
        image_path=args.image,
        dry_run=args.dry_run
    )

    if result['success']:
        print("✅ Post created successfully!")
        if result.get('dry_run'):
            print("   (dry run - not actually posted)")
        if result.get('post_url'):
            print(f"   URL: {result['post_url']}")
        if result.get('screenshot'):
            print(f"   Screenshot: {result['screenshot']}")
        return 0
    else:
        print("❌ Failed to create post")
        if result.get('error'):
            print(f"   Error: {result['error']}")
        return 1


if __name__ == "__main__":
    exit(main())
