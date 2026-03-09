# Gold Tier Implementation - Phase 1 Complete

**Status:** In Progress
**Started:** 2026-03-06
**Target:** Foundation components (Odoo MCP, Ralph Wiggum Loop, MCP Architecture)

---

## Phase 1 Objectives

✅ Create MCP servers directory structure
✅ Build Odoo MCP server with 6 core tools
✅ Implement Ralph Wiggum stop hook with file-based completion
✅ Set up Odoo Docker environment with docker-compose
✅ Create test scripts and setup automation
✅ Document installation and usage

---

## Directory Structure Created

```
mcp-servers/
└── odoo-mcp/
    ├── server.py              # Main MCP server (Odoo JSON-RPC)
    ├── requirements.txt       # Python dependencies
    ├── docker-compose.yml     # Odoo + PostgreSQL
    ├── setup_odoo.py          # Automated Odoo setup
    ├── test_connection.py     # Connection validation
    └── README.md              # Server documentation

AI_Employee_Vault/
└── .claude/
    └── stop-hooks/
        └── ralph_wiggum.py   # Autonomous loop handler
```

---

## Components Implemented

### 1. Odoo MCP Server (`mcp-servers/odoo-mcp/server.py`)

A full-featured MCP server providing 6 tools for Odoo integration:

**Tools:**
- `search_customers` - Find customers by email/name
- `create_invoice` - Generate draft invoices with line items
- `post_invoice` - Validate/post invoices
- `record_payment` - Log payments against invoices
- `get_account_balance` - Query account balances (AR, Cash, etc.)
- `list_recent_invoices` - Get recent invoices with status

**Features:**
- Automatic customer lookup/creation
- Product auto-creation on invoice
- Journal detection for payments
- Comprehensive error handling
- Structured JSON responses

**Authentication:**
- Username/password via environment variables
- OAuth2 / API key ready (future enhancement)

---

### 2. Ralph Wiggum Stop Hook (`AI_Employee_Vault/.claude/stop-hooks/ralph_wiggum.py`)

Implements file-based completion detection:

**Mechanism:**
- State file: `AI_Employee_Vault/.claude/loop_state.json`
- Tracks: current iteration, max iterations, task_id
- Checks completion: Does `/Plans/PLAN_*.md` move to `/Done/`?
- Checks pending work: Items in `/Needs_Action/`
- Auto-continues until task done or max iterations reached

**Configuration:**
```json
{
  "looping": true,
  "task_id": "invoice_20260306",
  "max_iterations": 10,
  "current_iteration": 0
}
```

**Usage:**
Start Claude Code with the stop hook enabled. When Claude tries to exit, the hook:
- Checks if task marked complete
- If not, returns `{"action": "continue"}` - Claude stays running
- If complete or max iterations reached, returns `{"action": "exit"}`

---

### 3. Odoo Docker Environment

`docker-compose.yml` provides:
- Odoo 19 Community
- PostgreSQL 15
- Persistent volumes
- Health checks
- Ready for accounting module installation

**Start:**
```bash
cd mcp-servers/odoo-mcp
docker-compose up -d
```

Access: http://localhost:8069
Admin: admin / admin

---

### 4. Setup Automation

**`setup_odoo.py`:**
- Installs required modules (account, sale, crm, purchase)
- Loads chart of accounts template
- Creates test customer
- Verifies user permissions
- Provides diagnostic output

**`test_connection.py`:**
- Tests Odoo connectivity
- Validates authentication
- Tests customer search
- Tests invoice creation (with cleanup)
- Tests account balance query
- Returns pass/fail summary

---

## Next Steps (Phase 2 Preparation)

1. **Install Odoo:**
   ```bash
   cd mcp-servers/odoo-mcp
   docker-compose up -d
   python setup_odoo.py
   python test_connection.py
   ```

2. **Create MCP Server Configuration:**
   Edit `~/.config/claude-code/mcp.json`:
   ```json
   {
     "servers": [
       {
         "name": "odoo",
         "command": "python",
         "args": ["/full/path/to/mcp-servers/odoo-mcp/server.py"],
         "env": {
           "ODOO_URL": "http://localhost:8069",
           "ODOO_DB": "odoo",
           "ODOO_USERNAME": "admin",
           "ODOO_PASSWORD": "admin"
         }
       }
     ]
   }
   ```

3. **Test with Claude Code:**
   ```bash
   claude .
   ```
   Ask: "Can you search for customers in Odoo with email test.client@example.com?"

4. **Create Agent Skill:**
   Build `AI_Employee_Vault/.claude/skills/manage_odoo_accounting/skill.md`
   That wraps the MCP tools into a cohesive skill for CEO briefing integration.

---

## Phase 1 Checklist

- [x] MCP server directory created
- [x] Odoo MCP server implemented (6 tools)
- [x] Requirements file
- [x] Docker compose for Odoo
- [x] Odoo setup script
- [x] Connection test script
- [x] Odoo MCP README
- [x] Ralph Wiggum stop hook implemented
- [x] State management with file-based completion
- [x] Documentation for Phase 1

---

## Phase 2 Roadmap

**Social Media MCP Server**
- Facebook/Instagram Graph API
- Twitter (X) API v2
- Post creation with media
- Insights retrieval
- Rate limit handling

**Skills Development**
- `post_to_social_media` - Unified social posting
- `analyze_social_engagement` - Insights reports
- `manage_odoo_accounting` - Full accounting workflow

**Dashboard Integration**
- Odoo financial widgets (AR balance, recent invoices)
- Social media stats (last posts, engagement)
- Cross-domain task board

**Enhanced Briefings**
- Odoo P&L integration
- Revenue recognition
- KPI dashboards
- Historical trends

---

## Testing Instructions

### Test Odoo MCP Server (standalone):

```bash
# Start Odoo
cd mcp-servers/odoo-mcp
docker-compose up -d

# Wait 30 seconds for Odoo to be ready
sleep 30

# Run setup
python setup_odoo.py

# Run connection tests
python test_connection.py
```

Expected output:
```
✅ Connected as admin (uid=2)
✅ Found 1 customer(s)
✅ Created draft invoice ID: 123
✅ Cleaned up test invoice
```

### Test Ralph Wiggum Hook:

```bash
# Create a dummy loop state
mkdir -p AI_Employee_Vault/.claude
echo '{"looping": true, "task_id": "test123", "max_iterations": 10, "current_iteration": 0}' > AI_Employee_Vault/.claude/loop_state.json

# Ensure a PLAN file exists in Done (simulate completion)
touch AI_Employee_Vault/Done/PLAN_test123_$(date +%s).md

# Test hook
python AI_Employee_Vault/.claude/stop-hooks/ralph_wiggum.py
# Should return: {"action": "exit", "reason": "Task test123 completed..."}
```

---

## Notes

- Odoo MCP server uses XML-RPC (Odoo's standard external API)
- Designed for Odoo 19+ (should work with 17+)
- No MCP library dependency yet (using stanford's MCP reference implementation in Claude Code)
- Ralph Wiggum hook uses file movement as completion signal (robust, no Promises needed)
- All sensitive credentials should be in `.env` (not committed)

---

## Resources

- Odoo External API: https://www.odoo.com/documentation/19.0/developer/reference/external_api.html
- MCP Reference: https://github.com/anthropic/mcp
- Docker Odoo: https://hub.docker.com/_/odoo

---

*Phase 1 Complete - Ready for Phase 2: Social Media Integration*
