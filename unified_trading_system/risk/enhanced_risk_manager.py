"""
Enhanced Risk Management with Dynamic VaR and Correlation-Aware Limits
Profitable Strategy Risk Components

Adds to UnifiedRiskManager:
- Dynamic VaR calculation with regime adjustments
- Correlation-aware position limits
- Portfolio heat management
- Tail risk protection
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque
import logging

from perception.belief_state import RegimeType

logger = logging.getLogger(__name__)


class DynamicVaRCalculator:
    """Dynamic Value at Risk calculator with regime adjustments"""
    
    def __init__(self, 
                 confidence_level: float = 0.99,
                 lookback_window: int = 100,
                 buffer_multiplier: float = 1.2):
        self.confidence_level = confidence_level
        self.lookback_window = lookback_window
        self.buffer_multiplier = buffer_multiplier
        
        # Return history for VaR calculation
        self.returns_history = deque(maxlen=lookback_window)
        
        # Regime-specific multipliers
        self.regime_multipliers = {
            RegimeType.BULL_LOW_VOL: 1.0,
            RegimeType.BULL_HIGH_VOL: 1.3,
            RegimeType.BEAR_LOW_VOL: 1.2,
            RegimeType.BEAR_HIGH_VOL: 1.6,
            RegimeType.SIDEWAYS_LOW_VOL: 0.9,
            RegimeType.SIDEWAYS_HIGH_VOL: 1.4,
            RegimeType.CRISIS: 2.5,
            RegimeType.RECOVERY: 1.1
        }
    
    def add_return(self, return_value: float):
        """Add a new return observation"""
        self.returns_history.append(return_value)
    
    def calculate_historical_var(self) -> float:
        """Calculate historical VaR"""
        if len(self.returns_history) < 10:
            return 0.05  # Default 5% VaR
        
        returns = np.array(list(self.returns_history))
        
        # Calculate percentile
        percentile = (1 - self.confidence_level) * 100
        var = np.percentile(returns, percentile)
        
        # Return absolute value (VaR is typically positive as a loss)
        return abs(var) if var < 0 else 0.0
    
    def calculate_regime_var(self, regime: RegimeType) -> float:
        """Calculate regime-adjusted VaR"""
        base_var = self.calculate_historical_var()
        
        # Apply regime multiplier
        multiplier = self.regime_multipliers.get(regime, 1.0)
        
        # Apply buffer
        var_with_buffer = base_var * multiplier * self.buffer_multiplier
        
        return var_with_buffer
    
    def calculate_conditional_var(self, regime: RegimeType) -> float:
        """Calculate Conditional VaR (Expected Shortfall)"""
        if len(self.returns_history) < 10:
            return 0.07  # Default 7% CVaR
        
        base_var = self.calculate_regime_var(regime)
        
        # CVaR is typically 1.5-2x VaR in normal conditions
        # Higher in crisis
        cvaR_multiplier = 1.5 if regime != RegimeType.CRISIS else 2.5
        
        return base_var * cvaR_multiplier
    
    def get_risk_bounds(self, regime: RegimeType) -> Tuple[float, float]:
        """Get VaR and CVaR bounds for risk management"""
        var = self.calculate_regime_var(regime)
        cvar = self.calculate_conditional_var(regime)
        
        return var, cvar


class CorrelationManager:
    """Manages position correlations for risk-aware sizing"""
    
    def __init__(self, 
                 max_correlated_exposure: float = 0.6,
                 correlation_threshold: float = 0.5):
        self.max_correlated_exposure = max_correlated_exposure
        self.correlation_threshold = correlation_threshold
        
        # Asset correlation matrix (simplified - would be learned in production)
        # Default: high correlation within crypto, lower across assets
        self.correlation_matrix = None
        self.asset_list = []
        
        # Position tracking
        self.positions = {}  # {symbol: quantity}
        
    def initialize_correlation_matrix(self, assets: List[str]):
        """Initialize correlation matrix for assets"""
        self.asset_list = assets
        n = len(assets)
        
        # Default correlation matrix (can be learned from data)
        # High correlation (0.7-0.9) for similar assets
        self.correlation_matrix = np.eye(n)
        
        # Set some default correlations
        # BTC/ETH/SOL - high correlation
        crypto_high = ['BTC', 'ETH', 'SOL']
        # ALTcoins - medium correlation
        crypto_mid = ['BNB', 'XRP', 'ADA', 'DOGE', 'MATIC']
        
        for i, asset_i in enumerate(assets):
            for j, asset_j in enumerate(assets):
                if i == j:
                    continue
                    
                # Check if both in high correlation group
                in_high_i = any(c in asset_i for c in crypto_high)
                in_high_j = any(c in asset_j for c in crypto_high)
                
                if in_high_i and in_high_j:
                    self.correlation_matrix[i, j] = 0.8
                    continue
                    
                # Check if both in mid correlation group
                in_mid_i = any(c in asset_i for c in crypto_mid)
                in_mid_j = any(c in asset_j for c in crypto_mid)
                
                if in_mid_i and in_mid_j:
                    self.correlation_matrix[i, j] = 0.5
                    continue
                    
                # Default correlation
                self.correlation_matrix[i, j] = 0.3
    
    def update_position(self, symbol: str, quantity: float):
        """Update position for correlation calculation"""
        self.positions[symbol] = quantity
    
    def remove_position(self, symbol: str):
        """Remove position"""
        if symbol in self.positions:
            del self.positions[symbol]
    
    def calculate_correlation_exposure(self, new_symbol: str, new_quantity: float) -> float:
        """Calculate correlation-adjusted exposure for new position"""
        if not self.positions or self.correlation_matrix is None:
            return new_quantity
        
        if new_symbol not in self.asset_list:
            return new_quantity
        
        new_idx = self.asset_list.index(new_symbol)
        
        # Calculate weighted correlation with existing positions
        total_correlation = 0.0
        total_exposure = 0.0
        
        for symbol, qty in self.positions.items():
            if symbol in self.asset_list:
                idx = self.asset_list.index(symbol)
                corr = self.correlation_matrix[new_idx, idx]
                
                # Weight by position size
                total_correlation += corr * qty
                total_exposure += qty
        
        if total_exposure > 0:
            avg_correlation = total_correlation / total_exposure
        else:
            avg_correlation = 0.0
        
        # Apply correlation penalty
        if avg_correlation > self.correlation_threshold:
            # Reduce effective quantity
            penalty = 1.0 - (avg_correlation - self.correlation_threshold)
            effective_quantity = new_quantity * max(penalty, 0.5)
            return effective_quantity
        
        return new_quantity
    
    def get_portfolio_correlation(self) -> float:
        """Calculate average portfolio correlation"""
        if not self.positions or self.correlation_matrix is None:
            return 0.0
        
        positions_list = list(self.positions.values())
        if len(positions_list) < 2:
            return 0.0
        
        # Get correlation values between all position pairs
        correlations = []
        for i, (sym_i, qty_i) in enumerate(self.positions.items()):
            for j, (sym_j, qty_j) in enumerate(self.positions.items()):
                if i >= j:
                    continue
                if sym_i in self.asset_list and sym_j in self.asset_list:
                    idx_i = self.asset_list.index(sym_i)
                    idx_j = self.asset_list.index(sym_j)
                    corr = self.correlation_matrix[idx_i, idx_j]
                    correlations.append(corr * min(qty_i, qty_j))
        
        if correlations:
            return np.mean(correlations)
        return 0.0


class PortfolioHeatManager:
    """Manages portfolio heat (aggregate risk exposure)"""
    
    def __init__(self,
                 max_heat: float = 0.80,
                 warning_heat: float = 0.60,
                 heat_decay_rate: float = 0.10):
        self.max_heat = max_heat
        self.warning_heat = warning_heat
        self.heat_decay_rate = heat_decay_rate
        
        self.current_heat = 0.0
        self.position_count = 0
        
    def calculate_heat(self, 
                      positions: Dict[str, Dict],
                      portfolio_value: float,
                      correlation_matrix: np.ndarray = None) -> float:
        """Calculate portfolio heat"""
        if not positions:
            self.current_heat = 0.0
            return 0.0
        
        # Calculate base heat from positions
        total_heat = 0.0
        position_values = []
        
        for symbol, pos in positions.items():
            position_value = pos.get('quantity', 0) * pos.get('entry_price', 1)
            leverage = pos.get('leverage', 1)
            
            # Heat contribution = position value * leverage
            heat_contribution = position_value * leverage
            position_values.append(heat_contribution)
            total_heat += heat_contribution
        
        # Apply correlation adjustment
        if correlation_matrix is not None and len(position_values) > 1:
            # Higher correlation = higher heat
            position_array = np.array(position_values)
            normalized = position_array / np.sum(position_array)
            
            # Calculate portfolio concentration
            concentration = np.dot(normalized, np.dot(correlation_matrix, normalized))
            
            # Adjust heat based on concentration
            total_heat *= (1 + concentration * 0.3)
        
        # Normalize by portfolio value
        if portfolio_value > 0:
            self.current_heat = total_heat / portfolio_value
        else:
            self.current_heat = 0.0
        
        self.position_count = len(positions)
        
        return self.current_heat
    
    def can_accept_new_position(self, additional_heat: float = 0.1) -> Tuple[bool, str]:
        """Check if new position can be added"""
        projected_heat = self.current_heat + additional_heat
        
        if projected_heat > self.max_heat:
            return False, f"Would exceed max heat ({self.max_heat:.0%})"
        
        if self.current_heat > self.warning_heat:
            return True, f"WARNING: Heat at {self.current_heat:.0%}"
        
        return True, "OK"
    
    def apply_heat_decay(self):
        """Apply heat decay when position closes"""
        self.current_heat = max(0, self.current_heat - self.heat_decay_rate)


class TailRiskProtector:
    """Protects against tail risk events"""
    
    def __init__(self,
                 volatility_multiplier: float = 2.0,
                 drawdown_threshold: float = 0.10,
                 crisis_lookback: int = 20):
        self.volatility_multiplier = volatility_multiplier
        self.drawdown_threshold = drawdown_threshold
        self.crisis_lookback = crisis_lookback
        
        # Recent returns for tail detection
        self.returns_history = deque(maxlen=crisis_lookback)
        
    def add_return(self, return_value: float):
        """Add return observation"""
        self.returns_history.append(return_value)
    
    def is_tail_risk_elevated(self) -> bool:
        """Check if tail risk is elevated"""
        if len(self.returns_history) < 10:
            return False
        
        returns = np.array(list(self.returns_history))
        
        # Check for large negative returns
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return > 0:
            # Current return more than 2 std below mean
            latest_return = returns[-1]
            
            if latest_return < mean_return - self.volatility_multiplier * std_return:
                return True
        
        # Check for consecutive losses
        consecutive_losses = 0
        for ret in reversed(returns):
            if ret < 0:
                consecutive_losses += 1
            else:
                break
        
        if consecutive_losses >= 5:
            return True
        
        return False
    
    def should_hedge(self, current_drawdown: float) -> bool:
        """Determine if hedging should be activated"""
        # Activate hedge if:
        # 1. Tail risk elevated
        # 2. Drawdown exceeds threshold
        # 3. Both
        
        tail_risk = self.is_tail_risk_elevated()
        drawdown_risk = current_drawdown > self.drawdown_threshold
        
        return tail_risk and drawdown_risk
    
    def get_protection_level(self, current_drawdown: float) -> str:
        """Get current protection level"""
        if current_drawdown > 0.15:
            return "CRITICAL"
        elif current_drawdown > 0.10:
            return "HIGH"
        elif current_drawdown > 0.05:
            return "MEDIUM"
        elif self.is_tail_risk_elevated():
            return "ELEVATED"
        else:
            return "NORMAL"


class EnhancedRiskManager:
    """Combined enhanced risk management"""
    
    def __init__(self, config: Dict = None):
        if config is None:
            config = {}
        
        # Initialize components
        self.var_calculator = DynamicVaRCalculator(
            confidence_level=config.get('var_confidence', 0.99),
            buffer_multiplier=config.get('var_buffer', 1.2)
        )
        
        self.correlation_manager = CorrelationManager(
            max_correlated_exposure=config.get('max_correlated_exposure', 0.6)
        )
        
        self.heat_manager = PortfolioHeatManager(
            max_heat=config.get('max_portfolio_heat', 0.80),
            warning_heat=config.get('warning_heat', 0.60)
        )
        
        self.tail_protector = TailRiskProtector(
            volatility_multiplier=config.get('tail_multiplier', 2.0),
            drawdown_threshold=config.get('drawdown_threshold', 0.10)
        )
        
        # Portfolio tracking
        self.portfolio_value = config.get('initial_capital', 10000.0)
        self.peak_value = self.portfolio_value
        self.current_drawdown = 0.0
        
    def update_portfolio_value(self, value: float):
        """Update portfolio value and calculate drawdown"""
        self.portfolio_value = value
        
        # Update peak
        if value > self.peak_value:
            self.peak_value = value
        
        # Calculate drawdown
        if self.peak_value > 0:
            self.current_drawdown = (self.peak_value - value) / self.peak_value
    
    def record_return(self, return_value: float):
        """Record return for VaR and tail risk calculation"""
        self.var_calculator.add_return(return_value)
        self.tail_protector.add_return(return_value)
    
    def assess_new_position(self, 
                           symbol: str,
                           quantity: float,
                           price: float,
                           existing_positions: Dict[str, Dict],
                           current_regime: RegimeType) -> Tuple[bool, str, Dict]:
        """
        Assess if new position should be allowed
        
        Returns:
            Tuple of (allowed: bool, reason: str, risk_metrics: Dict)
        """
        # Calculate position value
        position_value = quantity * price
        
        # Check heat
        heat_needed = position_value / self.portfolio_value
        can_add, heat_reason = self.heat_manager.can_accept_new_position(heat_needed)
        
        if not can_add:
            return False, heat_reason, {'heat_violation': True}
        
        # Check correlation
        effective_quantity = self.correlation_manager.calculate_correlation_exposure(
            symbol, quantity
        )
        
        if effective_quantity < quantity:
            reason = f"Correlation reduction: {effective_quantity/quantity:.0%} effective"
        
        # Check VaR
        var, cvar = self.var_calculator.get_risk_bounds(current_regime)
        
        # Calculate new portfolio VaR
        current_exposure = sum(
            p.get('quantity', 0) * p.get('entry_price', 1) 
            for p in existing_positions.values()
        )
        new_exposure = current_exposure + effective_quantity * price
        
        portfolio_var = (new_exposure / self.portfolio_value) * var if self.portfolio_value > 0 else 0
        
        # VaR limit check (20% of portfolio)
        if portfolio_var > 0.20:
            return False, f"VaR limit exceeded: {portfolio_var:.1%}", {'var_violation': True}
        
        # Check tail risk
        if self.tail_protector.should_hedge(self.current_drawdown):
            protection_level = self.tail_protector.get_protection_level(self.current_drawdown)
            if protection_level in ["CRITICAL", "HIGH"]:
                return False, f"Tail risk protection active ({protection_level})", {'tail_risk': True}
        
        # All checks passed
        risk_metrics = {
            'var': var,
            'cvar': cvar,
            'heat': self.heat_manager.current_heat,
            'drawdown': self.current_drawdown,
            'correlation': self.correlation_manager.get_portfolio_correlation(),
            'protection_level': self.tail_protector.get_protection_level(self.current_drawdown)
        }
        
        return True, "OK", risk_metrics
    
    def update_positions(self, positions: Dict[str, Dict]):
        """Update positions for correlation tracking"""
        self.correlation_manager.positions.clear()
        
        for symbol, pos in positions.items():
            quantity = pos.get('quantity', 0)
            if quantity > 0:
                self.correlation_manager.update_position(symbol, quantity)
    
    def get_risk_summary(self) -> Dict:
        """Get comprehensive risk summary"""
        return {
            'portfolio_value': self.portfolio_value,
            'peak_value': self.peak_value,
            'current_drawdown': self.current_drawdown,
            'portfolio_heat': self.heat_manager.current_heat,
            'position_count': self.heat_manager.position_count,
            'portfolio_correlation': self.correlation_manager.get_portfolio_correlation(),
            'tail_risk_level': self.tail_protector.get_protection_level(self.current_drawdown),
            'var': self.var_calculator.calculate_historical_var(),
            'cvar': self.var_calculator.calculate_conditional_var(RegimeType.SIDEWAYS_LOW_VOL)
        }


# Example usage
if __name__ == "__main__":
    # Create enhanced risk manager
    config = {
        'var_confidence': 0.99,
        'var_buffer': 1.2,
        'max_correlated_exposure': 0.6,
        'max_portfolio_heat': 0.80,
        'initial_capital': 10000.0
    }
    
    risk_manager = EnhancedRiskManager(config)
    
    # Simulate some returns
    for i in range(50):
        ret = np.random.normal(0.001, 0.02)
        risk_manager.record_return(ret)
    
    # Simulate existing positions
    positions = {
        'BTC': {'quantity': 0.1, 'entry_price': 50000, 'leverage': 20},
        'ETH': {'quantity': 1.0, 'entry_price': 3000, 'leverage': 15}
    }
    
    # Check new position
    allowed, reason, metrics = risk_manager.assess_new_position(
        symbol='SOL',
        quantity=10,
        price=100,
        existing_positions=positions,
        current_regime=RegimeType.BULL_LOW_VOL
    )
    
    print(f"Position allowed: {allowed}")
    print(f"Reason: {reason}")
    print(f"Risk metrics: {metrics}")
    
    # Get risk summary
    summary = risk_manager.get_risk_summary()
    print(f"\nRisk Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")