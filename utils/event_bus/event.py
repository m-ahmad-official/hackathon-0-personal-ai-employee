#!/usr/bin/env python3
"""
Event Bus - Gold Tier Phase 4
File-based event system for decoupled inter-component communication.

Architecture:
- Producers write events to AI_Employee_Vault/Events/ as JSON files
- Consumers watch the Events/ folder and process events
- After successful processing, events moved to Events/processed/
- Supports retry via error folder and event state tracking

Event Types:
- invoice_created, invoice_posted, payment_recorded (from Odoo MCP)
- post_published, engagement_updated (from Social MCP)
- email_received, email_sent (from Email MCP)
- approval_granted, approval_rejected (from Approval Workflow)
- system_alert, health_status (from Health Monitor)
"""

import json
import uuid
import os
import sys
import time
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum

# fcntl is Unix-only; use cross-platform alternative if needed
try:
    import fcntl
    _fcntl_available = True
except ImportError:
    # Windows/WSL - will use simple file locking via rename lock files
    _fcntl_available = False


class EventPriority(Enum):
    """Event priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Event:
    """Event data structure."""
    id: str
    timestamp: str
    type: str
    source: str
    priority: str = EventPriority.NORMAL.value
    data: Dict[str, Any] = None
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None

    # Metadata for routing
    consumed_by: List[str] = None  # List of consumer names that should process

    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.consumed_by is None:
            self.consumed_by = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def create(
        cls,
        event_type: str,
        source: str,
        data: Dict[str, Any],
        priority: str = EventPriority.NORMAL.value,
        consumed_by: List[str] = None,
        **kwargs
    ) -> "Event":
        """Factory method to create a new event."""
        return cls(
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            type=event_type,
            source=source,
            priority=priority,
            data=data,
            consumed_by=consumed_by or [],
            **kwargs
        )


class EventStore:
    """Manages event persistence to the filesystem."""

    def __init__(self, events_dir: str = "AI_Employee_Vault/Events"):
        self.events_dir = Path(events_dir)
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir = self.events_dir / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.error_dir = self.events_dir / "error"
        self.error_dir.mkdir(parents=True, exist_ok=True)

    def emit(self, event: Event) -> str:
        """
        Write event to disk atomically.

        Args:
            event: Event to emit

        Returns:
            Path to the written event file
        """
        # Create filename: {timestamp}_{type}_{id}.json
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_type = event.type.replace("/", "_").replace(":", "_")
        filename = f"{ts}_{safe_type}_{event.id[:8]}.json"
        filepath = self.events_dir / filename

        # Write atomically: write to temp then rename
        temp_path = filepath.with_suffix('.tmp')
        try:
            with open(temp_path, 'w') as f:
                json.dump(event.to_dict(), f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # Atomic rename
            temp_path.rename(filepath)

            return str(filepath)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise

    def list_pending(self) -> List[Path]:
        """List all pending event files (not yet processed)."""
        return sorted(self.events_dir.glob("*.json"))

    def list_processed(self) -> List[Path]:
        """List processed event files."""
        return sorted(self.processed_dir.glob("*.json"))

    def list_errors(self) -> List[Path]:
        """List events that failed processing."""
        return sorted(self.error_dir.glob("*.json"))

    def mark_processed(self, event_file: Path, consumer_name: str):
        """
        Move event to processed/ after successful consumption.

        Args:
            event_file: Path to event file in Events/
            consumer_name: Name of consumer that processed it
        """
        # Read event data first
        try:
            with open(event_file, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading event file: {e}")
            data = {}

        # Update metadata
        if "processed_by" not in data:
            data["processed_by"] = []
        if consumer_name not in data["processed_by"]:
            data["processed_by"].append(consumer_name)
        data["processed_at"] = datetime.now().isoformat()

        # Move to processed dir (with consumer name suffix to avoid collisions)
        dest_name = f"{event_file.stem}_{consumer_name}{event_file.suffix}"
        dest_path = self.processed_dir / dest_name

        # Write updated metadata to destination
        try:
            with open(dest_path, 'w') as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # Remove original
            event_file.unlink(missing_ok=True)
        except Exception as e:
            print(f"Error in mark_processed: {e}")
            # Fallback: just move without metadata update
            try:
                event_file.rename(dest_path)
            except:
                pass

    def mark_error(self, event_file: Path, consumer_name: str, error: str):
        """
        Move event to error/ after failed processing.

        Args:
            event_file: Path to event file
            consumer_name: Consumer that failed
            error: Error message
        """
        # Read event data
        try:
            with open(event_file, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading event file: {e}")
            data = {}

        # Update error info
        if "errors" not in data:
            data["errors"] = []
        data["errors"].append({
            "consumer": consumer_name,
            "timestamp": datetime.now().isoformat(),
            "error": str(error)
        })
        data["retry_count"] = data.get("retry_count", 0) + 1

        # Write to error dir with consumer suffix
        dest_name = f"{event_file.stem}_{consumer_name}_error{event_file.suffix}"
        dest_path = self.error_dir / dest_name

        try:
            with open(dest_path, 'w') as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # Remove original
            event_file.unlink(missing_ok=True)
        except Exception as e:
            print(f"Error in mark_error: {e}")
            # Fallback: just move
            try:
                event_file.rename(dest_path)
            except:
                pass

    def can_retry(self, event_file: Path) -> bool:
        """Check if event can be retried (based on retry_count)."""
        try:
            with open(event_file, 'r') as f:
                data = json.load(f)
                return data.get("retry_count", 0) < data.get("max_retries", 3)
        except:
            return False

    def cleanup_processed(self, retention_days: int = 30):
        """
        Delete processed events older than retention_days.

        Args:
            retention_days: Days to keep processed events
        """
        cutoff = datetime.now().timestamp() - (retention_days * 24 * 3600)
        deleted = 0

        for folder in [self.processed_dir, self.error_dir]:
            for filepath in folder.glob("*.json"):
                if filepath.stat().st_mtime < cutoff:
                    filepath.unlink(missing_ok=True)
                    deleted += 1

        return deleted


class EventConsumer:
    """Base class for event consumers."""

    def __init__(self, name: str, event_store: Optional[EventStore] = None):
        self.name = name
        self.event_store = event_store or EventStore()
        self._handlers: Dict[str, Callable] = {}

    def on(self, event_type: str, handler: Callable):
        """
        Register a handler for an event type.

        Example:
            @consumer.on("invoice_created")
            def handle_invoice_created(event):
                print(f"Invoice {event.data['invoice_id']} created")
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def handle(self, event: Event):
        """
        Dispatch event to registered handlers.

        Args:
            event: Event to handle

        Returns:
            True if handled successfully, False otherwise
        """
        try:
            # Call all handlers for this event type
            handlers = self._handlers.get(event.type, [])
            if not handlers:
                # No specific handler, check for wildcard
                handlers = self._handlers.get("*", [])

            for handler in handlers:
                handler(event)

            return True
        except Exception as e:
            print(f"Error handling event {event.id} ({event.type}) in {self.name}: {e}")
            return False

    def process_one(self, event_file: Path) -> bool:
        """
        Process a single event file.

        Args:
            event_file: Path to event JSON file

        Returns:
            True if successful, False if failed (and should be retried)
        """
        try:
            with open(event_file, 'r') as f:
                data = json.load(f)

            event = Event(**data)

            # Check if this consumer is in the consumed_by list (if specified)
            if event.consumed_by and self.name not in event.consumed_by:
                return True  # Not for us, but treat as success

            # Dispatch
            success = self.handle(event)

            if success:
                self.event_store.mark_processed(event_file, self.name)
            else:
                self.event_store.mark_error(event_file, self.name, "Handler failed")

            return success

        except Exception as e:
            print(f"Failed to process {event_file}: {e}")
            self.event_store.mark_error(event_file, self.name, str(e))
            return False

    def run(self, poll_interval: float = 1.0):
        """
        Continuously poll for new events and process them.

        Args:
            poll_interval: Seconds to wait between polls
        """
        print(f"[{self.name}] Starting event consumer...")
        while True:
            try:
                pending = self.event_store.list_pending()
                for event_file in pending:
                    # Check retry limit
                    if not self.event_store.can_retry(event_file):
                        print(f"[{self.name}] Skipping {event_file.name}: max retries exceeded")
                        # Move to error permanently
                        event_file.rename(self.event_store.error_dir / event_file.name)
                        continue

                    success = self.process_one(event_file)
                    if not success:
                        # Error already marked, but log
                        print(f"[{self.name}] Failed to process {event_file.name}")

                time.sleep(poll_interval)
            except KeyboardInterrupt:
                print(f"\n[{self.name}] Stopping...")
                break
            except Exception as e:
                print(f"[{self.name}] Error in consumer loop: {e}")
                time.sleep(poll_interval)


def emit_event(
    event_type: str,
    source: str,
    data: Dict[str, Any],
    priority: str = EventPriority.NORMAL.value,
    consumed_by: List[str] = None,
    event_store: Optional[EventStore] = None
) -> Event:
    """
    Emit an event to the event bus.

    Args:
        event_type: Type/category of event
        source: Component emitting the event
        data: Event payload
        priority: Event priority (low/normal/high/critical)
        consumed_by: List of consumer names that should process (empty = all)
        event_store: EventStore instance (creates default if None)

    Returns:
        Event object that was emitted
    """
    store = event_store or EventStore()
    event = Event.create(
        event_type=event_type,
        source=source,
        data=data,
        priority=priority,
        consumed_by=consumed_by or []
    )
    path = store.emit(event)
    print(f"[{source}] Emitted event {event.type} ({event.id}) to {path}")
    return event


# Example usage and event type constants
class EventTypes:
    """Standard event type names."""
    # Odoo events
    INVOICE_CREATED = "odoo.invoice.created"
    INVOICE_POSTED = "odoo.invoice.posted"
    PAYMENT_RECORDED = "odoo.payment.recorded"
    CUSTOMER_CREATED = "odoo.customer.created"

    # Social media events
    POST_PUBLISHED = "social.post.published"
    ENGAGEMENT_UPDATED = "social.engagement.updated"
    INSIGHTS_REFRESHED = "social.insights.refreshed"

    # Email events
    EMAIL_RECEIVED = "email.received"
    EMAIL_SENT = "email.sent"

    # Approval events
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_REJECTED = "approval.rejected"

    # System events
    HEALTH_ALERT = "system.health.alert"
    COMPONENT_DEGRADED = "system.component.degraded"
    COMPONENT_RECOVERED = "system.component.recovered"

    # Task events
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"


if __name__ == "__main__":
    # Example: emit test event
    store = EventStore()
    event = emit_event(
        event_type=EventTypes.INVOICE_CREATED,
        source="odoo-mcp",
        data={
            "invoice_id": 123,
            "invoice_number": "INV/2026/001",
            "amount": 500.00,
            "customer": "client@example.com"
        },
        consumed_by=["dashboard_updater", "ceo_briefing"]
    )
    print(f"Emitted: {event.to_dict()}")
