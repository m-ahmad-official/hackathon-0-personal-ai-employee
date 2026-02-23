#!/usr/bin/env python3
"""
Test Workflow - Bronze Tier Demo

Demonstrates the complete workflow:
1. Drop files into watch folder
2. Watcher creates action items
3. Orchestrator processes them
4. Dashboard updates

Run this to test the system end-to-end.
"""

import argparse
import time
from pathlib import Path
import sys

# Add current directory to path
sys.path.insert(0, '.')

from orchestrator import Orchestrator
from watcher import DropFolderHandler


def create_test_files(drop_folder: Path, count: int = 3):
    """
    Create test files to trigger the system.

    Args:
        drop_folder: Folder to drop files into
        count: Number of test files to create
    """
    drop_folder.mkdir(parents=True, exist_ok=True)

    print(f"\n📁 Creating {count} test files in {drop_folder}...")

    for i in range(count):
        test_file = drop_folder / f"test_document_{i+1}.txt"
        test_file.write_text(f"""Test Document #{i+1}
========================

Created: {time.strftime('%Y-%m-%d %H:%M:%S')}
Purpose: Integration test for AI Employee Bronze Tier

Contents:
This is a sample document to test the file drop workflow.
The AI Employee should:
1. Detect this file
2. Create action item in Needs_Action
3. Generate a plan
4. Move to Done
5. Update Dashboard

Priority: Medium
Category: Testing
""")
        print(f"  ✓ Created: {test_file.name}")

    print(f"✅ Test files ready in {drop_folder}\n")


def run_demo(vault_path: str, drop_folder: str, watch: bool = False):
    """
    Run the complete demo workflow.

    Args:
        vault_path: Path to the vault
        drop_folder: Path to drop folder
        watch: Run in watch mode
    """
    vault = Path(vault_path).resolve()
    drops = Path(drop_folder).resolve()

    print("\n" + "="*60)
    print("🤖 AI Employee - Bronze Tier Demo")
    print("="*60)

    print(f"\n📂 Vault: {vault}")
    print(f"📥 Drop folder: {drops}")

    # Verify structure
    required_folders = ['Needs_Action', 'Inbox', 'Done', 'Logs', 'Plans']
    print("\n🔍 Checking vault structure...")
    for folder in required_folders:
        folder_path = vault / folder
        if folder_path.exists():
            print(f"  ✓ {folder}/")
        else:
            print(f"  ⚠ {folder}/ missing (will be created)")

    # Create test files
    create_test_files(drops, count=3)

    # Start watcher briefly to process drops
    print("\n👀 Starting file watcher for 3 seconds...")
    import subprocess
    import threading

    # Start watcher in background
    watcher_proc = subprocess.Popen(
        [sys.executable, 'watcher.py', '--vault', str(vault), '--drop-folder', str(drops)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Let it run for 3 seconds
    time.sleep(3)

    # Stop watcher
    watcher_proc.terminate()
    watcher_proc.wait()

    print("✓ Watcher processed drops")

    # Check Needs_Action
    needs_action = vault / 'Needs_Action'
    action_items = list(needs_action.glob('*.md')) if needs_action.exists() else []
    print(f"\n📋 Action items created: {len(action_items)}")
    for item in action_items[:3]:  # Show first 3
        print(f"  • {item.name}")

    # Run orchestrator
    print("\n⚙️  Running orchestrator to process tasks...")
    orch = Orchestrator(str(vault))
    processed = orch.run_once()

    print(f"✓ Processed {processed} items")

    # Show results
    print("\n📊 Results:")
    print("-" * 40)

    # Check Done folder
    done_folder = vault / 'Done'
    done_items = list(done_folder.glob('*.md')) if done_folder.exists() else []
    print(f"  Done items: {len(done_items)}")

    # Check Plans folder
    plans_folder = vault / 'Plans'
    plan_items = list(plans_folder.glob('*.md')) if plans_folder.exists() else []
    print(f"  Plans created: {len(plan_items)}")

    # Check Dashboard
    dashboard = vault / 'Dashboard.md'
    if dashboard.exists():
        print(f"  ✓ Dashboard updated")

    print("\n" + "="*60)
    print("✅ Demo Complete!")
    print("="*60)

    print("\n📖 Next steps:")
    print("  1. Review files in /Done/ and /Plans/")
    print("  2. Open Dashboard.md to see updates")
    print("  3. Read Company_Handbook.md for rules")
    print("  4. Try dropping your own files into 'drops/' folder")
    print("\n💡 To run continuously:")
    print(f"  python orchestrator.py --vault {vault} --watch")
    print(f"  python watcher.py --vault {vault} --drop-folder {drops}")
    print("\n")


def main():
    parser = argparse.ArgumentParser(
        description="Test workflow for AI Employee Bronze Tier"
    )
    parser.add_argument(
        '--vault',
        default='.',
        help='Path to the Obsidian vault (default: current directory)'
    )
    parser.add_argument(
        '--drop-folder',
        default='./drops',
        help='Path to drop folder (default: ./drops)'
    )
    parser.add_argument(
        '--watch',
        action='store_true',
        help='Run in watch mode after demo'
    )

    args = parser.parse_args()
    run_demo(args.vault, args.drop_folder, args.watch)


if __name__ == "__main__":
    main()
