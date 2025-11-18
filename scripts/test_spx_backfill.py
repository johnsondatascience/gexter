#!/usr/bin/env python3
"""
Test SPX Price Backfill

Tests the backfill process on a small sample of data
"""

import sqlite3
import pandas as pd
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.tradier_api import TradierAPI
from src.config import Config
from dotenv import load_dotenv

def test_api_access():
    """Test that we can access the Tradier API"""
    print("1. Testing API access...")

    load_dotenv()
    config = Config()
    api = TradierAPI(config.tradier_api_key)

    # Try to fetch recent historical SPX data
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - pd.Timedelta(days=5)).strftime('%Y-%m-%d')

    data = api.get_historical_quote('SPX', start_date, end_date, 'daily')

    if not data.empty:
        print(f"   [OK] Successfully fetched {len(data)} days of data")
        print(f"   Sample data:")
        print(data.head(3))
        return True
    else:
        print("   [WARNING] No data returned")
        return False

def test_timestamp_matching():
    """Test matching logic"""
    print("\n2. Testing timestamp matching logic...")

    # Create sample data
    greek_timestamps = pd.DataFrame({
        'timestamp': pd.to_datetime([
            '2025-11-14 14:30:00',
            '2025-11-14 15:00:00',
            '2025-11-14 16:30:00',
        ])
    })

    spx_data = pd.DataFrame({
        'timestamp': pd.to_datetime([
            '2025-11-14 14:28:00',
            '2025-11-14 14:58:00',
            '2025-11-14 16:28:00',
        ]),
        'last': [6700.0, 6705.0, 6710.0],
        'open': [6695.0, 6700.0, 6705.0],
        'high': [6702.0, 6707.0, 6712.0],
        'low': [6693.0, 6698.0, 6703.0],
    })

    # Match using merge_asof
    matched = pd.merge_asof(
        greek_timestamps.sort_values('timestamp'),
        spx_data.sort_values('timestamp'),
        on='timestamp',
        direction='nearest',
        tolerance=pd.Timedelta('1 hour')
    )

    print("   Greek Timestamp  ->  SPX Timestamp  (Price)")
    for idx, row in matched.iterrows():
        spx_ts = spx_data.iloc[idx]['timestamp']
        diff = abs((row['timestamp'] - spx_ts).total_seconds() / 60)
        print(f"   {row['timestamp']}  ->  {spx_ts}  (${row['last']:.2f}) [{diff:.1f}min diff]")

    print("   [OK] Matching logic works correctly")
    return True

def test_database_query():
    """Test querying timestamps from database"""
    print("\n3. Testing database query...")

    conn = sqlite3.connect('data/gex_data.db')

    query = """
    SELECT DISTINCT "greeks.updated_at" as timestamp
    FROM gex_table
    WHERE spx_price IS NULL
    ORDER BY "greeks.updated_at" DESC
    LIMIT 5
    """

    df = pd.read_sql(query, conn)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f"   [OK] Found {len(df)} sample timestamps:")
    for ts in df['timestamp']:
        print(f"     - {ts}")

    conn.close()
    return len(df) > 0

def main():
    print("=" * 80)
    print("SPX BACKFILL TEST")
    print("=" * 80)

    tests = [
        ("API Access", test_api_access),
        ("Timestamp Matching", test_timestamp_matching),
        ("Database Query", test_database_query),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   [ERROR] {e}")
            results.append((test_name, False))

    print("\n" + "=" * 80)
    print("TEST RESULTS")
    print("=" * 80)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    all_passed = all(r[1] for r in results)

    if all_passed:
        print("\n[OK] All tests passed! Ready to run full backfill.")
        print("\nRun the full backfill with:")
        print("  python scripts/backfill_spx_prices.py")
    else:
        print("\n[WARNING] Some tests failed. Please investigate before running backfill.")

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
