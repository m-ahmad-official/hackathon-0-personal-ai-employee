#!/usr/bin/env python3
"""
Initialize Odoo database from inside container.
This script creates the Odoo schema in the existing empty database.
"""

import os
import sys
import time
import xmlrpc.client

ODOO_URL = "http://localhost:8069"
ODOO_DB = "odoo"
ODOO_MASTER_PASSWORD = "admin"

def wait_for_odoo(max_attempts=30):
    """Wait for Odoo to be responsive."""
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    for i in range(max_attempts):
        try:
            version = common.version()
            print(f"✅ Odoo is running (version {version['server_version']})")
            return True
        except Exception as e:
            print(f"⏳ Waiting for Odoo... ({i+1}/{max_attempts})")
            time.sleep(2)
    return False

def create_database():
    """Create the Odoo database via XML-RPC."""
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")

    print("📦 Creating Odoo database...")
    try:
        # Create database with demo data
        common.db_create(
            ODOO_MASTER_PASSWORD,
            ODOO_DB,
            True,  # demo data
            'en_US',
            'admin'
        )
        print(f"✅ Database '{ODOO_DB}' created successfully!")
        return True
    except Exception as e:
        print(f"❌ Database creation failed: {e}")
        return False

def main():
    print("=" * 60)
    print("Odoo Database Initialization")
    print("=" * 60)

    if not wait_for_odoo():
        print("❌ Odoo is not responding. Is it running?")
        sys.exit(1)

    if create_database():
        print("\n" + "=" * 60)
        print("✅ Odoo database initialized!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Verify Odoo is accessible at http://localhost:8069")
        print("2. Run: python test_connection.py")
    else:
        print("\n❌ Database creation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
