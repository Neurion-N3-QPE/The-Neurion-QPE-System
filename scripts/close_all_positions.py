"""
Close all open positions - for controlled testing
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.ig_markets_api import IGMarketsAPI
from config.settings import load_config


async def close_all_positions():
    config = load_config()
    ig_config = config['brokers']['ig_markets']
    
    api = IGMarketsAPI(
        api_key=ig_config['api_key'],
        username=ig_config['username'],
        password=ig_config['password'],
        account_id=ig_config['account_id'],
        demo=ig_config.get('demo', False)
    )
    
    await api.initialize()
    
    print(f"\n{'='*60}")
    print("CLOSING ALL POSITIONS")
    print(f"{'='*60}\n")
    
    # Get current positions
    positions = await api.get_positions()
    
    if not positions:
        print("✅ No open positions found")
        await api.close_session()
        return
    
    print(f"📊 Found {len(positions)} open position(s)")
    
    for i, pos_data in enumerate(positions, 1):
        deal_id = pos_data['position']['dealId']
        size = pos_data['position']['size']
        direction = pos_data['position']['direction']
        level = pos_data['position']['level']
        epic = pos_data['market']['epic']
        
        print(f"\n{i}. Position: {deal_id}")
        print(f"   Epic: {epic}")
        print(f"   Direction: {direction}")
        print(f"   Size: £{size}/point")
        print(f"   Entry: {level}")
        
        print(f"   🔄 Closing position...")
        result = await api.close_position(deal_id)
        
        if result and result.get('dealReference'):
            print(f"   ✅ Position closed! Deal reference: {result['dealReference']}")
        else:
            print(f"   ❌ Failed to close position")
    
    await api.close_session()
    print(f"\n{'='*60}")
    print("POSITION CLOSING COMPLETE")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(close_all_positions())
