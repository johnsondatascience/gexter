#!/usr/bin/env python3
"""
Test Tradier API Connection

Verifies connection to Tradier sandbox account and displays account information.
"""

import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()

# Tradier API configuration
# Try sandbox-specific key first, fallback to regular API key
TRADIER_API_KEY = os.getenv('TRADIER_SANDBOX_API_KEY') or os.getenv('TRADIER_API_KEY')
TRADIER_ACCOUNT = os.getenv('TRADIER_SANDBOX_ACCOUNT', 'VA86061098')  # Sandbox account

# Use sandbox endpoint
BASE_URL = 'https://sandbox.tradier.com/v1'

def get_account_balance():
    """Get account balance from Tradier"""

    url = f'{BASE_URL}/accounts/{TRADIER_ACCOUNT}/balances'

    headers = {
        'Authorization': f'Bearer {TRADIER_API_KEY}',
        'Accept': 'application/json'
    }

    print(f"\nQuerying Tradier Sandbox Account: {TRADIER_ACCOUNT}")
    print(f"Endpoint: {url}")
    print("-" * 80)

    try:
        response = requests.get(url, headers=headers)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if 'balances' in data:
                balances = data['balances']

                print("\nCONNECTION SUCCESSFUL!")
                print("=" * 80)
                print("ACCOUNT BALANCES")
                print("=" * 80)

                # Account info
                print(f"\nAccount Number: {TRADIER_ACCOUNT}")
                print(f"Account Type: {balances.get('account_type', 'N/A')}")

                # Cash balances
                print(f"\nCash Balances:")
                print(f"  Total Cash: ${balances.get('total_cash', 0):,.2f}")
                print(f"  Cash Available: ${balances.get('cash_available', 0):,.2f}")
                print(f"  Option Buying Power: ${balances.get('option_buying_power', 0):,.2f}")
                print(f"  Day Trading Buying Power: ${balances.get('day_trading_buying_power', 0):,.2f}")

                # Equity
                print(f"\nEquity:")
                print(f"  Total Equity: ${balances.get('total_equity', 0):,.2f}")
                print(f"  Market Value: ${balances.get('market_value', 0):,.2f}")

                # Profit/Loss
                print(f"\nProfit/Loss:")
                print(f"  Close P&L: ${balances.get('close_pl', 0):,.2f}")
                print(f"  Open P&L: ${balances.get('open_pl', 0):,.2f}")

                # Options
                print(f"\nOptions:")
                print(f"  Option Long Value: ${balances.get('option_long_value', 0):,.2f}")
                print(f"  Option Short Value: ${balances.get('option_short_value', 0):,.2f}")

                # Margin (if applicable)
                if balances.get('margin'):
                    margin = balances['margin']
                    print(f"\nMargin:")
                    print(f"  Fed Call: ${margin.get('fed_call', 0):,.2f}")
                    print(f"  Maintenance Call: ${margin.get('maintenance_call', 0):,.2f}")
                    print(f"  Option Requirement: ${margin.get('option_requirement', 0):,.2f}")

                print("\n" + "=" * 80)

                # Save response for inspection
                with open('output/tradier_balances.json', 'w') as f:
                    json.dump(data, f, indent=2)
                print("\nFull response saved to: output/tradier_balances.json")

                return True

            else:
                print("\nERROR: No balances data in response")
                print(f"Response: {response.text}")
                return False

        else:
            print(f"\nERROR: Request failed")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"\nEXCEPTION: {e}")
        return False


def get_positions():
    """Get current positions"""

    url = f'{BASE_URL}/accounts/{TRADIER_ACCOUNT}/positions'

    headers = {
        'Authorization': f'Bearer {TRADIER_API_KEY}',
        'Accept': 'application/json'
    }

    print("\n" + "=" * 80)
    print("CURRENT POSITIONS")
    print("=" * 80)

    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()

            if 'positions' in data and data['positions'] != 'null':
                positions = data['positions']['position']

                # Handle single position (not a list)
                if not isinstance(positions, list):
                    positions = [positions]

                print(f"\nTotal Positions: {len(positions)}")

                for pos in positions:
                    print(f"\n  Symbol: {pos.get('symbol')}")
                    print(f"  Quantity: {pos.get('quantity')}")
                    print(f"  Cost Basis: ${pos.get('cost_basis', 0):,.2f}")
                    print(f"  Date Acquired: {pos.get('date_acquired', 'N/A')}")

                # Save response
                with open('output/tradier_positions.json', 'w') as f:
                    json.dump(data, f, indent=2)
                print("\nFull positions saved to: output/tradier_positions.json")

            else:
                print("\nNo open positions")

            return True

        else:
            print(f"\nERROR getting positions: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"\nEXCEPTION: {e}")
        return False


def get_profile():
    """Get user profile"""

    url = f'{BASE_URL}/user/profile'

    headers = {
        'Authorization': f'Bearer {TRADIER_API_KEY}',
        'Accept': 'application/json'
    }

    print("\n" + "=" * 80)
    print("USER PROFILE")
    print("=" * 80)

    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()

            if 'profile' in data:
                profile = data['profile']

                print(f"\nName: {profile.get('name', 'N/A')}")
                print(f"Account ID: {profile.get('id', 'N/A')}")

                # Accounts
                if 'account' in profile:
                    accounts = profile['account']
                    if not isinstance(accounts, list):
                        accounts = [accounts]

                    print(f"\nLinked Accounts:")
                    for acc in accounts:
                        print(f"  - {acc.get('account_number')} ({acc.get('classification')}) - {acc.get('type')}")

                # Save response
                with open('output/tradier_profile.json', 'w') as f:
                    json.dump(data, f, indent=2)
                print("\nFull profile saved to: output/tradier_profile.json")

            return True

        else:
            print(f"\nERROR getting profile: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"\nEXCEPTION: {e}")
        return False


def main():
    """Run all tests"""

    print("\n" + "=" * 80)
    print("TRADIER SANDBOX CONNECTION TEST")
    print("=" * 80)

    # Check if API key is set
    if not TRADIER_API_KEY:
        print("\nERROR: TRADIER_API_KEY not found in .env file")
        print("\nPlease add your Tradier API key to .env:")
        print("  TRADIER_API_KEY=your_api_key_here")
        return

    print(f"\nAPI Key found: {TRADIER_API_KEY[:10]}...{TRADIER_API_KEY[-4:]}")
    print(f"Account: {TRADIER_ACCOUNT}")
    print(f"Environment: SANDBOX")

    os.makedirs('output', exist_ok=True)

    # Run tests
    success = True

    # 1. Get account balance
    if not get_account_balance():
        success = False

    # 2. Get positions
    if not get_positions():
        success = False

    # 3. Get profile
    if not get_profile():
        success = False

    # Summary
    print("\n" + "=" * 80)
    if success:
        print("ALL TESTS PASSED - Tradier connection is working!")
        print("\nYou're ready to paper trade with Tradier API")
    else:
        print("SOME TESTS FAILED - Please check the errors above")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
