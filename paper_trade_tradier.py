#!/usr/bin/env python3
"""
Tradier-Integrated Paper Trading Engine for Hedged Strangle Strategy

Uses real Tradier sandbox API for order execution while trading the hedged strangle strategy.

Features:
- Real-time GEX signal processing
- Actual order placement through Tradier API
- Position tracking and monitoring
- PDT protection (no same-day exits)
- Overnight position management
- Comprehensive logging
"""

import psycopg2
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import os
from datetime import datetime, time as dt_time
import json
import requests
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum

load_dotenv()

# Tradier API Configuration
TRADIER_API_KEY = os.getenv('TRADIER_SANDBOX_API_KEY') or os.getenv('TRADIER_API_KEY')
TRADIER_ACCOUNT = os.getenv('TRADIER_SANDBOX_ACCOUNT', 'VA86061098')
BASE_URL = 'https://sandbox.tradier.com/v1'

# Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'gex_data'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}


class LegType(Enum):
    """Option leg type"""
    CALL = "call"
    PUT = "put"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    REJECTED = "rejected"
    CANCELED = "canceled"


@dataclass
class TradierLeg:
    """Represents a single option leg traded through Tradier"""
    leg_id: str
    leg_type: LegType
    entry_date: str
    entry_time: str
    entry_spx_price: float
    strike: float
    expiration: str

    # Order information
    entry_order_id: Optional[str] = None
    entry_order_status: OrderStatus = OrderStatus.PENDING
    entry_price: Optional[float] = None
    option_symbol: Optional[str] = None

    # Exit information
    exit_date: Optional[str] = None
    exit_time: Optional[str] = None
    exit_spx_price: Optional[float] = None
    exit_order_id: Optional[str] = None
    exit_order_status: Optional[OrderStatus] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None

    # P&L
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None

    # Context
    zero_gex_at_entry: Optional[float] = None
    gex_signal_at_entry: Optional[str] = None


class TradierAPI:
    """Wrapper for Tradier API calls"""

    def __init__(self):
        self.api_key = TRADIER_API_KEY
        self.account = TRADIER_ACCOUNT
        self.base_url = BASE_URL
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json'
        }

    def get_option_chain(self, symbol: str = 'SPX', expiration: str = None) -> Optional[Dict]:
        """Get option chain for a symbol"""
        url = f'{self.base_url}/markets/options/chains'
        params = {
            'symbol': symbol,
            'expiration': expiration,
            'greeks': 'true'
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"ERROR: Failed to get option chain - {response.status_code}")
                return None
        except Exception as e:
            print(f"ERROR: Exception getting option chain - {e}")
            return None

    def get_option_quote(self, symbol: str) -> Optional[Dict]:
        """Get quote for a specific option symbol"""
        url = f'{self.base_url}/markets/quotes'
        params = {'symbols': symbol, 'greeks': 'true'}

        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                quotes = data.get('quotes', {}).get('quote', [])
                if isinstance(quotes, dict):
                    return quotes
                elif isinstance(quotes, list) and len(quotes) > 0:
                    return quotes[0]
                return None
            else:
                print(f"ERROR: Failed to get quote - {response.status_code}")
                return None
        except Exception as e:
            print(f"ERROR: Exception getting quote - {e}")
            return None

    def place_option_order(self, option_symbol: str, quantity: int,
                          side: str, order_type: str = 'market',
                          price: float = None) -> Optional[Dict]:
        """
        Place an option order

        Args:
            option_symbol: OCC option symbol (e.g., 'SPX251231C06000000')
            quantity: Number of contracts
            side: 'buy_to_open' or 'sell_to_close'
            order_type: 'market' or 'limit'
            price: Limit price if order_type is 'limit'

        Returns:
            Order response dict or None
        """
        url = f'{self.base_url}/accounts/{self.account}/orders'

        data = {
            'class': 'option',
            'symbol': option_symbol,
            'option_symbol': option_symbol,
            'side': side,
            'quantity': quantity,
            'type': order_type,
            'duration': 'day'
        }

        if order_type == 'limit' and price:
            data['price'] = f"{price:.2f}"

        try:
            response = requests.post(url, headers=self.headers, data=data)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"ERROR: Failed to place order - {response.status_code}")
                print(f"Response: {response.text}")
                return None
        except Exception as e:
            print(f"ERROR: Exception placing order - {e}")
            return None

    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get status of an order"""
        url = f'{self.base_url}/accounts/{self.account}/orders/{order_id}'

        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"ERROR: Failed to get order status - {response.status_code}")
                return None
        except Exception as e:
            print(f"ERROR: Exception getting order status - {e}")
            return None

    def get_positions(self) -> Optional[Dict]:
        """Get current positions"""
        url = f'{self.base_url}/accounts/{self.account}/positions'

        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"ERROR: Failed to get positions - {response.status_code}")
                return None
        except Exception as e:
            print(f"ERROR: Exception getting positions - {e}")
            return None

    def get_account_balance(self) -> Optional[Dict]:
        """Get account balance"""
        url = f'{self.base_url}/accounts/{self.account}/balances'

        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"ERROR: Failed to get balance - {response.status_code}")
                return None
        except Exception as e:
            print(f"ERROR: Exception getting balance - {e}")
            return None


class TradierPaperTrading:
    """Paper trading engine using Tradier sandbox API"""

    def __init__(self, db_connection):
        self.db = db_connection
        self.api = TradierAPI()
        self.active_legs: Dict[str, TradierLeg] = {}
        self.closed_legs: List[TradierLeg] = []

        # Strategy parameters
        self.profit_target_pct = 25.0
        self.stop_loss_pct = 40.0
        self.contracts_per_leg = 1

        # State
        self.current_date = None
        self.position_file = 'tradier_positions.json'
        self.log_file = 'logs/tradier_trading.log'

        # Create logs directory
        os.makedirs('logs', exist_ok=True)
        os.makedirs('output', exist_ok=True)

        # Load existing positions
        self.load_positions()

    def log(self, message: str, level: str = "INFO"):
        """Log message to file and console"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] [{level}] {message}"
        print(log_line)

        with open(self.log_file, 'a') as f:
            f.write(log_line + '\n')

    def load_positions(self):
        """Load positions from file"""
        if os.path.exists(self.position_file):
            try:
                with open(self.position_file, 'r') as f:
                    data = json.load(f)

                # Reconstruct active legs
                for leg_data in data.get('active_legs', []):
                    leg = TradierLeg(**leg_data)
                    # Convert string enums back to enums
                    leg.leg_type = LegType(leg.leg_type) if isinstance(leg.leg_type, str) else leg.leg_type
                    leg.entry_order_status = OrderStatus(leg.entry_order_status) if isinstance(leg.entry_order_status, str) else leg.entry_order_status
                    if leg.exit_order_status:
                        leg.exit_order_status = OrderStatus(leg.exit_order_status) if isinstance(leg.exit_order_status, str) else leg.exit_order_status

                    self.active_legs[leg.leg_id] = leg

                # Reconstruct closed legs
                for leg_data in data.get('closed_legs', []):
                    leg = TradierLeg(**leg_data)
                    leg.leg_type = LegType(leg.leg_type) if isinstance(leg.leg_type, str) else leg.leg_type
                    leg.entry_order_status = OrderStatus(leg.entry_order_status) if isinstance(leg.entry_order_status, str) else leg.entry_order_status
                    if leg.exit_order_status:
                        leg.exit_order_status = OrderStatus(leg.exit_order_status) if isinstance(leg.exit_order_status, str) else leg.exit_order_status

                    self.closed_legs.append(leg)

                self.log(f"Loaded {len(self.active_legs)} active legs, {len(self.closed_legs)} closed legs")

            except Exception as e:
                self.log(f"Error loading positions: {e}", "ERROR")

    def save_positions(self):
        """Save positions to file"""
        try:
            # Convert to serializable format
            active_legs_data = []
            for leg in self.active_legs.values():
                leg_dict = asdict(leg)
                leg_dict['leg_type'] = leg.leg_type.value
                leg_dict['entry_order_status'] = leg.entry_order_status.value
                if leg.exit_order_status:
                    leg_dict['exit_order_status'] = leg.exit_order_status.value
                active_legs_data.append(leg_dict)

            closed_legs_data = []
            for leg in self.closed_legs:
                leg_dict = asdict(leg)
                leg_dict['leg_type'] = leg.leg_type.value
                leg_dict['entry_order_status'] = leg.entry_order_status.value
                if leg.exit_order_status:
                    leg_dict['exit_order_status'] = leg.exit_order_status.value
                closed_legs_data.append(leg_dict)

            data = {
                'active_legs': active_legs_data,
                'closed_legs': closed_legs_data,
                'last_updated': datetime.now().isoformat()
            }

            with open(self.position_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            self.log(f"Error saving positions: {e}", "ERROR")

    def get_latest_snapshot(self) -> pd.DataFrame:
        """Get the most recent GEX snapshot"""
        query = """
        SELECT DISTINCT ON (strike, option_type)
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
            spx_price
        FROM gex_table
        WHERE "greeks.updated_at" = (
            SELECT MAX("greeks.updated_at") FROM gex_table
        )
        ORDER BY strike, option_type, "greeks.updated_at" DESC
        """

        return pd.read_sql(query, self.db)

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

        # Call wall - highest positive GEX above price
        calls = net_gex[(net_gex['strike'] > current_price) & (net_gex['gex'] > 0)]
        call_wall = float(calls.loc[calls['gex'].idxmax(), 'strike']) if len(calls) > 0 else None

        # Put wall - most negative GEX below price
        puts = net_gex[(net_gex['strike'] < current_price) & (net_gex['gex'] < 0)]
        put_wall = float(puts.loc[puts['gex'].idxmin(), 'strike']) if len(puts) > 0 else None

        return call_wall, put_wall

    def get_gex_signal(self, df: pd.DataFrame, current_price: float) -> str:
        """Determine GEX signal"""
        zero_gex = self.calculate_zero_gex(df)

        if zero_gex is None:
            return "NEUTRAL"

        if current_price > zero_gex:
            return "BUY"
        else:
            return "SELL"

    def build_option_symbol(self, strike: float, expiration: str, option_type: str) -> str:
        """
        Build OCC option symbol

        Format: SPX + YYMMDD + C/P + Strike (8 digits)
        Example: SPX251231C06000000 = SPX 12/31/2025 $6000 Call
        """
        # Parse expiration date
        exp_date = datetime.strptime(expiration, '%Y-%m-%d')
        date_part = exp_date.strftime('%y%m%d')

        # Option type
        opt_type = 'C' if option_type.upper() == 'CALL' else 'P'

        # Strike - multiply by 1000 and pad to 8 digits
        strike_int = int(strike * 1000)
        strike_part = f"{strike_int:08d}"

        return f"SPX{date_part}{opt_type}{strike_part}"

    def enter_leg(self, leg_type: LegType, strike: float, expiration: str,
                  current_price: float, zero_gex: Optional[float],
                  gex_signal: str) -> Optional[str]:
        """
        Enter a new option leg via Tradier API

        Returns:
            leg_id if successful, None otherwise
        """
        # Build option symbol
        option_symbol = self.build_option_symbol(
            strike, expiration, leg_type.value
        )

        # Get current quote
        quote = self.api.get_option_quote(option_symbol)
        if not quote:
            self.log(f"Failed to get quote for {option_symbol}", "ERROR")
            return None

        # Place order (using limit order at mid price for better fills)
        bid = quote.get('bid', 0)
        ask = quote.get('ask', 0)

        if bid <= 0 or ask <= 0:
            self.log(f"Invalid bid/ask for {option_symbol}: {bid}/{ask}", "ERROR")
            return None

        mid_price = (bid + ask) / 2

        order_result = self.api.place_option_order(
            option_symbol=option_symbol,
            quantity=self.contracts_per_leg,
            side='buy_to_open',
            order_type='limit',
            price=mid_price
        )

        if not order_result:
            self.log(f"Failed to place order for {option_symbol}", "ERROR")
            return None

        order_data = order_result.get('order', {})
        order_id = order_data.get('id')

        # Create leg object
        leg_id = f"{leg_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        now = datetime.now()

        leg = TradierLeg(
            leg_id=leg_id,
            leg_type=leg_type,
            entry_date=now.strftime('%Y-%m-%d'),
            entry_time=now.strftime('%H:%M:%S'),
            entry_spx_price=current_price,
            strike=strike,
            expiration=expiration,
            entry_order_id=order_id,
            entry_order_status=OrderStatus.PENDING,
            option_symbol=option_symbol,
            zero_gex_at_entry=zero_gex,
            gex_signal_at_entry=gex_signal
        )

        self.active_legs[leg_id] = leg
        self.save_positions()

        self.log(f"Placed ENTRY order for {leg_type.value.upper()} @ {strike} (Order ID: {order_id})")

        return leg_id

    def check_order_fills(self):
        """Check status of pending orders"""
        for leg_id, leg in list(self.active_legs.items()):
            # Check entry order
            if leg.entry_order_status == OrderStatus.PENDING and leg.entry_order_id:
                order_status = self.api.get_order_status(leg.entry_order_id)
                if order_status:
                    order = order_status.get('order', {})
                    status = order.get('status', '').lower()
                    avg_fill_price = order.get('avg_fill_price')

                    if status == 'filled' and avg_fill_price:
                        leg.entry_order_status = OrderStatus.FILLED
                        leg.entry_price = float(avg_fill_price)
                        self.log(f"ENTRY filled for {leg.leg_type.value.upper()} @ {leg.strike}: ${avg_fill_price}")
                        self.save_positions()

                    elif status in ['rejected', 'canceled']:
                        leg.entry_order_status = OrderStatus.REJECTED
                        self.log(f"ENTRY {status} for {leg.leg_type.value.upper()} @ {leg.strike}", "WARNING")
                        self.save_positions()

            # Check exit order
            if leg.exit_order_id and leg.exit_order_status == OrderStatus.PENDING:
                order_status = self.api.get_order_status(leg.exit_order_id)
                if order_status:
                    order = order_status.get('order', {})
                    status = order.get('status', '').lower()
                    avg_fill_price = order.get('avg_fill_price')

                    if status == 'filled' and avg_fill_price:
                        leg.exit_order_status = OrderStatus.FILLED
                        leg.exit_price = float(avg_fill_price)

                        # Calculate P&L
                        leg.pnl = (leg.exit_price - leg.entry_price) * 100 * self.contracts_per_leg
                        leg.pnl_pct = ((leg.exit_price - leg.entry_price) / leg.entry_price) * 100

                        self.log(f"EXIT filled for {leg.leg_type.value.upper()} @ {leg.strike}: ${avg_fill_price} (P&L: ${leg.pnl:.2f})")

                        # Move to closed
                        self.closed_legs.append(leg)
                        del self.active_legs[leg_id]
                        self.save_positions()

                    elif status in ['rejected', 'canceled']:
                        leg.exit_order_status = OrderStatus.REJECTED
                        self.log(f"EXIT {status} for {leg.leg_type.value.upper()} @ {leg.strike}", "WARNING")
                        self.save_positions()

    def should_exit_leg(self, leg: TradierLeg, current_date: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a leg should be exited

        PDT Protection: Don't exit if entered today
        """
        # Must be filled first
        if leg.entry_order_status != OrderStatus.FILLED:
            return False, None

        # PDT PROTECTION
        if leg.entry_date == current_date:
            return False, None

        # Get current quote
        quote = self.api.get_option_quote(leg.option_symbol)
        if not quote:
            return False, None

        # Use mid price
        bid = quote.get('bid', 0)
        ask = quote.get('ask', 0)

        if bid <= 0 or ask <= 0:
            return False, None

        current_price = (bid + ask) / 2
        pnl_pct = ((current_price - leg.entry_price) / leg.entry_price) * 100

        # Profit target
        if pnl_pct >= self.profit_target_pct:
            return True, "PROFIT_TARGET"

        # Stop loss
        if pnl_pct <= -self.stop_loss_pct:
            return True, "STOP_LOSS"

        return False, None

    def exit_leg(self, leg: TradierLeg, exit_reason: str):
        """Exit a leg via Tradier API"""
        # Get current quote
        quote = self.api.get_option_quote(leg.option_symbol)
        if not quote:
            self.log(f"Failed to get quote for exit: {leg.option_symbol}", "ERROR")
            return

        bid = quote.get('bid', 0)
        ask = quote.get('ask', 0)
        mid_price = (bid + ask) / 2

        # Place exit order
        order_result = self.api.place_option_order(
            option_symbol=leg.option_symbol,
            quantity=self.contracts_per_leg,
            side='sell_to_close',
            order_type='limit',
            price=mid_price
        )

        if not order_result:
            self.log(f"Failed to place exit order for {leg.option_symbol}", "ERROR")
            return

        order_data = order_result.get('order', {})
        order_id = order_data.get('id')

        now = datetime.now()
        leg.exit_date = now.strftime('%Y-%m-%d')
        leg.exit_time = now.strftime('%H:%M:%S')
        leg.exit_order_id = order_id
        leg.exit_order_status = OrderStatus.PENDING
        leg.exit_reason = exit_reason

        self.save_positions()

        self.log(f"Placed EXIT order for {leg.leg_type.value.upper()} @ {leg.strike} (Reason: {exit_reason}, Order ID: {order_id})")

    def check_entries(self, df: pd.DataFrame, current_price: float,
                     zero_gex: Optional[float], gex_signal: str,
                     call_wall: Optional[float], put_wall: Optional[float],
                     expiration: str):
        """Check for new entry signals"""
        # Check if we have active calls/puts
        has_active_call = any(
            leg.leg_type == LegType.CALL and leg.entry_order_status == OrderStatus.FILLED
            for leg in self.active_legs.values()
        )
        has_active_put = any(
            leg.leg_type == LegType.PUT and leg.entry_order_status == OrderStatus.FILLED
            for leg in self.active_legs.values()
        )

        # Enter calls on BUY signals or if we have puts but no calls
        if call_wall and not has_active_call:
            if gex_signal == "BUY" or has_active_put:
                self.enter_leg(
                    LegType.CALL, call_wall, expiration,
                    current_price, zero_gex, gex_signal
                )

        # Enter puts on SELL signals or if we have calls but no puts
        if put_wall and not has_active_put:
            if gex_signal == "SELL" or has_active_call:
                self.enter_leg(
                    LegType.PUT, put_wall, expiration,
                    current_price, zero_gex, gex_signal
                )

    def process_market_snapshot(self):
        """Process current market state"""
        current_dt = datetime.now()
        current_date = current_dt.strftime('%Y-%m-%d')
        current_time = current_dt.time()

        # Only trade during market hours (9:30 AM - 4:00 PM ET)
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)

        if not (market_open <= current_time <= market_close):
            self.log("Outside market hours", "DEBUG")
            return

        # Check order fills first
        self.check_order_fills()

        # Get latest GEX data
        df = self.get_latest_snapshot()

        if df.empty:
            self.log("No GEX data available", "WARNING")
            return

        # Get 0DTE options
        df_0dte = df[df['expiration_date'] == current_date].copy()

        if df_0dte.empty:
            self.log("No 0DTE options available", "WARNING")
            return

        current_price = df_0dte['spx_price'].iloc[0]
        zero_gex = self.calculate_zero_gex(df_0dte)
        gex_signal = self.get_gex_signal(df_0dte, current_price)
        call_wall, put_wall = self.find_gex_walls(df_0dte, current_price)

        self.log(f"SPX: {current_price:.2f} | Zero GEX: {zero_gex} | Signal: {gex_signal} | Walls: C={call_wall} P={put_wall}")

        # Check exits (PDT protected)
        for leg_id, leg in list(self.active_legs.items()):
            should_exit, reason = self.should_exit_leg(leg, current_date)
            if should_exit:
                self.exit_leg(leg, reason)

        # Check entries
        self.check_entries(
            df_0dte, current_price, zero_gex, gex_signal,
            call_wall, put_wall, current_date
        )

    def run(self, check_interval_seconds: int = 300):
        """
        Run the trading engine

        Args:
            check_interval_seconds: How often to check the market (default 5 minutes)
        """
        self.log("=" * 60)
        self.log("TRADIER PAPER TRADING ENGINE STARTED")
        self.log("=" * 60)
        self.log(f"Account: {TRADIER_ACCOUNT}")
        self.log(f"Check Interval: {check_interval_seconds}s")

        # Get initial balance
        balance = self.api.get_account_balance()
        if balance:
            balances = balance.get('balances', {})
            self.log(f"Starting Balance: ${balances.get('total_equity', 0):,.2f}")

        try:
            while True:
                self.process_market_snapshot()
                time.sleep(check_interval_seconds)

        except KeyboardInterrupt:
            self.log("Shutting down...", "INFO")
            self.save_positions()


def main():
    """Main entry point"""
    # Connect to database
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("Connected to database")
    except Exception as e:
        print(f"ERROR: Could not connect to database: {e}")
        return

    # Create trading engine
    engine = TradierPaperTrading(conn)

    # Run (checks market every 5 minutes)
    engine.run(check_interval_seconds=300)


if __name__ == "__main__":
    main()
