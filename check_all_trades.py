import asyncio
import aiohttp
import os
from dotenv import load_dotenv
load_dotenv()

async def check_recent_trades():
    # Setup session
    base_url = "https://api.ig.com/gateway/deal"
    api_key = os.getenv('IG_MARKETS_API_KEY')
    username = os.getenv('IG_MARKETS_USERNAME')
    password = os.getenv('IG_MARKETS_PASSWORD')
    
    async with aiohttp.ClientSession() as session:
        # Authenticate
        auth_headers = {
            'X-IG-API-KEY': api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Version': '2'
        }
        
        auth_payload = {
            'identifier': username,
            'password': password
        }
        
        async with session.post(f"{base_url}/session", json=auth_payload, headers=auth_headers) as response:
            security_token = response.headers.get('CST')
            client_token = response.headers.get('X-SECURITY-TOKEN')
        
        headers = {
            'X-IG-API-KEY': api_key,
            'CST': security_token,
            'X-SECURITY-TOKEN': client_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Version': '1'
        }
        
        # Check recent deal references from logs
        deal_refs = [
            'PRGREQG6Y94TYNK',  # Most recent (0.5 size)
            '8PFUPND82S8TYNK',  # Earlier (4.9 size)
            'N55B6C4BR24TYNK',  # Earlier (4.9 size)
        ]
        
        for deal_ref in deal_refs:
            print(f"\n{'='*60}")
            print(f"Checking Deal: {deal_ref}")
            print('='*60)
            
            url = f"{base_url}/confirms/{deal_ref}"
            
            async with session.get(url, headers=headers) as response:
                print(f"Status Code: {response.status}")
                text = await response.text()
                
                try:
                    import json
                    data = json.loads(text)
                    print(json.dumps(data, indent=2))
                    
                    # Highlight key fields
                    if data.get('dealStatus'):
                        print(f"\n🔍 DEAL STATUS: {data.get('dealStatus')}")
                    if data.get('reason'):
                        print(f"🔍 REASON: {data.get('reason')}")
                    if data.get('affectedDeals'):
                        print(f"🔍 AFFECTED DEALS: {data.get('affectedDeals')}")
                        
                except:
                    print(f"Response text: {text}")
        
        # Also check current positions
        print(f"\n{'='*60}")
        print("CURRENT OPEN POSITIONS")
        print('='*60)
        
        positions_url = f"{base_url}/positions"
        headers['Version'] = '2'
        
        async with session.get(positions_url, headers=headers) as response:
            if response.status == 200:
                positions_data = await response.json()
                import json
                print(json.dumps(positions_data, indent=2))
            else:
                print(f"Error getting positions: {await response.text()}")

asyncio.run(check_recent_trades())
