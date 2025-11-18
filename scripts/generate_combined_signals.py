#!/usr/bin/env python3
"""
Generate Combined Trading Signals

Combines GEX (Gamma Exposure) signals with Market Internals
to provide comprehensive trading analysis with high-conviction setups.
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
from src.api.tradier_api import TradierAPI
from src.signals.trading_signals import TradingSignalGenerator
from src.signals.market_internals import MarketInternalsCollector, MarketInternalsSignalGenerator
from src.signals.combined_signals import CombinedSignalGenerator


# Default watchlist for internals
DEFAULT_WATCHLIST = [
    'AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'AMD', 'AVGO', 'ORCL', 'CSCO', 'ADBE',
    'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'USB',
    'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'PFE', 'BMY',
    'AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'LOW', 'TJX', 'DG',
    'BA', 'CAT', 'HON', 'UNP', 'RTX', 'LMT', 'DE', 'GE', 'MMM', 'UPS',
    'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'MPC', 'PSX', 'VLO', 'OXY', 'HES',
    'LIN', 'APD', 'SHW', 'ECL', 'NEM', 'FCX', 'NUE', 'DD', 'DOW', 'PPG',
    'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE', 'XEL', 'ED', 'PEG',
    'TMUS', 'VZ', 'T', 'NFLX', 'DIS', 'CMCSA', 'CHTR', 'EA', 'TTWO', 'ATVI',
    'PLD', 'AMT', 'CCI', 'EQIX', 'PSA', 'WELL', 'DLR', 'SPG', 'O', 'VICI'
]


def main():
    """Generate and display combined trading signals"""
    load_dotenv()

    print("=" * 80)
    print("COMBINED TRADING SIGNALS GENERATOR")
    print("GEX Positioning + Market Internals")
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
        print("✓ Connected to PostgreSQL database\n")

        # Initialize API
        api_key = os.getenv('TRADIER_API_KEY')
        api = TradierAPI(api_key)

        # Step 1: Generate GEX Signals
        print("=" * 80)
        print("📊 STEP 1: GENERATING GEX SIGNALS")
        print("=" * 80)
        gex_generator = TradingSignalGenerator(conn)
        gex_signals = gex_generator.generate_comprehensive_signals()

        if 'error' in gex_signals:
            print(f"❌ Error generating GEX signals: {gex_signals['error']}")
            sys.exit(1)

        print(f"✓ GEX Signal: {gex_signals['composite_signal']}")
        print(f"✓ Confidence: {gex_signals['composite_confidence']:.0%}")
        print(f"✓ SPX Price: ${gex_signals['current_price']:.2f}")
        print(f"✓ Zero GEX: ${gex_signals['zero_gex_level']:.2f}" if gex_signals['zero_gex_level'] else "✓ Zero GEX: N/A")

        # Step 2: Generate Market Internals Signals
        print("\n" + "=" * 80)
        print("📊 STEP 2: GENERATING MARKET INTERNALS SIGNALS")
        print("=" * 80)

        internals_collector = MarketInternalsCollector(api)
        internals = internals_collector.collect_from_stock_universe(DEFAULT_WATCHLIST)

        if not internals:
            print("❌ Failed to collect market internals")
            sys.exit(1)

        # Collect sector breadth
        sector_breadth = internals_collector.collect_sector_breadth()
        if sector_breadth:
            internals.sector_breadth = sector_breadth

        # Try to get breadth indices
        indices = internals_collector.collect_from_indices()

        internals_sig_generator = MarketInternalsSignalGenerator()
        internals_signals = internals_sig_generator.generate_composite_signal(internals, indices)

        print(f"✓ Internals Signal: {internals_signals['composite_signal']}")
        print(f"✓ Confidence: {internals_signals['composite_confidence']:.0%}")
        print(f"✓ Breadth Ratio: {internals.breadth_ratio:+.1%}")
        print(f"✓ Volume Ratio: {internals.volume_ratio:+.1%}")
        if internals.sector_breadth:
            print(f"✓ Sector Breadth: {internals.sector_breadth.sector_breadth_ratio:+.1%}")

        # Step 3: Generate Combined Signals
        print("\n" + "=" * 80)
        print("🎯 STEP 3: COMBINING SIGNALS")
        print("=" * 80)

        combined_generator = CombinedSignalGenerator()
        combined_signals = combined_generator.generate_combined_signal(gex_signals, internals_signals)

        # Display Combined Results
        print("\n" + "=" * 80)
        print("🎲 COMBINED SIGNAL ANALYSIS")
        print("=" * 80)
        print(f"\nFinal Signal: {combined_signals['combined_signal']}")
        print(f"Combined Score: {combined_signals['combined_score']:+.2f} (range: -1 to +1)")
        print(f"Conviction Level: {combined_signals['conviction_level']}")
        print(f"  → {combined_signals['conviction_description']}")
        print(f"Signal Alignment: {combined_signals['alignment_score']:+.2f} (range: -1 to +1)")

        print("\n" + "-" * 80)
        print("Component Signals:")
        print(f"  GEX Positioning ({combined_signals['component_signals']['gex']['weight']:.0%} weight):")
        print(f"    Signal: {combined_signals['component_signals']['gex']['signal']}")
        print(f"    Confidence: {combined_signals['component_signals']['gex']['confidence']:.0%}")

        print(f"  Market Internals ({combined_signals['component_signals']['internals']['weight']:.0%} weight):")
        print(f"    Signal: {combined_signals['component_signals']['internals']['signal']}")
        print(f"    Confidence: {combined_signals['component_signals']['internals']['confidence']:.0%}")

        # Display Key Levels
        print("\n" + "-" * 80)
        print("Key Levels:")
        print(f"  Current SPX: ${combined_signals['key_levels']['current_price']:.2f}")
        if combined_signals['key_levels']['zero_gex']:
            print(f"  Zero GEX: ${combined_signals['key_levels']['zero_gex']:.2f}")
            regime = "Positive Gamma (Lower Vol)" if combined_signals['key_levels']['current_price'] > combined_signals['key_levels']['zero_gex'] else "Negative Gamma (Higher Vol)"
            print(f"  Regime: {regime}")

        if combined_signals['key_levels']['resistance_levels']:
            print(f"  Resistance (Call Walls):")
            for level in combined_signals['key_levels']['resistance_levels']:
                print(f"    • ${level:.0f}")

        if combined_signals['key_levels']['support_levels']:
            print(f"  Support (Put Walls):")
            for level in combined_signals['key_levels']['support_levels']:
                print(f"    • ${level:.0f}")

        # Display Internals Summary
        print("\n" + "-" * 80)
        print("Internals Summary:")
        print(f"  Breadth Ratio: {combined_signals['internals_summary']['breadth_ratio']:+.1%}")
        print(f"  Volume Ratio: {combined_signals['internals_summary']['volume_ratio']:+.1%}")

        if combined_signals['internals_summary']['sector_breadth']:
            sb = combined_signals['internals_summary']['sector_breadth']
            print(f"  Sector Breadth: {sb['sector_breadth_ratio']:+.1%}")
            print(f"  Strongest Sector: {sb['strongest_sector']}")
            print(f"  Weakest Sector: {sb['weakest_sector']}")

        # Display Recommendation
        print("\n" + "=" * 80)
        print("💡 TRADING RECOMMENDATION")
        print("=" * 80)
        print(combined_signals['recommendation'])

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
        output_file = os.path.join(output_dir, 'combined_signals.json')

        output_data = convert_to_serializable(combined_signals)

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"\n💾 Combined signals saved to: {output_file}")

        conn.close()

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
