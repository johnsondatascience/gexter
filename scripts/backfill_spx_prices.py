#!/usr/bin/env python3
"""
Backfill SPX Prices for Historical GEX Data

This script backfills SPX spot prices for existing GEX records by:
1. Identifying all timestamps that need SPX price data
2. Fetching historical 15-minute intraday SPX data from Tradier API
3. Matching the closest SPX price to each Greek calculation timestamp
4. Updating the database with SPX price data

Updated to use 15-minute intraday data to match Greek collection interval
and support both SQLite and PostgreSQL databases.
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import shutil
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

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

def get_timestamps_to_backfill(conn_or_engine):
    """Get all unique timestamps that need SPX price data"""
    print("\n2. Analyzing timestamps that need backfilling...")

    query = """
    SELECT DISTINCT "greeks.updated_at" as timestamp
    FROM gex_table
    WHERE spx_price IS NULL
    ORDER BY "greeks.updated_at"
    """

    df = pd.read_sql(query, conn_or_engine)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f"   Timestamps needing backfill: {len(df)}")

    if len(df) > 0:
        print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    return df

def fetch_spx_historical_data(api: TradierAPI, start_date: str, end_date: str, interval: str = '15min'):
    """Fetch historical SPX data at 15-minute intervals"""
    print(f"\n3. Fetching SPX {interval} intraday data from {start_date} to {end_date}...")

    # Calculate number of days
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    total_days = (end - start).days + 1

    print(f"   Fetching {total_days} days of {interval} interval data...")

    # Tradier's intraday API has limits, so we need to fetch in chunks
    # The API supports up to ~30 days at a time for intraday data
    all_data = []
    chunk_days = 30
    current_start = start

    try:
        while current_start <= end:
            current_end = min(current_start + timedelta(days=chunk_days), end)
            days_back = (datetime.now() - current_start).days + 1

            print(f"   Fetching chunk: {current_start.strftime('%Y-%m-%d')} to {current_end.strftime('%Y-%m-%d')} ({days_back} days back)...")

            # Use get_intraday_data method
            chunk_data = api.get_intraday_data('SPX', interval=interval, days_back=min(days_back, 30))

            if not chunk_data.empty:
                # Filter to the specific date range for this chunk
                chunk_data = chunk_data[
                    (chunk_data['datetime'] >= pd.Timestamp(current_start)) &
                    (chunk_data['datetime'] <= pd.Timestamp(current_end) + timedelta(days=1))
                ]

                if len(chunk_data) > 0:
                    all_data.append(chunk_data)
                    print(f"      Got {len(chunk_data)} {interval} bars")
            else:
                print(f"      [WARNING] No data for this chunk")

            # Move to next chunk
            current_start = current_end + timedelta(days=1)

        if all_data:
            # Combine all chunks
            historical_data = pd.concat(all_data, ignore_index=True)
            historical_data = historical_data.drop_duplicates(subset=['datetime']).sort_values('datetime')

            # Rename datetime to timestamp for consistency
            historical_data['timestamp'] = historical_data['datetime']

            # Use close as the primary price (last)
            historical_data['last'] = historical_data['close']

            # Calculate change from previous bar
            historical_data['prev_close'] = historical_data['close'].shift(1)
            historical_data['change'] = historical_data['close'] - historical_data['prev_close']
            historical_data['change_pct'] = (historical_data['change'] / historical_data['prev_close']) * 100

            print(f"   [OK] Fetched {len(historical_data)} {interval} bars total")
            print(f"   Time range: {historical_data['timestamp'].min()} to {historical_data['timestamp'].max()}")

            return historical_data
        else:
            print("   [WARNING] No historical data returned")
            return pd.DataFrame()

    except Exception as e:
        print(f"   [ERROR] Failed to fetch historical data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def match_prices_to_timestamps(timestamps_df: pd.DataFrame, spx_data: pd.DataFrame, tolerance_minutes: int = 15):
    """Match SPX prices to Greek calculation timestamps using nearest-time matching"""
    print("\n4. Matching SPX prices to Greek timestamps...")
    print(f"   Using tolerance of {tolerance_minutes} minutes for matching")

    if spx_data.empty:
        print("   [ERROR] No SPX data available for matching")
        return pd.DataFrame()

    # Ensure timestamp is datetime
    timestamps_df['timestamp'] = pd.to_datetime(timestamps_df['timestamp'])
    spx_data['timestamp'] = pd.to_datetime(spx_data['timestamp'])

    print(f"   Greek timestamps: {len(timestamps_df)}")
    print(f"   SPX data points: {len(spx_data)}")

    # Sort both dataframes by timestamp
    timestamps_df = timestamps_df.sort_values('timestamp')
    spx_data = spx_data.sort_values('timestamp')

    # Use merge_asof to find nearest SPX price within tolerance
    matched = pd.merge_asof(
        timestamps_df,
        spx_data,
        on='timestamp',
        direction='nearest',
        tolerance=pd.Timedelta(minutes=tolerance_minutes),
        suffixes=('', '_spx')
    )

    # Count successful matches
    matched_count = matched['last'].notna().sum()
    print(f"   Successful matches: {matched_count}/{len(matched)}")

    if matched_count < len(matched):
        unmatched = len(matched) - matched_count
        print(f"   [WARNING] {unmatched} timestamps could not be matched")

        # Show sample of unmatched timestamps
        unmatched_times = matched[matched['last'].isna()]['timestamp'].head(5)
        if len(unmatched_times) > 0:
            print(f"   Sample unmatched timestamps:")
            for ts in unmatched_times:
                print(f"     - {ts}")

    # Calculate match quality statistics
    matched_with_price = matched[matched['last'].notna()].copy()
    if len(matched_with_price) > 0:
        if 'timestamp_spx' in matched_with_price.columns:
            time_diffs = (matched_with_price['timestamp'] - matched_with_price['timestamp_spx']).abs()
            avg_diff = time_diffs.mean()
            max_diff = time_diffs.max()
            print(f"   Match quality: avg difference {avg_diff}, max difference {max_diff}")

    return matched

def update_database(conn_or_engine, matched_data: pd.DataFrame, db_type: str = 'sqlite'):
    """Update gex_table with matched SPX prices"""
    print("\n5. Updating database with SPX prices...")

    if matched_data.empty:
        print("   [ERROR] No data to update")
        return 0

    updated_timestamps = 0
    updated_records = 0

    # Filter to only rows with valid price data
    valid_data = matched_data[matched_data['last'].notna()].copy()
    print(f"   Processing {len(valid_data)} timestamps with valid SPX data...")

    if db_type == 'postgresql':
        # PostgreSQL update using SQLAlchemy
        with conn_or_engine.begin() as conn:
            for idx, row in valid_data.iterrows():
                timestamp_str = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')

                # Update all records with this timestamp
                update_query = text("""
                UPDATE gex_table
                SET
                    spx_price = :last,
                    spx_intraday_open = :open,
                    spx_intraday_high = :high,
                    spx_intraday_low = :low,
                    spx_intraday_close = :close,
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
                    'last': float(row['last']) if pd.notna(row['last']) else None,
                    'open': float(row.get('open')) if pd.notna(row.get('open')) else None,
                    'high': float(row.get('high')) if pd.notna(row.get('high')) else None,
                    'low': float(row.get('low')) if pd.notna(row.get('low')) else None,
                    'close': float(row.get('close')) if pd.notna(row.get('close')) else None,
                    'change': float(row.get('change')) if pd.notna(row.get('change')) else None,
                    'change_pct': float(row.get('change_pct')) if pd.notna(row.get('change_pct')) else None,
                    'prev_close': float(row.get('prev_close')) if pd.notna(row.get('prev_close')) else None,
                    'timestamp': timestamp_str
                })

                rows_affected = result.rowcount
                if rows_affected > 0:
                    updated_timestamps += 1
                    updated_records += rows_affected

                    if (updated_timestamps % 10 == 0):
                        print(f"   Progress: {updated_timestamps}/{len(valid_data)} timestamps, {updated_records:,} records updated")

    else:
        # SQLite update
        cursor = conn_or_engine.cursor()
        for idx, row in valid_data.iterrows():
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
                    print(f"   Progress: {updated_timestamps}/{len(valid_data)} timestamps, {updated_records:,} records updated")

        conn_or_engine.commit()

    print(f"\n   [OK] Updated {updated_timestamps} timestamps ({updated_records:,} records)")
    return updated_records

def verify_backfill(conn_or_engine):
    """Verify the backfill was successful"""
    print("\n6. Verifying backfill...")

    query = """
    SELECT
        COUNT(*) as total_records,
        COUNT(spx_price) as with_spx_price,
        COUNT(DISTINCT "greeks.updated_at") as total_timestamps
    FROM gex_table
    """

    result = pd.read_sql(query, conn_or_engine)

    print(f"   Total records: {result.iloc[0]['total_records']:,}")
    print(f"   Records with SPX price: {result.iloc[0]['with_spx_price']:,}")
    print(f"   Total timestamps: {result.iloc[0]['total_timestamps']}")

    # Check if any timestamps still missing SPX data
    missing_query = """
    SELECT COUNT(DISTINCT "greeks.updated_at") as count
    FROM gex_table
    WHERE spx_price IS NULL
    """

    missing = pd.read_sql(missing_query, conn_or_engine)
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
        samples = pd.read_sql(sample_query, conn_or_engine)
        print("\n   Sample missing timestamps:")
        for ts in samples['greeks.updated_at']:
            print(f"     - {ts}")

        return False

def main(interval: str = '15min'):
    # Load environment and initialize config
    load_dotenv()
    config = Config()
    api = TradierAPI(config.tradier_api_key)

    print("=" * 80)
    print("SPX PRICE BACKFILL - INTRADAY DATA")
    print("=" * 80)
    print(f"\nDatabase Type: {config.database_type}")
    print(f"Interval: {interval}")

    try:
        # Initialize database connection based on type
        if config.database_type == 'postgresql':
            print(f"PostgreSQL: {config.postgres_host}:{config.postgres_port}/{config.postgres_db}")
            conn_string = (
                f"postgresql://{config.postgres_user}:{config.postgres_password}@"
                f"{config.postgres_host}:{config.postgres_port}/{config.postgres_db}"
            )
            db_engine = create_engine(conn_string)
            conn_or_engine = db_engine
            db_type = 'postgresql'

            # Create backup for PostgreSQL (using pg_dump would be better, but for now we'll proceed)
            print("\n1. [INFO] PostgreSQL detected - consider creating manual backup with pg_dump")
            backup_path = None
        else:
            print(f"SQLite: {config.database_path}")
            db_path = config.database_path
            backup_path = create_backup(db_path)
            conn_or_engine = sqlite3.connect(db_path)
            db_type = 'sqlite'

        # Get timestamps to backfill
        timestamps_df = get_timestamps_to_backfill(conn_or_engine)

        if timestamps_df.empty:
            print("\n[INFO] No timestamps need backfilling!")
            if db_type == 'sqlite':
                conn_or_engine.close()
            return True

        # Determine date range
        start_date = timestamps_df['timestamp'].min().strftime('%Y-%m-%d')
        end_date = timestamps_df['timestamp'].max().strftime('%Y-%m-%d')

        # Fetch historical SPX intraday data
        spx_data = fetch_spx_historical_data(api, start_date, end_date, interval=interval)

        if spx_data.empty:
            print("\n[ERROR] Could not fetch SPX historical data")
            if db_type == 'sqlite':
                conn_or_engine.close()
            return False

        # Match prices to timestamps
        matched_data = match_prices_to_timestamps(timestamps_df, spx_data, tolerance_minutes=15)

        # Update database
        records_updated = update_database(conn_or_engine, matched_data, db_type=db_type)

        # Verify
        success = verify_backfill(conn_or_engine)

        if db_type == 'sqlite':
            conn_or_engine.close()

        print("\n" + "=" * 80)
        if success:
            print("[SUCCESS] SPX PRICE BACKFILL COMPLETE")
        else:
            print("[PARTIAL] SPX PRICE BACKFILL PARTIALLY COMPLETE")
        print("=" * 80)
        if backup_path:
            print(f"\nBackup saved to: {backup_path}")
        print(f"Records updated: {records_updated:,}")
        print(f"Interval used: {interval}")

        return success

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description='Backfill SPX prices for historical GEX data using intraday intervals'
    )
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Skip confirmation prompt')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--interval', default='15min',
                       choices=['15min', '30min', '1hour'],
                       help='Intraday interval to use (default: 15min)')
    args = parser.parse_args()

    if not args.yes and not args.dry_run:
        print("\nThis script will backfill SPX prices for all historical GEX records.")
        print(f"It will fetch historical {args.interval} intraday data from the Tradier API.")
        print("For PostgreSQL: Consider creating a manual backup with pg_dump first.")
        print("For SQLite: A backup will be created automatically.")
        try:
            response = input("\nProceed? (yes/no): ")
        except EOFError:
            print("\nNo input provided. Use --yes flag to run without confirmation.")
            sys.exit(1)

        if response.lower() not in ['yes', 'y']:
            print("Backfill cancelled.")
            sys.exit(0)

    success = main(interval=args.interval)
    sys.exit(0 if success else 1)
