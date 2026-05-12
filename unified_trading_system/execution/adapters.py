"""
Testnet Exchange Adapters for Unified Trading System
Provides paper trading with realistic exchange simulation.
"""

import asyncio
import hashlib
import hmac
import json
import time
import random
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import logging


class TestnetExchange(ABC):
    """Abstract base class for testnet exchanges"""
    
    def __init__(self, name: str, paper_balance: Dict[str, float]):
        self.name = name
        self.paper_balance = paper_balance
        self.orders: Dict[str, Dict] = {}
        self.order_counter = 0
        self._logger = logging.getLogger(f"testnet.{name}")
    
    @abstractmethod
    async def get_balance(self, symbol: str) -> Dict[str, float]:
        """Get account balance"""
        pass
    
    @abstractmethod
    async def create_order(self, order_type: str, symbol: str, side: str,
                          quantity: float, price: Optional[float] = None) -> Dict:
        """Create an order"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> Dict:
        """Get order status"""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict:
        """Get current ticker price"""
        pass
    
    def _generate_order_id(self) -> str:
        """Generate unique order ID"""
        self.order_counter += 1
        return f"{self.name.lower()}_{self.order_counter}_{int(time.time() * 1000)}"


class PaperTradingExchange(TestnetExchange):
    """
    Paper trading simulator with realistic price simulation
    """
    
    def __init__(self, name: str, paper_balance: Dict[str, float], 
                 base_prices: Optional[Dict[str, float]] = None,
                 price_volatility: float = 0.001):
        super().__init__(name, paper_balance)
        
        self.base_prices = base_prices or {
            "BTC/USDT": 50000.0,
            "ETH/USDT": 3000.0,
            "SOL/USDT": 100.0,
            "BNB/USDT": 400.0,
            "XRP/USDT": 0.5,
        }
        self.price_volatility = price_volatility
        self.current_prices = self.base_prices.copy()
        self.order_fills: Dict[str, List[Dict]] = {}
        
    async def get_balance(self, symbol: str) -> Dict[str, float]:
        """Get paper trading balance"""
        base, quote = symbol.split("/")
        return {
            "free": self.paper_balance.get(base, 0.0),
            "locked": 0.0,
            f"{quote.lower()}_balance": self.paper_balance.get(quote, 0.0),
        }
    
    async def create_order(self, order_type: str, symbol: str, side: str,
                          quantity: float, price: Optional[float] = None) -> Dict:
        """Create a paper trading order"""
        order_id = self._generate_order_id()
        
        current_price = self._get_current_price(symbol)
        
        order = {
            "orderId": order_id,
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
            "price": price or current_price,
            "status": "NEW",
            "createdTime": int(time.time() * 1000),
            "updatedTime": int(time.time() * 1000),
            "filledQuantity": 0.0,
            "averageFillPrice": 0.0,
        }
        
        self.orders[order_id] = order
        
        if order_type == "MARKET":
            await self._fill_market_order(order)
        
        return order
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a paper trading order"""
        if order_id in self.orders:
            order = self.orders[order_id]
            if order["status"] in ("NEW", "PARTIALLY_FILLED"):
                order["status"] = "CANCELED"
                order["updatedTime"] = int(time.time() * 1000)
                return True
        return False
    
    async def get_order_status(self, order_id: str) -> Dict:
        """Get order status"""
        return self.orders.get(order_id, {})
    
    async def get_ticker(self, symbol: str) -> Dict:
        """Get current ticker with simulated price"""
        price = self._get_current_price(symbol)
        spread = price * 0.0005
        
        return {
            "symbol": symbol,
            "lastPrice": price,
            "bidPrice": price - spread,
            "askPrice": price + spread,
            "volume24h": random.uniform(1000000, 10000000),
            "timestamp": int(time.time() * 1000),
        }
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Dict:
        """Get simulated order book"""
        price = self._get_current_price(symbol)
        
        bids = []
        asks = []
        
        for i in range(limit):
            bid_price = price * (1 - (i + 1) * 0.0001)
            ask_price = price * (1 + (i + 1) * 0.0001)
            bid_qty = random.uniform(0.1, 10.0)
            ask_qty = random.uniform(0.1, 10.0)
            
            bids.append([bid_price, bid_qty])
            asks.append([ask_price, ask_qty])
        
        return {
            "symbol": symbol,
            "bids": bids,
            "asks": asks,
            "timestamp": int(time.time() * 1000),
        }
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get all open orders"""
        orders = [o for o in self.orders.values() 
                 if o["status"] in ("NEW", "PARTIALLY_FILLED")]
        
        if symbol:
            orders = [o for o in orders if o["symbol"] == symbol]
        
        return orders
    
    async def get_positions(self) -> List[Dict]:
        """Get current positions"""
        positions = []
        
        for symbol in self.base_prices.keys():
            base = symbol.split("/")[0]
            if self.paper_balance.get(base, 0) > 0:
                positions.append({
                    "symbol": symbol,
                    "quantity": self.paper_balance.get(base, 0),
                    "entryPrice": self.base_prices[symbol],
                    "currentPrice": self._get_current_price(symbol),
                    "unrealizedPnL": self._calculate_pnl(symbol),
                })
        
        return positions
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price with random walk simulation"""
        if symbol not in self.current_prices:
            self.current_prices[symbol] = self.base_prices.get(symbol, 100.0)
        
        change = random.gauss(0, self.price_volatility)
        self.current_prices[symbol] *= (1 + change)
        
        return self.current_prices[symbol]
    
    async def _fill_market_order(self, order: Dict):
        """Fill a market order immediately"""
        symbol = order["symbol"]
        quantity = order["quantity"]
        side = order["side"]
        
        fill_price = self._get_current_price(symbol)
        
        base, quote = symbol.split("/")
        
        if side == "BUY":
            required_quote = quantity * fill_price
            if self.paper_balance.get(quote, 0) >= required_quote:
                self.paper_balance[quote] -= required_quote
                self.paper_balance[base] = self.paper_balance.get(base, 0) + quantity
                order["filledQuantity"] = quantity
                order["averageFillPrice"] = fill_price
                order["status"] = "FILLED"
        else:
            if self.paper_balance.get(base, 0) >= quantity:
                self.paper_balance[base] -= quantity
                self.paper_balance[quote] = self.paper_balance.get(quote, 0) + quantity * fill_price
                order["filledQuantity"] = quantity
                order["averageFillPrice"] = fill_price
                order["status"] = "FILLED"
        
        order["updatedTime"] = int(time.time() * 1000)
    
    def _calculate_pnl(self, symbol: str) -> float:
        """Calculate unrealized PnL for a position"""
        base = symbol.split("/")[0]
        quantity = self.paper_balance.get(base, 0)
        
        if quantity == 0:
            return 0.0
        
        entry_price = self.base_prices.get(symbol, 0)
        current_price = self._get_current_price(symbol)
        
        return (current_price - entry_price) * quantity
    
    def set_price(self, symbol: str, price: float):
        """Manually set price for a symbol"""
        self.base_prices[symbol] = price
        self.current_prices[symbol] = price


class BinanceTestnetAdapter(PaperTradingExchange):
    """Binance Testnet adapter"""
    
    def __init__(self, api_key: str = "test_api_key", 
                 api_secret: str = "test_api_secret",
                 paper_balance: Optional[Dict[str, float]] = None):
        
        balance = paper_balance or {
            "BTC": 1.0,
            "ETH": 10.0,
            "USDT": 100000.0,
            "BNB": 50.0,
            "SOL": 100.0,
        }
        
        super().__init__("BINANCE_TESTNET", balance)
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://testnet.binancefuture.com"
    
    async def get_server_time(self) -> Dict:
        """Get server time"""
        return {
            "serverTime": int(time.time() * 1000),
        }


class CoinbaseSandboxAdapter(PaperTradingExchange):
    """Coinbase Sandbox adapter"""
    
    def __init__(self, api_key: str = "test_api_key",
                 api_secret: str = "test_api_secret",
                 paper_balance: Optional[Dict[str, float]] = None):
        
        balance = paper_balance or {
            "BTC": 1.0,
            "ETH": 10.0,
            "USD": 100000.0,
            "SOL": 100.0,
        }
        
        super().__init__("COINBASE_SANDBOX", balance)
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api-public.sandbox.pro.coinbase.com"


class TestnetExchangeManager:
    """Manages multiple testnet exchanges"""
    
    def __init__(self):
        self.exchanges: Dict[str, TestnetExchange] = {}
        self._logger = logging.getLogger("testnet.manager")
    
    def add_exchange(self, exchange: TestnetExchange):
        """Add an exchange to the manager"""
        self.exchanges[exchange.name] = exchange
        self._logger.info(f"Added testnet exchange: {exchange.name}")
    
    def get_exchange(self, name: str) -> Optional[TestnetExchange]:
        """Get exchange by name"""
        return self.exchanges.get(name)
    
    def get_default_exchange(self) -> Optional[TestnetExchange]:
        """Get default exchange (first one added)"""
        if self.exchanges:
            return list(self.exchanges.values())[0]
        return None
    
    async def get_all_balances(self) -> Dict[str, Dict[str, float]]:
        """Get balances from all exchanges"""
        balances = {}
        for name, exchange in self.exchanges.items():
            balances[name] = {
                "total_quote_value": sum(exchange.paper_balance.values()),
                "positions": await exchange.get_positions(),
            }
        return balances
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all exchanges"""
        health = {}
        for name, exchange in self.exchanges.items():
            try:
                await exchange.get_ticker("BTC/USDT")
                health[name] = True
            except Exception as e:
                self._logger.error(f"Health check failed for {name}: {e}")
                health[name] = False
        return health


def create_testnet_exchanges(
    balance: Optional[Dict[str, float]] = None,
    enable_binance: bool = True,
    enable_coinbase: bool = True,
) -> TestnetExchangeManager:
    """Create configured testnet exchanges"""
    manager = TestnetExchangeManager()
    
    if enable_binance:
        binance = BinanceTestnetAdapter(paper_balance=balance)
        manager.add_exchange(binance)
    
    if enable_coinbase:
        coinbase = CoinbaseSandboxAdapter(paper_balance=balance)
        manager.add_exchange(coinbase)
    
    return manager


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    async def test_exchanges():
        manager = create_testnet_exchanges()
        
        exchange = manager.get_default_exchange()
        if exchange:
            ticker = await exchange.get_ticker("BTC/USDT")
            print(f"Ticker: {ticker}")
            
            balance = await exchange.get_balance("BTC/USDT")
            print(f"Balance: {balance}")
            
            order = await exchange.create_order(
                "MARKET", "BTC/USDT", "BUY", 0.1
            )
            print(f"Order: {order}")
            
            positions = await exchange.get_positions()
            print(f"Positions: {positions}")
    
    asyncio.run(test_exchanges())
