#!/usr/bin/env python3
"""
Test SPY-SPX Price Relationship

This script analyzes the relationship between SPY and SPX prices
to create an accurate conversion formula for price estimation.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import logging

import sys; import os; sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); from src.api.tradier_api import TradierAPI
from src.config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def analyze_spy_spx_relationship():
    """Analyze the historical relationship between SPY and SPX prices"""
    logger.info("Analyzing SPY-SPX price relationship...")
    
    try:
        # Set up API client
        os.environ['TRADIER_API_KEY'] = 'xfiiBZaKv6Z68ossl3VjtjWL0Tsc'
        os.environ['TRADIER_ACCOUNT_ID'] = '6YB53834'
        
        config = Config()
        api = TradierAPI(config.tradier_api_key)
        
        # Get historical data for both SPY and SPX
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
        
        logger.info(f"Fetching historical data from {start_date} to {end_date}")
        
        # Get SPY historical data
        logger.info("Fetching SPY historical data...")
        spy_data = api.get_historical_quotes(['SPY'], start_date, end_date, 'daily')
        
        # Get SPX historical data
        logger.info("Fetching SPX historical data...")
        spx_data = api.get_historical_quotes(['SPX'], start_date, end_date, 'daily')
        
        if spy_data.empty or spx_data.empty:
            logger.error("Failed to retrieve historical data")
            return None
        
        logger.info(f"SPY data: {len(spy_data)} records")
        logger.info(f"SPX data: {len(spx_data)} records")
        
        # Merge data on date
        spy_data = spy_data[['date', 'close']].rename(columns={'close': 'spy_close'})
        spx_data = spx_data[['date', 'close']].rename(columns={'close': 'spx_close'})
        
        merged_data = pd.merge(spy_data, spx_data, on='date', how='inner')
        
        if merged_data.empty:
            logger.error("No matching dates between SPY and SPX data")
            return None
        
        logger.info(f"Merged data: {len(merged_data)} matching records")
        
        # Calculate the SPX/SPY ratio
        merged_data['spx_spy_ratio'] = merged_data['spx_close'] / merged_data['spy_close']
        
        # Calculate statistics
        ratio_mean = merged_data['spx_spy_ratio'].mean()
        ratio_std = merged_data['spx_spy_ratio'].std()
        ratio_min = merged_data['spx_spy_ratio'].min()
        ratio_max = merged_data['spx_spy_ratio'].max()
        ratio_current = merged_data['spx_spy_ratio'].iloc[-1]
        
        logger.info("SPX/SPY Ratio Analysis:")
        logger.info(f"  Mean ratio: {ratio_mean:.6f}")
        logger.info(f"  Std deviation: {ratio_std:.6f}")
        logger.info(f"  Min ratio: {ratio_min:.6f}")
        logger.info(f"  Max ratio: {ratio_max:.6f}")
        logger.info(f"  Current ratio: {ratio_current:.6f}")
        logger.info(f"  Stability: {(ratio_std/ratio_mean)*100:.4f}% coefficient of variation")
        
        # Show recent price pairs
        logger.info("Recent SPY-SPX Price Pairs:")
        recent_data = merged_data.tail(5)
        for idx, row in recent_data.iterrows():
            logger.info(f"  {row['date']}: SPY ${row['spy_close']:.2f} → SPX ${row['spx_close']:.2f} (ratio: {row['spx_spy_ratio']:.6f})")
        
        # Test estimation accuracy
        logger.info("Testing estimation accuracy on recent data:")
        for idx, row in recent_data.iterrows():
            estimated_spx = row['spy_close'] * ratio_mean
            actual_spx = row['spx_close']
            error = abs(estimated_spx - actual_spx)
            error_pct = (error / actual_spx) * 100
            
            logger.info(f"  {row['date']}: Est ${estimated_spx:.2f} vs Act ${actual_spx:.2f} "
                       f"(Error: ${error:.2f}, {error_pct:.3f}%)")
        
        return {
            'ratio_mean': ratio_mean,
            'ratio_std': ratio_std,
            'ratio_current': ratio_current,
            'data_points': len(merged_data),
            'merged_data': merged_data
        }
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_current_prices():
    """Test current SPY and SPX prices to validate relationship"""
    logger.info("Testing current SPY-SPX price relationship...")
    
    try:
        os.environ['TRADIER_API_KEY'] = 'xfiiBZaKv6Z68ossl3VjtjWL0Tsc'
        os.environ['TRADIER_ACCOUNT_ID'] = '6YB53834'
        
        config = Config()
        api = TradierAPI(config.tradier_api_key)
        
        # Get current prices
        logger.info("Fetching current SPY price...")
        spy_quote = api.get_current_quote('SPY')
        
        logger.info("Fetching current SPX price...")
        spx_quote = api.get_current_quote('SPX')
        
        if spy_quote.empty or spx_quote.empty:
            logger.error("Failed to get current quotes")
            return None
        
        spy_price = spy_quote.iloc[0]['last']
        spx_price = spx_quote.iloc[0]['last']
        current_ratio = spx_price / spy_price
        
        logger.info("Current Price Comparison:")
        logger.info(f"  SPY: ${spy_price:.2f}")
        logger.info(f"  SPX: ${spx_price:.2f}")
        logger.info(f"  Current ratio: {current_ratio:.6f}")
        
        return {
            'spy_price': spy_price,
            'spx_price': spx_price,
            'current_ratio': current_ratio
        }
        
    except Exception as e:
        logger.error(f"Current price test failed: {e}")
        return None

def test_intraday_relationship():
    """Test SPY-SPX relationship using intraday data"""
    logger.info("Testing intraday SPY-SPX relationship...")
    
    try:
        os.environ['TRADIER_API_KEY'] = 'xfiiBZaKv6Z68ossl3VjtjWL0Tsc'
        os.environ['TRADIER_ACCOUNT_ID'] = '6YB53834'
        
        config = Config()
        api = TradierAPI(config.tradier_api_key)
        
        # Get 30-minute intraday data for both
        logger.info("Fetching SPY 30-minute data...")
        spy_intraday = api.get_intraday_data('SPY', interval='30min', days_back=2)
        
        logger.info("Fetching SPX 30-minute data...")
        spx_intraday = api.get_intraday_data('SPX', interval='30min', days_back=2)
        
        if spy_intraday.empty or spx_intraday.empty:
            logger.warning("Limited intraday data available")
            return None
        
        logger.info(f"SPY intraday: {len(spy_intraday)} bars")
        logger.info(f"SPX intraday: {len(spx_intraday)} bars")
        
        # Merge on datetime
        spy_intraday = spy_intraday[['datetime', 'close']].rename(columns={'close': 'spy_close'})
        spx_intraday = spx_intraday[['datetime', 'close']].rename(columns={'close': 'spx_close'})
        
        merged_intraday = pd.merge(spy_intraday, spx_intraday, on='datetime', how='inner')
        
        if merged_intraday.empty:
            logger.warning("No matching intraday timestamps")
            return None
        
        logger.info(f"Merged intraday: {len(merged_intraday)} matching bars")
        
        # Calculate intraday ratios
        merged_intraday['spx_spy_ratio'] = merged_intraday['spx_close'] / merged_intraday['spy_close']
        
        ratio_mean = merged_intraday['spx_spy_ratio'].mean()
        ratio_std = merged_intraday['spx_spy_ratio'].std()
        
        logger.info("Intraday SPX/SPY Ratio Analysis:")
        logger.info(f"  Mean ratio: {ratio_mean:.6f}")
        logger.info(f"  Std deviation: {ratio_std:.6f}")
        logger.info(f"  Intraday stability: {(ratio_std/ratio_mean)*100:.4f}% coefficient of variation")
        
        # Show recent intraday ratios
        recent_intraday = merged_intraday.tail(3)
        logger.info("Recent intraday ratios:")
        for idx, row in recent_intraday.iterrows():
            logger.info(f"  {row['datetime']}: {row['spx_spy_ratio']:.6f}")
        
        return {
            'intraday_ratio_mean': ratio_mean,
            'intraday_ratio_std': ratio_std,
            'intraday_data_points': len(merged_intraday)
        }
        
    except Exception as e:
        logger.error(f"Intraday relationship test failed: {e}")
        return None

if __name__ == "__main__":
    print("Testing SPY-SPX Price Relationship...\n")
    
    # Test 1: Historical relationship analysis
    try:
        historical_results = analyze_spy_spx_relationship()
        if historical_results:
            print(f"\nHistorical Analysis: SUCCESS")
            print(f"  Average SPX/SPY ratio: {historical_results['ratio_mean']:.6f}")
            print(f"  Ratio stability: {(historical_results['ratio_std']/historical_results['ratio_mean'])*100:.4f}%")
        else:
            print("\nHistorical Analysis: FAILED")
    except Exception as e:
        print(f"\nHistorical Analysis: FAILED - {e}")
        historical_results = None
    
    print("\n" + "="*50)
    
    # Test 2: Current price relationship
    try:
        current_results = test_current_prices()
        if current_results:
            print(f"\nCurrent Price Test: SUCCESS")
            print(f"  SPY: ${current_results['spy_price']:.2f}")
            print(f"  SPX: ${current_results['spx_price']:.2f}")
            print(f"  Current ratio: {current_results['current_ratio']:.6f}")
        else:
            print("\nCurrent Price Test: FAILED")
    except Exception as e:
        print(f"\nCurrent Price Test: FAILED - {e}")
        current_results = None
    
    print("\n" + "="*50)
    
    # Test 3: Intraday relationship
    try:
        intraday_results = test_intraday_relationship()
        if intraday_results:
            print(f"\nIntraday Analysis: SUCCESS")
            print(f"  Intraday ratio: {intraday_results['intraday_ratio_mean']:.6f}")
        else:
            print("\nIntraday Analysis: LIMITED DATA")
    except Exception as e:
        print(f"\nIntraday Analysis: FAILED - {e}")
        intraday_results = None
    
    # Summary and recommendation
    print("\n" + "="*50)
    if historical_results:
        ratio = historical_results['ratio_mean']
        stability = (historical_results['ratio_std']/historical_results['ratio_mean'])*100
        
        print(f"\nRecommended SPX Estimation Formula:")
        print(f"  SPX_estimated = SPY_price × {ratio:.6f}")
        print(f"  Expected accuracy: ±{stability:.3f}%")
        
        if current_results:
            estimated_spx = current_results['spy_price'] * ratio
            actual_spx = current_results['spx_price']
            error = abs(estimated_spx - actual_spx)
            error_pct = (error / actual_spx) * 100
            
            print(f"\nCurrent Estimation Test:")
            print(f"  Estimated SPX: ${estimated_spx:.2f}")
            print(f"  Actual SPX: ${actual_spx:.2f}")
            print(f"  Error: ${error:.2f} ({error_pct:.3f}%)")
    else:
        print("\nInsufficient data for SPX estimation formula")