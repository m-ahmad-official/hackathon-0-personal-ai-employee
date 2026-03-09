#!/usr/bin/env python3
"""
Event Bus Demo - Phase 4
Demonstrates the file-based event system with consumers.
"""

import os
import sys
import time
import json
from pathlib import Path

# Setup paths - we're in utils/event_bus/demo.py
current_file = os.path.abspath(__file__)
event_bus_dir = os.path.dirname(current_file)
sys.path.insert(0, event_bus_dir)  # So we can import 'event' module

import event
EventStore = event.EventStore
EventConsumer = event.EventConsumer
EventTypes = event.EventTypes
emit_event = event.emit_event


def demo_basic_event_emission():
    """Demo: Basic event emission."""
    print("=== Demo 1: Basic Event Emission ===")

    store = EventStore()

    # Emit various events
    events_emitted = []
    for i in range(3):
        e = emit_event(
            event_type=EventTypes.INVOICE_CREATED,
            source="odoo-mcp",
            data={"invoice_id": 100 + i, "amount": 500.00 + (i * 100), "customer": "client@example.com"}
        )
        events_emitted.append(e)

    print(f"Emitted {len(events_emitted)} events")
    print(f"Pending events in queue: {len(store.list_pending())}\n")
    return store


def demo_consumer(store: EventStore):
    """Demo: Consumer that processes events."""
    print("=== Demo 2: Event Consumer ===")

    class PrintConsumer(EventConsumer):
        def __init__(self):
            super().__init__(name="print_consumer", event_store=store)

        def register_handlers(self):
            self.on(EventTypes.INVOICE_CREATED, self.on_invoice)
            self.on(EventTypes.POST_PUBLISHED, self.on_social)
            self.on("*", self.on_any)  # Wildcard for any event

        def on_invoice(self, event):
            print(f"[PrintConsumer] Invoice: ${event.data.get('amount')} for {event.data.get('customer')}")

        def on_social(self, event):
            print(f"[PrintConsumer] Social post on {event.data.get('platform')}")

        def on_any(self, event):
            print(f"[PrintConsumer] Event: {event.type} from {event.source}")

    consumer = PrintConsumer()
    print("Consumer registered. Processing all pending events...\n")

    # Process all pending events
    pending = store.list_pending()
    count = 0
    for event_file in pending:
        success = consumer.process_one(event_file)
        if success:
            count += 1

    print(f"Processed {count} events")
    print(f"Remaining pending: {len(store.list_pending())}")
    print(f"Processed files: {len(store.list_processed())}\n")


def demo_filtered_routing(store: EventStore):
    """Demo: Events with consumed_by routing."""
    print("=== Demo 3: Filtered Delivery ===")

    # Emit event targeted to specific consumers
    event = emit_event(
        event_type=EventTypes.POST_PUBLISHED,
        source="social-mcp",
        data={"platform": "facebook", "post_id": "123_456", "reach": 150},
        consumed_by=["dashboard_updater", "ceo_briefing"]  # Only these consumers will process
    )

    print(f"Event emitted with consumed_by = {event.consumed_by}")
    print("Only consumers named 'dashboard_updater' or 'ceo_briefing' will process this event")
    print(f"Total events now pending: {len(store.list_pending())}\n")


def demo_retention_cleanup(store: EventStore):
    """Demo: Cleanup old processed events."""
    print("=== Demo 4: Retention Cleanup ===")

    # Cleanup events older than 7 days (demo uses 7, real would use 30)
    deleted = store.cleanup_processed(retention_days=7)
    print(f"Cleaned up {deleted} old files from processed/error directories\n")


def demo_custom_consumer_with_error():
    """Demo: Event processing with retry logic."""
    print("=== Demo 5: Error Handling & Retry ===")

    store = EventStore()

    class FailingConsumer(EventConsumer):
        def __init__(self):
            super().__init__(name="failing_consumer", event_store=store)

        def register_handlers(self):
            self.on(EventTypes.INVOICE_CREATED, self.fail_handler)

        def fail_handler(self, event):
            print(f"[FailingConsumer] Processing {event.id}... (will fail)")
            raise ValueError("Simulated processing error!")

    consumer = FailingConsumer()

    # Emit a test event
    event = emit_event(
        event_type=EventTypes.INVOICE_CREATED,
        source="test",
        data={"test": True}
    )

    # Try to process (will fail)
    event_file = store.list_pending()[0]
    print("Attempting to process event (will fail)...")
    success = consumer.process_one(event_file)
    print(f"Success: {success}")

    # Check retry count
    error_files = store.list_errors()
    print(f"Error files created: {len(error_files)}")
    if error_files:
        with open(error_files[0]) as f:
            data = json.load(f)
            print(f"Retry count: {data.get('retry_count', 0)}")
            print(f"Errors recorded: {len(data.get('errors', []))}")
    print()


def main():
    print("Event Bus Demonstration")
    print("=" * 60)
    print()

    # Demo 1: Emission
    store = demo_basic_event_emission()

    # Demo 2: Consumer processing
    demo_consumer(store)

    # Demo 3: Filtered routing
    demo_filtered_routing(store)

    # Demo 4: Error handling
    demo_custom_consumer_with_error()

    # Demo 5: Cleanup
    demo_retention_cleanup(store)

    print("=" * 60)
    print("Demo complete!")
    print()
    print("Files created:")
    print(f" - {store.events_dir} (pending events)")
    print(f" - {store.processed_dir} (archived events)")
    print(f" - {store.error_dir} (failed events)")
    print()
    print("To run consumers in production:")
    print("  python utils/event_bus/consumers/dashboard_consumer.py")
    print("  python utils/event_bus/consumers/email_odoo_consumer.py")
    print()


if __name__ == "__main__":
    main()
