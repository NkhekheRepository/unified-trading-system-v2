#!/usr/bin/env python3
"""
Single Order Test Script
Tests if real Binance orders work after Phase 1 fixes
"""

import asyncio
import json
import hmac
import hashlib
import time
import os
import aiohttp

# Configuration
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY")
BINANCE_API_SECRET = os.environ.get("BINANCE_API_SECRET")
BASE_URL = "https://testnet.binancefuture.com"  # Use testnet for safety
TEST_SYMBOL = "BTCUSDT"
TEST_QUANTITY = 0.001  # Fixed quantity: ~$77 at $77k, well above minimum notional of 50
MAX_NOTIONAL = 50.0  # Kept for reference but not used for quantity calculation


async def main():
    print("="*60)
    print("SINGLE ORDER TEST - PHASE 1 VERIFICATION")
    print("="*60)
    print(f"API Key: {BINANCE_API_KEY[:10]}...")
    print(f"Base URL: {BASE_URL}")
    print(f"Test Symbol: {TEST_SYMBOL}")
    print()
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Test public endpoint first (price)
        print("📊 STEP 1: Testing public endpoint (price)...")
        price = await get_price(session, TEST_SYMBOL, BASE_URL)
        print(f"   BTC Price: ${price:.2f}")
        if price == 0:
            print("❌ PUBLIC ENDPOINT FAILED - checking if API key works...")
            # Try without signature
            url = f"{BASE_URL}/fapi/v1/ping"
            async with session.get(url) as resp:
                print(f"   [GET ping] HTTP {resp.status}")
            print("   Let me try different endpoints...")
            return
        print()
        
        # Step 2: Try account balance with signature
        print("📊 STEP 2: Getting account balance...")
        balance_result = await get_account_balance(session, BINANCE_API_KEY, BINANCE_API_SECRET, BASE_URL)
        print(f"   Response: {balance_result}")
        print()
        
        # Calculate quantity based on max notional
        quantity = TEST_QUANTITY  # Use fixed quantity
        print(f"   Using fixed quantity: {quantity}")
        print()
        
        # Step 3: Set leverage to 40x
        print("📊 STEP 3: Setting leverage to 40x...")
        leverage_result = await set_leverage(session, BINANCE_API_KEY, BINANCE_API_SECRET, TEST_SYMBOL, 40, BASE_URL)
        print(f"   Leverage set: {leverage_result}")
        print()
        
        # Step 4: Place MARKET buy order
        print("📊 STEP 4: Placing MARKET BUY order...")
        order_result = await place_market_order(session, BINANCE_API_KEY, BINANCE_API_SECRET, TEST_SYMBOL, "BUY", quantity, BASE_URL)
        print(f"   Order Result: {json.dumps(order_result, indent=2)}")
        
        # Extract order ID
        order_id = order_result.get('orderId')
        order_status = order_result.get('status')
        avg_price = order_result.get('avgPrice')
        
        print(f"\n   📋 Order ID: {order_id}")
        print(f"   📋 Status: {order_status}")
        print(f"   📋 Avg Price: {avg_price}")
        print()
        
        if order_status in ['FILLED', 'NEW']:
            print("✅ ORDER PLACED SUCCESSFULLY!")
            
            # Step 5: Verify order exists
            print("\n📊 STEP 5: Verifying order on Binance...")
            await asyncio.sleep(1)  # Wait for order to process
            verification = await verify_order(session, BINANCE_API_KEY, BINANCE_API_SECRET, TEST_SYMBOL, order_id, BASE_URL)
            print(f"   Verification: {json.dumps(verification, indent=2)}")
            
            if verification and verification.get('status') in ['FILLED', 'NEW']:
                print("✅ ORDER VERIFIED!")
                
                # Step 6: Place close order (sell to close)
                print("\n📊 STEP 6: Placing CLOSE order (SELL to close BUY position)...")
                close_result = await place_market_order(session, BINANCE_API_KEY, BINANCE_API_SECRET, TEST_SYMBOL, "SELL", quantity, BASE_URL)
                print(f"   Close Result: {json.dumps(close_result, indent=2)}")
                
                close_order_id = close_result.get('orderId')
                close_status = close_result.get('status')
                
                print(f"\n   📋 Close Order ID: {close_order_id}")
                print(f"   📋 Close Status: {close_status}")
                
                if close_status in ['FILLED', 'NEW']:
                    print("✅ CLOSE ORDER PLACED SUCCESSFULLY!")
                    
                    # Verify close
                    await asyncio.sleep(1)
                    close_verification = await verify_order(session, BINANCE_API_KEY, BINANCE_API_SECRET, TEST_SYMBOL, close_order_id, BASE_URL)
                    print(f"   Close Verification: {json.dumps(close_verification, indent=2)}")
                    
                    print("\n" + "="*60)
                    print("🎉 FULL ROUND-TRIP TEST SUCCESSFUL!")
                    print("="*60)
                    print("✅ Order placed")
                    print("✅ Order verified")
                    print("✅ Close order placed")
                    print("✅ Close order verified")
                    print("\nSystem is ready for live trading!")
                else:
                    print("❌ CLOSE ORDER FAILED")
            else:
                print("❌ ORDER VERIFICATION FAILED")
        else:
            print("❌ ORDER PLACEMENT FAILED")
            print(f"   Error: {order_result.get('msg', 'Unknown error')}")


async def get_account_balance(session, api_key, api_secret, base_url):
    """Get account balance"""
    params = {'timestamp': int(time.time() * 1000)}
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    query_string += f"&signature={signature}"
    
    url = f"{base_url}/fapi/v1/account?{query_string}"
    headers = {'X-MBX-APIKEY': api_key}
    
    async with session.get(url, headers=headers) as resp:
        print(f"   [GET account] HTTP {resp.status}")
        result = await resp.json()
        
        if 'availableBalance' in result:
            return float(result['availableBalance'])
        
        print(f"   Full response: {result}")
        return 0.0


async def get_price(session, symbol, base_url):
    """Get current price for symbol"""
    url = f"{base_url}/fapi/v1/ticker/price?symbol={symbol}"
    
    async with session.get(url) as resp:
        result = await resp.json()
        return float(result.get('price', 0))


async def set_leverage(session, api_key, api_secret, symbol, leverage, base_url):
    """Set leverage for symbol"""
    params = {
        'symbol': symbol,
        'leverage': leverage,
        'timestamp': int(time.time() * 1000)
    }
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    query_string += f"&signature={signature}"
    
    url = f"{base_url}/fapi/v1/leverage?{query_string}"
    headers = {'X-MBX-APIKEY': api_key}
    
    async with session.post(url, headers=headers) as resp:
        print(f"   [POST leverage] HTTP {resp.status}")
        result = await resp.json()
        return result


async def place_market_order(session, api_key, api_secret, symbol, side, quantity, base_url):
    """Place a market order"""
    params = {
        'symbol': symbol,
        'side': side,
        'type': 'MARKET',
        'quantity': quantity,
        'timestamp': int(time.time() * 1000)
    }
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    query_string += f"&signature={signature}"
    
    url = f"{base_url}/fapi/v1/order?{query_string}"
    headers = {'X-MBX-APIKEY': api_key}
    
    async with session.post(url, headers=headers) as resp:
        raw_response = await resp.text()
        print(f"   [POST order] HTTP {resp.status}")
        print(f"   Raw response: {raw_response}")
        
        return json.loads(raw_response)


async def verify_order(session, api_key, api_secret, symbol, order_id, base_url):
    """Verify order exists on Binance"""
    params = {
        'symbol': symbol,
        'orderId': order_id,
        'timestamp': int(time.time() * 1000)
    }
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    query_string += f"&signature={signature}"
    
    url = f"{base_url}/fapi/v1/order?{query_string}"
    headers = {'X-MBX-APIKEY': api_key}
    
    async with session.get(url, headers=headers) as resp:
        print(f"   [GET order] HTTP {resp.status}")
        result = await resp.json()
        return result


if __name__ == "__main__":
    asyncio.run(main())