import sqlite3
import pandas as pd

# Connect to database and analyze schema
conn = sqlite3.connect('gex_data.db')

# Get table schema
schema_query = "PRAGMA table_info(gex_table)"
schema = pd.read_sql(schema_query, conn)
print("Current database schema:")
print(schema)

# Check available Greek columns
greek_columns = schema[schema['name'].str.contains('greeks', case=False, na=False)]['name'].tolist()
print(f"\nAvailable Greek columns: {greek_columns}")

# Sample recent data to understand structure
sample_query = """
SELECT * FROM gex_table 
ORDER BY [greeks.updated_at] DESC 
LIMIT 5
"""
sample = pd.read_sql(sample_query, conn)
print(f"\nSample data columns:")
print(list(sample.columns))

# Check unique option types, strikes, and expirations
unique_query = """
SELECT 
    COUNT(DISTINCT option_type) as unique_option_types,
    COUNT(DISTINCT strike) as unique_strikes,
    COUNT(DISTINCT expiration_date) as unique_expirations,
    COUNT(DISTINCT [greeks.updated_at]) as unique_timestamps
FROM gex_table
"""
unique_stats = pd.read_sql(unique_query, conn)
print(f"\nData uniqueness stats:")
print(unique_stats)

conn.close()