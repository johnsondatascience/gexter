#!/usr/bin/env python3
"""
Check available historical data for backtesting
"""
import psycopg2
import pandas as pd
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

# Connect to database
conn = psycopg2.connect(
    host=os.getenv('POSTGRES_HOST', 'localhost'),
    port=os.getenv('POSTGRES_PORT', 5432),
    database=os.getenv('POSTGRES_DB', 'gexdb'),
    user=os.getenv('POSTGRES_USER', 'gexuser'),
    password=os.getenv('POSTGRES_PASSWORD')
)

print("=" * 80)
print("HISTORICAL DATA SUMMARY FOR BACKTESTING")
print("=" * 80)

# Check date range
date_query = """
SELECT
    MIN("greeks.updated_at") as earliest_timestamp,
    MAX("greeks.updated_at") as latest_timestamp,
    MIN(DATE("greeks.updated_at")) as earliest_date,
    MAX(DATE("greeks.updated_at")) as latest_date,
    COUNT(DISTINCT DATE("greeks.updated_at")) as trading_days,
    COUNT(*) as total_records
FROM gex_table
"""

df_dates = pd.read_sql(date_query, conn)
print("\n[DATE RANGE]:")
print(f"  Earliest: {df_dates['earliest_date'].iloc[0]}")
print(f"  Latest: {df_dates['latest_date'].iloc[0]}")
print(f"  Trading days: {df_dates['trading_days'].iloc[0]}")
print(f"  Total records: {df_dates['total_records'].iloc[0]:,}")

# Check data by expiration
exp_query = """
SELECT
    expiration_date,
    COUNT(*) as option_count,
    COUNT(DISTINCT strike) as unique_strikes,
    MIN(strike) as min_strike,
    MAX(strike) as max_strike,
    AVG(spx_price) as avg_spx_price
FROM gex_table
WHERE "greeks.updated_at" = (SELECT MAX("greeks.updated_at") FROM gex_table)
GROUP BY expiration_date
ORDER BY expiration_date
LIMIT 10
"""

df_exp = pd.read_sql(exp_query, conn)
print("\n[LATEST SNAPSHOT - EXPIRATIONS AVAILABLE]:")
print(df_exp.to_string(index=False))

# Check if we have closing prices (for EOD strategy)
eod_query = """
SELECT
    DATE("greeks.updated_at") as trade_date,
    COUNT(DISTINCT "greeks.updated_at") as snapshots_per_day,
    MIN(EXTRACT(HOUR FROM "greeks.updated_at")) as earliest_hour,
    MAX(EXTRACT(HOUR FROM "greeks.updated_at")) as latest_hour
FROM gex_table
GROUP BY DATE("greeks.updated_at")
ORDER BY trade_date DESC
LIMIT 5
"""

df_eod = pd.read_sql(eod_query, conn)
print("\n[RECENT DAYS - DATA COLLECTION PATTERN]:")
print(df_eod.to_string(index=False))

# Check SPX price data availability
spx_query = """
SELECT
    COUNT(DISTINCT spx_price) as unique_prices,
    MIN(spx_price) as min_price,
    MAX(spx_price) as max_price
FROM gex_table
WHERE "greeks.updated_at" >= NOW() - INTERVAL '7 days'
"""

df_spx = pd.read_sql(spx_query, conn)
print("\n[SPX PRICE DATA (LAST 7 DAYS)]:")
print(f"  Unique prices: {df_spx['unique_prices'].iloc[0]}")
print(f"  Range: ${df_spx['min_price'].iloc[0]:.2f} - ${df_spx['max_price'].iloc[0]:.2f}")

# Check if we have market open/close data
market_hours_query = """
SELECT
    DATE("greeks.updated_at") as trade_date,
    MIN("greeks.updated_at") as first_snapshot,
    MAX("greeks.updated_at") as last_snapshot,
    EXTRACT(HOUR FROM MIN("greeks.updated_at")) as first_hour,
    EXTRACT(HOUR FROM MAX("greeks.updated_at")) as last_hour
FROM gex_table
WHERE "greeks.updated_at" >= NOW() - INTERVAL '5 days'
GROUP BY DATE("greeks.updated_at")
ORDER BY trade_date DESC
"""

df_hours = pd.read_sql(market_hours_query, conn)
print("\n[MARKET HOURS COVERAGE (LAST 5 DAYS)]:")
print(df_hours.to_string(index=False))

# Check if we have intraday bars for SPX
try:
    intraday_query = """
    SELECT
        COUNT(*) as intraday_bars,
        MIN(timestamp) as first_bar,
        MAX(timestamp) as last_bar
    FROM spx_indicators
    WHERE timestamp >= NOW() - INTERVAL '7 days'
    """
    df_intraday = pd.read_sql(intraday_query, conn)
    print("\n[SPX INDICATORS (EMAs, etc.)]:")
    print(f"  Intraday bars: {df_intraday['intraday_bars'].iloc[0]}")
    print(f"  First bar: {df_intraday['first_bar'].iloc[0]}")
    print(f"  Last bar: {df_intraday['last_bar'].iloc[0]}")
except Exception as e:
    print(f"\n[WARNING] SPX Indicators table not available: {e}")

conn.close()

print("\n" + "=" * 80)
print("[SUCCESS] Data check complete!")
print("=" * 80)
