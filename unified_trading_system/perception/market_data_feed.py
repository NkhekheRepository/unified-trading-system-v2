"""
Market Data Feed Abstraction for the Unified Trading System
Provides a standardized interface for connecting to real market data sources
"""

import abc
import time
from typing import Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class FeedType(Enum):
    """Types of market data feeds"""
    TICKER = "TICKER"
    ORDER_BOOK = "ORDER_BOOK"
    TRADES = "TRADES"
    CANDLES = "CANDLES"


@dataclass
class MarketDataUpdate:
    """Standardized market data update"""
    timestamp: int  # Nanoseconds since epoch
    symbol: str
    feed_type: FeedType
    data: Dict
    source: str  # Exchange or data provider name


class MarketDataFeed(abc.ABC):
    """
    Abstract base class for market data feeds
    Defines the interface for connecting to real market data sources
    """
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.is_connected = False
        self.last_update_time = 0
        self.update_callback: Optional[Callable[[MarketDataUpdate], None]] = None
        self._subscribed_feeds = set()
    
    @abc.abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the market data source
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def disconnect(self) -> None:
        """Close connection to the market data source"""
        pass
    
    @abc.abstractmethod
    def subscribe(self, feed_types: list[FeedType]) -> bool:
        """
        Subscribe to specific types of market data
        
        Args:
            feed_types: List of FeedType enums to subscribe to
            
        Returns:
            bool: True if subscription successful, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def unsubscribe(self, feed_types: list[FeedType]) -> None:
        """
        Unsubscribe from specific types of market data
        
        Args:
            feed_types: List of FeedType enums to unsubscribe from
        """
        pass
    
    def set_update_callback(self, callback: Callable[[MarketDataUpdate], None]) -> None:
        """
        Set callback function to be called when new market data arrives
        
        Args:
            callback: Function that takes a MarketDataUpdate parameter
        """
        self.update_callback = callback
    
    def _emit_update(self, feed_type: FeedType, data: Dict) -> None:
        """
        Emit a market data update to the callback function
        
        Args:
            feed_type: Type of feed the data came from
            data: The market data dictionary
        """
        if self.update_callback:
            update = MarketDataUpdate(
                timestamp=time.time_ns(),
                symbol=self.symbol,
                feed_type=feed_type,
                data=data,
                source=self.__class__.__name__
            )
            self.update_callback(update)
    
    def is_healthy(self) -> bool:
        """
        Check if the feed is healthy and providing timely data
        
        Returns:
            bool: True if feed is healthy
        """
        if not self.is_connected:
            return False
            
        # Consider feed unhealthy if no updates in last 30 seconds
        time_since_update = time.time_ns() - self.last_update_time
        return time_since_update < 30_000_000_000  # 30 seconds in nanoseconds


class SimulatedMarketDataFeed(MarketDataFeed):
    """
    Simulated market data feed for testing and development
    Generates realistic-looking market data for system validation
    """
    
    def __init__(self, symbol: str, base_price: float = 50000.0, volatility: float = 0.2):
        super().__init__(symbol)
        self.base_price = base_price
        self.volatility = volatility
        self.price = base_price
        self.trade_count = 0
        
    def connect(self) -> bool:
        """Simulate connecting to a market data feed"""
        self.is_connected = True
        self.last_update_time = time.time_ns()
        return True
    
    def disconnect(self) -> None:
        """Simulate disconnecting from a market data feed"""
        self.is_connected = False
    
    def subscribe(self, feed_types: list[FeedType]) -> bool:
        """Simulate subscribing to market data feeds"""
        self._subscribed_feeds.update(feed_types)
        self.last_update_time = time.time_ns()
        return True
    
    def unsubscribe(self, feed_types: list[FeedType]) -> None:
        """Simulate unsubscribing from market data feeds"""
        self._subscribed_feeds.difference_update(feed_types)
    
    def update_simulation(self) -> None:
        """Update the simulated market data (would be called by external timer)"""
        if not self.is_connected:
            return
            
        # Simulate price movement with geometric Brownian motion
        dt = 1.0  # 1 second time step
        drift = 0.0  # No drift for simplicity
        diffusion = self.volatility * np.sqrt(dt)
        
        # Generate random price change
        price_change = np.random.normal(drift * dt, diffusion)
        self.price *= np.exp(price_change)
        
        # Ensure price stays reasonable
        self.price = max(self.price, 0.01)
        
        # Generate market data update
        spread_bps = max(0.1, np.random.normal(2.0, 0.5))  # Normally around 2 bps
        spread = self.price * spread_bps / 10000
        
        # Order book data
        order_book_data = {
            "bid_price": self.price - spread/2,
            "ask_price": self.price + spread/2,
            "bid_size": np.random.uniform(0.5, 5.0),
            "ask_size": np.random.uniform(0.5, 5.0),
            "last_price": self.price,
            "last_size": np.random.uniform(0.1, 2.0),
            "volume": self.trade_count * np.random.uniform(0.5, 2.0)
        }
        
        # Emit ticker update
        self._emit_update(FeedType.TICKER, {
            "price": self.price,
            "bid_price": order_book_data["bid_price"],
            "ask_price": order_book_data["ask_price"],
            "bid_size": order_book_data["bid_size"],
            "ask_size": order_book_data["ask_size"],
            "last_price": order_book_data["last_price"],
            "last_size": order_book_data["last_size"],
            "volume": order_book_data["volume"],
            "timestamp": time.time_ns()
        })
        
        # Emit order book data
        self._emit_update(FeedType.ORDER_BOOK, order_book_data)
        
        # Emit trade data (occasional trades)
        if np.random.random() < 0.3:  # 30% chance of trade per update
            trade_data = {
                "price": self.price * (1 + np.random.normal(0, 0.0001)),  # Small price variation
                "size": np.random.uniform(0.1, 3.0),
                "side": "BUY" if np.random.random() > 0.5 else "SELL",
                "timestamp": time.time_ns(),
                "trade_id": f"sim_{self.trade_count}"
            }
            self._emit_update(FeedType.TRADES, trade_data)
            self.trade_count += 1
            
        self.last_update_time = time.time_ns()


# Example concrete implementation for a real exchange (template)
class ExchangeMarketDataFeed(MarketDataFeed):
    """
    Template for real exchange market data feeds
    To implement a real exchange, inherit from this class and implement the abstract methods
    """
    
    def __init__(self, symbol: str, exchange_name: str, api_key: str = None, api_secret: str = None):
        super().__init__(symbol)
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.api_secret = api_secret
        # In a real implementation, you would initialize the exchange client here
        # e.g., self.client = ccxt.exchange_name({'apiKey': api_key, 'secret': api_secret})
    
    def connect(self) -> bool:
        """
        Connect to the exchange
        In a real implementation, this would:
        1. Validate API credentials
        2. Establish WebSocket connections
        3. Perform initial REST calls for snapshot data
        4. Set up heartbeat/reconnection mechanisms
        """
        # Placeholder implementation
        try:
            # In reality: self._setup_websocket_connections()
            # In reality: self._fetch_initial_snapshot()
            self.is_connected = True
            self.last_update_time = time.time_ns()
            return True
        except Exception as e:
            print(f"Failed to connect to {self.exchange_name}: {e}")
            return False
    
    def disconnect(self) -> None:
        """
        Disconnect from the exchange
        In a real implementation, this would:
        1. Close WebSocket connections
        2. Clean up resources
        """
        # Placeholder implementation
        self.is_connected = False
        # In reality: self._close_websocket_connections()
    
    def subscribe(self, feed_types: list[FeedType]) -> bool:
        """
        Subscribe to market data feeds from the exchange
        In a real implementation, this would:
        1. Send subscription messages over WebSocket
        2. Handle subscription confirmations
        3. Subscribe to appropriate channels for each feed type
        """
        if not self.is_connected:
            if not self.connect():
                return False
                
        # Placeholder implementation
        self._subscribed_feeds.update(feed_types)
        self.last_update_time = time.time_ns()
        return True
    
    def unsubscribe(self, feed_types: list[FeedType]) -> None:
        """
        Unsubscribe from market data feeds
        In a real implementation, this would send unsubscription messages
        """
        self._subscribed_feeds.difference_update(feed_types)
        # In reality: self._send_unsubscribe_messages(feed_types)