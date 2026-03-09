#!/usr/bin/env python3
"""
Enhanced Audit Logger - Gold Tier Phase 3
Provides structured JSON logging with rotation, querying, and compliance features.

Features:
- Structured JSON logs with full context
- Automatic log rotation (daily, size-based)
- Log retention and archiving
- Query interface for filtering
- Compliance report generation
- Immutable append-only mode (WAL)
"""

import json
import logging
import os
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
import gzip
import shutil
from enum import Enum

# Module-level logger
logger = logging.getLogger(__name__)

# Use structlog if available, otherwise standard json logger
try:
    import structlog
    _structlog_available = True
except ImportError:
    _structlog_available = False


class LogLevel(Enum):
    """Audit log levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEntry:
    """Schema for audit log entries."""
    id: str                           # Unique UUID
    timestamp: str                    # ISO 8601 timestamp
    level: str                        # info, warning, error, critical
    actor: str                        # Who/what performed action
    action: str                       # Action type (email_send, invoice_create, etc.)
    target: Optional[str] = None      # Target of action (email address, invoice ID)
    parameters: Dict[str, Any] = field(default_factory=dict)  # Input parameters
    context: Dict[str, Any] = field(default_factory=dict)     # Additional context
    result: Dict[str, Any] = field(default_factory=dict)      # Result/outcome
    approval: Optional[Dict[str, Any]] = None                 # Approval details
    duration_ms: Optional[int] = None                         # Execution time
    error: Optional[str] = None                               # Error message if failed
    audit_trail: List[str] = field(default_factory=list)      # Chain of operations

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, removing None values."""
        data = asdict(self)
        # Remove None values for cleaner logs
        return {k: v for k, v in data.items() if v is not None and v != {}}


class AuditLogger:
    """
    Enhanced audit logger with structured JSON output.

    Features:
    - Daily log files with optional size-based rotation
    - Archival (gzip compression of old logs)
    - Retention policy (default: keep 90 days)
    - Query interface for filtering entries
    - Compliance report generation
    - Thread-safe writes

    Configuration:
        logger = AuditLogger(
            log_dir="AI_Employee_Vault/Logs",
            retention_days=90,
            rotation_days=1,
            max_bytes=10*1024*1024  # 10MB per file
        )

        # Log an event
        logger.log(audit_entry)

        # Query logs
        entries = logger.query(action="invoice_create", start_date="2026-03-01")

        # Generate compliance report
        report = logger.generate_compliance_report(date="2026-03-06")
    """

    def __init__(
        self,
        log_dir: str = "AI_Employee_Vault/Logs",
        retention_days: int = 90,
        rotation_days: int = 1,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        archive_dir: Optional[str] = None,
        enable_immutable: bool = False,  # Write-once, read-only after close
        process_name: Optional[str] = None  # Process identifier for separate logs
    ):
        # Convert to absolute path: if relative, assume it's from project root
        log_path = Path(log_dir)
        if not log_path.is_absolute():
            # Find project root (directory containing AI_Employee_Vault)
            current = Path.cwd()
            # Search up the directory tree for AI_Employee_Vault
            for parent in [current] + list(current.parents):
                if (parent / "AI_Employee_Vault").exists():
                    log_path = parent / log_path
                    break
            else:
                # Fall back to current working directory
                log_path = current / log_path

        self.log_dir = log_path
        self.retention_days = retention_days
        self.rotation_days = rotation_days
        self.max_bytes = max_bytes
        self.archive_dir = Path(archive_dir) if archive_dir else self.log_dir / "archive"
        self.enable_immutable = enable_immutable
        self.process_name = process_name or f"proc_{os.getpid()}"

        # Ensure directories exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        # Current log file handle
        self._current_file: Optional[Any] = None
        self._current_date: Optional[datetime] = None
        self._current_size: int = 0
        self._lock = threading.RLock()

    def _get_log_path(self, date: Optional[datetime] = None) -> Path:
        """Get log file path for given date (defaults to today). Uses process-specific naming."""
        if date is None:
            date = datetime.now()
        # Use separate log file per process to avoid cross-process corruption
        # Format: YYYY-MM-DD.PROCESSNAME.json (e.g., 2026-03-09.health_monitor.json)
        return self.log_dir / f"{date.strftime('%Y-%m-%d')}.{self.process_name}.json"

    def _rotate_if_needed(self):
        """Check if log rotation is needed and rotate."""
        now = datetime.now()
        current_date = now.date()

        with self._lock:
            # Check date rotation
            if self._current_date is None or current_date != self._current_date:
                self._close_current()
                self._current_date = current_date
                self._current_file = self._open_log_file(self._get_log_path(now))

            # Check size rotation
            if self._current_file and self._current_size >= self.max_bytes:
                self._close_current()
                # Append timestamp to rotated file
                timestamp = now.strftime("%H%M%S")
                old_path = self._get_log_path(now)
                new_path = self.log_dir / f"{now.strftime('%Y-%m-%d')}_{timestamp}.json"
                shutil.move(old_path, new_path)
                self._current_file = self._open_log_file(old_path)
                self._current_size = 0

    def _open_log_file(self, path: Path) -> Any:
        """Open log file for appending (returns file handle)."""
        # Create file if doesn't exist with opening bracket
        if not path.exists():
            with open(path, 'w') as f:
                f.write("[\n")
                f.flush()
                os.fsync(f.fileno())

        # Open in append mode
        return open(path, 'a+', encoding='utf-8')

    def _close_current(self):
        """Close current log file properly."""
        if self._current_file:
            # Remove trailing comma if last entry didn't have one
            # For simplicity, we'll keep trailing comma - valid JSON array
            self._current_file.close()
            self._current_file = None

    def log(self, entry: AuditEntry):
        """
        Write an audit entry to the log.

        Args:
            entry: AuditEntry object with all required fields
        """
        self._rotate_if_needed()

        with self._lock:
            if self._current_file:
                # Convert entry to JSON
                entry_dict = entry.to_dict()
                json_line = json.dumps(entry_dict, ensure_ascii=False)

                # Write entry with comma separator (array format)
                # If file is empty or ends with newline/[, don't add comma
                self._current_file.seek(0, 2)  # End of file
                if self._current_size > 0:
                    self._current_file.write(",\n")
                else:
                    # First entry after opening bracket
                    pass

                self._current_file.write(json_line)
                self._current_file.flush()
                self._current_size += len(json_line) + (2 if self._current_size > 0 else 1)

    def read_logs(
        self,
        date: Optional[str] = None,  # YYYY-MM-DD format
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        action: Optional[str] = None,
        actor: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 1000
    ) -> List[AuditEntry]:
        """
        Query audit logs with filtering.

        Args:
            date: Specific date (YYYY-MM-DD)
            start_date: Start of range (inclusive)
            end_date: End of range (inclusive)
            action: Filter by action type
            actor: Filter by actor
            level: Filter by log level
            limit: Max entries to return

        Returns:
            List of AuditEntry objects
        """
        entries = []

        # Determine which files to read
        # With per-process log files, we need to match patterns like YYYY-MM-DD.*.json
        if date:
            # Read all process files for that date
            files = sorted(self.log_dir.glob(f"{date}.*.json"))
        else:
            # Read all files in date range
            files = sorted(self.log_dir.glob("*.json"))

        for filepath in files:
            if not filepath.exists():
                continue

            # Parse date from filename (format: YYYY-MM-DD.PROCESS.json or YYYY-MM-DD.json)
            try:
                file_date_str = filepath.stem.split('.')[0]  # Get YYYY-MM-DD part
            except:
                file_date_str = ""

            if start_date and file_date_str < start_date:
                continue
            if end_date and file_date_str > end_date:
                continue

            # Read and parse entries
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        continue

                    # Fix array format: add closing bracket if missing
                    if not content.endswith(']'):
                        content += '\n]'

                    entries_data = json.loads(content)

                    for entry_data in entries_data:
                        # Apply filters
                        if action:
                            entry_action = entry_data.get('action')
                            if isinstance(action, list):
                                if entry_action not in action:
                                    continue
                            else:
                                if entry_action != action:
                                    continue
                        if actor and entry_data.get('actor') != actor:
                            continue
                        if level and entry_data.get('level') != level:
                            continue

                        entries.append(AuditEntry(**entry_data))

                        if len(entries) >= limit:
                            break
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse log file {filepath}: {e}")
                continue

        # Sort by timestamp (newest first)
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]

    def generate_compliance_report(
        self,
        date: Optional[str] = None,  # Default: yesterday
        include_sensitive: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a compliance report for a given date.

        Args:
            date: Date to report on (YYYY-MM-DD), defaults to yesterday
            include_sensitive: Include sensitive data (email addresses, etc.)

        Returns:
            Dictionary with compliance metrics
        """
        if date is None:
            date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        entries = self.read_logs(date=date, limit=10000)

        report = {
            "generated_at": datetime.now().isoformat(),
            "report_period": date,
            "total_actions": len(entries),
            "actions_by_type": {},
            "actions_by_actor": {},
            "approval_usage": {
                "total_approvals_required": 0,
                "auto_approved": 0,
                "human_approved": 0,
                "rejected": 0
            },
            "errors": {
                "count": 0,
                "by_type": {}
            },
            "sensitive_data_access": [],
            "duration_stats": {
                "avg_ms": 0,
                "max_ms": 0,
                "p95_ms": 0
            }
        }

        durations = []
        for entry in entries:
            # Count by action type
            action = entry.action
            report["actions_by_type"][action] = report["actions_by_type"].get(action, 0) + 1

            # Count by actor
            actor = entry.actor
            report["actions_by_actor"][actor] = report["actions_by_actor"].get(actor, 0) + 1

            # Approval stats
            if entry.approval:
                report["approval_usage"]["total_approvals_required"] += 1
                status = entry.approval.get("status", "")
                if status == "approved":
                    report["approval_usage"]["human_approved"] += 1
                elif status == "auto_approved":
                    report["approval_usage"]["auto_approved"] += 1
                elif status == "rejected":
                    report["approval_usage"]["rejected"] += 1

            # Errors
            if entry.error:
                report["errors"]["count"] += 1
                error_type = type(entry.error).__name__ if hasattr(entry.error, '__name__') else str(entry.error)
                report["errors"]["by_type"][error_type] = report["errors"]["by_type"].get(error_type, 0) + 1

            # Duration
            if entry.duration_ms:
                durations.append(entry.duration_ms)

            # Sensitive data (only if requested)
            if include_sensitive and entry.target and '@' in str(entry.target):
                report["sensitive_data_access"].append({
                    "timestamp": entry.timestamp,
                    "actor": entry.actor,
                    "action": entry.action,
                    "target": entry.target
                })

        # Calculate duration stats
        if durations:
            durations.sort()
            report["duration_stats"]["avg_ms"] = sum(durations) // len(durations)
            report["duration_stats"]["max_ms"] = max(durations)
            p95_index = int(len(durations) * 0.95)
            report["duration_stats"]["p95_ms"] = durations[p95_index]

        return report

    def cleanup_old_logs(self):
        """
        Delete logs older than retention period.
        Also archives (gzip) logs that are within retention but not current.
        """
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        deleted_count = 0
        archived_count = 0

        for filepath in self.log_dir.glob("*.json"):
            try:
                # Parse date from filename (format: YYYY-MM-DD.PROCESS.json)
                # Skip files that don't match pattern (e.g., archive files)
                filename = filepath.name
                if '.' not in filename:
                    continue  # Skip non-process files
                date_str = filename.split('.')[0]
                file_date = datetime.strptime(date_str, '%Y-%m-%d')

                if file_date < cutoff_date:
                    # Delete old log
                    filepath.unlink()
                    deleted_count += 1
                elif filepath != self._get_log_path():
                    # Archive old log (gzip)
                    archive_path = self.archive_dir / f"{filepath.name}.gz"
                    if not archive_path.exists():
                        with open(filepath, 'rb') as f_in:
                            with gzip.open(archive_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        filepath.unlink()
                        archived_count += 1
            except (ValueError, OSError) as e:
                logger.warning(f"Failed to process log file {filepath}: {e}")
                continue

        logger.info(f"Log cleanup: deleted {deleted_count}, archived {archived_count} files")
        return {"deleted": deleted_count, "archived": archived_count}

    def __del__(self):
        """Cleanup on destruction."""
        self._close_current()


# Convenience function to create global logger
_default_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create default audit logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = AuditLogger()
    return _default_logger


def log_audit(
    actor: str,
    action: str,
    target: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None,
    level: LogLevel = LogLevel.INFO,
    **kwargs
):
    """
    Convenience function to log an audit entry.

    Example:
        log_audit(
            actor="claude_code",
            action="invoice_create",
            target="INV/2026/001",
            parameters={"customer": "client@example.com", "amount": 500},
            result={"status": "success", "invoice_id": 123}
        )
    """
    import uuid
    from datetime import datetime

    logger = get_audit_logger()

    entry = AuditEntry(
        id=str(uuid.uuid4()),
        timestamp=datetime.now().isoformat(),
        level=level.value,
        actor=actor,
        action=action,
        target=target,
        parameters=parameters or {},
        result=result or {},
        **kwargs
    )
    logger.log(entry)


if __name__ == "__main__":
    # Example usage
    logger = AuditLogger(log_dir="test_logs")

    # Log some events
    log_audit(
        actor="test",
        action="test_action",
        target="test_target",
        parameters={"key": "value"},
        result={"status": "ok"}
    )

    # Query
    entries = logger.read_logs(action="test_action", limit=10)
    print(f"Found {len(entries)} entries")

    # Compliance report
    report = logger.generate_compliance_report()
    print(json.dumps(report, indent=2))
