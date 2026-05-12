"""
Binance Market Data Feed for Unified Trading System
Provides real market data from Binance Futures Testnet
"""
import asyncio
import logging
import time
from typing import Dict, Optional
import aiohttp
import hmac
import hashlib

from perception.market_data_feed import MarketDataFeed, FeedType, MarketDataUpdate


class BinanceFuturesMarketDataFeed(MarketDataFeed):
    """
    Real Binance Futures Testnet market data feed
    """
    
    def __init__(self, symbol: str, api_key: str, api_secret: str):
        super().__init__(symbol)
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://testnet.binancefuture.com"
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Store latest market data for belief state
        self.latest_ticker_data: Dict = {}
        self.latest_order_book_data: Dict = {}
        self.last_update_time: float = 0
        
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
        
        if self.session is None:
            self.session = aiohttp.ClientSession()
            
        async with self.session.request(method, url, headers=headers) as resp:
            return await resp.json()
    
    async def connect(self) -> bool:
        """Establish connection to Binance"""
        try:
            if self.session is None:
                self.session = aiohttp.ClientSession()
            
            # Test connection by getting account info
            account = await self._request('GET', '/fapi/v2/account')
            self.is_connected = True
            self.last_update_time = time.time_ns()
            return True
        except Exception as e:
            logging.getLogger("binance.feed").error(f"Failed to connect to Binance: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close connection to Binance"""
        if self.session:
            await self.session.close()
            self.session = None
        self.is_connected = False
    
    async def subscribe(self, feed_types: list[FeedType]) -> bool:
        """Subscribe to market data feeds"""
        if not self.is_connected:
            if not await self.connect():
                return False
        
        # For Binance REST API, we don't need explicit subscription for REST endpoints
        # We'll poll for data instead
        self._subscribed_feeds.update(feed_types)
        self.last_update_time = time.time_ns()
        return True
    
    async def unsubscribe(self, feed_types: list[FeedType]) -> None:
        """Unsubscribe from market data feeds"""
        self._subscribed_feeds.difference_update(feed_types)
    
    async def fetch_and_emit_ticker(self):
        """Fetch ticker data and emit update"""
        try:
            ticker = await self._request('GET', '/fapi/v1/ticker/24hr', {'symbol': self.symbol.replace('/', '')})
            
            # Store latest ticker data
            price = float(ticker.get('lastPrice', ticker.get('price', 0)))
            self.latest_ticker_data = {
                "symbol": self.symbol,
                "price": price,
                "bid_price": price * 0.999,  # Approximate bid from last price
                "ask_price": price * 1.001,  # Approximate ask from last price
                "bid_size": float(ticker.get('bidQty', ticker.get('volume', 1))) * 0.1,
                "ask_size": float(ticker.get('askQty', ticker.get('volume', 1))) * 0.1,
                "last_price": price,
                "last_size": float(ticker.get('lastQty', ticker.get('volume', 1))) * 0.01,
                "volume": float(ticker.get('volume', 0)),
                "timestamp": time.time_ns()
            }
            
            # Emit ticker update
            self._emit_update(FeedType.TICKER, self.latest_ticker_data)
            
            self.last_update_time = time.time_ns()
            
        except Exception as e:
            logging.getLogger("binance.feed").error(f"Error fetching ticker for {self.symbol}: {e}")
    
    async def fetch_and_emit_order_book(self):
        """Fetch order book data and emit update"""
        try:
            order_book = await self._request('GET', '/fapi/v1/orderBook', {
                'symbol': self.symbol.replace('/', ''),
                'limit': 10  # Get top 10 bids/asks
            })
            
            # Store latest order book data
            if order_book.get('bids') and order_book.get('asks'):
                self.latest_order_book_data = {
                    "symbol": self.symbol,
                    "bid_price": float(order_book['bids'][0][0]),
                    "ask_price": float(order_book['asks'][0][0]),
                    "bid_size": float(order_book['bids'][0][1]),
                    "ask_size": float(order_book['asks'][0][1]),
                    "last_price": (float(order_book['bids'][0][0]) + float(order_book['asks'][0][0])) / 2,
                    "last_size": 0.0,  # Not available in order book snapshot
                    "volume": 0.0,  # Not available in order book snapshot
                    "timestamp": time.time_ns()
                }
                
                # Emit order book data
                self._emit_update(FeedType.ORDER_BOOK, self.latest_order_book_data)
            
            self.last_update_time = time.time_ns()
            
        except Exception as e:
            logging.getLogger("binance.feed").error(f"Error fetching order book for {self.symbol}: {e}")