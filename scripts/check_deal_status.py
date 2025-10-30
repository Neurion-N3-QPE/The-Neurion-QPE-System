"""
Check the actual status of recent deal references
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.ig_markets_api import IGMarketsAPI
from config.settings import load_config


async def check_deal(deal_ref: str):
    """Check a specific deal reference"""
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
    print(f"Checking deal reference: {deal_ref}")
    print(f"{'='*60}\n")
    
    # Get deal confirmation
    url = f"{api.base_url}/confirms/{deal_ref}"
    headers = api._get_headers()
    
    async with api.session.get(url, headers=headers) as response:
        status_code = response.status
        response_text = await response.text()
        
        print(f"Status Code: {status_code}")
        print(f"Response: {response_text}\n")
        
        try:
            data = await response.json()
            
            # Print all fields
            for key, value in data.items():
                print(f"{key}: {value}")
                
        except Exception as e:
            print(f"Could not parse JSON: {e}")
    
    await api.close_session()


async def main():
    # Recent deal references from logs
    deal_refs = [
        "8PFUPND82S8TYNK",  # Most recent
        "N55B6C4BR24TYNK",  # Previous one
        "W2FY9XZTZQUTYNK",  # From earlier
    ]
    
    for deal_ref in deal_refs:
        try:
            await check_deal(deal_ref)
            print("\n")
        except Exception as e:
            print(f"Error checking {deal_ref}: {e}\n")
        
        await asyncio.sleep(1)  # Rate limit


if __name__ == "__main__":
    asyncio.run(main())
