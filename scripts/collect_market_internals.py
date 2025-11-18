#!/usr/bin/env python3
"""
Market Internals Collector

Collects market breadth and volume data, stores in database,
and generates trading signals based on market internals.
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
import pandas as pd
from dotenv import load_dotenv
from src.api.tradier_api import TradierAPI
from src.signals.market_internals import MarketInternalsCollector, MarketInternalsSignalGenerator


# Sample watchlist of liquid stocks across sectors
# In production, you'd want to use full S&P 500 or broader universe
DEFAULT_WATCHLIST = [
    # Technology
    'AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'AMD', 'AVGO', 'ORCL', 'CSCO', 'ADBE',
    'CRM', 'INTC', 'QCOM', 'TXN', 'NOW', 'INTU', 'AMAT', 'MU', 'LRCX', 'KLAC',

    # Financials
    'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'USB',
    'PNC', 'TFC', 'COF', 'BK', 'STT', 'CME', 'ICE', 'SPGI', 'MCO', 'AON',

    # Healthcare
    'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'PFE', 'BMY',
    'AMGN', 'GILD', 'CVS', 'CI', 'ISRG', 'REGN', 'VRTX', 'ZTS', 'SYK', 'BSX',

    # Consumer
    'AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'LOW', 'TJX', 'DG',
    'ROST', 'ORLY', 'AZO', 'ULTA', 'CMG', 'YUM', 'DRI', 'DECK', 'LULU', 'NVR',

    # Industrial
    'BA', 'CAT', 'HON', 'UNP', 'RTX', 'LMT', 'DE', 'GE', 'MMM', 'UPS',
    'NOC', 'GD', 'EMR', 'ETN', 'ITW', 'CSX', 'NSC', 'FDX', 'WM', 'RSG',

    # Energy
    'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'MPC', 'PSX', 'VLO', 'OXY', 'HES',

    # Materials
    'LIN', 'APD', 'SHW', 'ECL', 'NEM', 'FCX', 'NUE', 'DD', 'DOW', 'PPG',

    # Utilities
    'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE', 'XEL', 'ED', 'PEG',

    # Communication
    'TMUS', 'VZ', 'T', 'NFLX', 'DIS', 'CMCSA', 'CHTR', 'EA', 'TTWO', 'ATVI',

    # Real Estate
    'PLD', 'AMT', 'CCI', 'EQIX', 'PSA', 'WELL', 'DLR', 'SPG', 'O', 'VICI'
]


def load_watchlist(watchlist_file: str = None) -> list:
    """
    Load stock watchlist from file or use default

    Args:
        watchlist_file: Optional path to file with stock symbols (one per line)

    Returns:
        List of stock symbols
    """
    if watchlist_file and os.path.exists(watchlist_file):
        with open(watchlist_file, 'r') as f:
            symbols = [line.strip().upper() for line in f if line.strip()]
        print(f"Loaded {len(symbols)} symbols from {watchlist_file}")
        return symbols
    else:
        print(f"Using default watchlist of {len(DEFAULT_WATCHLIST)} stocks")
        return DEFAULT_WATCHLIST


def save_to_database(internals, conn, stock_universe_size: int):
    """
    Save market internals to database

    Args:
        internals: MarketInternals object
        conn: Database connection
        stock_universe_size: Number of stocks analyzed
    """
    try:
        cursor = conn.cursor()

        query = """
        INSERT INTO market_internals (
            timestamp, advances, declines, unchanged,
            advance_decline_ratio, breadth_ratio,
            up_volume, down_volume, up_down_volume_ratio, volume_ratio,
            tick, trin, add_index,
            cumulative_ad_line, breadth_thrust,
            data_source, stock_universe_size
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (timestamp) DO UPDATE SET
            advances = EXCLUDED.advances,
            declines = EXCLUDED.declines,
            unchanged = EXCLUDED.unchanged,
            advance_decline_ratio = EXCLUDED.advance_decline_ratio,
            breadth_ratio = EXCLUDED.breadth_ratio,
            up_volume = EXCLUDED.up_volume,
            down_volume = EXCLUDED.down_volume,
            up_down_volume_ratio = EXCLUDED.up_down_volume_ratio,
            volume_ratio = EXCLUDED.volume_ratio,
            tick = EXCLUDED.tick,
            trin = EXCLUDED.trin,
            add_index = EXCLUDED.add_index,
            cumulative_ad_line = EXCLUDED.cumulative_ad_line,
            breadth_thrust = EXCLUDED.breadth_thrust,
            stock_universe_size = EXCLUDED.stock_universe_size
        """

        cursor.execute(query, (
            internals.timestamp,
            internals.advances,
            internals.declines,
            internals.unchanged,
            internals.advance_decline_ratio,
            internals.breadth_ratio,
            int(internals.up_volume),
            int(internals.down_volume),
            internals.up_down_volume_ratio,
            internals.volume_ratio,
            internals.tick,
            internals.trin,
            internals.add,
            internals.cumulative_ad_line,
            internals.breadth_thrust,
            'calculated',
            stock_universe_size
        ))

        conn.commit()
        cursor.close()

        print(f"✓ Saved market internals to database")

    except Exception as e:
        print(f"✗ Error saving to database: {e}")
        conn.rollback()


def main():
    """Collect market internals and generate signals"""
    load_dotenv()

    import argparse
    parser = argparse.ArgumentParser(description='Market Internals Collector')
    parser.add_argument('--watchlist', type=str, help='Path to watchlist file (one symbol per line)')
    parser.add_argument('--no-save', action='store_true', help='Do not save to database')
    parser.add_argument('--output', type=str, help='Save signals to JSON file')
    args = parser.parse_args()

    print("=" * 80)
    print("MARKET INTERNALS COLLECTOR")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    try:
        # Initialize API
        api_key = os.getenv('TRADIER_API_KEY')
        if not api_key:
            print("✗ Error: TRADIER_API_KEY not found in environment")
            sys.exit(1)

        api = TradierAPI(api_key)

        # Load watchlist
        watchlist = load_watchlist(args.watchlist)

        # Connect to database
        db_conn = None
        if not args.no_save:
            try:
                db_conn = psycopg2.connect(
                    host=os.getenv('POSTGRES_HOST', 'localhost'),
                    port=os.getenv('POSTGRES_PORT', 5432),
                    database=os.getenv('POSTGRES_DB', 'gexdb'),
                    user=os.getenv('POSTGRES_USER', 'gexuser'),
                    password=os.getenv('POSTGRES_PASSWORD')
                )
                print("✓ Connected to PostgreSQL database\n")
            except Exception as e:
                print(f"✗ Database connection failed: {e}")
                print("Continuing without database storage...\n")

        # Collect market internals
        print("=" * 80)
        print("📊 COLLECTING MARKET INTERNALS")
        print("=" * 80)

        collector = MarketInternalsCollector(api)
        internals = collector.collect_from_stock_universe(watchlist)

        if not internals:
            print("✗ Failed to collect market internals")
            sys.exit(1)

        # Try to get breadth indices
        print("\nAttempting to fetch market breadth indices...")
        indices = collector.collect_from_indices()

        if indices:
            print(f"✓ Retrieved {len(indices)} breadth indices")
            # Add indices to internals object
            internals.tick = indices.get('tick')
            internals.trin = indices.get('trin')
            internals.add = indices.get('add')
        else:
            print("ℹ No breadth indices available from data source")

        # Collect sector breadth
        print("\nCollecting sector breadth...")
        sector_breadth = collector.collect_sector_breadth()
        if sector_breadth:
            internals.sector_breadth = sector_breadth
            print(f"✓ Sector breadth collected successfully")
        else:
            print("ℹ Unable to collect sector breadth data")

        # Calculate cumulative A/D line if database available
        if db_conn:
            net_ad = internals.advances - internals.declines
            cumulative_ad = collector.calculate_cumulative_ad_line(net_ad, db_conn)
            internals.cumulative_ad_line = cumulative_ad
            print(f"✓ Cumulative A/D Line: {cumulative_ad:,.0f}")

        # Save to database
        if db_conn and not args.no_save:
            save_to_database(internals, db_conn, len(watchlist))

        # Generate signals
        print("\n" + "=" * 80)
        print("🎯 GENERATING TRADING SIGNALS")
        print("=" * 80)

        generator = MarketInternalsSignalGenerator()
        signal_data = generator.generate_composite_signal(internals, indices)

        # Display results
        print("\n" + "=" * 80)
        print("📈 MARKET INTERNALS SUMMARY")
        print("=" * 80)
        print(f"Timestamp: {signal_data['timestamp']}")
        print(f"Universe: {len(watchlist)} stocks\n")

        print("Breadth:")
        print(f"  Advancing: {internals.advances}")
        print(f"  Declining: {internals.declines}")
        print(f"  Unchanged: {internals.unchanged}")
        print(f"  Ratio: {internals.breadth_ratio:+.2%} ({internals.advance_decline_ratio:.2f}:1)\n")

        print("Volume:")
        print(f"  Up Volume: {internals.up_volume:,.0f}")
        print(f"  Down Volume: {internals.down_volume:,.0f}")
        print(f"  Ratio: {internals.volume_ratio:+.2%} ({internals.up_down_volume_ratio:.2f}:1)")

        if indices:
            print("\nMarket Indices:")
            for key, value in indices.items():
                print(f"  {key.upper()}: {value:.2f}")

        if internals.sector_breadth:
            print("\nSector Rotation:")
            sb = internals.sector_breadth
            print(f"  Sectors Advancing: {sb.sectors_advancing}")
            print(f"  Sectors Declining: {sb.sectors_declining}")
            print(f"  Ratio: {sb.sector_breadth_ratio:+.2%}")
            print(f"  Strongest: {sb.strongest_sector} ({sb.sector_performance[sb.strongest_sector.split()[0]]:+.2f}%)")
            print(f"  Weakest: {sb.weakest_sector} ({sb.sector_performance[sb.weakest_sector.split()[0]]:+.2f}%)")
            print("\n  All Sectors:")
            # Sort sectors by performance
            sorted_sectors = sorted(sb.sector_performance.items(), key=lambda x: x[1], reverse=True)
            for symbol, pct_change in sorted_sectors:
                emoji = "🟢" if pct_change > 0 else "🔴" if pct_change < 0 else "⚪"
                print(f"    {emoji} {symbol}: {pct_change:+.2f}%")

        print("\n" + "=" * 80)
        print("📡 INDIVIDUAL SIGNALS")
        print("=" * 80)

        for sig in signal_data['individual_signals']:
            signal_type = sig['signal']
            if "BUY" in signal_type:
                emoji = "🟢"
            elif "SELL" in signal_type:
                emoji = "🔴"
            else:
                emoji = "⚪"

            print(f"\n{emoji} {sig['source']}")
            print(f"   Signal: {sig['signal']}")
            print(f"   Confidence: {sig['confidence']:.0%}")
            print(f"   Weight: {sig['normalized_weight']:.0%}")
            print(f"   {sig['reasoning']}")

        print("\n" + "=" * 80)
        print("🎲 COMPOSITE SIGNAL")
        print("=" * 80)
        print(f"Signal: {signal_data['composite_signal']}")
        print(f"Score: {signal_data['composite_score']:+.2f} (range: -1 to +1)")
        print(f"Confidence: {signal_data['composite_confidence']:.0%}")

        print("\n" + "=" * 80)
        print("💡 RECOMMENDATION")
        print("=" * 80)
        print(signal_data['recommendation'])

        # Save to JSON if requested
        if args.output:
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

            output_data = convert_to_serializable(signal_data)

            os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else '.', exist_ok=True)
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2)

            print(f"\n💾 Signals saved to: {args.output}")

        if db_conn:
            db_conn.close()

        print("\n" + "=" * 80)

    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
