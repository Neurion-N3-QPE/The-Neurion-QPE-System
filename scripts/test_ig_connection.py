"""
IG Markets API Connection Diagnostic Tool
Tests multiple authentication patterns and provides detailed feedback
"""

import asyncio
import aiohttp
import sys
from pathlib import Path
import pytest

# Credentials
API_KEY = "b8e1f49a835449717ed9ce037e24507f855883e7"
EMAIL = "CHNeural"
PASSWORD = "HfS56DD4p59dYtB5"
ACCOUNT_ID = "HTRFU"

# IG Markets API endpoints
DEMO_URL = "https://demo-api.ig.com/gateway/deal"
LIVE_URL = "https://api.ig.com/gateway/deal"


# Fixtures for test parameters
@pytest.fixture
def base_url():
    return "https://api.ig.com/gateway/deal"


@pytest.fixture
def identifier():
    return "CHNeural"


@pytest.fixture
def api_key():
    return "b8e1f49a835449717ed9ce037e24507f855883e7"


@pytest.fixture
def password():
    return "HfS56DD4p59dYtB5"


@pytest.mark.asyncio
async def test_authentication(base_url, identifier, api_key, password):
    """Test authentication with given identifier"""

    print(f"\nTesting...")
    print(f"  URL: {base_url}")
    print(f"  Identifier: {identifier}")
    print(f"  API Key: {API_KEY[:20]}...")

    url = f"{base_url}/session"

    headers = {
        'X-IG-API-KEY': api_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Version': '2'
    }

    payload = {
        'identifier': identifier,
        'password': password
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:

            status = response.status
            text = await response.text()

            print(f"  Status: {status}")

            if status == 200:
                data = await response.json()
                print(f"  SUCCESS!")
                print(f"  Client ID: {data.get('clientId', 'N/A')}")
                print(f"  Account ID: {data.get('accountId', 'N/A')}")

                # Get account info
                cst = response.headers.get('CST')
                x_security_token = response.headers.get('X-SECURITY-TOKEN', cst)

                accounts_url = f"{base_url}/accounts"
                accounts_headers = {
                    'X-IG-API-KEY': api_key,
                    'CST': cst,
                    'X-SECURITY-TOKEN': x_security_token,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }

                async with session.get(accounts_url, headers=accounts_headers) as acc_response:
                    if acc_response.status == 200:
                        accounts = await acc_response.json()
                        print(f"\n  Account Information:")
                        for acc in accounts.get('accounts', []):
                            print(f"    - Name: {acc.get('accountName')}")
                            print(f"      ID: {acc.get('accountId')}")
                            print(f"      Balance: {acc.get('balance', {}).get('balance')} {acc.get('currency')}")

                return True
            else:
                print(f"  FAILED: {text}")
                return False


async def main():
    """Run diagnostic tests"""

    print("="*70)
    print("IG MARKETS API CONNECTION DIAGNOSTIC")
    print("="*70)

    print("\nCredentials to test:")
    print(f"  Email: {EMAIL}")
    print(f"  Account ID: {ACCOUNT_ID}")
    print(f"  API Key: {API_KEY[:20]}...{API_KEY[-4:]}")

    # Test patterns
    patterns = [
        ("LIVE - Full Email", LIVE_URL, EMAIL),
    ]

    print("\n" + "="*70)
    print("TESTING AUTHENTICATION PATTERNS")
    print("="*70)

    success_count = 0
    for name, url, identifier in patterns:
        result = await test_authentication(url, identifier, name)
        if result:
            success_count += 1
        await asyncio.sleep(1)  # Rate limiting

    print("\n" + "="*70)
    print(f"RESULTS: {success_count}/{len(patterns)} patterns successful")
    print("="*70)

    if success_count == 0:
        print("\nTROUBLESHOOTING:")
        print("1. Verify your IG Markets account is active")
        print("2. Check that API access is enabled in your account settings")
        print("3. Confirm your API key is correct")
        print("4. Try logging into IG Markets web interface to verify credentials")
        print("5. Check if your account requires 2FA (which may block API access)")
        print("\n")
        print("IMPORTANT: IG Markets requires API access to be explicitly enabled.")
        print("Go to: My Account > Settings > API Access")
    else:
        print("\nSUCCESS: At least one authentication method worked!")
        print("The system will use the working configuration.")


if __name__ == "__main__":
    asyncio.run(main())
