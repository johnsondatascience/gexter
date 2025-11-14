import sqlite3
import pandas as pd
from datetime import datetime

# Connect to database and check data
conn = sqlite3.connect('gex_data.db')

# Check most recent timestamp
query = "SELECT MAX([greeks.updated_at]) AS max_updated_at FROM gex_table"
most_recent = pd.read_sql(query, conn)['max_updated_at'].iloc[0]
print(f"Most recent data timestamp: {most_recent}")

# Count total records
count_query = "SELECT COUNT(*) AS total_records FROM gex_table"
total_records = pd.read_sql(count_query, conn)['total_records'].iloc[0]
print(f"Total records in database: {total_records}")

# Check date range
date_range_query = """
SELECT 
    MIN(DATE([greeks.updated_at])) AS earliest_date,
    MAX(DATE([greeks.updated_at])) AS latest_date
FROM gex_table
"""
date_range = pd.read_sql(date_range_query, conn)
print(f"Date range: {date_range['earliest_date'].iloc[0]} to {date_range['latest_date'].iloc[0]}")

conn.close()