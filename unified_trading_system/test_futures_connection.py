#!/usr/bin/env python3
"""
Test connection to Binance Futures Testnet at testnet.binancefuture.com
Get API keys from: https://testnet.binancefuture.com/
"""
import sys
import os
import pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from binance.client import Client
except Exception:
    pytest.importorskip("binance", reason="Binance client not available")
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('BINANCE_TESTNET_API_KEY')
api_secret = os.getenv('BINANCE_TESTNET_API_SECRET')

print("=" * 60)
print("TESTING BINANCE FUTURES TESTNET CONNECTION")
print("URL: testnet.binancefuture.com")
print("=" * 60)

if not api_key or not api_secret:
    print("❌ API keys not found in .env")
    sys.exit(1)

print(f"✓ API Key (first 10): {api_key[:10]}...")
print(f"✓ API Secret (first 10): {api_secret[:10]}...")

try:
    import json
    # Connect to Futures testnet
    # Use testnet=True for testnet connection
    client = Client(api_key, api_secret, testnet=True)
    # Override base URL for Futures testnet
    client.SAPI_URL = 'https://testnet.binancefuture.com'
    client.API_URL = 'https://testnet.binancefuture.com'
    
    # Test connection
    print("\nTesting connection...")
    status = client.get_system_status()
    print(f"✓ System Status: {status}")
    
    # Get account info - use futures methods
    print("\nGetting account info...")
    account = client.futures_account()
    print(f"✓ Account connected!")
    print(f"  Account Type: {account.get('assets', [{}])[0].get('asset', 'N/A')}")
    
    # Show USDT balance
    if 'assets' in account:
        for asset in account['assets']:
            if asset['asset'] == 'USDT':
                wallet_balance = float(asset.get('walletBalance', 0))
                unrealized_pnl = float(asset.get('unrealizedProfit', 0))
                print(f"  USDT Balance: {wallet_balance}")
                print(f"  Unrealized PnL: {unrealized_pnl}")
    
    # Get current positions - use correct method
    positions = client.futures_position_information()
    open_positions = [p for p in positions if float(p['positionAmt']) != 0]
    
    print(f"\n  Open Positions: {len(open_positions)}")
    # Display a few open positions safely
    for pos in open_positions[:5]:
        pnl = pos.get('unrealizedProfit', 'N/A')
        print(f"    {pos['symbol']}: {pos['positionAmt']} (PnL: {pnl})")
    
    print("\n" + "=" * 60)
    print("✓ CONNECTION SUCCESSFUL!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run: python3 verify_enhancements.py")
    print("2. Monitor: tail -f logs/trading.log")
    print("3. Check performance: python3 scoring/score_system.py")
    
except Exception as e:
    print(f"\n❌ Connection failed: {e}")
    print("\nMake sure you:")
    print("1. Got keys from: https://testnet.binancefuture.com/")
    print("2. Keys are correctly saved in .env")
    print("3. Keys are for FUTES ")
    sys.exit(1)
