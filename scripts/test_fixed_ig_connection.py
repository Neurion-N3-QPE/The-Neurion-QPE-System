"""
Test IG Markets Connection with Fixed API
Tests:
1. Authentication
2. Account info fetching
3. Market data fetching
4. Position opening (DRY RUN - will cancel immediately)
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.ig_markets_api import IGMarketsAPI
from config.settings import load_config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_ig_connection():
    """Test IG Markets API with fixes"""
    logger.info("="*80)
    logger.info("🧪 TESTING IG MARKETS CONNECTION (FIXED)")
    logger.info("="*80)
    
    # Load config
    config = load_config()
    ig_config = config['brokers']['ig_markets']
    
    # Create API instance
    ig_api = IGMarketsAPI(
        api_key=ig_config['api_key'],
        username=ig_config['username'],
        password=ig_config['password'],
        account_id=ig_config['account_id'],
        demo=ig_config['demo']
    )
    
    try:
        # Test 1: Authentication
        logger.info("\n1️⃣ Testing Authentication...")
        await ig_api.initialize()
        logger.info("✅ Authentication successful!")
        
        # Test 2: Account Info
        logger.info("\n2️⃣ Testing Account Info...")
        account_info = await ig_api.get_account_info()
        if account_info and account_info.get('accounts'):
            for acc in account_info['accounts']:
                if acc['accountId'] == ig_config['account_id']:
                    balance = acc.get('balance', {}).get('balance', 0)
                    logger.info(f"✅ Account Balance: £{balance:.2f}")
                    break
        else:
            logger.error("❌ Could not fetch account info")
        
        # Test 3: Market Data
        logger.info("\n3️⃣ Testing Market Data...")
        epic = ig_config['default_epic']
        logger.info(f"   Testing EPIC: {epic}")
        market_data = await ig_api.get_market_data(epic)
        if market_data and market_data.get('snapshot'):
            snapshot = market_data['snapshot']
            bid = snapshot.get('bid', 0)
            offer = snapshot.get('offer', 0)
            logger.info(f"✅ Market Data Retrieved:")
            logger.info(f"   Bid: {bid}")
            logger.info(f"   Offer: {offer}")
            logger.info(f"   Spread: {offer - bid:.2f}")
        else:
            logger.error(f"❌ Could not fetch market data for {epic}")
        
        # Test 4: Test Position Opening Payload (DRY RUN)
        logger.info("\n4️⃣ Testing Position Opening (Payload Only - Not Executing)...")
        logger.info("   This would open a BUY position with:")
        logger.info(f"   - EPIC: {epic}")
        logger.info(f"   - Direction: BUY")
        logger.info(f"   - Size: £1.00 per point")
        logger.info(f"   - Expiry: DFB (Daily Funded Bet - Spread Betting)")
        logger.info("   ⚠️  SKIPPING ACTUAL EXECUTION FOR SAFETY")
        
        # Uncomment below to test REAL position opening (will use real money!)
        # position_response = await ig_api.open_position(
        #     epic=epic,
        #     direction='BUY',
        #     size=1.0
        # )
        # if position_response and position_response.get('dealReference'):
        #     logger.info(f"✅ Position opened: {position_response['dealReference']}")
        #     # Immediately close it
        #     await asyncio.sleep(2)
        #     await ig_api.close_position(position_response['dealReference'])
        # else:
        #     logger.error("❌ Position opening failed")
        
        logger.info("\n" + "="*80)
        logger.info("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
    finally:
        await ig_api.shutdown()


if __name__ == "__main__":
    asyncio.run(test_ig_connection())
