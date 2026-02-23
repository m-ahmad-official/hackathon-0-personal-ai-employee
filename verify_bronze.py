#!/usr/bin/env python3
"""
Bronze Tier Verification Script

Checks that all required components are in place.
Run this to verify your Bronze Tier completion.
"""

import sys
from pathlib import Path


def check_file(path: Path, description: str) -> bool:
    """Check if a file exists and report."""
    exists = path.exists()
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {path}")
    return exists


def check_folder(path: Path, description: str) -> bool:
    """Check if a folder exists and report."""
    exists = path.is_dir()
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {path}/")
    return exists


def main():
    print("\n" + "="*60)
    print("🔍 Bronze Tier Verification")
    print("="*60 + "\n")

    # Check for vault folder
    vault = Path('AI_Employee_Vault')
    if not vault.exists():
        print("❌ AI_Employee_Vault folder not found!")
        print("   Expected vault at: ./AI_Employee_Vault/")
        return 1

    all_good = True

    print("📁 Required Folders:")
    folders = [
        ('Inbox', 'Inbox folder'),
        ('Needs_Action', 'Needs_Action folder'),
        ('Done', 'Done folder'),
        ('Plans', 'Plans folder'),
        ('Logs', 'Logs folder'),
        ('Pending_Approval', 'Pending_Approval folder'),
        ('Approved', 'Approved folder'),
        ('Rejected', 'Rejected folder'),
    ]
    for folder, desc in folders:
        all_good &= check_folder(vault / folder, desc)

    print("\n📄 Required Files:")
    files = [
        ('Dashboard.md', 'Dashboard'),
        ('Company_Handbook.md', 'Company Handbook'),
        ('Business_Goals.md', 'Business Goals'),
    ]
    for file, desc in files:
        all_good &= check_file(vault / file, desc)

    print("\n🔧 Components (in project root):")
    components = [
        ('orchestrator.py', 'Orchestrator script'),
        ('watcher.py', 'Filesystem watcher'),
        ('requirements.txt', 'Python dependencies'),
        ('README.md', 'Documentation'),
        ('CLAUDE.md', 'Claude integration guide'),
        ('SECURITY.md', 'Security guidelines'),
        ('.gitignore', 'Git ignore file'),
    ]
    root = Path('.')
    for file, desc in components:
        all_good &= check_file(root / file, desc)

    print("\n🎯 Agent Skills (in vault):")
    skills = [
        ('process_needs_action', 'Process Needs Action skill'),
        ('update_dashboard', 'Update Dashboard skill'),
    ]
    for skill, desc in skills:
        skill_path = vault / '.claude' / 'skills' / skill / 'skill.md'
        all_good &= check_file(skill_path, desc)

    print("\n📦 Dependencies:")
    # Check if watchdog is installed
    try:
        import watchdog
        print("✅ Python dependencies installed (watchdog)")
    except ImportError:
        print("❌ Python dependencies NOT installed")
        print("   Run: pip install -r requirements.txt")
        all_good = False

    print("\n" + "="*60)
    if all_good:
        print("✅ ALL CHECKS PASSED - Bronze Tier Complete!")
    else:
        print("⚠️  Some checks failed. Review above.")
    print("="*60 + "\n")

    # Show next steps
    print("📋 Next Steps:\n")
    print("1. Install dependencies (if not done):")
    print("   pip install -r requirements.txt\n")
    print("2. Test the workflow:")
    print("   mkdir -p drops")
    print("   python watcher.py --vault AI_Employee_Vault --drop-folder ./drops &")
    print("   echo 'test' > drops/test.txt")
    print("   # Check AI_Employee_Vault/Needs_Action/ for action item\n")
    print("3. Run orchestrator:")
    print("   python orchestrator.py --vault AI_Employee_Vault --process-now\n")
    print("4. Use Claude Code:")
    print("   cd AI_Employee_Vault")
    print("   claude .")
    print("   Then ask: 'What's in Needs_Action?'\n")
    print("5. Review documentation:")
    print("   - README.md (usage guide)")
    print("   - Company_Handbook.md (rules)")
    print("   - CLAUDE.md (integration)")
    print("   - SECURITY.md (security)\n")

    return 0 if all_good else 1


if __name__ == "__main__":
    sys.exit(main())
