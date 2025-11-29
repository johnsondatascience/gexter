#!/usr/bin/env python3
"""
Hedged Strangle Strategy - Always maintain both legs

Strategy:
- Enter calls when conditions are favorable (BUY signals, near resistance)
- Enter puts when conditions are favorable (SELL signals, near support) OR as hedge
- Maintain hedged position (strangle) but time entries independently
- Exit each leg independently when profit target or stop loss hit
- Next day: close all overnight positions and start fresh
"""

import psycopg2
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import os
from datetime import datetime
import json
from typing import Dict, List, Tuple, Optional
import sys
sys.path.append(os.path.dirname(__file__))
from backtest_strangle_intraday import (
    IntradayStrangleBacktester, OptionLeg, LegType, LegStatus
)

load_dotenv()


class HedgedStrangleBacktester(IntradayStrangleBacktester):
    """Backtest hedged strangle with independent leg timing"""

    def should_enter_call_hedged(self, df: pd.DataFrame, current_price: float,
                                 call_wall: Optional[float], gex_signal: str,
                                 has_active_call: bool) -> Tuple[bool, Optional[float]]:
        """
        Determine if we should buy a call (hedged approach)

        More flexible entry - enter calls on:
        1. BUY signals (bullish)
        2. High volatility (as part of strangle hedge)
        3. If we have puts but no calls (balance the hedge)
        """
        if call_wall is None:
            return False, None

        # Check if we already have a call at this strike
        for leg_id, leg in self.active_legs.items():
            if leg.leg_type == LegType.CALL and leg.strike == call_wall:
                return False, None

        # Enter calls on BUY signals
        if gex_signal == "BUY" and not has_active_call:
            return True, call_wall

        # Also enter calls if we have puts but no calls (balance hedge)
        has_active_put = any(leg.leg_type == LegType.PUT for leg in self.active_legs.values())
        if has_active_put and not has_active_call:
            return True, call_wall

        return False, None

    def should_enter_put_hedged(self, df: pd.DataFrame, current_price: float,
                                put_wall: Optional[float], gex_signal: str,
                                has_active_put: bool, has_active_call: bool) -> Tuple[bool, Optional[float]]:
        """
        Determine if we should buy a put (hedged approach)

        More flexible entry - enter puts on:
        1. SELL signals (bearish)
        2. As hedge when we have calls
        3. High volatility scenarios
        """
        if put_wall is None:
            return False, None

        # Check if we already have a put at this strike
        for leg_id, leg in self.active_legs.items():
            if leg.leg_type == LegType.PUT and leg.strike == put_wall:
                return False, None

        # Enter puts on SELL signals
        if gex_signal == "SELL" and not has_active_put:
            return True, put_wall

        # Enter puts as hedge if we have calls but no puts
        if has_active_call and not has_active_put:
            return True, put_wall

        return False, None

    def backtest_hedged(self, start_date: str, end_date: str,
                       profit_target_pct: float = 25.0,
                       stop_loss_pct: float = 40.0) -> pd.DataFrame:
        """
        Run hedged strangle backtest

        Args:
            start_date: Start date
            end_date: End date
            profit_target_pct: Profit target %
            stop_loss_pct: Stop loss %

        Returns:
            DataFrame with results
        """
        print(f"\n{'='*80}")
        print(f"HEDGED STRANGLE BACKTESTING")
        print(f"{'='*80}")
        print(f"Date range: {start_date} to {end_date}")
        print(f"Strategy: Maintain both legs, time entries independently")
        print(f"Profit target: {profit_target_pct}%")
        print(f"Stop loss: {stop_loss_pct}%")
        print(f"{'='*80}\n")

        # Get trading dates
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

            # Get snapshots
            snapshots = self.get_intraday_snapshots(trade_date)

            if len(snapshots) == 0:
                # Close overnight positions
                for leg_id, leg in list(self.active_legs.items()):
                    leg.exit_date = trade_date
                    leg.exit_time = "09:30:00"
                    leg.status = LegStatus.CLOSED
                    leg.exit_reason = "overnight_close_no_data"
                    all_legs.append(leg)
                    del self.active_legs[leg_id]
                continue

            print(f"[{trade_date}] Processing {len(snapshots)} snapshots")

            # Close overnight positions
            if len(self.active_legs) > 0 and len(snapshots) > 0:
                first_snapshot_time = snapshots.iloc[0]['snapshot_time']
                first_snapshot_df = self.get_snapshot_data(first_snapshot_time)

                if len(first_snapshot_df) > 0:
                    for leg_id, leg in list(self.active_legs.items()):
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

            # Process intraday snapshots
            for _, snapshot_row in snapshots.iterrows():
                snapshot_time = snapshot_row['snapshot_time']

                try:
                    df = self.get_snapshot_data(snapshot_time)
                    if len(df) == 0:
                        continue

                    # Filter for tradeable options
                    df['expiration_date'] = pd.to_datetime(df['expiration_date'])
                    snapshot_date = pd.to_datetime(snapshot_time).date()
                    df['days_to_expiry'] = (df['expiration_date'].dt.date - snapshot_date).apply(lambda x: x.days)
                    df_tradeable = df[df['days_to_expiry'] <= 1].copy()

                    if len(df_tradeable) == 0:
                        continue

                    current_price = df_tradeable['spx_price'].iloc[0]
                    zero_gex = self.calculate_zero_gex(df_tradeable)
                    call_wall, put_wall = self.find_gex_walls(df_tradeable, current_price)
                    gex_signal = self.get_gex_signal(df_tradeable, current_price)

                    # 1. Check exits (PDT-protected)
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

                    # 2. Check for new entries (hedged approach)
                    has_active_call = any(leg.leg_type == LegType.CALL for leg in self.active_legs.values())
                    has_active_put = any(leg.leg_type == LegType.PUT for leg in self.active_legs.values())

                    # Try to enter call
                    should_enter, call_strike = self.should_enter_call_hedged(
                        df_tradeable, current_price, call_wall, gex_signal, has_active_call
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
                            hedge_note = " (HEDGE)" if has_active_put else ""
                            print(f"  [{pd.to_datetime(snapshot_time).strftime('%H:%M')}] ENTER CALL ${call_strike}: ${call_price:.2f}{hedge_note} (SPX=${current_price:.2f}, Signal={gex_signal})")

                    # Try to enter put
                    should_enter, put_strike = self.should_enter_put_hedged(
                        df_tradeable, current_price, put_wall, gex_signal, has_active_put, has_active_call
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
                            hedge_note = " (HEDGE)" if has_active_call else ""
                            print(f"  [{pd.to_datetime(snapshot_time).strftime('%H:%M')}] ENTER PUT ${put_strike}: ${put_price:.2f}{hedge_note} (SPX=${current_price:.2f}, Signal={gex_signal})")

                except Exception as e:
                    print(f"  [{snapshot_time}] Error: {e}")
                    continue

        # Close remaining positions
        for leg_id, leg in self.active_legs.items():
            leg.status = LegStatus.CLOSED
            leg.exit_reason = "end_of_backtest"
            all_legs.append(leg)

        # Convert to DataFrame
        results_df = pd.DataFrame([{
            'leg_id': leg.leg_id,
            'leg_type': leg.leg_type.value if hasattr(leg.leg_type, 'value') else leg.leg_type,
            'entry_date': leg.entry_date,
            'entry_time': leg.entry_time,
            'exit_date': leg.exit_date,
            'exit_time': leg.exit_time,
            'entry_spx_price': leg.entry_spx_price,
            'strike': leg.strike,
            'entry_price': leg.entry_price,
            'exit_price': leg.exit_price,
            'pnl': leg.pnl,
            'pnl_pct': leg.pnl_pct,
            'exit_reason': leg.exit_reason,
            'gex_signal_at_entry': leg.gex_signal_at_entry
        } for leg in all_legs])

        return results_df


def main():
    """Run hedged strangle backtest"""

    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', 5432),
        database=os.getenv('POSTGRES_DB', 'gexdb'),
        user=os.getenv('POSTGRES_USER', 'gexuser'),
        password=os.getenv('POSTGRES_PASSWORD')
    )

    backtester = HedgedStrangleBacktester(conn)

    results = backtester.backtest_hedged(
        start_date='2025-03-18',
        end_date='2025-11-28',
        profit_target_pct=25.0,
        stop_loss_pct=40.0
    )

    # Save results
    output_path = 'output/strangle_hedged_results.csv'
    os.makedirs('output', exist_ok=True)
    results.to_csv(output_path, index=False)
    print(f"\n\nResults saved to: {output_path}")

    # Generate performance
    performance = backtester.generate_performance_report(results)

    print(f"\n{'='*80}")
    print("HEDGED STRANGLE PERFORMANCE")
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

    # Save performance
    with open('output/strangle_hedged_performance.json', 'w') as f:
        json.dump(performance, f, indent=2, default=str)

    conn.close()


if __name__ == "__main__":
    main()
