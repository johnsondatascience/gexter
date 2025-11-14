#!/usr/bin/env python3
"""
Test SPX Volume Calculation Methods

This script tests different approaches to calculate or approximate
the volume of stocks traded on the SPX index.
"""

import pandas as pd
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

def test_spy_etf_volume():
    """Test using SPY ETF as a proxy for SPX volume"""
    logger.info("Testing SPY ETF volume as SPX proxy...")
    
    try:
        # Set up API client
        os.environ['TRADIER_API_KEY'] = 'xfiiBZaKv6Z68ossl3VjtjWL0Tsc'
        os.environ['TRADIER_ACCOUNT_ID'] = '6YB53834'
        
        config = Config()
        api = TradierAPI(config.tradier_api_key)
        
        # Test current SPY quote
        logger.info("Getting current SPY quote...")
        spy_quote = api.get_current_quote('SPY')
        
        if not spy_quote.empty:
            spy_data = spy_quote.iloc[0]
            logger.info(f"SPY Current Quote:")
            logger.info(f"  Price: ${spy_data.get('last', 'N/A'):.2f}")
            logger.info(f"  Volume: {spy_data.get('volume', 'N/A'):,}")
            logger.info(f"  Average Volume: {spy_data.get('average_volume', 'N/A'):,}")
            
            # Test SPY intraday data
            logger.info("Getting SPY 30-minute intraday data...")
            spy_intraday = api.get_intraday_data('SPY', interval='30min', days_back=2)
            
            if not spy_intraday.empty:
                logger.info(f"SPY 30-min data: {len(spy_intraday)} bars")
                logger.info(f"Date range: {spy_intraday['datetime'].min()} to {spy_intraday['datetime'].max()}")
                
                # Show recent volume data
                recent_data = spy_intraday.tail(5)
                logger.info("Recent 30-min SPY volume:")
                for idx, row in recent_data.iterrows():
                    logger.info(f"  {row['datetime']}: {row['volume']:,} shares @ ${row['close']:.2f}")
                
                # Calculate total daily volume
                spy_intraday['date'] = spy_intraday['datetime'].dt.date
                daily_volume = spy_intraday.groupby('date')['volume'].sum()
                
                logger.info("SPY Daily Volume Summary:")
                for date, volume in daily_volume.items():
                    logger.info(f"  {date}: {volume:,} shares")
                
                return True
            else:
                logger.warning("No SPY intraday data received")
                return False
        else:
            logger.error("No SPY quote data received")
            return False
            
    except Exception as e:
        logger.error(f"SPY volume test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_spx_volume_direct():
    """Test getting SPX volume directly (may not be available)"""
    logger.info("Testing direct SPX volume...")
    
    try:
        os.environ['TRADIER_API_KEY'] = 'xfiiBZaKv6Z68ossl3VjtjWL0Tsc'
        os.environ['TRADIER_ACCOUNT_ID'] = '6YB53834'
        
        config = Config()
        api = TradierAPI(config.tradier_api_key)
        
        # Test SPX quote
        spx_quote = api.get_current_quote('SPX')
        
        if not spx_quote.empty:
            spx_data = spx_quote.iloc[0]
            logger.info(f"SPX Current Quote:")
            logger.info(f"  Price: ${spx_data.get('last', 'N/A'):.2f}")
            logger.info(f"  Volume: {spx_data.get('volume', 'N/A')}")
            logger.info(f"  Average Volume: {spx_data.get('average_volume', 'N/A')}")
            
            # Test SPX intraday data
            logger.info("Getting SPX 30-minute intraday data...")
            spx_intraday = api.get_intraday_data('SPX', interval='30min', days_back=2)
            
            if not spx_intraday.empty:
                logger.info(f"SPX 30-min data: {len(spx_intraday)} bars")
                
                # Check if volume data exists
                volume_data = spx_intraday['volume'].dropna()
                if len(volume_data) > 0 and volume_data.sum() > 0:
                    logger.info("SPX has volume data:")
                    recent_data = spx_intraday.tail(5)
                    for idx, row in recent_data.iterrows():
                        logger.info(f"  {row['datetime']}: {row['volume']:,} @ ${row['close']:.2f}")
                    return True
                else:
                    logger.info("SPX volume data is zero/null (expected for index)")
                    return False
            else:
                logger.warning("No SPX intraday data received")
                return False
        else:
            logger.error("No SPX quote data received")
            return False
            
    except Exception as e:
        logger.error(f"SPX volume test failed: {e}")
        return False

def test_component_volume_sampling():
    """Test getting volume from major SPX components"""
    logger.info("Testing volume from SPX components...")
    
    try:
        os.environ['TRADIER_API_KEY'] = 'xfiiBZaKv6Z68ossl3VjtjWL0Tsc'
        os.environ['TRADIER_ACCOUNT_ID'] = '6YB53834'
        
        config = Config()
        api = TradierAPI(config.tradier_api_key)
        
        # Major SPX components (top 10 by weight - approximate)
        major_components = [
            'AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 
            'TSLA', 'META', 'BRK.B', 'UNH', 'JNJ'
        ]
        
        logger.info(f"Getting quotes for {len(major_components)} major SPX components...")
        
        # Get quotes for multiple symbols
        component_quotes = api.get_latest_quotes(major_components, greeks=False)
        
        if not component_quotes.empty:
            logger.info(f"Retrieved quotes for {len(component_quotes)} components")
            
            total_volume = 0
            total_dollar_volume = 0
            
            logger.info("Component Volume Summary:")
            for idx, row in component_quotes.iterrows():
                symbol = row['symbol']
                price = row.get('last', 0)
                volume = row.get('volume', 0)
                dollar_volume = price * volume
                
                total_volume += volume
                total_dollar_volume += dollar_volume
                
                logger.info(f"  {symbol}: {volume:,} shares @ ${price:.2f} = ${dollar_volume:,.0f}")
            
            logger.info(f"Total Sample Volume: {total_volume:,} shares")
            logger.info(f"Total Sample Dollar Volume: ${total_dollar_volume:,.0f}")
            
            # Estimate full SPX volume (these top 10 represent ~30% of SPX)
            estimated_full_volume = total_volume * 3.3  # Rough approximation
            estimated_full_dollar_volume = total_dollar_volume * 3.3
            
            logger.info(f"Estimated Full SPX Volume: {estimated_full_volume:,.0f} shares")
            logger.info(f"Estimated Full SPX Dollar Volume: ${estimated_full_dollar_volume:,.0f}")
            
            return True
        else:
            logger.error("No component quotes received")
            return False
            
    except Exception as e:
        logger.error(f"Component volume test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_volume_indicators():
    """Test various volume-based indicators"""
    logger.info("Testing volume indicators...")
    
    try:
        os.environ['TRADIER_API_KEY'] = 'xfiiBZaKv6Z68ossl3VjtjWL0Tsc'
        os.environ['TRADIER_ACCOUNT_ID'] = '6YB53834'
        
        config = Config()
        api = TradierAPI(config.tradier_api_key)
        
        # Get SPY historical data for volume analysis
        logger.info("Getting SPY historical data for volume indicators...")
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        spy_historical = api.get_historical_quotes(['SPY'], start_date, end_date, 'daily')
        
        if not spy_historical.empty:
            logger.info(f"Retrieved {len(spy_historical)} days of SPY data")
            
            # Calculate volume indicators
            spy_historical = spy_historical.sort_values('date').reset_index(drop=True)
            
            # Volume moving averages
            spy_historical['volume_ma_10'] = spy_historical['volume'].rolling(10).mean()
            spy_historical['volume_ma_20'] = spy_historical['volume'].rolling(20).mean()
            
            # Volume relative to average
            spy_historical['volume_vs_avg'] = spy_historical['volume'] / spy_historical['volume_ma_20']
            
            # Recent volume analysis
            recent_data = spy_historical.tail(5)
            logger.info("Recent SPY Volume Analysis:")
            
            for idx, row in recent_data.iterrows():
                volume_ratio = row['volume_vs_avg'] if pd.notna(row['volume_vs_avg']) else 0
                volume_desc = "High" if volume_ratio > 1.2 else "Normal" if volume_ratio > 0.8 else "Low"
                
                logger.info(f"  {row['date']}: {row['volume']:,} ({volume_desc}) "
                          f"vs 20-day avg: {volume_ratio:.1f}x")
            
            # Current volume statistics
            latest = spy_historical.iloc[-1]
            avg_volume = spy_historical['volume'].tail(20).mean()
            
            logger.info(f"Volume Statistics:")
            logger.info(f"  Latest Volume: {latest['volume']:,}")
            logger.info(f"  20-day Average: {avg_volume:,.0f}")
            logger.info(f"  Relative Volume: {latest['volume']/avg_volume:.2f}x")
            
            return True
        else:
            logger.error("No SPY historical data received")
            return False
            
    except Exception as e:
        logger.error(f"Volume indicators test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing SPX Volume Calculation Methods...\n")
    
    # Test 1: SPY ETF as proxy
    try:
        success1 = test_spy_etf_volume()
        print(f"\nSPY ETF Volume Test: {'PASSED' if success1 else 'FAILED'}")
    except Exception as e:
        print(f"\nSPY ETF Volume Test: FAILED - {e}")
        success1 = False
    
    print("\n" + "="*50)
    
    # Test 2: Direct SPX volume
    try:
        success2 = test_spx_volume_direct()
        print(f"\nDirect SPX Volume Test: {'PASSED' if success2 else 'FAILED'}")
    except Exception as e:
        print(f"\nDirect SPX Volume Test: FAILED - {e}")
        success2 = False
    
    print("\n" + "="*50)
    
    # Test 3: Component sampling
    try:
        success3 = test_component_volume_sampling()
        print(f"\nComponent Volume Sampling Test: {'PASSED' if success3 else 'FAILED'}")
    except Exception as e:
        print(f"\nComponent Volume Sampling Test: FAILED - {e}")
        success3 = False
    
    print("\n" + "="*50)
    
    # Test 4: Volume indicators
    try:
        success4 = test_volume_indicators()
        print(f"\nVolume Indicators Test: {'PASSED' if success4 else 'FAILED'}")
    except Exception as e:
        print(f"\nVolume Indicators Test: FAILED - {e}")
        success4 = False
    
    print("\n" + "="*50)
    
    if success1 or success3 or success4:
        print("\n✓ Volume analysis methods available!")
        print("\nRecommended approach:")
        if success1:
            print("- Use SPY ETF volume as primary SPX volume proxy")
        if success3:
            print("- Use major component sampling for additional context")
        if success4:
            print("- Include volume indicators for market analysis")
    else:
        print("\n✗ No reliable volume methods found")