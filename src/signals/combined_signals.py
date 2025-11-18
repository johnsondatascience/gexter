#!/usr/bin/env python3
"""
Combined Signal Generator

Merges GEX (Gamma Exposure) signals with Market Internals signals
to generate high-conviction trading signals with comprehensive context.
"""

from typing import Dict, Optional
from enum import Enum
import logging


class ConvictionLevel(Enum):
    """Combined signal conviction levels"""
    VERY_HIGH = "VERY_HIGH"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    CONFLICTING = "CONFLICTING"


class CombinedSignalGenerator:
    """Combines GEX and Market Internals signals for unified analysis"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Signal alignment scoring
        self.signal_map = {
            'STRONG_BUY': 1.0,
            'BUY': 0.5,
            'NEUTRAL': 0.0,
            'SELL': -0.5,
            'STRONG_SELL': -1.0
        }

    def calculate_signal_alignment(self, gex_signal: str, internals_signal: str) -> float:
        """
        Calculate alignment between GEX and internals signals

        Args:
            gex_signal: GEX composite signal
            internals_signal: Market internals composite signal

        Returns:
            Alignment score from -1 (opposing) to 1 (perfect alignment)
        """
        gex_score = self.signal_map.get(gex_signal, 0)
        internals_score = self.signal_map.get(internals_signal, 0)

        # Perfect alignment = 1.0, Opposite signals = -1.0
        if gex_score == 0 or internals_score == 0:
            return 0.5  # One neutral signal = moderate alignment
        elif (gex_score > 0 and internals_score > 0) or (gex_score < 0 and internals_score < 0):
            return abs(gex_score * internals_score)  # Same direction
        else:
            return -abs(gex_score * internals_score)  # Opposite directions

    def generate_combined_signal(self, gex_signals: Dict, internals_signals: Dict) -> Dict:
        """
        Generate combined signal from GEX and market internals

        Args:
            gex_signals: GEX trading signals output
            internals_signals: Market internals signals output

        Returns:
            Dictionary with combined analysis and recommendations
        """
        try:
            # Extract key signals
            gex_signal = gex_signals['composite_signal']
            gex_confidence = gex_signals['composite_confidence']
            gex_price = gex_signals['current_price']
            zero_gex = gex_signals['zero_gex_level']

            internals_signal = internals_signals['composite_signal']
            internals_confidence = internals_signals['composite_confidence']
            internals_score = internals_signals['composite_score']

            # Calculate alignment
            alignment = self.calculate_signal_alignment(gex_signal, internals_signal)

            # Determine conviction level
            if alignment > 0.7 and gex_confidence > 0.65 and internals_confidence > 0.65:
                conviction = ConvictionLevel.VERY_HIGH
                conviction_description = "Very High - GEX and internals strongly aligned"
            elif alignment > 0.5 and gex_confidence > 0.55 and internals_confidence > 0.55:
                conviction = ConvictionLevel.HIGH
                conviction_description = "High - GEX and internals aligned"
            elif alignment > 0.2:
                conviction = ConvictionLevel.MODERATE
                conviction_description = "Moderate - Some alignment between signals"
            elif alignment < -0.3:
                conviction = ConvictionLevel.CONFLICTING
                conviction_description = "Conflicting - GEX and internals disagree"
            else:
                conviction = ConvictionLevel.LOW
                conviction_description = "Low - Weak or mixed signals"

            # Generate combined score (weighted average)
            # GEX gets 55% weight, Internals gets 45% weight
            gex_score = self.signal_map.get(gex_signal, 0) * gex_confidence
            combined_score = (gex_score * 0.55) + (internals_score * 0.45)

            # Determine final signal
            if combined_score > 0.6:
                final_signal = "STRONG_BUY"
            elif combined_score > 0.2:
                final_signal = "BUY"
            elif combined_score < -0.6:
                final_signal = "STRONG_SELL"
            elif combined_score < -0.2:
                final_signal = "SELL"
            else:
                final_signal = "NEUTRAL"

            # Generate scenario-based recommendation
            recommendation = self._generate_scenario_recommendation(
                gex_signal, internals_signal, gex_price, zero_gex,
                internals_signals, alignment, conviction
            )

            # Compile key levels from GEX
            key_levels = {
                'zero_gex': zero_gex,
                'current_price': gex_price,
                'resistance_levels': gex_signals['gex_levels']['resistance'][:3] if gex_signals['gex_levels']['resistance'] else [],
                'support_levels': gex_signals['gex_levels']['support'][:3] if gex_signals['gex_levels']['support'] else [],
            }

            # Compile internals summary
            internals_summary = {
                'breadth_ratio': internals_signals['market_internals']['breadth_ratio'],
                'volume_ratio': internals_signals['market_internals']['volume_ratio'],
                'sector_breadth': internals_signals['market_internals'].get('sector_breadth', {})
            }

            return {
                'timestamp': gex_signals['timestamp'],
                'combined_signal': final_signal,
                'combined_score': combined_score,
                'conviction_level': conviction.value,
                'conviction_description': conviction_description,
                'alignment_score': alignment,
                'component_signals': {
                    'gex': {
                        'signal': gex_signal,
                        'confidence': gex_confidence,
                        'weight': 0.55
                    },
                    'internals': {
                        'signal': internals_signal,
                        'confidence': internals_confidence,
                        'score': internals_score,
                        'weight': 0.45
                    }
                },
                'key_levels': key_levels,
                'internals_summary': internals_summary,
                'recommendation': recommendation,
                'gex_signals': gex_signals,  # Full GEX signals
                'internals_signals': internals_signals  # Full internals signals
            }

        except Exception as e:
            self.logger.error(f"Error generating combined signal: {e}")
            return {
                'error': str(e),
                'combined_signal': 'ERROR',
                'recommendation': 'Unable to generate combined signal due to error'
            }

    def _generate_scenario_recommendation(self, gex_signal: str, internals_signal: str,
                                         price: float, zero_gex: Optional[float],
                                         internals_signals: Dict, alignment: float,
                                         conviction: ConvictionLevel) -> str:
        """
        Generate scenario-specific trading recommendation

        Args:
            gex_signal: GEX signal
            internals_signal: Internals signal
            price: Current SPX price
            zero_gex: Zero GEX level
            internals_signals: Full internals signal data
            alignment: Signal alignment score
            conviction: Conviction level

        Returns:
            Detailed trading recommendation
        """
        breadth_ratio = internals_signals['market_internals']['breadth_ratio']
        volume_ratio = internals_signals['market_internals']['volume_ratio']

        # Get sector breadth if available
        sector_info = ""
        if internals_signals['market_internals'].get('sector_breadth'):
            sb = internals_signals['market_internals']['sector_breadth']
            sector_info = f" Sector rotation: {sb['sectors_advancing']}/{sb['sectors_advancing'] + sb['sectors_declining']} sectors advancing."

        # Scenario 1: Bullish Confluence (both signals bullish)
        if "BUY" in gex_signal and "BUY" in internals_signal:
            if zero_gex and price > zero_gex:
                return (
                    f"🚀 BULLISH CONFLUENCE: Both GEX positioning and market internals support upside. "
                    f"Price is above Zero GEX ({price:.0f} > {zero_gex:.0f}), indicating positive gamma regime. "
                    f"Strong breadth ({breadth_ratio:+.1%}) and volume flow ({volume_ratio:+.1%}) confirm broad participation.{sector_info} "
                    f"Conviction: {conviction.value}. "
                    f"STRATEGY: Aggressive long positioning. Use dips to add. Trail stops."
                )
            else:
                return (
                    f"📈 BULLISH SETUP: GEX and internals aligned bullish. "
                    f"Breadth ({breadth_ratio:+.1%}) and volume ({volume_ratio:+.1%}) supporting.{sector_info} "
                    f"Conviction: {conviction.value}. "
                    f"STRATEGY: Build long positions on pullbacks. Watch key resistance levels."
                )

        # Scenario 2: Bearish Confluence (both signals bearish)
        elif "SELL" in gex_signal and "SELL" in internals_signal:
            if zero_gex and price < zero_gex:
                return (
                    f"📉 BEARISH CONFLUENCE: GEX and internals both negative. "
                    f"Price below Zero GEX ({price:.0f} < {zero_gex:.0f}) indicates negative gamma regime (higher volatility). "
                    f"Weak breadth ({breadth_ratio:+.1%}) and negative volume flow ({volume_ratio:+.1%}) confirm distribution.{sector_info} "
                    f"Conviction: {conviction.value}. "
                    f"STRATEGY: Reduce long exposure. Consider hedges. Avoid catching falling knives."
                )
            else:
                return (
                    f"⚠️ BEARISH SETUP: GEX and internals showing weakness. "
                    f"Breadth ({breadth_ratio:+.1%}) and volume ({volume_ratio:+.1%}) deteriorating.{sector_info} "
                    f"Conviction: {conviction.value}. "
                    f"STRATEGY: Tighten stops. Take profits. Wait for confirmation before new longs."
                )

        # Scenario 3: Bullish GEX, Weak Internals (divergence warning)
        elif "BUY" in gex_signal and internals_signal in ["SELL", "STRONG_SELL"]:
            return (
                f"🔶 DIVERGENCE WARNING: GEX shows bullish positioning but market internals are weak. "
                f"Breadth ({breadth_ratio:+.1%}) and volume ({volume_ratio:+.1%}) not confirming price action.{sector_info} "
                f"This suggests narrow market leadership or potential false breakout. "
                f"Conviction: {conviction.value}. "
                f"STRATEGY: Stay cautious. Avoid chasing. Wait for internal improvement or use tight stops."
            )

        # Scenario 4: Bearish GEX, Strong Internals (potential reversal setup)
        elif "SELL" in gex_signal and "BUY" in internals_signal:
            return (
                f"🔄 REVERSAL POTENTIAL: GEX bearish but internals improving. "
                f"Breadth ({breadth_ratio:+.1%}) and volume ({volume_ratio:+.1%}) showing strength.{sector_info} "
                f"Could indicate capitulation bottom or sector rotation. "
                f"Conviction: {conviction.value}. "
                f"STRATEGY: Watch for GEX confirmation. Scaled entries on strength. Be patient."
            )

        # Scenario 5: Mixed/Neutral
        else:
            regime = "positive gamma (lower volatility)" if zero_gex and price > zero_gex else "negative gamma (higher volatility)" if zero_gex else "unclear"
            return (
                f"⚪ MIXED SIGNALS: No clear directional consensus between GEX and internals. "
                f"Gamma regime: {regime}. "
                f"Breadth: {breadth_ratio:+.1%}, Volume: {volume_ratio:+.1%}.{sector_info} "
                f"Conviction: {conviction.value}. "
                f"STRATEGY: Wait for clearer setup. Focus on risk management. Avoid large directional bets."
            )
