#!/usr/bin/env python3
"""
Backfill SPX Prices for Historical GEX Data

This script backfills SPX spot prices for existing GEX records by:
1. Identifying all timestamps that need SPX price data
2. Fetching historical intraday SPX data from Tradier API
3. Matching the closest SPX price to each Greek calculation timestamp
4. Updating the database with SPX price data
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import shutil
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.tradier_api import TradierAPI
from src.config import Config

def create_backup(db_path: str) -> str:
    """Create a backup of the database"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_spx_backfill_{timestamp}"

    print(f"\n1. Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)

    if os.path.exists(backup_path):
        backup_size = os.path.getsize(backup_path) / (1024**3)  # GB
        print(f"   [OK] Backup created successfully ({backup_size:.2f} GB)")
        return backup_path
    else:
        raise Exception("Backup creation failed!")

def get_timestamps_to_backfill(conn: sqlite3.Connection):
    """Get all unique timestamps that need SPX price data"""
    print("\n2. Analyzing timestamps that need backfilling...")

    query = """
    SELECT DISTINCT "greeks.updated_at" as timestamp
    FROM gex_table
    WHERE spx_price IS NULL
    ORDER BY "greeks.updated_at"
    """

    df = pd.read_sql(query, conn)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f"   Timestamps needing backfill: {len(df)}")

    if len(df) > 0:
        print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    return df

def fetch_spx_historical_data(api: TradierAPI, start_date: str, end_date: str):
    """Fetch historical SPX data (daily OHLC)"""
    print(f"\n3. Fetching SPX historical data from {start_date} to {end_date}...")

    # Calculate number of days
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    total_days = (end - start).days + 1

    print(f"   Fetching {total_days} days of daily OHLC data...")

    try:
        # Use the historical quotes API which supports date ranges
        historical_data = api.get_historical_quote('SPX', start_date, end_date, 'daily')

        if not historical_data.empty:
            # Convert date to datetime for matching
            historical_data['timestamp'] = pd.to_datetime(historical_data['date'])

            # Use close as the primary price
            historical_data['last'] = historical_data['close']

            # Calculate change from previous day
            historical_data['prev_close'] = historical_data['close'].shift(1)
            historical_data['change'] = historical_data['close'] - historical_data['prev_close']
            historical_data['change_pct'] = (historical_data['change'] / historical_data['prev_close']) * 100

            print(f"   [OK] Fetched {len(historical_data)} days of data")
            print(f"   Date range: {historical_data['date'].min()} to {historical_data['date'].max()}")

            return historical_data
        else:
            print("   [WARNING] No historical data returned")
            return pd.DataFrame()

    except Exception as e:
        print(f"   [ERROR] Failed to fetch historical data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def match_prices_to_timestamps(timestamps_df: pd.DataFrame, spx_data: pd.DataFrame):
    """Match SPX prices to Greek calculation timestamps by date"""
    print("\n4. Matching SPX prices to Greek timestamps...")

    if spx_data.empty:
        print("   [ERROR] No SPX data available for matching")
        return pd.DataFrame()

    # Ensure timestamp is datetime
    timestamps_df['timestamp'] = pd.to_datetime(timestamps_df['timestamp'])
    spx_data['timestamp'] = pd.to_datetime(spx_data['timestamp'])

    # Extract date for matching (since we have daily data)
    timestamps_df['date'] = timestamps_df['timestamp'].dt.date
    spx_data['date'] = spx_data['timestamp'].dt.date

    print(f"   Greek timestamps: {len(timestamps_df)}")
    print(f"   SPX data points: {len(spx_data)}")

    # Merge on date to match daily SPX data to intraday Greek timestamps
    matched = timestamps_df.merge(
        spx_data,
        on='date',
        how='left',
        suffixes=('', '_spx')
    )

    # Drop the extra timestamp column from SPX data
    if 'timestamp_spx' in matched.columns:
        matched = matched.drop('timestamp_spx', axis=1)

    # Count successful matches
    matched_count = matched['last'].notna().sum()
    print(f"   Successful matches: {matched_count}/{len(matched)}")

    if matched_count < len(matched):
        unmatched = len(matched) - matched_count
        print(f"   [WARNING] {unmatched} timestamps could not be matched (likely weekends/holidays)")

        # Show sample of unmatched dates
        unmatched_dates = matched[matched['last'].isna()]['date'].unique()[:5]
        if len(unmatched_dates) > 0:
            print(f"   Sample unmatched dates: {', '.join(str(d) for d in unmatched_dates)}")

    return matched

def update_database(conn: sqlite3.Connection, matched_data: pd.DataFrame):
    """Update gex_table with matched SPX prices"""
    print("\n5. Updating database with SPX prices...")

    if matched_data.empty:
        print("   [ERROR] No data to update")
        return 0

    cursor = conn.cursor()
    updated_timestamps = 0
    updated_records = 0

    for idx, row in matched_data.iterrows():
        if pd.notna(row['last']):  # Only update if we have a price
            timestamp_str = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')

            # Update all records with this timestamp
            update_query = """
            UPDATE gex_table
            SET
                spx_price = ?,
                spx_open = ?,
                spx_high = ?,
                spx_low = ?,
                spx_close = ?,
                spx_change = ?,
                spx_change_pct = ?,
                spx_prevclose = ?
            WHERE "greeks.updated_at" = ?
            AND spx_price IS NULL
            """

            cursor.execute(update_query, (
                row['last'],
                row.get('open'),
                row.get('high'),
                row.get('low'),
                row.get('close'),
                row.get('change'),
                row.get('change_pct'),
                row.get('prev_close'),
                timestamp_str
            ))

            rows_affected = cursor.rowcount
            if rows_affected > 0:
                updated_timestamps += 1
                updated_records += rows_affected

                if (updated_timestamps % 10 == 0):
                    print(f"   Progress: {updated_timestamps}/{len(matched_data)} timestamps, {updated_records:,} records updated")

    conn.commit()

    print(f"\n   [OK] Updated {updated_timestamps} timestamps ({updated_records:,} records)")
    return updated_records

def verify_backfill(conn: sqlite3.Connection):
    """Verify the backfill was successful"""
    print("\n6. Verifying backfill...")

    query = """
    SELECT
        COUNT(*) as total_records,
        COUNT(spx_price) as with_spx_price,
        COUNT(DISTINCT "greeks.updated_at") as total_timestamps,
        SUM(CASE WHEN spx_price IS NOT NULL THEN 1 ELSE 0 END) /
            COUNT(DISTINCT "greeks.updated_at") as timestamps_with_spx
    FROM gex_table
    """

    result = pd.read_sql(query, conn)

    print(f"   Total records: {result.iloc[0]['total_records']:,}")
    print(f"   Records with SPX price: {result.iloc[0]['with_spx_price']:,}")
    print(f"   Total timestamps: {result.iloc[0]['total_timestamps']}")

    # Check if any timestamps still missing SPX data
    missing_query = """
    SELECT COUNT(DISTINCT "greeks.updated_at") as count
    FROM gex_table
    WHERE spx_price IS NULL
    """

    missing = pd.read_sql(missing_query, conn)
    missing_count = missing.iloc[0]['count']

    if missing_count == 0:
        print("\n   [SUCCESS] All timestamps now have SPX price data!")
        return True
    else:
        print(f"\n   [WARNING] {missing_count} timestamps still missing SPX data")

        # Show sample of missing timestamps
        sample_query = """
        SELECT DISTINCT "greeks.updated_at"
        FROM gex_table
        WHERE spx_price IS NULL
        ORDER BY "greeks.updated_at" DESC
        LIMIT 5
        """
        samples = pd.read_sql(sample_query, conn)
        print("\n   Sample missing timestamps:")
        for ts in samples['greeks.updated_at']:
            print(f"     - {ts}")

        return False

def main():
    db_path = 'data/gex_data.db'

    print("=" * 80)
    print("SPX PRICE BACKFILL")
    print("=" * 80)
    print(f"\nDatabase: {db_path}")

    # Load environment and initialize API
    load_dotenv()
    config = Config()
    api = TradierAPI(config.tradier_api_key)

    try:
        # Create backup
        backup_path = create_backup(db_path)

        # Connect to database
        conn = sqlite3.connect(db_path)

        # Get timestamps to backfill
        timestamps_df = get_timestamps_to_backfill(conn)

        if timestamps_df.empty:
            print("\n[INFO] No timestamps need backfilling!")
            conn.close()
            return True

        # Determine date range
        start_date = timestamps_df['timestamp'].min().strftime('%Y-%m-%d')
        end_date = timestamps_df['timestamp'].max().strftime('%Y-%m-%d')

        # Fetch historical SPX data
        spx_data = fetch_spx_historical_data(api, start_date, end_date)

        if spx_data.empty:
            print("\n[ERROR] Could not fetch SPX historical data")
            conn.close()
            return False

        # Match prices to timestamps
        matched_data = match_prices_to_timestamps(timestamps_df, spx_data)

        # Update database
        records_updated = update_database(conn, matched_data)

        # Verify
        success = verify_backfill(conn)

        conn.close()

        print("\n" + "=" * 80)
        if success:
            print("[SUCCESS] SPX PRICE BACKFILL COMPLETE")
        else:
            print("[PARTIAL] SPX PRICE BACKFILL PARTIALLY COMPLETE")
        print("=" * 80)
        print(f"\nBackup saved to: {backup_path}")
        print(f"Records updated: {records_updated:,}")

        return success

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Backfill SPX prices for historical GEX data')
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Skip confirmation prompt')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    args = parser.parse_args()

    if not args.yes and not args.dry_run:
        print("\nThis script will backfill SPX prices for all historical GEX records.")
        print("It will fetch historical intraday data from the Tradier API.")
        print("A backup will be created automatically.")
        try:
            response = input("\nProceed? (yes/no): ")
        except EOFError:
            print("\nNo input provided. Use --yes flag to run without confirmation.")
            sys.exit(1)

        if response.lower() not in ['yes', 'y']:
            print("Backfill cancelled.")
            sys.exit(0)

    success = main()
    sys.exit(0 if success else 1)
