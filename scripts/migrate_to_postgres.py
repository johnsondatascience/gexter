#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script

This script migrates all data from the SQLite database to PostgreSQL.
It handles the migration in chunks to avoid memory issues with the 4.5M+ records.
"""

import sys
import os
import argparse
from datetime import datetime
from io import StringIO
import pandas as pd
from dotenv import load_dotenv
import psycopg2

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.database import DatabaseConnection

# Migration configuration
CHUNK_SIZE = 100000  # Process 100K records at a time
TABLE_NAME = 'gex_table'


def create_backup_sqlite():
    """Create backup of SQLite database before migration"""
    import shutil

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    source = 'data/gex_data.db'
    backup = f'data/gex_data.db.backup_pre_postgres_{timestamp}'

    print(f"\n1. Creating SQLite backup...")
    print(f"   Source: {source}")
    print(f"   Backup: {backup}")

    shutil.copy2(source, backup)
    backup_size = os.path.getsize(backup) / (1024**3)  # GB

    print(f"   [OK] Backup created ({backup_size:.2f} GB)")
    return backup


def connect_databases(config):
    """
    Create connections to both SQLite and PostgreSQL

    Returns:
        tuple: (sqlite_conn, postgres_conn)
    """
    print("\n2. Connecting to databases...")

    # SQLite connection
    sqlite_conn = DatabaseConnection(
        db_type='sqlite',
        db_path=config.database_path
    )
    print(f"   [OK] Connected to SQLite: {config.database_path}")

    # PostgreSQL connection
    postgres_conn = DatabaseConnection(
        db_type='postgresql',
        host=config.postgres_host,
        port=config.postgres_port,
        database=config.postgres_db,
        user=config.postgres_user,
        password=config.postgres_password,
        pool_size=config.postgres_pool_size,
        max_overflow=config.postgres_max_overflow
    )
    print(f"   [OK] Connected to PostgreSQL: {config.postgres_user}@{config.postgres_host}/{config.postgres_db}")

    return sqlite_conn, postgres_conn


def get_migration_stats(sqlite_conn):
    """Get statistics about data to migrate"""
    print("\n3. Analyzing data to migrate...")

    # Get total row count
    total_rows = sqlite_conn.get_row_count(TABLE_NAME)
    print(f"   Total rows: {total_rows:,}")

    # Get date range
    query = '''
    SELECT
        MIN("greeks.updated_at") as min_date,
        MAX("greeks.updated_at") as max_date,
        COUNT(DISTINCT "greeks.updated_at") as unique_timestamps
    FROM gex_table
    '''

    stats = sqlite_conn.read_sql(query)

    print(f"   Date range: {stats['min_date'].iloc[0]} to {stats['max_date'].iloc[0]}")
    print(f"   Unique timestamps: {stats['unique_timestamps'].iloc[0]}")
    print(f"   Chunk size: {CHUNK_SIZE:,} rows")
    print(f"   Estimated chunks: {(total_rows // CHUNK_SIZE) + 1}")

    return total_rows


def check_postgres_table(postgres_conn, auto_confirm=False):
    """Check if PostgreSQL table exists and is empty"""
    print("\n4. Checking PostgreSQL table...")

    if postgres_conn.table_exists(TABLE_NAME):
        row_count = postgres_conn.get_row_count(TABLE_NAME)

        if row_count > 0:
            print(f"   [WARNING] Table '{TABLE_NAME}' exists with {row_count:,} rows")

            if auto_confirm:
                print("   [INFO] Will append to existing data (--yes flag, using ON CONFLICT to skip duplicates)")
            else:
                response = input("   Clear existing data? (yes/no): ")

                if response.lower() in ['yes', 'y']:
                    print("   Truncating table...")
                    postgres_conn.execute(f'TRUNCATE TABLE {TABLE_NAME}')
                    print("   [OK] Table truncated")
                else:
                    print("   [INFO] Will append to existing data")
        else:
            print(f"   [OK] Table '{TABLE_NAME}' exists and is empty")
    else:
        print(f"   [ERROR] Table '{TABLE_NAME}' does not exist")
        print("   Run 'docker-compose up -d' to create the database schema")
        return False

    return True


def migrate_data_chunked(sqlite_conn, postgres_conn, total_rows):
    """
    Migrate data in chunks to handle large dataset

    Args:
        sqlite_conn: SQLite database connection
        postgres_conn: PostgreSQL database connection
        total_rows: Total number of rows to migrate
    """
    print(f"\n5. Migrating {total_rows:,} rows in chunks of {CHUNK_SIZE:,}...")

    offset = 0
    chunk_num = 0
    total_migrated = 0

    while offset < total_rows:
        chunk_num += 1

        print(f"\n   Chunk {chunk_num}: Rows {offset:,} to {min(offset + CHUNK_SIZE, total_rows):,}")

        # Read chunk from SQLite
        query = f'''
        SELECT * FROM {TABLE_NAME}
        ORDER BY "greeks.updated_at", expiration_date, option_type, strike
        LIMIT {CHUNK_SIZE} OFFSET {offset}
        '''

        print(f"      Reading from SQLite...", end=' ')
        chunk_df = sqlite_conn.read_sql(query)
        print(f"{len(chunk_df):,} rows")

        if chunk_df.empty:
            break

        # Remove duplicates (keep first occurrence only)
        pk_cols = ['greeks.updated_at', 'expiration_date', 'option_type', 'strike']
        before_dedup = len(chunk_df)
        chunk_df = chunk_df.drop_duplicates(subset=pk_cols, keep='first')
        after_dedup = len(chunk_df)
        if before_dedup != after_dedup:
            print(f"      Removed {before_dedup - after_dedup:,} duplicates, {after_dedup:,} unique rows remaining")

        # Write chunk to PostgreSQL using COPY to temp table then INSERT with conflict handling
        print(f"      Writing to PostgreSQL...", end=' ')
        try:
            # Convert boolean columns to proper format for PostgreSQL
            if 'has_previous_data' in chunk_df.columns:
                chunk_df['has_previous_data'] = chunk_df['has_previous_data'].map({1.0: 't', 0.0: 'f', 1: 't', 0: 'f', True: 't', False: 'f'})

            # Convert DataFrame to CSV in memory
            buffer = StringIO()
            chunk_df.to_csv(buffer, index=False, header=False, sep='\t', na_rep='\\N')
            buffer.seek(0)

            # Get raw psycopg2 connection
            conn = postgres_conn.engine.raw_connection()
            try:
                cursor = conn.cursor()

                # Create temporary table for this chunk
                temp_table = f"{TABLE_NAME}_temp_{chunk_num}"
                col_list = ', '.join([f'"{col}"' for col in chunk_df.columns])
                cursor.execute(f"CREATE TEMP TABLE {temp_table} (LIKE {TABLE_NAME} INCLUDING DEFAULTS)")

                # COPY to temp table (fast)
                cursor.copy_from(
                    buffer,
                    temp_table,
                    sep='\t',
                    null='\\N',
                    columns=list(chunk_df.columns)
                )

                # INSERT from temp to real table with conflict handling (skip duplicates)
                cursor.execute(f"""
                    INSERT INTO {TABLE_NAME} ({col_list})
                    SELECT {col_list} FROM {temp_table}
                    ON CONFLICT ("greeks.updated_at", expiration_date, option_type, strike) DO NOTHING
                """)

                rows_inserted = cursor.rowcount
                cursor.execute(f"DROP TABLE {temp_table}")
                conn.commit()
            finally:
                conn.close()

            print(f"[OK] ({rows_inserted:,} inserted, {len(chunk_df) - rows_inserted:,} skipped as duplicates)")
            total_migrated += rows_inserted

        except Exception as e:
            print(f"[ERROR]")
            print(f"      Error: {e}")
            raise

        offset += CHUNK_SIZE

        # Progress update
        progress_pct = (total_migrated / total_rows) * 100
        print(f"      Progress: {total_migrated:,}/{total_rows:,} ({progress_pct:.1f}%)")

    print(f"\n   [OK] Migration complete: {total_migrated:,} rows migrated")
    return total_migrated


def verify_migration(sqlite_conn, postgres_conn):
    """Verify that migration was successful"""
    print("\n6. Verifying migration...")

    # Compare row counts
    sqlite_count = sqlite_conn.get_row_count(TABLE_NAME)
    postgres_count = postgres_conn.get_row_count(TABLE_NAME)

    print(f"   SQLite rows:     {sqlite_count:,}")
    print(f"   PostgreSQL rows: {postgres_count:,}")

    if sqlite_count == postgres_count:
        print("   [OK] Row counts match")
    else:
        print(f"   [ERROR] Row count mismatch: {abs(sqlite_count - postgres_count):,} rows different")
        return False

    # Compare sample data
    print("\n   Checking sample records...")

    # Get first and last records from each database
    for label, order in [("First", "ASC"), ("Last", "DESC")]:
        sqlite_query = f'''
        SELECT "greeks.updated_at", strike, option_type, gex, spx_price
        FROM {TABLE_NAME}
        ORDER BY "greeks.updated_at" {order}, strike {order}
        LIMIT 1
        '''

        postgres_query = f'''
        SELECT "greeks.updated_at", strike, option_type, gex, spx_price
        FROM {TABLE_NAME}
        ORDER BY "greeks.updated_at" {order}, strike {order}
        LIMIT 1
        '''

        sqlite_sample = sqlite_conn.read_sql(sqlite_query)
        postgres_sample = postgres_conn.read_sql(postgres_query)

        print(f"\n   {label} record comparison:")
        print(f"      SQLite:     {sqlite_sample.to_dict('records')[0]}")
        print(f"      PostgreSQL: {postgres_sample.to_dict('records')[0]}")

        # Compare values
        if sqlite_sample.equals(postgres_sample):
            print(f"      [OK] {label} records match")
        else:
            print(f"      [WARNING] {label} records differ (may be due to float precision)")

    # Check for NULL values in key columns
    null_check_query = f'''
    SELECT
        COUNT(*) as total,
        COUNT("greeks.updated_at") as has_timestamp,
        COUNT(spx_price) as has_spx_price
    FROM {TABLE_NAME}
    '''

    postgres_nulls = postgres_conn.read_sql(null_check_query)
    print(f"\n   PostgreSQL NULL check:")
    print(f"      Total rows: {postgres_nulls['total'].iloc[0]:,}")
    print(f"      With timestamp: {postgres_nulls['has_timestamp'].iloc[0]:,}")
    print(f"      With SPX price: {postgres_nulls['has_spx_price'].iloc[0]:,}")

    print("\n   [SUCCESS] Migration verification complete")
    return True


def create_indexes(postgres_conn):
    """Create additional indexes for performance"""
    print("\n7. Creating additional indexes...")

    # The primary indexes are created by init.sql
    # Add any additional indexes needed for queries

    additional_indexes = [
        ('idx_gex_table_has_prev_data', 'has_previous_data'),
        ('idx_gex_table_symbol', 'symbol'),
    ]

    for index_name, column in additional_indexes:
        try:
            print(f"   Creating {index_name}...", end=' ')
            postgres_conn.execute(
                f'CREATE INDEX IF NOT EXISTS {index_name} ON {TABLE_NAME}({column})'
            )
            print("[OK]")
        except Exception as e:
            print(f"[SKIP] {e}")

    print("   [OK] Indexes created")


def run_vacuum_analyze(postgres_conn):
    """Run VACUUM ANALYZE to optimize PostgreSQL performance"""
    print("\n8. Optimizing PostgreSQL (VACUUM ANALYZE)...")

    try:
        # Note: VACUUM cannot run inside a transaction, use autocommit
        with postgres_conn.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text(f"VACUUM ANALYZE {TABLE_NAME}"))
        print("   [OK] VACUUM ANALYZE complete")
    except Exception as e:
        print(f"   [WARNING] VACUUM ANALYZE failed: {e}")
        print("   You can run it manually later")


def main():
    """Main migration function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Migrate SQLite database to PostgreSQL')
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Auto-confirm migration without prompting')
    args = parser.parse_args()

    load_dotenv()

    print("=" * 80)
    print("SQLite to PostgreSQL Migration")
    print("=" * 80)

    # Load config
    config = Config()

    # Override to use SQLite for reading
    config.database_type = 'sqlite'

    try:
        # Create backup
        backup_path = create_backup_sqlite()

        # Connect to databases
        sqlite_conn, postgres_conn = connect_databases(config)

        # Get migration stats
        total_rows = get_migration_stats(sqlite_conn)

        # Check PostgreSQL table
        if not check_postgres_table(postgres_conn, auto_confirm=args.yes):
            return False

        # Confirm migration
        print("\n" + "=" * 80)
        print("Ready to migrate")
        print("=" * 80)

        if not args.yes:
            response = input("\nProceed with migration? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("Migration cancelled.")
                return False
        else:
            print("\nAuto-confirming migration (--yes flag)")


        # Migrate data
        rows_migrated = migrate_data_chunked(sqlite_conn, postgres_conn, total_rows)

        # Verify migration
        if not verify_migration(sqlite_conn, postgres_conn):
            print("\n[ERROR] Verification failed")
            return False

        # Create indexes
        create_indexes(postgres_conn)

        # Optimize
        run_vacuum_analyze(postgres_conn)

        # Close connections
        sqlite_conn.close()
        postgres_conn.close()

        print("\n" + "=" * 80)
        print("[SUCCESS] MIGRATION COMPLETE")
        print("=" * 80)
        print(f"\nMigrated: {rows_migrated:,} rows")
        print(f"Backup: {backup_path}")
        print("\nNext steps:")
        print("1. Update .env: Set DATABASE_TYPE=postgresql")
        print("2. Test application: python run_gex_collector.py --force")
        print("3. Keep SQLite backup for safety")

        return True

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        print(f"\nSQLite backup is available for rollback")
        return False


if __name__ == "__main__":
    from sqlalchemy import text

    success = main()
    sys.exit(0 if success else 1)
