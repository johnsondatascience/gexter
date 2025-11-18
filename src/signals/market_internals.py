#!/usr/bin/env python3
"""
Market Internals Module

Collects and analyzes market internals including:
- Breadth (advancing vs declining stocks)
- Advance/Decline Line
- Up Volume / Down Volume
- TICK, TRIN, ADD indices (if available)

Generates trading signals based on market internal strength/weakness.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum


class SignalType(Enum):
    """Trading signal types"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


@dataclass
class SectorBreadth:
    """Sector breadth data"""
    timestamp: datetime
    sectors_advancing: int
    sectors_declining: int
    sector_breadth_ratio: float
    strongest_sector: str
    weakest_sector: str
    sector_performance: Dict[str, float]  # ETF symbol -> % change from open

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp,
            'sectors_advancing': self.sectors_advancing,
            'sectors_declining': self.sectors_declining,
            'sector_breadth_ratio': self.sector_breadth_ratio,
            'strongest_sector': self.strongest_sector,
            'weakest_sector': self.weakest_sector,
            'sector_performance': self.sector_performance
        }


@dataclass
class MarketInternals:
    """Market internals data point"""
    timestamp: datetime

    # Breadth metrics
    advances: int
    declines: int
    unchanged: int
    advance_decline_ratio: float
    breadth_ratio: float  # (ADV - DEC) / (ADV + DEC)

    # Volume metrics
    up_volume: float
    down_volume: float
    up_down_volume_ratio: float
    volume_ratio: float  # (UP_VOL - DOWN_VOL) / (UP_VOL + DOWN_VOL)

    # Market indices (if available)
    tick: Optional[float] = None
    trin: Optional[float] = None
    add: Optional[float] = None

    # Derived metrics
    cumulative_ad_line: Optional[float] = None
    breadth_thrust: Optional[float] = None

    # Sector breadth
    sector_breadth: Optional[SectorBreadth] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for database storage"""
        data = {
            'timestamp': self.timestamp,
            'advances': self.advances,
            'declines': self.declines,
            'unchanged': self.unchanged,
            'advance_decline_ratio': self.advance_decline_ratio,
            'breadth_ratio': self.breadth_ratio,
            'up_volume': self.up_volume,
            'down_volume': self.down_volume,
            'up_down_volume_ratio': self.up_down_volume_ratio,
            'volume_ratio': self.volume_ratio,
            'tick': self.tick,
            'trin': self.trin,
            'add': self.add,
            'cumulative_ad_line': self.cumulative_ad_line,
            'breadth_thrust': self.breadth_thrust
        }
        if self.sector_breadth:
            data['sector_breadth'] = self.sector_breadth.to_dict()
        return data


class MarketInternalsCollector:
    """Collects market internals data from various sources"""

    def __init__(self, api_client):
        """
        Initialize market internals collector

        Args:
            api_client: Tradier API client or other market data source
        """
        self.api = api_client
        self.logger = logging.getLogger(__name__)

        # Common market breadth symbols to try
        self.breadth_symbols = {
            'tick': '$TICK',      # NYSE TICK (net upticks vs downticks)
            'add': '$ADD',        # NYSE Advance/Decline
            'trin': '$TRIN',      # NYSE TRIN (Arms Index)
            'advn': '$ADVN',      # NYSE Advances
            'decn': '$DECN',      # NYSE Declines
            'volup': '$UVOL',     # NYSE Up Volume
            'voldn': '$DVOL',     # NYSE Down Volume
        }

        # S&P 500 Sector ETFs (SPDR Select Sector)
        self.sector_etfs = {
            'XLK': 'Technology',
            'XLV': 'Healthcare',
            'XLF': 'Financials',
            'XLE': 'Energy',
            'XLI': 'Industrials',
            'XLC': 'Communication Services',
            'XLY': 'Consumer Discretionary',
            'XLP': 'Consumer Staples',
            'XLRE': 'Real Estate',
            'XLU': 'Utilities',
            'XLB': 'Materials'
        }

    def collect_from_stock_universe(self, symbols: List[str]) -> MarketInternals:
        """
        Calculate market internals from a universe of stocks

        Args:
            symbols: List of stock symbols to analyze (e.g., S&P 500 components)

        Returns:
            MarketInternals data point
        """
        try:
            self.logger.info(f"Collecting market internals from {len(symbols)} stocks")

            # Get current quotes for all symbols
            quotes_df = self.api.get_latest_quotes(symbols, greeks=False)

            if quotes_df.empty:
                self.logger.warning("No quote data received")
                return None

            self.logger.info(f"Received quotes for {len(quotes_df)} stocks")

            # Calculate breadth metrics using change_percentage for better accuracy
            # Filter out NaN values
            quotes_df = quotes_df[quotes_df['change_percentage'].notna()].copy()

            if quotes_df.empty:
                self.logger.warning("No valid quote data with price changes")
                return None

            advances = len(quotes_df[quotes_df['change_percentage'] > 0.01])  # >0.01% threshold
            declines = len(quotes_df[quotes_df['change_percentage'] < -0.01])  # <-0.01% threshold
            unchanged = len(quotes_df) - advances - declines

            total_stocks = advances + declines
            if total_stocks == 0:
                # Market is closed or no movement, still return neutral data
                self.logger.info("No significant price changes (market likely closed)")
                total_stocks = len(quotes_df)
                advance_decline_ratio = 1.0
                breadth_ratio = 0.0
            else:
                advance_decline_ratio = advances / declines if declines > 0 else float('inf')
                breadth_ratio = (advances - declines) / total_stocks

            # Calculate volume metrics
            advancing_stocks = quotes_df[quotes_df['change_percentage'] > 0.01]
            declining_stocks = quotes_df[quotes_df['change_percentage'] < -0.01]

            up_volume = advancing_stocks['volume'].sum()
            down_volume = declining_stocks['volume'].sum()

            total_volume = up_volume + down_volume
            if total_volume == 0:
                # No volume or all volume in unchanged stocks
                self.logger.info("No volume in advancing/declining stocks")
                # Get total volume from all stocks
                total_volume = quotes_df['volume'].sum()
                up_down_volume_ratio = 1.0
                volume_ratio = 0.0
            else:
                up_down_volume_ratio = up_volume / down_volume if down_volume > 0 else float('inf')
                volume_ratio = (up_volume - down_volume) / total_volume

            internals = MarketInternals(
                timestamp=datetime.now(),
                advances=advances,
                declines=declines,
                unchanged=unchanged,
                advance_decline_ratio=advance_decline_ratio,
                breadth_ratio=breadth_ratio,
                up_volume=up_volume,
                down_volume=down_volume,
                up_down_volume_ratio=up_down_volume_ratio,
                volume_ratio=volume_ratio
            )

            self.logger.info(f"Breadth: {advances}↑ {declines}↓ (ratio: {breadth_ratio:.2%})")
            self.logger.info(f"Volume: {up_volume:,.0f}↑ {down_volume:,.0f}↓ (ratio: {volume_ratio:.2%})")

            return internals

        except Exception as e:
            self.logger.error(f"Error collecting market internals: {e}")
            return None

    def collect_from_indices(self) -> Dict[str, float]:
        """
        Attempt to collect market breadth indices

        Returns:
            Dictionary of available breadth indices
        """
        indices = {}

        try:
            # Try to fetch common breadth symbols
            symbols_to_try = list(self.breadth_symbols.values())
            quotes_df = self.api.get_latest_quotes(symbols_to_try, greeks=False)

            if not quotes_df.empty:
                for key, symbol in self.breadth_symbols.items():
                    matching = quotes_df[quotes_df['symbol'] == symbol]
                    if not matching.empty:
                        indices[key] = matching.iloc[0]['last']
                        self.logger.info(f"Retrieved {symbol}: {indices[key]}")

            return indices

        except Exception as e:
            self.logger.warning(f"Unable to fetch breadth indices: {e}")
            return {}

    def collect_sector_breadth(self) -> Optional[SectorBreadth]:
        """
        Collect sector breadth using sector ETF performance

        Calculates percentage change from open for each sector ETF
        to determine sector rotation and breadth

        Returns:
            SectorBreadth object with sector analysis
        """
        try:
            self.logger.info("Collecting sector breadth...")

            # Get quotes for all sector ETFs
            sector_symbols = list(self.sector_etfs.keys())
            quotes_df = self.api.get_latest_quotes(sector_symbols, greeks=False)

            if quotes_df.empty:
                self.logger.warning("No sector ETF data received")
                return None

            # Calculate % change from open for each sector
            sector_performance = {}
            for symbol in sector_symbols:
                sector_data = quotes_df[quotes_df['symbol'] == symbol]
                if not sector_data.empty:
                    row = sector_data.iloc[0]
                    open_price = row.get('open', 0)
                    last_price = row.get('last', 0)

                    if open_price and open_price > 0:
                        pct_change = ((last_price - open_price) / open_price) * 100
                        sector_performance[symbol] = pct_change
                    else:
                        # Use change_percentage if open not available
                        sector_performance[symbol] = row.get('change_percentage', 0)

            if not sector_performance:
                self.logger.warning("No valid sector performance data")
                return None

            # Calculate sector breadth
            sectors_advancing = sum(1 for pct in sector_performance.values() if pct > 0)
            sectors_declining = sum(1 for pct in sector_performance.values() if pct < 0)
            total_sectors = len(sector_performance)

            if total_sectors > 0:
                sector_breadth_ratio = (sectors_advancing - sectors_declining) / total_sectors
            else:
                sector_breadth_ratio = 0.0

            # Find strongest and weakest sectors
            strongest_symbol = max(sector_performance, key=sector_performance.get)
            weakest_symbol = min(sector_performance, key=sector_performance.get)

            strongest_sector = f"{strongest_symbol} ({self.sector_etfs[strongest_symbol]})"
            weakest_sector = f"{weakest_symbol} ({self.sector_etfs[weakest_symbol]})"

            sector_breadth = SectorBreadth(
                timestamp=datetime.now(),
                sectors_advancing=sectors_advancing,
                sectors_declining=sectors_declining,
                sector_breadth_ratio=sector_breadth_ratio,
                strongest_sector=strongest_sector,
                weakest_sector=weakest_sector,
                sector_performance=sector_performance
            )

            self.logger.info(f"Sector Breadth: {sectors_advancing}↑ {sectors_declining}↓ "
                           f"(ratio: {sector_breadth_ratio:.2%})")
            self.logger.info(f"Strongest: {strongest_sector} "
                           f"({sector_performance[strongest_symbol]:+.2f}%)")
            self.logger.info(f"Weakest: {weakest_sector} "
                           f"({sector_performance[weakest_symbol]:+.2f}%)")

            return sector_breadth

        except Exception as e:
            self.logger.error(f"Error collecting sector breadth: {e}")
            return None

    def calculate_cumulative_ad_line(self, current_ad: int, db_connection) -> float:
        """
        Calculate cumulative advance/decline line

        Args:
            current_ad: Current net advances - declines
            db_connection: Database connection to get historical data

        Returns:
            Cumulative A/D line value
        """
        try:
            query = """
            SELECT cumulative_ad_line
            FROM market_internals
            ORDER BY timestamp DESC
            LIMIT 1
            """
            result = pd.read_sql(query, db_connection)

            if not result.empty and result['cumulative_ad_line'].iloc[0]:
                previous_ad_line = result['cumulative_ad_line'].iloc[0]
                return previous_ad_line + current_ad
            else:
                # Initialize at 0 if no previous data
                return float(current_ad)

        except Exception as e:
            self.logger.warning(f"Error calculating cumulative A/D line: {e}")
            return float(current_ad)

    def calculate_breadth_thrust(self, internals_history: pd.DataFrame,
                                 window: int = 10) -> Optional[float]:
        """
        Calculate breadth thrust indicator

        Breadth thrust occurs when advancing issues over a 10-day period
        increase from below 40% to above 61.5%

        Args:
            internals_history: Historical internals data
            window: Rolling window size (default 10 days)

        Returns:
            Current breadth thrust value (0-1)
        """
        try:
            if len(internals_history) < window:
                return None

            # Calculate 10-day EMA of breadth ratio
            breadth_series = internals_history['breadth_ratio'].tail(window)
            ema = breadth_series.ewm(span=window, adjust=False).mean().iloc[-1]

            # Normalize to 0-1 scale (breadth_ratio is -1 to 1)
            normalized = (ema + 1) / 2

            return normalized

        except Exception as e:
            self.logger.error(f"Error calculating breadth thrust: {e}")
            return None


class MarketInternalsSignalGenerator:
    """Generates trading signals from market internals"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def analyze_breadth(self, internals: MarketInternals) -> Tuple[SignalType, float, str]:
        """
        Analyze breadth metrics and generate signal

        Args:
            internals: Current market internals data

        Returns:
            Tuple of (signal_type, confidence, reasoning)
        """
        breadth_ratio = internals.breadth_ratio
        ad_ratio = internals.advance_decline_ratio

        # Strong bullish breadth: >70% advancing
        if breadth_ratio > 0.70:
            return (
                SignalType.STRONG_BUY,
                0.90,
                f"Exceptional breadth: {breadth_ratio:.1%} of stocks advancing. "
                f"A/D ratio: {ad_ratio:.2f}:1"
            )

        # Bullish breadth: >60% advancing
        elif breadth_ratio > 0.60:
            return (
                SignalType.BUY,
                0.75,
                f"Strong breadth: {breadth_ratio:.1%} of stocks advancing. "
                f"A/D ratio: {ad_ratio:.2f}:1"
            )

        # Moderate bullish: >55% advancing
        elif breadth_ratio > 0.20:
            return (
                SignalType.BUY,
                0.60,
                f"Positive breadth: {breadth_ratio:.1%} of stocks advancing. "
                f"A/D ratio: {ad_ratio:.2f}:1"
            )

        # Moderate bearish: <-55% (more declining)
        elif breadth_ratio < -0.20:
            return (
                SignalType.SELL,
                0.60,
                f"Negative breadth: {abs(breadth_ratio):.1%} of stocks declining. "
                f"A/D ratio: {ad_ratio:.2f}:1"
            )

        # Bearish breadth: <-60%
        elif breadth_ratio < -0.60:
            return (
                SignalType.SELL,
                0.75,
                f"Weak breadth: {abs(breadth_ratio):.1%} of stocks declining. "
                f"A/D ratio: {ad_ratio:.2f}:1"
            )

        # Strong bearish: <-70%
        elif breadth_ratio < -0.70:
            return (
                SignalType.STRONG_SELL,
                0.90,
                f"Extremely weak breadth: {abs(breadth_ratio):.1%} of stocks declining. "
                f"A/D ratio: {ad_ratio:.2f}:1"
            )

        # Neutral
        else:
            return (
                SignalType.NEUTRAL,
                0.50,
                f"Mixed breadth: {internals.advances} advancing, {internals.declines} declining"
            )

    def analyze_volume(self, internals: MarketInternals) -> Tuple[SignalType, float, str]:
        """
        Analyze volume metrics and generate signal

        Args:
            internals: Current market internals data

        Returns:
            Tuple of (signal_type, confidence, reasoning)
        """
        volume_ratio = internals.volume_ratio
        uv_dv_ratio = internals.up_down_volume_ratio

        # Very strong up volume: >80%
        if volume_ratio > 0.80:
            return (
                SignalType.STRONG_BUY,
                0.85,
                f"Overwhelming buying pressure: {volume_ratio:.1%} of volume in advancing stocks. "
                f"Up/Down volume: {uv_dv_ratio:.2f}:1"
            )

        # Strong up volume: >65%
        elif volume_ratio > 0.65:
            return (
                SignalType.BUY,
                0.70,
                f"Strong buying pressure: {volume_ratio:.1%} of volume in advancing stocks. "
                f"Up/Down volume: {uv_dv_ratio:.2f}:1"
            )

        # Moderate up volume: >55%
        elif volume_ratio > 0.20:
            return (
                SignalType.BUY,
                0.55,
                f"Positive volume flow: {volume_ratio:.1%} of volume in advancing stocks"
            )

        # Moderate down volume: <-55%
        elif volume_ratio < -0.20:
            return (
                SignalType.SELL,
                0.55,
                f"Negative volume flow: {abs(volume_ratio):.1%} of volume in declining stocks"
            )

        # Strong down volume: <-65%
        elif volume_ratio < -0.65:
            return (
                SignalType.SELL,
                0.70,
                f"Strong selling pressure: {abs(volume_ratio):.1%} of volume in declining stocks. "
                f"Up/Down volume: {uv_dv_ratio:.2f}:1"
            )

        # Very strong down volume: <-80%
        elif volume_ratio < -0.80:
            return (
                SignalType.STRONG_SELL,
                0.85,
                f"Overwhelming selling pressure: {abs(volume_ratio):.1%} of volume in declining stocks. "
                f"Up/Down volume: {uv_dv_ratio:.2f}:1"
            )

        # Neutral
        else:
            return (
                SignalType.NEUTRAL,
                0.50,
                f"Balanced volume: {internals.up_volume:,.0f} up, {internals.down_volume:,.0f} down"
            )

    def analyze_tick(self, tick_value: float) -> Tuple[SignalType, float, str]:
        """
        Analyze NYSE TICK indicator

        TICK measures net upticks vs downticks
        +1000 = very bullish
        -1000 = very bearish

        Args:
            tick_value: Current $TICK value

        Returns:
            Tuple of (signal_type, confidence, reasoning)
        """
        if tick_value > 1000:
            return (
                SignalType.STRONG_BUY,
                0.80,
                f"Extreme bullish momentum: TICK at +{tick_value:.0f}"
            )
        elif tick_value > 600:
            return (
                SignalType.BUY,
                0.70,
                f"Strong bullish momentum: TICK at +{tick_value:.0f}"
            )
        elif tick_value > 200:
            return (
                SignalType.BUY,
                0.60,
                f"Bullish momentum: TICK at +{tick_value:.0f}"
            )
        elif tick_value < -1000:
            return (
                SignalType.STRONG_SELL,
                0.80,
                f"Extreme bearish momentum: TICK at {tick_value:.0f}"
            )
        elif tick_value < -600:
            return (
                SignalType.SELL,
                0.70,
                f"Strong bearish momentum: TICK at {tick_value:.0f}"
            )
        elif tick_value < -200:
            return (
                SignalType.SELL,
                0.60,
                f"Bearish momentum: TICK at {tick_value:.0f}"
            )
        else:
            return (
                SignalType.NEUTRAL,
                0.50,
                f"Neutral momentum: TICK at {tick_value:.0f}"
            )

    def analyze_trin(self, trin_value: float) -> Tuple[SignalType, float, str]:
        """
        Analyze NYSE TRIN (Arms Index)

        TRIN = (Advances/Declines) / (Up Volume/Down Volume)
        < 0.50 = very bullish (low selling pressure)
        > 3.00 = very bearish (high selling pressure)

        Args:
            trin_value: Current $TRIN value

        Returns:
            Tuple of (signal_type, confidence, reasoning)
        """
        if trin_value < 0.50:
            return (
                SignalType.STRONG_BUY,
                0.75,
                f"Very low selling pressure: TRIN at {trin_value:.2f}"
            )
        elif trin_value < 0.80:
            return (
                SignalType.BUY,
                0.65,
                f"Low selling pressure: TRIN at {trin_value:.2f}"
            )
        elif trin_value > 3.00:
            return (
                SignalType.STRONG_SELL,
                0.75,
                f"Very high selling pressure: TRIN at {trin_value:.2f}"
            )
        elif trin_value > 2.00:
            return (
                SignalType.SELL,
                0.65,
                f"High selling pressure: TRIN at {trin_value:.2f}"
            )
        else:
            return (
                SignalType.NEUTRAL,
                0.50,
                f"Normal selling pressure: TRIN at {trin_value:.2f}"
            )

    def analyze_sector_breadth(self, sector_breadth: SectorBreadth) -> Tuple[SignalType, float, str]:
        """
        Analyze sector breadth and generate signal

        Args:
            sector_breadth: SectorBreadth object with sector performance data

        Returns:
            Tuple of (signal_type, confidence, reasoning)
        """
        ratio = sector_breadth.sector_breadth_ratio
        advancing = sector_breadth.sectors_advancing
        declining = sector_breadth.sectors_declining

        # Strong sector rotation to upside
        if ratio > 0.70:  # >8/11 sectors up
            return (
                SignalType.STRONG_BUY,
                0.85,
                f"Exceptional sector rotation: {advancing}/{advancing+declining} sectors advancing. "
                f"Leading: {sector_breadth.strongest_sector}"
            )

        # Good sector breadth
        elif ratio > 0.40:  # >7/11 sectors up
            return (
                SignalType.BUY,
                0.70,
                f"Strong sector breadth: {advancing}/{advancing+declining} sectors advancing. "
                f"Leading: {sector_breadth.strongest_sector}"
            )

        # Moderate positive
        elif ratio > 0.10:  # 6/11 sectors up
            return (
                SignalType.BUY,
                0.60,
                f"Positive sector rotation: {advancing}/{advancing+declining} sectors advancing"
            )

        # Moderate negative
        elif ratio < -0.10:  # Majority declining
            return (
                SignalType.SELL,
                0.60,
                f"Negative sector rotation: {declining}/{advancing+declining} sectors declining"
            )

        # Weak sector breadth
        elif ratio < -0.40:
            return (
                SignalType.SELL,
                0.70,
                f"Weak sector breadth: {declining}/{advancing+declining} sectors declining. "
                f"Lagging: {sector_breadth.weakest_sector}"
            )

        # Very weak
        elif ratio < -0.70:
            return (
                SignalType.STRONG_SELL,
                0.85,
                f"Widespread sector weakness: {declining}/{advancing+declining} sectors declining. "
                f"Lagging: {sector_breadth.weakest_sector}"
            )

        # Neutral
        else:
            return (
                SignalType.NEUTRAL,
                0.50,
                f"Mixed sector performance: {advancing}↑ {declining}↓"
            )

    def generate_composite_signal(self, internals: MarketInternals,
                                  indices: Optional[Dict[str, float]] = None) -> Dict:
        """
        Generate composite signal from all market internals

        Args:
            internals: Current market internals data
            indices: Optional breadth indices (TICK, TRIN, etc.)

        Returns:
            Dictionary with composite signal and analysis
        """
        signals = []

        # Analyze breadth
        breadth_signal, breadth_conf, breadth_reason = self.analyze_breadth(internals)
        signals.append({
            'source': 'Breadth Analysis',
            'signal': breadth_signal.value,
            'confidence': breadth_conf,
            'reasoning': breadth_reason,
            'weight': 0.35  # 35% weight
        })

        # Analyze volume
        volume_signal, volume_conf, volume_reason = self.analyze_volume(internals)
        signals.append({
            'source': 'Volume Analysis',
            'signal': volume_signal.value,
            'confidence': volume_conf,
            'reasoning': volume_reason,
            'weight': 0.30  # 30% weight
        })

        # Analyze TICK if available
        if indices and 'tick' in indices:
            tick_signal, tick_conf, tick_reason = self.analyze_tick(indices['tick'])
            signals.append({
                'source': 'TICK Indicator',
                'signal': tick_signal.value,
                'confidence': tick_conf,
                'reasoning': tick_reason,
                'weight': 0.20  # 20% weight
            })

        # Analyze TRIN if available
        if indices and 'trin' in indices:
            trin_signal, trin_conf, trin_reason = self.analyze_trin(indices['trin'])
            signals.append({
                'source': 'TRIN Indicator',
                'signal': trin_signal.value,
                'confidence': trin_conf,
                'reasoning': trin_reason,
                'weight': 0.15  # 15% weight
            })

        # Analyze Sector Breadth if available
        if internals.sector_breadth:
            sector_signal, sector_conf, sector_reason = self.analyze_sector_breadth(internals.sector_breadth)
            signals.append({
                'source': 'Sector Rotation',
                'signal': sector_signal.value,
                'confidence': sector_conf,
                'reasoning': sector_reason,
                'weight': 0.25  # 25% weight - sectors are important for trend confirmation
            })

        # Calculate weighted composite signal
        total_weight = sum(s['weight'] for s in signals)

        # Normalize weights if we don't have all signals
        for sig in signals:
            sig['normalized_weight'] = sig['weight'] / total_weight

        # Calculate composite score (-1 to +1)
        signal_scores = {
            'STRONG_SELL': -1.0,
            'SELL': -0.5,
            'NEUTRAL': 0.0,
            'BUY': 0.5,
            'STRONG_BUY': 1.0
        }

        composite_score = sum(
            signal_scores[s['signal']] * s['confidence'] * s['normalized_weight']
            for s in signals
        )

        composite_confidence = sum(
            s['confidence'] * s['normalized_weight']
            for s in signals
        )

        # Determine composite signal
        if composite_score > 0.6:
            composite_signal = SignalType.STRONG_BUY.value
        elif composite_score > 0.2:
            composite_signal = SignalType.BUY.value
        elif composite_score < -0.6:
            composite_signal = SignalType.STRONG_SELL.value
        elif composite_score < -0.2:
            composite_signal = SignalType.SELL.value
        else:
            composite_signal = SignalType.NEUTRAL.value

        # Generate recommendation
        if composite_score > 0.6:
            recommendation = (
                f"Strong bullish internals suggest high probability of upside. "
                f"Market breadth and volume confirm broad participation. "
                f"Consider long positions or adding to existing longs."
            )
        elif composite_score > 0.2:
            recommendation = (
                f"Moderately bullish internals support upside bias. "
                f"Look for pullback entries on strong stocks."
            )
        elif composite_score < -0.6:
            recommendation = (
                f"Strong bearish internals suggest high probability of downside. "
                f"Market breadth and volume indicate distribution. "
                f"Consider reducing exposure or hedging positions."
            )
        elif composite_score < -0.2:
            recommendation = (
                f"Moderately bearish internals support downside bias. "
                f"Avoid chasing rallies, wait for confirmation."
            )
        else:
            recommendation = (
                f"Mixed internals provide no clear directional bias. "
                f"Wait for confirmation from breadth and volume before taking new positions."
            )

        return {
            'timestamp': internals.timestamp,
            'market_internals': internals.to_dict(),
            'breadth_indices': indices or {},
            'individual_signals': signals,
            'composite_signal': composite_signal,
            'composite_score': composite_score,
            'composite_confidence': composite_confidence,
            'recommendation': recommendation
        }
