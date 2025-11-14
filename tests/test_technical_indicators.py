#!/usr/bin/env python3
"""
Test Technical Indicators functionality

This script tests the SPX technical indicators including EMAs
and relative positioning calculations.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
import logging

from src.indicators.technical_indicators import TechnicalIndicators, SPXIndicatorCalculator
import sys; import os; sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); from src.api.tradier_api import TradierAPI
from src.config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_ema_calculations():
    """Test basic EMA calculations"""
    logger.info("Testing EMA calculations...")
    
    # Create test data
    test_prices = pd.Series([100, 102, 101, 105, 107, 104, 108, 110, 109, 112, 115, 113, 118, 120, 119])
    
    indicators = TechnicalIndicators()
    
    # Test 8-period EMA
    ema_8 = indicators.calculate_ema(test_prices, 8)
    logger.info(f"EMA 8 calculation: {len(ema_8)} values")
    logger.info(f"Latest EMA 8 value: {ema_8.iloc[-1]:.2f}")
    
    # Test 21-period EMA (should have NaN for early values)
    ema_21 = indicators.calculate_ema(test_prices, 21)
    logger.info(f"EMA 21 calculation: {len(ema_21)} values")
    logger.info(f"Latest EMA 21 value: {ema_21.iloc[-1]:.2f}")
    
    # Test relative position
    current_price = 120.0
    ema_8_current = ema_8.iloc[-1]
    
    relative_pos = indicators.get_relative_position(current_price, ema_8_current)
    logger.info(f"Relative position vs EMA 8:")
    logger.info(f"  Absolute diff: {relative_pos['absolute_diff']:.2f}")
    logger.info(f"  Percentage diff: {relative_pos['percentage_diff']:.2f}%")
    logger.info(f"  Above EMA: {bool(relative_pos['position'])}")
    
    # Test EMA trend
    trend = indicators.calculate_ema_trend(ema_8, ema_21)
    logger.info(f"EMA Trend:")
    logger.info(f"  Bullish: {bool(trend['trend'])}")
    logger.info(f"  Strength: {trend['trend_strength']:.2f}%")
    
    return True

def test_spx_indicator_calculator():
    """Test SPX indicator calculator with real API data"""
    logger.info("Testing SPX indicator calculator...")
    
    try:
        # Set up API client
        os.environ['TRADIER_API_KEY'] = 'xfiiBZaKv6Z68ossl3VjtjWL0Tsc'
        os.environ['TRADIER_ACCOUNT_ID'] = '6YB53834'
        
        config = Config()
        api = TradierAPI(config.tradier_api_key)
        calculator = SPXIndicatorCalculator(api)
        
        # Test 30-minute data retrieval
        logger.info("Testing 30-minute data retrieval...")
        df_30min = calculator.get_spx_30min_data(days_back=5)
        
        if df_30min.empty:
            logger.warning("No 30-minute data received - may be outside market hours")
            logger.info("Testing with simulated current price...")
            current_price = 6870.0  # Use a reasonable test price
        else:
            logger.info(f"Retrieved {len(df_30min)} 30-minute bars")
            logger.info(f"Date range: {df_30min['datetime'].min()} to {df_30min['datetime'].max()}")
            logger.info(f"Price range: ${df_30min['close'].min():.2f} - ${df_30min['close'].max():.2f}")
            
            # Use latest close as current price for testing
            current_price = df_30min['close'].iloc[-1]
        
        # Calculate all indicators
        logger.info(f"Calculating indicators for SPX price: ${current_price:.2f}")
        indicators = calculator.calculate_spx_indicators(current_price)
        
        # Display results
        logger.info("SPX Indicator Results:")
        for key, value in indicators.items():
            if isinstance(value, (int, float)) and not pd.isna(value):
                if 'pct' in key or 'percentage' in key:
                    logger.info(f"  {key}: {value:.2f}%")
                elif 'price' in key or 'ema' in key:
                    logger.info(f"  {key}: ${value:.2f}")
                elif 'above' in key or 'bullish' in key:
                    logger.info(f"  {key}: {bool(value)}")
                else:
                    logger.info(f"  {key}: {value:.4f}")
            else:
                logger.info(f"  {key}: {value}")
        
        # Test saving to CSV
        logger.info("Testing CSV save...")
        save_success = calculator.save_indicators_to_csv(indicators)
        
        if save_success and os.path.exists('spx_indicators.csv'):
            df = pd.read_csv('spx_indicators.csv')
            logger.info(f"Indicators CSV: {len(df)} records, {len(df.columns)} columns")
            
            # Show sample columns
            indicator_cols = [col for col in df.columns if 'spx_' in col]
            logger.info(f"Sample indicator columns: {indicator_cols[:5]}")
        
        return True
        
    except Exception as e:
        logger.error(f"SPX indicator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration_with_gex_collector():
    """Test integration with the main GEX collector"""
    logger.info("Testing integration with GEX collector...")
    
    try:
        from src.gex_collector import GEXCollector
        
        # Set up config
        os.environ['TRADIER_API_KEY'] = 'xfiiBZaKv6Z68ossl3VjtjWL0Tsc'
        os.environ['TRADIER_ACCOUNT_ID'] = '6YB53834'
        
        config = Config()
        collector = GEXCollector(config)
        
        # Test getting SPX price and indicators
        logger.info("Testing SPX price and indicator collection...")
        spx_price_data = collector.get_current_spx_price()
        
        if spx_price_data:
            logger.info(f"Got SPX price: ${spx_price_data['last']:.2f}")
            
            # Calculate indicators
            spx_indicators = collector.indicator_calculator.calculate_spx_indicators(spx_price_data['last'])
            collector.current_spx_indicators = spx_indicators
            
            # Test CSV export with indicators
            export_success = collector.export_to_csv()
            
            if export_success:
                logger.info("CSV export with indicators completed successfully")
                
                # Check if indicator columns are in the CSV
                if os.path.exists('gex.csv'):
                    df = pd.read_csv('gex.csv')
                    
                    # Look for EMA and positioning columns
                    ema_columns = [col for col in df.columns if 'ema' in col]
                    position_columns = [col for col in df.columns if 'above' in col or 'vs_' in col]
                    trend_columns = [col for col in df.columns if 'trend' in col]
                    
                    logger.info(f"EMA columns in CSV: {len(ema_columns)}")
                    logger.info(f"Position columns in CSV: {len(position_columns)}")
                    logger.info(f"Trend columns in CSV: {len(trend_columns)}")
                    
                    if ema_columns:
                        logger.info(f"Sample EMA columns: {ema_columns[:3]}")
                    
                    # Show sample values
                    if 'spx_ema_8_current' in df.columns and len(df) > 0:
                        ema_8_val = df['spx_ema_8_current'].iloc[0]
                        logger.info(f"Sample EMA 8 value in CSV: ${ema_8_val:.2f}")
                    
                    if 'spx_above_ema8' in df.columns and len(df) > 0:
                        above_ema8 = df['spx_above_ema8'].iloc[0]
                        logger.info(f"SPX above EMA 8: {bool(above_ema8)}")
                
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

def analyze_indicators_csv():
    """Analyze the indicators CSV file"""
    logger.info("Analyzing indicators CSV file...")
    
    indicators_file = 'spx_indicators.csv'
    
    if os.path.exists(indicators_file):
        df = pd.read_csv(indicators_file)
        
        logger.info(f"Indicators CSV Analysis:")
        logger.info(f"  Records: {len(df)}")
        logger.info(f"  Columns: {len(df.columns)}")
        
        # Show key indicator columns
        key_indicators = [
            'spx_current_price', 'spx_ema_8_current', 'spx_ema_21_current',
            'spx_above_ema8', 'spx_above_ema21', 'spx_ema_trend_bullish'
        ]
        
        available_indicators = [col for col in key_indicators if col in df.columns]
        logger.info(f"  Key indicators available: {available_indicators}")
        
        if len(df) > 0:
            latest = df.iloc[-1]
            logger.info(f"Latest indicator values:")
            
            for indicator in available_indicators:
                value = latest[indicator]
                if pd.isna(value):
                    logger.info(f"    {indicator}: N/A")
                elif 'price' in indicator or 'ema' in indicator:
                    logger.info(f"    {indicator}: ${value:.2f}")
                elif 'above' in indicator or 'bullish' in indicator:
                    logger.info(f"    {indicator}: {bool(value)}")
                else:
                    logger.info(f"    {indicator}: {value:.4f}")
    else:
        logger.info(f"{indicators_file} does not exist yet")

if __name__ == "__main__":
    print("Testing Technical Indicators functionality...\n")
    
    # Test basic EMA calculations
    try:
        success1 = test_ema_calculations()
        print(f"\nEMA Calculations Test: {'PASSED' if success1 else 'FAILED'}")
    except Exception as e:
        print(f"\nEMA Calculations Test: FAILED - {e}")
        success1 = False
    
    print("\n" + "="*50)
    
    # Test SPX indicator calculator
    try:
        success2 = test_spx_indicator_calculator()
        print(f"\nSPX Indicator Calculator Test: {'PASSED' if success2 else 'FAILED'}")
    except Exception as e:
        print(f"\nSPX Indicator Calculator Test: FAILED - {e}")
        success2 = False
    
    print("\n" + "="*50)
    
    # Test integration
    try:
        success3 = test_integration_with_gex_collector()
        print(f"\nGEX Collector Integration Test: {'PASSED' if success3 else 'FAILED'}")
    except Exception as e:
        print(f"\nGEX Collector Integration Test: FAILED - {e}")
        success3 = False
    
    print("\n" + "="*50)
    
    # Analyze results
    print("\nFinal Analysis:")
    analyze_indicators_csv()
    
    if success1 and success2 and success3:
        print("\n✓ All technical indicator tests passed!")
    else:
        print("\n✗ Some tests failed - check logs for details")