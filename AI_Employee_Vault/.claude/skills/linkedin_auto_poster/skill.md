# LinkedIn Auto-Poster Skill

**Silver Tier Agent Skill** - Automatically create and post LinkedIn updates about business activities to generate sales leads.

---

## Description

This skill automates LinkedIn posting to maintain an active business presence. It generates professional posts based on business activities, project updates, or industry insights, and posts them to LinkedIn either automatically (with approval) or via HITL workflow.

**Purpose**: Generate sales leads and maintain professional visibility without manual effort.

---

## Usage

```
/skill linkedin_auto_poster [--create-post] [--draft-only] [--schedule WHEN] [--list-queued]
```

---

## Behavior

### 1. Create and Post (`--create-post`)

Generates a LinkedIn post based on recent business activity and posts it.

**Example:**
```
/skill linkedin_auto_poster --create-post
```

**What it does:**
1. Reads `Business_Goals.md` and `Dashboard.md` to understand current state
2. Scans `/Done/` for completed tasks this week
3. Generates professional post content (3-5 paragraphs)
4. Checks Company_Handbook for branding guidelines
5. **If auto-approve enabled**: Uses Playwright MCP to post immediately
6. **If approval required**: Creates approval request in `/Pending_Approval/`

**Post content typically includes:**
- Recent project completion
- Lessons learned
- Call to action (CTA)
- Relevant hashtags
- @mentions if appropriate

---

### 2. Draft Only (`--draft-only`)

Creates post but saves as draft in `/Plans/` for human review before posting.

**Example:**
```
/skill linkedin_auto_poster --draft-only --schedule "tomorrow at 9am"
```

**Output:**
Creates `DRAFT_LINKEDIN_<date>.md` in `/Plans/` with:
- Full post content
- Suggested image (if applicable)
- Optimal posting time
- Target hashtags

Human can then approve or edit.

---

### 3. Schedule Post (`--schedule WHEN`)

Schedules a post for future publication.

**Parameters:**
- `WHEN` - When to post (natural language or ISO 8601)
  - `"tomorrow at 9am"`
  - `"2026-02-25T14:00:00"`
  - `"next monday"`

**Example:**
```
/skill linkedin_auto_poster --create-post --schedule "next monday at 10am"
```

Creates scheduled post metadata and adds to posting calendar (stored in `/Plans/` or external scheduler).

---

### 4. List Queued Posts (`--list-queued`)

Shows all posts pending approval or scheduled.

**Example:**
```
/skill linkedin_auto_poster --list-queued
```

---

## Post Generation Logic

### Content Sources (priority order):

1. **Project Completions** (highest priority)
   - Read `/Done/` tasks from past week
   - Extract achievements, outcomes, metrics
   - Turn into success story

2. **Business Milestones**
   - Check `Business_Goals.md` progress
   - Revenue milestones
   - Client acquisitions

3. **Industry Insights** (if no activity)
   - Share news/trends in your field
   - Comment on relevant topics
   - Add your perspective

### Post Structure:

```
🎯 [HOOK - 1 sentence grabbing attention]

[Body - 2-3 paragraphs with context, details, value]

📈 [Results/Metrics if available]
- Completed X project resulting in Y outcome
- Saved Z hours or $ amount

💡 [Lesson learned or insight]

## [Call to Action]
- "What are your thoughts?"
- "DM me if interested"
- "Book a call: [link]"

#Hashtag1 #Hashtag2 #Industry #Business
```

---

## Posting Mechanics

### Using Playwright MCP

The skill uses the `browsing-with-playwright` MCP server (already available) to:

1. Navigate to LinkedIn post creation page
2. Fill in post content field
3. Add hashtags (auto-linkified by LinkedIn)
4. Add media if specified (image upload)
5. Set visibility (public/connections-only)
6. Click "Post" (requires approval unless auto-approve)

**Required MCP tools:**
- `browser_navigate` - Go to LinkedIn
- `browser_snapshot` - Get form elements
- `browser_type` - Enter post content
- `browser_click` - Click Post button
- `browser_take_screenshot` - Capture confirmation

---

## Approval Workflow

**When approval is required** (default per Handbook):

1. Skill creates `POST_LinkedIn_<topic>_<timestamp>.md` in `/Pending_Approval/`
2. Human reviews content
3. Human moves to `/Approved/` to execute, `/Rejected/` to cancel
4. Orchestrator (or this skill) monitors `/Approved/` and triggers posting via MCP
5. Once posted, file moved to `/Done/` and Dashboard updated

**Approval criteria** (configurable in `Company_Handbook.md`):
- Any external-facing post → Always approve (recommended)
- Internal/project update only → Auto-approve
- Contains client names → Always approve
- Contains financial numbers → Always approve

---

## Configuration

### In `Company_Handbook.md` add:

```yaml
linkedin_posting:
  enabled: true
  auto_approve: false  # Set true for no approval needed
  frequency: "twice_weekly"  # daily, weekly, twice_weekly
  optimal_time: "10:00"  # 10am local time
  hashtags: ["AI", "Automation", "Business", "Entrepreneur"]
  mention_company: false
  require_media: false
```

---

## File Naming

```
LinkedIn Posts:
  - DRAFT_LINKEDIN_<topic>_<YYYYMMDD_HHMMSS>.md (drafts in /Plans/)
  - POST_LinkedIn_<topic>_<YYYYMMDD_HHMMSS>.md (pending approval)
  - APPROVED_POST_LinkedIn_<topic>_<YYYYMMDD_HHMMSS>.md (in /Approved/)
  - REJECTED_POST_LinkedIn_<topic>_<YYYYMMDD_HHMMSS>.md (in /Rejected/)
  - POSTED_LinkedIn_<topic>_<YYYYMMDD_HHMMSS>.md (in /Done/)

Logs:
  - /Logs/YYYY-MM-DD.json (audit entry)
  -linkedin_poster.log (detailed log)
```

---

## Example Generated Post

**DRAFT_LINKEDIN_automation_20260224_010000.md:**

```markdown
---
type: linkedin_post
status: draft
created: 2026-02-24T01:00:00Z
scheduled_for: null
hashtags: ["AI", "Automation", "Productivity", "Business"]
media: null
---

# Just automated my entire invoicing workflow! 🤖

For the past 3 months, I've been tracking time spent on admin tasks. The result? 15 hours per week just on invoices, follow-ups, and payment tracking.

This week, I deployed my AI Employee to handle it. Here's what happened:

✅ Invoices generated automatically
✅ Payment reminders sent on schedule
✅ All data logged to my Odoo instance
✅ Zero manual intervention needed

**The result?** I reclaimed 15 hours to focus on client work. That's 60 hours per month of billable time I was missing out on.

📊 Key takeaway: Automation isn't just about efficiency—it's about opportunity cost. Every hour spent on manual work is an hour not spent on revenue-generating activities.

🔧 Tech stack: Claude Code + Obsidian + Odoo + Python

💡 Want to build your own? I'm documenting the journey at [link to blog/GitHub]

What administrative tasks are eating up your time? Drop a comment below 👇

#AI #Automation #Productivity #Entrepreneurship #BusinessAutomation
```

---

## Integration with Dashboard

After posting, Dashboard.md is updated:

```markdown
## Recent LinkedIn Activity
- ✅ "Automation Savings" posted 2026-02-24 01:30 (12 likes, 3 comments)
- ✅ "New Client Onboarding" posted 2026-02-22 10:00 (8 likes)

## Posting Schedule
- Next: 2026-02-26 10:00 AM (draft ready for approval)
```

---

## Error Handling

- **LinkedIn login expired**: Skill detects login page → creates approval request for manual login
- **Rate limits**: Space out posts (minimum 4 hours between posts)
- **Post failed**: Retry up to 3 times, then flag for manual review
- **Content generation failure**: Use template fallback, flag error in Dashboard

---

## Frequency Limits

Per LinkedIn best practices (to avoid shadow-banning):
- **Maximum**: 1 post/day (default)
- **Minimum**: 4 hours between posts
- **Business pages** vs **personal profile**: Configurable

Configure in `Company_Handbook.md`:

```yaml
linkedin_posting:
  max_posts_per_day: 1
  min_hours_between: 4
  posting_window: ["09:00", "17:00"]  # Only post during business hours
```

---

## Testing

### Test 1: Draft only (no posting)
```
/skill linkedin_auto_poster --draft-only
```
Check `/Plans/` for draft file.

### Test 2: Preview content
```
/skill linkedin_auto_poster --create-post --dry-run
```
Generates content and logs but doesn't post.

### Test 3: Full workflow
```
/skill linkedin_auto_poster --create-post
```
→ Creates approval request (if approval enabled)
→ Human approves
→ Posts to LinkedIn

---

## Dependencies

- Playwright MCP server (`browsing-with-playwright` skill)
- LinkedIn account (credentials stored in browser session)
- Active internet connection

---

## Security & Privacy

⚠ **Important**:
- LinkedIn credentials stored in browser session (Playwright persistent context)
- Session stored in `./session` directory - keep secure
- All posts represent your professional brand - review before approval
- Never auto-approve without content filtering

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| LinkedIn login page appears | You're not logged in. Run Playwright MCP, manually log in first, save session |
| Post truncated | LinkedIn has character limit (3000). Skill should respect this |
| Hashtags not linking | LinkedIn auto-linkifies on post - ensure spacing |
| Rate limited | Wait 24h, reduce posting frequency |

---

## Future Enhancements (Gold Tier)

- Analytics tracking (likes, comments, impressions)
- A/B testing of post times/content
- Auto-engagement (responding to comments)
- LinkedIn API integration (instead of Playwright)
- Multi-account support (personal + company page)
- Content calendar with drag-and-drop rescheduling

---

## References

- Company_Handbook.md - Branding and approval guidelines
- Hackathon: Silver Tier Requirement #3
- Playwright MCP skill for browser automation

---

*Skill: linkedin_auto_poster*
*Version: 1.0-Silver*
*Last Updated: 2026-02-24*
