#!/usr/bin/env python3
"""
Add Intraday and Daily OHLC Columns

This script adds separate columns for intraday (15-min bar) and daily OHLC data.

Current columns:
- spx_open, spx_high, spx_low, spx_close (currently daily data)

New structure:
- spx_daily_open, spx_daily_high, spx_daily_low, spx_daily_close (daily session OHLC)
- spx_intraday_open, spx_intraday_high, spx_intraday_low, spx_intraday_close (15-min bar OHLC)
"""

import sys
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config


def main():
    load_dotenv()
    config = Config()

    print("=" * 80)
    print("ADD INTRADAY AND DAILY OHLC COLUMNS")
    print("=" * 80)
    print(f"\nDatabase Type: {config.database_type}\n")

    if config.database_type != 'postgresql':
        print("ERROR: Only PostgreSQL is supported")
        return False

    # Connect to database
    conn_string = (
        f"postgresql://{config.postgres_user}:{config.postgres_password}@"
        f"{config.postgres_host}:{config.postgres_port}/{config.postgres_db}"
    )
    engine = create_engine(conn_string)

    print("1. Creating new columns...")

    with engine.begin() as conn:
        # Add new daily OHLC columns
        print("   Adding spx_daily_* columns...")
        conn.execute(text("ALTER TABLE gex_table ADD COLUMN IF NOT EXISTS spx_daily_open REAL"))
        conn.execute(text("ALTER TABLE gex_table ADD COLUMN IF NOT EXISTS spx_daily_high REAL"))
        conn.execute(text("ALTER TABLE gex_table ADD COLUMN IF NOT EXISTS spx_daily_low REAL"))
        conn.execute(text("ALTER TABLE gex_table ADD COLUMN IF NOT EXISTS spx_daily_close REAL"))

        # Add new intraday OHLC columns
        print("   Adding spx_intraday_* columns...")
        conn.execute(text("ALTER TABLE gex_table ADD COLUMN IF NOT EXISTS spx_intraday_open REAL"))
        conn.execute(text("ALTER TABLE gex_table ADD COLUMN IF NOT EXISTS spx_intraday_high REAL"))
        conn.execute(text("ALTER TABLE gex_table ADD COLUMN IF NOT EXISTS spx_intraday_low REAL"))
        conn.execute(text("ALTER TABLE gex_table ADD COLUMN IF NOT EXISTS spx_intraday_close REAL"))

        print("   [OK] Columns added")

    print("\n2. Migrating existing data...")
    print("   Copying current spx_open/high/low/close to spx_daily_* columns...")

    with engine.begin() as conn:
        # Copy existing OHLC data to daily columns (they were daily data)
        conn.execute(text("""
            UPDATE gex_table
            SET
                spx_daily_open = spx_open,
                spx_daily_high = spx_high,
                spx_daily_low = spx_low,
                spx_daily_close = spx_close
            WHERE spx_open IS NOT NULL
        """))

        result = conn.execute(text("SELECT COUNT(*) FROM gex_table WHERE spx_daily_open IS NOT NULL"))
        count = result.scalar()
        print(f"   [OK] Migrated {count:,} records")

    print("\n3. Verifying migration...")

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total_records,
                COUNT(spx_price) as with_spx_price,
                COUNT(spx_daily_open) as with_daily_ohlc,
                COUNT(spx_intraday_open) as with_intraday_ohlc
            FROM gex_table
        """))

        row = result.fetchone()
        print(f"   Total records: {row[0]:,}")
        print(f"   With SPX price: {row[1]:,}")
        print(f"   With daily OHLC: {row[2]:,}")
        print(f"   With intraday OHLC: {row[3]:,}")

    print("\n" + "=" * 80)
    print("[SUCCESS] OHLC COLUMNS MIGRATION COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Old columns (spx_open/high/low/close) preserved for compatibility")
    print("2. New spx_daily_* columns populated with existing data")
    print("3. New spx_intraday_* columns ready for backfill")
    print("4. Run backfill scripts to populate intraday OHLC data")

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Add intraday and daily OHLC columns')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation')
    args = parser.parse_args()

    if not args.yes:
        print("\nThis will add new columns for intraday and daily OHLC separation.")
        print("Existing spx_open/high/low/close data will be copied to spx_daily_* columns.")
        try:
            response = input("\nProceed? (yes/no): ")
        except EOFError:
            print("\nUse --yes flag to run without confirmation.")
            sys.exit(1)

        if response.lower() not in ['yes', 'y']:
            print("Cancelled.")
            sys.exit(0)

    success = main()
    sys.exit(0 if success else 1)
