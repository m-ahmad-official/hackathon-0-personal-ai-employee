# Odoo MCP Server
# Gold Tier - Phase 1
# Provides MCP tools for interacting with Odoo Community via JSON-RPC

import os
import sys
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.types import (
    CallToolRequest,
    Tool as ToolDefinition
)
import xmlrpc.client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("odoo-mcp")

# Add parent directory to path for error recovery utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'utils', 'error_recovery'))
try:
    from retry_circuit import CircuitBreaker, CircuitState
    _error_recovery_available = True
except ImportError:
    _error_recovery_available = False
    logger.warning("Error recovery utilities not available, using basic retry")

# Add parent directory to path for audit logger
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'utils', 'audit'))
try:
    from logger import log_audit
    _audit_logger_available = True
except ImportError:
    _audit_logger_available = False
    logger.warning("Audit logger not available, skipping audit trail")

# Configuration from environment
ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.getenv("ODOO_DB", "odoo")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "admin")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "admin")

class OdooMCPServer:
    """MCP Server for Odoo Community integration using JSON-RPC."""

    def __init__(self):
        self.server = Server("odoo-mcp")
        self.common = None
        self.models = None
        self.uid = None
        self._breakers: Dict[str, CircuitBreaker] = {}
        # Find project root (directory containing AI_Employee_Vault)
        current_file = os.path.abspath(__file__)
        self.project_root = None
        for parent in [Path(current_file).parent] + list(Path(current_file).parents)[:10]:
            if (parent / "AI_Employee_Vault").exists():
                self.project_root = parent
                break
        self._setup_routes()
        self._connect_to_odoo()

    def _connect_to_odoo(self):
        """Establish connection to Odoo via XML-RPC."""
        try:
            # Authenticate
            common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
            self.uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
            if not self.uid:
                raise Exception("Authentication failed")
            self.models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
            logger.info(f"Connected to Odoo as user {ODOO_USERNAME} (uid={self.uid})")
        except Exception as e:
            logger.error(f"Failed to connect to Odoo: {e}")
            raise

    def _get_circuit_breaker(self, operation: str) -> CircuitBreaker:
        """Get or create circuit breaker for Odoo operations."""
        if operation not in self._breakers and _error_recovery_available:
            self._breakers[operation] = CircuitBreaker(
                name=f"odoo_{operation}",
                failure_threshold=5,
                recovery_timeout=60,
                success_threshold=3,
                expected_exceptions=(ConnectionError, TimeoutError, xmlrpc.client.ProtocolError, xmlrpc.client.Fault)
            )
        return self._breakers.get(operation)

    def _call_odoo_with_retry(self, model: str, method: str, args: List,
                              kwargs: Optional[Dict] = None, max_attempts: int = 3) -> Any:
        """Execute Odoo XML-RPC call with retry and circuit breaker protection."""
        if kwargs is None:
            kwargs = {}
        breaker = self._get_circuit_breaker("odoo")

        def do_call():
            return self.models.execute_kw(ODOO_DB, self.uid, ODOO_PASSWORD, model, method, args, kwargs)

        if breaker:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    if breaker.state.value == "open":
                        raise Exception(f"Circuit breaker '{breaker.name}' is OPEN - Odoo unavailable")

                    result = breaker.call(do_call)
                    return result

                except (ConnectionError, TimeoutError, xmlrpc.client.ProtocolError) as e:
                    last_exception = e
                    logger.warning(f"Odoo call {model}.{method} failed (attempt {attempt+1}/{max_attempts}): {e}")
                    if attempt == max_attempts - 1:
                        raise
                    delay = min(2 ** attempt, 60)
                    time.sleep(delay)

                except xmlrpc.client.Fault as e:
                    # Retry only on server errors (5xx)
                    if e.faultCode >= 500:
                        last_exception = e
                        logger.warning(f"Odoo server error {e.faultCode} (attempt {attempt+1}/{max_attempts}): {e}")
                        if attempt == max_attempts - 1:
                            raise
                        delay = min(2 ** attempt, 60)
                        time.sleep(delay)
                    else:
                        raise

            if last_exception:
                raise last_exception
        else:
            return do_call()

    def _create_receipt(self, platform: str, action: str, external_id: str, url: Optional[str],
                       parameters: Dict, result: Dict, duration_ms: Optional[int] = None):
        """Create a receipt file in the Done folder."""
        if not self.project_root:
            logger.warning("Project root not found, cannot create receipt")
            return

        done_dir = self.project_root / "AI_Employee_Vault" / "Done"
        done_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
        filename = f"{platform.upper()}_{action.upper()}_{timestamp}.md"
        filepath = done_dir / filename

        # Build frontmatter
        frontmatter = {
            "type": "external_action",
            "platform": platform,
            "action": action,
            "external_id": external_id,
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "duration_ms": duration_ms
        }

        # Format parameters and result for readability
        params_str = json.dumps(parameters, indent=2) if parameters else "None"
        result_str = json.dumps(result, indent=2) if result else "None"

        content = f"""---
{json.dumps(frontmatter, indent=2)[1:-1]}
---

# External Action Receipt

**Platform:** {platform}
**Action:** {action}
**External ID:** {external_id}
{f"**URL:** {url}" if url else ""}
**Completed:** {frontmatter['timestamp']}
{f"**Duration:** {duration_ms}ms" if duration_ms else ""}

## Parameters
```json
{params_str}
```

## Result
```json
{result_str}
```
"""

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Created receipt: {filepath}")
        except Exception as e:
            logger.warning(f"Failed to write receipt: {e}")

    def _setup_routes(self):
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> List[ToolDefinition]:
            """Return available Odoo tools."""
            return [
                ToolDefinition(
                    name="search_customers",
                    description="Search customers/partners by email, name, or criteria",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "email": {"type": "string", "description": "Email to search"},
                            "name": {"type": "string", "description": "Name to search"},
                            "limit": {"type": "integer", "description": "Max results (default 10)"}
                        }
                    }
                ),
                ToolDefinition(
                    name="create_invoice",
                    description="Create an invoice for a customer",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "customer_email": {"type": "string", "description": "Customer email"},
                            "customer_name": {"type": "string", "description": "Customer name (if new)"},
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string", "description": "Product name"},
                                        "quantity": {"type": "number", "description": "Quantity"},
                                        "price": {"type": "number", "description": "Unit price"}
                                    },
                                    "required": ["name", "quantity", "price"]
                                }
                            },
                            "due_date": {"type": "string", "description": "Due date (YYYY-MM-DD)"}
                        },
                        "required": ["customer_email", "items"]
                    }
                ),
                ToolDefinition(
                    name="post_invoice",
                    description="Post/validate an invoice (change from draft to posted)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "invoice_id": {"type": "integer", "description": "Invoice ID to post"}
                        },
                        "required": ["invoice_id"]
                    }
                ),
                ToolDefinition(
                    name="record_payment",
                    description="Record a payment for an invoice",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "invoice_id": {"type": "integer", "description": "Invoice ID"},
                            "amount": {"type": "number", "description": "Payment amount"},
                            "payment_date": {"type": "string", "description": "Payment date (YYYY-MM-DD)"},
                            "journal": {"type": "string", "description": "Payment method (e.g., 'bank', 'cash')"}
                        },
                        "required": ["invoice_id", "amount"]
                    }
                ),
                ToolDefinition(
                    name="get_account_balance",
                    description="Get balance for a specific account (e.g., cash, receivables)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_code": {"type": "string", "description": "Account code (e.g., '121000' for AR)"}
                        },
                        "required": ["account_code"]
                    }
                ),
                ToolDefinition(
                    name="list_recent_invoices",
                    description="List recent invoices with status",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "description": "Max invoices to return (default 10)"},
                            "status": {"type": "string", "description": "Filter by status (draft, posted, paid)"}
                        }
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(request: CallToolRequest) -> List[Dict[str, Any]]:
            """Handle tool invocations."""
            tool_name = request.params.name
            arguments = request.params.arguments or {}
            start_time = time.time()

            try:
                if tool_name == "search_customers":
                    result = self._search_customers(**arguments)
                elif tool_name == "create_invoice":
                    result = self._create_invoice(**arguments)
                elif tool_name == "post_invoice":
                    result = self._post_invoice(**arguments)
                elif tool_name == "record_payment":
                    result = self._record_payment(**arguments)
                elif tool_name == "get_account_balance":
                    result = self._get_account_balance(**arguments)
                elif tool_name == "list_recent_invoices":
                    result = self._list_recent_invoices(**arguments)
                else:
                    return [{"type": "error", "text": f"Unknown tool: {tool_name}"}]

                duration_ms = int((time.time() - start_time) * 1000)

                # Audit logging for success
                if _audit_logger_available:
                    try:
                        log_audit(
                            actor="odoo-mcp",
                            action=tool_name,
                            target=result.get("invoice_id") or result.get("payment_id") or result.get("account_code"),
                            parameters=arguments,
                            result=result,
                            duration_ms=duration_ms
                        )
                    except Exception as audit_error:
                        logger.warning(f"Failed to write audit log: {audit_error}")

                return [{"type": "text", "text": json.dumps(result, indent=2)}]

            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.error(f"Error in {tool_name}: {e}", exc_info=True)

                # Audit logging for errors
                if _audit_logger_available:
                    try:
                        log_audit(
                            actor="odoo-mcp",
                            action=tool_name,
                            parameters=arguments,
                            error=str(e),
                            duration_ms=duration_ms,
                            level="error"
                        )
                    except Exception as audit_error:
                        logger.warning(f"Failed to write audit log: {audit_error}")

                return [{"type": "error", "text": f"Error: {str(e)}"}]

    def _search_customers(self, email: Optional[str] = None, name: Optional[str] = None, limit: int = 10) -> Dict:
        """Search customers by email or name with retry."""
        domain = []
        if email:
            domain.append(('email', 'ilike', email))
        if name:
            domain.append(('name', 'ilike', name))

        fields = ['id', 'name', 'email', 'phone', 'company_type', 'customer_rank']
        records = self._call_odoo_with_retry(
            model='res.partner',
            method='search_read',
            args=[domain],
            kwargs={'fields': fields, 'limit': limit}
        )
        return {
            "count": len(records),
            "customers": records
        }

    def _create_invoice(self, customer_email: str, items: List[Dict],
                       customer_name: Optional[str] = None, due_date: Optional[str] = None) -> Dict:
        """Create a draft invoice."""
        start_time = time.time()

        # 1. Find or create customer
        customer = self._find_or_create_customer(customer_email, customer_name)
        if not customer:
            raise Exception(f"Could not find or create customer with email {customer_email}")

        # 2. Create invoice
        invoice_vals = {
            'partner_id': customer['id'],
            'move_type': 'out_invoice',
            'invoice_date': due_date or '',  # Odoo will use today if empty
        }
        if due_date:
            invoice_vals['invoice_date_due'] = due_date

        invoice_id = self._call_odoo_with_retry(
            model='account.move',
            method='create',
            args=[invoice_vals]
        )

        # 3. Add invoice lines
        for item in items:
            # Find or create product
            product_id = self._get_or_create_product(item['name'], item['price'])

            line_vals = {
                'product_id': product_id,
                'quantity': item['quantity'],
                'price_unit': item['price'],
            }
            self._call_odoo_with_retry(
                model='account.move.line',
                method='create',
                args=[{'move_id': invoice_id, **line_vals}]
            )

        # 4. Return invoice details
        invoice = self._call_odoo_with_retry(
            model='account.move',
            method='read',
            args=[[invoice_id]],
            kwargs={'fields': ['name', 'partner_id', 'amount_total', 'state', 'invoice_date']}
        )[0]

        logger.info(f"Created invoice {invoice['name']} for {customer_email}")

        # Audit logging
        if _audit_logger_available:
            try:
                log_audit(
                    actor="odoo-mcp",
                    action="invoice_create",
                    target=invoice['name'],
                    parameters={"customer_email": customer_email, "items": items, "due_date": due_date},
                    result={"invoice_id": invoice_id, "amount_total": invoice['amount_total']},
                    duration_ms=int((time.time() - start_time) * 1000)
                )
            except Exception as audit_error:
                logger.warning(f"Failed to write audit log: {audit_error}")

        # Create receipt
        self._create_receipt(
            platform="odoo",
            action="invoice_create",
            external_id=str(invoice_id),
            url=f"{ODOO_URL}/web#id={invoice_id}&model=account.move&view_type=form",
            parameters={
                "customer_email": customer_email,
                "customer_name": customer_name,
                "items": items,
                "due_date": due_date
            },
            result={
                "invoice_id": invoice_id,
                "invoice_number": invoice['name'],
                "customer": invoice['partner_id'][1],
                "amount_total": invoice['amount_total']
            },
            duration_ms=int((time.time() - start_time) * 1000)
        )

        return {
            "invoice_id": invoice_id,
            "invoice_number": invoice['name'],
            "customer": invoice['partner_id'][1],
            "amount_total": invoice['amount_total'],
            "state": invoice['state'],
            "invoice_date": invoice['invoice_date']
        }

    def _post_invoice(self, invoice_id: int) -> Dict:
        """Post/validate an invoice with retry."""
        start_time = time.time()

        # Validate first (invoices must be in draft)
        invoice = self._call_odoo_with_retry(
            model='account.move',
            method='read',
            args=[[invoice_id]],
            kwargs={'fields': ['state', 'name']}
        )[0]

        if invoice['state'] != 'draft':
            return {
                "success": False,
                "error": f"Invoice {invoice_id} is not in draft state (current: {invoice['state']})"
            }

        # Post the invoice
        self._call_odoo_with_retry(
            model='account.move',
            method='action_post',
            args=[[invoice_id]]
        )

        logger.info(f"Posted invoice {invoice['name']}")

        # Audit logging
        if _audit_logger_available:
            try:
                log_audit(
                    actor="odoo-mcp",
                    action="invoice_post",
                    target=invoice['name'],
                    parameters={"invoice_id": invoice_id},
                    result={"state": "posted"},
                    duration_ms=int((time.time() - start_time) * 1000)
                )
            except Exception as audit_error:
                logger.warning(f"Failed to write audit log: {audit_error}")

        # Create receipt
        self._create_receipt(
            platform="odoo",
            action="invoice_post",
            external_id=str(invoice_id),
            url=f"{ODOO_URL}/web#id={invoice_id}&model=account.move&view_type=form",
            parameters={"invoice_id": invoice_id},
            result={"invoice_number": invoice['name'], "state": "posted"},
            duration_ms=int((time.time() - start_time) * 1000)
        )

        return {
            "success": True,
            "invoice_id": invoice_id,
            "invoice_number": invoice['name'],
            "state": "posted"
        }

    def _record_payment(self, invoice_id: int, amount: float,
                       payment_date: Optional[str] = None, journal: str = "bank") -> Dict:
        """Record a payment for an invoice with retry."""

        # Get invoice
        invoice = self._call_odoo_with_retry(
            model='account.move',
            method='read',
            args=[[invoice_id]],
            kwargs={'fields': ['name', 'amount_residual', 'move_type']}
        )[0]

        if invoice['move_type'] != 'out_invoice':
            raise Exception(f"Record {invoice_id} is not an invoice")

        # Create payment
        payment_vals = {
            'partner_id': invoice['partner_id'][0],
            'amount': amount,
            'payment_date': payment_date or '',
            'journal_id': self._get_journal_id(journal),
            'payment_type': 'inbound',
            'ref': f"Payment for {invoice['name']}",
        }

        payment_id = self._call_odoo_with_retry(
            model='account.payment',
            method='create',
            args=[payment_vals]
        )

        # Post payment and reconcile
        self._call_odoo_with_retry(
            model='account.payment',
            method='action_post',
            args=[[payment_id]]
        )

        logger.info(f"Recorded payment of ${amount} for invoice {invoice['name']}")
        return {
            "payment_id": payment_id,
            "invoice_id": invoice_id,
            "amount": amount,
            "journal": journal
        }

    def _get_account_balance(self, account_code: str) -> Dict:
        """Get balance for an account code with retry."""
        # Search for account by code
        account_ids = self._call_odoo_with_retry(
            model='account.account',
            method='search',
            args=[[['code', '=', account_code]]]
        )

        if not account_ids:
            return {"error": f"Account with code {account_code} not found"}

        # Get account info (balance field not directly available in Odoo 19)
        account = self._call_odoo_with_retry(
            model='account.account',
            method='read',
            args=[account_ids],
            kwargs={'fields': ['code', 'name']}
        )[0]

        # Compute balance from posted move lines
        domain = [
            ('account_id', '=', account_ids[0]),
            ('parent_state', '=', 'posted')
        ]
        move_lines = self._call_odoo_with_retry(
            model='account.move.line',
            method='search_read',
            args=[domain],
            kwargs={'fields': ['balance']}
        )
        total_balance = sum(ml.get('balance', 0) for ml in move_lines)

        return {
            "account_code": account['code'],
            "account_name": account['name'],
            "balance": total_balance
        }

    def _list_recent_invoices(self, limit: int = 10, status: Optional[str] = None) -> Dict:
        """List recent invoices with retry."""
        domain = []
        if status:
            domain.append(('state', '=', status))

        fields = ['name', 'partner_id', 'invoice_date', 'amount_total', 'state', 'payment_state']
        records = self._call_odoo_with_retry(
            model='account.move',
            method='search_read',
            args=[domain],
            kwargs={'fields': fields, 'limit': limit, 'order': 'invoice_date desc'}
        )

        return {
            "count": len(records),
            "invoices": records
        }

    def _find_or_create_customer(self, email: str, name: Optional[str] = None) -> Optional[Dict]:
        """Find customer by email, or create if not exists with retry."""
        # Search by email
        customer_ids = self._call_odoo_with_retry(
            model='res.partner',
            method='search',
            args=[[['email', '=', email]]]
        )

        if customer_ids:
            customer = self._call_odoo_with_retry(
                model='res.partner',
                method='read',
                args=[customer_ids],
                kwargs={'fields': ['id', 'name', 'email', 'customer_rank']}
            )[0]
            logger.info(f"Found existing customer: {email}")
            return customer

        # Create new customer
        if not name:
            name = email.split('@')[0]

        customer_id = self._call_odoo_with_retry(
            model='res.partner',
            method='create',
            args=[{
                'name': name,
                'email': email,
                'company_type': 'person',
                'customer_rank': 1  # Mark as customer
            }]
        )
        logger.info(f"Created new customer: {email}")
        return {'id': customer_id, 'name': name, 'email': email, 'customer_rank': 1}

    def _get_or_create_product(self, name: str, price: float) -> int:
        """Find or create a product with retry."""
        # Search by name
        product_ids = self._call_odoo_with_retry(
            model='product.product',
            method='search',
            args=[[['name', '=', name]]]
        )

        if product_ids:
            return product_ids[0]

        # Create new service product
        product_id = self._call_odoo_with_retry(
            model='product.product',
            method='create',
            args=[{
                'name': name,
                'type': 'service',
                'list_price': price,
                'sale_ok': True,
                'purchase_ok': False
            }]
        )
        return product_id

    def _get_journal_id(self, journal_name: str) -> int:
        """Get journal ID by name with retry."""
        journal_ids = self._call_odoo_with_retry(
            model='account.journal',
            method='search',
            args=[[['name', 'ilike', journal_name]]]
        )
        if not journal_ids:
            raise Exception(f"Journal '{journal_name}' not found")
        return journal_ids[0]

    async def run(self):
        """Run the MCP server."""
        from mcp.server.stdio import stdio_server
        logger.info("Starting Odoo MCP Server...")
        async with stdio_server() as (read_stream, write_stream):
            logger.info("Odoo MCP Server is running")
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    """Entry point for the Odoo MCP server."""
    server = OdooMCPServer()
    import asyncio
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
