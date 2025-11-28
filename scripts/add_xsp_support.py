#!/usr/bin/env python3
"""
Add XSP Support to GEX Collector

This script adds XSP (Micro SPX) tracking alongside SPX.
Both indices will be collected in parallel for comparison.

Changes made:
1. Add 'underlying_symbol' column to gex_table
2. Update gex_collector.py to collect both SPX and XSP
3. Update database schema to support multiple underlyings
"""

import sys
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config

def main():
    load_dotenv()
    config = Config()

    print("=" * 80)
    print("ADD XSP SUPPORT TO GEX COLLECTOR")
    print("=" * 80)
    print()

    if config.database_type != 'postgresql':
        print("ERROR: Only PostgreSQL is supported")
        print("SQLite version would require significant schema changes")
        return False

    # Connect to database
    conn_string = (
        f"postgresql://{config.postgres_user}:{config.postgres_password}@"
        f"{config.postgres_host}:{config.postgres_port}/{config.postgres_db}"
    )
    engine = create_engine(conn_string)

    print("1. Adding 'underlying_symbol' column to gex_table...")

    try:
        with engine.begin() as conn:
            # Check if column exists
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='gex_table' AND column_name='underlying_symbol'
            """))

            if result.fetchone():
                print("   Column 'underlying_symbol' already exists")
            else:
                # Add column with default 'SPX' for existing data
                conn.execute(text("""
                    ALTER TABLE gex_table
                    ADD COLUMN underlying_symbol VARCHAR(10) DEFAULT 'SPX'
                """))
                print("   Column added successfully")

            # Update existing records to explicitly set SPX
            result = conn.execute(text("""
                UPDATE gex_table
                SET underlying_symbol = 'SPX'
                WHERE underlying_symbol IS NULL
            """))

            updated = result.rowcount
            if updated > 0:
                print(f"   Updated {updated:,} existing records to 'SPX'")

    except Exception as e:
        print(f"   ERROR: {e}")
        return False

    print()
    print("2. Creating index on underlying_symbol...")

    try:
        with engine.begin() as conn:
            # Check if index exists
            result = conn.execute(text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename='gex_table' AND indexname='idx_underlying_symbol'
            """))

            if result.fetchone():
                print("   Index already exists")
            else:
                conn.execute(text("""
                    CREATE INDEX idx_underlying_symbol ON gex_table(underlying_symbol)
                """))
                print("   Index created successfully")

    except Exception as e:
        print(f"   ERROR: {e}")
        return False

    print()
    print("3. Verifying database changes...")

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                underlying_symbol,
                COUNT(*) as record_count,
                COUNT(DISTINCT "greeks.updated_at") as timestamp_count
            FROM gex_table
            GROUP BY underlying_symbol
            ORDER BY underlying_symbol
        """))

        print()
        print("   Current data by underlying:")
        for row in result:
            print(f"     {row[0]}: {row[1]:,} records, {row[2]} timestamps")

    print()
    print("=" * 80)
    print("[SUCCESS] DATABASE READY FOR MULTI-UNDERLYING SUPPORT")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Update .env to enable XSP: COLLECT_XSP=true")
    print("  2. Restart collector: docker compose restart scheduler")
    print("  3. Verify collection: Check logs for both SPX and XSP")
    print()
    print("Query examples:")
    print("  -- SPX data only:")
    print("  SELECT * FROM gex_table WHERE underlying_symbol = 'SPX' LIMIT 10;")
    print()
    print("  -- XSP data only:")
    print("  SELECT * FROM gex_table WHERE underlying_symbol = 'XSP' LIMIT 10;")
    print()
    print("  -- Compare GEX totals:")
    print("  SELECT underlying_symbol, SUM(total_gamma_dollars) FROM gex_table")
    print("  GROUP BY underlying_symbol;")
    print()

    return True

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Add XSP support to GEX collector')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation')
    args = parser.parse_args()

    if not args.yes:
        print("This will add XSP (Micro SPX) support to your GEX collector.")
        print("Both SPX and XSP will be collected in parallel.")
        print()
        try:
            response = input("Proceed? (yes/no): ")
        except EOFError:
            print("\nUse --yes flag to run without confirmation.")
            sys.exit(1)

        if response.lower() not in ['yes', 'y']:
            print("Cancelled.")
            sys.exit(0)

    success = main()
    sys.exit(0 if success else 1)
