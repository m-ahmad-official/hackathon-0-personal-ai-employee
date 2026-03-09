#!/usr/bin/env python3
"""
Email → Odoo Invoice Event Consumer
Listens for email invoice requests and orchestrates cross-domain workflow.

Consumes:
- email.received (with invoice intent)

Emits:
- odoo.invoice.created
- odoo.invoice.posted
- email.sent (confirmation)

This demonstrates event-driven integration between email processing and Odoo accounting.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add paths for imports
current_file = os.path.abspath(__file__)
# Current: utils/event_bus/consumers/email_odoo_consumer.py
event_bus_dir = os.path.dirname(os.path.dirname(current_file))  # utils/event_bus
sys.path.insert(0, event_bus_dir)  # So we can import 'event' module

from event import EventConsumer, Event, EventTypes


class EmailOdooConsumer(EventConsumer):
    """Consumes email events and creates Odoo invoices when appropriate."""

    def __init__(self):
        super().__init__(name="email_odoo_integration")
        self.register_handlers()

    def register_handlers(self):
        """Register event handlers."""
        self.on(EventTypes.EMAIL_RECEIVED, self.handle_email_received)

    def handle_email_received(self, event: Event):
        """
        Process incoming email and check for invoice request intent.

        Expected email event data:
        {
            "email_id": "msg_123",
            "from": "client@example.com",
            "subject": "Please send invoice",
            "body": "Hi, please send an invoice for $500...",
            "attachments": []
        }
        """
        print(f"[EmailOdooConsumer] Processing email from {event.data.get('from')}")

        # Simple detection logic (would be more sophisticated in reality)
        subject = event.data.get('subject', '').lower()
        body = event.data.get('body', '').lower()

        invoice_keywords = ['invoice', 'bill', 'payment request', 'send invoice']
        has_invoice_intent = any(keyword in subject or keyword in body for keyword in invoice_keywords)

        if not has_invoice_intent:
            print(f"[EmailOdooConsumer] No invoice intent detected, skipping")
            return

        # Extract amount (very simple regex-like approach)
        amount = self._extract_amount(event.data.get('body', ''))
        if not amount:
            print(f"[EmailOdooConsumer] Could not extract amount, skipping")
            # Could emit event for manual review
            return

        # Extract customer email
        customer_email = event.data.get('from')

        # Extract description (first sentence or subject)
        description = subject if len(subject) > 10 else body[:100]

        # Create invoice in Odoo (would call Odoo MCP via tool invocation)
        print(f"[EmailOdooConsumer] Would create Odoo invoice:")
        print(f"  Customer: {customer_email}")
        print(f"  Amount: ${amount}")
        print(f"  Description: {description}")

        # In real implementation, would:
        # 1. Call odoo-mcp search_customers
        # 2. If not exists, create customer
        # 3. Call create_invoice
        # 4. Optionally post invoice
        # 5. Send confirmation email
        # 6. Emit events along the way

        # For demo, just emit an event showing what would happen
        self.emit_invoice_created_event(customer_email, amount, description)

    def _extract_amount(self, text: str) -> float:
        """Extract dollar amount from text (simplified)."""
        import re
        # Look for $X.XX pattern
        match = re.search(r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                return float(amount_str)
            except:
                return None
        return None

    def emit_invoice_created_event(self, customer_email: str, amount: float, description: str):
        """Emit event indicating invoice was created."""
        from event_bus.event import emit_event, EventTypes

        emit_event(
            event_type=EventTypes.INVOICE_CREATED,
            source="email_odoo_consumer",
            data={
                "customer_email": customer_email,
                "amount": amount,
                "description": description,
                "invoice_number": "INV/2026/DEMO",  # Would be real from Odoo
                "invoice_id": 999,  # Would be real from Odoo
                "status": "draft"
            },
            consumed_by=["dashboard_updater", "ceo_briefing"]
        )


def main():
    """Run the consumer."""
    consumer = EmailOdooConsumer()
    print("Email→Odoo Consumer started. Listening for email events...")
    consumer.run(poll_interval=2.0)


if __name__ == "__main__":
    main()
