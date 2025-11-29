#!/usr/bin/env python3
"""
Comprehensive Performance Analysis for Strangle Strategy

Generates detailed performance reports, metrics, and insights.
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
import os


class PerformanceAnalyzer:
    """Analyze and report on backtest performance"""

    def __init__(self, results_csv_path: str):
        """
        Initialize analyzer with backtest results

        Args:
            results_csv_path: Path to CSV file with backtest results
        """
        self.df = pd.read_csv(results_csv_path)
        self.completed_trades = self.df[self.df['pnl'].notna()].copy()

    def generate_comprehensive_report(self) -> dict:
        """Generate comprehensive performance analysis"""

        report = {
            'summary_statistics': self._calculate_summary_stats(),
            'risk_metrics': self._calculate_risk_metrics(),
            'trade_analysis': self._analyze_trades(),
            'win_loss_analysis': self._analyze_win_loss(),
            'gex_signal_analysis': self._analyze_gex_signals(),
            'time_analysis': self._analyze_by_time(),
            'drawdown_analysis': self._calculate_drawdowns(),
            'recommendations': self._generate_recommendations()
        }

        return report

    def _calculate_summary_stats(self) -> dict:
        """Calculate summary statistics"""
        df = self.completed_trades

        if len(df) == 0:
            return {"error": "No completed trades"}

        return {
            'total_trades': len(df),
            'winning_trades': len(df[df['pnl'] > 0]),
            'losing_trades': len(df[df['pnl'] < 0]),
            'breakeven_trades': len(df[df['pnl'] == 0]),
            'win_rate': len(df[df['pnl'] > 0]) / len(df),
            'loss_rate': len(df[df['pnl'] < 0]) / len(df),
            'total_pnl': df['pnl'].sum(),
            'total_pnl_pct': df['pnl_pct'].mean(),
            'avg_pnl_per_trade': df['pnl'].mean(),
            'median_pnl_per_trade': df['pnl'].median(),
            'total_premium_deployed': df['total_entry_cost'].sum(),
            'avg_premium_per_trade': df['total_entry_cost'].mean(),
            'return_on_premium': df['pnl'].sum() / df['total_entry_cost'].sum() if df['total_entry_cost'].sum() > 0 else 0
        }

    def _calculate_risk_metrics(self) -> dict:
        """Calculate risk-adjusted metrics"""
        df = self.completed_trades

        if len(df) == 0:
            return {"error": "No completed trades"}

        # Win/Loss stats
        wins = df[df['pnl'] > 0]['pnl']
        losses = df[df['pnl'] < 0]['pnl']

        avg_win = wins.mean() if len(wins) > 0 else 0
        avg_loss = losses.mean() if len(losses) > 0 else 0
        largest_win = wins.max() if len(wins) > 0 else 0
        largest_loss = losses.min() if len(losses) > 0 else 0

        # Profit factor
        gross_profit = wins.sum() if len(wins) > 0 else 0
        gross_loss = abs(losses.sum()) if len(losses) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Expectancy
        win_rate = len(wins) / len(df)
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss))

        # Sharpe ratio (simplified)
        returns = df['pnl']
        sharpe = returns.mean() / returns.std() if returns.std() > 0 else 0

        # Sortino ratio (downside deviation)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 1 else returns.std()
        sortino = returns.mean() / downside_std if downside_std > 0 else 0

        return {
            'average_win': avg_win,
            'average_loss': avg_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'win_loss_ratio': abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        }

    def _analyze_trades(self) -> dict:
        """Analyze trade characteristics"""
        df = self.completed_trades

        if len(df) == 0:
            return {"error": "No completed trades"}

        # Analyze by strike selection
        call_otm_pct = ((df['call_strike'] - df['entry_spx_price']) / df['entry_spx_price'] * 100).mean()
        put_otm_pct = ((df['entry_spx_price'] - df['put_strike']) / df['entry_spx_price'] * 100).mean()

        # Analyze premium costs
        premium_stats = {
            'min_premium': df['total_entry_cost'].min(),
            'max_premium': df['total_entry_cost'].max(),
            'avg_premium': df['total_entry_cost'].mean(),
            'median_premium': df['total_entry_cost'].median()
        }

        # Analyze hold periods (if both entry and exit dates exist)
        if 'entry_date' in df.columns and 'exit_date' in df.columns:
            df['hold_days'] = (pd.to_datetime(df['exit_date']) - pd.to_datetime(df['entry_date'])).dt.days
            hold_period_stats = {
                'avg_hold_days': df['hold_days'].mean(),
                'min_hold_days': df['hold_days'].min(),
                'max_hold_days': df['hold_days'].max()
            }
        else:
            hold_period_stats = {}

        return {
            'avg_call_otm_pct': call_otm_pct,
            'avg_put_otm_pct': put_otm_pct,
            'premium_stats': premium_stats,
            'hold_period': hold_period_stats
        }

    def _analyze_win_loss(self) -> dict:
        """Analyze winning vs losing trades"""
        df = self.completed_trades

        wins = df[df['pnl'] > 0]
        losses = df[df['pnl'] < 0]

        win_analysis = {
            'count': len(wins),
            'avg_pnl': wins['pnl'].mean() if len(wins) > 0 else 0,
            'avg_pnl_pct': wins['pnl_pct'].mean() if len(wins) > 0 else 0,
            'avg_premium': wins['total_entry_cost'].mean() if len(wins) > 0 else 0
        }

        loss_analysis = {
            'count': len(losses),
            'avg_pnl': losses['pnl'].mean() if len(losses) > 0 else 0,
            'avg_pnl_pct': losses['pnl_pct'].mean() if len(losses) > 0 else 0,
            'avg_premium': losses['total_entry_cost'].mean() if len(losses) > 0 else 0
        }

        return {
            'winning_trades': win_analysis,
            'losing_trades': loss_analysis
        }

    def _analyze_gex_signals(self) -> dict:
        """Analyze performance by GEX signal"""
        df = self.completed_trades

        if 'gex_signal' not in df.columns:
            return {"error": "No GEX signal data"}

        signal_performance = {}

        for signal in df['gex_signal'].unique():
            signal_trades = df[df['gex_signal'] == signal]

            if len(signal_trades) > 0:
                signal_performance[signal] = {
                    'trade_count': len(signal_trades),
                    'win_rate': len(signal_trades[signal_trades['pnl'] > 0]) / len(signal_trades),
                    'avg_pnl': signal_trades['pnl'].mean(),
                    'total_pnl': signal_trades['pnl'].sum(),
                    'avg_pnl_pct': signal_trades['pnl_pct'].mean()
                }

        return signal_performance

    def _analyze_by_time(self) -> dict:
        """Analyze performance by entry time periods"""
        df = self.completed_trades

        if 'entry_date' not in df.columns:
            return {"error": "No entry date data"}

        df['entry_datetime'] = pd.to_datetime(df['entry_date'])
        df['month'] = df['entry_datetime'].dt.month
        df['day_of_week'] = df['entry_datetime'].dt.dayofweek

        # By month - convert to simple dict
        monthly_df = df.groupby('month')['pnl'].agg(['count', 'sum', 'mean']).reset_index()
        monthly_perf = {
            f"month_{int(row['month'])}": {
                'trade_count': int(row['count']),
                'total_pnl': float(row['sum']),
                'avg_pnl': float(row['mean'])
            }
            for _, row in monthly_df.iterrows()
        }

        # By day of week - convert to simple dict
        dow_df = df.groupby('day_of_week')['pnl'].agg(['count', 'sum', 'mean']).reset_index()
        dow_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        dow_perf = {
            dow_names[int(row['day_of_week'])]: {
                'trade_count': int(row['count']),
                'total_pnl': float(row['sum']),
                'avg_pnl': float(row['mean'])
            }
            for _, row in dow_df.iterrows()
        }

        return {
            'monthly_performance': monthly_perf,
            'day_of_week_performance': dow_perf
        }

    def _calculate_drawdowns(self) -> dict:
        """Calculate drawdown statistics"""
        df = self.completed_trades.copy()

        if len(df) == 0:
            return {"error": "No completed trades"}

        # Calculate cumulative P&L
        df = df.sort_values('entry_date')
        df['cumulative_pnl'] = df['pnl'].cumsum()

        # Calculate running maximum
        df['running_max'] = df['cumulative_pnl'].expanding().max()

        # Calculate drawdown
        df['drawdown'] = df['cumulative_pnl'] - df['running_max']

        max_drawdown = df['drawdown'].min()
        max_drawdown_pct = (max_drawdown / df['running_max'].max() * 100) if df['running_max'].max() > 0 else 0

        # Find longest drawdown period
        in_drawdown = df['drawdown'] < 0
        drawdown_periods = (in_drawdown != in_drawdown.shift()).cumsum()
        longest_drawdown = drawdown_periods[in_drawdown].value_counts().max() if in_drawdown.any() else 0

        return {
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown_pct,
            'longest_drawdown_trades': int(longest_drawdown) if not pd.isna(longest_drawdown) else 0,
            'current_drawdown': df['drawdown'].iloc[-1] if len(df) > 0 else 0
        }

    def _generate_recommendations(self) -> list:
        """Generate actionable recommendations based on analysis"""
        recommendations = []

        df = self.completed_trades

        if len(df) == 0:
            return ["Insufficient data for recommendations"]

        # Win rate analysis
        win_rate = len(df[df['pnl'] > 0]) / len(df)

        if win_rate > 0.75:
            recommendations.append(
                "STRONG STRATEGY: Win rate above 75% indicates robust strategy. "
                "Consider scaling position sizes gradually."
            )
        elif win_rate < 0.50:
            recommendations.append(
                "LOW WIN RATE: Win rate below 50%. Review strike selection and exit criteria. "
                "Consider tighter strike selection or different GEX levels."
            )

        # Profit factor analysis
        wins = df[df['pnl'] > 0]['pnl'].sum()
        losses = abs(df[df['pnl'] < 0]['pnl'].sum())
        profit_factor = wins / losses if losses > 0 else float('inf')

        if profit_factor > 2.0:
            recommendations.append(
                "EXCELLENT PROFIT FACTOR: Wins significantly outweigh losses. "
                "Strategy demonstrates good risk/reward."
            )
        elif profit_factor < 1.5:
            recommendations.append(
                "LOW PROFIT FACTOR: Average wins not significantly larger than losses. "
                "Consider tightening stop losses or improving entry timing."
            )

        # GEX signal analysis
        if 'gex_signal' in df.columns:
            signal_perf = self._analyze_gex_signals()

            for signal, metrics in signal_perf.items():
                if isinstance(metrics, dict) and 'win_rate' in metrics:
                    if metrics['win_rate'] > 0.80:
                        recommendations.append(
                            f"HIGH PERFORMANCE ON {signal} SIGNALS: {metrics['win_rate']:.1%} win rate. "
                            f"Consider filtering for {signal} signals only."
                        )
                    elif metrics['win_rate'] < 0.40:
                        recommendations.append(
                            f"POOR PERFORMANCE ON {signal} SIGNALS: {metrics['win_rate']:.1%} win rate. "
                            f"Consider avoiding trades when {signal} signal is present."
                        )

        # Premium analysis
        avg_premium = df['total_entry_cost'].mean()
        avg_pnl = df['pnl'].mean()

        if avg_pnl > avg_premium * 0.20:
            recommendations.append(
                f"STRONG RETURNS: Average P&L is {avg_pnl/avg_premium:.1%} of premium deployed. "
                "Strategy delivers good returns relative to capital risked."
            )

        # Add general recommendations
        recommendations.append(
            "RISK MANAGEMENT: Always use position sizing that limits each trade to 1-2% of portfolio."
        )

        recommendations.append(
            "MONITOR MARKET CONDITIONS: GEX signals work best in normal market conditions. "
            "Reduce position sizes during FOMC, earnings, and major economic releases."
        )

        return recommendations

    def print_report(self):
        """Print formatted report to console"""

        report = self.generate_comprehensive_report()

        print("\n" + "="*80)
        print("COMPREHENSIVE PERFORMANCE ANALYSIS")
        print("="*80)

        # Summary Statistics
        print("\n[SUMMARY STATISTICS]")
        print("-" * 80)
        for key, value in report['summary_statistics'].items():
            if isinstance(value, float):
                if 'rate' in key or 'return' in key:
                    print(f"  {key:30s}: {value:.2%}")
                else:
                    print(f"  {key:30s}: {value:,.2f}")
            else:
                print(f"  {key:30s}: {value}")

        # Risk Metrics
        print("\n[RISK METRICS]")
        print("-" * 80)
        for key, value in report['risk_metrics'].items():
            if isinstance(value, float):
                if 'ratio' in key:
                    print(f"  {key:30s}: {value:.3f}")
                else:
                    print(f"  {key:30s}: ${value:,.2f}")

        # Drawdown Analysis
        print("\n[DRAWDOWN ANALYSIS]")
        print("-" * 80)
        for key, value in report['drawdown_analysis'].items():
            if 'pct' in key:
                print(f"  {key:30s}: {value:.2f}%")
            else:
                print(f"  {key:30s}: ${value:,.2f}")

        # GEX Signal Performance
        if 'gex_signal_analysis' in report and not isinstance(report['gex_signal_analysis'], dict):
            print("\n[GEX SIGNAL PERFORMANCE]")
            print("-" * 80)
            for signal, metrics in report['gex_signal_analysis'].items():
                if isinstance(metrics, dict):
                    print(f"\n  {signal}:")
                    for key, value in metrics.items():
                        if isinstance(value, float):
                            if 'rate' in key or 'pct' in key:
                                print(f"    {key:28s}: {value:.2%}")
                            else:
                                print(f"    {key:28s}: {value:,.2f}")
                        else:
                            print(f"    {key:28s}: {value}")

        # Recommendations
        print("\n[STRATEGIC RECOMMENDATIONS]")
        print("-" * 80)
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"\n  {i}. {rec}")

        print("\n" + "="*80)

    def save_report(self, output_path: str):
        """Save report to JSON file"""

        report = self.generate_comprehensive_report()

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\nDetailed report saved to: {output_path}")


def main():
    """Run performance analysis"""

    results_path = 'output/strangle_backtest_results.csv'

    if not os.path.exists(results_path):
        print(f"Error: Results file not found at {results_path}")
        print("Please run backtest_strangle_strategy.py first.")
        return

    # Create analyzer
    analyzer = PerformanceAnalyzer(results_path)

    # Print report
    analyzer.print_report()

    # Save detailed report
    analyzer.save_report('output/strangle_detailed_analysis.json')


if __name__ == "__main__":
    main()
