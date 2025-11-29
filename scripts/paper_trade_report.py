#!/usr/bin/env python3
"""
Paper Trading Performance Report

Generates daily performance reports from paper trading positions.

Usage:
    python scripts/paper_trade_report.py
"""

import json
import pandas as pd
from datetime import datetime
import os


def load_positions():
    """Load paper trading positions"""
    positions_file = 'output/paper_trading_positions.json'

    if not os.path.exists(positions_file):
        print("No paper trading positions found. Start paper trading first.")
        return None

    with open(positions_file, 'r') as f:
        return json.load(f)


def generate_report():
    """Generate comprehensive performance report"""
    data = load_positions()

    if data is None:
        return

    active_legs = data.get('active_legs', [])
    closed_legs = data.get('closed_legs', [])

    print("\n" + "=" * 80)
    print("PAPER TRADING PERFORMANCE REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Active Positions
    print(f"\nACTIVE POSITIONS: {len(active_legs)}")
    print("-" * 80)

    if len(active_legs) > 0:
        for leg in active_legs:
            print(f"\n{leg['leg_type'].upper()} @ ${leg['strike']}")
            print(f"  Entry: {leg['entry_date']} {leg['entry_time']}")
            print(f"  Entry Price: ${leg['entry_price']:.2f}")
            print(f"  Entry SPX: ${leg['entry_spx_price']:.2f}")
            print(f"  Signal: {leg['gex_signal_at_entry']}")
    else:
        print("  No active positions")

    # Closed Positions
    print(f"\n\nCLOSED POSITIONS: {len(closed_legs)}")
    print("-" * 80)

    if len(closed_legs) == 0:
        print("  No completed trades yet")
        print("\n" + "=" * 80)
        return

    # Convert to DataFrame for analysis
    df = pd.DataFrame(closed_legs)

    # Overall Performance
    total_pnl = df['pnl'].sum()
    wins = df[df['pnl'] > 0]
    losses = df[df['pnl'] < 0]
    win_rate = len(wins) / len(df) if len(df) > 0 else 0

    print("\nOVERALL PERFORMANCE:")
    print(f"  Total Trades: {len(df)}")
    print(f"  Winning Trades: {len(wins)}")
    print(f"  Losing Trades: {len(losses)}")
    print(f"  Win Rate: {win_rate:.1%}")
    print(f"  Total P&L: ${total_pnl:,.2f}")
    print(f"  Average P&L: ${df['pnl'].mean():,.2f}")
    print(f"  Average Win: ${wins['pnl'].mean():,.2f}" if len(wins) > 0 else "  Average Win: N/A")
    print(f"  Average Loss: ${losses['pnl'].mean():,.2f}" if len(losses) > 0 else "  Average Loss: N/A")
    print(f"  Max Win: ${df['pnl'].max():,.2f}")
    print(f"  Max Loss: ${df['pnl'].min():,.2f}")

    # Profit Factor
    gross_profit = wins['pnl'].sum() if len(wins) > 0 else 0
    gross_loss = abs(losses['pnl'].sum()) if len(losses) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    print(f"  Profit Factor: {profit_factor:.2f}x")

    # By Leg Type
    print("\nPERFORMANCE BY LEG TYPE:")
    for leg_type in ['call', 'put']:
        leg_df = df[df['leg_type'] == leg_type]
        if len(leg_df) > 0:
            leg_wins = leg_df[leg_df['pnl'] > 0]
            leg_win_rate = len(leg_wins) / len(leg_df)
            print(f"\n  {leg_type.upper()}S:")
            print(f"    Trades: {len(leg_df)}")
            print(f"    Win Rate: {leg_win_rate:.1%}")
            print(f"    Total P&L: ${leg_df['pnl'].sum():,.2f}")
            print(f"    Avg P&L: ${leg_df['pnl'].mean():,.2f}")

    # By Signal
    print("\nPERFORMANCE BY ENTRY SIGNAL:")
    for signal in df['gex_signal_at_entry'].unique():
        signal_df = df[df['gex_signal_at_entry'] == signal]
        signal_wins = signal_df[signal_df['pnl'] > 0]
        signal_win_rate = len(signal_wins) / len(signal_df)
        print(f"\n  {signal}:")
        print(f"    Trades: {len(signal_df)}")
        print(f"    Win Rate: {signal_win_rate:.1%}")
        print(f"    Total P&L: ${signal_df['pnl'].sum():,.2f}")

    # By Exit Reason
    print("\nEXITS BY REASON:")
    for reason in df['exit_reason'].unique():
        reason_df = df[df['exit_reason'] == reason]
        print(f"  {reason}: {len(reason_df)} trades, P&L: ${reason_df['pnl'].sum():,.2f}")

    # Recent Trades
    print("\nRECENT TRADES (Last 10):")
    print("-" * 80)
    recent = df.tail(10)
    for _, trade in recent.iterrows():
        pnl_sign = "+" if trade['pnl'] > 0 else ""
        print(f"{trade['entry_date']} {trade['leg_type'].upper()} ${trade['strike']}: "
              f"${trade['entry_price']:.2f} -> ${trade['exit_price']:.2f} = "
              f"{pnl_sign}${trade['pnl']:.2f} ({pnl_sign}{trade['pnl_pct']:.1f}%) [{trade['exit_reason']}]")

    # Save detailed report
    report_file = f"output/paper_trading_report_{datetime.now().strftime('%Y%m%d')}.csv"
    df.to_csv(report_file, index=False)
    print(f"\nDetailed report saved to: {report_file}")

    print("\n" + "=" * 80)


def main():
    """Generate report"""
    generate_report()


if __name__ == "__main__":
    main()
