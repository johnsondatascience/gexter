#!/usr/bin/env python3
"""
Analyze differences between gex_table, dgex_table, and default.gex_table
"""

import sqlite3
import pandas as pd

def main():
    conn = sqlite3.connect('data/gex_data.db')

    print("=" * 80)
    print("DATABASE TABLE DIFFERENCE ANALYSIS")
    print("=" * 80)

    # Find records in dgex_table NOT in gex_table
    print("\n1. Finding records in dgex_table NOT in gex_table...")
    query_dgex_missing = """
    SELECT
        d."greeks.updated_at",
        d.expiration_date,
        d.option_type,
        d.strike,
        d.last,
        d.open_interest,
        d.gex
    FROM dgex_table d
    LEFT JOIN gex_table g ON
        d."greeks.updated_at" = g."greeks.updated_at" AND
        d.expiration_date = g.expiration_date AND
        d.option_type = g.option_type AND
        d.strike = g.strike
    WHERE g.strike IS NULL
    """

    missing_from_gex = pd.read_sql(query_dgex_missing, conn)
    print(f"\nRecords in dgex_table but NOT in gex_table: {len(missing_from_gex)}")

    if len(missing_from_gex) > 0:
        print("\nSample of missing records (first 10):")
        print(missing_from_gex.head(10))

        # Group by timestamp
        print("\nMissing records by timestamp:")
        timestamp_counts = missing_from_gex.groupby('greeks.updated_at').size()
        print(timestamp_counts)

    # Find records in gex_table NOT in dgex_table (for same date range)
    print("\n\n2. Finding records in gex_table NOT in dgex_table (same date range)...")
    query_gex_extra = """
    SELECT
        g."greeks.updated_at",
        g.expiration_date,
        g.option_type,
        g.strike,
        g.last,
        g.open_interest,
        g.gex
    FROM gex_table g
    LEFT JOIN dgex_table d ON
        g."greeks.updated_at" = d."greeks.updated_at" AND
        g.expiration_date = d.expiration_date AND
        g.option_type = d.option_type AND
        g.strike = d.strike
    WHERE
        g."greeks.updated_at" BETWEEN '2025-03-18 20:00:10' AND '2025-03-19 18:59:10'
        AND d.strike IS NULL
    """

    extra_in_gex = pd.read_sql(query_gex_extra, conn)
    print(f"\nRecords in gex_table but NOT in dgex_table (same dates): {len(extra_in_gex)}")

    if len(extra_in_gex) > 0:
        print("\nSample of extra records (first 10):")
        print(extra_in_gex.head(10))

        # Group by timestamp
        print("\nExtra records by timestamp:")
        timestamp_counts = extra_in_gex.groupby('greeks.updated_at').size()
        print(timestamp_counts)

    # Analyze default.gex_table
    print("\n\n3. Analyzing default.gex_table...")
    query_default_missing = """
    SELECT
        d."greeks.updated_at",
        d.expiration_date,
        d.option_type,
        d.strike,
        d.last,
        d.open_interest,
        d.gex
    FROM "default.gex_table" d
    LEFT JOIN gex_table g ON
        d."greeks.updated_at" = g."greeks.updated_at" AND
        d.expiration_date = g.expiration_date AND
        d.option_type = g.option_type AND
        d.strike = g.strike
    WHERE g.strike IS NULL
    """

    default_missing = pd.read_sql(query_default_missing, conn)
    print(f"\nRecords in default.gex_table but NOT in gex_table: {len(default_missing)}")

    if len(default_missing) > 0:
        print("\nSample of missing records (first 10):")
        print(default_missing.head(10))

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nUnique records in dgex_table: {len(missing_from_gex)}")
    print(f"Unique records in gex_table (overlapping dates): {len(extra_in_gex)}")
    print(f"Unique records in default.gex_table: {len(default_missing)}")

    # Recommendation
    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)

    if len(missing_from_gex) > 0:
        print("\n⚠️  WARNING: dgex_table contains unique data NOT in gex_table!")
        print("   Suggested action: MIGRATE unique records to gex_table before dropping")
    else:
        print("\n✅ dgex_table has no unique data. Safe to drop.")

    if len(default_missing) > 0:
        print("\n⚠️  WARNING: default.gex_table contains unique data NOT in gex_table!")
        print("   Suggested action: MIGRATE unique records to gex_table before dropping")
    else:
        print("\n✅ default.gex_table has no unique data. Safe to drop.")

    conn.close()

if __name__ == "__main__":
    main()
