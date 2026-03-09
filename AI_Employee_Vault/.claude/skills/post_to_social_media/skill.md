# Post to Social Media
**Gold Tier Skill** - Unified posting to Facebook, Instagram, and Twitter

---

## Description

This skill provides a single interface to post content to multiple social media platforms simultaneously. It intelligently formats content for each platform's best practices.

**Platforms Supported:**
- **Facebook**: Text posts, links, images
- **Instagram**: Images with captions (max 2,200 chars, hashtag-friendly)
- **Twitter/X**: Tweets (max 280 chars), optionally with media

**Gold Tier Capability:** Cross-platform social media automation with engagement tracking.

---

## Usage

```
/skill post_to_social_media [--text CONTENT] [--image URL] [--dry-run]
```

---

## Behavior

### 1. Content Analysis

The skill analyzes the content to determine:
- **Platform selection**: All configured platforms, or specific via `--platform`
- **Content type**: Text-only, link, image
- **Hashtag optimization**: Extract hashtags, ensure relevance
- **Length adaptation**: Truncate for Twitter, expand for Instagram

### 2. Platform-Specific Formatting

**Facebook:**
- Full content preserved (up to 63,000 chars)
- Links auto-expand with preview
- Images uploaded separately

**Instagram:**
- Caption optimized: hook, line, CTA, 3-5 hashtags
- Alt text generated for accessibility
- Image must be public URL

**Twitter:**
- Content truncated to 280 chars intelligently (preserve key info, shorten URLs)
- Media attachment supported (1 image, or 1 GIF, or up to 4 images in video)
- Thread support (if content > 280, create threaded tweets)

### 3. Execution Order

1. **Post to Facebook** (if configured)
2. **Post to Instagram** (if image + IG configured)
3. **Post to Twitter** (if configured)

All posts happen in parallel (async) where possible.

### 4. Engagement Reporting (24 hours later)

Optional: Schedule follow-up to get insights:
- Facebook: Reach, engagement, clicks
- Instagram: Likes, comments, shares
- Twitter: Impressions, likes, retweets, replies

---

## Parameters

### `--text` or `-t`
Text content to post. Required unless reading from stdin.

```
--text "New product launch! Check it out: https://example.com #newproduct"
```

### `--image` or `-i`
Image URL to attach. Required for Instagram posts.

```
--image "https://example.com/product.jpg"
```

### `--platform` or `-p`
Target specific platform(s). Default: all configured.

```
--platform facebook,twitter  # Only FB and Twitter
--platform instagram         # Only Instagram
```

### `--link` or `-l`
URL to share (Facebook only).

```
--link "https://example.com/blog/new-post"
```

### `--dry-run`
Preview the post without actually publishing.

---

## Examples

### Example 1: Multi-platform launch announcement
```
/skill post_to_social_media --text "We're thrilled to announce v2.0! 🎉 New features: dashboard, reports, API. Try it free: https://example.com" --image "https://example.com/screenshot.png"
```

**What happens:**
- Facebook: Full text + image + link
- Instagram: Caption with hook + hashtags + image
- Twitter: Condensed text + image + shortened link

---

### Example 2: Text-only Twitter update
```
/skill post_to_social_media --platform twitter --text "Just shipped a new feature! Thread 🧵 1/3"
```

---

### Example 3: Instagram-only (image required)
```
/skill post_to_social_media --platform instagram --image "https://example.com/photo.jpg" --text "Sunset view from the office. #worklife #sunset"
```

---

## Input Sources

The skill can accept content from:
- Stdin (pipe)
- File (--from FILE)
- Direct arguments (--text, --image)

**Pipe example:**
```bash
echo "Hello from AI Employee!" | /skill post_to_social_media
```

---

## Configuration

In `Company_Handbook.md`, add:

```yaml
social_media:
  platforms:
    facebook:
      enabled: true
      auto_post: false  # Require approval?
    instagram:
      enabled: true
      requires_image: true
    twitter:
      enabled: true
      max_hashtags: 3
  hashtag_strategy:
    auto_generate: true
    include_brand: ["aiegoal", "aiemployee"]  # Always include
    max_per_post: 5
  approval_required:
    - instagram  # Always approve IG posts
    - facebook:  # FB posts over 1000 chars
      threshold: 1000
```

---

## Approval Workflow

Sensitive posts require human approval:

1. Claude detects `--platform instagram` or Facebook post with link
2. Creates approval request in `/Pending_Approval/`
3. Human reviews and moves to `/Approved/` or `/Rejected/`
4. If approved, executor publishes
5. Engagement metrics fetched 24h later

---

## Data Sources

Claude can pull content from:
- `Business_Goals.md` - Marketing campaigns, messaging
- `Dashboard.md` - Current metrics to share
- `/Briefings/` - Weekly highlights to amplify
- Email threads (via `process_email_requests`) - Customer testimonials

---

## Error Handling

- **Rate limit**: If API returns 429, wait and retry (exponential backoff)
- **Media failure**: If image URL invalid, fall back to text-only
- **Platform unavailable**: Skip platform, log error, continue with others
- **Token expired**: Alert human, pause all social posting until fixed

---

## Output

- Post IDs and URLs logged to `/Logs/`
- Dashboard updated with latest post counts
- Engagement report generated after 24h (if configured)

---

## Integration

This skill works with:
- `generate_weekly_briefing` - Pulls social metrics for CEO report
- `approval_workflow` - Human review for sensitive posts
- `process_email_requests` - Can auto-share customer testimonials
- Dashboard - Shows social stats widget

---

## Testing

### Test 1: Dry run
```
/skill post_to_social_media --text "Test post" --dry-run
```
Shows what would be posted to each platform.

### Test 2: Real post (with approval)
```
/skill post_to_social_media --text "Hello world!" --platform twitter
```
Creates approval request if needed, then posts.

### Test 3: Image post
```
/skill post_to_social_media --image "https://example.com/test.jpg" --text "Testing image post"
```

---

## Gold Tier Requirement

This fulfills:
- ✅ Facebook integration (posting + insights)
- ✅ Instagram integration (image posting)
- ✅ Twitter integration (tweeting + timeline)
- ✅ Multiple MCP servers (social-mcp separate from odoo-mcp)
- ✅ All AI functionality as Agent Skills

---

## Future Enhancements (Platinum)

- Multi-image carousel posts (Instagram, Facebook)
- Video posting
- Scheduled posting queue
- Hashtag performance analytics
- Auto-response to comments/DMs
- Competitor monitoring
- Sentiment analysis on mentions

---

## References

- Facebook Graph API: https://developers.facebook.com/docs/graph-api
- Instagram Graph API: https://developers.facebook.com/docs/instagram-api
- Twitter API v2: https://developer.twitter.com/en/docs/twitter-api

---

*Skill: post_to_social_media*
*Version: 0.1-Gold*
*Last Updated: 2026-03-06*
