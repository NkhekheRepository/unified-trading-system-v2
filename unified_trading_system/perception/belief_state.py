"""
Belief State Estimation for Unified Trading System
Combines LVR's feature engineering with Autonomous System's POMDP belief state
"""


import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import json
import time


class RegimeType(Enum):
    """Market regime types"""
    BULL_LOW_VOL = 0
    BULL_HIGH_VOL = 1
    BEAR_LOW_VOL = 2
    BEAR_HIGH_VOL = 3
    SIDEWAYS_LOW_VOL = 4
    SIDEWAYS_HIGH_VOL = 5
    CRISIS = 6
    RECOVERY = 7


@dataclass
class BeliefState:
    """
    Unified belief state combining LVR's market insights with 
    Autonomous System's POMDP formulation
    """
    # Core POMDP elements (from Autonomous System)
    expected_return: float                    # Expected asset return
    expected_return_uncertainty: float        # Uncertainty in expected return
    aleatoric_uncertainty: float              # Irreducible market uncertainty
    epistemic_uncertainty: float              # Reducible model uncertainty
    regime_probabilities: List[float]         # Probability over regime types
    
    # LVR-enhanced features
    microstructure_features: Dict[str, float] # OFI, I*, L*, S*, depth imbalance, etc.
    volatility_estimate: float                # Estimated volatility
    liquidity_estimate: float                 # Estimated market liquidity
    momentum_signal: float                    # Price momentum signal
    volume_signal: float                      # Volume-based signal
    
    # Metadata
    timestamp: int                            #nanoseconds since epoch
    confidence: float                         #Overall belief state confidence (0-1)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "expected_return": self.expected_return,
            "expected_return_uncertainty": self.expected_return_uncertainty,
            "aleatoric_uncertainty": self.aleatoric_uncertainty,
            "epistemic_uncertainty": self.epistemic_uncertainty,
            "regime_probabilities": self.regime_probabilities,
            "microstructure_features": self.microstructure_features,
            "volatility_estimate": self.volatility_estimate,
            "liquidity_estimate": self.liquidity_estimate,
            "momentum_signal": self.momentum_signal,
            "volume_signal": self.volume_signal,
            "timestamp": self.timestamp,
            "confidence": self.confidence
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BeliefState':
        """Create from dictionary"""
        return cls(
            expected_return=data["expected_return"],
            expected_return_uncertainty=data["expected_return_uncertainty"],
            aleatoric_uncertainty=data["aleatoric_uncertainty"],
            epistemic_uncertainty=data["epistemic_uncertainty"],
            regime_probabilities=data["regime_probabilities"],
            microstructure_features=data["microstructure_features"],
            volatility_estimate=data["volatility_estimate"],
            liquidity_estimate=data["liquidity_estimate"],
            momentum_signal=data["momentum_signal"],
            volume_signal=data["volume_signal"],
            timestamp=data["timestamp"],
            confidence=data["confidence"]
        )
    
    def get_most_likely_regime(self) -> Tuple[RegimeType, float]:
        """Get the most likely regime and its probability"""
        if not self.regime_probabilities:
            return RegimeType.SIDEWAYS_LOW_VOL, 0.0
        
        max_idx = np.argmax(self.regime_probabilities)
        return list(RegimeType)[max_idx], self.regime_probabilities[max_idx]
    
    def get_entropy(self) -> float:
        """Calculate entropy of regime probabilities (measure of uncertainty)"""
        # Add small epsilon to avoid log(0)
        eps = 1e-10
        probs = np.array(self.regime_probabilities) + eps
        probs = probs / np.sum(probs)  # Renormalize
        return -np.sum(probs * np.log(probs))
    
    def get_total_uncertainty(self) -> float:
        """Get total uncertainty (aleatoric + epistemic)"""
        return self.aleatoric_uncertainty + self.epistemic_uncertainty
    
    def is_confident(self, threshold: float = 0.7) -> bool:
        """Check if belief state is confident enough for trading"""
        # For trading signals, we mainly care about confidence in returns
        # Regime uncertainty is acceptable as long as we have clear signal
        return self.confidence >= threshold


class BeliefStateEstimator:
    """
    Estimates belief state by combining LVR's feature computation
    with Autonomous System's uncertainty quantification
    """
    
    def __init__(self, n_regimes: int = 8):
        self.n_regimes = n_regimes
        self.regime_transition_matrix = self._initialize_transition_matrix()
        self.feature_weights = self._initialize_feature_weights()
        
    def _initialize_transition_matrix(self) -> np.ndarray:
        """Initialize regime transition probabilities"""
        # Start with uniform transitions (would be learned in practice)
        return np.full((self.n_regimes, self.n_regimes), 1.0 / self.n_regimes)
    
    def _initialize_feature_weights(self) -> Dict[str, float]:
        """Initialize weights for different features in belief formation"""
        return {
            "ofI": 0.2,           # Order flow imbalance
            "I_star": 0.15,       # Informed trading probability
            "L_star": 0.15,       # Liquidity-driven trading
            "S_star": 0.1,        # Smarter informed trading
            "depth_imbalance": 0.1, # Order book depth imbalance
            "volume_imbalance": 0.1, # Volume imbalance
            "price_momentum": 0.1,  # Price momentum
            "volatility_estimate": 0.1 # Volatility estimate
        }
    
    def update(
        self, 
        market_data: Dict,
        prior_belief: Optional['BeliefState'] = None
    ) -> BeliefState:
        """
        Update belief state with new market data
        """
        # Step 1: Extract LVR-style microstructure features
        features = self._extract_microstructure_features(market_data)
        
        # Step 2: Compute expected return and uncertainties
        expected_return, return_uncertainty = self._compute_expected_return_and_uncertainty(features)
        
        # Step 3: Update regime probabilities using POMDP update
        regime_probabilities = self._update_regime_probabilities(features, prior_belief)
        
        # Step 4: Extract values from features
        volatility_estimate = features.get("volatility_estimate", 0.15)
        liquidity_estimate = features.get("liquidity_estimate", 0.5)
        momentum_signal = features.get("price_momentum", 0.0)
        volume_signal = features.get("volume_imbalance", 0.0)
        
        # Compute uncertainties using proper decomposition
        aleatoric_unc, epistemic_unc = self._decompose_uncertainty(features, prior_belief)
        
        # Compute confidence properly using existing method
        confidence = self._compute_confidence(
            aleatoric_unc, epistemic_unc, regime_probabilities
        )
        
        # Create and return updated belief state (convert numpy array to list for compatibility)
        return BeliefState(
            expected_return=expected_return,
            expected_return_uncertainty=return_uncertainty,
            aleatoric_uncertainty=aleatoric_unc,
            epistemic_uncertainty=epistemic_unc,
            regime_probabilities=regime_probabilities.tolist(),
            microstructure_features=features,
            volatility_estimate=volatility_estimate,
            liquidity_estimate=liquidity_estimate,
            momentum_signal=momentum_signal,
            volume_signal=volume_signal,
            timestamp=int(time.time() * 1e9),
            confidence=confidence
        )
    
    def _extract_microstructure_features(self, market_data: Dict) -> Dict[str, float]:
        """
        Extract microstructure features similar to LVR's approach
        OFI, I*, L*, S*, depth imbalance, etc.
        """
        # In a real implementation, this would process raw market data
        # For now, we'll simulate based on typical market data fields
        
        features = {}
        
        # Extract basic market data
        bid_price = market_data.get("bid_price", 0.0)
        ask_price = market_data.get("ask_price", 0.0)
        bid_size = market_data.get("bid_size", 0.0)
        ask_size = market_data.get("ask_size", 0.0)
        last_price = market_data.get("last_price", 0.0)
        last_size = market_data.get("last_size", 0.0)
        
        # Mid price
        mid_price = (bid_price + ask_price) / 2.0 if bid_price > 0 and ask_price > 0 else 0.0
        
        # Spread
        spread = ask_price - bid_price if ask_price > bid_price else 0.0
        spread_bps = (spread / mid_price * 10000) if mid_price > 0 else 0.0
        
        # Order Flow Imbalance (OFI) - normalized
        total_size = bid_size + ask_size
        if total_size > 0:
            ofi = (bid_size - ask_size) / total_size
        else:
            ofi = 0.0
        features["ofI"] = ofi
        
        # Informed Trading Probability (I*) - simplified
        # Based on price impact and order flow
        if spread > 0 and total_size > 0:
            # Simplified approximation
            price_change = abs(last_price - mid_price) if mid_price > 0 else 0.0
            I_star = min(price_change / spread, 1.0) * abs(ofi)
        else:
            I_star = 0.0
        features["I_star"] = I_star
        
        # Liquidity-driven Trading (L*) - based on depth
        # Simplified: larger sizes indicate more liquidity-driven trading
        size_ratio = min(bid_size, ask_size) / max(bid_size, ask_size) if max(bid_size, ask_size) > 0 else 0.0
        features["L_star"] = size_ratio
        
        # Smarter Informed Trading (S*) - interaction term
        features["S_star"] = ofi * I_star
        
        # Depth Imbalance
        if ask_size > 0:
            depth_imbalance = (bid_size - ask_size) / (bid_size + ask_size)
        else:
            depth_imbalance = 0.0
        features["depth_imbalance"] = depth_imbalance
        
        # Volume Imbalance (would need volume history in practice)
        features["volume_imbalance"] = 0.0  # Placeholder
        
        # Price Momentum (would need price history in practice)
        features["price_momentum"] = 0.0   # Placeholder
        
        # Volatility Estimate (simplified from spread)
        features["volatility_estimate"] = min(spread_bps / 10.0, 1.0)  # Normalize to 0-1 range
        
        return features
    
    def _compute_expected_return_and_uncertainty(
        self, features: Dict[str, float]
    ) -> Tuple[float, float]:
        """
        Compute expected return and its uncertainty from features
        Combines LVR's signal generation with uncertainty quantification
        """
        # Simple linear model for expected return (would be more sophisticated in practice)
        # OFI and I* are primary drivers of short-term returns
        expected_return = (
            0.1 * features.get("ofI", 0.0) +
            0.2 * features.get("I_star", 0.0) +
            0.05 * features.get("price_momentum", 0.0) -
            0.05 * features.get("volatility_estimate", 0.0)  # Volatility drag
        )
        
        # Uncertainty increases with volatility and decreases with liquidity/confidence
        volatility = features.get("volatility_estimate", 0.1)
        liquidity = 1.0 / (1.0 + features.get("depth_imbalance", 0.0)**2)
        base_uncertainty = 0.05 + 0.3 * volatility  # Reduced base uncertainty
        uncertainty_reduction = 0.3 * liquidity    # Increased liquidity reduction
        
        expected_return_uncertainty = max(base_uncertainty - uncertainty_reduction, 0.01)
        
        return expected_return, expected_return_uncertainty
    
    def _decompose_uncertainty(
        self, 
        features: Dict[str, float], 
        prior_belief: Optional[BeliefState]
    ) -> Tuple[float, float]:
        """
        Decompose uncertainty into aleatoric (market) and epistemic (model) components
        Based on Autonomous System's approach
        """
        # Aleatoric uncertainty: irreducible market uncertainty
        # Based on volatility and liquidity
        volatility = features.get("volatility_estimate", 0.1)
        liquidity = features.get("depth_imbalance", 0.0)
        aleatoric_uncertainty = 0.05 + 0.3 * abs(volatility) + 0.1 * abs(liquidity)
        
        # Epistemic uncertainty: reducible model uncertainty
        # Based on disagreement between methods or lack of data
        if prior_belief is None:
            # High epistemic uncertainty when no prior
            epistemic_uncertainty = 0.3
        else:
            # Lower epistemic uncertainty when we have prior beliefs
            # Would be based on model disagreement in practice
            epistemic_uncertainty = 0.1 * (1.0 - prior_belief.confidence)
        
        return aleatoric_uncertainty, epistemic_uncertainty
    
    def _update_regime_probabilities(
        self, 
        features: Dict[str, float], 
        prior_belief: Optional[BeliefState]
    ) -> np.ndarray:
        """
        Update regime probabilities using Bayes' rule
        Combines LVR's regime detection with Autonomous System's approach
        """
        # Feature vector for regime detection
        feature_vector = np.array([
            features.get("volatility_estimate", 0.0),
            abs(features.get("price_momentum", 0.0)),
            abs(features.get("volume_imbalance", 0.0)),
            features.get("ofI", 0.0),
            1.0 / (1.0 + features.get("depth_imbalance", 0.0)**2),  # Liquidity
        ])
        
        # Normalize feature vector
        feature_norm = np.linalg.norm(feature_vector)
        if feature_norm > 0:
            feature_vector = feature_vector / feature_norm
        
        # Likelihood of features under each regime
        # In practice, these would be learned Gaussian mixtures
        likelihoods = self._compute_regime_likelihoods(feature_vector)
        
        # Prior probabilities (from previous belief or uniform)
        if prior_belief is not None:
            priors = np.array(prior_belief.regime_probabilities)
        else:
            priors = np.ones(self.n_regimes) / self.n_regimes  # Uniform prior
        
        # Apply transition model (Markovian assumption)
        predicted_priors = self.regime_transition_matrix.T @ priors
        
        # Bayes' rule: posterior ∝ likelihood × prior
        unnormalized_posterior = likelihoods * predicted_priors
        posterior = unnormalized_posterior / np.sum(unnormalized_posterior)
        
        return posterior
    
    def _compute_regime_likelihoods(self, feature_vector: np.ndarray) -> np.ndarray:
        """
        Compute likelihood of features under each regime
        Enhanced with regime-specific patterns and better separation
        """
        # Define typical feature patterns for each regime with better separation
        regime_characteristics = {
            RegimeType.BULL_LOW_VOL:     {"vol": 0.05, "trend": 0.3, "liq": 0.9, "ofi": 0.2, "volm": 0.3},
            RegimeType.BULL_HIGH_VOL:    {"vol": 0.5, "trend": 0.4, "liq": 0.6, "ofi": 0.3, "volm": 0.5},
            RegimeType.BEAR_LOW_VOL:     {"vol": 0.08, "trend": -0.3, "liq": 0.85, "ofi": -0.2, "volm": 0.3},
            RegimeType.BEAR_HIGH_VOL:    {"vol": 0.6, "trend": -0.4, "liq": 0.55, "ofi": -0.3, "volm": 0.5},
            RegimeType.SIDEWAYS_LOW_VOL: {"vol": 0.06, "trend": 0.0, "liq": 0.95, "ofi": 0.0, "volm": 0.2},
            RegimeType.SIDEWAYS_HIGH_VOL:{"vol": 0.4, "trend": 0.05, "liq": 0.7, "ofi": 0.05, "volm": 0.4},
            RegimeType.CRISIS:           {"vol": 0.9, "trend": -0.6, "liq": 0.15, "ofi": -0.5, "volm": 0.9},
            RegimeType.RECOVERY:         {"vol": 0.35, "trend": 0.25, "liq": 0.6, "ofi": 0.25, "volm": 0.4}
        }
        
        likelihoods = []
        for regime in RegimeType:
            chars = regime_characteristics[regime]
            
            # Create expected feature vector for this regime
            expected_features = np.array([
                chars["vol"],      # volatility
                abs(chars["trend"]), # price momentum (absolute)
                chars["volm"],     # volume
                chars["ofi"],      # order flow imbalance
                chars["liq"]       # liquidity
            ])
            
            # Compute likelihood using Gaussian with regime-specific variance
            diff = feature_vector - expected_features
            # Use Mahalanobis-like distance with regime-specific scaling
            if "BULL" in regime.name or "BEAR" in regime.name:
                scale = 0.3  # Tighter clustering for trending regimes
            elif "SIDEWAYS" in regime.name:
                scale = 0.2  # Very tight for sideways
            elif regime == RegimeType.CRISIS:
                scale = 0.5  # Wider for crisis (more variable)
            else:
                scale = 0.35
            
            distance_sq = np.sum((diff / scale)**2)
            likelihood = np.exp(-0.5 * distance_sq)  # Gaussian likelihood
            likelihoods.append(likelihood)
        
        likelihoods = np.array(likelihoods)
        
        # Normalize to get proper likelihoods
        if np.sum(likelihoods) > 0:
            likelihoods = likelihoods / np.sum(likelihoods)
        else:
            likelihoods = np.ones_like(likelihoods) / len(likelihoods)
            
        return likelihoods
    
    def _compute_confidence(
        self, 
        aleatoric_uncertainty: float, 
        epistemic_uncertainty: float, 
        regime_probabilities: np.ndarray
    ) -> float:
        """
        Compute overall confidence in the belief state
        High confidence when:
        - Low total uncertainty
        - Clear regime identification (low entropy)
        """
        # Uncertainty component (lower uncertainty = higher confidence)
        # Use sigmoid-based mapping instead of aggressive exponential decay
        total_uncertainty = aleatoric_uncertainty + epistemic_uncertainty
        # Map uncertainty to confidence: uncertainty of 0 -> 1.0, uncertainty of 0.5 -> 0.5
        uncertainty_confidence = 1.0 / (1.0 + total_uncertainty * 2.0)
        
        # Regime clarity component (lower entropy = higher confidence)
        # Add small epsilon to avoid log(0)
        eps = 1e-10
        probs = regime_probabilities + eps
        probs = probs / np.sum(probs)  # Renormalize
        entropy = -np.sum(probs * np.log(probs))
        max_entropy = np.log(len(probs))  # Maximum possible entropy
        regime_confidence = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 1.0
        
        # Combine components - weight regime clarity more heavily
        confidence = 0.3 * uncertainty_confidence + 0.7 * regime_confidence
        
        # Boost confidence when regime is reasonably clear
        max_regime_prob = np.max(regime_probabilities)
        if max_regime_prob > 0.3:
            confidence = min(1.0, confidence * (1.0 + max_regime_prob))
        
        # Ensure bounds
        return max(0.0, min(1.0, confidence))


# Example usage and testing
if __name__ == "__main__":
    import time
    
    # Create belief state estimator
    estimator = BeliefStateEstimator()
    
    # Simulate market data
    market_data = {
        "bid_price": 100.0,
        "ask_price": 100.5,
        "bid_size": 10.0,
        "ask_size": 8.0,
        "last_price": 100.2,
        "last_size": 5.0
    }
    
    # Update belief state
    belief_state = estimator.update(market_data)
    
    print("Belief State:")
    print(f"  Expected Return: {belief_state.expected_return:.4f}")
    print(f"  Return Uncertainty: {belief_state.expected_return_uncertainty:.4f}")
    print(f"  Aleatoric Uncertainty: {belief_state.aleatoric_uncertainty:.4f}")
    print(f"  Epistemic Uncertainty: {belief_state.epistemic_uncertainty:.4f}")
    print(f"  Volatility Estimate: {belief_state.volatility_estimate:.4f}")
    print(f"  Liquidity Estimate: {belief_state.liquidity_estimate:.4f}")
    print(f"  Momentum Signal: {belief_state.momentum_signal:.4f}")
    print(f"  Volume Signal: {belief_state.volume_signal:.4f}")
    print(f"  Confidence: {belief_state.confidence:.4f}")
    
    regime, prob = belief_state.get_most_likely_regime()
    print(f"  Most Likely Regime: {regime.name} ({prob:.4f})")
    print(f"  Entropy: {belief_state.get_entropy():.4f}")
    print(f"  Is Confident: {belief_state.is_confident()}")
    
    # Show microstructure features
    print("\nMicrostructure Features:")
    for feature, value in belief_state.microstructure_features.items():
        print(f"  {feature}: {value:.4f}")