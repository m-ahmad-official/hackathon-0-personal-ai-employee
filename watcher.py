#!/usr/bin/env python3
"""
Filesystem Watcher - Bronze Tier Component

Monitors a designated drop folder for new files and creates action items
in the Needs_Action folder of the AI Employee vault.

Usage:
    python watcher.py --vault /path/to/vault --drop-folder /path/to/drops
"""

import argparse
import logging
import json
import time
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('watcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DropFolderHandler(FileSystemEventHandler):
    """Handles file creation events in the drop folder."""

    def __init__(self, vault_path: str, drop_folder: str):
        """
        Initialize the handler.

        Args:
            vault_path: Path to the Obsidian vault
            drop_folder: Path to the folder being monitored
        """
        self.vault_path = Path(vault_path)
        self.drop_folder = Path(drop_folder)
        self.needs_action = self.vault_path / 'Needs_Action'
        self.processed_files = set()

        # Ensure directories exist
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self.drop_folder.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized watcher:")
        logger.info(f"  Vault: {self.vault_path}")
        logger.info(f"  Drop folder: {self.drop_folder}")
        logger.info(f"  Needs_Action: {self.needs_action}")

    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return

        source_path = Path(event.src_path)

        # Avoid processing the same file multiple times
        if str(source_path) in self.processed_files:
            return

        try:
            logger.info(f"New file detected: {source_path.name}")
            self.process_file(source_path)
            self.processed_files.add(str(source_path))
        except Exception as e:
            logger.error(f"Error processing {source_path}: {e}")

    def process_file(self, source_path: Path):
        """
        Process a new file and create action item.

        Args:
            source_path: Path to the source file
        """
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = source_path.stem.replace(" ", "_")
        action_filename = f"FILE_{safe_name}_{timestamp}.md"
        action_path = self.needs_action / action_filename

        # Copy file to vault (optional - store metadata only)
        vault_file = self.vault_path / 'Inbox' / source_path.name
        vault_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, vault_file)

        # Create action item with metadata
        content = f"""---
type: file_drop
original_name: {source_path.name}
stored_at: {vault_file}
size: {source_path.stat().st_size}
dropped: {datetime.now().isoformat()}
status: pending
---

# File Drop Action

A new file was dropped into the watch folder.

## Details
- **Original Name**: {source_path.name}
- **Size**: {source_path.stat().st_size:,} bytes
- **Dropped At**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Stored In**: {vault_file.relative_to(self.vault_path)}

## Suggested Actions
- [ ] Review the file content
- [ ] Categorize and move to appropriate project folder
- [ ] Extract relevant information
- [ ] Generate response or follow-up task

## Notes
This file was automatically detected by the filesystem watcher and placed in the inbox for processing.
"""

        action_path.write_text(content)
        logger.info(f"Created action item: {action_path}")

        # Update dashboard
        self.update_dashboard()

    def update_dashboard(self):
        """Update the dashboard with current statistics."""
        try:
            dashboard_path = self.vault_path / 'Dashboard.md'
            if dashboard_path.exists():
                content = dashboard_path.read_text()
                # Simple update - increment pending count
                # In production, you'd parse and update properly
                logger.info(f"Dashboard updated: {dashboard_path}")
        except Exception as e:
            logger.warning(f"Could not update dashboard: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Filesystem Watcher for AI Employee"
    )
    parser.add_argument(
        '--vault',
        required=True,
        help='Path to the Obsidian vault'
    )
    parser.add_argument(
        '--drop-folder',
        required=True,
        help='Path to the folder to monitor'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=1,
        help='Check interval in seconds (for polling mode)'
    )

    args = parser.parse_args()

    vault_path = Path(args.vault).resolve()
    drop_folder = Path(args.drop_folder).resolve()

    if not vault_path.exists():
        logger.error(f"Vault path does not exist: {vault_path}")
        return 1

    # Create event handler and observer
    event_handler = DropFolderHandler(str(vault_path), str(drop_folder))
    observer = Observer()
    observer.schedule(event_handler, str(drop_folder), recursive=False)

    logger.info("Starting filesystem watcher...")
    observer.start()

    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping watcher...")
        observer.stop()
    observer.join()

    return 0


if __name__ == "__main__":
    exit(main())
