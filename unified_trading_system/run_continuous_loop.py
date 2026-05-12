#!/usr/bin/env python3
"""
Start the continuous trading loop connected to real Binance Futures Testnet
"""

import asyncio
import os
import logging
import aiohttp
import hmac
import hashlib
import time
from datetime import datetime
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
logger = logging.getLogger("trading_loop")


class BinanceFuturesClient:
    """Real Binance Futures Testnet API client"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = BINANCE_BASE_URL
        self.positions = {}
        self.balance = {}
    
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
    
    async def get_position(self, symbol: str) -> Dict:
        params = {'symbol': symbol}
        result = await self._request('GET', '/fapi/v2/positionRisk', params)
        for pos in result:
            if pos['symbol'] == symbol:
                return pos
        return {'positionAmt': '0', 'entryPrice': '0', 'unrealizedProfit': '0'}


async def place_order(client: BinanceFuturesClient, symbol: str, side: str, quantity: float) -> Dict:
    """Place an order on Binance"""
    try:
        order = await client.create_order(symbol, side, 'MARKET', quantity)
        
        # Send Telegram alert
        from observability.alerting import configure_alerting_from_env, send_trade_execution_alert
        configure_alerting_from_env()
        
        await send_trade_execution_alert(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=0,  # Market order
            success=True
        )
        
        return order
    except Exception as e:
        logger.error(f"Order failed: {e}")
        return {"error": str(e)}


async def run_trading_cycle(client: BinanceFuturesClient, cycle_num: int):
    """Run a single trading cycle"""
    logger.info(f"Starting cycle_{cycle_num}")
    
    symbols = ["BTCUSDT", "ETHUSDT"]
    
    for symbol in symbols:
        try:
            # Get ticker data
            ticker = await client.get_ticker(symbol)
            price = float(ticker.get('lastPrice', 0))
            change_24h = float(ticker.get('priceChangePercent', 0))
            
            logger.info(f"{symbol}: ${price} ({change_24h:+.2f}%)")
            
            # Simple signal: buy on dip, sell on spike
            # This is a demo strategy - you can enhance it with belief state
            signal = None
            
            if change_24h < -2:  # More than 2% down - potential buy
                signal = "BUY"
                quantity = 0.001  # Small quantity for safety
            elif change_24h > 2:  # More than 2% up - potential sell
                signal = "SELL"  
                quantity = 0.001
            
            if signal:
                logger.info(f"  Signal: {signal} {quantity} {symbol}")
                order = await place_order(client, symbol, signal, quantity)
                
                if 'orderId' in order:
                    logger.info(f"  Order placed: {order['orderId']}")
                else:
                    logger.warning(f"  Order failed: {order}")
            
        except Exception as e:
            logger.error(f"  Error processing {symbol}: {e}")
    
    # Check account balance
    try:
        account = await client.get_account()
        logger.info(f"Balance: ${account.get('availableBalance', 'N/A')} USDT")
    except Exception as e:
        logger.error(f"Failed to get account: {e}")
    
    logger.info(f"Completed cycle_{cycle_num}")
    return True


async def main():
    print("=" * 60)
    print("CONTINUOUS TRADING LOOP - BINANCE FUTURES TESTNET")
    print("=" * 60)
    print("Starting trading...")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    # Initialize Binance client
    client = BinanceFuturesClient(BINANCE_API_KEY, BINANCE_API_SECRET)
    
    # Send startup alert
    os.environ['TELEGRAM_BOT_TOKEN'] = '8668023431:AAFJl08NZTtpkpfSjfjVbKvLkPeFwRbVxCE'
    os.environ['TELEGRAM_CHAT_IDS'] = '7361240735'
    from observability.alerting import configure_alerting_from_env, send_system_status_alert
    configure_alerting_from_env()
    await send_system_status_alert(
        component='trading_loop',
        status='started',
        details={
            'mode': 'BINANCE_TESTNET',
            'message': 'Continuous trading loop started'
        }
    )
    
    cycle_num = 0
    
    try:
        while True:
            cycle_num += 1
            await run_trading_cycle(client, cycle_num)
            
            # Wait 60 seconds before next cycle
            await asyncio.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Shutdown requested...")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await send_system_status_alert(
            component='trading_loop',
            status='stopped',
            details={'cycles': cycle_num}
        )
        print("\n✅ Trading loop stopped.")


if __name__ == "__main__":
    asyncio.run(main())
