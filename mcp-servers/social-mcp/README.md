# Social Media MCP Server

**Gold Tier Phase 2** - Unified API for Facebook, Instagram, and Twitter (X). **Now fully functional with error recovery and audit logging.**

## Overview

This MCP server provides Claude Code with tools to interact with major social media platforms:

| Platform | Capabilities | API Used | Status |
|----------|--------------|----------|--------|
| **Facebook** | Post to Page, get insights | Graph API v20.0+ | ✅ **Working** |
| **Instagram** | Post images to Business Account | Graph API (Instagram) | ✅ **Working** |
| **Twitter/X** | Tweet, get timeline, mentions | X API v2 | ⚠️ Implementation complete, API credits needed |

## Features

- ✅ Platform-specific formatting and optimization
- ✅ Retry logic with exponential backoff (Phase 3)
- ✅ Circuit breaker protection per platform (Phase 3)
- ✅ Comprehensive audit logging (Phase 3)
- ✅ Multi-platform posting with single tool
- ✅ Hashtag optimization for Instagram
- ✅ Twitter thread support (long content)

## Status

**Phase 2 + Phase 3 Integration: ✅ COMPLETE**

Facebook and Instagram have been tested and verified working with real posts. Twitter implementation is complete but requires API credits to actually post (free tier exhausted).

## Prerequisites

### Facebook & Instagram
1. Facebook Developer account: https://developers.facebook.com
2. Create a **Page** (if you don't have one)
3. Create an **Instagram Business Account** linked to your Facebook Page
4. Create a **Facebook App** with:
   - `pages_show_list` permission
   - `pages_read_engagement` permission
   - `pages_manage_posts` permission (for posting)
   - `instagram_basic` permission
   - `instagram_content_publish` permission (for Instagram posting)
5. Generate a **Page Access Token** (long-lived, ~60 days)
6. Get your **Facebook Page ID** and **Instagram Business Account ID**

### Twitter (X)
1. Apply for **X Developer account**: https://developer.twitter.com
2. Create a **Project** and **App**
3. Set App permissions to **Read and Write**
4. Fill in required URLs:
   - Website URL: `https://localhost` (or your domain)
   - Callback URL: `https://localhost`
5. Get **API Key & Secret** (OAuth 1.0a)
6. Get **Access Token & Secret** (for posting) - regenerate after changing permissions
7. Or get **Bearer Token** (for read-only operations)

## Installation

```bash
cd mcp-servers/social-mcp
pip install -r requirements.txt
```

## Configuration

Set environment variables or create `.env` file:

```env
# Facebook
FACEBOOK_PAGE_ID=your_page_id
FACEBOOK_ACCESS_TOKEN=your_page_access_token

# Instagram (uses same Facebook token)
INSTAGRAM_BUSINESS_ID=your_ig_business_id

# Twitter (for posting - OAuth 1.0a)
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_SECRET=your_access_secret

# Twitter (for read-only - OAuth 2.0)
TWITTER_BEARER_TOKEN=your_bearer_token
```

**Note:** The `.env` file is already in this directory (copy from `.env.example` and fill in your actual credentials).

## Starting the Server

```bash
python server.py
```

The server runs via stdio and communicates with Claude Code.

## Integration with Claude Code

Add to `~/.config/claude-code/mcp.json`:

```json
{
  "servers": [
    {
      "name": "social-mcp",
      "command": "python",
      "args": ["/path/to/project/mcp-servers/social-mcp/server.py"],
      "env": {
        "FACEBOOK_PAGE_ID": "your_page_id",
        "FACEBOOK_ACCESS_TOKEN": "your_token",
        "INSTAGRAM_BUSINESS_ID": "your_ig_id",
        "TWITTER_API_KEY": "your_key",
        "TWITTER_API_SECRET": "your_secret",
        "TWITTER_ACCESS_TOKEN": "your_access_token",
        "TWITTER_ACCESS_SECRET": "your_access_secret"
      }
    }
  ]
}
```

Restart Claude Code. Tools will be available automatically.

## Tools Reference

### facebook_post

Post a message to your Facebook Page.

**Parameters:**
- `message` (string, **required**): Text content (max 63,000 characters)
- `link` (string, optional): URL to share (link preview)
- `media_url` (string, optional): Image/video URL to attach

**Example:**
```json
{
  "message": "Check out our latest update! 🚀",
  "link": "https://example.com/blog/new-post",
  "media_url": "https://example.com/image.jpg"
}
```

**Returns:**
```json
{
  "success": true,
  "platform": "facebook",
  "post_id": "123456_789012345678901",
  "url": "https://facebook.com/123456_789012345678901"
}
```

**Notes:**
- Requires `pages_manage_posts` permission
- Must use Page Access Token (not User token)
- Image URLs must be publicly accessible

---

### facebook_get_insights

Get Page performance metrics.

**Parameters:**
- `period` (string): "day", "week", "month", or "lifetime" (default: "week")

**Returns:**
```json
{
  "platform": "facebook",
  "page_id": "123456",
  "period": "week",
  "insights": {
    "page_impressions": {"value": 1234, "period": "week"},
    "page_engaged_users": {"value": 56, "period": "week"},
    "page_fans": {"value": 1234, "period": "lifetime"}
  }
}
```

---

### instagram_post

Post an image to Instagram Business Account.

**Parameters:**
- `image_url` (string, **required**): Publicly accessible image URL (must be reachable by Facebook)
- `caption` (string, **required**): Post caption (max 2,200 characters)
- `alt_text` (string, optional): Accessibility description

**Example:**
```json
{
  "image_url": "https://example.com/photo.jpg",
  "caption": "Beautiful sunset from today! 🌅 #photography #nature",
  "alt_text": "Orange sunset over mountain range"
}
```

**Returns:**
```json
{
  "success": true,
  "platform": "instagram",
  "media_id": "17911248696165605",
  "container_id": "17904883329370034",
  "url": "https://instagram.com/p/17911248696165605"
}
```

**Two-step process:**
1. Create media container (uploads image to Instagram) - may take a few seconds
2. Publish container (makes it live)

**Note:** Instagram requires a Facebook Page access token with `instagram_content_publish` permission and the Instagram Business Account must be linked to the Facebook Page.

---

### twitter_tweet

Post a tweet.

**Requirements:**
- Twitter OAuth 1.0a credentials (API key/secret + access token/secret)
- Read-only Bearer token won't work for posting
- App must have **Read and Write** permissions (not just Read)
- Free tier may have credit limitations

**Parameters:**
- `text` (string, **required**): Tweet content (max 280 characters)
- `media_url` (string, optional): Image/video URL to attach

**Example:**
```json
{
  "text": "Just launched our new product! 🚀 Check it out: https://example.com",
  "media_url": "https://example.com/product.jpg"
}
```

**Returns:**
```json
{
  "success": true,
  "platform": "twitter",
  "tweet_id": "1234567890123456789",
  "url": "https://twitter.com/i/web/status/1234567890123456789"
}
```

---

### twitter_get_timeline

Get recent tweets from your timeline.

**Parameters:**
- `count` (integer): Number of tweets (1-100, default: 10)

**Returns:**
```json
{
  "platform": "twitter",
  "count": 10,
  "tweets": [
    {
      "id": "123456",
      "text": "Tweet content...",
      "created_at": "2026-03-09T01:00:00Z",
      "public_metrics": {"like_count": 5, "retweet_count": 2}
    }
  ]
}
```

---

### twitter_get_mentions

Get recent tweets that mention your account.

**Parameters:**
- `count` (integer): Number of mentions (default: 10)

**Returns:**
```json
{
  "platform": "twitter",
  "user_id": "1965039369607077888",
  "count": 5,
  "mentions": [
    {
      "id": "789012",
      "text": "@yourusername Hello!",
      "author_id": "987654321",
      "created_at": "2026-03-09T01:05:00Z"
    }
  ]
}
```

---

## Usage in Claude Code

Once connected, you can ask Claude:

```
Post to our Facebook page: "New product launch! Check it out: https://example.com #excited"
```

Claude will:
1. Use `facebook_post` tool
2. Log the operation to audit trail
3. Return post ID and URL

Or:

```
Post to Instagram: image_url="https://example.com/photo.jpg" caption="Our team retreat! #team"
```

---

## Testing

### Verify Facebook connection:
```bash
cd mcp-servers/social-mcp
python check_token.py
```

Expected output:
```
✅ Token is valid
✅ Can access page
✅ POST SUCCESSFUL!
```

### Test Facebook post:
```bash
python test_facebook_post.py
```

### Test Instagram post:
```bash
python test_instagram.py
```

### Test Twitter authentication:
```bash
python test_twitter_direct.py
```

---

## Error Recovery (Phase 3)

All API calls include automatic retry and circuit breaker protection:

- **Retry**: 3 attempts with exponential backoff (2^attempt seconds, max 60s)
- **Circuit Breaker**: After 5 consecutive failures, circuit opens for 60 seconds to prevent cascade
- **State Tracking**: CLOSED → OPEN (on threshold) → HALF_OPEN (after timeout) → CLOSED (after 3 successes)

Circuit breakers are per-platform:
- `facebook_api`
- `instagram_api`
- `twitter_api`

---

## Audit Logging (Phase 3)

Every tool invocation is logged to `AI_Employee_Vault/Logs/YYYY-MM-DD.json` with full context:

```json
{
  "id": "uuid",
  "timestamp": "2026-03-09T01:20:13.890",
  "level": "info",
  "actor": "social-mcp",
  "action": "facebook_post",
  "target": "123456_789012345678901",
  "parameters": {"message": "...", "link": "..."},
  "result": {"success": true, "post_id": "..."},
  "duration_ms": 1250
}
```

On errors:
```json
{
  "actor": "social-mcp",
  "action": "twitter_tweet",
  "error": "403 Client Error: Forbidden",
  "duration_ms": 450
}
```

**Query logs:**
```python
from utils.audit.logger import get_audit_logger
logs = get_audit_logger()
entries = logs.read_logs(action="facebook_post", limit=10)
```

---

## Rate Limits

| Platform | Limit |
|----------|-------|
| Facebook Graph API | 200 calls/hour per user |
| Instagram Graph API | Shared with Facebook (200 calls/hour) |
| Twitter API v2 | 300 calls/15 min (OAuth 2.0 read) |
| Twitter POST | 50 tweets/day (rate limit bucket) |

**Implementation:** Retry logic handles 429 responses with exponential backoff. For Twitter rate limits, the code waits for the reset time indicated in headers.

---

## Troubleshooting

**Facebook "Unsupported get request"**
- Page ID or token is invalid
- Regenerate Page Access Token from Graph API Explorer

**Instagram "Invalid container" or "Only photo or video can be accepted"**
- Image URL must be publicly accessible (Facebook servers fetch it)
- Use a real image URL (not placeholder). Test: `curl -I <image_url>` should return `Content-Type: image/jpeg` or `image/png`

**Twitter "CreditsDepleted"**
- Free tier API credits exhausted. Upgrade to paid tier or wait for monthly reset.

**403 Forbidden on all platforms**
- Verify permissions are granted in app dashboard
- Token may be for a different app or user
- For Twitter: ensure app has "Read and Write" permission (not just "Read")

**"Your client app is not configured with the appropriate oauth1 app permissions"**
- Twitter: App permissions set to "Read" only. Change to "Read and Write" in Developer Portal, then regenerate Access Token & Secret.

---

## Security Notes

- Never commit `.env` or credentials to Git (already in `.gitignore`)
- Use long-lived tokens where possible (Facebook Page tokens: 60 days)
- Store tokens in secure vault (e.g., 1Password, system keychain) for production
- Rotate tokens quarterly
- Use app secrets (not personal account tokens) for production
- Limit Facebook Page roles to "Editor" (not Admin) for posting - least privilege

---

## Gold Tier Integration

This MCP server enables:
- Automated social media posting from Claude
- Engagement reporting in CEO Briefing
- Social media calendar in Dashboard
- Cross-domain workflows: Email inquiry → social response
- Integration with `post_to_social_media` Agent Skill

---

## Next Steps (Optional Enhancements)

1. **Error recovery tuning**: Adjust retry attempts or circuit breaker thresholds if needed
2. **Health monitoring**: Install `psutil` and start health server to monitor MCP server status
3. **Audit log analysis**: Build reporting tools to summarize social media activity
4. **Media upload**: Implement direct media upload for Twitter (currently only URL supported)
5. **Insights dashboard**: Create daily/weekly social media metrics reports
6. **Auto-hashtagging**: AI-powered hashtag suggestions for posts

---

*Version: 0.2-Gold (Phase 2 + Phase 3)*
*Last Updated: 2026-03-09*
*Status: ✅ Production Ready (Facebook & Instagram), ⚠️ Twitter: Ready but needs API credits*

## Tools Reference

### facebook_post

Post a message to your Facebook Page.

**Parameters:**
- `message` (string, required): Text content (max 63,000 characters)
- `link` (string, optional): URL to share
- `media_url` (string, optional): Image/video URL to attach

**Example:**
```json
{
  "message": "Check out our latest update!",
  "link": "https://example.com/blog/new-post",
  "media_url": "https://example.com/image.jpg"
}
```

---

### facebook_get_insights

Get Page performance metrics.

**Parameters:**
- `period` (string): "day", "week", or "month" (default: "week")

**Returns:**
- Page reach
- Post engagement
- Follower growth
- Page views

**Example output:**
```json
{
  "platform": "facebook",
  "page_id": "123456",
  "insights": {
    "page_impressions": {"value": 1234, "period": "week"},
    "page_engaged_users": {"value": 56, "period": "week"}
  }
}
```

---

### instagram_post

Post an image to Instagram Business Account.

**Parameters:**
- `image_url` (string, **required**): Publicly accessible image URL
- `caption` (string, **required**): Post caption (max 2,200 characters)
- `alt_text` (string, optional): Accessibility description

**Two-step process:**
1. Create media container (uploads image to Instagram)
2. Publish container (makes it live)

**Example:**
```json
{
  "image_url": "https://example.com/photo.jpg",
  "caption": "Beautiful sunset from today! #photography",
  "alt_text": "Orange sunset over mountains"
}
```

**Note:** Instagram requires a Facebook Page access token with `instagram_content_publish` permission.

---

### twitter_tweet

Post a tweet.

**Requirements:**
- Twitter OAuth 1.0a credentials (API key/secret + access token/secret)
- Read-only (Bearer token) won't work for posting.

**Parameters:**
- `text` (string, **required**): Tweet content (max 280 characters)
- `media_url` (string, optional): Image/video URL to attach

**Example:**
```json
{
  "text": "Just launched our new product! 🚀 Check it out: https://example.com",
  "media_url": "https://example.com/product.jpg"
}
```

---

### twitter_get_timeline

Get recent tweets from your timeline.

**Parameters:**
- `count` (integer): Number of tweets (1-100, default: 10)

**Returns:**
List of tweets with text, ID, creation time, metrics.

---

### twitter_get_mentions

Get recent tweets that mention your account.

**Parameters:**
- `count` (integer): Number of mentions (default: 10)

**Returns:**
List of mention tweets with author ID, text, time.

---

## Usage in Claude Code

Once connected, you can ask Claude to:

```
Post to social media: "New blog post is live! https://example.com/blog/awesome-post #marketing"
```

Claude will:
1. Determine platform (Facebook/Instagram/Twitter) based on content and settings
2. Call appropriate tool(s)
3. Log result to `/Logs/`
4. Update Dashboard with engagement metrics

## Testing

### Test Facebook connection:
```bash
# Check page access
curl "https://graph.facebook.com/v20.0/<PAGE_ID>?fields=name&access_token=<TOKEN>"
```

### Test Instagram connection:
```bash
curl "https://graph.facebook.com/v20.0/<IG_BUSINESS_ID>?fields=username&access_token=<TOKEN>"
```

### Test Twitter connection:
```bash
curl -H "Authorization: Bearer <BEARER_TOKEN>" \
  "https://api.twitter.com/2/users/me"
```

---

## Rate Limits

| Platform | Limit |
|----------|-------|
| Facebook Graph API | 200 calls/hour per user |
| Instagram Graph API | Same as Facebook (shared) |
| Twitter API v2 | 300 calls/15 min (OAuth 2.0) |
| Twitter POST | 50 tweets/day (rate limit bucket) |

**Implementation Note:** The MCP server should implement retry logic with exponential backoff for rate limit (429) responses.

---

## Error Handling

Common errors and solutions:

- **Facebook "Unsupported get request"**: Page ID or token is invalid
- **Instagram "Invalid container"**: Image URL must be publicly accessible
- **Twitter "Could not find user"**: User ID not found or token lacks permissions
- **401/403 errors**: Token expired or permissions insufficient

All errors are logged to stderr and returned as MCP error responses.

---

## Security Notes

- Never commit `.env` or credentials to Git
- Use long-lived tokens where possible
- Store tokens in secure vault (e.g., 1Password, system keychain)
- Rotate tokens quarterly
- Use app secrets (not personal account tokens) for production
- Limit Facebook Page roles to "Editor" (not Admin) for posting

---

## Gold Tier Integration

This MCP server enables:
- Automated social media posting from Claude
- Engagement reporting in CEO Briefing
- Social media calendar in Dashboard
- Cross-domain workflows: Email inquiry → social response

See also: `post_to_social_media` Agent Skill (to be created).

---

## Troubleshooting

**"Invalid OAuth access token"**
- Token expired. Regenerate long-lived token (60 days) or refresh.

**"Unsupported post request"**
- Check you're using Page Access Token (not User token) for Facebook.

**"Media URL not accessible"**
- Instagram requires image to be publicly reachable by Facebook's servers. Use a public CDN or image hosting service.

**"403 Forbidden"**
- Verify your app has the required permissions approved via App Review (Facebook/Instagram).

---

*Version: 0.1-Gold Phase 2*
*Last Updated: 2026-03-06*
