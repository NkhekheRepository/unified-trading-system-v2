"""
Position Sizing Module for Trading System
Implements Kelly Criterion and utility-based position sizing with uncertainty quantification
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from dataclasses import dataclass
import json

class RiskAversionType:
    """Risk aversion types for position sizing"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"

logger = logging.getLogger(__name__)

pass

@dataclass
class PositionSizeParams:
    """Parameters for position sizing calculation"""
    expected_return: float           # Expected return (e.g., 0.02 = 2%)
    uncertainty: float               # Uncertainty in return estimate (std dev)
    win_rate: float                  # Historical win rate (0-1)
    avg_win: float                   # Average winning trade amount
    avg_loss: float                  # Average losing trade amount
    max_position_pct: float = 0.1    # Maximum position as % of portfolio
    kelly_fraction: float = 0.25     # Kelly fraction (0.25 = half-Kelly)
    risk_aversion: str = "moderate"

@dataclass
class PositionSizeResult:
    """Result of position sizing calculation"""
    position_size_pct: float         # Suggested position as % of portfolio
    position_size_value: float       # Suggested position in dollar terms
    kelly_bet: float                 # Raw Kelly bet size
    adjusted_kelly: float            # Adjusted Kelly after risk controls
    confidence_level: float          # Confidence in the position size
    risk_metrics: Dict[str, float]   # Additional risk metrics
    recommended_action: str          # Suggested action (ENTER, REDUCE, AVOID)

class KellyPositionSizer:
    """
    Position sizing using Kelly Criterion with risk adjustments
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.position_history = []
        self.performance_history = []
        
    def _default_config(self) -> Dict:
        return {
            'max_position_pct': 0.1,           # 10% max position
            'kelly_fraction': 0.25,           # Use 25% of Kelly (half-Kelly)
            'min_kelly_threshold': 0.01,      # Minimum Kelly to take position
            'max_kelly_cap': 0.5,             # Cap Kelly at 50%
            'use_uncertainty_scaling': True,
            'use_drawdown_scaling': True,
            'drawdown_threshold': 0.1,        # Start reducing at 10% drawdown
            'drawdown_max_reduction': 0.8,    # Max reduction at max drawdown
            'volatility_scaling': True,
            'target_volatility': 0.15,        # Target annualized volatility
            'risk_aversion_multipliers': {
                'conservative': 0.25,
                'moderate': 0.5,
                'aggressive': 1.0
            }
        }
    
    def calculate_kelly(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Calculate raw Kelly Criterion
        
        Kelly % = W - (1-W) / (Avg Win / Avg Loss)
        
        Where:
        - W = win rate
        - (1-W) = loss rate
        - Avg Win / Avg Loss = payoff ratio
        """
        if avg_loss == 0:
            return 0.0
            
        payoff_ratio = avg_win / abs(avg_loss)
        
        # Kelly formula
        kelly = win_rate - ((1 - win_rate) / payoff_ratio)
        
        # Kelly can be negative (don't trade) or > 1 (rare, cap it)
        return max(0.0, min(kelly, self.config['max_kelly_cap']))
    
    def calculate_uncertainty_adjusted_kelly(self, kelly: float, 
                                            uncertainty: float) -> float:
        """
        Adjust Kelly based on uncertainty in the estimate
        Higher uncertainty = lower effective Kelly
        """
        if not self.config['use_uncertainty_scaling']:
            return kelly
            
        # Uncertainty factor: higher uncertainty reduces Kelly
        # Use a decay function
        uncertainty_factor = np.exp(-uncertainty * 2)
        
        adjusted_kelly = kelly * uncertainty_factor
        
        return adjusted_kelly
    
    def calculate_drawdown_adjusted_kelly(self, kelly: float, 
                                          current_drawdown: float) -> float:
        """
        Adjust Kelly based on current drawdown
        Higher drawdown = smaller positions
        """
        if not self.config['use_drawdown_scaling']:
            return kelly
            
        drawdown_threshold = self.config['drawdown_threshold']
        max_reduction = self.config['drawdown_max_reduction']
        
        if current_drawdown <= drawdown_threshold:
            # No adjustment needed
            return kelly
            
        # Linear scaling from drawdown threshold to max drawdown
        reduction_factor = min(
            max_reduction,
            (current_drawdown - drawdown_threshold) / (0.5 - drawdown_threshold)  # Assume 50% max drawdown
        )
        
        adjusted_kelly = kelly * (1 - reduction_factor)
        
        return adjusted_kelly
    
    def calculate_volatility_adjusted_kelly(self, kelly: float,
                                          current_volatility: float) -> float:
        """
        Adjust Kelly based on current vs target volatility
        """
        if not self.config['volatility_scaling']:
            return kelly
            
        target_vol = self.config['target_volatility']
        
        if current_volatility <= 0:
            return kelly
            
        # Scale inversely with volatility
        vol_ratio = target_vol / current_volatility
        
        # Bound the adjustment
        vol_adjustment = np.clip(vol_ratio, 0.5, 2.0)
        
        adjusted_kelly = kelly * vol_adjustment
        
        return adjusted_kelly
    
    def calculate_position_size(self, 
                               params: PositionSizeParams,
                               portfolio_value: float = 100000,
                               current_drawdown: float = 0.0,
                               current_volatility: float = 0.15) -> PositionSizeResult:
        """
        Calculate optimal position size based on Kelly Criterion with adjustments
        """
        # Step 1: Calculate raw Kelly
        kelly_bet = self.calculate_kelly(
            params.win_rate,
            params.avg_win,
            params.avg_loss
        )
        
        # Step 2: Apply uncertainty adjustment
        adjusted_kelly = self.calculate_uncertainty_adjusted_kelly(
            kelly_bet,
            params.uncertainty
        )
        
        # Step 3: Apply Kelly fraction (e.g., half-Kelly)
        adjusted_kelly *= params.kelly_fraction
        
        # Step 4: Apply risk aversion multiplier
        risk_mult = self.config['risk_aversion_multipliers'].get(
            params.risk_aversion, 
            0.5
        )
        adjusted_kelly *= risk_mult
        
        # Step 5: Apply drawdown scaling
        adjusted_kelly = self.calculate_drawdown_adjusted_kelly(
            adjusted_kelly,
            current_drawdown
        )
        
        # Step 6: Apply volatility scaling
        adjusted_kelly = self.calculate_volatility_adjusted_kelly(
            adjusted_kelly,
            current_volatility
        )
        
        # Step 7: Apply maximum position constraint
        max_position = min(params.max_position_pct, self.config['max_position_pct'])
        final_position_pct = min(adjusted_kelly, max_position)
        
        # Step 8: Calculate position value
        position_value = portfolio_value * final_position_pct
        
        # Step 9: Calculate confidence level
        confidence = self._calculate_confidence(params, kelly_bet, adjusted_kelly)
        
        # Step 10: Determine recommended action
        action = self._determine_action(final_position_pct, kelly_bet, confidence)
        
        # Additional risk metrics
        risk_metrics = {
            'kelly_bet_raw': kelly_bet,
            'kelly_after_uncertainty': kelly_bet * np.exp(-params.uncertainty * 2),
            'kelly_after_all_adjustments': adjusted_kelly,
            'position_as_kelly_pct': (final_position_pct / kelly_bet) if kelly_bet > 0 else 0,
            'volatility_adjustment_factor': current_volatility / self.config['target_volatility'],
            'drawdown_reduction_factor': 1.0 - max(0, min(0.8, (current_drawdown - 0.1) / 0.4))
        }
        
        result = PositionSizeResult(
            position_size_pct=final_position_pct,
            position_size_value=position_value,
            kelly_bet=kelly_bet,
            adjusted_kelly=adjusted_kelly,
            confidence_level=confidence,
            risk_metrics=risk_metrics,
            recommended_action=action
        )
        
        # Store for history
        self.position_history.append({
            'position_size_pct': final_position_pct,
            'kelly_bet': kelly_bet,
            'adjusted_kelly': adjusted_kelly,
            'expected_return': params.expected_return,
            'uncertainty': params.uncertainty,
            'win_rate': params.win_rate
        })
        
        return result
    
    def _calculate_confidence(self, params: PositionSizeParams, 
                             kelly_bet: float,
                             adjusted_kelly: float) -> float:
        """
        Calculate confidence in the position size recommendation
        """
        confidence_factors = []
        
        # Factor 1: Kelly magnitude (higher Kelly = more confidence)
        kelly_confidence = min(kelly_bet / 0.2, 1.0)  # 20% Kelly = max confidence
        confidence_factors.append(kelly_confidence)
        
        # Factor 2: Win rate certainty
        win_rate_confidence = params.win_rate if params.win_rate > 0.5 else (1 - params.win_rate)
        confidence_factors.append(win_rate_confidence)
        
        # Factor 3: Uncertainty (lower uncertainty = higher confidence)
        uncertainty_confidence = np.exp(-params.uncertainty)
        confidence_factors.append(uncertainty_confidence)
        
        # Factor 4: Edge stability (how close adjusted Kelly is to raw Kelly)
        if kelly_bet > 0:
            stability_confidence = adjusted_kelly / kelly_bet
        else:
            stability_confidence = 0.0
        confidence_factors.append(stability_confidence)
        
        # Combined confidence
        combined_confidence = np.mean(confidence_factors)
        
        return float(np.clip(combined_confidence, 0.0, 1.0))
    
    def _determine_action(self, position_pct: float, kelly_bet: float,
                         confidence: float) -> str:
        """
        Determine recommended action based on position size and confidence
        """
        # No trade conditions
        if kelly_bet < self.config['min_kelly_threshold']:
            return "AVOID"
        
        if kelly_bet <= 0:
            return "AVOID"
        
        # Low confidence
        if confidence < 0.3:
            return "AVOID"
        
        # Position size-based actions
        if position_pct >= 0.05:  # 5%+ position
            return "ENTER"
        elif position_pct >= 0.02:  # 2-5%
            return "ENTER" if confidence > 0.5 else "REDUCE"
        elif position_pct >= 0.01:  # 1-2%
            return "REDUCE"
        else:
            return "AVOID"
    
    def update_performance(self, trade_result: Dict):
        """
        Update position sizer with actual trade results for learning
        """
        self.performance_history.append({
            'expected_return': trade_result.get('expected_return', 0),
            'actual_return': trade_result.get('actual_return', 0),
            'position_size': trade_result.get('position_size', 0),
            'win': trade_result.get('win', False),
            'pnl': trade_result.get('pnl', 0)
        })
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get position sizing statistics
        """
        if not self.performance_history:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'kelly_recommendation': 0
            }
        
        wins = [t for t in self.performance_history if t['win']]
        losses = [t for t in self.performance_history if not t['win']]
        
        win_rate = len(wins) / len(self.performance_history)
        avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['pnl'] for t in losses]) if losses else 0
        
        kelly = self.calculate_kelly(win_rate, avg_win, avg_loss)
        
        return {
            'total_trades': len(self.performance_history),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'kelly_recommendation': kelly,
            'avg_position_size': np.mean([t['position_size'] for t in self.position_history]) if self.position_history else 0
        }

class UtilityBasedPositionSizer:
    """
    Position sizing using utility theory
    """
    
    def __init__(self, risk_aversion: float = 0.5):
        self.risk_aversion = risk_aversion  # 0 = risk neutral, 1 = very risk averse
        
    def calculate_position_size(self,
                               expected_return: float,
                               return_variance: float,
                               portfolio_value: float = 100000,
                               max_position_pct: float = 0.1) -> float:
        """
        Calculate optimal position using mean-variance utility
        
        U = E[r] - (gamma/2) * Var[r]
        
        Where gamma is risk aversion coefficient
        """
        # Avoid division by zero
        if return_variance <= 0:
            return 0.0
        
        # Gamma coefficient based on risk aversion
        gamma = 2 * self.risk_aversion
        
        # Optimal position using analytical solution for mean-variance utility
        # For single asset: position = expected_return / (gamma * variance)
        optimal_position = expected_return / (gamma * return_variance)
        
        # Scale by portfolio value
        position_value = portfolio_value * optimal_position
        
        # Apply constraints
        max_position_value = portfolio_value * max_position_pct
        position_value = np.clip(position_value, 0, max_position_value)
        
        # Convert back to percentage
        position_pct = position_value / portfolio_value
        
        return position_pct
    
    def calculate_cvar_adjusted_position(self,
                                         expected_return: float,
                                         cvar: float,
                                         target_return: float,
                                         portfolio_value: float = 100000,
                                         max_position_pct: float = 0.1) -> float:
        """
        Adjust position based on CVaR constraint
        """
        # If expected return doesn't meet target, reduce position
        if expected_return < target_return:
            shortfall = target_return - expected_return
            reduction_factor = max(0, 1 - shortfall / abs(cvar)) if cvar < 0 else 1
            position_pct = max_position_pct * reduction_factor
        else:
            position_pct = max_position_pct
            
        return position_pct

class AdaptivePositionSizer:
    """
    Combines multiple position sizing approaches with adaptive weighting
    """
    
    def __init__(self):
        self.kelly_sizer = KellyPositionSizer()
        self.utility_sizer = UtilityBasedPositionSizer()
        self.performance_weights = {
            'kelly': 0.5,
            'utility': 0.5
        }
        
    def calculate_position_size(self,
                                params: PositionSizeParams,
                                portfolio_value: float = 100000,
                                current_drawdown: float = 0.0,
                                current_volatility: float = 0.15,
                                expected_return_variance: float = 0.01) -> PositionSizeResult:
        """
        Calculate position size using combined approach
        """
        # Get Kelly-based position
        kelly_result = self.kelly_sizer.calculate_position_size(
            params, portfolio_value, current_drawdown, current_volatility
        )
        
        # Get utility-based position
        utility_position = self.utility_sizer.calculate_position_size(
            params.expected_return,
            expected_return_variance,
            portfolio_value,
            params.max_position_pct
        )
        
        # Combine positions using weights
        combined_position = (
            self.performance_weights['kelly'] * kelly_result.position_size_pct +
            self.performance_weights['utility'] * utility_position
        )
        
        # Use Kelly result as base, adjust with utility
        final_result = PositionSizeResult(
            position_size_pct=combined_position,
            position_size_value=portfolio_value * combined_position,
            kelly_bet=kelly_result.kelly_bet,
            adjusted_kelly=kelly_result.adjusted_kelly,
            confidence_level=kelly_result.confidence_level,
            risk_metrics={
                **kelly_result.risk_metrics,
                'utility_position': utility_position,
                'kelly_weight': self.performance_weights['kelly'],
                'utility_weight': self.performance_weights['utility']
            },
            recommended_action=kelly_result.recommended_action
        )
        
        return final_result
    
    def update_weights(self, kelly_performance: float, utility_performance: float):
        """
        Update combination weights based on recent performance
        """
        total = kelly_performance + utility_performance
        if total > 0:
            self.performance_weights['kelly'] = kelly_performance / total
            self.performance_weights['utility'] = utility_performance / total

def create_position_sizer(method: str = "kelly", **kwargs) -> Any:
    """
    Factory function to create a position sizer
    """
    if method.lower() == "kelly":
        return KellyPositionSizer(kwargs.get('config'))
    elif method.lower() == "utility":
        return UtilityBasedPositionSizer(kwargs.get('risk_aversion', 0.5))
    elif method.lower() == "adaptive":
        return AdaptivePositionSizer()
    else:
        return KellyPositionSizer(kwargs.get('config'))