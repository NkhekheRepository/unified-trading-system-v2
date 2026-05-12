#!/usr/bin/env python3
"""
System health check and quick start for the enhanced trading system.
Usage:
    python3 check_health.py         # Check status only
    python3 check_health.py start   # Start the system
    python3 check_health.py stop   # Stop the system
"""
import os
import sys
import time
import hmac
import hashlib
import asyncio
import aiohttp
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = f'{SCRIPT_DIR}/.env'
BASE = 'https://testnet.binancefuture.com'

def load_keys():
    key = secret = ''
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith('BINANCE_TESTNET_API_KEY'):
                key = line.split('=', 1)[1]
            if line.startswith('BINANCE_TESTNET_API_SECRET'):
                secret = line.split('=', 1)[1]
    return key, secret

async def check_positions(key, secret):
    ts = int(time.time() * 1000)
    query = f'timestamp={ts}'
    sig = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    url = f'{BASE}/fapi/v2/positionRisk?{query}&signature={sig}'
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers={'X-MBX-APIKEY': key}) as r:
            data = await r.json()
            return [p for p in data if float(p.get('positionAmt', 0)) != 0]

async def check_account(key, secret):
    ts = int(time.time() * 1000)
    query = f'timestamp={ts}'
    sig = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    url = f'{BASE}/fapi/v2/account?{query}&signature={sig}'
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers={'X-MBX-APIKEY': key}) as r:
            return await r.json()

def check_process():
    result = subprocess.run(['pgrep', '-f', 'run_enhanced_testnet.py'], 
                      capture_output=True, text=True)
    return result.stdout.strip()

async def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'status'
    
    key, secret = load_keys()
    if not key or not secret:
        print('ERROR: API keys not found')
        return
    
    if action == 'start':
        print('Starting enhanced trading system...')
        subprocess.Popen(['bash', f'{SCRIPT_DIR}/start_enhanced.sh'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print('System started.')
        return
    
    if action == 'stop':
        pid = check_process()
        if pid:
            subprocess.run(['kill', pid])
            print(f'Stopped process {pid}')
        else:
            print('No running process found')
        return
    
    # Status check
    print('=' * 60)
    print('ENHANCED TRADING SYSTEM - HEALTH CHECK')
    print('=' * 60)
    
    # Process check
    pid = check_process()
    if pid:
        print(f'✅ Loop running (PID: {pid})')
    else:
        print('❌ Loop NOT running')
    
    # API check
    try:
        account = await check_account(key, secret)
        balance = float(account.get('totalWalletBalance', 0))
        unrealized = float(account.get('totalUnrealizedProfit', 0))
        print(f'✅ API connected')
        print(f'   Balance: ${balance:.2f}')
        print(f'   Unrealized PnL: ${unrealized:.2f}')
    except Exception as e:
        print(f'❌ API error: {e}')
    
    # Positions check
    try:
        positions = await check_positions(key, secret)
        print(f'📊 Open positions: {len(positions)}')
        for p in positions[:5]:
            amt = float(p['positionAmt'])
            pnl = float(p['unRealizedProfit'])
            side = 'LONG' if amt > 0 else 'SHORT'
            print(f'   {p["symbol"]:10} {side:5} {abs(amt):>8} @ ${pnl:>6.2f}')
    except Exception as e:
        print(f'❌ Position check error: {e}')
    
    print('=' * 60)

if __name__ == '__main__':
    asyncio.run(main())