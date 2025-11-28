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

from sqlalchemy import create_engine
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

        # Initialize API
        api_key = os.getenv('TRADIER_API_KEY')
        api = TradierAPI(api_key)

        # Step 1: Generate Multi-Timeframe GEX Signals
        print("=" * 80)
        print("📊 STEP 1: GENERATING MULTI-TIMEFRAME GEX SIGNALS")
        print("=" * 80)
        gex_generator = TradingSignalGenerator(engine)

        # Generate 0DTE-focused multi-timeframe signals
        multiframe_signals = gex_generator.generate_multi_timeframe_signals()

        # Also generate comprehensive signals for backward compatibility
        gex_signals = gex_generator.generate_comprehensive_signals()

        if 'error' in gex_signals:
            print(f"❌ Error generating GEX signals: {gex_signals['error']}")
            sys.exit(1)

        # Display 0DTE signals
        print("\n🎯 0DTE Signals (Same-Day Expiration):")
        if 'error' not in multiframe_signals['0dte']:
            dte_0 = multiframe_signals['0dte']
            print(f"  Signal: {dte_0['composite_signal']} (Confidence: {dte_0['composite_confidence']:.0%})")
            print(f"  Options: {dte_0['options_count']:,} | Zero GEX: ${dte_0['zero_gex_level']:.2f}" if dte_0['zero_gex_level'] else f"  Options: {dte_0['options_count']:,}")
            if dte_0['gex_levels']['resistance']:
                print(f"  Resistance: {', '.join(f'${x:.0f}' for x in dte_0['gex_levels']['resistance'][:2])}")
            if dte_0['gex_levels']['support']:
                print(f"  Support: {', '.join(f'${x:.0f}' for x in dte_0['gex_levels']['support'][:2])}")
        else:
            print(f"  ❌ {multiframe_signals['0dte']['error']}")

        # Display short-term signals
        print("\n📈 Short-Term Signals (0-2 Days):")
        if 'error' not in multiframe_signals['short_term']:
            dte_short = multiframe_signals['short_term']
            print(f"  Signal: {dte_short['composite_signal']} (Confidence: {dte_short['composite_confidence']:.0%})")
            print(f"  Options: {dte_short['options_count']:,}")
        else:
            print(f"  ❌ {multiframe_signals['short_term']['error']}")

        # Display all expirations (comprehensive)
        print("\n🌐 All Expirations (Full Context):")
        print(f"  Signal: {gex_signals['composite_signal']}")
        print(f"  Confidence: {gex_signals['composite_confidence']:.0%}")
        print(f"  SPX Price: ${gex_signals['current_price']:.2f}")
        print(f"  Zero GEX: ${gex_signals['zero_gex_level']:.2f}" if gex_signals['zero_gex_level'] else "  Zero GEX: N/A")

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

        # Signal Divergence Analysis
        print("\n" + "=" * 80)
        print("🔍 SIGNAL DIVERGENCE ANALYSIS")
        print("=" * 80)

        if 'error' not in multiframe_signals['0dte']:
            dte_0_signal = multiframe_signals['0dte']['composite_signal']
            combined_signal = combined_signals['combined_signal']

            if dte_0_signal == combined_signal:
                print(f"✅ ALIGNMENT: 0DTE and Combined signals agree ({dte_0_signal})")
                print("   → High conviction setup across all timeframes")
                print("   → Consider standard position sizing")
            else:
                print(f"⚠️ DIVERGENCE: 0DTE={dte_0_signal}, Combined={combined_signal}")
                print("   → Mixed signals across timeframes")
                print("   → Reduce position size or wait for alignment")

                # Explain the divergence
                if 'BUY' in dte_0_signal and 'SELL' in combined_signal:
                    print("   → 0DTE showing intraday bullish pressure")
                    print("   → Longer-term structure bearish - caution on holding overnight")
                elif 'SELL' in dte_0_signal and 'BUY' in combined_signal:
                    print("   → 0DTE showing intraday bearish pressure")
                    print("   → Longer-term structure bullish - may be short-term dip")
                elif 'NEUTRAL' in dte_0_signal or 'NEUTRAL' in combined_signal:
                    print("   → One timeframe neutral - wait for clearer setup")

            # Compare with all expirations GEX
            all_gex_signal = gex_signals['composite_signal']
            if dte_0_signal != all_gex_signal:
                print(f"\n📊 0DTE vs All Expirations GEX: {dte_0_signal} vs {all_gex_signal}")
                print(f"   → 0DTE has {multiframe_signals['0dte']['options_count']:,} options ({multiframe_signals['0dte']['options_count']/multiframe_signals['all']['options_count']*100:.1f}% of total)")
                print("   → Consider that longer-dated options may be dominating the full picture")
        else:
            print(f"⚠️ 0DTE signals unavailable: {multiframe_signals['0dte']['error']}")

        # Display Recommendation
        print("\n" + "=" * 80)
        print("💡 TRADING RECOMMENDATION")
        print("=" * 80)
        print(combined_signals['recommendation'])

        # Add 0DTE-specific recommendation if available
        if 'error' not in multiframe_signals['0dte']:
            print("\n🎯 0DTE Intraday Focus:")
            dte_0 = multiframe_signals['0dte']
            if 'BUY' in dte_0['composite_signal']:
                print("   → Look for LONG entries near support levels")
                if dte_0['gex_levels']['support']:
                    print(f"   → Entry zones: {', '.join(f'${x:.0f}' for x in dte_0['gex_levels']['support'][:2])}")
            elif 'SELL' in dte_0['composite_signal']:
                print("   → Look for SHORT entries near resistance levels")
                if dte_0['gex_levels']['resistance']:
                    print(f"   → Entry zones: {', '.join(f'${x:.0f}' for x in dte_0['gex_levels']['resistance'][:2])}")
            else:
                print("   → NEUTRAL - Trade the range or wait for clearer setup")

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

        # Create comprehensive output with both multi-timeframe and combined signals
        output_data = {
            'generated_at': datetime.now().isoformat(),
            'multi_timeframe_gex': convert_to_serializable(multiframe_signals),
            'combined_signals': convert_to_serializable(combined_signals)
        }

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"\n💾 Combined signals saved to: {output_file}")

        engine.dispose()

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
