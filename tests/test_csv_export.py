#!/usr/bin/env python3
"""
Test CSV export functionality with Greek differences

This script tests the updated CSV export to ensure it includes all
Greek difference columns and creates proper snapshots.
"""

import pandas as pd
import sqlite3
import os
from datetime import datetime
import logging

from src.gex_collector import GEXCollector
from src.config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_csv_export():
    """Test the CSV export functionality"""
    
    logger.info("Testing CSV export with Greek differences...")
    
    try:
        # Create a minimal config for testing
        os.environ['TRADIER_API_KEY'] = 'test_key'
        os.environ['TRADIER_ACCOUNT_ID'] = 'test_account'
        
        config = Config()
        collector = GEXCollector(config)
        
        # Test the export function
        success = collector.export_to_csv()
        
        if success:
            logger.info("CSV export completed successfully")
            
            # Check if files were created
            files_to_check = ['gex.csv', 'gex_summary.csv']
            
            for filename in files_to_check:
                if os.path.exists(filename):
                    df = pd.read_csv(filename)
                    logger.info(f"{filename}: {len(df)} rows, {len(df.columns)} columns")
                    
                    # Check for Greek difference columns
                    diff_columns = [col for col in df.columns if col.endswith('_diff')]
                    pct_change_columns = [col for col in df.columns if col.endswith('_pct_change')]
                    
                    logger.info(f"  Difference columns: {len(diff_columns)}")
                    logger.info(f"  Percentage change columns: {len(pct_change_columns)}")
                    
                    # Show sample of column names
                    if diff_columns:
                        logger.info(f"  Sample diff columns: {diff_columns[:3]}")
                    if pct_change_columns:
                        logger.info(f"  Sample pct columns: {pct_change_columns[:3]}")
                    
                    # Check metadata columns
                    metadata_cols = ['prev_timestamp', 'has_previous_data']
                    present_metadata = [col for col in metadata_cols if col in df.columns]
                    logger.info(f"  Metadata columns: {present_metadata}")
                    
                    # Show snapshot timestamp info
                    if 'greeks.updated_at' in df.columns:
                        unique_timestamps = df['greeks.updated_at'].nunique()
                        latest_timestamp = df['greeks.updated_at'].iloc[0] if len(df) > 0 else None
                        logger.info(f"  Unique timestamps in snapshot: {unique_timestamps}")
                        logger.info(f"  Snapshot timestamp: {latest_timestamp}")
                    
                    # Show data with previous comparisons
                    if 'has_previous_data' in df.columns:
                        with_prev_data = df['has_previous_data'].sum()
                        logger.info(f"  Options with previous data: {with_prev_data}/{len(df)}")
                    
                else:
                    logger.warning(f"{filename} was not created")
            
            return True
            
        else:
            logger.error("CSV export failed")
            return False
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def analyze_current_csv():
    """Analyze the current gex.csv file if it exists"""
    
    logger.info("Analyzing current CSV files...")
    
    files_to_analyze = ['gex.csv', 'gex_summary.csv']
    
    for filename in files_to_analyze:
        if os.path.exists(filename):
            logger.info(f"\nAnalyzing {filename}:")
            
            df = pd.read_csv(filename)
            
            # Basic info
            logger.info(f"  Shape: {df.shape}")
            logger.info(f"  Memory usage: {df.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB")
            
            # Column analysis
            total_cols = len(df.columns)
            greek_cols = len([col for col in df.columns if col.startswith('greeks.')])
            diff_cols = len([col for col in df.columns if col.endswith('_diff')])
            pct_cols = len([col for col in df.columns if col.endswith('_pct_change')])
            
            logger.info(f"  Total columns: {total_cols}")
            logger.info(f"  Greek columns: {greek_cols}")
            logger.info(f"  Difference columns: {diff_cols}")
            logger.info(f"  Percentage change columns: {pct_cols}")
            
            # Timestamp analysis
            if 'greeks.updated_at' in df.columns:
                timestamps = df['greeks.updated_at'].unique()
                logger.info(f"  Unique timestamps: {len(timestamps)}")
                if len(timestamps) > 0:
                    logger.info(f"  Latest timestamp: {timestamps[0] if len(timestamps) == 1 else 'Multiple timestamps found'}")
            
            # Data completeness
            if 'has_previous_data' in df.columns:
                with_prev = df['has_previous_data'].sum()
                logger.info(f"  Records with previous data: {with_prev} ({with_prev/len(df)*100:.1f}%)")
            
            # Sample of key columns
            key_cols = ['option_type', 'strike', 'expiration_date', 'gex']
            if 'gex_diff' in df.columns:
                key_cols.append('gex_diff')
            if 'gex_pct_change' in df.columns:
                key_cols.append('gex_pct_change')
            
            available_key_cols = [col for col in key_cols if col in df.columns]
            if available_key_cols and len(df) > 0:
                sample = df[available_key_cols].head(3)
                logger.info(f"  Sample data:")
                for idx, row in sample.iterrows():
                    logger.info(f"    {dict(row)}")
                    
        else:
            logger.info(f"{filename} does not exist")

def verify_snapshot_behavior():
    """Verify that the CSV contains only the latest snapshot"""
    
    logger.info("\nVerifying snapshot behavior...")
    
    try:
        # Check database for multiple timestamps
        conn = sqlite3.connect('gex_data.db')
        
        timestamp_query = """
        SELECT [greeks.updated_at], COUNT(*) as record_count
        FROM gex_table
        GROUP BY [greeks.updated_at]
        ORDER BY [greeks.updated_at] DESC
        LIMIT 5
        """
        
        timestamps_df = pd.read_sql(timestamp_query, conn)
        conn.close()
        
        logger.info("Recent timestamps in database:")
        for idx, row in timestamps_df.iterrows():
            logger.info(f"  {row['greeks.updated_at']}: {row['record_count']} records")
        
        # Check CSV timestamp consistency
        if os.path.exists('gex.csv'):
            csv_df = pd.read_csv('gex.csv')
            if 'greeks.updated_at' in csv_df.columns:
                csv_timestamps = csv_df['greeks.updated_at'].unique()
                logger.info(f"CSV contains {len(csv_timestamps)} unique timestamps")
                if len(csv_timestamps) == 1:
                    logger.info(f"✓ CSV is a proper snapshot from: {csv_timestamps[0]}")
                else:
                    logger.warning(f"⚠ CSV contains multiple timestamps: {csv_timestamps}")
        
    except Exception as e:
        logger.error(f"Error verifying snapshot behavior: {e}")

if __name__ == "__main__":
    print("Testing CSV export functionality...\n")
    
    # First analyze current state
    analyze_current_csv()
    
    print("\n" + "="*50)
    
    # Verify snapshot behavior
    verify_snapshot_behavior()
    
    print("\n" + "="*50)
    
    # Test the export function
    try:
        success = test_csv_export()
        if success:
            print("\n✅ CSV export test completed successfully!")
            print("\nRe-analyzing exported files:")
            analyze_current_csv()
        else:
            print("\n❌ CSV export test failed!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")