#!/usr/bin/env python3
"""
Test SPX Price Tracking

Quick test to verify SPX price data is being saved correctly
"""

import sqlite3
import pandas as pd
from datetime import datetime

def test_schema():
    """Test that SPX columns exist"""
    print("1. Testing database schema...")

    conn = sqlite3.connect('data/gex_data.db')
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(gex_table)")
    columns = [row[1] for row in cursor.fetchall()]

    spx_columns = [col for col in columns if col.startswith('spx_')]

    print(f"   SPX columns found: {len(spx_columns)}")
    for col in spx_columns:
        print(f"     - {col}")

    conn.close()

    return len(spx_columns) == 10

def test_data():
    """Test if any SPX data has been saved"""
    print("\n2. Testing for existing SPX data...")

    conn = sqlite3.connect('data/gex_data.db')

    query = """
    SELECT
        COUNT(*) as total_records,
        COUNT(spx_price) as records_with_spx,
        MIN("greeks.updated_at") as earliest_spx_data,
        MAX("greeks.updated_at") as latest_spx_data
    FROM gex_table
    WHERE spx_price IS NOT NULL
    """

    df = pd.read_sql(query, conn)

    print(f"   Total records with SPX price: {df.iloc[0]['records_with_spx']:,}")

    if df.iloc[0]['records_with_spx'] > 0:
        print(f"   Earliest SPX data: {df.iloc[0]['earliest_spx_data']}")
        print(f"   Latest SPX data: {df.iloc[0]['latest_spx_data']}")

        # Show sample
        sample_query = """
        SELECT
            "greeks.updated_at",
            strike,
            option_type,
            spx_price,
            spx_change,
            spx_change_pct
        FROM gex_table
        WHERE spx_price IS NOT NULL
        ORDER BY "greeks.updated_at" DESC
        LIMIT 5
        """

        sample = pd.read_sql(sample_query, conn)
        print("\n   Sample records:")
        print(sample.to_string(index=False))

    conn.close()

    return df.iloc[0]['records_with_spx'] > 0

def main():
    print("=" * 80)
    print("SPX PRICE TRACKING TEST")
    print("=" * 80)

    schema_ok = test_schema()
    data_exists = test_data()

    print("\n" + "=" * 80)
    if schema_ok:
        print("[OK] Schema is correct - 10 SPX columns added")
    else:
        print("[ERROR] Schema issue - SPX columns missing")

    if data_exists:
        print("[OK] SPX price data is being saved to database")
    else:
        print("[INFO] No SPX price data saved yet - run collector to populate")

    print("=" * 80)

if __name__ == "__main__":
    main()
