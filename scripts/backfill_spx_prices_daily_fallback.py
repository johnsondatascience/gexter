#!/usr/bin/env python3
"""
Backfill SPX Prices - Daily Fallback for Old Data

This script backfills SPX spot prices using DAILY data for timestamps
that are too old to have intraday data available from the API.
"""

import pandas as pd
from datetime import datetime
import sys
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.tradier_api import TradierAPI
from src.config import Config


def main():
    load_dotenv()
    config = Config()
    api = TradierAPI(config.tradier_api_key)

    print("=" * 80)
    print("SPX PRICE BACKFILL - DAILY DATA FALLBACK")
    print("=" * 80)
    print(f"Database Type: {config.database_type}\n")

    # Connect to database
    if config.database_type == 'postgresql':
        conn_string = (
            f"postgresql://{config.postgres_user}:{config.postgres_password}@"
            f"{config.postgres_host}:{config.postgres_port}/{config.postgres_db}"
        )
        engine = create_engine(conn_string)
    else:
        print("ERROR: Only PostgreSQL is supported")
        return False

    # Get timestamps still needing backfill
    print("1. Finding timestamps without SPX data...")
    query = """
    SELECT DISTINCT "greeks.updated_at" as timestamp
    FROM gex_table
    WHERE spx_price IS NULL
    ORDER BY "greeks.updated_at"
    """
    timestamps_df = pd.read_sql(query, engine)
    timestamps_df['timestamp'] = pd.to_datetime(timestamps_df['timestamp'])

    if timestamps_df.empty:
        print("   No timestamps need backfilling!")
        return True

    print(f"   Found {len(timestamps_df)} timestamps without SPX data")
    print(f"   Date range: {timestamps_df['timestamp'].min()} to {timestamps_df['timestamp'].max()}")

    # Get daily SPX data
    start_date = timestamps_df['timestamp'].min().strftime('%Y-%m-%d')
    end_date = timestamps_df['timestamp'].max().strftime('%Y-%m-%d')

    print(f"\n2. Fetching daily SPX data from {start_date} to {end_date}...")
    spx_daily = api.get_historical_quote('SPX', start_date, end_date, 'daily')

    if spx_daily.empty:
        print("   ERROR: Could not fetch daily SPX data")
        return False

    print(f"   Fetched {len(spx_daily)} days of data")

    # Prepare daily data
    spx_daily['date'] = pd.to_datetime(spx_daily['date'])
    spx_daily['last'] = spx_daily['close']
    spx_daily['prev_close'] = spx_daily['close'].shift(1)
    spx_daily['change'] = spx_daily['close'] - spx_daily['prev_close']
    spx_daily['change_pct'] = (spx_daily['change'] / spx_daily['prev_close']) * 100

    # Match timestamps to daily data by date
    print("\n3. Matching timestamps to daily SPX data...")
    timestamps_df['date'] = timestamps_df['timestamp'].dt.date
    spx_daily['date_only'] = spx_daily['date'].dt.date

    matched = timestamps_df.merge(
        spx_daily,
        left_on='date',
        right_on='date_only',
        how='left'
    )

    matched_count = matched['last'].notna().sum()
    print(f"   Matched {matched_count}/{len(matched)} timestamps")

    # Update database
    print("\n4. Updating database with daily SPX data...")
    updated_timestamps = 0
    updated_records = 0

    with engine.begin() as conn:
        for _, row in matched[matched['last'].notna()].iterrows():
            timestamp_str = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')

            update_query = text("""
            UPDATE gex_table
            SET
                spx_price = :last,
                spx_daily_open = :open,
                spx_daily_high = :high,
                spx_daily_low = :low,
                spx_daily_close = :close,
                spx_open = :open,
                spx_high = :high,
                spx_low = :low,
                spx_close = :close,
                spx_change = :change,
                spx_change_pct = :change_pct,
                spx_prevclose = :prev_close
            WHERE "greeks.updated_at" = :timestamp
            AND spx_price IS NULL
            """)

            result = conn.execute(update_query, {
                'last': float(row['last']),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'change': float(row['change']) if pd.notna(row['change']) else None,
                'change_pct': float(row['change_pct']) if pd.notna(row['change_pct']) else None,
                'prev_close': float(row['prev_close']) if pd.notna(row['prev_close']) else None,
                'timestamp': timestamp_str
            })

            if result.rowcount > 0:
                updated_timestamps += 1
                updated_records += result.rowcount

                if updated_timestamps % 10 == 0:
                    print(f"   Progress: {updated_timestamps}/{matched_count} timestamps")

    print(f"\n   Updated {updated_timestamps} timestamps ({updated_records:,} records)")

    # Verify
    print("\n5. Verifying backfill...")
    verify_query = """
    SELECT
        COUNT(*) as total_records,
        COUNT(spx_price) as with_spx_price,
        COUNT(DISTINCT "greeks.updated_at") as total_timestamps
    FROM gex_table
    """
    result = pd.read_sql(verify_query, engine)

    print(f"   Total records: {result.iloc[0]['total_records']:,}")
    print(f"   Records with SPX price: {result.iloc[0]['with_spx_price']:,}")

    missing_query = "SELECT COUNT(DISTINCT \"greeks.updated_at\") as count FROM gex_table WHERE spx_price IS NULL"
    missing = pd.read_sql(missing_query, engine)
    missing_count = missing.iloc[0]['count']

    print("\n" + "=" * 80)
    if missing_count == 0:
        print("[SUCCESS] ALL TIMESTAMPS NOW HAVE SPX DATA")
    else:
        print(f"[PARTIAL] {missing_count} timestamps still missing SPX data")
    print("=" * 80)
    print(f"Records updated: {updated_records:,}")
    print("Note: Daily data used for timestamps beyond intraday API limit")

    return missing_count == 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Backfill SPX prices using daily data')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation')
    args = parser.parse_args()

    if not args.yes:
        print("\nThis will backfill missing SPX prices using DAILY data.")
        print("This is a fallback for old timestamps beyond the intraday API limit.")
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
