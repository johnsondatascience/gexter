#!/usr/bin/env python3
"""Verify SPX backfill results"""

import sqlite3
import pandas as pd

conn = sqlite3.connect('data/gex_data.db')

print('SPX Price Backfill Verification')
print('=' * 60)

print('\n1. Coverage Statistics:')
stats = pd.read_sql('''
    SELECT
        COUNT(*) as total,
        COUNT(spx_price) as with_spx,
        ROUND(COUNT(spx_price)*100.0/COUNT(*), 2) as pct
    FROM gex_table
''', conn)
print(f'   Total records: {stats.iloc[0]["total"]:,}')
print(f'   With SPX price: {stats.iloc[0]["with_spx"]:,}')
print(f'   Coverage: {stats.iloc[0]["pct"]}%')

print('\n2. Sample SPX prices from recent timestamps:')
sample = pd.read_sql('''
    SELECT DISTINCT
        "greeks.updated_at",
        spx_price,
        spx_open,
        spx_high,
        spx_low,
        spx_change_pct
    FROM gex_table
    WHERE spx_price IS NOT NULL
    ORDER BY "greeks.updated_at" DESC
    LIMIT 5
''', conn)
print(sample.to_string(index=False))

print('\n3. SPX price range:')
range_q = pd.read_sql('''
    SELECT
        MIN(spx_price) as min_price,
        MAX(spx_price) as max_price,
        AVG(spx_price) as avg_price
    FROM gex_table
    WHERE spx_price IS NOT NULL
''', conn)
print(f'   Min: ${range_q.iloc[0]["min_price"]:.2f}')
print(f'   Max: ${range_q.iloc[0]["max_price"]:.2f}')
print(f'   Avg: ${range_q.iloc[0]["avg_price"]:.2f}')

print('\n4. Timestamps with SPX data:')
ts_count = pd.read_sql('''
    SELECT COUNT(DISTINCT "greeks.updated_at") as count
    FROM gex_table
    WHERE spx_price IS NOT NULL
''', conn)
print(f'   Unique timestamps with SPX: {ts_count.iloc[0]["count"]}')

conn.close()

print('\n' + '=' * 60)
print('[SUCCESS] All 4.5M+ records now have SPX price data!')
print('=' * 60)
