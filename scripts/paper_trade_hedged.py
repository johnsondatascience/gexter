#!/usr/bin/env python3
"""
Paper Trading Engine - Hedged Strangle Strategy

Real-time paper trading that monitors the market and executes the hedged strangle
strategy using live GEX data. Tracks positions, logs decisions, and calculates P&L.

Usage:
    python scripts/paper_trade_hedged.py

The script will:
- Run during market hours (9:30 AM - 4:00 PM ET)
- Monitor GEX signals every 5 minutes
- Enter calls on BUY signals
- Enter puts as hedges when holding calls
- Exit positions based on profit targets and stop losses
- Avoid PDT violations (no same-day round trips)
- Log all decisions and track P&L
"""

import psycopg2
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import os
from datetime import datetime, time
import pytz
import json
import time as time_module
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging

load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/paper_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class LegType(Enum):
    """Option leg type"""
    CALL = "call"
    PUT = "put"


class LegStatus(Enum):
    """Position status"""
    ACTIVE = "active"
    CLOSED = "closed"


@dataclass
class PaperTradeLeg:
    """Represents a paper trade option leg"""
    leg_id: str
    leg_type: LegType
    entry_date: str
    entry_time: str
    entry_spx_price: float
    strike: float
    entry_price: float

    # GEX context at entry
    zero_gex_at_entry: Optional[float]
    gex_signal_at_entry: str

    # Exit details
    exit_date: Optional[str] = None
    exit_time: Optional[str] = None
    exit_spx_price: Optional[float] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None

    # P&L
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None

    # Status
    status: LegStatus = LegStatus.ACTIVE


class PaperTradingEngine:
    """Paper trading engine for hedged strangle strategy"""

    def __init__(self, db_connection):
        """
        Initialize paper trading engine

        Args:
            db_connection: PostgreSQL database connection
        """
        self.db = db_connection
        self.active_legs: Dict[str, PaperTradeLeg] = {}
        self.closed_legs: List[PaperTradeLeg] = []
        self.leg_counter = 0

        # Trading parameters (from backtest)
        self.profit_target_pct = 25.0
        self.stop_loss_pct = 40.0

        # Market hours (ET)
        self.market_open = time(9, 30)
        self.market_close = time(16, 0)
        self.timezone = pytz.timezone('America/New_York')

        # Load existing positions if any
        self.load_positions()

        logger.info("Paper Trading Engine initialized")
        logger.info(f"Profit target: {self.profit_target_pct}%")
        logger.info(f"Stop loss: {self.stop_loss_pct}%")

    def load_positions(self):
        """Load existing positions from file"""
        positions_file = 'output/paper_trading_positions.json'

        if os.path.exists(positions_file):
            try:
                with open(positions_file, 'r') as f:
                    data = json.load(f)

                # Reconstruct active positions
                for leg_data in data.get('active_legs', []):
                    leg = PaperTradeLeg(
                        leg_id=leg_data['leg_id'],
                        leg_type=LegType(leg_data['leg_type']),
                        entry_date=leg_data['entry_date'],
                        entry_time=leg_data['entry_time'],
                        entry_spx_price=leg_data['entry_spx_price'],
                        strike=leg_data['strike'],
                        entry_price=leg_data['entry_price'],
                        zero_gex_at_entry=leg_data.get('zero_gex_at_entry'),
                        gex_signal_at_entry=leg_data['gex_signal_at_entry'],
                        status=LegStatus.ACTIVE
                    )
                    self.active_legs[leg.leg_id] = leg

                # Load closed positions
                for leg_data in data.get('closed_legs', []):
                    leg = PaperTradeLeg(
                        leg_id=leg_data['leg_id'],
                        leg_type=LegType(leg_data['leg_type']),
                        entry_date=leg_data['entry_date'],
                        entry_time=leg_data['entry_time'],
                        entry_spx_price=leg_data['entry_spx_price'],
                        strike=leg_data['strike'],
                        entry_price=leg_data['entry_price'],
                        zero_gex_at_entry=leg_data.get('zero_gex_at_entry'),
                        gex_signal_at_entry=leg_data['gex_signal_at_entry'],
                        exit_date=leg_data.get('exit_date'),
                        exit_time=leg_data.get('exit_time'),
                        exit_spx_price=leg_data.get('exit_spx_price'),
                        exit_price=leg_data.get('exit_price'),
                        exit_reason=leg_data.get('exit_reason'),
                        pnl=leg_data.get('pnl'),
                        pnl_pct=leg_data.get('pnl_pct'),
                        status=LegStatus.CLOSED
                    )
                    self.closed_legs.append(leg)

                self.leg_counter = data.get('leg_counter', 0)
                logger.info(f"Loaded {len(self.active_legs)} active positions and {len(self.closed_legs)} closed positions")

            except Exception as e:
                logger.error(f"Error loading positions: {e}")

    def save_positions(self):
        """Save current positions to file"""
        positions_file = 'output/paper_trading_positions.json'
        os.makedirs('output', exist_ok=True)

        data = {
            'active_legs': [asdict(leg) for leg in self.active_legs.values()],
            'closed_legs': [asdict(leg) for leg in self.closed_legs],
            'leg_counter': self.leg_counter,
            'last_updated': datetime.now(self.timezone).isoformat()
        }

        # Convert enums to strings
        for leg_list in [data['active_legs'], data['closed_legs']]:
            for leg in leg_list:
                if isinstance(leg.get('leg_type'), LegType):
                    leg['leg_type'] = leg['leg_type'].value
                if isinstance(leg.get('status'), LegStatus):
                    leg['status'] = leg['status'].value

        with open(positions_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        logger.debug("Positions saved")

    def get_latest_snapshot(self) -> pd.DataFrame:
        """Get the most recent options snapshot from database"""
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
        WHERE "greeks.updated_at" = (SELECT MAX("greeks.updated_at") FROM gex_table)
        ORDER BY expiration_date, strike, option_type
        """

        return pd.read_sql(query, self.db)

    def calculate_zero_gex(self, df: pd.DataFrame) -> Optional[float]:
        """Calculate Zero GEX level"""
        net_gex = df.groupby('strike')['gex'].sum().reset_index()
        net_gex = net_gex.sort_values('strike')

        # Find sign changes
        net_gex['sign_change'] = np.sign(net_gex['gex']).diff()
        crosses = net_gex[net_gex['sign_change'] != 0]

        if len(crosses) == 0:
            return None

        return float(crosses['strike'].iloc[0])

    def find_gex_walls(self, df: pd.DataFrame, current_price: float) -> Tuple[Optional[float], Optional[float]]:
        """Find call and put walls (max GEX levels)"""
        net_gex = df.groupby('strike')['gex'].sum().reset_index()

        above_price = net_gex[net_gex['strike'] > current_price]
        below_price = net_gex[net_gex['strike'] < current_price]

        call_wall = above_price.nlargest(1, 'gex')['strike'].iloc[0] if len(above_price) > 0 else None
        put_wall = below_price.nsmallest(1, 'gex')['strike'].iloc[0] if len(below_price) > 0 else None

        return call_wall, put_wall

    def get_gex_signal(self, df: pd.DataFrame, current_price: float) -> str:
        """Get GEX-based signal"""
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

        # Fallback to mid price
        bid = option['bid'].iloc[0]
        ask = option['ask'].iloc[0]

        if pd.notna(bid) and pd.notna(ask) and bid > 0 and ask > 0:
            return (bid + ask) / 2

        return None

    def should_enter_call(self, df: pd.DataFrame, current_price: float,
                         call_wall: Optional[float], gex_signal: str,
                         has_active_call: bool) -> Tuple[bool, Optional[float]]:
        """Determine if we should buy a call"""
        if call_wall is None:
            return False, None

        # Check if we already have a call at this strike
        for leg in self.active_legs.values():
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

    def should_enter_put(self, df: pd.DataFrame, current_price: float,
                        put_wall: Optional[float], gex_signal: str,
                        has_active_put: bool, has_active_call: bool) -> Tuple[bool, Optional[float]]:
        """Determine if we should buy a put"""
        if put_wall is None:
            return False, None

        # Check if we already have a put at this strike
        for leg in self.active_legs.values():
            if leg.leg_type == LegType.PUT and leg.strike == put_wall:
                return False, None

        # Enter puts on SELL signals
        if gex_signal == "SELL" and not has_active_put:
            return True, put_wall

        # Enter puts as hedge if we have calls but no puts
        if has_active_call and not has_active_put:
            return True, put_wall

        return False, None

    def should_exit_leg(self, leg: PaperTradeLeg, current_price: float,
                       df: pd.DataFrame, current_date: str) -> Tuple[bool, Optional[str]]:
        """
        Determine if we should exit a leg

        PDT Protection: Don't exit if entered today (would create day trade)
        """
        # PDT PROTECTION
        if leg.entry_date == current_date:
            return False, None

        option_price = self.get_option_price(df, leg.strike, leg.leg_type.value)

        if option_price is None:
            return False, None

        # Calculate P&L
        pnl_pct = ((option_price - leg.entry_price) / leg.entry_price) * 100

        # Check profit target
        if pnl_pct >= self.profit_target_pct:
            return True, f"profit_target_{pnl_pct:.1f}pct"

        # Check stop loss
        if pnl_pct <= -self.stop_loss_pct:
            return True, f"stop_loss_{pnl_pct:.1f}pct"

        return False, None

    def process_market_snapshot(self):
        """Process current market snapshot and make trading decisions"""
        try:
            # Get latest data
            df = self.get_latest_snapshot()

            if len(df) == 0:
                logger.warning("No market data available")
                return

            # Filter for 0DTE or 1DTE options
            df['expiration_date'] = pd.to_datetime(df['expiration_date'])
            snapshot_date = pd.to_datetime(df['greeks.updated_at'].iloc[0]).date()
            df['days_to_expiry'] = (df['expiration_date'].dt.date - snapshot_date).apply(lambda x: x.days)
            df_tradeable = df[df['days_to_expiry'] <= 1].copy()

            if len(df_tradeable) == 0:
                logger.warning("No tradeable options (0-1 DTE)")
                return

            # Get current market state
            current_price = df_tradeable['spx_price'].iloc[0]
            snapshot_time = df['greeks.updated_at'].iloc[0]
            current_date = snapshot_time.strftime('%Y-%m-%d')
            current_time_str = snapshot_time.strftime('%H:%M:%S')

            zero_gex = self.calculate_zero_gex(df_tradeable)
            call_wall, put_wall = self.find_gex_walls(df_tradeable, current_price)
            gex_signal = self.get_gex_signal(df_tradeable, current_price)

            logger.info(f"Market snapshot: SPX=${current_price:.2f}, Zero GEX=${zero_gex:.2f if zero_gex else 0:.2f}, Signal={gex_signal}")

            # 1. Check exits for active positions
            for leg_id, leg in list(self.active_legs.items()):
                should_exit, reason = self.should_exit_leg(leg, current_price, df_tradeable, current_date)

                if should_exit:
                    exit_price = self.get_option_price(df_tradeable, leg.strike, leg.leg_type.value)

                    if exit_price:
                        leg.exit_date = current_date
                        leg.exit_time = current_time_str
                        leg.exit_spx_price = current_price
                        leg.exit_price = exit_price
                        leg.exit_reason = reason
                        leg.pnl = exit_price - leg.entry_price
                        leg.pnl_pct = (leg.pnl / leg.entry_price) * 100
                        leg.status = LegStatus.CLOSED

                        logger.info(f"EXIT {leg.leg_type.value.upper()} ${leg.strike}: ${leg.entry_price:.2f} -> ${exit_price:.2f} = {leg.pnl_pct:+.1f}% ({reason})")

                        self.closed_legs.append(leg)
                        del self.active_legs[leg_id]

            # 2. Check for new entries
            has_active_call = any(leg.leg_type == LegType.CALL for leg in self.active_legs.values())
            has_active_put = any(leg.leg_type == LegType.PUT for leg in self.active_legs.values())

            # Try to enter call
            should_enter, call_strike = self.should_enter_call(
                df_tradeable, current_price, call_wall, gex_signal, has_active_call
            )

            if should_enter and call_strike:
                call_price = self.get_option_price(df_tradeable, call_strike, 'call')

                if call_price and call_price > 0:
                    self.leg_counter += 1
                    leg = PaperTradeLeg(
                        leg_id=f"{current_date}_call_{self.leg_counter}",
                        leg_type=LegType.CALL,
                        entry_date=current_date,
                        entry_time=current_time_str,
                        entry_spx_price=current_price,
                        strike=call_strike,
                        entry_price=call_price,
                        zero_gex_at_entry=zero_gex,
                        gex_signal_at_entry=gex_signal
                    )

                    self.active_legs[leg.leg_id] = leg
                    hedge_note = " (HEDGE)" if has_active_put else ""
                    logger.info(f"ENTER CALL ${call_strike}: ${call_price:.2f}{hedge_note} (SPX=${current_price:.2f}, Signal={gex_signal})")

            # Try to enter put
            should_enter, put_strike = self.should_enter_put(
                df_tradeable, current_price, put_wall, gex_signal, has_active_put, has_active_call
            )

            if should_enter and put_strike:
                put_price = self.get_option_price(df_tradeable, put_strike, 'put')

                if put_price and put_price > 0:
                    self.leg_counter += 1
                    leg = PaperTradeLeg(
                        leg_id=f"{current_date}_put_{self.leg_counter}",
                        leg_type=LegType.PUT,
                        entry_date=current_date,
                        entry_time=current_time_str,
                        entry_spx_price=current_price,
                        strike=put_strike,
                        entry_price=put_price,
                        zero_gex_at_entry=zero_gex,
                        gex_signal_at_entry=gex_signal
                    )

                    self.active_legs[leg.leg_id] = leg
                    hedge_note = " (HEDGE)" if has_active_call else ""
                    logger.info(f"ENTER PUT ${put_strike}: ${put_price:.2f}{hedge_note} (SPX=${current_price:.2f}, Signal={gex_signal})")

            # Save positions
            self.save_positions()

            # Log current positions
            if len(self.active_legs) > 0:
                logger.info(f"Active positions: {len(self.active_legs)}")
                for leg_id, leg in self.active_legs.items():
                    current_option_price = self.get_option_price(df_tradeable, leg.strike, leg.leg_type.value)
                    if current_option_price:
                        unrealized_pnl = current_option_price - leg.entry_price
                        unrealized_pnl_pct = (unrealized_pnl / leg.entry_price) * 100
                        logger.info(f"  {leg.leg_type.value.upper()} ${leg.strike}: ${leg.entry_price:.2f} -> ${current_option_price:.2f} = {unrealized_pnl_pct:+.1f}%")

        except Exception as e:
            logger.error(f"Error processing market snapshot: {e}", exc_info=True)

    def close_overnight_positions(self):
        """Close any overnight positions at market open"""
        try:
            df = self.get_latest_snapshot()

            if len(df) == 0:
                logger.warning("No market data for closing overnight positions")
                return

            current_date = datetime.now(self.timezone).strftime('%Y-%m-%d')
            current_price = df['spx_price'].iloc[0]
            snapshot_time = df['greeks.updated_at'].iloc[0]
            current_time_str = snapshot_time.strftime('%H:%M:%S')

            for leg_id, leg in list(self.active_legs.items()):
                if leg.entry_date != current_date:
                    # This is an overnight position
                    exit_price = self.get_option_price(df, leg.strike, leg.leg_type.value)

                    if exit_price:
                        leg.exit_date = current_date
                        leg.exit_time = current_time_str
                        leg.exit_spx_price = current_price
                        leg.exit_price = exit_price
                        leg.exit_reason = "overnight_close"
                        leg.pnl = exit_price - leg.entry_price
                        leg.pnl_pct = (leg.pnl / leg.entry_price) * 100
                        leg.status = LegStatus.CLOSED

                        logger.info(f"CLOSE OVERNIGHT {leg.leg_type.value.upper()} ${leg.strike}: ${leg.entry_price:.2f} -> ${exit_price:.2f} = {leg.pnl_pct:+.1f}%")

                        self.closed_legs.append(leg)
                        del self.active_legs[leg_id]

            self.save_positions()

        except Exception as e:
            logger.error(f"Error closing overnight positions: {e}", exc_info=True)

    def is_market_hours(self) -> bool:
        """Check if current time is during market hours"""
        now = datetime.now(self.timezone)
        current_time = now.time()

        # Check if weekend
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False

        return self.market_open <= current_time <= self.market_close

    def run(self, check_interval: int = 300):
        """
        Run the paper trading engine

        Args:
            check_interval: Seconds between market checks (default: 300 = 5 minutes)
        """
        logger.info("=" * 80)
        logger.info("PAPER TRADING ENGINE STARTED")
        logger.info("Strategy: Hedged Strangle (Independent Leg Timing)")
        logger.info(f"Check interval: {check_interval} seconds")
        logger.info("=" * 80)

        overnight_closed_today = False

        try:
            while True:
                now = datetime.now(self.timezone)
                current_date = now.strftime('%Y-%m-%d')

                if self.is_market_hours():
                    # Check if we need to close overnight positions (do this once at market open)
                    if not overnight_closed_today and now.time() < time(10, 0):
                        logger.info("Market open - checking for overnight positions to close")
                        self.close_overnight_positions()
                        overnight_closed_today = True

                    # Process market snapshot
                    self.process_market_snapshot()

                else:
                    if overnight_closed_today:
                        # Reset for next day
                        overnight_closed_today = False

                    next_open = now.replace(hour=self.market_open.hour, minute=self.market_open.minute, second=0)
                    if now.time() > self.market_close:
                        # After close, wait until tomorrow
                        next_open = next_open.replace(day=now.day + 1)

                    logger.info(f"Market closed. Next check at {next_open.strftime('%Y-%m-%d %H:%M')}")

                # Wait before next check
                time_module.sleep(check_interval)

        except KeyboardInterrupt:
            logger.info("\nPaper trading stopped by user")
            self.print_summary()
        except Exception as e:
            logger.error(f"Fatal error in trading loop: {e}", exc_info=True)

    def print_summary(self):
        """Print trading summary"""
        logger.info("\n" + "=" * 80)
        logger.info("PAPER TRADING SUMMARY")
        logger.info("=" * 80)

        total_trades = len(self.closed_legs)
        if total_trades == 0:
            logger.info("No completed trades yet")
            return

        df = pd.DataFrame([asdict(leg) for leg in self.closed_legs])
        df['leg_type'] = df['leg_type'].apply(lambda x: x if isinstance(x, str) else x.value)

        wins = df[df['pnl'] > 0]
        losses = df[df['pnl'] < 0]

        total_pnl = df['pnl'].sum()
        win_rate = len(wins) / len(df) if len(df) > 0 else 0
        avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
        avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0

        logger.info(f"Total Trades: {total_trades}")
        logger.info(f"Winning Trades: {len(wins)}")
        logger.info(f"Losing Trades: {len(losses)}")
        logger.info(f"Win Rate: {win_rate:.1%}")
        logger.info(f"Total P&L: ${total_pnl:,.2f}")
        logger.info(f"Average Win: ${avg_win:,.2f}")
        logger.info(f"Average Loss: ${avg_loss:,.2f}")

        # By leg type
        call_trades = df[df['leg_type'] == 'call']
        put_trades = df[df['leg_type'] == 'put']

        if len(call_trades) > 0:
            logger.info(f"\nCall Trades: {len(call_trades)}, P&L: ${call_trades['pnl'].sum():,.2f}")
        if len(put_trades) > 0:
            logger.info(f"Put Trades: {len(put_trades)}, P&L: ${put_trades['pnl'].sum():,.2f}")

        logger.info(f"\nActive Positions: {len(self.active_legs)}")
        for leg_id, leg in self.active_legs.items():
            logger.info(f"  {leg.leg_type.value.upper()} ${leg.strike} @ ${leg.entry_price:.2f}")

        logger.info("=" * 80)


def main():
    """Run paper trading engine"""

    # Connect to database
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', 5432),
        database=os.getenv('POSTGRES_DB', 'gexdb'),
        user=os.getenv('POSTGRES_USER', 'gexuser'),
        password=os.getenv('POSTGRES_PASSWORD')
    )

    # Create trading engine
    engine = PaperTradingEngine(conn)

    # Run (checks market every 5 minutes)
    engine.run(check_interval=300)


if __name__ == "__main__":
    main()
