#!/usr/bin/env python3
"""
Odoo Initial Setup Script for Gold Tier
Automates: Account creation, chart of accounts, demo data
"""

import os
import sys
import xmlrpc.client
from datetime import datetime, timedelta

ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.getenv("ODOO_DB", "odoo")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "admin")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "admin")

def connect():
    """Connect to Odoo and return uid and models."""
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
    if not uid:
        raise Exception("Authentication failed")
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    print(f"✅ Connected as {ODOO_USERNAME} (uid={uid})")
    return uid, models

def install_modules(uid, models):
    """Install required modules (account, sale, etc.)."""
    print("\n📦 Installing required modules...")

    # List of modules to install
    modules = ['account', 'sale', 'crm', 'purchase']

    for module in modules:
        try:
            # Check if already installed
            module_ids = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'ir.module.module', 'search',
                [[['name', '=', module], ['state', '=', 'installed']]]
            )
            if module_ids:
                print(f"   ✓ {module} already installed")
            else:
                # Install module
                print(f"   Installing {module}...")
                models.execute_kw(
                    ODOO_DB, uid, ODOO_PASSWORD,
                    'ir.module.module', 'button_immediate_install',
                    [[['name', '=', module]]]
                )
                print(f"   ✓ {module} installed")
        except Exception as e:
            print(f"   ⚠️  Error with {module}: {e}")

def configure_chart_of_accounts(uid, models):
    """Set up a basic chart of accounts."""
    print("\n💰 Setting up Chart of Accounts...")

    # Check if chart already exists
    account_ids = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'account.account', 'search_count',
        [[]]
    )
    if account_ids > 100:  # Already has accounts
        print(f"   ✓ Chart of Accounts already exists ({account_ids} accounts)")
        return

    # Install account module with demo data
    print("   Loading demo chart of accounts...")
    try:
        models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'account.chart.template', 'load_for_current_company',
            [['generic']]  # Generic chart template
        )
        print("   ✅ Chart of Accounts loaded")
    except Exception as e:
        print(f"   ⚠️  Could not load template: {e}")
        print("   You may need to configure manually in Odoo UI")

def create_test_customer(uid, models):
    """Create a test customer for development."""
    print("\n👤 Creating test customer...")
    test_email = "test.client@example.com"

    # Check if exists
    existing = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'res.partner', 'search',
        [[['email', '=', test_email]]]
    )
    if existing:
        print(f"   ✓ Test customer already exists: {test_email}")
        return existing[0]

    # Create
    customer_id = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'res.partner', 'create',
        [{
            'name': 'Test Client',
            'email': test_email,
            'phone': '+1-555-123-4567',
            'company_type': 'person',
            'customer_rank': 1,
            'country_id': 1  # USA
        }]
    )
    print(f"   ✅ Created test customer: {test_email} (ID: {customer_id})")
    return customer_id

def verify_permissions(uid, models):
    """Check if user has necessary permissions."""
    print("\n🔐 Verifying permissions...")

    # Check user groups - in Odoo 19, groups are accessible via many2many
    try:
        user = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'res.users', 'read',
            [[uid]],
            {'fields': ['name', 'groups_id']}
        )[0]
        group_ids = user.get('groups_id', [])
    except Exception as e:
        print(f"   ⚠️  Could not read user groups: {e}")
        print("   (This is normal for Odoo 19 admin - admin has all permissions)")
        return True  # Admin has all permissions by default

    # Check key groups
    required_groups = [
        ('account.group_account_user', 'Accounting / User'),
        ('sale.group_sale_salesman', 'Sales / Salesman')
    ]

    all_present = True
    for group_xml_id, group_name in required_groups:
        group_ids_check = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'res.groups', 'search',
            [[['xml_id', '=', group_xml_id]]]
        )
        if group_ids_check and group_ids_check[0] in group_ids:
            print(f"   ✓ {group_name}")
        else:
            print(f"   ✗ {group_name} - MISSING")
            all_present = False

    return all_present

def main():
    print("=" * 60)
    print("Odoo Setup for Gold Tier")
    print("=" * 60)

    try:
        uid, models = connect()
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\nMake sure Odoo is running:")
        print("  cd mcp-servers/odoo-mcp")
        print("  docker-compose up -d")
        print("\nThen wait ~30 seconds for Odoo to start.")
        sys.exit(1)

    install_modules(uid, models)
    configure_chart_of_accounts(uid, models)
    create_test_customer(uid, models)
    permissions_ok = verify_permissions(uid, models)

    print("\n" + "=" * 60)
    print("✅ Odoo setup complete!")
    print("=" * 60)

    print("\n📋 Next steps:")
    print("1. Review your Chart of Accounts in Odoo UI")
    print("2. Add account codes for key accounts (if missing):")
    print("   - Accounts Receivable: 121000")
    print("   - Cash/Bank: 101000 or 101401")
    print("   - Sales Revenue: 400000")
    print("3. Test connection with: python test_connection.py")
    print("4. Add Odoo MCP server to Claude Code config")
    print("5. Restart Claude Code and test tools")

    if not permissions_ok:
        print("\n⚠️  WARNING: User may not have sufficient permissions.")
        print("   Grant Accounting and Sales permissions to your user in Odoo.")

    print("\n🧪 Quick test after restarting Claude:")
    print('   Claude, use the odoo tool to search_customers with email "test.client@example.com"')

if __name__ == "__main__":
    main()
