"""
Enhanced Belief State Estimation with Multi-Timeframe Features
Advanced feature computation for profitable trading strategy

Extends the base BeliefState with:
- Multi-timeframe momentum (1m, 5m, 15m, 1h)
- Enhanced volatility modeling (realized, implied, regime-adjusted)
- Volume-weighted price features
- Order flow dynamics
- Advanced uncertainty decomposition
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import time
import logging

from perception.belief_state import BeliefState, BeliefStateEstimator, RegimeType

logger = logging.getLogger(__name__)


class MultiTimeframeMomentum:
    """Calculate momentum across multiple timeframes"""
    
    def __init__(self, 
                 timeframes: List[int] = [1, 5, 15, 60],  # minutes
                 decay_weights: List[float] = [0.4, 0.3, 0.2, 0.1]):
        self.timeframes = timeframes
        self.decay_weights = np.array(decay_weights) / sum(decay_weights)
        
        # Price history for each timeframe
        self.price_history = {tf: deque(maxlen=100) for tf in timeframes}
        self.volume_history = {tf: deque(maxlen=100) for tf in timeframes}
        
    def add_observation(self, price: float, volume: float, timestamp: int):
        """Add new price/volume observation"""
        # Store in all timeframes (simplified - in production would bucket by time)
        for tf in self.timeframes:
            self.price_history[tf].append(price)
            self.volume_history[tf].append(volume)
    
    def calculate_momentum(self, timeframe: int) -> float:
        """Calculate momentum for a specific timeframe"""
        history = self.price_history.get(timeframe, deque())
        
        if len(history) < 3:
            return 0.0
        
        # Simple momentum: (current - n periods ago) / n periods ago
        n = min(5, len(history) - 1)
        if n > 0:
            momentum = (history[-1] - history[-n-1]) / history[-n-1] if history[-n-1] > 0 else 0.0
        else:
            momentum = 0.0
            
        return momentum
    
    def calculate_composite_momentum(self) -> Tuple[float, float, float]:
        """Calculate weighted composite momentum across timeframes
        
        Returns:
            Tuple of (composite_momentum, short_term, long_term)
        """
        if not self.price_history or len(list(self.price_history.values())[0]) < 3:
            return 0.0, 0.0, 0.0
        
        # Calculate momentum for each timeframe
        momenta = []
        for tf in self.timeframes:
            mom = self.calculate_momentum(tf)
            momenta.append(mom)
        
        momenta = np.array(momenta)
        
        # Weighted composite
        composite = np.dot(momenta, self.decay_weights)
        
        # Short-term (first 2 timeframes)
        short_term = np.mean(momenta[:2]) if len(momenta) >= 2 else momenta[0]
        
        # Long-term (last 2 timeframes)
        long_term = np.mean(momenta[2:]) if len(momenta) >= 4 else momenta[-1]
        
        return composite, short_term, long_term


class EnhancedVolatilityModel:
    """Enhanced volatility modeling with realized, implied, and regime-adjusted components"""
    
    def __init__(self, 
                 lookback_periods: int = 20,
                 ewma_span: int = 10):
        self.lookback_periods = lookback_periods
        self.ewma_span = ewma_span
        
        self.price_history = deque(maxlen=lookback_periods * 2)
        self.returns_history = deque(maxlen=lookback_periods * 2)
        
        # EWMA volatility
        self.ewma_volatility = None
        self.ewma_alpha = 2.0 / (ewma_span + 1)
        
    def add_observation(self, price: float):
        """Add new price observation"""
        self.price_history.append(price)
        
        # Calculate return
        if len(self.price_history) >= 2:
            ret = (price - self.price_history[-2]) / self.price_history[-2] if self.price_history[-2] > 0 else 0.0
            self.returns_history.append(ret)
    
    def calculate_realized_volatility(self) -> float:
        """Calculate realized volatility (rolling standard deviation of returns)"""
        if len(self.returns_history) < 5:
            return 0.15  # Default assumption
        
        returns = np.array(list(self.returns_history))
        return np.std(returns) if len(returns) > 0 else 0.15
    
    def calculate_ewma_volatility(self) -> float:
        """Calculate exponentially-weighted moving average volatility"""
        if len(self.returns_history) < 2:
            return 0.15
        
        returns = np.array(list(self.returns_history))
        
        if self.ewma_volatility is None:
            # Initialize with realized volatility
            self.ewma_volatility = self.calculate_realized_volatility()
            return self.ewma_volatility
        
        # Latest return
        latest_return = returns[-1]
        
        # Update EWMA
        self.ewma_volatility = np.sqrt(
            self.ewma_alpha * latest_return**2 + 
            (1 - self.ewma_alpha) * self.ewma_volatility**2
        )
        
        return self.ewma_volatility
    
    def calculate_regime_adjusted_volatility(self, regime: RegimeType) -> float:
        """Calculate regime-adjusted volatility"""
        base_vol = self.calculate_ewma_volatility()
        
        # Regime multipliers
        regime_multipliers = {
            RegimeType.BULL_LOW_VOL: 0.8,
            RegimeType.BULL_HIGH_VOL: 1.3,
            RegimeType.BEAR_LOW_VOL: 0.9,
            RegimeType.BEAR_HIGH_VOL: 1.5,
            RegimeType.SIDEWAYS_LOW_VOL: 0.6,
            RegimeType.SIDEWAYS_HIGH_VOL: 1.4,
            RegimeType.CRISIS: 2.0,
            RegimeType.RECOVERY: 1.1
        }
        
        multiplier = regime_multipliers.get(regime, 1.0)
        return base_vol * multiplier
    
    def calculate_volatility_regime(self) -> str:
        """Determine volatility regime"""
        if len(self.returns_history) < 10:
            return "unknown"
        
        current_vol = self.calculate_ewma_volatility()
        
        if current_vol < 0.02:
            return "very_low"
        elif current_vol < 0.04:
            return "low"
        elif current_vol < 0.08:
            return "medium"
        elif current_vol < 0.15:
            return "high"
        else:
            return "very_high"


class OrderFlowAnalyzer:
    """Advanced order flow analysis for microstructure"""
    
    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        
        # Order flow history
        self.bid_size_history = deque(maxlen=window_size)
        self.ask_size_history = deque(maxlen=window_size)
        self.trade_direction_history = deque(maxlen=window_size)  # +1 buy, -1 sell, 0 unknown
        
        # Cumulative OFI
        self.cumulative_ofi = 0.0
        self.ofi_history = deque(maxlen=window_size)
        
    def update(self, 
               bid_size: float, 
               ask_size: float, 
               last_size: float = 0,
               trade_side: str = "unknown"):
        """Update with new market data"""
        self.bid_size_history.append(bid_size)
        self.ask_size_history.append(ask_size)
        
        # Calculate instantaneous OFI
        total = bid_size + ask_size
        if total > 0:
            ofi = (bid_size - ask_size) / total
        else:
            ofi = 0.0
        
        self.ofi_history.append(ofi)
        self.cumulative_ofi += ofi
        
        # Track trade direction
        if trade_side in ["buy", "BUY"]:
            self.trade_direction_history.append(1)
        elif trade_side in ["sell", "SELL"]:
            self.trade_direction_history.append(-1)
        else:
            self.trade_direction_history.append(0)
    
    def calculate_ofi(self) -> float:
        """Get current OFI"""
        if not self.ofi_history:
            return 0.0
        return self.ofi_history[-1]
    
    def calculate_cumulative_ofi(self) -> float:
        """Get cumulative OFI (decaying)"""
        if len(self.ofi_history) < 3:
            return self.cumulative_ofi
        
        # Apply decay to older OFI
        weights = np.exp(-np.arange(len(self.ofi_history)) * 0.1)
        weighted_ofi = np.array(list(self.ofi_history)) * weights
        return np.sum(weighted_ofi)
    
    def calculate_ofi_momentum(self) -> float:
        """Calculate OFI momentum (rate of change)"""
        if len(self.ofi_history) < 5:
            return 0.0
        
        recent = np.mean(list(self.ofi_history)[-3:])
        older = np.mean(list(self.ofi_history)[-5:-3])
        
        return recent - older
    
    def calculate_order_imbalance_strength(self) -> float:
        """Calculate strength of order imbalance (confirms direction)"""
        if not self.ofi_history:
            return 0.0
        
        # Check if OFI has been consistent in direction
        recent_ofi = list(self.ofi_history)[-5:]
        
        if not recent_ofi:
            return 0.0
            
        # Count direction consistency
        signs = np.sign(recent_ofi)
        positive_count = np.sum(signs > 0)
        negative_count = np.sum(signs < 0)
        
        consistency = max(positive_count, negative_count) / len(signs)
        
        # Magnitude
        magnitude = np.mean(np.abs(recent_ofi))
        
        return consistency * magnitude


@dataclass
class EnhancedBeliefState(BeliefState):
    """
    Enhanced belief state with additional features for profitable strategy
    """
    # Additional features
    momentum_1m: float = 0.0       # 1-minute momentum
    momentum_5m: float = 0.0       # 5-minute momentum
    momentum_15m: float = 0.0      # 15-minute momentum
    momentum_composite: float = 0.0  # Weighted composite
    
    realized_volatility: float = 0.0    # Realized volatility
    ewma_volatility: float = 0.0        # EWMA volatility
    volatility_regime: str = "unknown"   # Current volatility regime
    
    cumulative_ofi: float = 0.0         # Cumulative order flow
    ofi_momentum: float = 0.0           # OFI rate of change
    order_imbalance_strength: float = 0.0  # Direction consistency
    
    volume_weighted_price: float = 0.0  # VWAP
    twap_deviation: float = 0.0          # Price deviation from TWAP
    
    # Feature quality indicators
    data_quality_score: float = 1.0      # How reliable is the data
    feature_availability: Dict[str, bool] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary including enhanced features"""
        base_dict = super().to_dict()
        
        # Add enhanced features
        base_dict.update({
            "momentum_1m": self.momentum_1m,
            "momentum_5m": self.momentum_5m,
            "momentum_15m": self.momentum_15m,
            "momentum_composite": self.momentum_composite,
            "realized_volatility": self.realized_volatility,
            "ewma_volatility": self.ewma_volatility,
            "volatility_regime": self.volatility_regime,
            "cumulative_ofi": self.cumulative_ofi,
            "ofi_momentum": self.ofi_momentum,
            "order_imbalance_strength": self.order_imbalance_strength,
            "volume_weighted_price": self.volume_weighted_price,
            "twap_deviation": self.twap_deviation,
            "data_quality_score": self.data_quality_score,
            "feature_availability": self.feature_availability
        })
        
        return base_dict


class EnhancedBeliefStateEstimator(BeliefStateEstimator):
    """
    Enhanced belief state estimator with multi-timeframe features
    """
    
    def __init__(self, n_regimes: int = 8):
        super().__init__(n_regimes)
        
        # Initialize enhanced components
        self.momentum_analyzer = MultiTimeframeMomentum()
        self.volatility_model = EnhancedVolatilityModel()
        self.order_flow_analyzer = OrderFlowAnalyzer()
        
        # Price history for VWAP and TWAP
        self.price_volume_history = deque(maxlen=100)
        
    def update(self, 
               market_data: Dict,
               prior_belief: Optional[BeliefState] = None) -> EnhancedBeliefState:
        """
        Update belief state with enhanced features
        """
        # First, run base feature extraction
        base_belief = super().update(market_data, prior_belief)
        
        # Extract market data
        last_price = market_data.get("last_price", 0.0)
        volume = market_data.get("last_size", 1.0)
        bid_price = market_data.get("bid_price", 0.0)
        ask_price = market_data.get("ask_price", 0.0)
        bid_size = market_data.get("bid_size", 0.0)
        ask_size = market_data.get("ask_size", 0.0)
        
        # Update enhanced analyzers
        self.momentum_analyzer.add_observation(last_price, volume, int(time.time() * 1e9))
        self.volatility_model.add_observation(last_price)
        self.order_flow_analyzer.update(bid_size, ask_size, volume)
        
        # Store price-volume for VWAP
        if last_price > 0:
            self.price_volume_history.append((last_price, volume))
        
        # Calculate enhanced features
        momentum_composite, momentum_1m, momentum_5m = self.momentum_analyzer.calculate_composite_momentum()
        
        # Determine timeframe momentum based on window
        if len(self.momentum_analyzer.price_history.get(1, [])) > 0:
            momentum_1m = self.momentum_analyzer.calculate_momentum(1)
        if len(self.momentum_analyzer.price_history.get(5, [])) > 0:
            momentum_5m = self.momentum_analyzer.calculate_momentum(5)
        if len(self.momentum_analyzer.price_history.get(15, [])) > 0:
            momentum_15m = self.momentum_analyzer.calculate_momentum(15)
        
        # Volatility features
        realized_vol = self.volatility_model.calculate_realized_volatility()
        ewma_vol = self.volatility_model.calculate_ewma_volatility()
        volatility_reg = self.volatility_model.calculate_volatility_regime()
        
        # Order flow features
        cumulative_ofi = self.order_flow_analyzer.calculate_cumulative_ofi()
        ofi_momentum = self.order_flow_analyzer.calculate_ofi_momentum()
        imbalance_strength = self.order_flow_analyzer.calculate_order_imbalance_strength()
        
        # VWAP and TWAP deviation
        vwap = 0.0
        twap_dev = 0.0
        if self.price_volume_history:
            total_pv = sum(p * v for p, v in self.price_volume_history)
            total_v = sum(v for p, v in self.price_volume_history)
            vwap = total_pv / total_v if total_v > 0 else last_price
            
            # TWAP (simple average)
            prices = [p for p, v in self.price_volume_history]
            twap = np.mean(prices) if prices else last_price
            
            twap_dev = (last_price - twap) / twap if twap > 0 else 0.0
        
        # Calculate data quality
        data_quality = self._assess_data_quality(market_data)
        
        # Feature availability
        feature_availability = {
            "momentum": len(self.momentum_analyzer.price_history.get(1, [])) >= 3,
            "volatility": len(self.volatility_model.returns_history) >= 10,
            "order_flow": len(self.order_flow_analyzer.ofi_history) >= 3,
            "vwap": len(self.price_volume_history) >= 5
        }
        
        # Create enhanced belief state
        enhanced = EnhancedBeliefState(
            # Base fields from parent
            expected_return=base_belief.expected_return,
            expected_return_uncertainty=base_belief.expected_return_uncertainty,
            aleatoric_uncertainty=base_belief.aleatoric_uncertainty,
            epistemic_uncertainty=base_belief.epistemic_uncertainty,
            regime_probabilities=base_belief.regime_probabilities,
            microstructure_features=base_belief.microstructure_features,
            volatility_estimate=base_belief.volatility_estimate,
            liquidity_estimate=base_belief.liquidity_estimate,
            momentum_signal=momentum_composite,
            volume_signal=base_belief.volume_signal,
            timestamp=base_belief.timestamp,
            confidence=base_belief.confidence,
            
            # Enhanced features
            momentum_1m=momentum_1m,
            momentum_5m=momentum_5m,
            momentum_15m=momentum_15m,
            momentum_composite=momentum_composite,
            realized_volatility=realized_vol,
            ewma_volatility=ewma_vol,
            volatility_regime=volatility_reg,
            cumulative_ofi=cumulative_ofi,
            ofi_momentum=ofi_momentum,
            order_imbalance_strength=imbalance_strength,
            volume_weighted_price=vwap,
            twap_deviation=twap_dev,
            data_quality_score=data_quality,
            feature_availability=feature_availability
        )
        
        return enhanced
    
    def _assess_data_quality(self, market_data: Dict) -> float:
        """Assess quality of market data"""
        score = 1.0
        
        # Check required fields
        required = ["bid_price", "ask_price", "last_price"]
        missing = sum(1 for f in required if not market_data.get(f, 0) > 0)
        score -= missing * 0.15
        
        # Check spread sanity
        bid = market_data.get("bid_price", 0)
        ask = market_data.get("ask_price", 0)
        if ask > 0 and bid > 0:
            spread_pct = (ask - bid) / ((ask + bid) / 2)
            if spread_pct > 0.05:  # > 5% spread is suspicious
                score -= 0.3
            elif spread_pct < 0:  # Negative spread is invalid
                score -= 0.5
        
        # Check for stale data (would need timestamp comparison in production)
        
        return max(0.0, min(1.0, score))
    
    def calculate_enhanced_expected_return(
        self, 
        belief_state: EnhancedBeliefState,
        weights: np.ndarray = None
    ) -> float:
        """
        Calculate enhanced expected return using multi-factor model
        
        Args:
            belief_state: Enhanced belief state
            weights: Feature weights (if None, uses default)
            
        Returns:
            Expected return estimate
        """
        if weights is None:
            # Default weights for feature contribution
            weights = np.array([
                0.10,  # ofI
                0.15,  # I_star
                0.08,  # S_star
                0.07,  # L_star
                0.05,  # depth_imbalance
                0.05,  # volume_imbalance
                0.15,  # momentum
                0.05,  # volatility (negative contribution)
                0.10,  # cumulative_ofi
                0.10,  # ofi_momentum
                0.10,  # momentum_composite
            ])
        
        features = belief_state.microstructure_features
        
        # Extract feature values
        feature_values = np.array([
            features.get("ofI", 0),
            features.get("I_star", 0),
            features.get("S_star", 0),
            features.get("L_star", 0),
            features.get("depth_imbalance", 0),
            features.get("volume_imbalance", 0),
            features.get("price_momentum", 0),
            -features.get("volatility_estimate", 0),  # Negative contribution
            belief_state.cumulative_ofi * 0.1,  # Scale cumulative OFI
            belief_state.ofi_momentum,
            belief_state.momentum_composite,
        ])
        
        # Calculate expected return
        expected_return = np.dot(weights, feature_values)
        
        # Apply confidence adjustment
        expected_return *= belief_state.confidence
        
        # Apply data quality penalty
        expected_return *= belief_state.data_quality_score
        
        return expected_return


# Example usage
if __name__ == "__main__":
    # Create enhanced estimator
    estimator = EnhancedBeliefStateEstimator()
    
    # Simulate market data
    market_data = {
        "bid_price": 50000.0,
        "ask_price": 50010.0,
        "bid_size": 100.0,
        "ask_size": 80.0,
        "last_price": 50005.0,
        "last_size": 1.5
    }
    
    # Add some historical data
    for i in range(30):
        price = 50000 + np.random.randn() * 100
        volume = np.random.uniform(0.5, 2.0)
        estimator.momentum_analyzer.add_observation(price, volume, int(time.time() * 1e9))
        estimator.volatility_model.add_observation(price)
    
    # Update belief state
    enhanced_belief = estimator.update(market_data)
    
    print("Enhanced Belief State:")
    print(f"  Expected Return: {enhanced_belief.expected_return:.5f}")
    print(f"  Confidence: {enhanced_belief.confidence:.4f}")
    print(f"  Momentum (1m): {enhanced_belief.momentum_1m:.5f}")
    print(f"  Momentum (5m): {enhanced_belief.momentum_5m:.5f}")
    print(f"  Momentum Composite: {enhanced_belief.momentum_composite:.5f}")
    print(f"  EWMA Volatility: {enhanced_belief.ewma_volatility:.5f}")
    print(f"  Volatility Regime: {enhanced_belief.volatility_regime}")
    print(f"  Cumulative OFI: {enhanced_belief.cumulative_ofi:.5f}")
    print(f"  Data Quality: {enhanced_belief.data_quality_score:.2f}")