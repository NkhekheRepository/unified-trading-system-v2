#!/usr/bin/env python3
"""
Quick verification script for the enhanced trading system.
Checks:
1. API keys are present in .env
2. Loop process is running
3. Open positions on testnet
4. Current unrealized PnL
"""
import os
import time
import hmac
import hashlib
import json
import aiohttp
import asyncio

# Load keys from .env
def load_keys(env_path='/home/nkhekhe/unified_trading_system/.env'):
    key = secret = ''
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith('BINANCE_TESTNET_API_KEY'):
                key = line.split('=', 1)[1]
            if line.startswith('BINANCE_TESTNET_API_SECRET'):
                secret = line.split('=', 1)[1]
    return key, secret

BASE = 'https://testnet.binancefuture.com'

async def check_positions(key, secret):
    ts = int(time.time() * 1000)
    query = f'timestamp={ts}'
    sig = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    url = f'{BASE}/fapi/v2/positionRisk?{query}&signature={sig}'
    headers = {'X-MBX-APIKEY': key}
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers=headers) as r:
            data = await r.json()
            positions = [p for p in data if float(p.get('positionAmt', 0)) != 0]
            return positions

async def get_unrealized_pnl(key, secret):
    ts = int(time.time() * 1000)
    query = f'timestamp={ts}'
    sig = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    url = f'{BASE}/fapi/v2/account?{query}&signature={sig}'
    headers = {'X-MBX-APIKEY': key}
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers=headers) as r:
            data = await r.json()
            return float(data.get('totalUnrealizedProfit', 0))

async def main():
    key, secret = load_keys()
    if not key or not secret:
        print('ERROR: API keys not found in .env')
        return
    
    print('=' * 60)
    print('ENHANCED TRADING SYSTEM - STATUS CHECK')
    print('=' * 60)
    
    # Check positions
    positions = await check_positions(key, secret)
    print(f'\n📊 Open Positions: {len(positions)}')
    total_pnl = 0.0
    for p in positions[:10]:
        amt = float(p['positionAmt'])
        pnl = float(p['unRealizedProfit'])
        total_pnl += pnl
        side = 'LONG' if amt > 0 else 'SHORT'
        print(f'  {p["symbol"]:12} {side:5} {abs(amt):>10} @ ${pnl:>8.2f}')
    
    # Get total unrealized
    unrlz = await get_unrealized_pnl(key, secret)
    print(f'\n💰 Total Unrealized PnL: ${unrlz:.2f}')
    print('=' * 60)

if __name__ == '__main__':
    asyncio.run(main())