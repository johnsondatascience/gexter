#!/usr/bin/env python3
"""
Add SPX Price Tracking to GEX Table

This script adds columns to track the SPX spot price at the time
each set of Greeks was calculated.
"""

import sqlite3
import pandas as pd
import shutil
from datetime import datetime
import os

def create_backup(db_path: str) -> str:
    """Create a backup of the database"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"

    print(f"\n1. Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)

    if os.path.exists(backup_path):
        backup_size = os.path.getsize(backup_path) / (1024**3)  # GB
        print(f"   [OK] Backup created successfully ({backup_size:.2f} GB)")
        return backup_path
    else:
        raise Exception("Backup creation failed!")

def add_spx_columns(db_path: str):
    """Add SPX price tracking columns to gex_table"""

    print("\n2. Adding SPX price tracking columns...")

    # Columns to add
    spx_columns = [
        ('spx_price', 'REAL', 'SPX spot price at time of Greek calculation'),
        ('spx_open', 'REAL', 'SPX open price for the day'),
        ('spx_high', 'REAL', 'SPX high price for the day'),
        ('spx_low', 'REAL', 'SPX low price for the day'),
        ('spx_close', 'REAL', 'SPX close price (previous day)'),
        ('spx_bid', 'REAL', 'SPX bid price'),
        ('spx_ask', 'REAL', 'SPX ask price'),
        ('spx_change', 'REAL', 'SPX price change from previous close'),
        ('spx_change_pct', 'REAL', 'SPX price change percentage'),
        ('spx_prevclose', 'REAL', 'SPX previous close price'),
    ]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get existing columns
    cursor.execute("PRAGMA table_info(gex_table)")
    existing_columns = [row[1] for row in cursor.fetchall()]

    columns_added = 0

    for col_name, col_type, description in spx_columns:
        if col_name not in existing_columns:
            try:
                cursor.execute(f'ALTER TABLE gex_table ADD COLUMN "{col_name}" {col_type}')
                print(f"   [OK] Added {col_name}: {description}")
                columns_added += 1
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e):
                    print(f"   [ERROR] Failed to add {col_name}: {e}")
        else:
            print(f"   [SKIP] {col_name} already exists")

    conn.commit()
    conn.close()

    print(f"\n   Total columns added: {columns_added}")
    return columns_added

def verify_columns(db_path: str):
    """Verify that the columns were added successfully"""

    print("\n3. Verifying schema update...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(gex_table)")
    columns = [row[1] for row in cursor.fetchall()]

    spx_columns = [col for col in columns if col.startswith('spx_')]

    print(f"   SPX columns in gex_table: {len(spx_columns)}")
    for col in spx_columns:
        print(f"     - {col}")

    # Get total column count
    print(f"\n   Total columns in gex_table: {len(columns)}")

    conn.close()

    return len(spx_columns) > 0

def main():
    db_path = 'data/gex_data.db'

    print("=" * 80)
    print("ADD SPX PRICE TRACKING TO GEX TABLE")
    print("=" * 80)
    print(f"\nDatabase: {db_path}")

    try:
        # Create backup
        backup_path = create_backup(db_path)

        # Add columns
        columns_added = add_spx_columns(db_path)

        # Verify
        if verify_columns(db_path):
            print("\n" + "=" * 80)
            print("[SUCCESS] SPX PRICE TRACKING COLUMNS ADDED")
            print("=" * 80)
            print(f"\nBackup saved to: {backup_path}")
            print(f"\nColumns added: {columns_added}")
            print("\nNext steps:")
            print("1. Update GEXCollector to populate SPX price columns")
            print("2. Test data collection with new schema")
            return True
        else:
            print("\n[ERROR] Verification failed")
            return False

    except Exception as e:
        print(f"\n[ERROR] {e}")
        return False

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Add SPX price tracking to gex_table')
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Skip confirmation prompt')
    args = parser.parse_args()

    if not args.yes:
        print("\nThis script will modify your database schema.")
        print("A backup will be created automatically.")
        try:
            response = input("\nProceed? (yes/no): ")
        except EOFError:
            print("\nNo input provided. Use --yes flag to run without confirmation.")
            sys.exit(1)

        if response.lower() not in ['yes', 'y']:
            print("Operation cancelled.")
            sys.exit(0)

    success = main()
    sys.exit(0 if success else 1)
