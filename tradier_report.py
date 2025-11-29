#!/usr/bin/env python3
"""
Tradier Paper Trading Report

Displays current positions, P&L, and performance metrics from Tradier paper trading.
"""

import json
import os
from datetime import datetime
from typing import Dict, List
import pandas as pd
from dotenv import load_dotenv
import requests

load_dotenv()

# Tradier API Configuration
TRADIER_API_KEY = os.getenv('TRADIER_SANDBOX_API_KEY') or os.getenv('TRADIER_API_KEY')
TRADIER_ACCOUNT = os.getenv('TRADIER_SANDBOX_ACCOUNT', 'VA86061098')
BASE_URL = 'https://sandbox.tradier.com/v1'

POSITION_FILE = 'tradier_positions.json'


def get_account_balance():
    """Get current account balance from Tradier"""
    url = f'{BASE_URL}/accounts/{TRADIER_ACCOUNT}/balances'
    headers = {
        'Authorization': f'Bearer {TRADIER_API_KEY}',
        'Accept': 'application/json'
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get('balances', {})
        return None
    except Exception as e:
        print(f"ERROR: Could not get balance - {e}")
        return None


def get_tradier_positions():
    """Get current positions from Tradier"""
    url = f'{BASE_URL}/accounts/{TRADIER_ACCOUNT}/positions'
    headers = {
        'Authorization': f'Bearer {TRADIER_API_KEY}',
        'Accept': 'application/json'
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            positions = data.get('positions')
            if positions and positions != 'null':
                position_list = positions.get('position', [])
                if isinstance(position_list, dict):
                    return [position_list]
                return position_list
            return []
        return []
    except Exception as e:
        print(f"ERROR: Could not get positions - {e}")
        return []


def load_local_positions():
    """Load positions from local JSON file"""
    if not os.path.exists(POSITION_FILE):
        return {'active_legs': [], 'closed_legs': []}

    try:
        with open(POSITION_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"ERROR: Could not load positions file - {e}")
        return {'active_legs': [], 'closed_legs': []}


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_section(title: str):
    """Print formatted section"""
    print("\n" + "-" * 80)
    print(f"  {title}")
    print("-" * 80)


def display_account_summary():
    """Display account balance and summary"""
    print_header("TRADIER PAPER TRADING REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Account: {TRADIER_ACCOUNT}")

    balance = get_account_balance()
    if balance:
        print_section("Account Balance")
        print(f"  Total Equity:        ${balance.get('total_equity', 0):>12,.2f}")
        print(f"  Cash Available:      ${balance.get('total_cash', 0):>12,.2f}")
        print(f"  Option Buying Power: ${balance.get('option_buying_power', 0):>12,.2f}")
        print(f"  P&L (Day):           ${balance.get('day_trade_buying_power', 0):>12,.2f}")


def display_tradier_positions():
    """Display positions from Tradier API"""
    positions = get_tradier_positions()

    print_section(f"Live Positions from Tradier ({len(positions)} positions)")

    if not positions:
        print("  No open positions")
        return

    for pos in positions:
        symbol = pos.get('symbol', 'Unknown')
        quantity = pos.get('quantity', 0)
        cost_basis = pos.get('cost_basis', 0)
        date_acquired = pos.get('date_acquired', 'Unknown')

        print(f"\n  Symbol: {symbol}")
        print(f"    Quantity:      {quantity}")
        print(f"    Cost Basis:    ${cost_basis:,.2f}")
        print(f"    Date Acquired: {date_acquired}")


def display_local_positions():
    """Display positions from local tracking file"""
    data = load_local_positions()
    active = data.get('active_legs', [])
    closed = data.get('closed_legs', [])

    # Active positions
    print_section(f"Active Legs (from local tracking) - {len(active)} legs")

    if not active:
        print("  No active legs")
    else:
        for leg in active:
            leg_type = leg.get('leg_type', 'Unknown').upper()
            strike = leg.get('strike', 0)
            entry_price = leg.get('entry_price', 0)
            entry_status = leg.get('entry_order_status', 'Unknown')
            entry_date = leg.get('entry_date', 'Unknown')
            signal = leg.get('gex_signal_at_entry', 'Unknown')

            print(f"\n  {leg_type} @ ${strike}")
            print(f"    Entry Date:   {entry_date}")
            print(f"    Entry Price:  ${entry_price:.2f}")
            print(f"    Order Status: {entry_status}")
            print(f"    Signal:       {signal}")

    # Closed positions
    print_section(f"Closed Legs (from local tracking) - {len(closed)} legs")

    if not closed:
        print("  No closed legs")
    else:
        # Create DataFrame for analysis
        df_closed = pd.DataFrame(closed)

        # Summary stats
        total_pnl = df_closed['pnl'].sum() if 'pnl' in df_closed.columns else 0
        total_trades = len(df_closed)

        winners = df_closed[df_closed['pnl'] > 0] if 'pnl' in df_closed.columns else pd.DataFrame()
        losers = df_closed[df_closed['pnl'] < 0] if 'pnl' in df_closed.columns else pd.DataFrame()

        win_count = len(winners)
        loss_count = len(losers)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

        print(f"\n  Total P&L:      ${total_pnl:>10,.2f}")
        print(f"  Total Trades:   {total_trades:>10}")
        print(f"  Win Rate:       {win_rate:>10.1f}%")
        print(f"  Winners:        {win_count:>10}")
        print(f"  Losers:         {loss_count:>10}")

        if win_count > 0:
            avg_win = winners['pnl'].mean()
            print(f"  Avg Win:        ${avg_win:>10,.2f}")

        if loss_count > 0:
            avg_loss = losers['pnl'].mean()
            print(f"  Avg Loss:       ${avg_loss:>10,.2f}")

        # Recent trades
        print("\n  Recent Trades:")
        recent = df_closed.tail(10)

        for _, leg in recent.iterrows():
            leg_type = leg.get('leg_type', 'Unknown').upper()
            strike = leg.get('strike', 0)
            pnl = leg.get('pnl', 0)
            pnl_pct = leg.get('pnl_pct', 0)
            exit_reason = leg.get('exit_reason', 'Unknown')
            exit_date = leg.get('exit_date', 'Unknown')

            pnl_str = f"${pnl:>8,.2f} ({pnl_pct:>6.1f}%)"
            print(f"    {exit_date} | {leg_type:4} @ ${strike:>7.0f} | {pnl_str} | {exit_reason}")


def display_performance_by_type():
    """Display performance broken down by leg type and signal"""
    data = load_local_positions()
    closed = data.get('closed_legs', [])

    if not closed:
        return

    df = pd.DataFrame(closed)

    if 'pnl' not in df.columns:
        return

    print_section("Performance Analysis")

    # By leg type
    if 'leg_type' in df.columns:
        print("\n  By Leg Type:")
        type_stats = df.groupby('leg_type').agg({
            'pnl': ['sum', 'mean', 'count']
        }).round(2)

        for leg_type in type_stats.index:
            total = type_stats.loc[leg_type, ('pnl', 'sum')]
            avg = type_stats.loc[leg_type, ('pnl', 'mean')]
            count = int(type_stats.loc[leg_type, ('pnl', 'count')])

            print(f"    {leg_type.upper():4} - Count: {count:3} | Total: ${total:>9,.2f} | Avg: ${avg:>8,.2f}")

    # By signal
    if 'gex_signal_at_entry' in df.columns:
        print("\n  By Entry Signal:")
        signal_stats = df.groupby('gex_signal_at_entry').agg({
            'pnl': ['sum', 'mean', 'count']
        }).round(2)

        for signal in signal_stats.index:
            total = signal_stats.loc[signal, ('pnl', 'sum')]
            avg = signal_stats.loc[signal, ('pnl', 'mean')]
            count = int(signal_stats.loc[signal, ('pnl', 'count')])

            print(f"    {signal:7} - Count: {count:3} | Total: ${total:>9,.2f} | Avg: ${avg:>8,.2f}")

    # By exit reason
    if 'exit_reason' in df.columns:
        print("\n  By Exit Reason:")
        exit_stats = df.groupby('exit_reason').agg({
            'pnl': ['sum', 'mean', 'count']
        }).round(2)

        for reason in exit_stats.index:
            total = exit_stats.loc[reason, ('pnl', 'sum')]
            avg = exit_stats.loc[reason, ('pnl', 'mean')]
            count = int(exit_stats.loc[reason, ('pnl', 'count')])

            print(f"    {reason:13} - Count: {count:3} | Total: ${total:>9,.2f} | Avg: ${avg:>8,.2f}")


def export_to_csv():
    """Export closed trades to CSV"""
    data = load_local_positions()
    closed = data.get('closed_legs', [])

    if not closed:
        print("\n  No trades to export")
        return

    df = pd.DataFrame(closed)

    # Create output directory
    os.makedirs('output', exist_ok=True)

    # Export
    output_file = 'output/tradier_trades.csv'
    df.to_csv(output_file, index=False)

    print(f"\n  Exported {len(df)} trades to {output_file}")


def main():
    """Main report generator"""
    display_account_summary()
    display_tradier_positions()
    display_local_positions()
    display_performance_by_type()
    export_to_csv()

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
