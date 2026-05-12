#!/usr/bin/env python3
"""
Direct API test to verify keys work with testnet.binancefuture.com
"""
import os
import sys
from binance.client import Client
from dotenv import load_dotenv

def main():
    # Load environment
    load_dotenv('/home/nkhekhe/unified_trading_system/.env')

    api_key = os.getenv('BINANCE_TESTNET_API_KEY')
    api_secret = os.getenv('BINANCE_TESTNET_API_SECRET')
    testnet_url = 'https://testnet.binancefuture.com'

    print("=" * 60)
    print("DIRECT API VALIDATION TEST")
    print("=" * 60)
    print(f"API Key: {api_key[:10]}...")
    print(f"API Secret: {api_secret[:10]}...")
    print(f"Testnet URL: {testnet_url}")
    print()

    try:
        # Initialize client
        client = Client(api_key, api_secret, testnet=True)
        
        # Override URLs to use our testnet
        client.API_URL = testnet_url
        
        print("🔍 Testing connection...")
        # Test 1: System status
        status = client.get_system_status()
        print(f"✅ System Status: {status['msg']}")
        
        # Test 2: Exchange info
        print("🔍 Fetching exchange info...")
        exchange_info = client.futures_exchange_info()
        print(f"✅ Exchange Info: {len(exchange_info['symbols'])} symbols")
        
        # Test 3: Account info
        print("🔍 Fetching account info...")
        account = client.futures_account()
        print(f"✅ Account Retrieved")
        
        # Find USDT balance
        usdt_balance = 0
        for asset in account.get('assets', []):
            if asset['asset'] == 'USDT':
                usdt_balance = float(asset['walletBalance'])
                break
        
        print(f"💰 USDT Balance: ${usdt_balance:.2f}")
        
        # Test 4: Recent prices
        print("🔍 Fetching recent prices...")
        prices = client.futures_symbol_ticker()
        btc_price = float([p for p in prices if p['symbol'] == 'BTCUSDT'][0]['price'])
        print(f"₿ BTC/USDT: ${btc_price:,.2f}")
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED - API KEYS ARE VALID!")
        print("🚀 Ready to place orders on testnet.binancefuture.com")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❠ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)