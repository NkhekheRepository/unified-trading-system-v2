#!/usr/bin/env python3
"""
Place real orders on Binance Testnet to verify trade execution
"""
import asyncio
import time
import hmac
import hashlib
import aiohttp
import json

API_KEY = os.environ.get("BINANCE_API_KEY")
API_SECRET = os.environ.get("BINANCE_API_SECRET")
BASE_URL = "https://testnet.binancefuture.com"

async def place_order(symbol, side, quantity):
    """Place a market order on Binance Testnet"""
    params = {
        'symbol': symbol,
        'side': side,
        'type': 'MARKET',
        'quantity': quantity,
        'timestamp': int(time.time() * 1000)
    }
    
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(
        API_SECRET.encode(),
        query_string.encode(),
        hashlib.sha256
    ).hexdigest()
    query_string += f"&signature={signature}"
    
    url = f"{BASE_URL}/fapi/v1/order?{query_string}"
    headers = {'X-MBX-APIKEY': API_KEY}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers) as resp:
            result = await resp.json()
            return result

async def main():
    print("=== PLACING REAL ORDERS ON BINANCE TESTNET ===")
    
    # Test with small orders
    orders = [
        ("BTCUSDT", "BUY", 0.001),
        ("ETHUSDT", "BUY", 0.001),
    ]
    
    for symbol, side, qty in orders:
        print(f"\nPlacing {side} {qty} {symbol}...")
        try:
            result = await place_order(symbol, side, qty)
            if 'orderId' in result:
                print(f"✅ SUCCESS! Order ID: {result['orderId']}")
                print(f"   Status: {result.get('status')}")
                print(f"   Price: {result.get('avgPrice', 'N/A')}")
                print(f"   Qty: {result.get('executedQty')}")
            else:
                print(f"❌ FAILED: {result.get('msg', 'Unknown error')}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        await asyncio.sleep(1)
    
    print("\n=== ORDERS COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())
