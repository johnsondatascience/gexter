#!/usr/bin/env python3
"""
Database Unification Script

This script unifies all GEX data into a single gex_table by:
1. Creating a backup of the current database
2. Migrating unique records from dgex_table to gex_table
3. Dropping legacy tables (dgex_table, default.gex_table)
4. Vacuuming the database to reclaim space
5. Updating references in code
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

    # Verify backup
    if os.path.exists(backup_path):
        backup_size = os.path.getsize(backup_path) / (1024**3)  # GB
        print(f"   [OK] Backup created successfully ({backup_size:.2f} GB)")
        return backup_path
    else:
        raise Exception("Backup creation failed!")

def analyze_missing_data(conn: sqlite3.Connection):
    """Analyze what data is missing from gex_table"""
    print("\n2. Analyzing data to migrate...")

    query = """
    SELECT COUNT(*) as count
    FROM dgex_table d
    LEFT JOIN gex_table g ON
        d."greeks.updated_at" = g."greeks.updated_at" AND
        d.expiration_date = g.expiration_date AND
        d.option_type = g.option_type AND
        d.strike = g.strike
    WHERE g.strike IS NULL
    """

    result = pd.read_sql(query, conn)
    missing_count = result.iloc[0]['count']

    print(f"   Records to migrate from dgex_table: {missing_count}")
    return missing_count

def migrate_dgex_data(conn: sqlite3.Connection, missing_count: int):
    """Migrate unique records from dgex_table to gex_table"""
    if missing_count == 0:
        print("   [OK] No data to migrate from dgex_table")
        return True

    print(f"\n3. Migrating {missing_count} records from dgex_table to gex_table...")

    # First, get the schema columns for gex_table
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(gex_table)")
    gex_columns = [row[1] for row in cursor.fetchall()]

    # Get columns from dgex_table
    cursor.execute("PRAGMA table_info(dgex_table)")
    dgex_columns = [row[1] for row in cursor.fetchall()]

    # Find common columns
    common_columns = [col for col in dgex_columns if col in gex_columns]

    print(f"   Common columns: {len(common_columns)}/{len(gex_columns)}")

    # Build INSERT query for common columns
    columns_str = ', '.join([f'"{col}"' for col in common_columns])

    insert_query = f"""
    INSERT INTO gex_table ({columns_str})
    SELECT {columns_str}
    FROM dgex_table d
    WHERE NOT EXISTS (
        SELECT 1 FROM gex_table g
        WHERE d."greeks.updated_at" = g."greeks.updated_at"
        AND d.expiration_date = g.expiration_date
        AND d.option_type = g.option_type
        AND d.strike = g.strike
    )
    """

    try:
        cursor.execute(insert_query)
        rows_inserted = cursor.rowcount
        conn.commit()
        print(f"   [OK] Migrated {rows_inserted} records successfully")
        return True
    except Exception as e:
        print(f"   [ERROR] Migration failed: {e}")
        conn.rollback()
        return False

def verify_migration(conn: sqlite3.Connection):
    """Verify that all data has been migrated"""
    print("\n4. Verifying migration...")

    # Check if any records are still missing
    query = """
    SELECT COUNT(*) as count
    FROM dgex_table d
    LEFT JOIN gex_table g ON
        d."greeks.updated_at" = g."greeks.updated_at" AND
        d.expiration_date = g.expiration_date AND
        d.option_type = g.option_type AND
        d.strike = g.strike
    WHERE g.strike IS NULL
    """

    result = pd.read_sql(query, conn)
    still_missing = result.iloc[0]['count']

    if still_missing == 0:
        print("   [OK] All data successfully migrated")
        return True
    else:
        print(f"   [ERROR] Still missing {still_missing} records")
        return False

def drop_legacy_tables(conn: sqlite3.Connection):
    """Drop legacy tables"""
    print("\n5. Dropping legacy tables...")

    cursor = conn.cursor()

    try:
        # Drop dgex_table
        cursor.execute("DROP TABLE IF EXISTS dgex_table")
        print("   [OK] Dropped dgex_table")

        # Drop default.gex_table
        cursor.execute('DROP TABLE IF EXISTS "default.gex_table"')
        print("   [OK] Dropped default.gex_table")

        conn.commit()
        return True
    except Exception as e:
        print(f"   [ERROR] Failed to drop tables: {e}")
        conn.rollback()
        return False

def vacuum_database(conn: sqlite3.Connection):
    """Vacuum the database to reclaim space"""
    print("\n6. Vacuuming database to reclaim space...")

    try:
        cursor = conn.cursor()
        cursor.execute("VACUUM")
        print("   [OK] Database vacuumed successfully")
        return True
    except Exception as e:
        print(f"   [ERROR] Vacuum failed: {e}")
        return False

def get_database_stats(conn: sqlite3.Connection):
    """Get database statistics"""
    cursor = conn.cursor()

    # Get table list
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    print("\n7. Final database statistics:")
    print(f"   Tables: {', '.join(tables)}")

    # Get row count for gex_table
    result = pd.read_sql("SELECT COUNT(*) as count FROM gex_table", conn)
    print(f"   Total records in gex_table: {result.iloc[0]['count']:,}")

    # Get date range
    result = pd.read_sql(
        'SELECT MIN("greeks.updated_at") as min_date, MAX("greeks.updated_at") as max_date FROM gex_table',
        conn
    )
    print(f"   Date range: {result.iloc[0]['min_date']} to {result.iloc[0]['max_date']}")

def main():
    db_path = 'data/gex_data.db'

    print("=" * 80)
    print("GEX DATABASE UNIFICATION")
    print("=" * 80)
    print(f"\nDatabase: {db_path}")

    # Create backup
    try:
        backup_path = create_backup(db_path)
    except Exception as e:
        print(f"ERROR: {e}")
        return False

    # Connect to database
    conn = sqlite3.connect(db_path)

    try:
        # Analyze missing data
        missing_count = analyze_missing_data(conn)

        # Migrate data
        if not migrate_dgex_data(conn, missing_count):
            print("\n[ERROR] Migration failed. Database unchanged.")
            return False

        # Verify migration
        if not verify_migration(conn):
            print("\n[ERROR] Verification failed. Not dropping tables.")
            return False

        # Drop legacy tables
        if not drop_legacy_tables(conn):
            print("\n[ERROR] Failed to drop legacy tables.")
            return False

        # Vacuum database
        vacuum_database(conn)

        # Get final stats
        get_database_stats(conn)

        print("\n" + "=" * 80)
        print("[SUCCESS] DATABASE UNIFICATION COMPLETE")
        print("=" * 80)
        print(f"\nBackup saved to: {backup_path}")
        print("\nNext steps:")
        print("1. Update gex_data.session.sql to reference gex_table")
        print("2. Remove empty gex_data.db file from root directory")
        print("3. Test application to ensure everything works")

        return True

    except Exception as e:
        print(f"\n[ERROR] {e}")
        print(f"Backup is available at: {backup_path}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Unify GEX database tables')
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Skip confirmation prompt')
    args = parser.parse_args()

    # Confirm before proceeding
    if not args.yes:
        print("\nThis script will modify your database.")
        print("A backup will be created automatically.")
        try:
            response = input("\nProceed with unification? (yes/no): ")
        except EOFError:
            print("\nNo input provided. Use --yes flag to run without confirmation.")
            sys.exit(1)

        if response.lower() not in ['yes', 'y']:
            print("Unification cancelled.")
            sys.exit(0)

    success = main()
    sys.exit(0 if success else 1)
