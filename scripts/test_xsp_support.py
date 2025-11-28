#!/usr/bin/env python3
"""
Test XSP (Micro SPX) Support via Tradier API

This script verifies that XSP options are available and have
sufficient data quality for GEX calculations.
"""

import sys
import os
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.tradier_api import TradierAPI
from src.config import Config
import requests

def main():
    load_dotenv()
    config = Config()
    api = TradierAPI(config.tradier_api_key)

    print("=" * 60)
    print("XSP (MICRO SPX) SUPPORT TEST")
    print("=" * 60)
    print()

    # Test 1: XSP Quote
    print("1. Testing XSP quote availability...")
    try:
        quote = api.get_current_quote('XSP')
        if not quote.empty:
            price = quote['last'].iloc[0]
            volume = quote['volume'].iloc[0]
            print(f"   [OK] XSP quote available")
            print(f"        Price: ${price:.2f}")
            print(f"        Volume: {volume:,.0f}")

            # Compare to SPX
            spx_quote = api.get_current_quote('SPX')
            if not spx_quote.empty:
                spx_price = spx_quote['last'].iloc[0]
                ratio = spx_price / price
                print(f"        SPX/XSP ratio: {ratio:.2f} (should be ~10)")
        else:
            print("   [ERROR] XSP quote not available")
            return False
    except Exception as e:
        print(f"   [ERROR] {e}")
        return False

    print()

    # Test 2: XSP Option Expirations
    print("2. Testing XSP option expirations...")
    try:
        response = requests.get(
            'https://api.tradier.com/v1/markets/options/expirations',
            params={'symbol': 'XSP'},
            headers={
                'Authorization': f'Bearer {config.tradier_api_key}',
                'Accept': 'application/json'
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            expirations = data.get('expirations', {})
            if expirations:
                dates = expirations.get('date', [])
                if isinstance(dates, str):
                    dates = [dates]

                if dates:
                    print(f"   [OK] Found {len(dates)} expirations")
                    print(f"        Next 5: {', '.join(dates[:5])}")

                    # Test option chain for first expiration
                    test_exp = dates[0]
                    print()
                    print(f"3. Testing option chain for {test_exp}...")

                    chain = api.get_chains('XSP', test_exp)
                    if not chain.empty:
                        print(f"   [OK] Option chain available")
                        print(f"        Total contracts: {len(chain)}")

                        # Check Greeks availability
                        with_greeks = chain['greeks.delta'].notna().sum()
                        with_oi = chain['open_interest'].notna().sum()
                        total_oi = chain['open_interest'].sum()

                        print(f"        Contracts with Greeks: {with_greeks} ({with_greeks/len(chain)*100:.1f}%)")
                        print(f"        Contracts with OI: {with_oi} ({with_oi/len(chain)*100:.1f}%)")
                        print(f"        Total open interest: {total_oi:,.0f}")

                        # Show OI by type
                        calls = chain[chain['option_type'] == 'call']
                        puts = chain[chain['option_type'] == 'put']
                        call_oi = calls['open_interest'].sum()
                        put_oi = puts['open_interest'].sum()

                        print(f"        Call OI: {call_oi:,.0f}")
                        print(f"        Put OI: {put_oi:,.0f}")
                        print(f"        Put/Call ratio: {put_oi/call_oi:.2f}")

                        # Sample strikes
                        print()
                        print("   Sample strikes (showing 3 around ATM):")
                        current_price = quote['last'].iloc[0]
                        chain_sorted = chain.sort_values('strike')
                        atm_idx = (chain_sorted['strike'] - current_price).abs().idxmin()
                        atm_position = chain_sorted.index.get_loc(atm_idx)

                        sample_start = max(0, atm_position - 1)
                        sample_end = min(len(chain_sorted), atm_position + 2)
                        sample = chain_sorted.iloc[sample_start:sample_end]

                        for _, row in sample.iterrows():
                            oi = row['open_interest'] if not pd.isna(row['open_interest']) else 0
                            gamma = row['greeks.gamma'] if not pd.isna(row['greeks.gamma']) else 0
                            print(f"        ${row['strike']:.0f} {row['option_type']}: OI={oi:.0f}, Gamma={gamma:.4f}")

                        print()
                        print("=" * 60)
                        print("[SUCCESS] XSP IS FULLY SUPPORTED")
                        print("=" * 60)
                        print()
                        print("Summary:")
                        print(f"  - XSP quote: Available (${price:.2f})")
                        print(f"  - Option expirations: {len(dates)}")
                        print(f"  - Greeks available: Yes ({with_greeks}/{len(chain)} contracts)")
                        print(f"  - Total open interest: {total_oi:,.0f}")
                        print()
                        print("Recommendation:")
                        if total_oi > 10000:
                            print("  [HIGH] XSP has sufficient liquidity for GEX analysis")
                        elif total_oi > 5000:
                            print("  [MEDIUM] XSP has moderate liquidity - suitable for analysis")
                        else:
                            print("  [LOW] XSP has low liquidity - GEX signals may be noisy")

                        return True
                    else:
                        print(f"   [ERROR] Option chain empty")
                        return False
                else:
                    print("   [ERROR] No expiration dates found")
                    return False
            else:
                print("   [ERROR] No expirations data in response")
                return False
        else:
            print(f"   [ERROR] API request failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"   [ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import pandas as pd
    success = main()
    sys.exit(0 if success else 1)
