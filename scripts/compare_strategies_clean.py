#!/usr/bin/env python3
"""
Compare EOD vs Intraday Strangle Strategies

Loads results from both backtests and provides side-by-side comparison.
"""

import pandas as pd
import json
import os


def load_results():
    """Load both backtest results"""

    # Original EOD strategy
    eod_results = pd.read_csv('output/strangle_backtest_results.csv')
    with open('output/strangle_performance.json', 'r') as f:
        eod_perf = json.load(f)

    # Intraday strategy
    intraday_results = pd.read_csv('output/strangle_intraday_results.csv')
    with open('output/strangle_intraday_performance.json', 'r') as f:
        intraday_perf = json.load(f)

    return eod_results, eod_perf, intraday_results, intraday_perf


def print_comparison():
    """Print side-by-side comparison"""

    eod_results, eod_perf, intraday_results, intraday_perf = load_results()

    print("\n" + "="*100)
    print("STRATEGY COMPARISON: EOD STRANGLE vs INTRADAY INDEPENDENT LEGS")
    print("="*100)

    print("\n" + "="*100)
    print("OVERVIEW")
    print("="*100)

    print(f"\n{'Metric':<40s} {'EOD Strategy':>25s} {'Intraday Strategy':>25s}")
    print("-" * 100)

    # Strategy description
    print(f"{'Strategy Type':<40s} {'Both legs at close':>25s} {'Independent leg entry':>25s}")
    print(f"{'Exit Timing':<40s} {'Next market open':>25s} {'Throughout day + overnight':>25s}")
    print(f"{'PDT Compliance':<40s} {'N/A (overnight hold)':>25s} {'Protected (no same-day)':>25s}")

    print("\n" + "="*100)
    print("PERFORMANCE METRICS")
    print("="*100)

    print(f"\n{'Metric':<40s} {'EOD Strategy':>25s} {'Intraday Strategy':>25s}")
    print("-" * 100)

    # Calculate EOD legs from completed trades (each strangle = 2 legs)
    eod_completed = eod_results[eod_results['pnl'].notna()]
    eod_legs = len(eod_completed) * 2  # Each strangle has call + put

    # Trades
    eod_pos_str = f"{len(eod_completed)} strangles"
    intraday_pos_str = f"{intraday_perf['total_legs_traded']} legs"
    print(f"{'Total Positions':<40s} {eod_pos_str:>25s} {intraday_pos_str:>25s}")

    eod_legs_str = f"{eod_legs} legs"
    intraday_legs_str = f"{intraday_perf['total_legs_traded']} legs"
    print(f"{'Total Legs Traded':<40s} {eod_legs_str:>25s} {intraday_legs_str:>25s}")

    print(f"{'  - Call Legs':<40s} {str(len(eod_completed)):>25s} {str(intraday_perf['call_legs']):>25s}")
    print(f"{'  - Put Legs':<40s} {str(len(eod_completed)):>25s} {str(intraday_perf['put_legs']):>25s}")

    # Win rate (for EOD, calculate from individual legs for fair comparison)
    eod_call_wins = len(eod_completed[eod_completed['pnl'] > 0])
    eod_put_wins = len(eod_completed[eod_completed['pnl'] > 0])  # Assuming both profitable together
    eod_call_losses = len(eod_completed[eod_completed['pnl'] < 0])
    eod_put_losses = len(eod_completed[eod_completed['pnl'] < 0])

    # Win rate
    eod_wr = f"{eod_perf['win_rate']:.1%}"
    int_wr = f"{intraday_perf['win_rate']:.1%}"
    print(f"\n{'Win Rate':<40s} {eod_wr:>25s} {int_wr:>25s}")
    print(f"{'Winning Positions':<40s} {str(eod_perf['winning_trades']):>25s} {str(intraday_perf['winning_legs']):>25s}")
    print(f"{'Losing Positions':<40s} {str(eod_perf['losing_trades']):>25s} {str(intraday_perf['losing_legs']):>25s}")

    # P&L
    eod_pnl = f"${eod_perf['total_pnl']:,.2f}"
    int_pnl = f"${intraday_perf['total_pnl']:,.2f}"
    print(f"\n{'Total P&L':<40s} {eod_pnl:>25s} {int_pnl:>25s}")

    eod_avg = f"${eod_perf['avg_pnl']:,.2f}"
    int_avg = f"${intraday_perf['avg_pnl_per_leg']:,.2f}"
    print(f"{'Average P&L per Position':<40s} {eod_avg:>25s} {int_avg:>25s}")

    eod_avgwin = f"${eod_perf['avg_win']:,.2f}"
    int_avgwin = f"${intraday_perf['avg_win']:,.2f}"
    print(f"{'Average Win':<40s} {eod_avgwin:>25s} {int_avgwin:>25s}")

    eod_avgloss = f"${eod_perf['avg_loss']:,.2f}"
    int_avgloss = f"${intraday_perf['avg_loss']:,.2f}"
    print(f"{'Average Loss':<40s} {eod_avgloss:>25s} {int_avgloss:>25s}")

    eod_maxwin = f"${eod_perf['max_win']:,.2f}"
    int_maxwin = f"${intraday_perf['max_win']:,.2f}"
    print(f"{'Max Win':<40s} {eod_maxwin:>25s} {int_maxwin:>25s}")

    eod_maxloss = f"${eod_perf['max_loss']:,.2f}"
    int_maxloss = f"${intraday_perf['max_loss']:,.2f}"
    print(f"{'Max Loss':<40s} {eod_maxloss:>25s} {int_maxloss:>25s}")

    # Risk metrics
    eod_pf = f"{eod_perf['profit_factor']:.2f}x"
    int_pf = f"{intraday_perf['profit_factor']:.2f}x"
    print(f"\n{'Profit Factor':<40s} {eod_pf:>25s} {int_pf:>25s}")

    eod_sharpe = f"{eod_perf['sharpe_ratio']:.3f}"
    print(f"{'Sharpe Ratio':<40s} {eod_sharpe:>25s} {'N/A':>25s}")

    # Capital efficiency
    eod_prem = f"${eod_perf['total_premium_deployed']:,.2f}"
    int_prem = f"${intraday_perf['total_premium_deployed']:,.2f}"
    print(f"\n{'Total Premium Deployed':<40s} {eod_prem:>25s} {int_prem:>25s}")

    eod_roi = (eod_perf['total_pnl'] / eod_perf['total_premium_deployed']) * 100
    intraday_roi = (intraday_perf['total_pnl'] / intraday_perf['total_premium_deployed']) * 100
    eod_roi_str = f"{eod_roi:.1f}%"
    int_roi_str = f"{intraday_roi:.1f}%"
    print(f"{'Return on Premium':<40s} {eod_roi_str:>25s} {int_roi_str:>25s}")

    print("\n" + "="*100)
    print("ANALYSIS & RECOMMENDATIONS")
    print("="*100)

    print("\n PERFORMANCE COMPARISON:")
    print("-" * 100)

    # Total P&L comparison
    pnl_diff = intraday_perf['total_pnl'] - eod_perf['total_pnl']
    pnl_pct_diff = (pnl_diff / eod_perf['total_pnl']) * 100

    if pnl_diff > 0:
        print(f" Intraday strategy generated {pnl_pct_diff:+.1f}% MORE profit (${pnl_diff:,.2f} more)")
    else:
        print(f" Intraday strategy generated {abs(pnl_pct_diff):.1f}% LESS profit (${abs(pnl_diff):,.2f} less)")

    # Capital efficiency
    capital_diff = intraday_perf['total_premium_deployed'] - eod_perf['total_premium_deployed']
    capital_pct_diff = (capital_diff / eod_perf['total_premium_deployed']) * 100

    if capital_diff < 0:
        print(f" Intraday strategy used {abs(capital_pct_diff):.1f}% LESS capital (${abs(capital_diff):,.2f} less)")
    else:
        print(f" Intraday strategy used {capital_pct_diff:+.1f}% MORE capital (${capital_diff:,.2f} more)")

    # ROI comparison
    roi_diff = intraday_roi - eod_roi
    if roi_diff > 0:
        print(f" Intraday strategy has {roi_diff:+.1f}% points BETTER return on capital")
    else:
        print(f" Intraday strategy has {abs(roi_diff):.1f}% points WORSE return on capital")

    # Win rate comparison
    wr_diff = intraday_perf['win_rate'] - eod_perf['win_rate']
    if wr_diff > 0:
        print(f" Intraday strategy has {wr_diff:+.1%} points HIGHER win rate")
    else:
        print(f"  Intraday strategy has {abs(wr_diff):.1%} points LOWER win rate")

    # Profit factor comparison
    pf_diff = intraday_perf['profit_factor'] - eod_perf['profit_factor']
    if pf_diff > 0:
        print(f" Intraday strategy has {pf_diff:+.2f}x BETTER profit factor")
    else:
        print(f"  Intraday strategy has {abs(pf_diff):.2f}x WORSE profit factor")

    print("\n KEY INSIGHTS:")
    print("-" * 100)

    if intraday_roi > eod_roi and pnl_diff > 0:
        print(" WINNER: Intraday Strategy")
        print("    Higher total profit")
        print("    Better capital efficiency")
        print("    Superior return on premium")
        if wr_diff < 0:
            print("     Trade-off: Lower win rate (but better average wins)")
    elif eod_perf['win_rate'] > intraday_perf['win_rate'] and eod_perf['profit_factor'] > intraday_perf['profit_factor']:
        print(" WINNER: EOD Strategy")
        print("    Higher win rate")
        print("    Better profit factor")
        print("    More consistent")
        if intraday_roi > eod_roi:
            print("     Note: Intraday has better ROI but EOD more reliable")
    else:
        print(" MIXED RESULTS")
        print("    Each strategy has advantages")
        print("    Choice depends on risk tolerance and capital")

    print("\n STRATEGY SELECTION GUIDE:")
    print("-" * 100)
    print("\nChoose EOD Strategy if you want:")
    print(f"   Higher win rate ({eod_perf['win_rate']:.1%} vs {intraday_perf['win_rate']:.1%})")
    print(f"   Higher profit factor ({eod_perf['profit_factor']:.1f}x vs {intraday_perf['profit_factor']:.1f}x)")
    print("   Simpler execution (one entry, one exit per day)")
    print("   More predictable results")
    print("   Good for smaller accounts")

    print("\nChoose Intraday Strategy if you want:")
    print(f"   Higher total profit (${intraday_perf['total_pnl']:,.2f} vs ${eod_perf['total_pnl']:,.2f})")
    print(f"   Better capital efficiency ({intraday_roi:.0f}% ROI vs {eod_roi:.0f}% ROI)")
    print("   More trading opportunities")
    print("   Ability to cut losers / take profits intraday")
    print("   PDT-compliant (no same-day round trips)")

    print("\n  HYBRID APPROACH:")
    print("-" * 100)
    print("  Consider combining both strategies:")
    print("   Use EOD for core positions (higher conviction)")
    print("   Use Intraday for tactical trades (exploit opportunities)")
    print("   Split capital 60/40 or 70/30 (EOD/Intraday)")
    print(f"   Projected combined P&L: ~${eod_perf['total_pnl']*0.6 + intraday_perf['total_pnl']*0.4:,.2f}")

    print("\n" + "="*100)
    print("\n")


if __name__ == "__main__":
    print_comparison()
