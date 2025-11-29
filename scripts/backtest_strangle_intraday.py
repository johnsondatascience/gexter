#!/usr/bin/env python3
"""
Intraday Options Strangle Backtesting Framework

Enhanced strategy allowing independent entry and exit of each leg throughout the trading day.

Key Features:
- Buy and sell each leg independently
- Multiple intraday opportunities
- Dynamic position management
- Profit-taking and stop-loss per leg
"""

import psycopg2
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
from dataclasses import dataclass, asdict
from enum import Enum

load_dotenv()


class LegType(Enum):
    """Option leg type"""
    CALL = "call"
    PUT = "put"


class LegStatus(Enum):
    """Status of an option leg"""
    OPEN = "open"
    CLOSED = "closed"


@dataclass
class OptionLeg:
    """Represents a single option leg (call or put)"""
    leg_id: str
    leg_type: LegType
    entry_date: str
    entry_time: str
    entry_spx_price: float
    strike: float
    entry_price: float

    exit_date: Optional[str] = None
    exit_time: Optional[str] = None
    exit_spx_price: Optional[float] = None
    exit_price: Optional[float] = None

    status: LegStatus = LegStatus.OPEN
    exit_reason: Optional[str] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None

    # Context
    zero_gex_at_entry: Optional[float] = None
    gex_signal_at_entry: Optional[str] = None


@dataclass
class IntradayTrade:
    """Represents a complete trading session (may have multiple legs)"""
    trade_id: str
    date: str
    call_legs: List[OptionLeg]
    put_legs: List[OptionLeg]
    total_pnl: float = 0.0
    total_premium_deployed: float = 0.0


class IntradayStrangleBacktester:
    """Backtest strangle strategy with intraday independent leg trading"""

    def __init__(self, db_connection):
        self.db = db_connection
        self.trades: List[IntradayTrade] = []
        self.active_legs: Dict[str, OptionLeg] = {}  # leg_id -> OptionLeg

    def get_intraday_snapshots(self, trade_date: str) -> pd.DataFrame:
        """
        Get all available snapshots for a given trading day

        Args:
            trade_date: Date in YYYY-MM-DD format

        Returns:
            DataFrame with all snapshots and their timestamps
        """
        query = """
        SELECT DISTINCT "greeks.updated_at" as snapshot_time
        FROM gex_table
        WHERE DATE("greeks.updated_at") = %s
        ORDER BY snapshot_time
        """

        return pd.read_sql(query, self.db, params=(trade_date,))

    def get_snapshot_data(self, snapshot_time: str) -> pd.DataFrame:
        """
        Get options data for a specific snapshot

        Args:
            snapshot_time: Timestamp for snapshot

        Returns:
            DataFrame with options data
        """
        query = """
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
        WHERE "greeks.updated_at" = %s
        ORDER BY expiration_date, strike, option_type
        """

        return pd.read_sql(query, self.db, params=(snapshot_time,))

    def calculate_zero_gex(self, df: pd.DataFrame) -> Optional[float]:
        """Calculate Zero GEX level"""
        net_gex = df.groupby('strike')['gex'].sum().reset_index()
        net_gex = net_gex.sort_values('strike')
        net_gex['sign_change'] = np.sign(net_gex['gex']).diff()
        crosses = net_gex[net_gex['sign_change'] != 0]

        if len(crosses) == 0:
            return None

        return float(crosses['strike'].iloc[0])

    def find_gex_walls(self, df: pd.DataFrame, current_price: float) -> Tuple[Optional[float], Optional[float]]:
        """Find call and put walls"""
        net_gex = df.groupby('strike')['gex'].sum().reset_index()

        above_price = net_gex[net_gex['strike'] > current_price]
        below_price = net_gex[net_gex['strike'] < current_price]

        call_wall = above_price.nlargest(1, 'gex')['strike'].iloc[0] if len(above_price) > 0 else None
        put_wall = below_price.nsmallest(1, 'gex')['strike'].iloc[0] if len(below_price) > 0 else None

        return call_wall, put_wall

    def get_gex_signal(self, df: pd.DataFrame, current_price: float) -> str:
        """Determine GEX signal (BUY/SELL/NEUTRAL)"""
        zero_gex = self.calculate_zero_gex(df)

        if zero_gex is None:
            return "NEUTRAL"

        if current_price > zero_gex:
            return "BUY"
        elif current_price < zero_gex:
            return "SELL"
        else:
            return "NEUTRAL"

    def get_option_price(self, df: pd.DataFrame, strike: float, option_type: str) -> Optional[float]:
        """Get option price (prioritize last traded price)"""
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

    def should_enter_call(self, df: pd.DataFrame, current_price: float,
                         call_wall: Optional[float], gex_signal: str) -> Tuple[bool, Optional[float]]:
        """
        Determine if we should buy a call

        Args:
            df: Current snapshot data
            current_price: Current SPX price
            call_wall: Call wall strike
            gex_signal: Current GEX signal

        Returns:
            Tuple of (should_enter, strike)
        """
        # Entry conditions:
        # 1. BUY signal (bullish regime)
        # 2. Have a call wall to target
        # 3. Not already holding a call at this strike

        if gex_signal != "BUY":
            return False, None

        if call_wall is None:
            return False, None

        # Check if we already have a call at this strike
        for leg_id, leg in self.active_legs.items():
            if leg.leg_type == LegType.CALL and leg.strike == call_wall:
                return False, None

        return True, call_wall

    def should_enter_put(self, df: pd.DataFrame, current_price: float,
                        put_wall: Optional[float], gex_signal: str) -> Tuple[bool, Optional[float]]:
        """
        Determine if we should buy a put

        Args:
            df: Current snapshot data
            current_price: Current SPX price
            put_wall: Put wall strike
            gex_signal: Current GEX signal

        Returns:
            Tuple of (should_enter, strike)
        """
        # Entry conditions:
        # 1. SELL signal (bearish regime) OR hedging in volatile conditions
        # 2. Have a put wall to target
        # 3. Not already holding a put at this strike

        if gex_signal != "SELL":
            # Could also enter puts as hedge in BUY regime, but let's keep it directional for now
            return False, None

        if put_wall is None:
            return False, None

        # Check if we already have a put at this strike
        for leg_id, leg in self.active_legs.items():
            if leg.leg_type == LegType.PUT and leg.strike == put_wall:
                return False, None

        return True, put_wall

    def should_exit_leg(self, leg: OptionLeg, current_price: float,
                       current_df: pd.DataFrame,
                       current_date: str,
                       profit_target_pct: float = 25.0,
                       stop_loss_pct: float = 40.0,
                       avoid_pdt: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Determine if we should exit a leg

        Args:
            leg: The option leg
            current_price: Current option price
            current_df: Current snapshot data
            current_date: Current trading date (for PDT check)
            profit_target_pct: Take profit at this % gain
            stop_loss_pct: Cut losses at this % loss
            avoid_pdt: If True, avoid round-trip trades on same day (PDT rule)

        Returns:
            Tuple of (should_exit, reason)
        """
        # PDT PROTECTION: Don't exit if entered today (would create day trade)
        if avoid_pdt and leg.entry_date == current_date:
            return False, None

        option_price = self.get_option_price(
            current_df,
            leg.strike,
            leg.leg_type.value
        )

        if option_price is None:
            return False, None

        pnl_pct = ((option_price - leg.entry_price) / leg.entry_price) * 100

        # Profit target
        if pnl_pct >= profit_target_pct:
            return True, f"profit_target_{profit_target_pct}%"

        # Stop loss
        if pnl_pct <= -stop_loss_pct:
            return True, f"stop_loss_{stop_loss_pct}%"

        # Expiration day - close all positions
        # (We're trading 0DTE or near expiration, so close before 3:50pm or end of day)
        snapshot_time = pd.to_datetime(current_df['greeks.updated_at'].iloc[0])
        if snapshot_time.hour >= 15:  # After 3pm, start managing risk
            # Close losing positions to avoid theta decay
            if pnl_pct < -10:
                return True, "eod_risk_management"

        return False, None

    def backtest_intraday(self, start_date: str, end_date: str,
                         profit_target_pct: float = 25.0,
                         stop_loss_pct: float = 40.0,
                         max_legs_per_type: int = 2) -> pd.DataFrame:
        """
        Run intraday backtest with independent leg trading

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            profit_target_pct: Take profit at this % gain
            stop_loss_pct: Cut losses at this % loss
            max_legs_per_type: Maximum number of legs per type (call/put) at once

        Returns:
            DataFrame with all leg results
        """
        print(f"\n{'='*80}")
        print(f"INTRADAY STRANGLE BACKTESTING")
        print(f"{'='*80}")
        print(f"Date range: {start_date} to {end_date}")
        print(f"Profit target: {profit_target_pct}%")
        print(f"Stop loss: {stop_loss_pct}%")
        print(f"Max legs per type: {max_legs_per_type}")
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

        all_legs = []
        leg_counter = 0

        for i, row in trading_dates.iterrows():
            trade_date = str(row['trade_date'])

            # Get all snapshots for this day first
            snapshots = self.get_intraday_snapshots(trade_date)

            if len(snapshots) == 0:
                # No snapshots today, but close any overnight positions anyway
                for leg_id, leg in list(self.active_legs.items()):
                    print(f"[{trade_date}] Closing overnight position (no data): {leg.leg_type.value} at ${leg.strike}")
                    leg.exit_date = trade_date
                    leg.exit_time = "09:30:00"
                    leg.status = LegStatus.CLOSED
                    leg.exit_reason = "overnight_close_no_data"
                    all_legs.append(leg)
                    del self.active_legs[leg_id]
                continue

            print(f"[{trade_date}] Processing {len(snapshots)} snapshots")

            # Close overnight positions using first snapshot of the day
            if len(self.active_legs) > 0 and len(snapshots) > 0:
                first_snapshot_time = snapshots.iloc[0]['snapshot_time']
                first_snapshot_df = self.get_snapshot_data(first_snapshot_time)

                if len(first_snapshot_df) > 0:
                    for leg_id, leg in list(self.active_legs.items()):
                        # Only close if opened on a previous day
                        if leg.entry_date != trade_date:
                            exit_price = self.get_option_price(
                                first_snapshot_df, leg.strike, leg.leg_type.value
                            )

                            if exit_price:
                                leg.exit_date = trade_date
                                leg.exit_time = pd.to_datetime(first_snapshot_time).strftime('%H:%M:%S')
                                leg.exit_spx_price = first_snapshot_df['spx_price'].iloc[0]
                                leg.exit_price = exit_price
                                leg.status = LegStatus.CLOSED
                                leg.exit_reason = "overnight_close"
                                leg.pnl = exit_price - leg.entry_price
                                leg.pnl_pct = (leg.pnl / leg.entry_price) * 100

                                print(f"  [OPEN] CLOSE overnight {leg.leg_type.value.upper()} ${leg.strike}: "
                                      f"${leg.entry_price:.2f} -> ${exit_price:.2f} = {leg.pnl_pct:+.1f}%")

                                all_legs.append(leg)
                                del self.active_legs[leg_id]

            for _, snapshot_row in snapshots.iterrows():
                snapshot_time = snapshot_row['snapshot_time']

                try:
                    # Get data for this snapshot
                    df = self.get_snapshot_data(snapshot_time)

                    if len(df) == 0:
                        continue

                    # Filter for next-day or 0DTE options
                    df['expiration_date'] = pd.to_datetime(df['expiration_date'])
                    snapshot_date = pd.to_datetime(snapshot_time).date()

                    # Include 0DTE and 1DTE
                    df['days_to_expiry'] = (df['expiration_date'].dt.date - snapshot_date).apply(lambda x: x.days)
                    df_tradeable = df[df['days_to_expiry'] <= 1].copy()

                    if len(df_tradeable) == 0:
                        continue

                    current_price = df_tradeable['spx_price'].iloc[0]
                    zero_gex = self.calculate_zero_gex(df_tradeable)
                    call_wall, put_wall = self.find_gex_walls(df_tradeable, current_price)
                    gex_signal = self.get_gex_signal(df_tradeable, current_price)

                    # 1. Check if we should exit any active legs
                    for leg_id, leg in list(self.active_legs.items()):
                        should_exit, reason = self.should_exit_leg(
                            leg, current_price, df_tradeable, trade_date,
                            profit_target_pct, stop_loss_pct, avoid_pdt=True
                        )

                        if should_exit:
                            exit_price = self.get_option_price(
                                df_tradeable, leg.strike, leg.leg_type.value
                            )

                            if exit_price:
                                leg.exit_date = trade_date
                                leg.exit_time = pd.to_datetime(snapshot_time).strftime('%H:%M:%S')
                                leg.exit_spx_price = current_price
                                leg.exit_price = exit_price
                                leg.status = LegStatus.CLOSED
                                leg.exit_reason = reason
                                leg.pnl = exit_price - leg.entry_price
                                leg.pnl_pct = (leg.pnl / leg.entry_price) * 100

                                print(f"  [{pd.to_datetime(snapshot_time).strftime('%H:%M')}] EXIT {leg.leg_type.value.upper()} ${leg.strike}: "
                                      f"${leg.entry_price:.2f} -> ${exit_price:.2f} = {leg.pnl_pct:+.1f}% ({reason})")

                                all_legs.append(leg)
                                del self.active_legs[leg_id]

                    # 2. Check if we should enter new legs
                    # Count active legs by type
                    active_calls = sum(1 for leg in self.active_legs.values() if leg.leg_type == LegType.CALL)
                    active_puts = sum(1 for leg in self.active_legs.values() if leg.leg_type == LegType.PUT)

                    # Try to enter a call
                    if active_calls < max_legs_per_type:
                        should_enter, call_strike = self.should_enter_call(
                            df_tradeable, current_price, call_wall, gex_signal
                        )

                        if should_enter and call_strike:
                            call_price = self.get_option_price(df_tradeable, call_strike, 'call')

                            if call_price and call_price > 0:
                                leg_counter += 1
                                leg = OptionLeg(
                                    leg_id=f"{trade_date}_call_{leg_counter}",
                                    leg_type=LegType.CALL,
                                    entry_date=trade_date,
                                    entry_time=pd.to_datetime(snapshot_time).strftime('%H:%M:%S'),
                                    entry_spx_price=current_price,
                                    strike=call_strike,
                                    entry_price=call_price,
                                    zero_gex_at_entry=zero_gex,
                                    gex_signal_at_entry=gex_signal
                                )

                                self.active_legs[leg.leg_id] = leg
                                print(f"  [{pd.to_datetime(snapshot_time).strftime('%H:%M')}] ENTER CALL ${call_strike}: ${call_price:.2f} (SPX=${current_price:.2f}, Signal={gex_signal})")

                    # Try to enter a put
                    if active_puts < max_legs_per_type:
                        should_enter, put_strike = self.should_enter_put(
                            df_tradeable, current_price, put_wall, gex_signal
                        )

                        if should_enter and put_strike:
                            put_price = self.get_option_price(df_tradeable, put_strike, 'put')

                            if put_price and put_price > 0:
                                leg_counter += 1
                                leg = OptionLeg(
                                    leg_id=f"{trade_date}_put_{leg_counter}",
                                    leg_type=LegType.PUT,
                                    entry_date=trade_date,
                                    entry_time=pd.to_datetime(snapshot_time).strftime('%H:%M:%S'),
                                    entry_spx_price=current_price,
                                    strike=put_strike,
                                    entry_price=put_price,
                                    zero_gex_at_entry=zero_gex,
                                    gex_signal_at_entry=gex_signal
                                )

                                self.active_legs[leg.leg_id] = leg
                                print(f"  [{pd.to_datetime(snapshot_time).strftime('%H:%M')}] ENTER PUT ${put_strike}: ${put_price:.2f} (SPX=${current_price:.2f}, Signal={gex_signal})")

                except Exception as e:
                    print(f"  [{snapshot_time}] Error: {e}")
                    continue

        # Close any remaining open legs
        for leg_id, leg in self.active_legs.items():
            leg.status = LegStatus.CLOSED
            leg.exit_reason = "end_of_backtest"
            all_legs.append(leg)

        # Convert to DataFrame
        results_df = pd.DataFrame([asdict(leg) for leg in all_legs])

        # Convert enums to strings
        if len(results_df) > 0:
            results_df['leg_type'] = results_df['leg_type'].apply(lambda x: x if isinstance(x, str) else x.value)
            results_df['status'] = results_df['status'].apply(lambda x: x if isinstance(x, str) else x.value)

        return results_df

    def generate_performance_report(self, results_df: pd.DataFrame) -> Dict:
        """Generate performance metrics from intraday backtest"""

        if len(results_df) == 0:
            return {"error": "No trades executed"}

        completed = results_df[results_df['pnl'].notna()].copy()

        if len(completed) == 0:
            return {"error": "No completed trades"}

        total_trades = len(completed)
        winning_trades = len(completed[completed['pnl'] > 0])
        losing_trades = len(completed[completed['pnl'] < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        total_pnl = completed['pnl'].sum()
        avg_pnl = completed['pnl'].mean()
        avg_win = completed[completed['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = completed[completed['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0

        # Breakdown by leg type
        call_legs = completed[completed['leg_type'] == 'call']
        put_legs = completed[completed['leg_type'] == 'put']

        return {
            'total_legs_traded': total_trades,
            'call_legs': len(call_legs),
            'put_legs': len(put_legs),
            'winning_legs': winning_trades,
            'losing_legs': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl_per_leg': avg_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_win': completed['pnl'].max(),
            'max_loss': completed['pnl'].min(),
            'profit_factor': abs(completed[completed['pnl'] > 0]['pnl'].sum() / completed[completed['pnl'] < 0]['pnl'].sum()) if losing_trades > 0 else float('inf'),
            'total_premium_deployed': completed['entry_price'].sum(),
            'avg_pnl_pct': completed['pnl_pct'].mean(),
            'call_performance': {
                'win_rate': len(call_legs[call_legs['pnl'] > 0]) / len(call_legs) if len(call_legs) > 0 else 0,
                'total_pnl': call_legs['pnl'].sum() if len(call_legs) > 0 else 0,
                'avg_pnl_pct': call_legs['pnl_pct'].mean() if len(call_legs) > 0 else 0
            },
            'put_performance': {
                'win_rate': len(put_legs[put_legs['pnl'] > 0]) / len(put_legs) if len(put_legs) > 0 else 0,
                'total_pnl': put_legs['pnl'].sum() if len(put_legs) > 0 else 0,
                'avg_pnl_pct': put_legs['pnl_pct'].mean() if len(put_legs) > 0 else 0
            }
        }


def main():
    """Run intraday backtest"""

    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', 5432),
        database=os.getenv('POSTGRES_DB', 'gexdb'),
        user=os.getenv('POSTGRES_USER', 'gexuser'),
        password=os.getenv('POSTGRES_PASSWORD')
    )

    backtester = IntradayStrangleBacktester(conn)

    # Run backtest
    results = backtester.backtest_intraday(
        start_date='2025-03-18',
        end_date='2025-11-28',
        profit_target_pct=25.0,
        stop_loss_pct=40.0,
        max_legs_per_type=2
    )

    # Save results
    output_path = 'output/strangle_intraday_results.csv'
    os.makedirs('output', exist_ok=True)
    results.to_csv(output_path, index=False)
    print(f"\n\nResults saved to: {output_path}")

    # Generate performance report
    performance = backtester.generate_performance_report(results)

    print(f"\n{'='*80}")
    print("INTRADAY PERFORMANCE SUMMARY")
    print(f"{'='*80}")
    for key, value in performance.items():
        if isinstance(value, dict):
            print(f"\n{key}:")
            for k, v in value.items():
                if isinstance(v, float):
                    if 'rate' in k or 'pct' in k:
                        print(f"  {k:25s}: {v:.2%}")
                    else:
                        print(f"  {k:25s}: ${v:,.2f}")
                else:
                    print(f"  {k:25s}: {v}")
        elif isinstance(value, float):
            if 'rate' in key or 'factor' in key:
                print(f"{key:30s}: {value:.2%}" if value < 10 else f"{key:30s}: {value:.2f}x")
            else:
                print(f"{key:30s}: ${value:,.2f}")
        else:
            print(f"{key:30s}: {value}")
    print(f"{'='*80}\n")

    # Save performance report
    perf_path = 'output/strangle_intraday_performance.json'
    with open(perf_path, 'w') as f:
        json.dump(performance, f, indent=2, default=str)
    print(f"Performance report saved to: {perf_path}\n")

    conn.close()


if __name__ == "__main__":
    main()
