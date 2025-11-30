#!/usr/bin/env python3
"""
Test Tradier API Connection

Verifies connection to Tradier sandbox account and displays account information.
"""

import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()

# Configuration - prioritize sandbox-specific key
TRADIER_API_KEY = os.getenv('TRADIER_SANDBOX_API_KEY') or os.getenv('TRADIER_API_KEY')
TRADIER_ACCOUNT = os.getenv('TRADIER_SANDBOX_ACCOUNT', 'VA86061098')
BASE_URL = 'https://sandbox.tradier.com/v1'

if not TRADIER_API_KEY:
    print("ERROR: No Tradier API key found in .env file")
    print("Please add TRADIER_SANDBOX_API_KEY to your .env file")
    exit(1)


def get_account_balance():
    """Get account balance and cash information"""
    url = f'{BASE_URL}/accounts/{TRADIER_ACCOUNT}/balances'
    headers = {
        'Authorization': f'Bearer {TRADIER_API_KEY}',
        'Accept': 'application/json'
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"ERROR: Failed to get balance")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return None


def get_positions():
    """Get current positions"""
    url = f'{BASE_URL}/accounts/{TRADIER_ACCOUNT}/positions'
    headers = {
        'Authorization': f'Bearer {TRADIER_API_KEY}',
        'Accept': 'application/json'
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"ERROR: Failed to get positions")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return None


def get_profile():
    """Get user profile information"""
    url = f'{BASE_URL}/user/profile'
    headers = {
        'Authorization': f'Bearer {TRADIER_API_KEY}',
        'Accept': 'application/json'
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"ERROR: Failed to get profile")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return None


def main():
    """Test connection and display account information"""
    print("=" * 60)
    print("TRADIER API CONNECTION TEST")
    print("=" * 60)
    print(f"\nAccount: {TRADIER_ACCOUNT}")
    print(f"API Endpoint: {BASE_URL}")
    print(f"Using API Key: {TRADIER_API_KEY[:10]}...")
    print("\n" + "-" * 60)

    # Test 1: Get account balance
    print("\n[1/3] Testing account balance endpoint...")
    balance_data = get_account_balance()

    if balance_data:
        print("SUCCESS: Retrieved account balance")

        # Save to file
        os.makedirs('output', exist_ok=True)
        with open('output/tradier_balances.json', 'w') as f:
            json.dump(balance_data, f, indent=2)

        # Display key metrics
        balances = balance_data.get('balances', {})
        print(f"\n  Account Value: ${balances.get('total_equity', 0):,.2f}")
        print(f"  Cash Available: ${balances.get('total_cash', 0):,.2f}")
        print(f"  Buying Power: ${balances.get('option_buying_power', 0):,.2f}")
        print(f"  Account Type: {balances.get('account_type', 'Unknown')}")
    else:
        print("FAILED: Could not retrieve balance")
        return False

    # Test 2: Get positions
    print("\n[2/3] Testing positions endpoint...")
    positions_data = get_positions()

    if positions_data:
        print("SUCCESS: Retrieved positions")

        # Save to file
        with open('output/tradier_positions.json', 'w') as f:
            json.dump(positions_data, f, indent=2)

        # Display positions
        positions = positions_data.get('positions')
        if positions and positions != 'null':
            position_list = positions.get('position', [])
            if isinstance(position_list, dict):
                position_list = [position_list]

            print(f"\n  Open Positions: {len(position_list)}")
            for pos in position_list:
                print(f"    {pos.get('symbol')}: {pos.get('quantity')} @ ${pos.get('cost_basis', 0):.2f}")
        else:
            print("\n  No open positions")
    else:
        print("FAILED: Could not retrieve positions")
        return False

    # Test 3: Get profile
    print("\n[3/3] Testing profile endpoint...")
    profile_data = get_profile()

    if profile_data:
        print("SUCCESS: Retrieved profile")

        # Save to file
        with open('output/tradier_profile.json', 'w') as f:
            json.dump(profile_data, f, indent=2)

        # Display profile info
        profile = profile_data.get('profile', {})
        account = profile.get('account', {})
        print(f"\n  Account Number: {account.get('account_number', 'Unknown')}")
        print(f"  Classification: {account.get('classification', 'Unknown')}")
        print(f"  Status: {account.get('status', 'Unknown')}")
    else:
        print("FAILED: Could not retrieve profile")
        return False

    # All tests passed
    print("\n" + "=" * 60)
    print("CONNECTION SUCCESSFUL!")
    print("=" * 60)
    print("\nAll Tradier API endpoints are working correctly.")
    print("Results saved to output/ directory.")

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
