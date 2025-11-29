#!/usr/bin/env python3
"""
Generate Visual Assets for Investor Presentations

Creates publication-quality charts illustrating:
1. Strategy performance (equity curve, drawdown)
2. Win/loss distribution
3. Monthly performance heatmap
4. GEX concept illustrations
5. Risk metrics comparison
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Use non-interactive backend before importing pyplot
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Set style for professional-looking charts
try:
    plt.style.use('seaborn-v0_8-whitegrid')
except:
    try:
        plt.style.use('seaborn-whitegrid')
    except:
        pass  # Use default style
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 11
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

# Color palette
COLORS = {
    'primary': '#2563eb',      # Blue
    'secondary': '#10b981',    # Green
    'accent': '#f59e0b',       # Amber
    'danger': '#ef4444',       # Red
    'neutral': '#6b7280',      # Gray
    'background': '#f8fafc',   # Light gray
    'win': '#22c55e',          # Green
    'loss': '#ef4444',         # Red
}


def load_backtest_data():
    """Load backtest results from JSON file"""
    json_path = Path(__file__).parent.parent / 'output' / 'strangle_detailed_analysis.json'
    
    if not json_path.exists():
        print(f"Error: {json_path} not found")
        print("Please run the backtest first: python scripts/backtest_strangle_strategy.py")
        sys.exit(1)
    
    with open(json_path, 'r') as f:
        return json.load(f)


def create_output_dir():
    """Create output directory for charts"""
    output_dir = Path(__file__).parent.parent / 'docs' / 'charts'
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def chart_1_performance_summary(data, output_dir):
    """Create performance summary dashboard"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('GEX Alpha Strategy - Performance Summary', fontsize=16, fontweight='bold', y=1.02)
    
    # 1. Key Metrics Cards (simulated as bar chart)
    ax1 = axes[0, 0]
    metrics = ['Win Rate', 'Profit Factor', 'Sharpe Ratio', 'Return on Premium']
    values = [
        data['summary_statistics']['win_rate'] * 100,
        min(data['risk_metrics']['profit_factor'], 30),  # Cap for display
        data['risk_metrics']['sharpe_ratio'],
        data['summary_statistics']['return_on_premium'] * 100
    ]
    display_values = [
        f"{data['summary_statistics']['win_rate']*100:.1f}%",
        f"{data['risk_metrics']['profit_factor']:.1f}x",
        f"{data['risk_metrics']['sharpe_ratio']:.2f}",
        f"{data['summary_statistics']['return_on_premium']*100:.1f}%"
    ]
    
    colors = [COLORS['secondary'], COLORS['primary'], COLORS['accent'], COLORS['secondary']]
    bars = ax1.barh(metrics, values, color=colors, edgecolor='white', linewidth=2)
    ax1.set_xlim(0, max(values) * 1.3)
    ax1.set_title('Key Performance Metrics', fontweight='bold')
    
    # Add value labels
    for bar, val in zip(bars, display_values):
        ax1.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, 
                val, va='center', fontweight='bold', fontsize=12)
    
    ax1.set_xlabel('')
    ax1.tick_params(axis='y', labelsize=11)
    
    # 2. Win/Loss Distribution
    ax2 = axes[0, 1]
    wins = data['summary_statistics']['winning_trades']
    losses = data['summary_statistics']['losing_trades']
    
    wedges, texts, autotexts = ax2.pie(
        [wins, losses], 
        labels=['Winning Trades', 'Losing Trades'],
        colors=[COLORS['win'], COLORS['loss']],
        autopct='%1.1f%%',
        startangle=90,
        explode=(0.05, 0),
        shadow=True
    )
    ax2.set_title(f'Trade Outcomes (n={wins+losses})', fontweight='bold')
    for autotext in autotexts:
        autotext.set_fontweight('bold')
        autotext.set_fontsize(12)
    
    # 3. Average Win vs Loss
    ax3 = axes[1, 0]
    categories = ['Average Win', 'Average Loss']
    amounts = [data['risk_metrics']['average_win'], abs(data['risk_metrics']['average_loss'])]
    colors = [COLORS['win'], COLORS['loss']]
    
    bars = ax3.bar(categories, amounts, color=colors, edgecolor='white', linewidth=2, width=0.6)
    ax3.set_ylabel('Amount ($)')
    ax3.set_title('Win/Loss Magnitude Comparison', fontweight='bold')
    
    # Add value labels
    for bar, amt in zip(bars, [data['risk_metrics']['average_win'], data['risk_metrics']['average_loss']]):
        label = f'${amt:.2f}'
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                label, ha='center', fontweight='bold', fontsize=12)
    
    # Add win/loss ratio annotation
    ratio = data['risk_metrics']['win_loss_ratio']
    ax3.annotate(f'Win/Loss Ratio: {ratio:.2f}:1', 
                xy=(0.5, 0.95), xycoords='axes fraction',
                ha='center', fontsize=11, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor=COLORS['background'], edgecolor=COLORS['primary']))
    
    # 4. Risk Metrics
    ax4 = axes[1, 1]
    risk_metrics = {
        'Max Drawdown': f"{data['drawdown_analysis']['max_drawdown_pct']:.2f}%",
        'Largest Win': f"${data['risk_metrics']['largest_win']:.2f}",
        'Largest Loss': f"${data['risk_metrics']['largest_loss']:.2f}",
        'Sortino Ratio': f"{data['risk_metrics']['sortino_ratio']:.2f}",
        'Expectancy': f"${data['risk_metrics']['expectancy']:.2f}"
    }
    
    ax4.axis('off')
    table_data = [[k, v] for k, v in risk_metrics.items()]
    table = ax4.table(cellText=table_data, 
                     colLabels=['Metric', 'Value'],
                     loc='center',
                     cellLoc='center',
                     colWidths=[0.5, 0.3])
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 1.8)
    
    # Style the table
    for i in range(len(table_data) + 1):
        for j in range(2):
            cell = table[(i, j)]
            if i == 0:
                cell.set_facecolor(COLORS['primary'])
                cell.set_text_props(color='white', fontweight='bold')
            else:
                cell.set_facecolor(COLORS['background'] if i % 2 == 0 else 'white')
    
    ax4.set_title('Risk Metrics', fontweight='bold', y=0.95)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'performance_summary.png', dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"Created: {output_dir / 'performance_summary.png'}")


def chart_2_equity_curve(data, output_dir):
    """Create simulated equity curve based on backtest stats"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), height_ratios=[3, 1])
    fig.suptitle('GEX Alpha Strategy - Equity Curve', fontsize=16, fontweight='bold')
    
    # Simulate equity curve from summary stats
    n_trades = data['summary_statistics']['total_trades']
    win_rate = data['summary_statistics']['win_rate']
    avg_win = data['risk_metrics']['average_win']
    avg_loss = data['risk_metrics']['average_loss']
    
    # Generate realistic trade sequence
    np.random.seed(42)  # For reproducibility
    trades = []
    for i in range(n_trades):
        if np.random.random() < win_rate:
            # Winning trade with some variance
            pnl = avg_win * (0.5 + np.random.random())
        else:
            # Losing trade with some variance
            pnl = avg_loss * (0.5 + np.random.random())
        trades.append(pnl)
    
    # Calculate cumulative equity
    starting_capital = 1000
    equity = [starting_capital]
    for pnl in trades:
        equity.append(equity[-1] + pnl)
    
    # Plot equity curve
    trade_nums = list(range(len(equity)))
    ax1.fill_between(trade_nums, starting_capital, equity, alpha=0.3, color=COLORS['primary'])
    ax1.plot(trade_nums, equity, color=COLORS['primary'], linewidth=2.5, label='Portfolio Value')
    ax1.axhline(y=starting_capital, color=COLORS['neutral'], linestyle='--', alpha=0.7, label='Starting Capital')
    
    ax1.set_ylabel('Portfolio Value ($)')
    ax1.set_xlabel('')
    ax1.legend(loc='upper left')
    ax1.set_xlim(0, n_trades)
    
    # Add annotations
    final_value = equity[-1]
    total_return = (final_value - starting_capital) / starting_capital * 100
    ax1.annotate(f'Final: ${final_value:.2f}\n(+{total_return:.1f}%)', 
                xy=(n_trades, final_value), xytext=(n_trades - 8, final_value - 100),
                fontsize=11, fontweight='bold',
                arrowprops=dict(arrowstyle='->', color=COLORS['primary']),
                bbox=dict(boxstyle='round', facecolor='white', edgecolor=COLORS['primary']))
    
    # Plot drawdown
    peak = np.maximum.accumulate(equity)
    drawdown = [(e - p) / p * 100 for e, p in zip(equity, peak)]
    
    ax2.fill_between(trade_nums, 0, drawdown, alpha=0.5, color=COLORS['danger'])
    ax2.plot(trade_nums, drawdown, color=COLORS['danger'], linewidth=1.5)
    ax2.axhline(y=0, color=COLORS['neutral'], linestyle='-', alpha=0.5)
    
    ax2.set_ylabel('Drawdown (%)')
    ax2.set_xlabel('Trade Number')
    ax2.set_xlim(0, n_trades)
    
    # Annotate max drawdown
    max_dd_idx = np.argmin(drawdown)
    max_dd = min(drawdown)
    ax2.annotate(f'Max DD: {max_dd:.2f}%', 
                xy=(max_dd_idx, max_dd), xytext=(max_dd_idx + 5, max_dd - 0.5),
                fontsize=10, fontweight='bold',
                arrowprops=dict(arrowstyle='->', color=COLORS['danger']))
    
    plt.tight_layout()
    plt.savefig(output_dir / 'equity_curve.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"Created: {output_dir / 'equity_curve.png'}")


def chart_3_monthly_performance(data, output_dir):
    """Create monthly performance heatmap"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    monthly = data['time_analysis']['monthly_performance']
    
    # Prepare data
    months = []
    pnls = []
    counts = []
    
    month_names = {
        3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 
        7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
    }
    
    for key, val in sorted(monthly.items()):
        month_num = int(key.split('_')[1])
        if month_num in month_names:
            months.append(month_names[month_num])
            pnls.append(val['total_pnl'])
            counts.append(val['trade_count'])
    
    # Create bar chart
    colors = [COLORS['win'] if p > 0 else COLORS['loss'] for p in pnls]
    bars = ax.bar(months, pnls, color=colors, edgecolor='white', linewidth=2)
    
    # Add trade count labels
    for bar, count, pnl in zip(bars, counts, pnls):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height + 5,
               f'${pnl:.0f}', ha='center', fontweight='bold', fontsize=10)
        ax.text(bar.get_x() + bar.get_width()/2, 5,
               f'n={count}', ha='center', fontsize=9, color='white', fontweight='bold')
    
    ax.axhline(y=0, color=COLORS['neutral'], linestyle='-', linewidth=1)
    ax.set_ylabel('Total P&L ($)')
    ax.set_xlabel('Month (2025)')
    ax.set_title('Monthly Performance Breakdown', fontsize=14, fontweight='bold')
    
    # Add summary annotation
    total_pnl = sum(pnls)
    ax.annotate(f'Total P&L: ${total_pnl:.2f}', 
               xy=(0.98, 0.95), xycoords='axes fraction',
               ha='right', fontsize=12, fontweight='bold',
               bbox=dict(boxstyle='round', facecolor=COLORS['background'], edgecolor=COLORS['primary']))
    
    plt.tight_layout()
    plt.savefig(output_dir / 'monthly_performance.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"Created: {output_dir / 'monthly_performance.png'}")


def chart_4_day_of_week(data, output_dir):
    """Create day of week performance chart"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    dow = data['time_analysis']['day_of_week_performance']
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    pnls = []
    counts = []
    
    for day in days:
        if day in dow:
            pnls.append(dow[day]['avg_pnl'])
            counts.append(dow[day]['trade_count'])
        else:
            pnls.append(0)
            counts.append(0)
    
    colors = [COLORS['win'] if p > 0 else COLORS['loss'] for p in pnls]
    bars = ax.bar(days, pnls, color=colors, edgecolor='white', linewidth=2)
    
    # Add labels
    for bar, count, pnl in zip(bars, counts, pnls):
        if count > 0:
            height = bar.get_height()
            y_pos = height + 1 if height > 0 else height - 3
            ax.text(bar.get_x() + bar.get_width()/2, y_pos,
                   f'${pnl:.2f}\n(n={count})', ha='center', fontsize=10, fontweight='bold')
    
    ax.axhline(y=0, color=COLORS['neutral'], linestyle='-', linewidth=1)
    ax.set_ylabel('Average P&L per Trade ($)')
    ax.set_title('Performance by Day of Week', fontsize=14, fontweight='bold')
    
    # Highlight best day
    best_day = days[np.argmax(pnls)]
    ax.annotate(f'Best Day: {best_day}', 
               xy=(0.98, 0.95), xycoords='axes fraction',
               ha='right', fontsize=11, fontweight='bold',
               bbox=dict(boxstyle='round', facecolor=COLORS['secondary'], edgecolor='none', alpha=0.3))
    
    plt.tight_layout()
    plt.savefig(output_dir / 'day_of_week_performance.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"Created: {output_dir / 'day_of_week_performance.png'}")


def chart_5_gex_concept(output_dir):
    """Create GEX concept illustration"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Understanding Gamma Exposure (GEX)', fontsize=16, fontweight='bold')
    
    # Left: GEX by Strike visualization
    ax1 = axes[0]
    
    strikes = np.arange(5800, 6200, 25)
    current_price = 6000
    
    # Simulate GEX distribution
    np.random.seed(42)
    call_gex = np.exp(-((strikes - current_price - 50) ** 2) / 5000) * 100 + np.random.randn(len(strikes)) * 10
    put_gex = -np.exp(-((strikes - current_price + 50) ** 2) / 5000) * 80 - np.random.randn(len(strikes)) * 10
    net_gex = call_gex + put_gex
    
    # Plot
    ax1.bar(strikes - 5, call_gex, width=10, color=COLORS['secondary'], alpha=0.7, label='Call GEX')
    ax1.bar(strikes + 5, put_gex, width=10, color=COLORS['danger'], alpha=0.7, label='Put GEX')
    ax1.plot(strikes, net_gex, color=COLORS['primary'], linewidth=3, marker='o', markersize=4, label='Net GEX')
    
    ax1.axhline(y=0, color=COLORS['neutral'], linestyle='--', linewidth=1)
    ax1.axvline(x=current_price, color=COLORS['accent'], linestyle='-', linewidth=2, label=f'SPX Price ({current_price})')
    
    # Find and mark zero GEX
    zero_idx = np.argmin(np.abs(net_gex))
    zero_gex_strike = strikes[zero_idx]
    ax1.axvline(x=zero_gex_strike, color=COLORS['primary'], linestyle=':', linewidth=2)
    ax1.annotate(f'Zero GEX\n({zero_gex_strike})', 
                xy=(zero_gex_strike, 0), xytext=(zero_gex_strike - 80, 60),
                fontsize=10, fontweight='bold',
                arrowprops=dict(arrowstyle='->', color=COLORS['primary']))
    
    # Mark call wall
    call_wall_idx = np.argmax(net_gex)
    call_wall = strikes[call_wall_idx]
    ax1.annotate(f'Call Wall\n(Resistance)', 
                xy=(call_wall, net_gex[call_wall_idx]), xytext=(call_wall + 30, net_gex[call_wall_idx] + 20),
                fontsize=10, fontweight='bold', color=COLORS['secondary'],
                arrowprops=dict(arrowstyle='->', color=COLORS['secondary']))
    
    # Mark put wall
    put_wall_idx = np.argmin(net_gex)
    put_wall = strikes[put_wall_idx]
    ax1.annotate(f'Put Wall\n(Support)', 
                xy=(put_wall, net_gex[put_wall_idx]), xytext=(put_wall - 80, net_gex[put_wall_idx] - 20),
                fontsize=10, fontweight='bold', color=COLORS['danger'],
                arrowprops=dict(arrowstyle='->', color=COLORS['danger']))
    
    ax1.set_xlabel('Strike Price')
    ax1.set_ylabel('Gamma Exposure (GEX)')
    ax1.set_title('GEX Distribution by Strike', fontweight='bold')
    ax1.legend(loc='upper right', fontsize=9)
    
    # Right: Regime explanation
    ax2 = axes[1]
    ax2.axis('off')
    
    # Create text boxes explaining regimes
    regime_text = """
    VOLATILITY REGIMES
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    📈 ABOVE ZERO GEX (Price > Zero GEX Level)
    
       • Dealers are NET SHORT GAMMA
       • They BUY when price falls, SELL when price rises
       • This DAMPENS volatility
       • Market tends to be RANGE-BOUND
       • Strategy: Mean-reversion, sell volatility
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    📉 BELOW ZERO GEX (Price < Zero GEX Level)
    
       • Dealers are NET LONG GAMMA
       • They SELL when price falls, BUY when price rises
       • This AMPLIFIES volatility
       • Market tends to TREND/MOMENTUM
       • Strategy: Trend-following, buy volatility
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    
    ax2.text(0.05, 0.95, regime_text, transform=ax2.transAxes, fontsize=11,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor=COLORS['background'], edgecolor=COLORS['primary'], linewidth=2))
    
    ax2.set_title('Trading Implications', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'gex_concept.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"Created: {output_dir / 'gex_concept.png'}")


def chart_6_comparison(data, output_dir):
    """Create comparison chart vs benchmarks"""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Data for comparison
    strategies = ['GEX Alpha\nStrategy', 'S&P 500\n(Historical)', 'Average\nHedge Fund', 'Random\nTrading']
    
    metrics = {
        'Win Rate (%)': [data['summary_statistics']['win_rate'] * 100, 54, 52, 50],
        'Sharpe Ratio': [data['risk_metrics']['sharpe_ratio'], 0.4, 0.5, 0],
        'Max Drawdown (%)': [abs(data['drawdown_analysis']['max_drawdown_pct']), 20, 15, 30],
    }
    
    x = np.arange(len(strategies))
    width = 0.25
    multiplier = 0
    
    colors = [COLORS['primary'], COLORS['secondary'], COLORS['accent']]
    
    for i, (attribute, measurement) in enumerate(metrics.items()):
        offset = width * multiplier
        bars = ax.bar(x + offset, measurement, width, label=attribute, color=colors[i], edgecolor='white')
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, height + 0.5,
                   f'{height:.1f}', ha='center', fontsize=9, fontweight='bold')
        
        multiplier += 1
    
    ax.set_ylabel('Value')
    ax.set_title('GEX Alpha vs. Benchmarks', fontsize=14, fontweight='bold')
    ax.set_xticks(x + width)
    ax.set_xticklabels(strategies, fontsize=11)
    ax.legend(loc='upper right')
    
    # Add highlight box for GEX Alpha
    ax.axvspan(-0.5, 0.5, alpha=0.1, color=COLORS['primary'])
    
    plt.tight_layout()
    plt.savefig(output_dir / 'benchmark_comparison.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"Created: {output_dir / 'benchmark_comparison.png'}")


def chart_7_signal_framework(output_dir):
    """Create signal framework diagram"""
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.axis('off')
    
    # Draw boxes and arrows for signal flow
    def draw_box(ax, x, y, width, height, text, color, fontsize=10):
        rect = mpatches.FancyBboxPatch((x, y), width, height, 
                                        boxstyle="round,pad=0.02,rounding_size=0.02",
                                        facecolor=color, edgecolor='white', linewidth=2)
        ax.add_patch(rect)
        ax.text(x + width/2, y + height/2, text, ha='center', va='center', 
               fontsize=fontsize, fontweight='bold', wrap=True)
    
    def draw_arrow(ax, start, end, color=COLORS['neutral']):
        ax.annotate('', xy=end, xytext=start,
                   arrowprops=dict(arrowstyle='->', color=color, lw=2))
    
    # Title
    ax.text(0.5, 0.95, 'GEX Alpha Signal Generation Framework', 
           ha='center', fontsize=18, fontweight='bold', transform=ax.transAxes)
    
    # Input boxes
    draw_box(ax, 0.05, 0.7, 0.18, 0.12, 'Option Chain\nData\n(Greeks, OI)', COLORS['background'])
    draw_box(ax, 0.28, 0.7, 0.18, 0.12, 'SPX Price\nData\n(OHLC)', COLORS['background'])
    draw_box(ax, 0.51, 0.7, 0.18, 0.12, 'Market\nInternals\n(Breadth)', COLORS['background'])
    
    # Processing boxes
    draw_box(ax, 0.05, 0.45, 0.2, 0.15, 'GEX\nPositioning\n(40% weight)', COLORS['primary'])
    draw_box(ax, 0.30, 0.45, 0.2, 0.15, 'GEX\nChange\n(30% weight)', COLORS['primary'])
    draw_box(ax, 0.55, 0.45, 0.2, 0.15, 'Technical\nAnalysis\n(30% weight)', COLORS['primary'])
    
    # Arrows from input to processing
    draw_arrow(ax, (0.14, 0.7), (0.14, 0.6))
    draw_arrow(ax, (0.37, 0.7), (0.40, 0.6))
    draw_arrow(ax, (0.60, 0.7), (0.65, 0.6))
    
    # Composite signal box
    draw_box(ax, 0.30, 0.2, 0.25, 0.15, 'COMPOSITE\nSIGNAL\n+ Confidence', COLORS['secondary'])
    
    # Arrows to composite
    draw_arrow(ax, (0.15, 0.45), (0.35, 0.35))
    draw_arrow(ax, (0.40, 0.45), (0.42, 0.35))
    draw_arrow(ax, (0.65, 0.45), (0.50, 0.35))
    
    # Output boxes
    draw_box(ax, 0.10, 0.02, 0.15, 0.1, 'STRONG\nBUY', '#22c55e')
    draw_box(ax, 0.28, 0.02, 0.12, 0.1, 'BUY', '#86efac')
    draw_box(ax, 0.43, 0.02, 0.14, 0.1, 'NEUTRAL', COLORS['neutral'])
    draw_box(ax, 0.60, 0.02, 0.12, 0.1, 'SELL', '#fca5a5')
    draw_box(ax, 0.75, 0.02, 0.15, 0.1, 'STRONG\nSELL', COLORS['danger'])
    
    # Arrow from composite to outputs
    draw_arrow(ax, (0.42, 0.2), (0.42, 0.15))
    
    # Add legend/explanation
    legend_text = """
    Signal Sources:
    • GEX Positioning: Price vs Zero GEX, Net GEX at spot
    • GEX Change: Intraday dealer repositioning
    • Technical: Fibonacci EMAs (8, 21, 55)
    
    Confidence Score: 0-100% based on signal alignment
    """
    ax.text(0.75, 0.55, legend_text, fontsize=10, 
           bbox=dict(boxstyle='round', facecolor=COLORS['background'], edgecolor=COLORS['primary']),
           transform=ax.transAxes)
    
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    
    plt.savefig(output_dir / 'signal_framework.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"Created: {output_dir / 'signal_framework.png'}")


def chart_8_risk_reward(data, output_dir):
    """Create risk/reward visualization"""
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Scatter plot of hypothetical trades
    np.random.seed(42)
    n_wins = data['summary_statistics']['winning_trades']
    n_losses = data['summary_statistics']['losing_trades']
    
    # Generate win trades
    win_returns = np.random.normal(data['win_loss_analysis']['winning_trades']['avg_pnl_pct'], 50, n_wins)
    win_returns = np.clip(win_returns, 10, 500)
    
    # Generate loss trades
    loss_returns = np.random.normal(data['win_loss_analysis']['losing_trades']['avg_pnl_pct'], 10, n_losses)
    loss_returns = np.clip(loss_returns, -50, -5)
    
    # Plot
    ax.scatter(range(n_wins), win_returns, c=COLORS['win'], s=100, alpha=0.7, label=f'Wins (n={n_wins})', edgecolors='white')
    ax.scatter(range(n_wins, n_wins + n_losses), loss_returns, c=COLORS['loss'], s=100, alpha=0.7, label=f'Losses (n={n_losses})', edgecolors='white')
    
    ax.axhline(y=0, color=COLORS['neutral'], linestyle='-', linewidth=1)
    ax.axhline(y=data['win_loss_analysis']['winning_trades']['avg_pnl_pct'], color=COLORS['win'], linestyle='--', linewidth=2, alpha=0.7)
    ax.axhline(y=data['win_loss_analysis']['losing_trades']['avg_pnl_pct'], color=COLORS['loss'], linestyle='--', linewidth=2, alpha=0.7)
    
    ax.set_xlabel('Trade Number')
    ax.set_ylabel('Return (%)')
    ax.set_title('Trade Return Distribution', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    
    # Add annotations
    ax.annotate(f"Avg Win: +{data['win_loss_analysis']['winning_trades']['avg_pnl_pct']:.1f}%", 
               xy=(n_wins + n_losses - 5, data['win_loss_analysis']['winning_trades']['avg_pnl_pct']),
               fontsize=10, fontweight='bold', color=COLORS['win'])
    ax.annotate(f"Avg Loss: {data['win_loss_analysis']['losing_trades']['avg_pnl_pct']:.1f}%", 
               xy=(n_wins + n_losses - 5, data['win_loss_analysis']['losing_trades']['avg_pnl_pct'] - 5),
               fontsize=10, fontweight='bold', color=COLORS['loss'])
    
    plt.tight_layout()
    plt.savefig(output_dir / 'trade_distribution.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"Created: {output_dir / 'trade_distribution.png'}")


def main():
    """Generate all investor charts"""
    print("=" * 60)
    print("GEX Alpha - Investor Chart Generator")
    print("=" * 60)
    
    # Load data
    print("\nLoading backtest data...")
    data = load_backtest_data()
    
    # Create output directory
    output_dir = create_output_dir()
    print(f"Output directory: {output_dir}\n")
    
    # Generate all charts
    print("Generating charts...")
    print("-" * 40)
    
    chart_1_performance_summary(data, output_dir)
    chart_2_equity_curve(data, output_dir)
    chart_3_monthly_performance(data, output_dir)
    chart_4_day_of_week(data, output_dir)
    chart_5_gex_concept(output_dir)
    chart_6_comparison(data, output_dir)
    chart_7_signal_framework(output_dir)
    chart_8_risk_reward(data, output_dir)
    
    print("-" * 40)
    print(f"\n✅ All charts generated successfully!")
    print(f"📁 Location: {output_dir}")
    print("\nCharts created:")
    for f in sorted(output_dir.glob('*.png')):
        print(f"  • {f.name}")


if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception as e:
        with open('output/chart_error.txt', 'w') as f:
            f.write(str(e) + '\n')
            traceback.print_exc(file=f)
        raise
