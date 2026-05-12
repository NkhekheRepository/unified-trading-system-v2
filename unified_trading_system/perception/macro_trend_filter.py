import requests
import numpy as np
from datetime import datetime
from typing import Dict, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MacroTrendFilter:
    """Filters micro-signals using higher timeframe trend analysis (1H, 4H, 1D)"""
    
    def __init__(self, symbol: str = "BTCUSDT", timeframes: list = ["1h", "4h", "1d"]):
        self.symbol = symbol
        self.timeframes = timeframes
        self.api_base = "https://testnet.binancefuture.com/fapi/v1/klines"
        
    def fetch_klines(self, timeframe: str, limit: int = 200) -> list:
        """Fetch kline data from Binance for specified timeframe"""
        try:
            params = {
                "symbol": self.symbol,
                "interval": timeframe,
                "limit": limit
            }
            resp = requests.get(self.api_base, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch {timeframe} klines: {e}")
            return []
    
    def calculate_ema(self, prices: list, period: int) -> float:
        """Calculate EMA for given price list"""
        if len(prices) < period:
            return prices[-1] if prices else 0.0
        ema = prices[0]
        multiplier = 2 / (period + 1)
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        return ema
    
    def detect_market_structure(self, klines: list) -> str:
        """Detect market structure (higher highs/lows for bullish, lower for bearish)"""
        if len(klines) < 20:
            return "NEUTRAL"
        
        closes = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        
        # Check last 10 candles for structure
        recent_highs = highs[-10:]
        recent_lows = lows[-10:]
        
        # Bullish: Higher highs and higher lows
        if (recent_highs[-1] > recent_highs[0] and recent_lows[-1] > recent_lows[0]):
            return "BULLISH"
        # Bearish: Lower highs and lower lows
        elif (recent_highs[-1] < recent_highs[0] and recent_lows[-1] < recent_lows[0]):
            return "BEARISH"
        return "NEUTRAL"
    
    def get_timeframe_trend(self, timeframe: str) -> str:
        """Get trend for single timeframe"""
        klines = self.fetch_klines(timeframe)
        if not klines:
            return "NEUTRAL"
        
        closes = [float(k[4]) for k in klines]
        current_price = closes[-1]
        
        # EMA Trend (EMA50 > EMA200 = Bullish)
        ema50 = self.calculate_ema(closes, 50)
        ema200 = self.calculate_ema(closes, 200)
        ema_trend = "BULLISH" if ema50 > ema200 else "BEARISH"
        
        # Market Structure Trend
        structure_trend = self.detect_market_structure(klines)
        
        # Consensus
        if ema_trend == structure_trend and ema_trend != "NEUTRAL":
            return ema_trend
        return "NEUTRAL"
    
    def get_macro_trend(self) -> Tuple[str, Dict[str, str]]:
        """Get consensus macro trend across all timeframes"""
        trends = {}
        for tf in self.timeframes:
            trends[tf] = self.get_timeframe_trend(tf)
        
        # Weight higher timeframes more (1d > 4h > 1h)
        bullish_count = sum(1 for t in trends.values() if t == "BULLISH")
        bearish_count = sum(1 for t in trends.values() if t == "BEARISH")
        
        if bullish_count >= 2:  # Majority consensus
            return ("BULLISH", trends)
        elif bearish_count >= 2:
            return ("BEARISH", trends)
        return ("NEUTRAL", trends)

if __name__ == "__main__":
    filter = MacroTrendFilter()
    trend, details = filter.get_macro_trend()
    print(f"Macro Trend: {trend}")
    print(f"Details: {details}")
