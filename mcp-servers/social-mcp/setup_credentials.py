#!/usr/bin/env python3
"""
Social Media API Credentials Setup Guide
This script provides instructions for obtaining API credentials.
"""

import webbrowser
from pathlib import Path

def show_facebook_instructions():
    """Display Facebook/Instagram setup steps."""
    print("\n" + "=" * 70)
    print("📘 FACEBOOK & INSTAGRAM SETUP")
    print("=" * 70)

    print("""
1. Go to https://developers.facebook.com
2. Create a Developer account (if you don't have one)
3. Create a new App:
   - Choose "Business" or "Other" as app type
   - Add "Facebook Login" and "Instagram Basic Display" products
4. In the App Dashboard:
   - Go to "App Review" → "Permissions and Features"
   - Request these permissions:
     • pages_show_list
     • pages_read_engagement
     • pages_manage_posts
     • instagram_basic
     • instagram_content_publish
5. Generate a Long-Lived Page Access Token:
   a. Go to "Tools" → "Graph API Explorer"
   b. Select your app and your Facebook Page
   c. Generate token with page permissions
   d. Extend token to 60 days: https://developers.facebook.com/docs/facebook-login/access-tokens/refreshing
6. Get your Page ID and Instagram Business ID:
   - Page ID: https://graph.facebook.com/v20.0/me/accounts (with token)
   - Instagram ID: https://graph.facebook.com/v20.0/{page-id}?fields=instagram_business_account

Keep these values:
- FACEBOOK_PAGE_ID = "123456..."
- FACEBOOK_ACCESS_TOKEN = "EAAGm..."
- INSTAGRAM_BUSINESS_ID = "178414..."
    """)

    open_browser = input("Open Facebook Developers site? (y/n): ").lower()
    if open_browser == 'y':
        webbrowser.open("https://developers.facebook.com")

def show_twitter_instructions():
    """Display Twitter/X setup steps."""
    print("\n" + "=" * 70)
    print("🐦 TWITTER (X) SETUP")
    print("=" * 70)

    print("""
1. Apply for a Developer account at https://developer.twitter.com
   - Choose "Academic Research" or "Business" depending on use
   - Wait for approval (may take days/weeks)
2. Once approved, create a Project and App
3. In the App dashboard, enable these:
   - "OAuth 1.0a" (for posting tweets)
   - "OAuth 2.0" (for read-only with Bearer token)
4. Generate credentials:
   a. API Key & Secret (OAuth 1.0a)
   b. Access Token & Secret (for user context)
   c. Bearer Token (for app-only auth)
5. Set app permissions to "Read and Write" for posting

Keep these values:
- TWITTER_API_KEY = "consumer_key..."
- TWITTER_API_SECRET = "consumer_secret..."
- TWITTER_ACCESS_TOKEN = "access_token..."
- TWITTER_ACCESS_SECRET = "access_token_secret..."
- TWITTER_BEARER_TOKEN = "AAAAAAAA..."
    """)

    open_browser = input("Open Twitter Developer site? (y/n): ").lower()
    if open_browser == 'y':
        webbrowser.open("https://developer.twitter.com")

def create_env_file():
    """Create .env file with placeholders."""
    env_path = Path(".env")
    template = """# Social Media MCP Configuration
# Fill in your actual credentials from the setup guides

# Facebook
FACEBOOK_PAGE_ID=
FACEBOOK_ACCESS_TOKEN=

# Instagram (uses Facebook token)
INSTAGRAM_BUSINESS_ID=

# Twitter
TWITTER_BEARER_TOKEN=
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_SECRET=
"""

    if env_path.exists():
        overwrite = input(f"{env_path} exists. Overwrite? (y/n): ").lower()
        if overwrite != 'y':
            print("Skipping .env creation")
            return

    env_path.write_text(template)
    print(f"\n✅ Created {env_path}")
    print("   Fill in your credentials and save.")

def main():
    print("=" * 70)
    print("Social Media API Setup Guide")
    print("=" * 70)
    print("\nThis script helps you obtain API credentials for:")
    print("  • Facebook Pages")
    print("  • Instagram Business Accounts")
    print("  • Twitter/X")

    while True:
        print("\nOptions:")
        print("  1. Show Facebook/Instagram setup instructions")
        print("  2. Show Twitter setup instructions")
        print("  3. Create .env template file")
        print("  4. Exit")

        choice = input("\nSelect (1-4): ").strip()

        if choice == "1":
            show_facebook_instructions()
        elif choice == "2":
            show_twitter_instructions()
        elif choice == "3":
            create_env_file()
        elif choice == "4":
            print("\nDone! After obtaining credentials:")
            print("1. Edit .env with your tokens")
            print("2. Run: python test_connection.py")
            print("3. Add to Claude Code MCP config")
            break
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()
