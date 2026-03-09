#!/usr/bin/env python3
"""
Dashboard Event Consumer - Phase 4
Listens for events and updates dashboard metrics in real-time.

Consumes:
- odoo.invoice.created
- odoo.invoice.posted
- odoo.payment.recorded
- social.post.published
- task.completed
- system.health.alert

Triggers immediate dashboard refresh when significant events occur.
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add paths for imports
current_file = os.path.abspath(__file__)
# Current: utils/event_bus/consumers/dashboard_consumer.py
event_bus_dir = os.path.dirname(os.path.dirname(current_file))  # utils/event_bus
utils_dir = os.path.dirname(event_bus_dir)                     # utils
project_root = os.path.dirname(utils_dir)                      # project root

sys.path.insert(0, event_bus_dir)   # So we can import 'event' module
sys.path.insert(0, utils_dir)       # So we can import 'dashboard_updater'
sys.path.insert(0, project_root)   # For any other project modules

from event import EventConsumer, Event, EventTypes
from utils.dashboard_updater import update_dashboard, generate_metrics_section, fetch_health_metrics, fetch_odoo_metrics, fetch_social_metrics, fetch_task_metrics


class DashboardEventConsumer(EventConsumer):
    """Consumer that updates dashboard on relevant events."""

    def __init__(self, vault_path: str = "AI_Employee_Vault"):
        super().__init__(name="dashboard_updater")
        self.vault_path = Path(vault_path)
        self.dashboard_path = self.vault_path / "Dashboard.md"

        # Register handlers
        self.register_handlers()

    def register_handlers(self):
        """Register event handlers."""
        # Financial events
        self.on(EventTypes.INVOICE_CREATED, self.handle_invoice_created)
        self.on(EventTypes.INVOICE_POSTED, self.handle_invoice_posted)
        self.on(EventTypes.PAYMENT_RECORDED, self.handle_payment_recorded)

        # Social events
        self.on(EventTypes.POST_PUBLISHED, self.handle_post_published)

        # Task events
        self.on(EventTypes.TASK_COMPLETED, self.handle_task_completed)

        # System events
        self.on(EventTypes.COMPONENT_DEGRADED, self.handle_system_alert)
        self.on(EventTypes.COMPONENT_RECOVERED, self.handle_system_alert)

        # Wildcard for any other events
        self.on("*", self.handle_generic)

    def handle_invoice_created(self, event: Event):
        """Handle new invoice creation."""
        print(f"[Dashboard] Invoice created: {event.data.get('invoice_number')}")
        self.trigger_update()

    def handle_invoice_posted(self, event: Event):
        """Handle invoice posting."""
        print(f"[Dashboard] Invoice posted: {event.data.get('invoice_number')}")
        self.trigger_update()

    def handle_payment_recorded(self, event: Event):
        """Handle payment recorded."""
        print(f"[Dashboard] Payment recorded: {event.data.get('amount')} for invoice {event.data.get('invoice_id')}")
        self.trigger_update()

    def handle_post_published(self, event: Event):
        """Handle social media post."""
        platform = event.data.get('platform', 'social')
        print(f"[Dashboard] Social post published on {platform}")
        self.trigger_update()

    def handle_task_completed(self, event: Event):
        """Handle task completion."""
        print(f"[Dashboard] Task completed: {event.data.get('task_type')}")
        self.trigger_update()

    def handle_system_alert(self, event: Event):
        """Handle system health alerts."""
        print(f"[Dashboard] System alert: {event.type}")
        self.trigger_update()

    def handle_generic(self, event: Event):
        """Handle any unhandled event types."""
        # Only refresh for significant events, not every single one
        if event.priority in ("high", "critical"):
            print(f"[Dashboard] High priority event: {event.type}")
            self.trigger_update()

    def trigger_update(self):
        """Trigger immediate dashboard update."""
        try:
            # Fetch latest metrics
            health = fetch_health_metrics()
            odoo = fetch_odoo_metrics()
            social = fetch_social_metrics()
            tasks = fetch_task_metrics()

            # Generate and update dashboard
            section = generate_metrics_section(health, odoo, social, tasks)
            update_dashboard(section)

            print(f"[{self.name}] Dashboard updated at {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"[{self.name}] Failed to update dashboard: {e}")


def main():
    """Run the dashboard event consumer."""
    consumer = DashboardEventConsumer()
    print("Dashboard Event Consumer started. Listening for events...")
    consumer.run(poll_interval=2.0)  # Check every 2 seconds


if __name__ == "__main__":
    main()
