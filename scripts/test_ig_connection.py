"""
Test IG Markets API Connection
Verifies credentials and account access
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.ig_markets_api import IGMarketsAPI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_connection():
    """Test IG Markets connection"""
    
    print("="*60)
    print("🔗 TESTING IG MARKETS API CONNECTION")
    print("="*60)
    
    # Your credentials
    api_key = "58ab902e80ec5a4c8a367376d14115df8a284744"
    username = "contact@NeuralNetWorth.co.uk"
    password = "HfS56DD4p59dYtB5"
    account_id = "HTRFU"
    
    print("\n📋 Configuration:")
    print(f"   Account: N3-QPE")
    print(f"   Account ID: {account_id}")
    print(f"   Mode: LIVE")
    print(f"   Username: {username}")
    
    try:
        # Initialize API
        api = IGMarketsAPI(
            api_key=api_key,
            username=username,
            password=password,
            account_id=account_id,
            demo=False  # LIVE mode
        )
        
        # Test connection
        print("\n🔐 Authenticating...")
        await api.initialize()
        
        print("✅ Authentication successful!")
        
        # Get account info
        print("\n💰 Fetching account information...")
        account_info = await api.get_account_info()
        
        if account_info:
            print("\n" + "="*60)
            print("📊 ACCOUNT DETAILS")
            print("="*60)
            
            # Display account info
            for account in account_info.get('accounts', []):
                if account.get('accountId') == account_id:
                    print(f"\n   Account Name: {account.get('accountName', 'N/A')}")
                    print(f"   Account ID: {account.get('accountId', 'N/A')}")
                    print(f"   Balance: £{account.get('balance', {}).get('balance', 'N/A')}")
                    print(f"   Available: £{account.get('balance', {}).get('available', 'N/A')}")
                    print(f"   Deposit: £{account.get('balance', {}).get('deposit', 'N/A')}")
                    print(f"   Profit/Loss: £{account.get('balance', {}).get('profitLoss', 'N/A')}")
                    print(f"   Currency: {account.get('currency', 'N/A')}")
                    break
        
        # Test market data
        print("\n📈 Testing market data access...")
        market_data = await api.get_market_data("CS.D.GBPUSD.TODAY.IP")
        
        if market_data:
            print("✅ Market data access working!")
            instrument = market_data.get('instrument', {})
            snapshot = market_data.get('snapshot', {})
            
            print(f"\n   Instrument: {instrument.get('name', 'N/A')}")
            print(f"   Epic: {instrument.get('epic', 'N/A')}")
            print(f"   Bid: {snapshot.get('bid', 'N/A')}")
            print(f"   Ask: {snapshot.get('offer', 'N/A')}")
            print(f"   Spread: {snapshot.get('offer', 0) - snapshot.get('bid', 0):.5f}")
        
        # Get positions
        print("\n📊 Checking open positions...")
        positions = await api.get_positions()
        
        if positions:
            print(f"   Open positions: {len(positions)}")
            for pos in positions:
                print(f"   - {pos.get('market', {}).get('instrumentName', 'N/A')}")
        else:
            print("   No open positions")
        
        # Cleanup
        await api.shutdown()
        
        print("\n" + "="*60)
        print("✅ CONNECTION TEST SUCCESSFUL!")
        print("="*60)
        print("\n🎯 Your IG Markets account is ready for trading!")
        print("   Run: python main.py")
        
    except Exception as e:
        print(f"\n❌ CONNECTION TEST FAILED!")
        print(f"   Error: {e}")
        print("\n🔍 Troubleshooting:")
        print("   1. Verify your credentials are correct")
        print("   2. Check your IG Markets account is active")
        print("   3. Ensure API access is enabled")
        print("   4. Check your internet connection")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
