"""
Market Data Feed Factory for the Unified Trading System
Provides convenient methods for creating market data feed instances
"""

from typing import Optional
from .market_data_feed import MarketDataFeed, SimulatedMarketDataFeed, ExchangeMarketDataFeed, FeedType


class MarketDataFeedFactory:
    """
    Factory for creating market data feed instances
    """
    
    @staticmethod
    def create_feed(feed_type: str, symbol: str, **kwargs) -> MarketDataFeed:
        """
        Create a market data feed instance
        
        Args:
            feed_type: Type of feed to create ('simulated' or exchange name like 'binance')
            symbol: Trading symbol (e.g., 'BTCUSDT')
            **kwargs: Additional arguments specific to the feed type
            
        Returns:
            MarketDataFeed instance
        """
        feed_type_lower = feed_type.lower()
        
        if feed_type_lower == 'simulated':
            base_price = kwargs.get('base_price', 50000.0)
            volatility = kwargs.get('volatility', 0.2)
            return SimulatedMarketDataFeed(symbol, base_price, volatility)
        
        # For real exchanges, return the template implementation
        # In a full implementation, you would have specific classes for each exchange
        elif feed_type_lower in ['binance', 'coinbase', 'kraken', 'bybit', 'okx']:
            api_key = kwargs.get('api_key')
            api_secret = kwargs.get('api_secret')
            return ExchangeMarketDataFeed(symbol, feed_type_lower.capitalize(), api_key, api_secret)
        
        else:
            raise ValueError(f"Unsupported feed type: {feed_type}. "
                           f"Supported types: 'simulated', 'binance', 'coinbase', 'kraken', 'bybit', 'okx'")
    
    @staticmethod
    def create_multiple_feeds(symbols: list[str], feed_type: str = 'simulated', **kwargs) -> dict[str, MarketDataFeed]:
        """
        Create multiple market data feeds for different symbols
        
        Args:
            symbols: List of trading symbols
            feed_type: Type of feed to create for all symbols
            **kwargs: Additional arguments for feed creation
            
        Returns:
            Dictionary mapping symbol to MarketDataFeed instance
        """
        feeds = {}
        for symbol in symbols:
            feeds[symbol] = MarketDataFeedFactory.create_feed(feed_type, symbol, **kwargs)
        return feeds


# Convenience functions
def create_simulated_feed(symbol: str, base_price: float = 50000.0, volatility: float = 0.2) -> MarketDataFeed:
    """Create a simulated market data feed"""
    return MarketDataFeedFactory.create_feed('simulated', symbol, base_price=base_price, volatility=volatility)


def create_exchange_feed(symbol: str, exchange: str, api_key: str = None, api_secret: str = None) -> MarketDataFeed:
    """Create an exchange market data feed"""
    return MarketDataFeedFactory.create_feed(exchange, symbol, api_key=api_key, api_secret=api_secret)