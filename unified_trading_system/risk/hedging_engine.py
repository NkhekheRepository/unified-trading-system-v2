import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HedgingEngine:
    """Active delta hedging engine to neutralize portfolio risk using correlated assets"""
    
    def __init__(self, config_path: str = "/home/nkhekhe/unified_trading_system/config/hedging_config.yaml"):
        self.positions = {}  # symbol -> {quantity, side, delta, entry_price}
        self.correlation_matrix = {}
        self.delta_threshold = 0.5  # Max allowed net delta before hedging
        self.hedge_positions = {}  # symbol -> hedge position details
        self.correlation_window = 30  # Days for correlation calculation
        
    def update_position(self, symbol: str, quantity: float, side: str, price: float):
        """Update position tracking"""
        delta = quantity if side == "BUY" else -quantity
        self.positions[symbol] = {
            "quantity": quantity,
            "side": side,
            "delta": delta,
            "entry_price": price,
            "timestamp": datetime.now().isoformat()
        }
        logger.info(f"Updated position for {symbol}: {side} {quantity} @ {price}")
        
    def calculate_portfolio_delta(self) -> float:
        """Calculate net portfolio delta"""
        total_delta = sum(pos["delta"] for pos in self.positions.values())
        logger.debug(f"Portfolio delta: {total_delta:.2f}")
        return total_delta
    
    def update_correlation_matrix(self, symbols: List[str]):
        """Update correlation matrix for traded symbols (simplified version)"""
        # In production, this would fetch historical prices and calculate Pearson correlations
        # For now, use predefined correlations for major pairs
        predefined_correlations = {
            "BTCUSDT": {"ETHUSDT": 0.85, "BNBUSDT": 0.65, "SOLUSDT": 0.70},
            "ETHUSDT": {"BTCUSDT": 0.85, "BNBUSDT": 0.60, "SOLUSDT": 0.75},
            "SOLUSDT": {"BTCUSDT": 0.70, "ETHUSDT": 0.75, "BNBUSDT": 0.55}
        }
        
        for sym in symbols:
            if sym not in self.correlation_matrix:
                self.correlation_matrix[sym] = predefined_correlations.get(sym, {})
        logger.debug(f"Updated correlation matrix for {len(symbols)} symbols")
    
    def find_hedge_candidate(self, portfolio_delta: float) -> Optional[Tuple[str, str, float]]:
        """Find best asset to hedge portfolio delta"""
        if abs(portfolio_delta) <= self.delta_threshold:
            return None
            
        # Determine hedge direction (opposite of portfolio delta)
        hedge_side = "SELL" if portfolio_delta > 0 else "BUY"
        
        # Find most correlated asset not already in portfolio
        candidates = []
        for sym, pos in self.positions.items():
            correlations = self.correlation_matrix.get(sym, {})
            for asset, corr in correlations.items():
                if asset not in self.positions:  # Don't hedge with existing positions
                    candidates.append((asset, corr, sym))
        
        if not candidates:
            return None
            
        # Select asset with highest correlation
        best_candidate = max(candidates, key=lambda x: x[1])
        asset, corr, original_sym = best_candidate
        
        # Calculate hedge quantity based on correlation and portfolio delta
        hedge_quantity = abs(portfolio_delta) * corr
        return (asset, hedge_side, hedge_quantity)
    
    def execute_hedge(self, portfolio_delta: float) -> Optional[Dict]:
        """Execute hedging trade if needed"""
        hedge_details = self.find_hedge_candidate(portfolio_delta)
        if not hedge_details:
            return None
            
        asset, side, quantity = hedge_details
        hedge_trade = {
            "symbol": asset,
            "side": side,
            "quantity": quantity,
            "reason": f"Hedge against portfolio delta {portfolio_delta:.2f}",
            "timestamp": datetime.now().isoformat()
        }
        
        # Track hedge position
        self.hedge_positions[asset] = hedge_trade
        logger.info(f"Executing hedge: {side} {quantity:.2f} {asset}")
        return hedge_trade
    
    def unwind_hedges(self, symbol: str = None):
        """Unwind hedge positions when original position closes or delta changes"""
        if symbol and symbol in self.hedge_positions:
            hedge = self.hedge_positions.pop(symbol)
            logger.info(f"Unwinding hedge for {symbol}: {hedge}")
            return hedge
        elif not symbol:
            # Unwind all hedges
            unwound = []
            for sym, hedge in list(self.hedge_positions.items()):
                unwound.append(hedge)
                del self.hedge_positions[sym]
            return unwound if unwound else None
        return None
    
    def evaluate_hedging_need(self) -> Dict:
        """Evaluate if hedging is needed and return action plan"""
        portfolio_delta = self.calculate_portfolio_delta()
        needs_hedge = abs(portfolio_delta) > self.delta_threshold
        
        evaluation = {
            "timestamp": datetime.now().isoformat(),
            "portfolio_delta": round(portfolio_delta, 4),
            "needs_hedge": needs_hedge,
            "delta_threshold": self.delta_threshold,
            "hedge_action": None
        }
        
        if needs_hedge:
            hedge = self.execute_hedge(portfolio_delta)
            if hedge:
                evaluation["hedge_action"] = hedge
                
        return evaluation

if __name__ == "__main__":
    engine = HedgingEngine()
    engine.update_position("BTCUSDT", 1.0, "BUY", 50000.0)
    engine.update_correlation_matrix(["BTCUSDT", "ETHUSDT"])
    evaluation = engine.evaluate_hedging_need()
    print(json.dumps(evaluation, indent=2))
