#!/usr/bin/env python3
"""
Strangle Strategy Optimization Framework

Tests different parameter combinations to find optimal strategy configuration.
"""

import psycopg2
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import os
import json
from itertools import product
from datetime import datetime
from backtest_strangle_strategy import (
    StrangleBacktester, StrikeSelectionMethod
)

load_dotenv()


class StrategyOptimizer:
    """Optimize strangle strategy parameters"""

    def __init__(self, db_connection):
        self.db = db_connection
        self.backtester = StrangleBacktester(db_connection)
        self.optimization_results = []

    def optimize_strike_selection(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Test different strike selection methods

        Args:
            start_date: Start date for backtesting
            end_date: End date for backtesting

        Returns:
            DataFrame with results for each method
        """
        print("\n" + "="*80)
        print("OPTIMIZING STRIKE SELECTION METHODS")
        print("="*80 + "\n")

        methods_to_test = [
            {
                'method': StrikeSelectionMethod.GEX_WALLS,
                'params': {},
                'label': 'GEX Walls (Call/Put Walls)'
            },
            {
                'method': StrikeSelectionMethod.ZERO_GEX_OFFSET,
                'params': {'call_offset_pct': 1.0, 'put_offset_pct': 1.0},
                'label': 'Zero GEX +/- 1.0%'
            },
            {
                'method': StrikeSelectionMethod.ZERO_GEX_OFFSET,
                'params': {'call_offset_pct': 1.5, 'put_offset_pct': 1.5},
                'label': 'Zero GEX +/- 1.5%'
            },
            {
                'method': StrikeSelectionMethod.ZERO_GEX_OFFSET,
                'params': {'call_offset_pct': 2.0, 'put_offset_pct': 2.0},
                'label': 'Zero GEX +/- 2.0%'
            },
            {
                'method': StrikeSelectionMethod.ATM_OFFSET,
                'params': {'offset_pct': 1.5},
                'label': 'ATM +/- 1.5%'
            },
            {
                'method': StrikeSelectionMethod.ATM_OFFSET,
                'params': {'offset_pct': 2.0},
                'label': 'ATM +/- 2.0%'
            },
            {
                'method': StrikeSelectionMethod.ATM_OFFSET,
                'params': {'offset_pct': 2.5},
                'label': 'ATM +/- 2.5%'
            },
            {
                'method': StrikeSelectionMethod.DELTA_BASED,
                'params': {'target_delta': 0.25},
                'label': '0.25 Delta'
            },
            {
                'method': StrikeSelectionMethod.DELTA_BASED,
                'params': {'target_delta': 0.30},
                'label': '0.30 Delta'
            }
        ]

        results = []

        for config in methods_to_test:
            print(f"\nTesting: {config['label']}")
            print("-" * 40)

            try:
                # Run backtest
                backtest_results = self.backtester.backtest(
                    start_date=start_date,
                    end_date=end_date,
                    strike_method=config['method'],
                    strike_params=config['params'],
                    exit_strategy='technical',
                    entry_hour=15,
                    exit_hour=10
                )

                # Calculate performance
                performance = self.backtester.generate_performance_report(backtest_results)

                if 'error' not in performance:
                    results.append({
                        'method': config['label'],
                        **performance
                    })

                    print(f"  Total Trades: {performance['total_trades']}")
                    print(f"  Win Rate: {performance['win_rate']:.1%}")
                    print(f"  Total P&L: ${performance['total_pnl']:.2f}")
                    print(f"  Avg P&L%: {performance['avg_pnl_pct']:.1f}%")
                    print(f"  Profit Factor: {performance['profit_factor']:.2f}x")

            except Exception as e:
                print(f"  Error: {e}")

        return pd.DataFrame(results)

    def optimize_exit_strategy(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Test different exit strategies

        Args:
            start_date: Start date for backtesting
            end_date: End date for backtesting

        Returns:
            DataFrame with results for each exit strategy
        """
        print("\n" + "="*80)
        print("OPTIMIZING EXIT STRATEGIES")
        print("="*80 + "\n")

        exit_strategies = [
            'technical',
            'profit_target',
            'stop_loss'
        ]

        results = []

        for strategy in exit_strategies:
            print(f"\nTesting Exit Strategy: {strategy}")
            print("-" * 40)

            try:
                # Run backtest
                backtest_results = self.backtester.backtest(
                    start_date=start_date,
                    end_date=end_date,
                    strike_method=StrikeSelectionMethod.GEX_WALLS,
                    exit_strategy=strategy,
                    entry_hour=15,
                    exit_hour=10
                )

                # Calculate performance
                performance = self.backtester.generate_performance_report(backtest_results)

                if 'error' not in performance:
                    results.append({
                        'exit_strategy': strategy,
                        **performance
                    })

                    print(f"  Total Trades: {performance['total_trades']}")
                    print(f"  Win Rate: {performance['win_rate']:.1%}")
                    print(f"  Total P&L: ${performance['total_pnl']:.2f}")
                    print(f"  Avg P&L%: {performance['avg_pnl_pct']:.1f}%")

            except Exception as e:
                print(f"  Error: {e}")

        return pd.DataFrame(results)

    def optimize_entry_time(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Test different entry times

        Args:
            start_date: Start date for backtesting
            end_date: End date for backtesting

        Returns:
            DataFrame with results for each entry time
        """
        print("\n" + "="*80)
        print("OPTIMIZING ENTRY TIME")
        print("="*80 + "\n")

        entry_hours = [14, 15, 16]  # 2pm, 3pm, 4pm ET

        results = []

        for hour in entry_hours:
            print(f"\nTesting Entry Time: {hour}:00 ET")
            print("-" * 40)

            try:
                # Run backtest
                backtest_results = self.backtester.backtest(
                    start_date=start_date,
                    end_date=end_date,
                    strike_method=StrikeSelectionMethod.GEX_WALLS,
                    exit_strategy='technical',
                    entry_hour=hour,
                    exit_hour=10
                )

                # Calculate performance
                performance = self.backtester.generate_performance_report(backtest_results)

                if 'error' not in performance:
                    results.append({
                        'entry_hour': f"{hour}:00 ET",
                        **performance
                    })

                    print(f"  Total Trades: {performance['total_trades']}")
                    print(f"  Win Rate: {performance['win_rate']:.1%}")
                    print(f"  Total P&L: ${performance['total_pnl']:.2f}")

            except Exception as e:
                print(f"  Error: {e}")

        return pd.DataFrame(results)

    def run_full_optimization(self, start_date: str, end_date: str) -> Dict:
        """
        Run complete optimization suite

        Args:
            start_date: Start date for optimization
            end_date: End date for optimization

        Returns:
            Dictionary with all optimization results
        """
        print("\n" + "="*80)
        print("FULL STRATEGY OPTIMIZATION")
        print(f"Date Range: {start_date} to {end_date}")
        print("="*80)

        results = {}

        # 1. Optimize strike selection
        strike_results = self.optimize_strike_selection(start_date, end_date)
        results['strike_selection'] = strike_results

        # 2. Optimize exit strategy
        exit_results = self.optimize_exit_strategy(start_date, end_date)
        results['exit_strategy'] = exit_results

        # 3. Optimize entry time
        entry_time_results = self.optimize_entry_time(start_date, end_date)
        results['entry_time'] = entry_time_results

        # Find best configuration
        if not strike_results.empty:
            best_strike = strike_results.nlargest(1, 'total_pnl').iloc[0]
            results['best_strike_method'] = best_strike.to_dict()

        if not exit_results.empty:
            best_exit = exit_results.nlargest(1, 'total_pnl').iloc[0]
            results['best_exit_strategy'] = best_exit.to_dict()

        if not entry_time_results.empty:
            best_entry = entry_time_results.nlargest(1, 'total_pnl').iloc[0]
            results['best_entry_time'] = best_entry.to_dict()

        return results


def main():
    """Run optimization"""

    # Connect to database
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', 5432),
        database=os.getenv('POSTGRES_DB', 'gexdb'),
        user=os.getenv('POSTGRES_USER', 'gexuser'),
        password=os.getenv('POSTGRES_PASSWORD')
    )

    # Create optimizer
    optimizer = StrategyOptimizer(conn)

    # Run optimization
    results = optimizer.run_full_optimization(
        start_date='2025-03-18',
        end_date='2025-11-28'
    )

    # Save results
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)

    # Save strike selection results
    if 'strike_selection' in results and not results['strike_selection'].empty:
        results['strike_selection'].to_csv(f'{output_dir}/optimization_strike_selection.csv', index=False)
        print(f"\nStrike selection results saved to: {output_dir}/optimization_strike_selection.csv")

    # Save exit strategy results
    if 'exit_strategy' in results and not results['exit_strategy'].empty:
        results['exit_strategy'].to_csv(f'{output_dir}/optimization_exit_strategy.csv', index=False)
        print(f"Exit strategy results saved to: {output_dir}/optimization_exit_strategy.csv")

    # Save entry time results
    if 'entry_time' in results and not results['entry_time'].empty:
        results['entry_time'].to_csv(f'{output_dir}/optimization_entry_time.csv', index=False)
        print(f"Entry time results saved to: {output_dir}/optimization_entry_time.csv")

    # Print summary
    print("\n" + "="*80)
    print("OPTIMIZATION SUMMARY - BEST CONFIGURATIONS")
    print("="*80)

    if 'best_strike_method' in results:
        print("\nBEST STRIKE SELECTION METHOD:")
        print(f"  Method: {results['best_strike_method']['method']}")
        print(f"  Win Rate: {results['best_strike_method']['win_rate']:.1%}")
        print(f"  Total P&L: ${results['best_strike_method']['total_pnl']:.2f}")
        print(f"  Avg P&L%: {results['best_strike_method']['avg_pnl_pct']:.1f}%")
        print(f"  Profit Factor: {results['best_strike_method']['profit_factor']:.2f}x")

    if 'best_exit_strategy' in results:
        print("\nBEST EXIT STRATEGY:")
        print(f"  Strategy: {results['best_exit_strategy']['exit_strategy']}")
        print(f"  Win Rate: {results['best_exit_strategy']['win_rate']:.1%}")
        print(f"  Total P&L: ${results['best_exit_strategy']['total_pnl']:.2f}")

    if 'best_entry_time' in results:
        print("\nBEST ENTRY TIME:")
        print(f"  Time: {results['best_entry_time']['entry_hour']}")
        print(f"  Win Rate: {results['best_entry_time']['win_rate']:.1%}")
        print(f"  Total P&L: ${results['best_entry_time']['total_pnl']:.2f}")

    # Save summary JSON
    summary = {
        'best_strike_method': results.get('best_strike_method'),
        'best_exit_strategy': results.get('best_exit_strategy'),
        'best_entry_time': results.get('best_entry_time'),
        'optimization_date': datetime.now().isoformat()
    }

    with open(f'{output_dir}/optimization_summary.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\nOptimization summary saved to: {output_dir}/optimization_summary.json")
    print("="*80 + "\n")

    conn.close()


if __name__ == "__main__":
    main()
