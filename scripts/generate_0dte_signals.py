#!/usr/bin/env python3
"""
Generate 0DTE-Focused Trading Signals

Generates multi-timeframe GEX signals with emphasis on same-day expiration (0DTE)
for intraday scalping and short-term trading strategies.
"""

import sys
import os
import json
from datetime import datetime

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from dotenv import load_dotenv
from src.signals.trading_signals import TradingSignalGenerator


def format_signal_output(timeframe: str, signals: dict) -> str:
    """Format signal data for display"""
    if 'error' in signals:
        return f"❌ Error: {signals['error']}"

    lines = []
    lines.append(f"Signal: {signals['composite_signal']}")
    lines.append(f"Confidence: {signals['composite_confidence']:.0%}")
    lines.append(f"Options Count: {signals['options_count']:,}")

    if signals['zero_gex_level']:
        lines.append(f"Zero GEX: ${signals['zero_gex_level']:.2f}")
        regime = "Positive Gamma" if signals['current_price'] > signals['zero_gex_level'] else "Negative Gamma"
        lines.append(f"Regime: {regime}")
    else:
        lines.append("Zero GEX: N/A")

    if signals['gex_levels']['resistance']:
        resistance_str = ', '.join(f"${x:.0f}" for x in signals['gex_levels']['resistance'])
        lines.append(f"Resistance: {resistance_str}")

    if signals['gex_levels']['support']:
        support_str = ', '.join(f"${x:.0f}" for x in signals['gex_levels']['support'])
        lines.append(f"Support: {support_str}")

    lines.append(f"Reasoning: {signals['reasoning']}")

    return '\n  '.join(lines)


def main():
    """Generate and display 0DTE-focused signals"""
    load_dotenv()

    print("=" * 80)
    print("0DTE-FOCUSED TRADING SIGNALS GENERATOR")
    print("Multi-Timeframe GEX Analysis")
    print("=" * 80)
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    try:
        # Connect to database using SQLAlchemy
        db_url = (
            f"postgresql://{os.getenv('POSTGRES_USER', 'gexuser')}:"
            f"{os.getenv('POSTGRES_PASSWORD')}@"
            f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
            f"{os.getenv('POSTGRES_PORT', 5432)}/"
            f"{os.getenv('POSTGRES_DB', 'gexdb')}"
        )
        engine = create_engine(db_url)
        print("✓ Connected to PostgreSQL database\n")

        # Generate multi-timeframe signals
        print("=" * 80)
        print("📊 GENERATING MULTI-TIMEFRAME GEX SIGNALS")
        print("=" * 80)

        gex_generator = TradingSignalGenerator(engine)
        all_signals = gex_generator.generate_multi_timeframe_signals()

        # Display current price
        print(f"\n💰 Current SPX Price: ${all_signals['current_price']:.2f}\n")

        # Display 0DTE signals (PRIMARY FOCUS)
        print("=" * 80)
        print("🎯 0DTE SIGNALS (Same-Day Expiration) - PRIMARY FOCUS")
        print("=" * 80)
        print(format_signal_output("0DTE", all_signals['0dte']))
        print()

        # Display short-term signals
        print("=" * 80)
        print("📈 SHORT-TERM SIGNALS (0-2 Days) - Swing Trades")
        print("=" * 80)
        print(format_signal_output("SHORT-TERM", all_signals['short_term']))
        print()

        # Display weekly signals
        print("=" * 80)
        print("📅 WEEKLY SIGNALS (0-7 Days) - Weekly Positioning")
        print("=" * 80)
        print(format_signal_output("WEEKLY", all_signals['weekly']))
        print()

        # Display all expirations (context)
        print("=" * 80)
        print("🌐 ALL EXPIRATIONS - Full Market Context")
        print("=" * 80)
        print(format_signal_output("ALL", all_signals['all']))
        print()

        # Trading recommendations by timeframe
        print("=" * 80)
        print("💡 TRADING RECOMMENDATIONS")
        print("=" * 80)

        dte_0 = all_signals['0dte']
        dte_short = all_signals['short_term']

        print("\n🎯 0DTE Trading (Intraday Scalping):")
        if 'error' not in dte_0:
            if dte_0['composite_signal'] in ['STRONG_BUY', 'BUY']:
                print("  → Look for LONG entries near support levels")
                if dte_0['gex_levels']['support']:
                    print(f"  → Entry zones: {', '.join(f'${x:.0f}' for x in dte_0['gex_levels']['support'])}")
                if dte_0['gex_levels']['resistance']:
                    print(f"  → Profit targets: {', '.join(f'${x:.0f}' for x in dte_0['gex_levels']['resistance'][:2])}")
            elif dte_0['composite_signal'] in ['STRONG_SELL', 'SELL']:
                print("  → Look for SHORT entries near resistance levels")
                if dte_0['gex_levels']['resistance']:
                    print(f"  → Entry zones: {', '.join(f'${x:.0f}' for x in dte_0['gex_levels']['resistance'])}")
                if dte_0['gex_levels']['support']:
                    print(f"  → Profit targets: {', '.join(f'${x:.0f}' for x in dte_0['gex_levels']['support'][:2])}")
            else:
                print("  → NEUTRAL - Wait for clearer setup or trade the range")
                if dte_0['gex_levels']['support'] and dte_0['gex_levels']['resistance']:
                    print(f"  → Range: ${dte_0['gex_levels']['support'][0]:.0f} - ${dte_0['gex_levels']['resistance'][0]:.0f}")
        else:
            print(f"  → {dte_0['error']}")

        print("\n📈 Short-Term Trading (0-2 Days):")
        if 'error' not in dte_short:
            if dte_short['composite_signal'] in ['STRONG_BUY', 'BUY']:
                print("  → Bullish bias - Consider overnight long positions")
            elif dte_short['composite_signal'] in ['STRONG_SELL', 'SELL']:
                print("  → Bearish bias - Consider overnight short positions")
            else:
                print("  → NEUTRAL - Avoid overnight risk, focus on intraday")
        else:
            print(f"  → {dte_short['error']}")

        # Signal comparison
        print("\n🔍 Signal Alignment Analysis:")
        if 'error' not in dte_0 and 'error' not in all_signals['all']:
            dte_0_signal = dte_0['composite_signal']
            all_signal = all_signals['all']['composite_signal']

            if dte_0_signal == all_signal:
                print(f"  ✅ STRONG ALIGNMENT: 0DTE and ALL timeframes agree ({dte_0_signal})")
                print("  → High conviction setup - Consider larger position size")
            else:
                print(f"  ⚠️ DIVERGENCE: 0DTE={dte_0_signal}, ALL={all_signal}")
                print("  → Mixed signals - Use caution, reduce position size")
                print("  → 0DTE may be setting up for reversal or short-term move")

        # Save to JSON
        import numpy as np

        def convert_to_serializable(obj):
            """Convert numpy/pandas types to native Python types"""
            if isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            elif isinstance(obj, (np.int64, np.int32)):
                return int(obj)
            elif isinstance(obj, (np.float64, np.float32)):
                return float(obj)
            elif isinstance(obj, datetime):
                return str(obj)
            elif obj is None or isinstance(obj, (str, int, float, bool)):
                return obj
            else:
                return str(obj)

        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, '0dte_signals.json')

        output_data = convert_to_serializable(all_signals)

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"\n💾 0DTE signals saved to: {output_file}")

        engine.dispose()

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
