#!/usr/bin/env python3
"""
Options Strangle Backtesting Framework

Backtests a long-only strangle strategy:
1. Buy strangle near market close (15:00-16:00) with next-day expiration
2. Strike selection based on GEX levels and technical analysis
3. Evaluate at next market open whether to hold or sell each leg
4. Optimize parameters and generate performance reports
"""

import psycopg2
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta, time
from typing import Dict, List, Tuple, Optional
import json
from dataclasses import dataclass, asdict
from enum import Enum

load_dotenv()


class StrikeSelectionMethod(Enum):
    """Methods for selecting strangle strikes"""
    GEX_WALLS = "gex_walls"  # Use max GEX levels (call/put walls)
    ZERO_GEX_OFFSET = "zero_gex_offset"  # Offset from Zero GEX level
    DELTA_BASED = "delta_based"  # Use specific delta targets
    ATM_OFFSET = "atm_offset"  # Fixed % offset from current price
    SUPPORT_RESISTANCE = "support_resistance"  # S/R from GEX


class ExitSignal(Enum):
    """Exit decision signals"""
    HOLD = "hold"
    SELL_CALL = "sell_call"
    SELL_PUT = "sell_put"
    SELL_BOTH = "sell_both"


@dataclass
class StranglePosition:
    """Represents a strangle position"""
    entry_date: str
    entry_time: str
    exit_date: Optional[str]
    exit_time: Optional[str]

    # Entry details
    entry_spx_price: float
    call_strike: float
    put_strike: float
    call_entry_price: float
    put_entry_price: float
    total_entry_cost: float

    # Exit details
    call_exit_price: Optional[float]
    put_exit_price: Optional[float]
    total_exit_value: Optional[float]

    # Market context at entry
    zero_gex_level: Optional[float]
    max_call_gex_strike: Optional[float]
    max_put_gex_strike: Optional[float]

    # Signals
    gex_signal: str
    trend_signal: Optional[str]

    # P&L
    pnl: Optional[float]
    pnl_pct: Optional[float]

    # Metadata
    expiration_date: str
    days_to_expiry: int
    exit_reason: Optional[str]


class StrangleBacktester:
    """Backtester for options strangle strategies"""

    def __init__(self, db_connection):
        """
        Initialize backtester

        Args:
            db_connection: PostgreSQL database connection
        """
        self.db = db_connection
        self.positions: List[StranglePosition] = []

    def get_eod_snapshot(self, trade_date: str, target_hour: int = 15) -> pd.DataFrame:
        """
        Get end-of-day snapshot for a given date

        Args:
            trade_date: Date in YYYY-MM-DD format
            target_hour: Target hour for EOD (default: 15 = 3pm ET)

        Returns:
            DataFrame with EOD options data
        """
        query = """
        WITH snapshots_today AS (
            SELECT
                "greeks.updated_at",
                EXTRACT(HOUR FROM "greeks.updated_at") as hour,
                ABS(EXTRACT(HOUR FROM "greeks.updated_at") - %s) as hour_diff
            FROM gex_table
            WHERE DATE("greeks.updated_at") = %s
        ),
        closest_snapshot AS (
            SELECT "greeks.updated_at"
            FROM snapshots_today
            ORDER BY hour_diff ASC, "greeks.updated_at" DESC
            LIMIT 1
        )
        SELECT
            "greeks.updated_at",
            expiration_date,
            strike,
            option_type,
            last as option_price,
            bid,
            ask,
            volume,
            open_interest,
            gex,
            "greeks.delta",
            "greeks.gamma",
            "greeks.theta",
            "greeks.vega",
            spx_price
        FROM gex_table
        WHERE "greeks.updated_at" = (SELECT "greeks.updated_at" FROM closest_snapshot)
        AND expiration_date > %s
        ORDER BY expiration_date, strike, option_type
        """

        return pd.read_sql(query, self.db, params=(target_hour, trade_date, trade_date))

    def get_open_snapshot(self, trade_date: str, target_hour: int = 10) -> pd.DataFrame:
        """
        Get market open snapshot for a given date

        Args:
            trade_date: Date in YYYY-MM-DD format
            target_hour: Target hour for open (default: 10 = 10am ET)

        Returns:
            DataFrame with market open options data
        """
        return self.get_eod_snapshot(trade_date, target_hour)

    def calculate_zero_gex(self, df: pd.DataFrame) -> Optional[float]:
        """Calculate Zero GEX level from options data"""
        net_gex = df.groupby('strike')['gex'].sum().reset_index()
        net_gex = net_gex.sort_values('strike')

        # Find sign changes
        net_gex['sign_change'] = np.sign(net_gex['gex']).diff()
        crosses = net_gex[net_gex['sign_change'] != 0]

        if len(crosses) == 0:
            return None

        # Return first zero cross
        return float(crosses['strike'].iloc[0])

    def find_gex_walls(self, df: pd.DataFrame, current_price: float) -> Tuple[Optional[float], Optional[float]]:
        """
        Find call and put walls (max GEX levels)

        Args:
            df: Options data
            current_price: Current SPX price

        Returns:
            Tuple of (call_wall_strike, put_wall_strike)
        """
        net_gex = df.groupby('strike')['gex'].sum().reset_index()

        above_price = net_gex[net_gex['strike'] > current_price]
        below_price = net_gex[net_gex['strike'] < current_price]

        call_wall = above_price.nlargest(1, 'gex')['strike'].iloc[0] if len(above_price) > 0 else None
        put_wall = below_price.nsmallest(1, 'gex')['strike'].iloc[0] if len(below_price) > 0 else None

        return call_wall, put_wall

    def select_strikes(self, df: pd.DataFrame, method: StrikeSelectionMethod,
                      **params) -> Tuple[float, float]:
        """
        Select call and put strikes for strangle

        Args:
            df: Options data
            method: Strike selection method
            **params: Method-specific parameters

        Returns:
            Tuple of (call_strike, put_strike)
        """
        current_price = df['spx_price'].iloc[0]

        if method == StrikeSelectionMethod.GEX_WALLS:
            # Use GEX walls as strikes
            call_wall, put_wall = self.find_gex_walls(df, current_price)
            return call_wall or current_price * 1.02, put_wall or current_price * 0.98

        elif method == StrikeSelectionMethod.ZERO_GEX_OFFSET:
            # Use offset from zero GEX
            zero_gex = self.calculate_zero_gex(df)
            if zero_gex is None:
                zero_gex = current_price

            call_offset_pct = params.get('call_offset_pct', 1.5)
            put_offset_pct = params.get('put_offset_pct', 1.5)

            call_strike = current_price * (1 + call_offset_pct / 100)
            put_strike = current_price * (1 - put_offset_pct / 100)

            # Round to nearest available strike
            call_strike = self._round_to_strike(df, call_strike, 'call')
            put_strike = self._round_to_strike(df, put_strike, 'put')

            return call_strike, put_strike

        elif method == StrikeSelectionMethod.DELTA_BASED:
            # Select by delta (e.g., 0.30 delta)
            target_delta = params.get('target_delta', 0.30)

            calls = df[(df['option_type'] == 'call') & (df['greeks.delta'].notna())]
            puts = df[(df['option_type'] == 'put') & (df['greeks.delta'].notna())]

            if len(calls) > 0 and len(puts) > 0:
                call_strike = calls.iloc[(calls['greeks.delta'] - target_delta).abs().argsort()[0]]['strike']
                put_strike = puts.iloc[(puts['greeks.delta'] + target_delta).abs().argsort()[0]]['strike']
                return float(call_strike), float(put_strike)

        elif method == StrikeSelectionMethod.ATM_OFFSET:
            # Fixed percentage offset from ATM
            offset_pct = params.get('offset_pct', 2.0)

            call_strike = current_price * (1 + offset_pct / 100)
            put_strike = current_price * (1 - offset_pct / 100)

            call_strike = self._round_to_strike(df, call_strike, 'call')
            put_strike = self._round_to_strike(df, put_strike, 'put')

            return call_strike, put_strike

        # Default fallback
        return current_price * 1.02, current_price * 0.98

    def _round_to_strike(self, df: pd.DataFrame, target_strike: float,
                        option_type: str) -> float:
        """Round to nearest available strike"""
        options = df[df['option_type'] == option_type]
        if len(options) == 0:
            return target_strike

        closest = options.iloc[(options['strike'] - target_strike).abs().argsort()[0]]
        return float(closest['strike'])

    def get_option_price(self, df: pd.DataFrame, strike: float,
                        option_type: str) -> Optional[float]:
        """Get option price for a given strike"""
        option = df[(df['strike'] == strike) & (df['option_type'] == option_type)]

        if len(option) == 0:
            return None

        # Prioritize last traded price
        last_price = option['option_price'].iloc[0]
        if pd.notna(last_price) and last_price > 0:
            return last_price

        # Fallback to mid price (bid + ask) / 2
        bid = option['bid'].iloc[0]
        ask = option['ask'].iloc[0]

        if pd.notna(bid) and pd.notna(ask) and bid > 0 and ask > 0:
            return (bid + ask) / 2

        return None

    def evaluate_exit_signal(self, position: StranglePosition,
                            current_df: pd.DataFrame,
                            exit_strategy: str = 'technical') -> ExitSignal:
        """
        Evaluate whether to hold or exit position

        Args:
            position: Current position
            current_df: Current market data
            exit_strategy: Strategy for exit ('technical', 'profit_target', 'stop_loss')

        Returns:
            ExitSignal enum
        """
        current_price = current_df['spx_price'].iloc[0]

        if exit_strategy == 'profit_target':
            # Check if either leg is profitable
            call_price = self.get_option_price(current_df, position.call_strike, 'call')
            put_price = self.get_option_price(current_df, position.put_strike, 'put')

            if call_price and call_price > position.call_entry_price * 1.2:
                return ExitSignal.SELL_CALL
            if put_price and put_price > position.put_entry_price * 1.2:
                return ExitSignal.SELL_PUT

        elif exit_strategy == 'stop_loss':
            # Exit if losing more than threshold
            call_price = self.get_option_price(current_df, position.call_strike, 'call')
            put_price = self.get_option_price(current_df, position.put_strike, 'put')

            if call_price and put_price:
                total_value = call_price + put_price
                if total_value < position.total_entry_cost * 0.7:
                    return ExitSignal.SELL_BOTH

        elif exit_strategy == 'technical':
            # Use GEX and trend signals
            zero_gex = self.calculate_zero_gex(current_df)

            # Bearish: price below zero GEX and trending down
            if zero_gex and current_price < zero_gex:
                # Keep put, sell call if losing
                call_price = self.get_option_price(current_df, position.call_strike, 'call')
                if call_price and call_price < position.call_entry_price * 0.8:
                    return ExitSignal.SELL_CALL

            # Bullish: price above zero GEX and trending up
            elif zero_gex and current_price > zero_gex:
                # Keep call, sell put if losing
                put_price = self.get_option_price(current_df, position.put_strike, 'put')
                if put_price and put_price < position.put_entry_price * 0.8:
                    return ExitSignal.SELL_PUT

        return ExitSignal.HOLD

    def backtest(self, start_date: str, end_date: str,
                strike_method: StrikeSelectionMethod = StrikeSelectionMethod.GEX_WALLS,
                exit_strategy: str = 'technical',
                strike_params: Optional[Dict] = None,
                entry_hour: int = 15,
                exit_hour: int = 10) -> pd.DataFrame:
        """
        Run backtest over date range

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            strike_method: Method for selecting strikes
            exit_strategy: Strategy for exiting positions
            strike_params: Parameters for strike selection
            entry_hour: Hour to enter positions (default 15 = 3pm)
            exit_hour: Hour to evaluate exits (default 10 = 10am)

        Returns:
            DataFrame with backtest results
        """
        if strike_params is None:
            strike_params = {}

        print(f"\n{'='*80}")
        print(f"BACKTESTING STRANGLE STRATEGY")
        print(f"{'='*80}")
        print(f"Date range: {start_date} to {end_date}")
        print(f"Strike selection: {strike_method.value}")
        print(f"Exit strategy: {exit_strategy}")
        print(f"Entry time: {entry_hour}:00 ET")
        print(f"Exit evaluation: {exit_hour}:00 ET")
        print(f"{'='*80}\n")

        # Get all trading dates
        trading_dates_query = """
        SELECT DISTINCT DATE("greeks.updated_at") as trade_date
        FROM gex_table
        WHERE DATE("greeks.updated_at") >= %s
        AND DATE("greeks.updated_at") <= %s
        ORDER BY trade_date
        """

        trading_dates = pd.read_sql(trading_dates_query, self.db,
                                    params=(start_date, end_date))

        print(f"Found {len(trading_dates)} trading dates\n")

        for i, row in trading_dates.iterrows():
            trade_date = str(row['trade_date'])

            # Get EOD snapshot for entry
            try:
                eod_df = self.get_eod_snapshot(trade_date, entry_hour)

                if len(eod_df) == 0:
                    print(f"[{trade_date}] No EOD data available")
                    continue

                # Filter for next-day expiration
                next_day = (pd.to_datetime(trade_date) + timedelta(days=1)).strftime('%Y-%m-%d')
                eod_df['expiration_date'] = pd.to_datetime(eod_df['expiration_date'])
                next_day_options = eod_df[eod_df['expiration_date'].dt.strftime('%Y-%m-%d') == next_day]

                if len(next_day_options) == 0:
                    print(f"[{trade_date}] No next-day expiration options")
                    continue

                # Calculate GEX metrics
                current_price = next_day_options['spx_price'].iloc[0]
                zero_gex = self.calculate_zero_gex(next_day_options)
                call_wall, put_wall = self.find_gex_walls(next_day_options, current_price)

                # Select strikes
                call_strike, put_strike = self.select_strikes(
                    next_day_options, strike_method, **strike_params
                )

                # Get option prices
                call_price = self.get_option_price(next_day_options, call_strike, 'call')
                put_price = self.get_option_price(next_day_options, put_strike, 'put')

                if call_price is None or put_price is None:
                    print(f"[{trade_date}] Could not get option prices")
                    continue

                # Create position
                position = StranglePosition(
                    entry_date=trade_date,
                    entry_time=next_day_options['greeks.updated_at'].iloc[0].strftime('%H:%M:%S'),
                    exit_date=None,
                    exit_time=None,
                    entry_spx_price=current_price,
                    call_strike=call_strike,
                    put_strike=put_strike,
                    call_entry_price=call_price,
                    put_entry_price=put_price,
                    total_entry_cost=call_price + put_price,
                    call_exit_price=None,
                    put_exit_price=None,
                    total_exit_value=None,
                    zero_gex_level=zero_gex,
                    max_call_gex_strike=call_wall,
                    max_put_gex_strike=put_wall,
                    gex_signal="BUY" if zero_gex and current_price > zero_gex else "SELL" if zero_gex else "NEUTRAL",
                    trend_signal=None,
                    pnl=None,
                    pnl_pct=None,
                    expiration_date=next_day,
                    days_to_expiry=1,
                    exit_reason=None
                )

                print(f"[{trade_date}] ENTRY: SPX=${current_price:.2f}, Call=${call_strike}, Put=${put_strike}, Cost=${position.total_entry_cost:.2f}")

                # Get next day open for exit evaluation
                try:
                    next_open_df = self.get_open_snapshot(next_day, exit_hour)

                    if len(next_open_df) > 0:
                        # Evaluate exit
                        exit_signal = self.evaluate_exit_signal(position, next_open_df, exit_strategy)

                        call_exit_price = self.get_option_price(next_open_df, call_strike, 'call')
                        put_exit_price = self.get_option_price(next_open_df, put_strike, 'put')

                        if call_exit_price and put_exit_price:
                            position.exit_date = next_day
                            position.exit_time = next_open_df['greeks.updated_at'].iloc[0].strftime('%H:%M:%S')
                            position.call_exit_price = call_exit_price
                            position.put_exit_price = put_exit_price
                            position.total_exit_value = call_exit_price + put_exit_price
                            position.pnl = position.total_exit_value - position.total_entry_cost
                            position.pnl_pct = (position.pnl / position.total_entry_cost) * 100
                            position.exit_reason = exit_signal.value

                            print(f"  [{next_day}] EXIT: Value=${position.total_exit_value:.2f}, P&L=${position.pnl:.2f} ({position.pnl_pct:+.1f}%)")

                except Exception as e:
                    print(f"  [{next_day}] Could not evaluate exit: {e}")

                self.positions.append(position)

            except Exception as e:
                print(f"[{trade_date}] Error: {e}")
                continue

        # Convert to DataFrame
        results_df = pd.DataFrame([asdict(p) for p in self.positions])

        return results_df

    def generate_performance_report(self, results_df: pd.DataFrame) -> Dict:
        """Generate performance metrics from backtest results"""

        if len(results_df) == 0:
            return {"error": "No trades executed"}

        # Filter completed trades
        completed = results_df[results_df['pnl'].notna()].copy()

        if len(completed) == 0:
            return {"error": "No completed trades"}

        # Calculate metrics
        total_trades = len(completed)
        winning_trades = len(completed[completed['pnl'] > 0])
        losing_trades = len(completed[completed['pnl'] < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        total_pnl = completed['pnl'].sum()
        avg_pnl = completed['pnl'].mean()
        avg_win = completed[completed['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = completed[completed['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0

        max_win = completed['pnl'].max()
        max_loss = completed['pnl'].min()

        # Calculate profit factor
        gross_profit = completed[completed['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(completed[completed['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Sharpe-like ratio (simplified)
        sharpe = completed['pnl'].mean() / completed['pnl'].std() if completed['pnl'].std() > 0 else 0

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_pnl": avg_pnl,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "max_win": max_win,
            "max_loss": max_loss,
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe,
            "avg_pnl_pct": completed['pnl_pct'].mean(),
            "total_premium_deployed": completed['total_entry_cost'].sum()
        }


def main():
    """Example usage"""

    # Connect to database
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', 5432),
        database=os.getenv('POSTGRES_DB', 'gexdb'),
        user=os.getenv('POSTGRES_USER', 'gexuser'),
        password=os.getenv('POSTGRES_PASSWORD')
    )

    # Create backtester
    backtester = StrangleBacktester(conn)

    # Run backtest
    results = backtester.backtest(
        start_date='2025-03-18',
        end_date='2025-11-28',
        strike_method=StrikeSelectionMethod.GEX_WALLS,
        exit_strategy='technical',
        entry_hour=15,
        exit_hour=10
    )

    # Save results
    output_path = 'output/strangle_backtest_results.csv'
    os.makedirs('output', exist_ok=True)
    results.to_csv(output_path, index=False)
    print(f"\nResults saved to: {output_path}")

    # Generate performance report
    performance = backtester.generate_performance_report(results)

    print(f"\n{'='*80}")
    print("PERFORMANCE SUMMARY")
    print(f"{'='*80}")
    for key, value in performance.items():
        if isinstance(value, float):
            if 'rate' in key or 'ratio' in key:
                print(f"{key:30s}: {value:.2%}" if value < 10 else f"{key:30s}: {value:.2f}")
            else:
                print(f"{key:30s}: ${value:,.2f}")
        else:
            print(f"{key:30s}: {value}")
    print(f"{'='*80}\n")

    # Save performance report
    perf_path = 'output/strangle_performance.json'
    with open(perf_path, 'w') as f:
        json.dump(performance, f, indent=2, default=str)
    print(f"Performance report saved to: {perf_path}\n")

    conn.close()


if __name__ == "__main__":
    main()
