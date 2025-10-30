import asyncio
import aiohttp
import os
from dotenv import load_dotenv
load_dotenv()

async def check_deal_confirmation():
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
        
        # Check the deal confirmation
        deal_ref = '8PFUPND82S8TYNK'  # From 18:35:35 log
        
        headers = {
            'X-IG-API-KEY': api_key,
            'CST': security_token,
            'X-SECURITY-TOKEN': client_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Version': '1'
        }
        
        url = f"{base_url}/confirms/{deal_ref}"
        
        async with session.get(url, headers=headers) as response:
            print(f"Status Code: {response.status}")
            text = await response.text()
            print(f"Response: {text}")
            
            try:
                import json
                data = json.loads(text)
                print(f"\n=== Parsed JSON ===")
                print(json.dumps(data, indent=2))
                
                # Check for key status fields
                print(f"\n=== Key Status Fields ===")
                print(f"dealStatus: {data.get('dealStatus')}")
                print(f"status: {data.get('status')}")
                print(f"reason: {data.get('reason')}")
                print(f"affectedDeals: {data.get('affectedDeals')}")
                
            except:
                print("Could not parse as JSON")

asyncio.run(check_deal_confirmation())
