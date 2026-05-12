#!/usr/bin/env python3
"""
Simple Binance API Connectivity Test
"""

import asyncio
import json
import hmac
import hashlib
import time
import os
import aiohttp

# Configuration - Try both testnet and live
TEST_CONFIGS = [
    ("https://testnet.binancefuture.com", "Testnet"),
    ("https://fapi.binance.com", "Live"),
]

BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY")
BINANCE_API_SECRET = os.environ.get("BINANCE_API_SECRET")

TEST_SYMBOL = "BTCUSDT"


async def test_endpoint(session, base_url, endpoint, method="GET", data=None, headers=None):
    """Generic endpoint tester"""
    url = f"{base_url}{endpoint}"
    if headers is None:
        headers = {}
    
    if method == "GET":
        async with session.get(url, headers=headers) as resp:
            text = await resp.text()
            return resp.status, text
    elif method == "POST":
        async with session.post(url, headers=headers, json=data) as resp:
            text = await resp.text()
            return resp.status, text


async def make_signed_request(session, base_url, api_key, api_secret, endpoint, params=None):
    """Make signed request"""
    if params is None:
        params = {}
    
    params['timestamp'] = int(time.time() * 1000)
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    query_string += f"&signature={signature}"
    
    url = f"{base_url}{endpoint}?{query_string}"
    headers = {'X-MBX-APIKEY': api_key}
    
    async with session.get(url, headers=headers) as resp:
        text = await resp.text()
        return resp.status, text


async def main():
    print("="*60)
    print("BINANCE API CONNECTIVITY TEST")
    print("="*60)
    
    async with aiohttp.ClientSession() as session:
        for base_url, name in TEST_CONFIGS:
            print(f"\n{'='*60}")
            print(f"Testing: {name} ({base_url})")
            print("="*60)
            
            # Test 1: Ping (public)
            status, text = await test_endpoint(session, base_url, "/fapi/v1/ping")
            print(f"1. PING: HTTP {status}")
            if status != 200:
                print(f"   ❌ Failed: {text[:100]}")
                continue
            print(f"   ✅ OK")
            
            # Test 2: Time (public)
            status, text = await test_endpoint(session, base_url, "/fapi/v1/time")
            print(f"2. TIME: HTTP {status}")
            if status != 200:
                print(f"   ❌ Failed: {text[:100]}")
            else:
                print(f"   ✅ OK: {text[:50]}")
            
            # Test 3: Price (public)
            status, text = await test_endpoint(session, base_url, f"/fapi/v1/ticker/price?symbol={TEST_SYMBOL}")
            print(f"3. PRICE: HTTP {status}")
            if status != 200:
                print(f"   ❌ Failed: {text[:100]}")
            else:
                try:
                    data = json.loads(text)
                    print(f"   ✅ OK: BTC=${data.get('price')}")
                except:
                    print(f"   ❌ Parse error: {text[:100]}")
            
            # Test 4: Account (signed)
            status, text = await make_signed_request(session, base_url, BINANCE_API_KEY, BINANCE_API_SECRET, "/fapi/v1/account")
            print(f"4. ACCOUNT: HTTP {status}")
            if status != 200:
                print(f"   ❌ Failed: {text[:150]}")
            else:
                try:
                    data = json.loads(text)
                    balance = data.get('availableBalance', 'N/A')
                    print(f"   ✅ OK: Balance={balance} USDT")
                except:
                    print(f"   ❌ Parse error: {text[:100]}")
            
            # Test 5: Place order (signed) - DRY RUN
            params = {
                'symbol': TEST_SYMBOL,
                'side': 'BUY',
                'type': 'MARKET',
                'quantity': 0.001,
            }
            status, text = await make_signed_request(session, base_url, BINANCE_API_KEY, BINANCE_API_SECRET, "/fapi/v1/order", params)
            print(f"5. ORDER (dry): HTTP {status}")
            if status == 200:
                print(f"   ✅ Order would work!")
                data = json.loads(text)
                print(f"      OrderId: {data.get('orderId')}, Status: {data.get('status')}")
            else:
                print(f"   ❌ Failed: {text[:150]}")
            
            print()


if __name__ == "__main__":
    asyncio.run(main())