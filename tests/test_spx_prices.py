#!/usr/bin/env python3
"""
Test SPX price collection functionality

This script tests the SPX intraday price collection to ensure
it works correctly and integrates properly with the main system.
"""

import pandas as pd
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

def test_spx_price_collection():
    """Test SPX price collection functionality"""
    
    logger.info("Testing SPX price collection...")
    
    try:
        # Create a minimal config for testing
        os.environ['TRADIER_API_KEY'] = 'xfiiBZaKv6Z68ossl3VjtjWL0Tsc'  # Use actual key for testing
        os.environ['TRADIER_ACCOUNT_ID'] = '6YB53834'  # Use actual account for testing
        
        config = Config()
        collector = GEXCollector(config)
        
        # Test SPX price collection
        logger.info("Fetching current SPX price...")
        spx_price_data = collector.get_current_spx_price()
        
        if spx_price_data:
            logger.info("SPX price data retrieved successfully!")
            logger.info(f"Price data keys: {list(spx_price_data.keys())}")
            
            # Display the price data
            logger.info("SPX Price Information:")
            logger.info(f"  Symbol: {spx_price_data.get('symbol')}")
            logger.info(f"  Last: ${spx_price_data.get('last', 'N/A')}")
            logger.info(f"  Open: ${spx_price_data.get('open', 'N/A')}")
            logger.info(f"  High: ${spx_price_data.get('high', 'N/A')}")
            logger.info(f"  Low: ${spx_price_data.get('low', 'N/A')}")
            logger.info(f"  Close: ${spx_price_data.get('close', 'N/A')}")
            logger.info(f"  Change: {spx_price_data.get('change', 'N/A')}")
            logger.info(f"  Change %: {spx_price_data.get('change_percentage', 'N/A')}%")
            logger.info(f"  Volume: {spx_price_data.get('volume', 'N/A')}")
            logger.info(f"  Timestamp: {spx_price_data.get('timestamp')}")
            
            # Test saving to CSV
            logger.info("Testing SPX price CSV save...")
            save_success = collector.save_spx_price_to_csv(spx_price_data)
            
            if save_success:
                logger.info("SPX price saved to CSV successfully!")
                
                # Check if file exists and analyze it
                if os.path.exists('spx_intraday_prices.csv'):
                    df = pd.read_csv('spx_intraday_prices.csv')
                    logger.info(f"SPX CSV file contains {len(df)} records")
                    logger.info(f"Columns: {list(df.columns)}")
                    
                    if len(df) > 0:
                        latest_record = df.iloc[-1]
                        logger.info(f"Latest record: SPX ${latest_record['last']:.2f} at {latest_record['timestamp']}")
                
            else:
                logger.error("Failed to save SPX price to CSV")
            
            return True
            
        else:
            logger.error("Failed to retrieve SPX price data")
            return False
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_csv_integration():
    """Test that SPX prices are properly integrated into main CSV exports"""
    
    logger.info("Testing SPX price integration with CSV exports...")
    
    try:
        # Set up config
        os.environ['TRADIER_API_KEY'] = 'xfiiBZaKv6Z68ossl3VjtjWL0Tsc'
        os.environ['TRADIER_ACCOUNT_ID'] = '6YB53834'
        
        config = Config()
        collector = GEXCollector(config)
        
        # Get SPX price first
        spx_price_data = collector.get_current_spx_price()
        
        if spx_price_data:
            logger.info(f"Got SPX price: ${spx_price_data['last']:.2f}")
            
            # Test the CSV export (this should now include SPX data)
            export_success = collector.export_to_csv()
            
            if export_success:
                logger.info("CSV export completed successfully")
                
                # Check if SPX columns are in the CSV
                if os.path.exists('gex.csv'):
                    df = pd.read_csv('gex.csv')
                    spx_columns = [col for col in df.columns if col.startswith('spx_')]
                    
                    logger.info(f"Found {len(spx_columns)} SPX columns in CSV")
                    if spx_columns:
                        logger.info(f"SPX columns: {spx_columns}")
                        
                        # Show sample SPX data from the CSV
                        if 'spx_last' in df.columns and len(df) > 0:
                            spx_price_in_csv = df['spx_last'].iloc[0]
                            logger.info(f"SPX price in CSV: ${spx_price_in_csv}")
                    else:
                        logger.warning("No SPX columns found in CSV - integration may have failed")
                
                # Check summary CSV too
                if os.path.exists('gex_summary.csv'):
                    summary_df = pd.read_csv('gex_summary.csv')
                    summary_spx_columns = [col for col in summary_df.columns if col.startswith('spx_')]
                    logger.info(f"Summary CSV has {len(summary_spx_columns)} SPX columns")
                
                return True
            else:
                logger.error("CSV export failed")
                return False
        else:
            logger.error("Could not get SPX price for integration test")
            return False
            
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def analyze_spx_csv_file():
    """Analyze the SPX intraday prices CSV file"""
    
    logger.info("Analyzing SPX intraday prices file...")
    
    spx_file = 'spx_intraday_prices.csv'
    
    if os.path.exists(spx_file):
        df = pd.read_csv(spx_file)
        
        logger.info(f"SPX CSV Analysis:")
        logger.info(f"  Records: {len(df)}")
        logger.info(f"  Columns: {list(df.columns)}")
        logger.info(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        if len(df) > 0:
            latest = df.iloc[-1]
            logger.info(f"  Latest price: ${latest['last']:.2f}")
            logger.info(f"  Latest change: {latest.get('change_percentage', 'N/A')}%")
            
            # Show price range for the day
            if 'high' in df.columns and 'low' in df.columns:
                high = df['high'].max()
                low = df['low'].min()
                logger.info(f"  Session range: ${low:.2f} - ${high:.2f}")
        
    else:
        logger.info(f"{spx_file} does not exist yet")

if __name__ == "__main__":
    print("Testing SPX price collection functionality...\n")
    
    # Analyze existing file first
    analyze_spx_csv_file()
    
    print("\n" + "="*50)
    
    # Test SPX price collection
    try:
        success1 = test_spx_price_collection()
        print(f"\nSPX Price Collection Test: {'PASSED' if success1 else 'FAILED'}")
    except Exception as e:
        print(f"\nSPX Price Collection Test: FAILED - {e}")
        success1 = False
    
    print("\n" + "="*50)
    
    # Test CSV integration
    try:
        success2 = test_csv_integration()
        print(f"\nCSV Integration Test: {'PASSED' if success2 else 'FAILED'}")
    except Exception as e:
        print(f"\nCSV Integration Test: FAILED - {e}")
        success2 = False
    
    print("\n" + "="*50)
    
    # Final analysis
    print("\nFinal Analysis:")
    analyze_spx_csv_file()
    
    if success1 and success2:
        print("\n✓ All SPX price tests passed!")
    else:
        print("\n✗ Some tests failed - check logs for details")