#!/usr/bin/env python3
"""
Black-Scholes Option Pricing and Greeks Calculator

Calculates real-time option greeks using current market data and implied volatility.
This allows for fresh greeks every collection run, independent of Tradier's
greeks.updated_at timestamp.
"""

import numpy as np
from scipy.stats import norm
from typing import Dict, Literal, Optional
import pandas as pd
from datetime import datetime, date
import logging

logger = logging.getLogger('gex_collector')


class BlackScholesCalculator:
    """
    Black-Scholes calculator for European-style options (like SPX).

    Calculates option prices and greeks using:
    - S: Current underlying price
    - K: Strike price
    - T: Time to expiration (years)
    - r: Risk-free rate (annual)
    - sigma: Implied volatility (annual)
    - q: Dividend yield (annual)
    """

    def __init__(self, risk_free_rate: float = 0.045, dividend_yield: float = 0.013):
        """
        Initialize calculator with market parameters.

        Args:
            risk_free_rate: Annual risk-free rate (default: 4.5%)
            dividend_yield: Annual dividend yield for SPX (default: 1.3%)
        """
        self.risk_free_rate = risk_free_rate
        self.dividend_yield = dividend_yield
        logger.info(f"Black-Scholes calculator initialized: r={risk_free_rate:.3f}, q={dividend_yield:.3f}")

    def _calculate_d1_d2(self, S: float, K: float, T: float, r: float, sigma: float, q: float) -> tuple:
        """Calculate d1 and d2 for Black-Scholes formula"""
        if T <= 0 or sigma <= 0:
            return None, None

        d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        return d1, d2

    def calculate_option_price(self, S: float, K: float, T: float, sigma: float,
                               option_type: Literal['call', 'put'],
                               r: Optional[float] = None, q: Optional[float] = None) -> float:
        """
        Calculate option price using Black-Scholes formula.

        Args:
            S: Current underlying price
            K: Strike price
            T: Time to expiration (years)
            sigma: Implied volatility (annual, as decimal)
            option_type: 'call' or 'put'
            r: Risk-free rate (uses instance default if None)
            q: Dividend yield (uses instance default if None)

        Returns:
            Option price
        """
        r = r if r is not None else self.risk_free_rate
        q = q if q is not None else self.dividend_yield

        if T <= 0:
            # Expired option
            if option_type == 'call':
                return max(0, S - K)
            else:
                return max(0, K - S)

        if sigma <= 0:
            return 0.0

        d1, d2 = self._calculate_d1_d2(S, K, T, r, sigma, q)
        if d1 is None:
            return 0.0

        if option_type == 'call':
            price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:  # put
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)

        return max(0, price)

    def calculate_delta(self, S: float, K: float, T: float, sigma: float,
                       option_type: Literal['call', 'put'],
                       r: Optional[float] = None, q: Optional[float] = None) -> float:
        """Calculate option delta (∂V/∂S)"""
        r = r if r is not None else self.risk_free_rate
        q = q if q is not None else self.dividend_yield

        if T <= 0 or sigma <= 0:
            return 0.0

        d1, _ = self._calculate_d1_d2(S, K, T, r, sigma, q)
        if d1 is None:
            return 0.0

        if option_type == 'call':
            delta = np.exp(-q * T) * norm.cdf(d1)
        else:  # put
            delta = -np.exp(-q * T) * norm.cdf(-d1)

        return delta

    def calculate_gamma(self, S: float, K: float, T: float, sigma: float,
                       r: Optional[float] = None, q: Optional[float] = None) -> float:
        """Calculate option gamma (∂²V/∂S²) - same for calls and puts"""
        r = r if r is not None else self.risk_free_rate
        q = q if q is not None else self.dividend_yield

        if T <= 0 or sigma <= 0 or S <= 0:
            return 0.0

        d1, _ = self._calculate_d1_d2(S, K, T, r, sigma, q)
        if d1 is None:
            return 0.0

        gamma = (np.exp(-q * T) * norm.pdf(d1)) / (S * sigma * np.sqrt(T))
        return gamma

    def calculate_theta(self, S: float, K: float, T: float, sigma: float,
                       option_type: Literal['call', 'put'],
                       r: Optional[float] = None, q: Optional[float] = None) -> float:
        """Calculate option theta (∂V/∂T) - per year, divide by 365 for daily"""
        r = r if r is not None else self.risk_free_rate
        q = q if q is not None else self.dividend_yield

        if T <= 0 or sigma <= 0:
            return 0.0

        d1, d2 = self._calculate_d1_d2(S, K, T, r, sigma, q)
        if d1 is None:
            return 0.0

        term1 = -(S * norm.pdf(d1) * sigma * np.exp(-q * T)) / (2 * np.sqrt(T))

        if option_type == 'call':
            term2 = q * S * norm.cdf(d1) * np.exp(-q * T)
            term3 = -r * K * np.exp(-r * T) * norm.cdf(d2)
        else:  # put
            term2 = -q * S * norm.cdf(-d1) * np.exp(-q * T)
            term3 = r * K * np.exp(-r * T) * norm.cdf(-d2)

        theta = term1 + term2 + term3
        return theta / 365  # Convert to daily theta

    def calculate_vega(self, S: float, K: float, T: float, sigma: float,
                      r: Optional[float] = None, q: Optional[float] = None) -> float:
        """Calculate option vega (∂V/∂σ) - same for calls and puts"""
        r = r if r is not None else self.risk_free_rate
        q = q if q is not None else self.dividend_yield

        if T <= 0 or sigma <= 0:
            return 0.0

        d1, _ = self._calculate_d1_d2(S, K, T, r, sigma, q)
        if d1 is None:
            return 0.0

        vega = S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T)
        return vega / 100  # Per 1% change in volatility

    def calculate_rho(self, S: float, K: float, T: float, sigma: float,
                     option_type: Literal['call', 'put'],
                     r: Optional[float] = None, q: Optional[float] = None) -> float:
        """Calculate option rho (∂V/∂r)"""
        r = r if r is not None else self.risk_free_rate
        q = q if q is not None else self.dividend_yield

        if T <= 0 or sigma <= 0:
            return 0.0

        _, d2 = self._calculate_d1_d2(S, K, T, r, sigma, q)
        if d2 is None:
            return 0.0

        if option_type == 'call':
            rho = K * T * np.exp(-r * T) * norm.cdf(d2)
        else:  # put
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2)

        return rho / 100  # Per 1% change in interest rate

    def calculate_all_greeks(self, S: float, K: float, T: float, sigma: float,
                            option_type: Literal['call', 'put'],
                            r: Optional[float] = None, q: Optional[float] = None) -> Dict[str, float]:
        """
        Calculate all greeks at once (more efficient than individual calls).

        Returns:
            Dictionary with keys: delta, gamma, theta, vega, rho, price
        """
        r = r if r is not None else self.risk_free_rate
        q = q if q is not None else self.dividend_yield

        # Handle edge cases
        if T <= 0:
            intrinsic = max(0, S - K) if option_type == 'call' else max(0, K - S)
            return {
                'delta': 0.0,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0,
                'rho': 0.0,
                'price': intrinsic
            }

        if sigma <= 0 or S <= 0:
            return {
                'delta': 0.0,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0,
                'rho': 0.0,
                'price': 0.0
            }

        # Calculate d1 and d2 once
        d1, d2 = self._calculate_d1_d2(S, K, T, r, sigma, q)
        if d1 is None:
            return {
                'delta': 0.0,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0,
                'rho': 0.0,
                'price': 0.0
            }

        # Common terms
        exp_qt = np.exp(-q * T)
        exp_rt = np.exp(-r * T)
        pdf_d1 = norm.pdf(d1)
        sqrt_T = np.sqrt(T)

        # Calculate greeks
        if option_type == 'call':
            price = S * exp_qt * norm.cdf(d1) - K * exp_rt * norm.cdf(d2)
            delta = exp_qt * norm.cdf(d1)
            theta_term2 = q * S * norm.cdf(d1) * exp_qt
            theta_term3 = -r * K * exp_rt * norm.cdf(d2)
            rho = K * T * exp_rt * norm.cdf(d2)
        else:  # put
            price = K * exp_rt * norm.cdf(-d2) - S * exp_qt * norm.cdf(-d1)
            delta = -exp_qt * norm.cdf(-d1)
            theta_term2 = -q * S * norm.cdf(-d1) * exp_qt
            theta_term3 = r * K * exp_rt * norm.cdf(-d2)
            rho = -K * T * exp_rt * norm.cdf(-d2)

        gamma = (exp_qt * pdf_d1) / (S * sigma * sqrt_T)
        theta_term1 = -(S * pdf_d1 * sigma * exp_qt) / (2 * sqrt_T)
        theta = (theta_term1 + theta_term2 + theta_term3) / 365  # Daily theta
        vega = S * exp_qt * pdf_d1 * sqrt_T / 100  # Per 1% vol change

        return {
            'delta': delta,
            'gamma': gamma,
            'theta': theta,
            'vega': vega,
            'rho': rho / 100,  # Per 1% rate change
            'price': max(0, price)
        }

    def years_to_expiration(self, expiration_date: str, current_date: Optional[datetime] = None) -> float:
        """
        Calculate time to expiration in years.

        Args:
            expiration_date: Expiration date as string (YYYY-MM-DD)
            current_date: Current datetime (uses now if None)

        Returns:
            Time to expiration in years
        """
        if current_date is None:
            current_date = datetime.now()

        if isinstance(expiration_date, str):
            exp_date = datetime.strptime(expiration_date, '%Y-%m-%d')
        else:
            exp_date = expiration_date

        # Calculate days to expiration
        if isinstance(current_date, datetime):
            current_date = current_date.date()
        if isinstance(exp_date, datetime):
            exp_date = exp_date.date()

        days_to_exp = (exp_date - current_date).days

        # Convert to years (using 365 days)
        return max(0, days_to_exp / 365.0)

    def calculate_greeks_for_dataframe(self, df: pd.DataFrame,
                                      underlying_price_col: str = 'spx_price',
                                      iv_col: str = 'greeks.mid_iv',
                                      prefix: str = 'calc_greeks.') -> pd.DataFrame:
        """
        Calculate greeks for entire DataFrame of options.

        Args:
            df: DataFrame with option data
            underlying_price_col: Column name for underlying price
            iv_col: Column name for implied volatility (can use bid_iv, mid_iv, or ask_iv)
            prefix: Prefix for calculated greek columns

        Returns:
            DataFrame with added calculated greek columns
        """
        if df.empty:
            return df

        logger.info(f"Calculating fresh greeks for {len(df)} options using {iv_col}...")

        # Create copy to avoid modifying original
        result_df = df.copy()

        # Initialize columns
        result_df[f'{prefix}delta'] = 0.0
        result_df[f'{prefix}gamma'] = 0.0
        result_df[f'{prefix}theta'] = 0.0
        result_df[f'{prefix}vega'] = 0.0
        result_df[f'{prefix}rho'] = 0.0
        result_df[f'{prefix}price'] = 0.0

        # Get current date for time calculations
        current_date = datetime.now().date()

        # Calculate for each row
        for idx, row in result_df.iterrows():
            try:
                S = row[underlying_price_col]
                K = row['strike']
                sigma = row[iv_col]
                option_type = row['option_type']
                exp_date_str = row['expiration_date']

                # Skip if missing critical data
                if pd.isna(S) or pd.isna(K) or pd.isna(sigma) or sigma <= 0:
                    continue

                # Calculate time to expiration
                T = self.years_to_expiration(exp_date_str, datetime.now())

                # Calculate all greeks
                greeks = self.calculate_all_greeks(S, K, T, sigma, option_type)

                # Store in DataFrame
                result_df.at[idx, f'{prefix}delta'] = greeks['delta']
                result_df.at[idx, f'{prefix}gamma'] = greeks['gamma']
                result_df.at[idx, f'{prefix}theta'] = greeks['theta']
                result_df.at[idx, f'{prefix}vega'] = greeks['vega']
                result_df.at[idx, f'{prefix}rho'] = greeks['rho']
                result_df.at[idx, f'{prefix}price'] = greeks['price']

            except Exception as e:
                logger.debug(f"Error calculating greeks for row {idx}: {e}")
                continue

        # Calculate GEX using calculated gamma
        result_df[f'{prefix}gex'] = (
            result_df['strike'] *
            result_df[f'{prefix}gamma'] *
            result_df['open_interest'] * 100
        )
        # Put options have negative GEX
        result_df.loc[result_df['option_type'] == 'put', f'{prefix}gex'] *= -1

        logger.info("Fresh greeks calculation complete")

        return result_df


def test_black_scholes():
    """Test the Black-Scholes calculator"""
    calculator = BlackScholesCalculator(risk_free_rate=0.045, dividend_yield=0.013)

    # Test case: SPX call option
    S = 6850.0  # SPX price
    K = 6900.0  # Strike
    T = 30 / 365  # 30 days to expiration
    sigma = 0.15  # 15% IV

    print("Test Black-Scholes Calculator")
    print("=" * 50)
    print(f"Underlying: ${S:.2f}")
    print(f"Strike: ${K:.2f}")
    print(f"Time to exp: {T*365:.0f} days")
    print(f"IV: {sigma*100:.1f}%")
    print(f"Risk-free rate: {calculator.risk_free_rate*100:.2f}%")
    print(f"Dividend yield: {calculator.dividend_yield*100:.2f}%")
    print()

    # Calculate call
    call_greeks = calculator.calculate_all_greeks(S, K, T, sigma, 'call')
    print("CALL Option:")
    print(f"  Price: ${call_greeks['price']:.2f}")
    print(f"  Delta: {call_greeks['delta']:.4f}")
    print(f"  Gamma: {call_greeks['gamma']:.6f}")
    print(f"  Theta: ${call_greeks['theta']:.2f} per day")
    print(f"  Vega: ${call_greeks['vega']:.2f} per 1% vol")
    print(f"  Rho: ${call_greeks['rho']:.2f} per 1% rate")
    print()

    # Calculate put
    put_greeks = calculator.calculate_all_greeks(S, K, T, sigma, 'put')
    print("PUT Option:")
    print(f"  Price: ${put_greeks['price']:.2f}")
    print(f"  Delta: {put_greeks['delta']:.4f}")
    print(f"  Gamma: {put_greeks['gamma']:.6f}")
    print(f"  Theta: ${put_greeks['theta']:.2f} per day")
    print(f"  Vega: ${put_greeks['vega']:.2f} per 1% vol")
    print(f"  Rho: ${put_greeks['rho']:.2f} per 1% rate")


if __name__ == "__main__":
    test_black_scholes()
