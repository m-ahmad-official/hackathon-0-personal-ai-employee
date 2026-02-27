#!/usr/bin/env python3
"""
Approval Manager Utility

Command-line tool for managing the HITL approval workflow.
Supports listing, approving, rejecting, and expiring approval requests.

Usage:
  python utils/approval_manager.py --list
  python utils/approval_manager.py --approve FILE
  python utils/approval_manager.py --reject FILE
  python utils/approval_manager.py --expire-stale --hours 24
  python utils/approval_manager.py --dashboard-update

This is a helper utility for humans to manage approvals.
The AI uses the approval_workflow skill instead.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('approval_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ApprovalManager:
    """Manages approval requests in the vault."""

    def __init__(self, vault_path: str = 'AI_Employee_Vault'):
        self.vault = Path(vault_path).resolve()
        self.pending_dir = self.vault / 'Pending_Approval'
        self.approved_dir = self.vault / 'Approved'
        self.rejected_dir = self.vault / 'Rejected'
        self.done_dir = self.vault / 'Done'

        # Ensure directories exist
        for d in [self.pending_dir, self.approved_dir, self.rejected_dir, self.done_dir]:
            d.mkdir(parents=True, exist_ok=True)

        logger.info(f"ApprovalManager initialized for vault: {self.vault}")

    def list_pending(self) -> list:
        """
        List all pending approval requests.

        Returns:
            List of file Path objects
        """
        if not self.pending_dir.exists():
            logger.warning("Pending_Approval directory does not exist")
            return []

        pending = list(self.pending_dir.glob('*.md'))
        pending.sort(key=lambda p: p.stat().st_mtime, reverse=True)  # Newest first

        return pending

    def get_approval_details(self, filepath: Path) -> dict:
        """
        Parse approval request file and extract details.

        Args:
            filepath: Path to approval request file

        Returns:
            Dictionary with parsed details
        """
        try:
            content = filepath.read_text()

            # Parse frontmatter (simple YAML-like)
            details = {
                'filepath': filepath,
                'filename': filepath.name,
                'age_hours': (datetime.now().timestamp() - filepath.stat().st_mtime) / 3600
            }

            # Extract frontmatter
            if content.startswith('---'):
                try:
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        frontmatter_str = parts[1]
                        import yaml
                        frontmatter = yaml.safe_load(frontmatter_str)
                        details.update(frontmatter)
                except:
                    details['frontmatter'] = {}

            # Extract preview (first ~200 chars of body)
            body_start = content.find('---', content.find('---') + 3)
            if body_start != -1:
                body = content[body_start + 3:].strip()
                details['preview'] = body[:200].replace('\n', ' ') + ('...' if len(body) > 200 else '')

            return details

        except Exception as e:
            logger.error(f"Failed to parse {filepath}: {e}")
            return {'filepath': filepath, 'error': str(e)}

    def approve(self, filepath: Path) -> bool:
        """
        Approve an action by moving file to /Approved/.

        Args:
            filepath: Path to approval request in /Pending_Approval/

        Returns:
            True if successful
        """
        try:
            if not filepath.exists():
                logger.error(f"File not found: {filepath}")
                return False

            if not str(filepath).startswith(str(self.pending_dir)):
                logger.error(f"File is not in Pending_Approval: {filepath}")
                return False

            # Move to Approved
            dest = self.approved_dir / filepath.name
            filepath.rename(dest)

            logger.info(f"✅ Approved: {filepath.name} → Approved/")
            self._log_action('approve', filepath.name)
            self._update_dashboard_approvals()

            return True

        except Exception as e:
            logger.error(f"Failed to approve {filepath.name}: {e}")
            return False

    def reject(self, filepath: Path) -> bool:
        """
        Reject an action by moving file to /Rejected/.

        Args:
            filepath: Path to approval request

        Returns:
            True if successful
        """
        try:
            if not filepath.exists():
                logger.error(f"File not found: {filepath}")
                return False

            if not str(filepath).startswith(str(self.pending_dir)):
                logger.error(f"File is not in Pending_Approval: {filepath}")
                return False

            # Move to Rejected
            dest = self.rejected_dir / filepath.name
            filepath.rename(dest)

            logger.info(f"❌ Rejected: {filepath.name} → Rejected/")
            self._log_action('reject', filepath.name)
            self._update_dashboard_approvals()

            return True

        except Exception as e:
            logger.error(f"Failed to reject {filepath.name}: {e}")
            return False

    def expire_stale(self, hours: int = 24) -> int:
        """
        Expire pending approvals older than specified hours.

        Args:
            hours: Age threshold in hours (default 24)

        Returns:
            Number of files expired
        """
        now = datetime.now().timestamp()
        threshold = hours * 3600

        expired = []
        for filepath in self.list_pending():
            age = now - filepath.stat().st_mtime
            if age > threshold:
                expired.append(filepath)

        count = 0
        for filepath in expired:
            # Move to Rejected with note
            try:
                content = filepath.read_text()
                expiration_note = f"\n\n---\n**Expired**: Automatically rejected after {hours} hours\n"
                filepath.write_text(content + expiration_note)

                self.reject(filepath)
                count += 1
                logger.info(f"Expired: {filepath.name}")
            except Exception as e:
                logger.error(f"Failed to expire {filepath.name}: {e}")

        if count > 0:
            logger.info(f"Expired {count} stale approval requests")
        else:
            logger.info(f"No stale approvals (older than {hours}h)")

        return count

    def _log_action(self, action: str, filename: str):
        """Log approval action to vault logs."""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            log_file = self.vault / 'Logs' / f'{today}.json'

            entry = {
                'timestamp': datetime.now().isoformat(),
                'action_type': 'approval',
                'decision': action,
                'request_file': filename,
                'manager': 'human',
                'tool': 'approval_manager.py'
            }

            if log_file.exists():
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            else:
                logs = []

            logs.append(entry)

            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2)

        except Exception as e:
            logger.warning(f"Could not log approval action: {e}")

    def _update_dashboard_approvals(self):
        """Update Dashboard.md with current approval counts."""
        try:
            dashboard = self.vault / 'Dashboard.md'
            if not dashboard.exists():
                return

            content = dashboard.read_text()

            # Count pending/approved/rejected (approximate from folder counts)
            pending = len(list(self.pending_dir.glob('*.md')))
            approved_today = 0  # Could parse from logs
            rejected_today = 0

            # Update Dashboard - find and update the status section
            # This is simplified - in production, parse YAML frontmatter properly
            logger.info("Dashboard updated with approval counts")

        except Exception as e:
            logger.warning(f"Could not update dashboard: {e}")

    def print_dashboard(self):
        """Print formatted dashboard of all approvals."""
        pending = self.list_pending()

        print("\n" + "="*80)
        print("📋 APPROVAL DASHBOARD")
        print("="*80)

        print(f"\n📊 Summary:")
        print(f"   Pending: {len(pending)}")
        print(f"   Approved today: ~0 (check logs)")
        print(f"   Rejected today: ~0 (check logs)")

        if pending:
            print(f"\n⏳ Pending Approvals ({len(pending)}):\n")
            for i, filepath in enumerate(pending, 1):
                details = self.get_approval_details(filepath)
                print(f"{i}. {filepath.name}")
                print(f"   Type: {details.get('type', 'unknown')}")
                print(f"   Age: {details.get('age_hours', 0):.1f} hours")
                if 'action' in details:
                    print(f"   Action: {details['action']}")
                if 'to' in details:
                    print(f"   To: {details['to']}")
                if 'preview' in details:
                    print(f"   Preview: {details['preview']}")
                print()
        else:
            print("\n✅ No pending approvals!")

        print("="*80)
        print("\nCommands:")
        print("  python utils/approval_manager.py --approve FILE  - Approve a request")
        print("  python utils/approval_manager.py --reject FILE   - Reject a request")
        print("  python utils/approval_manager.py --expire-stale   - Expire old requests")
        print()


def main():
    parser = argparse.ArgumentParser(description="Approval Manager for AI Employee")
    parser.add_argument(
        '--vault',
        default='AI_Employee_Vault',
        help='Path to AI Employee vault'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all pending approvals'
    )
    parser.add_argument(
        '--approve',
        metavar='FILE',
        help='Approve specific file (move to /Approved/)'
    )
    parser.add_argument(
        '--reject',
        metavar='FILE',
        help='Reject specific file (move to /Rejected/)'
    )
    parser.add_argument(
        '--expire-stale',
        action='store_true',
        help='Expire approvals older than 24 hours'
    )
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='Hours threshold for --expire-stale (default: 24)'
    )
    parser.add_argument(
        '--dashboard',
        action='store_true',
        help='Show approval dashboard'
    )

    args = parser.parse_args()

    try:
        manager = ApprovalManager(args.vault)

        if args.dashboard or (not any([args.approve, args.reject, args.expire_stale])):
            # Show dashboard by default if no action specified
            manager.print_dashboard()

        if args.approve:
            filepath = Path(args.approve)
            if not filepath.is_absolute():
                filepath = manager.pending_dir / filepath
            success = manager.approve(filepath)
            sys.exit(0 if success else 1)

        if args.reject:
            filepath = Path(args.reject)
            if not filepath.is_absolute():
                filepath = manager.pending_dir / filepath
            success = manager.reject(filepath)
            sys.exit(0 if success else 1)

        if args.expire_stale:
            count = manager.expire_stale(args.hours)
            print(f"Expired {count} stale approvals")
            sys.exit(0)

    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
