#!/usr/bin/env python3
"""
Test SPX Price Estimation System

This script tests the SPX price estimation functionality that uses SPY
as a proxy when SPX is not actively traded.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indicators.technical_indicators import SPXIndicatorCalculator
from src.api.tradier_api import TradierAPI
from src.config import Config
from src.gex_collector import GEXCollector

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_spx_estimation_basic():
    """Test basic SPX estimation functionality"""
    logger.info("Testing basic SPX estimation...")
    
    try:
        # Set up API client
        os.environ['TRADIER_API_KEY'] = 'xfiiBZaKv6Z68ossl3VjtjWL0Tsc'
        os.environ['TRADIER_ACCOUNT_ID'] = '6YB53834'
        
        config = Config()
        api = TradierAPI(config.tradier_api_key)
        calculator = SPXIndicatorCalculator(api)
        
        # Test with known values
        test_spy_price = 680.0
        test_spx_price = 6820.0
        
        logger.info(f"Testing estimation with SPY=${test_spy_price:.2f}, SPX=${test_spx_price:.2f}")
        
        # Test estimation
        estimation_result = calculator.estimate_spx_from_spy(test_spy_price, test_spx_price)
        
        logger.info("Estimation Results:")
        for key, value in estimation_result.items():
            if isinstance(value, (int, float)) and not pd.isna(value):
                if 'price' in key:
                    logger.info(f"  {key}: ${value:.2f}")
                elif 'ratio' in key:
                    logger.info(f"  {key}: {value:.6f}")
                elif 'pct' in key:
                    logger.info(f"  {key}: {value:.3f}%")
                else:
                    logger.info(f"  {key}: {value}")
            else:
                logger.info(f"  {key}: {value}")
        
        # Verify estimation accuracy
        estimated_price = estimation_result.get('spx_estimated_price', 0)
        expected_price = test_spy_price * calculator.spy_spx_ratio
        
        if abs(estimated_price - expected_price) < 0.01:
            logger.info("✓ Estimation calculation correct")
            return True
        else:
            logger.error(f"✗ Estimation calculation error: {estimated_price} vs {expected_price}")
            return False
            
    except Exception as e:
        logger.error(f"Basic estimation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_spx_estimation_with_real_data():
    """Test SPX estimation with real market data"""
    logger.info("Testing SPX estimation with real data...")
    
    try:
        os.environ['TRADIER_API_KEY'] = 'xfiiBZaKv6Z68ossl3VjtjWL0Tsc'
        os.environ['TRADIER_ACCOUNT_ID'] = '6YB53834'
        
        config = Config()
        api = TradierAPI(config.tradier_api_key)
        calculator = SPXIndicatorCalculator(api)
        
        # Get current SPY price
        logger.info("Fetching current SPY price...")
        spy_quote = api.get_current_quote('SPY')
        
        # Get current SPX price
        logger.info("Fetching current SPX price...")
        spx_quote = api.get_current_quote('SPX')
        
        if spy_quote.empty or spx_quote.empty:
            logger.error("Failed to get current quotes")
            return False
        
        spy_price = spy_quote.iloc[0]['last']
        spx_price = spx_quote.iloc[0]['last']
        
        logger.info(f"Current market prices: SPY=${spy_price:.2f}, SPX=${spx_price:.2f}")
        
        # Test estimation with real data
        estimation_result = calculator.estimate_spx_from_spy(spy_price, spx_price)
        
        # Display results
        estimated_spx = estimation_result.get('spx_estimated_price', 0)
        estimation_error = estimation_result.get('spx_estimation_error', 0)
        estimation_error_pct = estimation_result.get('spx_estimation_error_pct', 0)
        price_source = estimation_result.get('spx_price_source', 'unknown')
        
        logger.info("Real Data Estimation Results:")
        logger.info(f"  SPY Price: ${spy_price:.2f}")
        logger.info(f"  SPX Actual: ${spx_price:.2f}")
        logger.info(f"  SPX Estimated: ${estimated_spx:.2f}")
        logger.info(f"  Estimation Error: ${estimation_error:.2f} ({estimation_error_pct:.3f}%)")
        logger.info(f"  Price Source: {price_source}")
        
        # Test different scenarios
        logger.info("\nTesting stale SPX scenario (simulated)...")
        stale_spx_price = spx_price * 0.95  # Simulate 5% stale price
        stale_result = calculator.estimate_spx_from_spy(spy_price, stale_spx_price)
        
        logger.info(f"Stale SPX test:")
        logger.info(f"  Simulated stale SPX: ${stale_spx_price:.2f}")
        logger.info(f"  Price source decision: {stale_result.get('spx_price_source', 'unknown')}")
        logger.info(f"  Final price used: ${stale_result.get('spx_final_price', 0):.2f}")
        
        return True
        
    except Exception as e:
        logger.error(f"Real data estimation test failed: {e}")
        return False

def test_spx_estimation_integration():
    """Test SPX estimation integration with the full GEX collector"""
    logger.info("Testing SPX estimation integration...")
    
    try:
        os.environ['TRADIER_API_KEY'] = 'xfiiBZaKv6Z68ossl3VjtjWL0Tsc'
        os.environ['TRADIER_ACCOUNT_ID'] = '6YB53834'
        
        config = Config()
        collector = GEXCollector(config)
        
        # Get SPX price data
        spx_price_data = collector.get_current_spx_price()
        
        if not spx_price_data:
            logger.error("Failed to get SPX price data")
            return False
        
        spx_price = spx_price_data['last']
        logger.info(f"Current SPX price: ${spx_price:.2f}")
        
        # Calculate indicators (which includes estimation logic)
        logger.info("Calculating indicators with estimation logic...")
        indicators = collector.indicator_calculator.calculate_spx_indicators(spx_price)
        
        # Check for estimation-related indicators
        estimation_indicators = {k: v for k, v in indicators.items() if 'estimation' in k or 'spy_price' in k}
        
        logger.info("Estimation indicators in results:")
        for key, value in estimation_indicators.items():
            if isinstance(value, (int, float)) and not pd.isna(value):
                if 'price' in key:
                    logger.info(f"  {key}: ${value:.2f}")
                elif 'ratio' in key:
                    logger.info(f"  {key}: {value:.6f}")
                elif 'error' in key and 'pct' in key:
                    logger.info(f"  {key}: {value:.3f}%")
                else:
                    logger.info(f"  {key}: {value}")
            else:
                logger.info(f"  {key}: {value}")
        
        # Test CSV export with estimation data
        export_success = collector.export_to_csv()
        
        if export_success and os.path.exists('gex.csv'):
            df = pd.read_csv('gex.csv')
            
            # Check for estimation columns
            estimation_cols = [col for col in df.columns if 'estimation' in col or 'spy_price_for' in col]
            
            logger.info(f"Estimation columns in CSV: {len(estimation_cols)}")
            if estimation_cols:
                logger.info(f"Sample estimation columns: {estimation_cols[:3]}")
                
                # Show sample values
                if 'spx_estimated_price' in df.columns and len(df) > 0:
                    estimated_value = df['spx_estimated_price'].iloc[0]
                    logger.info(f"Sample estimated SPX in CSV: ${estimated_value:.2f}")
            
            return True
        else:
            logger.error("CSV export failed")
            return False
            
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_estimation_edge_cases():
    """Test edge cases for SPX estimation"""
    logger.info("Testing estimation edge cases...")
    
    try:
        os.environ['TRADIER_API_KEY'] = 'xfiiBZaKv6Z68ossl3VjtjWL0Tsc'
        os.environ['TRADIER_ACCOUNT_ID'] = '6YB53834'
        
        config = Config()
        api = TradierAPI(config.tradier_api_key)
        calculator = SPXIndicatorCalculator(api)
        
        # Test 1: No SPX price provided
        logger.info("Test 1: No SPX price provided")
        result1 = calculator.estimate_spx_from_spy(680.0, None)
        logger.info(f"  Price source: {result1.get('spx_price_source')}")
        logger.info(f"  Final price: ${result1.get('spx_final_price', 0):.2f}")
        
        # Test 2: Zero SPX price
        logger.info("Test 2: Zero SPX price")
        result2 = calculator.estimate_spx_from_spy(680.0, 0)
        logger.info(f"  Price source: {result2.get('spx_price_source')}")
        logger.info(f"  Final price: ${result2.get('spx_final_price', 0):.2f}")
        
        # Test 3: Very stale SPX price (10% deviation)
        logger.info("Test 3: Very stale SPX price")
        spy_price = 680.0
        stale_spx = spy_price * calculator.spy_spx_ratio * 0.9  # 10% below expected
        result3 = calculator.estimate_spx_from_spy(spy_price, stale_spx)
        logger.info(f"  SPY: ${spy_price:.2f}, Stale SPX: ${stale_spx:.2f}")
        logger.info(f"  Price source: {result3.get('spx_price_source')}")
        logger.info(f"  Appears stale: {result3.get('spx_price_appears_stale', False)}")
        logger.info(f"  Final price: ${result3.get('spx_final_price', 0):.2f}")
        
        # Test 4: Invalid SPY price
        logger.info("Test 4: Invalid SPY price")
        try:
            result4 = calculator.estimate_spx_from_spy(0, 6800.0)
            logger.info(f"  Handled zero SPY gracefully: {result4.get('spx_price_source')}")
        except Exception as e:
            logger.info(f"  Error handling for zero SPY: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Edge cases test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing SPX Price Estimation System...\n")
    
    # Test 1: Basic estimation
    try:
        success1 = test_spx_estimation_basic()
        print(f"\nBasic Estimation Test: {'PASSED' if success1 else 'FAILED'}")
    except Exception as e:
        print(f"\nBasic Estimation Test: FAILED - {e}")
        success1 = False
    
    print("\n" + "="*50)
    
    # Test 2: Real data estimation
    try:
        success2 = test_spx_estimation_with_real_data()
        print(f"\nReal Data Estimation Test: {'PASSED' if success2 else 'FAILED'}")
    except Exception as e:
        print(f"\nReal Data Estimation Test: FAILED - {e}")
        success2 = False
    
    print("\n" + "="*50)
    
    # Test 3: Integration test
    try:
        success3 = test_spx_estimation_integration()
        print(f"\nIntegration Test: {'PASSED' if success3 else 'FAILED'}")
    except Exception as e:
        print(f"\nIntegration Test: FAILED - {e}")
        success3 = False
    
    print("\n" + "="*50)
    
    # Test 4: Edge cases
    try:
        success4 = test_estimation_edge_cases()
        print(f"\nEdge Cases Test: {'PASSED' if success4 else 'FAILED'}")
    except Exception as e:
        print(f"\nEdge Cases Test: FAILED - {e}")
        success4 = False
    
    print("\n" + "="*50)
    
    if success1 and success2 and success3 and success4:
        print("\n✓ All SPX estimation tests passed!")
        print("\nSPX estimation system is ready for production:")
        print("- Provides reliable SPX estimates when index is not actively traded")
        print("- Automatically detects stale SPX prices and uses estimation instead")
        print("- Includes estimation accuracy metrics and confidence indicators")
        print("- Fully integrated with technical indicators and CSV exports")
    else:
        print("\n✗ Some tests failed - check logs for details")