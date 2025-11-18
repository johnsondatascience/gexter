#!/usr/bin/env python3
"""
Generate Trading Signals

Runs the trading signal generator and outputs actionable signals
based on GEX positioning and technical analysis.
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

import psycopg2
from dotenv import load_dotenv
from src.signals.trading_signals import TradingSignalGenerator


def main():
    """Generate and display trading signals"""
    load_dotenv()

    print("=" * 80)
    print("SPX TRADING SIGNALS GENERATOR")
    print("=" * 80)
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    try:
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

        if 'error' in signals:
            print(f"❌ Error: {signals['error']}")
            sys.exit(1)

        # Display results
        print("=" * 80)
        print("📊 MARKET OVERVIEW")
        print("=" * 80)
        print(f"Timestamp: {signals['timestamp']}")
        print(f"SPX Price: {signals['current_price']:.2f}")
        zero_gex_str = f"{signals['zero_gex_level']:.2f}" if signals['zero_gex_level'] else "N/A"
        print(f"Zero GEX Level: {zero_gex_str}")
        print(f"Net GEX at Price: {signals['net_gex_at_price']:,.0f}")

        print("\n" + "=" * 80)
        print("🎯 KEY LEVELS")
        print("=" * 80)
        if signals['gex_levels']['resistance']:
            print("Resistance (Call Walls):")
            for level in signals['gex_levels']['resistance']:
                print(f"  • {level:.0f}")
        if signals['gex_levels']['support']:
            print("\nSupport (Put Walls):")
            for level in signals['gex_levels']['support']:
                print(f"  • {level:.0f}")

        print("\n" + "=" * 80)
        print("📡 INDIVIDUAL SIGNALS")
        print("=" * 80)
        for sig in signals['individual_signals']:
            emoji = "🟢" if "BUY" in sig['signal'] else "🔴" if "SELL" in sig['signal'] else "⚪"
            print(f"\n{emoji} {sig['source']}")
            print(f"   Signal: {sig['signal']}")
            print(f"   Confidence: {sig['confidence']:.0%}")
            print(f"   {sig['reasoning']}")

        print("\n" + "=" * 80)
        print("🎲 COMPOSITE SIGNAL")
        print("=" * 80)
        print(f"Signal: {signals['composite_signal']}")
        print(f"Confidence: {signals['composite_confidence']:.0%}")

        print("\n" + "=" * 80)
        print("💡 RECOMMENDATION")
        print("=" * 80)
        print(signals['recommendation'])

        # Save to JSON
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'trading_signals.json')

        # Convert timestamp to string for JSON serialization
        signals_copy = signals.copy()
        signals_copy['timestamp'] = str(signals['timestamp'])

        with open(output_file, 'w') as f:
            json.dump(signals_copy, f, indent=2)

        print(f"\n💾 Signals saved to: {output_file}")

        conn.close()

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n❌ Error generating signals: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
