"""
Technical Indicators for SPX Analysis

Calculates EMAs and relative positioning indicators for market analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger('gex_collector')


class TechnicalIndicators:
    """Calculate technical indicators for price analysis"""
    
    def __init__(self):
        pass
    
    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        try:
            if len(prices) < period:
                logger.warning(f"Insufficient data for EMA{period}: {len(prices)} bars, need {period}")
                return pd.Series([np.nan] * len(prices), index=prices.index)
            
            # Calculate EMA using pandas ewm
            ema = prices.ewm(span=period, adjust=False).mean()
            
            logger.debug(f"Calculated EMA{period} with {len(ema)} values")
            return ema
            
        except Exception as e:
            logger.error(f"Error calculating EMA{period}: {e}")
            return pd.Series([np.nan] * len(prices), index=prices.index)
    
    def calculate_multiple_emas(self, prices: pd.Series, periods: list) -> Dict[str, pd.Series]:
        """Calculate multiple EMAs at once"""
        emas = {}
        for period in periods:
            emas[f'ema_{period}'] = self.calculate_ema(prices, period)
        return emas
    
    def get_relative_position(self, current_price: float, ema_value: float) -> Dict[str, float]:
        """Calculate relative position of current price vs EMA"""
        try:
            if pd.isna(ema_value) or ema_value == 0:
                return {
                    'absolute_diff': np.nan,
                    'percentage_diff': np.nan,
                    'position': np.nan  # 1 = above, 0 = below
                }
            
            absolute_diff = current_price - ema_value
            percentage_diff = (absolute_diff / ema_value) * 100
            position = 1.0 if current_price > ema_value else 0.0
            
            return {
                'absolute_diff': absolute_diff,
                'percentage_diff': percentage_diff,
                'position': position
            }
            
        except Exception as e:
            logger.error(f"Error calculating relative position: {e}")
            return {
                'absolute_diff': np.nan,
                'percentage_diff': np.nan,
                'position': np.nan
            }
    
    def calculate_ema_trend(self, ema_short: pd.Series, ema_long: pd.Series) -> Dict[str, float]:
        """Calculate trend between two EMAs"""
        try:
            if len(ema_short) == 0 or len(ema_long) == 0:
                return {'trend': np.nan, 'trend_strength': np.nan}
            
            short_current = ema_short.iloc[-1] if not pd.isna(ema_short.iloc[-1]) else np.nan
            long_current = ema_long.iloc[-1] if not pd.isna(ema_long.iloc[-1]) else np.nan
            
            if pd.isna(short_current) or pd.isna(long_current):
                return {'trend': np.nan, 'trend_strength': np.nan}
            
            # Trend: 1 = bullish (short > long), 0 = bearish (short < long)
            trend = 1.0 if short_current > long_current else 0.0
            
            # Trend strength as percentage difference
            trend_strength = ((short_current - long_current) / long_current) * 100
            
            return {
                'trend': trend,
                'trend_strength': trend_strength
            }
            
        except Exception as e:
            logger.error(f"Error calculating EMA trend: {e}")
            return {'trend': np.nan, 'trend_strength': np.nan}
    
    def get_ema_slope(self, ema: pd.Series, periods_back: int = 3) -> float:
        """Calculate EMA slope over recent periods"""
        try:
            if len(ema) < periods_back + 1:
                return np.nan
            
            # Get recent values
            recent_values = ema.tail(periods_back + 1)
            
            # Calculate slope using linear regression
            x = np.arange(len(recent_values))
            y = recent_values.values
            
            # Remove NaN values
            valid_mask = ~np.isnan(y)
            if np.sum(valid_mask) < 2:
                return np.nan
            
            x_valid = x[valid_mask]
            y_valid = y[valid_mask]
            
            # Calculate slope
            slope = np.polyfit(x_valid, y_valid, 1)[0]
            
            return slope
            
        except Exception as e:
            logger.error(f"Error calculating EMA slope: {e}")
            return np.nan


class SPXIndicatorCalculator:
    """SPX-specific indicator calculator"""
    
    def __init__(self, api_client):
        self.api = api_client
        self.indicators = TechnicalIndicators()
        # SPY-SPX conversion ratio (based on historical analysis)
        self.spy_spx_ratio = 10.029114  # SPX = SPY * this ratio
        self.spy_spx_ratio_tolerance = 0.05  # 5% tolerance for ratio validation
    
    def get_spy_volume_data(self) -> Dict:
        """Get SPY volume data as SPX proxy"""
        try:
            logger.info("Fetching SPY volume data as SPX proxy...")
            
            # Get current SPY quote
            spy_quote = self.api.get_current_quote('SPY')
            
            if spy_quote.empty:
                logger.warning("No SPY quote data received")
                return {}
            
            spy_data = spy_quote.iloc[0]
            
            # Get SPY historical data for volume analysis (last 30 days)
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            spy_historical = self.api.get_historical_quotes(['SPY'], start_date, end_date, 'daily')
            
            volume_indicators = {}
            
            if not spy_historical.empty:
                # Calculate volume moving averages
                spy_historical = spy_historical.sort_values('date').reset_index(drop=True)
                spy_historical['volume_ma_10'] = spy_historical['volume'].rolling(10).mean()
                spy_historical['volume_ma_20'] = spy_historical['volume'].rolling(20).mean()
                
                # Get latest values
                latest = spy_historical.iloc[-1]
                
                volume_indicators = {
                    'spy_current_volume': spy_data.get('volume', 0),
                    'spy_average_volume': spy_data.get('average_volume', 0),
                    'spy_volume_ma_10': latest.get('volume_ma_10', 0),
                    'spy_volume_ma_20': latest.get('volume_ma_20', 0),
                    'spy_volume_vs_ma10': spy_data.get('volume', 0) / latest.get('volume_ma_10', 1) if latest.get('volume_ma_10', 0) > 0 else 0,
                    'spy_volume_vs_ma20': spy_data.get('volume', 0) / latest.get('volume_ma_20', 1) if latest.get('volume_ma_20', 0) > 0 else 0,
                    'spy_price': spy_data.get('last', 0),
                    'spy_dollar_volume': spy_data.get('volume', 0) * spy_data.get('last', 0)
                }
                
                # Volume classification
                volume_ratio = volume_indicators['spy_volume_vs_ma20']
                if volume_ratio > 1.5:
                    volume_class = 2  # High
                elif volume_ratio > 0.8:
                    volume_class = 1  # Normal  
                else:
                    volume_class = 0  # Low
                
                volume_indicators['spy_volume_classification'] = volume_class
                
                logger.info(f"SPY Volume: {volume_indicators['spy_current_volume']:,} shares "
                          f"({volume_ratio:.1f}x vs 20-day avg)")
                
            else:
                logger.warning("No SPY historical data for volume calculations")
                volume_indicators = {
                    'spy_current_volume': spy_data.get('volume', 0),
                    'spy_average_volume': spy_data.get('average_volume', 0),
                    'spy_volume_ma_10': 0,
                    'spy_volume_ma_20': 0,
                    'spy_volume_vs_ma10': 0,
                    'spy_volume_vs_ma20': 0,
                    'spy_price': spy_data.get('last', 0),
                    'spy_dollar_volume': spy_data.get('volume', 0) * spy_data.get('last', 0),
                    'spy_volume_classification': 1
                }
            
            return volume_indicators
            
        except Exception as e:
            logger.error(f"Error getting SPY volume data: {e}")
            return {}
    
    def estimate_spx_from_spy(self, spy_price: float, spx_price: Optional[float] = None) -> Dict:
        """Estimate SPX price from SPY when SPX is not actively traded"""
        try:
            # Calculate estimated SPX price
            estimated_spx = spy_price * self.spy_spx_ratio
            
            # Initialize result
            result = {
                'spy_price_for_estimation': spy_price,
                'spx_estimated_price': estimated_spx,
                'spx_estimation_ratio': self.spy_spx_ratio,
                'spx_price_is_estimated': True,
                'spx_actual_price': spx_price if spx_price else np.nan,
                'spx_estimation_error': np.nan,
                'spx_estimation_error_pct': np.nan,
                'spx_estimation_confidence': 'high'  # Based on 0.0998% historical variance
            }
            
            # If actual SPX price is available, calculate estimation accuracy
            if spx_price and not pd.isna(spx_price) and spx_price > 0:
                # Check if SPX appears to be stale (significant deviation from estimated)
                current_ratio = spx_price / spy_price
                ratio_deviation = abs(current_ratio - self.spy_spx_ratio) / self.spy_spx_ratio
                
                if ratio_deviation > self.spy_spx_ratio_tolerance:
                    # SPX appears stale, use estimation
                    logger.warning(f"SPX price appears stale. Ratio deviation: {ratio_deviation:.2%}")
                    result['spx_price_appears_stale'] = True
                    result['spx_final_price'] = estimated_spx
                    result['spx_price_source'] = 'estimated_due_to_stale_spx'
                else:
                    # SPX appears current, use actual
                    estimation_error = abs(estimated_spx - spx_price)
                    estimation_error_pct = (estimation_error / spx_price) * 100
                    
                    result['spx_estimation_error'] = estimation_error
                    result['spx_estimation_error_pct'] = estimation_error_pct
                    result['spx_price_is_estimated'] = False
                    result['spx_price_appears_stale'] = False
                    result['spx_final_price'] = spx_price
                    result['spx_price_source'] = 'actual_spx'
                    
                    logger.info(f"SPX estimation accuracy: ${estimation_error:.2f} ({estimation_error_pct:.3f}%)")
            else:
                # No SPX price available, use estimation
                result['spx_final_price'] = estimated_spx
                result['spx_price_source'] = 'estimated_no_spx_available'
            
            logger.info(f"SPX Price Analysis: SPY ${spy_price:.2f} -> Estimated SPX ${estimated_spx:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in SPX estimation: {e}")
            return {
                'spy_price_for_estimation': spy_price,
                'spx_estimated_price': np.nan,
                'spx_estimation_ratio': self.spy_spx_ratio,
                'spx_price_is_estimated': True,
                'spx_final_price': np.nan,
                'spx_price_source': 'estimation_error'
            }
    
    def get_spx_30min_data(self, days_back: int = 10) -> pd.DataFrame:
        """Get SPX 30-minute data for indicator calculations"""
        try:
            logger.info(f"Fetching SPX 30-minute data for last {days_back} days...")
            
            # Get 30-minute intraday data
            df = self.api.get_intraday_data('SPX', interval='30min', days_back=days_back)
            
            if df.empty:
                logger.warning("No 30-minute SPX data received")
                return df
            
            # Ensure we have OHLC columns
            required_cols = ['datetime', 'open', 'high', 'low', 'close']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                logger.error(f"Missing required columns in 30min data: {missing_cols}")
                return pd.DataFrame()
            
            # Sort by datetime and clean data
            df = df.sort_values('datetime').reset_index(drop=True)
            
            # Convert price columns to numeric
            price_cols = ['open', 'high', 'low', 'close']
            for col in price_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            logger.info(f"Retrieved {len(df)} 30-minute bars for SPX")
            return df
            
        except Exception as e:
            logger.error(f"Error getting SPX 30min data: {e}")
            return pd.DataFrame()
    
    def calculate_spx_indicators(self, current_spx_price: float) -> Dict:
        """Calculate all SPX indicators including EMAs and relative positioning"""
        try:
            logger.info("Calculating SPX technical indicators...")
            
            # Get SPY volume data
            spy_volume_data = self.get_spy_volume_data()
            
            # Get SPY price for estimation
            spy_price = spy_volume_data.get('spy_price', 0)
            
            # Estimate SPX price from SPY
            spx_estimation_data = {}
            if spy_price > 0:
                spx_estimation_data = self.estimate_spx_from_spy(spy_price, current_spx_price)
                
                # Use estimated price for technical analysis if SPX appears stale
                if spx_estimation_data.get('spx_price_source') == 'estimated_due_to_stale_spx':
                    current_spx_price = spx_estimation_data.get('spx_final_price', current_spx_price)
                    logger.info(f"Using estimated SPX price for technical analysis: ${current_spx_price:.2f}")
            
            # Get 30-minute data
            df_30min = self.get_spx_30min_data(days_back=10)
            
            if df_30min.empty:
                logger.warning("No 30-minute data available for indicator calculation")
                return self._get_empty_indicators()
            
            # Use close prices for EMA calculations
            close_prices = df_30min['close']
            
            # Calculate EMAs
            ema_8 = self.indicators.calculate_ema(close_prices, 8)
            ema_21 = self.indicators.calculate_ema(close_prices, 21)
            
            # Get current EMA values (most recent)
            current_ema_8 = ema_8.iloc[-1] if len(ema_8) > 0 and not pd.isna(ema_8.iloc[-1]) else np.nan
            current_ema_21 = ema_21.iloc[-1] if len(ema_21) > 0 and not pd.isna(ema_21.iloc[-1]) else np.nan
            
            # Calculate relative positions
            pos_vs_ema8 = self.indicators.get_relative_position(current_spx_price, current_ema_8)
            pos_vs_ema21 = self.indicators.get_relative_position(current_spx_price, current_ema_21)
            
            # Calculate EMA trend (8 vs 21)
            ema_trend = self.indicators.calculate_ema_trend(ema_8, ema_21)
            
            # Simple EMA positioning (8 vs 21)
            ema_8_above_21 = 1.0 if (not pd.isna(current_ema_8) and not pd.isna(current_ema_21) and current_ema_8 > current_ema_21) else 0.0
            
            # Calculate EMA slopes
            ema_8_slope = self.indicators.get_ema_slope(ema_8)
            ema_21_slope = self.indicators.get_ema_slope(ema_21)
            
            # Compile all indicators
            indicators = {
                # Current values
                'spx_current_price': current_spx_price,
                'spx_ema_8_current': current_ema_8,
                'spx_ema_21_current': current_ema_21,
                
                # Position vs EMA 8
                'spx_vs_ema8_abs_diff': pos_vs_ema8['absolute_diff'],
                'spx_vs_ema8_pct_diff': pos_vs_ema8['percentage_diff'],
                'spx_above_ema8': pos_vs_ema8['position'],
                
                # Position vs EMA 21
                'spx_vs_ema21_abs_diff': pos_vs_ema21['absolute_diff'],
                'spx_vs_ema21_pct_diff': pos_vs_ema21['percentage_diff'],
                'spx_above_ema21': pos_vs_ema21['position'],
                
                # EMA trend analysis
                'spx_ema_trend_bullish': ema_trend['trend'],
                'spx_ema_trend_strength': ema_trend['trend_strength'],
                'spx_ema8_above_ema21': ema_8_above_21,
                
                # EMA slopes
                'spx_ema_8_slope': ema_8_slope,
                'spx_ema_21_slope': ema_21_slope,
                
                # Data quality indicators
                'spx_30min_bars_count': len(df_30min),
                'spx_indicators_timestamp': pd.Timestamp.now().isoformat()
            }
            
            # Add SPY volume indicators
            indicators.update(spy_volume_data)
            
            # Add SPX estimation indicators
            indicators.update(spx_estimation_data)
            
            # Log key indicators
            self._log_indicators(indicators)
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating SPX indicators: {e}")
            return self._get_empty_indicators()
    
    def _get_empty_indicators(self) -> Dict:
        """Return empty/NaN indicators when calculation fails"""
        return {
            'spx_current_price': np.nan,
            'spx_ema_8_current': np.nan,
            'spx_ema_21_current': np.nan,
            'spx_vs_ema8_abs_diff': np.nan,
            'spx_vs_ema8_pct_diff': np.nan,
            'spx_above_ema8': np.nan,
            'spx_vs_ema21_abs_diff': np.nan,
            'spx_vs_ema21_pct_diff': np.nan,
            'spx_above_ema21': np.nan,
            'spx_ema_trend_bullish': np.nan,
            'spx_ema_trend_strength': np.nan,
            'spx_ema8_above_ema21': np.nan,
            'spx_ema_8_slope': np.nan,
            'spx_ema_21_slope': np.nan,
            'spx_30min_bars_count': 0,
            'spx_indicators_timestamp': pd.Timestamp.now().isoformat()
        }
    
    def _log_indicators(self, indicators: Dict):
        """Log key indicator values"""
        try:
            current_price = indicators.get('spx_current_price', 0)
            ema_8 = indicators.get('spx_ema_8_current', np.nan)
            ema_21 = indicators.get('spx_ema_21_current', np.nan)
            
            above_ema8 = indicators.get('spx_above_ema8', np.nan)
            above_ema21 = indicators.get('spx_above_ema21', np.nan)
            
            pct_vs_ema8 = indicators.get('spx_vs_ema8_pct_diff', np.nan)
            pct_vs_ema21 = indicators.get('spx_vs_ema21_pct_diff', np.nan)
            
            trend_bullish = indicators.get('spx_ema_trend_bullish', np.nan)
            ema8_above_ema21 = indicators.get('spx_ema8_above_ema21', np.nan)
            
            logger.info(f"SPX Indicators: Price=${current_price:.2f}")
            
            if not pd.isna(ema_8):
                logger.info(f"  EMA8: ${ema_8:.2f} ({'Above' if above_ema8 else 'Below'}) {pct_vs_ema8:+.2f}%")
            
            if not pd.isna(ema_21):
                logger.info(f"  EMA21: ${ema_21:.2f} ({'Above' if above_ema21 else 'Below'}) {pct_vs_ema21:+.2f}%")
            
            if not pd.isna(trend_bullish):
                trend_label = "Bullish" if trend_bullish else "Bearish"
                logger.info(f"  EMA Trend: {trend_label}")
            
            if not pd.isna(ema8_above_ema21):
                ema_position = "Above" if ema8_above_ema21 else "Below"
                logger.info(f"  EMA8 vs EMA21: {ema_position}")
                
        except Exception as e:
            logger.debug(f"Error logging indicators: {e}")
    
    def save_indicators_to_csv(self, indicators: Dict) -> bool:
        """Save indicators to a dedicated CSV file"""
        try:
            if not indicators:
                return False
            
            # Create DataFrame from indicators
            indicators_df = pd.DataFrame([indicators])
            
            # Try to load existing data and append
            import os
            indicators_file = os.path.join('output', 'spx_indicators.csv')
            os.makedirs('output', exist_ok=True)
            try:
                existing_df = pd.read_csv(indicators_file)
                combined_df = pd.concat([existing_df, indicators_df], ignore_index=True)
            except FileNotFoundError:
                combined_df = indicators_df

            # Keep only last 500 records to prevent file from growing too large
            if len(combined_df) > 500:
                combined_df = combined_df.tail(500)

            # Save to CSV
            combined_df.to_csv(indicators_file, index=False)
            
            logger.info(f"SPX indicators saved to {indicators_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving indicators to CSV: {e}")
            return False