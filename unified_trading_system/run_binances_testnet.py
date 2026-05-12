#!/usr/bin/env python3
"""
Start the trading system with real Binance Futures Testnet connection
"""

import asyncio
import os
import logging
import aiohttp
import hmac
import hashlib
import time
from typing import Dict, Optional

# Binance API credentials
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY")
BINANCE_API_SECRET = os.environ.get("BINANCE_API_SECRET")
BINANCE_BASE_URL = "https://testnet.binancefuture.com"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)


class BinanceFuturesClient:
    """Real Binance Futures Testnet API client"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = BINANCE_BASE_URL
    
    def _sign(self, params: str) -> str:
        return hmac.new(
            self.api_secret.encode(),
            params.encode(),
            hashlib.sha256
        ).hexdigest()
    
    async def _request(self, method: str, endpoint: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        
        params['timestamp'] = int(time.time() * 1000)
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        signature = self._sign(query_string)
        query_string += f"&signature={signature}"
        
        url = f"{self.base_url}{endpoint}?{query_string}"
        headers = {'X-MBX-APIKEY': self.api_key}
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers) as resp:
                return await resp.json()
    
    async def get_account(self) -> Dict:
        return await self._request('GET', '/fapi/v2/account')
    
    async def get_balance(self) -> Dict:
        return await self._request('GET', '/fapi/v2/balance')
    
    async def get_position_risk(self) -> Dict:
        return await self._request('GET', '/fapi/v2/positionRisk')
    
    async def get_ticker(self, symbol: str) -> Dict:
        return await self._request('GET', '/fapi/v1/ticker/24hr', {'symbol': symbol})
    
    async def get_klines(self, symbol: str, interval: str = '1m', limit: int = 100) -> Dict:
        return await self._request('GET', '/fapi/v1/klines', {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        })
    
    async def create_order(self, symbol: str, side: str, order_type: str, 
                          quantity: float, price: Optional[float] = None) -> Dict:
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity,
        }
        if price:
            params['price'] = price
            params['timeInForce'] = 'GTC'
        
        return await self._request('POST', '/fapi/v1/order', params)


async def main():
    print("=" * 60)
    print("BINANCE FUTURES TESTNET TRADING SYSTEM")
    print("=" * 60)
    print(f"Mode: REAL TESTNET (Binance Futures)")
    print(f"Symbols: BTCUSDT, ETHUSDT")
    print("=" * 60)
    
    # Create Binance client
    client = BinanceFuturesClient(BINANCE_API_KEY, BINANCE_API_SECRET)
    
    # Get account info
    print("\n📊 Fetching account info...")
    account = await client.get_account()
    print(f"✅ Account connected!")
    print(f"   Total Balance: {account.get('totalWalletBalance', 'N/A')} USDT")
    print(f"   Available: {account.get('availableBalance', 'N/A')} USDT")
    
    # Get positions
    print("\n📈 Fetching positions...")
    positions = await client.get_position_risk()
    print(f"✅ Positions: {len(positions)}")
    for pos in positions[:3]:
        if float(pos.get('positionAmt', 0)) != 0:
            print(f"   {pos['symbol']}: {pos['positionAmt']} @ {pos['entryPrice']}")
    
    # Get ticker
    print("\n💰 Fetching BTCUSDT ticker...")
    ticker = await client.get_ticker('BTCUSDT')
    print(f"✅ BTCUSDT:")
    print(f"   Last Price: ${ticker.get('lastPrice', 'N/A')}")
    print(f"   24h Change: {ticker.get('priceChangePercent', 'N/A')}%")
    print(f"   24h High: ${ticker.get('highPrice', 'N/A')}")
    print(f"   24h Low: ${ticker.get('lowPrice', 'N/A')}")
    
    print("\n" + "=" * 60)
    print("🚀 System ready for live testnet trading!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
