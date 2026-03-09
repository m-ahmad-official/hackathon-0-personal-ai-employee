# MCP Servers - Gold Tier

This directory contains Model Context Protocol (MCP) servers for Gold Tier integrations.

## Servers

### 1. Odoo MCP (`odoo-mcp/`) ✅ **WORKING**

Provides tools for interacting with Odoo Community (accounting, CRM, sales). Fully tested and functional with Odoo 19.

**Tools:**
- `search_customers` - Find customers by email/name
- `create_invoice` - Create draft invoices
- `post_invoice` - Post/validate invoices
- `record_payment` - Record payments
- `get_account_balance` - Query account balances
- `list_recent_invoices` - List recent invoices

**Status:** ✅ Complete and tested

**Quick Start:**
```bash
cd odoo-mcp
pip install -r requirements.txt
docker-compose up -d  # Start Odoo
python test_connection.py  # Verify setup
```

**Configuration:** See `odoo-mcp/README.md`

---

### 2. Social Media MCP (`social-mcp/`) ✅ **WORKING**

Unified API for Facebook, Instagram, and Twitter. All core functionality working.

**Tools:**
- `facebook_post` - Post to Facebook Page
- `facebook_get_insights` - Get page insights
- `instagram_post` - Post images to Instagram Business
- `twitter_tweet` - Post tweets (requires API credits)
- `twitter_get_timeline` - Get recent tweets
- `twitter_get_mentions` - Get mentions

**Status:**
- ✅ Facebook: Tested and working
- ✅ Instagram: Tested and working
- ⚠️ Twitter: Implementation complete, but requires API credits to post (free tier exhausted)

**Quick Start:**
```bash
cd social-mcp
pip install -r requirements.txt
# Configure .env with API credentials
python test_facebook_post.py  # Test Facebook
python test_instagram.py  # Test Instagram
```

**Configuration:** See `social-mcp/README.md`

---

### 3. Features Implemented (Phase 3)

The following are **implemented and integrated** but can be tested later:

- ✅ **Error Recovery**: Retry logic (exponential backoff), circuit breakers
- ✅ **Audit Logging**: Structured JSON logs with rotation and querying
- ✅ **Health Monitoring**: HTTP endpoints for production monitoring

See documentation: `../GOLD_TIER_PHASE3.md` and `../PHASE3_SUMMARY.md`


---

## Adding New Servers

Each server should follow this structure:

```
server-name/
├── server.py           # Main MCP server implementation
├── requirements.txt    # Python dependencies (if Python)
├── package.json        # Node dependencies (if Node.js)
├── README.md           # Documentation
├── test_*.py           # Test scripts
└── .env.example        # Environment variables template
```

**Registration:** Add to `~/.config/claude-code/mcp.json`:

```json
{
  "servers": [
    {
      "name": "server-name",
      "command": "python",  # or "node"
      "args": ["/path/to/server.py"],
      "env": {
        "VAR1": "value1",
        "VAR2": "value2"
      }
    }
  ]
}
```

---

## Development Guidelines

1. **Use stdio transport**: MCP servers communicate via stdin/stdout
2. **JSON-RPC protocol**: Follow MCP specification
3. **Error handling**: Return errors in MCP format, log to stderr
4. **Logging**: Use stderr for logs, stdout for MCP message only
5. **Async**: Use async/await for handlers (non-blocking)
6. **Authentication**: Use env vars or config files (never hardcode secrets)
7. **Testing**: Provide test scripts that simulate MCP calls

---

## Security

- Never commit credentials
- Use environment variables or `.env` files
- Add `.env` to `.gitignore`
- Restrict MCP server binding to localhost
- Implement rate limiting for external APIs

---

## Resources

- MCP Specification: https://github.com/anthropics/mcp
- Claude Code MCP: https://agentfactory.panaversity.org/docs/AI-Tool-Landscape/mcp-servers
