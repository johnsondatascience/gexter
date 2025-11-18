#!/usr/bin/env python3
"""
Trading Signal Generator

Generates actionable trading signals based on:
1. Gamma Exposure (GEX) - Dealer positioning
2. Technical Analysis - EMAs (8, 21, 55 Fibonacci sequence)
3. Multi-timeframe analysis
4. Support/Resistance levels from GEX
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging


class SignalType(Enum):
    """Trading signal types"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class SignalSource(Enum):
    """Source of trading signal"""
    GEX_POSITIONING = "GEX_POSITIONING"
    GEX_CHANGE = "GEX_CHANGE"
    EMA_CROSSOVER = "EMA_CROSSOVER"
    EMA_POSITIONING = "EMA_POSITIONING"
    ZERO_GEX_LEVEL = "ZERO_GEX_LEVEL"
    MAX_GEX_LEVEL = "MAX_GEX_LEVEL"
    SUPPORT_RESISTANCE = "SUPPORT_RESISTANCE"


class TradingSignalGenerator:
    """Generate trading signals from GEX and technical analysis"""

    def __init__(self, db_connection):
        """
        Initialize signal generator

        Args:
            db_connection: Database connection (psycopg2 or SQLAlchemy)
        """
        self.db = db_connection
        self.logger = logging.getLogger(__name__)

    def get_latest_gex_data(self, lookback_hours: int = 168) -> pd.DataFrame:
        """
        Get latest GEX data for analysis

        Args:
            lookback_hours: Hours of historical data to retrieve (default: 168 = 7 days)

        Returns:
            DataFrame with GEX data
        """
        query = """
        SELECT
            "greeks.updated_at",
            expiration_date,
            strike,
            option_type,
            gex,
            gex_diff,
            gex_pct_change,
            open_interest,
            spx_price,
            "greeks.delta",
            "greeks.gamma"
        FROM gex_table
        WHERE "greeks.updated_at" >= NOW() - INTERVAL '%s hours'
        ORDER BY "greeks.updated_at" DESC, expiration_date, strike
        """
        return pd.read_sql(query, self.db, params=(lookback_hours,))

    def calculate_net_gex_by_strike(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate net GEX per strike (calls - puts)

        Args:
            df: DataFrame with GEX data

        Returns:
            DataFrame with net GEX by strike
        """
        latest_timestamp = df['greeks.updated_at'].max()
        latest_df = df[df['greeks.updated_at'] == latest_timestamp].copy()

        # Pivot to get calls and puts by strike
        pivot = latest_df.pivot_table(
            index='strike',
            columns='option_type',
            values='gex',
            aggfunc='sum'
        ).fillna(0)

        # Calculate net GEX (calls are positive, puts are already negative)
        if 'call' in pivot.columns and 'put' in pivot.columns:
            pivot['net_gex'] = pivot['call'] + pivot['put']  # puts are already negative
        elif 'call' in pivot.columns:
            pivot['net_gex'] = pivot['call']
        elif 'put' in pivot.columns:
            pivot['net_gex'] = pivot['put']
        else:
            pivot['net_gex'] = 0

        return pivot.reset_index()

    def find_zero_gex_level(self, net_gex_df: pd.DataFrame, current_price: float) -> Optional[float]:
        """
        Find the "zero GEX" level where net GEX crosses zero
        This is a critical level - market tends to be volatile below it

        Args:
            net_gex_df: DataFrame with net GEX by strike
            current_price: Current SPX price

        Returns:
            Zero GEX strike level or None
        """
        try:
            # Sort by strike
            sorted_df = net_gex_df.sort_values('strike')

            # Find where net_gex crosses zero
            sorted_df['sign_change'] = np.sign(sorted_df['net_gex']).diff()
            zero_crosses = sorted_df[sorted_df['sign_change'] != 0]

            if len(zero_crosses) == 0:
                return None

            # Find closest zero cross to current price
            zero_crosses['distance'] = abs(zero_crosses['strike'] - current_price)
            closest = zero_crosses.nsmallest(1, 'distance')

            return float(closest['strike'].iloc[0])

        except Exception as e:
            self.logger.error(f"Error finding zero GEX level: {e}")
            return None

    def find_max_gex_levels(self, net_gex_df: pd.DataFrame,
                           current_price: float,
                           num_levels: int = 3) -> Dict[str, List[float]]:
        """
        Find maximum positive and negative GEX levels
        These act as support/resistance

        Args:
            net_gex_df: DataFrame with net GEX by strike
            current_price: Current SPX price
            num_levels: Number of levels to find above and below

        Returns:
            Dict with 'resistance' and 'support' lists
        """
        try:
            above_price = net_gex_df[net_gex_df['strike'] > current_price].copy()
            below_price = net_gex_df[net_gex_df['strike'] < current_price].copy()

            # Resistance (above) - find max positive GEX (call walls)
            resistance = above_price.nlargest(num_levels, 'net_gex')['strike'].tolist()

            # Support (below) - find max negative GEX (put walls)
            support = below_price.nsmallest(num_levels, 'net_gex')['strike'].tolist()

            return {
                'resistance': sorted(resistance),
                'support': sorted(support, reverse=True)
            }

        except Exception as e:
            self.logger.error(f"Error finding max GEX levels: {e}")
            return {'resistance': [], 'support': []}

    def calculate_gex_positioning_signal(self, current_price: float,
                                        zero_gex: Optional[float],
                                        net_gex_at_price: float) -> Tuple[SignalType, float, str]:
        """
        Generate signal based on GEX positioning

        Rules:
        - Below zero GEX = volatile, dealers are long gamma (STRONG momentum signals)
        - Above zero GEX = pinned, dealers are short gamma (weaker momentum)
        - Positive net GEX at spot = resistance/ceiling
        - Negative net GEX at spot = support/floor

        Args:
            current_price: Current SPX price
            zero_gex: Zero GEX strike level
            net_gex_at_price: Net GEX near current price

        Returns:
            Tuple of (signal_type, confidence, reasoning)
        """
        if zero_gex is None:
            return SignalType.NEUTRAL, 0.5, "No clear GEX zero level found"

        # Check if below zero GEX (volatile regime)
        below_zero_gex = current_price < zero_gex
        distance_from_zero = abs(current_price - zero_gex) / current_price * 100

        if below_zero_gex:
            # Below zero GEX - expect strong momentum moves
            if net_gex_at_price < 0:
                # Negative GEX at spot = put support, bullish if holding
                return (SignalType.BUY, 0.7,
                       f"Below zero GEX ({zero_gex:.0f}), negative GEX at spot = put support. "
                       f"Expect volatile moves with momentum.")
            else:
                # Positive GEX at spot = call resistance
                return (SignalType.SELL, 0.6,
                       f"Below zero GEX ({zero_gex:.0f}), positive GEX at spot = call resistance. "
                       f"May face selling pressure.")
        else:
            # Above zero GEX - expect pinning/range-bound
            if distance_from_zero < 1.0:
                # Very close to zero GEX
                return (SignalType.NEUTRAL, 0.8,
                       f"Near zero GEX ({zero_gex:.0f}), expect choppy price action.")
            else:
                # Well above zero GEX
                return (SignalType.NEUTRAL, 0.6,
                       f"Above zero GEX ({zero_gex:.0f}), market likely to be pinned. "
                       f"Range-bound trading expected.")

    def calculate_gex_change_signal(self, df: pd.DataFrame,
                                    current_price: float,
                                    lookback_periods: int = 3) -> Tuple[SignalType, float, str]:
        """
        Generate signal based on intraday GEX changes

        Large changes in GEX indicate dealer repositioning

        Args:
            df: DataFrame with GEX data
            current_price: Current SPX price
            lookback_periods: Number of periods to analyze

        Returns:
            Tuple of (signal_type, confidence, reasoning)
        """
        try:
            # Get recent timestamps
            timestamps = sorted(df['greeks.updated_at'].unique())[-lookback_periods:]
            if len(timestamps) < 2:
                return SignalType.NEUTRAL, 0.3, "Insufficient data for GEX change analysis"

            # Filter data near current price (+/- 2%)
            price_window = current_price * 0.02
            near_price = df[
                (df['strike'] >= current_price - price_window) &
                (df['strike'] <= current_price + price_window)
            ].copy()

            # Calculate net GEX change over period
            gex_by_time = near_price.groupby('greeks.updated_at')['gex'].sum()

            if len(gex_by_time) < 2:
                return SignalType.NEUTRAL, 0.3, "Insufficient data points"

            # Calculate change
            recent_gex = gex_by_time.iloc[-1]
            previous_gex = gex_by_time.iloc[0]
            gex_change = recent_gex - previous_gex
            gex_pct_change = (gex_change / abs(previous_gex) * 100) if previous_gex != 0 else 0

            # Generate signal based on change magnitude
            if abs(gex_pct_change) < 5:
                return SignalType.NEUTRAL, 0.4, f"Small GEX change ({gex_pct_change:.1f}%)"

            if gex_change > 0:
                # Increasing GEX = more call buying or put selling (bullish)
                confidence = min(0.9, 0.5 + abs(gex_pct_change) / 100)
                return (SignalType.BUY if gex_pct_change > 10 else SignalType.BUY,
                       confidence,
                       f"GEX increased {gex_pct_change:.1f}% - bullish repositioning detected")
            else:
                # Decreasing GEX = more put buying or call selling (bearish)
                confidence = min(0.9, 0.5 + abs(gex_pct_change) / 100)
                return (SignalType.SELL if gex_pct_change < -10 else SignalType.SELL,
                       confidence,
                       f"GEX decreased {gex_pct_change:.1f}% - bearish repositioning detected")

        except Exception as e:
            self.logger.error(f"Error calculating GEX change signal: {e}")
            return SignalType.NEUTRAL, 0.3, f"Error in analysis: {str(e)}"

    def get_ema_signals(self) -> pd.DataFrame:
        """
        Get EMA-based signals from the indicators table

        Returns:
            DataFrame with latest EMA values and signals
        """
        query = """
        SELECT
            timestamp,
            spx_price,
            ema_8,
            ema_21,
            price_vs_ema8_pct,
            price_vs_ema21_pct,
            ema8_vs_ema21_pct,
            ema_signal
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (ORDER BY timestamp DESC) as rn
            FROM spx_indicators
        ) sub
        WHERE rn <= 10
        ORDER BY timestamp DESC
        """
        try:
            return pd.read_sql(query, self.db)
        except Exception as e:
            self.logger.error(f"Error fetching EMA signals: {e}")
            return pd.DataFrame()

    def calculate_ema_positioning_signal(self, ema_df: pd.DataFrame) -> Tuple[SignalType, float, str]:
        """
        Generate signal based on EMA positioning

        Rules:
        - Price > EMA8 > EMA21 = Strong uptrend
        - Price < EMA8 < EMA21 = Strong downtrend
        - Price between EMAs = Consolidation
        - EMA crossovers = Trend changes

        Args:
            ema_df: DataFrame with EMA data

        Returns:
            Tuple of (signal_type, confidence, reasoning)
        """
        if ema_df.empty or len(ema_df) < 2:
            return SignalType.NEUTRAL, 0.3, "Insufficient EMA data"

        latest = ema_df.iloc[0]
        previous = ema_df.iloc[1]

        price = latest['spx_price']
        ema8 = latest['ema_8']
        ema21 = latest['ema_21']

        # Check for crossover
        ema8_above_21_now = ema8 > ema21
        ema8_above_21_prev = previous['ema_8'] > previous['ema_21']
        crossover = ema8_above_21_now != ema8_above_21_prev

        if crossover:
            if ema8_above_21_now:
                return (SignalType.STRONG_BUY, 0.85,
                       f"Bullish EMA crossover: EMA8 ({ema8:.2f}) crossed above EMA21 ({ema21:.2f})")
            else:
                return (SignalType.STRONG_SELL, 0.85,
                       f"Bearish EMA crossover: EMA8 ({ema8:.2f}) crossed below EMA21 ({ema21:.2f})")

        # Check positioning
        if price > ema8 and ema8 > ema21:
            # Strong uptrend
            distance_8 = (price - ema8) / price * 100
            confidence = 0.75 if distance_8 < 0.5 else 0.65  # Lower confidence if overextended
            return (SignalType.BUY, confidence,
                   f"Strong uptrend: Price ({price:.2f}) > EMA8 ({ema8:.2f}) > EMA21 ({ema21:.2f})")

        elif price < ema8 and ema8 < ema21:
            # Strong downtrend
            distance_8 = (ema8 - price) / price * 100
            confidence = 0.75 if distance_8 < 0.5 else 0.65
            return (SignalType.SELL, confidence,
                   f"Strong downtrend: Price ({price:.2f}) < EMA8 ({ema8:.2f}) < EMA21 ({ema21:.2f})")

        elif ema8 < price < ema21:
            return (SignalType.NEUTRAL, 0.6,
                   f"Price between EMAs - consolidation. Watch for breakout above {ema21:.2f}")

        elif ema21 < price < ema8:
            return (SignalType.NEUTRAL, 0.6,
                   f"Price between EMAs - consolidation. Watch for breakdown below {ema21:.2f}")

        else:
            return (SignalType.NEUTRAL, 0.5,
                   f"Mixed EMA signals - no clear trend")

    def generate_comprehensive_signals(self) -> Dict:
        """
        Generate comprehensive trading signals from all sources

        Returns:
            Dict with all signals and recommendations
        """
        self.logger.info("Generating comprehensive trading signals...")

        # Get data
        gex_df = self.get_latest_gex_data(lookback_hours=24)
        ema_df = self.get_ema_signals()

        if gex_df.empty:
            return {
                'error': 'No GEX data available',
                'timestamp': datetime.now()
            }

        # Get current price
        current_price = float(gex_df['spx_price'].iloc[0])
        latest_timestamp = gex_df['greeks.updated_at'].max()

        # Calculate GEX metrics
        net_gex_df = self.calculate_net_gex_by_strike(gex_df)
        zero_gex = self.find_zero_gex_level(net_gex_df, current_price)
        gex_levels = self.find_max_gex_levels(net_gex_df, current_price)

        # Get net GEX near current price
        near_price = net_gex_df[
            (net_gex_df['strike'] >= current_price - 5) &
            (net_gex_df['strike'] <= current_price + 5)
        ]
        net_gex_at_price = float(near_price['net_gex'].mean()) if not near_price.empty else 0

        # Generate individual signals
        signals = []

        # 1. GEX Positioning Signal
        gex_pos_signal, gex_pos_conf, gex_pos_reason = self.calculate_gex_positioning_signal(
            current_price, zero_gex, net_gex_at_price
        )
        signals.append({
            'source': SignalSource.GEX_POSITIONING.value,
            'signal': gex_pos_signal.value,
            'confidence': gex_pos_conf,
            'reasoning': gex_pos_reason
        })

        # 2. GEX Change Signal
        gex_change_signal, gex_change_conf, gex_change_reason = self.calculate_gex_change_signal(
            gex_df, current_price
        )
        signals.append({
            'source': SignalSource.GEX_CHANGE.value,
            'signal': gex_change_signal.value,
            'confidence': gex_change_conf,
            'reasoning': gex_change_reason
        })

        # 3. EMA Positioning Signal
        if not ema_df.empty:
            ema_signal, ema_conf, ema_reason = self.calculate_ema_positioning_signal(ema_df)
            signals.append({
                'source': SignalSource.EMA_POSITIONING.value,
                'signal': ema_signal.value,
                'confidence': ema_conf,
                'reasoning': ema_reason
            })

        # Calculate composite signal
        composite_signal, composite_conf = self._calculate_composite_signal(signals)

        return {
            'timestamp': latest_timestamp,
            'current_price': current_price,
            'zero_gex_level': zero_gex,
            'gex_levels': gex_levels,
            'net_gex_at_price': net_gex_at_price,
            'individual_signals': signals,
            'composite_signal': composite_signal.value,
            'composite_confidence': composite_conf,
            'recommendation': self._generate_recommendation(
                composite_signal, composite_conf, current_price, zero_gex, gex_levels
            )
        }

    def _calculate_composite_signal(self, signals: List[Dict]) -> Tuple[SignalType, float]:
        """
        Calculate weighted composite signal from individual signals

        Args:
            signals: List of individual signal dicts

        Returns:
            Tuple of (composite_signal, confidence)
        """
        if not signals:
            return SignalType.NEUTRAL, 0.5

        # Signal to numeric value mapping
        signal_values = {
            'STRONG_BUY': 2,
            'BUY': 1,
            'NEUTRAL': 0,
            'SELL': -1,
            'STRONG_SELL': -2
        }

        # Calculate weighted average
        weighted_sum = sum(
            signal_values[s['signal']] * s['confidence']
            for s in signals
        )
        weight_total = sum(s['confidence'] for s in signals)

        avg_signal = weighted_sum / weight_total if weight_total > 0 else 0
        avg_confidence = weight_total / len(signals)

        # Convert back to signal type
        if avg_signal >= 1.5:
            return SignalType.STRONG_BUY, avg_confidence
        elif avg_signal >= 0.5:
            return SignalType.BUY, avg_confidence
        elif avg_signal <= -1.5:
            return SignalType.STRONG_SELL, avg_confidence
        elif avg_signal <= -0.5:
            return SignalType.SELL, avg_confidence
        else:
            return SignalType.NEUTRAL, avg_confidence

    def _generate_recommendation(self, signal: SignalType, confidence: float,
                                current_price: float, zero_gex: Optional[float],
                                gex_levels: Dict) -> str:
        """
        Generate human-readable trading recommendation

        Args:
            signal: Composite signal type
            confidence: Signal confidence (0-1)
            current_price: Current SPX price
            zero_gex: Zero GEX level
            gex_levels: Support/resistance levels

        Returns:
            Formatted recommendation string
        """
        rec = []

        # Main signal
        if signal == SignalType.STRONG_BUY:
            rec.append(f"🟢 STRONG BUY signal (Confidence: {confidence:.0%})")
            rec.append("Consider opening long positions or adding to existing longs.")
        elif signal == SignalType.BUY:
            rec.append(f"🟢 BUY signal (Confidence: {confidence:.0%})")
            rec.append("Bullish bias. Consider long positions on pullbacks.")
        elif signal == SignalType.STRONG_SELL:
            rec.append(f"🔴 STRONG SELL signal (Confidence: {confidence:.0%})")
            rec.append("Consider opening short positions or reducing longs.")
        elif signal == SignalType.SELL:
            rec.append(f"🔴 SELL signal (Confidence: {confidence:.0%})")
            rec.append("Bearish bias. Consider short positions on rallies.")
        else:
            rec.append(f"⚪ NEUTRAL signal (Confidence: {confidence:.0%})")
            rec.append("No clear directional bias. Wait for better setup.")

        rec.append("")

        # Key levels
        rec.append(f"Current SPX: {current_price:.2f}")
        if zero_gex:
            position = "below" if current_price < zero_gex else "above"
            rec.append(f"Zero GEX: {zero_gex:.2f} (SPX is {position})")

        if gex_levels['resistance']:
            rec.append(f"Resistance levels: {', '.join(f'{x:.0f}' for x in gex_levels['resistance'])}")
        if gex_levels['support']:
            rec.append(f"Support levels: {', '.join(f'{x:.0f}' for x in gex_levels['support'])}")

        return '\n'.join(rec)


def main():
    """Example usage"""
    import psycopg2
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Connect to database
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', 5432),
        database=os.getenv('POSTGRES_DB', 'gexdb'),
        user=os.getenv('POSTGRES_USER', 'gexuser'),
        password=os.getenv('POSTGRES_PASSWORD')
    )

    # Generate signals
    generator = TradingSignalGenerator(conn)
    signals = generator.generate_comprehensive_signals()

    # Print results
    print("=" * 80)
    print("TRADING SIGNALS REPORT")
    print("=" * 80)
    print(f"\nTimestamp: {signals['timestamp']}")
    print(f"\n{signals['recommendation']}")
    print("\n" + "=" * 80)
    print("INDIVIDUAL SIGNALS")
    print("=" * 80)
    for sig in signals['individual_signals']:
        print(f"\n{sig['source']}:")
        print(f"  Signal: {sig['signal']} (Confidence: {sig['confidence']:.0%})")
        print(f"  {sig['reasoning']}")

    conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
