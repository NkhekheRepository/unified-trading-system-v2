"""
Unified Risk Management System
Combines LVR's protection levels with Autonomous System's risk manifold and control barrier system
"""


import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import time


class RiskLevel(Enum):
    """Risk levels combining LVR's protection levels with Autonomous System's approach"""
    LEVEL_0_NORMAL = 0      # Normal operation
    LEVEL_1_CAUTION = 1     # Elevated risk - reduce size
    LEVEL_2_WARNING = 2     # High risk - restrict trading
    LEVEL_3_DANGER = 3      # Danger - close all positions
    LEVEL_4_CRITICAL = 4    # Critical - manual intervention required


@dataclass
class RiskAssessment:
    """Comprehensive risk assessment"""
    risk_level: RiskLevel
    risk_score: float                    # Overall risk score [0, 1]
    cvar: float                         # Conditional Value at Risk
    volatility: float                   # Estimated volatility
    drawdown: float                     # Current drawdown
    leverage_ratio: float               # Current leverage usage
    liquidity_score: float              # Market liquidity [0, 1]
    concentration_risk: float           # Position concentration risk
    correlation_risk: float             # Portfolio correlation risk
    risk_gradient: np.ndarray           # Gradient of risk w.r.t. trading actions
    protective_action: str              # Recommended protective action
    timestamp: int                      # Nanoseconds since epoch
    metadata: Dict[str, Any] = field(default_factory=dict)


class RiskManifold:
    """
    Unified Risk Manifold combining:
    1. LVR's multi-factor risk assessment
    2. Autonomous System's nonlinear Risk Manifold
    3. LVR's protection levels with Autonomous System's control barrier theory
    """
    
    def __init__(
        self,
        # Risk manifold parameters (from Autonomous System)
        risk_sensitivity: float = 1.0,
        nonlinearity_factor: float = 0.5,
        
        # LVR protection level thresholds
        drawdown_warning: float = 0.05,    # 5% drawdown -> Level 1
        drawdown_danger: float = 0.10,     # 10% drawdown -> Level 2
        drawdown_critical: float = 0.15,   # 15% drawdown -> Level 3
        
        daily_loss_warning: float = 0.03,  # 3% daily loss -> Level 1
        daily_loss_danger: float = 0.05,   # 5% daily loss -> Level 2
        daily_loss_critical: float = 0.08, # 8% daily loss -> Level 3
        
        leverage_warning: float = 45.0,
        leverage_danger: float = 48.0,
        leverage_critical: float = 50.0,
        
        # Correlation and concentration thresholds
        correlation_warning: float = 0.6,  # 60% correlation -> Level 1
        correlation_danger: float = 0.8,   # 80% correlation -> Level 2
        concentration_warning: float = 0.3, # 30% in single position -> Level 1
        concentration_danger: float = 0.5,  # 50% in single position -> Level 2
    ):
        import logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            
        self.risk_sensitivity = risk_sensitivity
        self.nonlinearity_factor = nonlinearity_factor
        
        # LVR protection thresholds
        self.drawdown_warning = drawdown_warning
        self.drawdown_danger = drawdown_danger
        self.drawdown_critical = drawdown_critical
        
        self.daily_loss_warning = daily_loss_warning
        self.daily_loss_danger = daily_loss_danger
        self.daily_loss_critical = daily_loss_critical
        
        self.leverage_warning = leverage_warning
        self.leverage_danger = leverage_danger
        self.leverage_critical = leverage_critical
        
        self.correlation_warning = correlation_warning
        self.correlation_danger = correlation_danger
        self.concentration_warning = concentration_warning
        self.concentration_danger = concentration_danger
        
        # Risk factor weights (would be calibrated in practice)
        self.risk_weights = {
            "drawdown": 0.25,
            "daily_loss": 0.20,
            "leverage_ratio": 0.15,
            "volatility": 0.15,
            "liquidity_score": 0.10,
            "correlation_risk": 0.10,
            "concentration_risk": 0.05
        }
        
        # Risk factor histories for trend analysis
        self.risk_history = {
            "drawdown": [],
            "daily_loss": [],
            "leverage": [],
            "volatility": [],
            "liquidity": [],
            "correlation": [],
            "concentration": []
        }
        
        self.max_history_length = 1000
    
    def _update_risk_factor_histories(self, risk_factors: Dict[str, float]):
        """Update risk factor histories for trend analysis"""
        # Update each risk factor history
        for factor_name in self.risk_history.keys():
            if factor_name in risk_factors:
                self.risk_history[factor_name].append(risk_factors[factor_name])
                # Keep history within limits
                if len(self.risk_history[factor_name]) > self.max_history_length:
                    self.risk_history[factor_name] = self.risk_history[factor_name][-self.max_history_length:]
    
    def assess_risk(
        self,
        belief_state: Dict,
        portfolio_state: Dict,
        market_data: Dict,
        current_positions: Dict = None,
        recent_returns: List[float] = None
    ) -> RiskAssessment:
        """
        Assess current risk levels
        
        Args:
            belief_state: Current belief state from perception layer
            portfolio_state: Current portfolio state
            market_data: Current market data
            current_positions: Current positions (optional)
            recent_returns: Recent returns for volatility/drawdown calc (optional)
            
        Returns:
            Comprehensive risk assessment
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Ensure all inputs are dictionaries
        if not isinstance(belief_state, dict):
            logger.warning(f"belief_state is not dict: {type(belief_state)}")
            belief_state = {}
        if not isinstance(portfolio_state, dict):
            logger.warning(f"portfolio_state is not dict: {type(portfolio_state)}")
            portfolio_state = {}
        if not isinstance(market_data, dict):
            logger.warning(f"market_data is not dict: {type(market_data)}")
            market_data = {}
        if current_positions is not None and not isinstance(current_positions, dict):
            logger.warning(f"current_positions is not dict: {type(current_positions)}")
            current_positions = {}
        
        try:
            # Extract risk factors
            risk_factors = self._extract_risk_factors(
                belief_state, portfolio_state, market_data, 
                current_positions, recent_returns
            )
        except Exception as e:
            logger.error(f"Error extracting risk factors: {e}")
            logger.error(f"belief_state: {belief_state}")
            logger.error(f"portfolio_state: {portfolio_state}")
            logger.error(f"market_data: {market_data}")
            # Return default risk assessment in error case
            risk_factors = {
                "drawdown": 0.0,
                "daily_loss": 0.0,
                "leverage_ratio": 0.0,
                "volatility": 0.0,
                "liquidity_score": 0.5,
                "correlation_risk": 0.0,
                "concentration_risk": 0.0,
                "cvar": 0.0
            }
        
        # Compute nonlinear risk manifold
        risk_score = self._compute_risk_manifold(risk_factors)
        
        # Add Epistemic Squelch penalty to the risk score
        epistemic = risk_factors.get("epistemic_risk", 0.0)
        risk_score = np.clip(risk_score + (epistemic * 0.5), 0.0, 1.0)
        
        # Determine risk level based on LVR-style thresholds
        risk_level = self._determine_risk_level(risk_factors)
        
        # Compute risk gradient (for use in aggression controller)
        risk_gradient = self._compute_risk_gradient(risk_factors, belief_state)
        
        # Determine protective action
        protective_action = self._determine_protective_action(risk_level, risk_factors)
        
        # Create risk assessment
        assessment = RiskAssessment(
            risk_level=risk_level,
            risk_score=risk_score,
            cvar=risk_factors.get("cvar", 0.0),
            volatility=risk_factors.get("volatility", 0.0),
            drawdown=risk_factors.get("drawdown", 0.0),
            leverage_ratio=risk_factors.get("leverage_ratio", 0.0),
            liquidity_score=risk_factors.get("liquidity_score", 0.0),
            concentration_risk=risk_factors.get("concentration_risk", 0.0),
            correlation_risk=risk_factors.get("correlation_risk", 0.0),
            risk_gradient=risk_gradient,
            protective_action=protective_action,
            timestamp=int(time.time() * 1e9),
            metadata={
                "risk_factors": risk_factors,
                "risk_level_name": risk_level.name,
                "risk_factor_contributions": self._compute_risk_factor_contributions(risk_factors)
            }
        )
        
        # Update risk factor histories
        self._update_risk_factor_histories(risk_factors)
        
        return assessment
    
    def _extract_risk_factors(
        self,
        belief_state: Dict,
        portfolio_state: Dict,
        market_data: Dict,
        current_positions: Dict = None,
        recent_returns: List[float] = None
    ) -> Dict[str, float]:
        """Extract all relevant risk factors"""
        import logging
        logger = logging.getLogger(__name__)
        
        factors = {}
        
        # Debug: Check inputs for non-dict types that would break .get()
        def safe_get(d, key, default=0.0):
            if not isinstance(d, dict):
                logger.warning(f"safe_get: d is not dict, type={type(d)}, d={str(d)[:100]}")
                return default
            try:
                result = d.get(key, default)
                if isinstance(result, str):
                    logger.warning(f"safe_get: key={key} returned string: {result[:50]}...")
                    return default
                return result
            except Exception as e:
                logger.error(f"safe_get error for key={key}: {e}")
                return default
        
        # 1. Drawdown risk (from portfolio state or belief state)
        try:
            factors["drawdown"] = safe_get(portfolio_state, "drawdown", 0.0) or safe_get(belief_state, "drawdown", 0.0)
        except Exception as e:
            logger.error(f"Error extracting drawdown: {e}")
            factors["drawdown"] = 0.0
        
        # 2. Daily loss risk (would need intraday P&L tracking)
        # Simplified: use recent returns if available
        if recent_returns and len(recent_returns) > 0:
            # Calculate worst daily loss in recent period
            # Simplified: use minimum return as proxy
            factors["daily_loss"] = max(0.0, -min(recent_returns))
        else:
            factors["daily_loss"] = 0.0
        
        # 3. Leverage ratio (from portfolio state)
        factors["leverage_ratio"] = portfolio_state.get("leverage_ratio", 0.0)
        
        # 4. Volatility (from belief state or market data)
        factors["volatility"] = safe_get(belief_state, "volatility_estimate", 0.0) or safe_get(market_data, "volatility", 0.0)
        
        # 5. Liquidity score (inverse of volatility-adjusted spread)
        spread = safe_get(market_data, "spread_bps", 1.0)  # basis points
        base_liquidity = safe_get(belief_state, "liquidity_estimate", 0.5)
        # Higher spread = lower liquidity
        factors["liquidity_score"] = base_liquidity * np.exp(-spread / 50.0)  # Normalize spread impact
        
        # 6. Correlation risk (would need portfolio analysis)
        # Simplified: based on belief state regime uncertainty
        # Check for string value in regime_entropy
        regime_entropy_raw = safe_get(belief_state, "entropy", 0.0)
        if isinstance(regime_entropy_raw, str):
            # Try to parse if it's a string
            try:
                regime_entropy = float(regime_entropy_raw)
            except:
                regime_entropy = 0.0
                logger.warning(f"Could not parse regime_entropy string: {regime_entropy_raw[:50]}")
        else:
            regime_entropy = regime_entropy_raw
            
        max_entropy = np.log(8)  # Assuming 8 regime types
        factors["correlation_risk"] = min(regime_entropy / max_entropy, 1.0) if max_entropy > 0 else 0.0
        
        # 7. Concentration risk (from current positions)
        if current_positions and isinstance(current_positions, dict) and len(current_positions) > 0:
            try:
                total_value = sum(
                    abs(pos.get("quantity", 0) * pos.get("avg_price", 0)) 
                    for pos in current_positions.values()
                    if isinstance(pos, dict)
                )
                if total_value > 0:
                    max_position_value = max(
                        abs(pos.get("quantity", 0) * pos.get("avg_price", 0)) 
                        for pos in current_positions.values()
                        if isinstance(pos, dict)
                    )
                    factors["concentration_risk"] = max_position_value / total_value
                else:
                    factors["concentration_risk"] = 0.0
            except Exception as e:
                logger.error(f"Error computing concentration_risk: {e}")
                factors["concentration_risk"] = 0.0
        else:
            factors["concentration_risk"] = 0.0
        
        # 9. Epistemic Squelch (Model Uncertainty Check)
        # If the model is 'guessing' (high epistemic uncertainty), we inflate the risk score
        epistemic = safe_get(belief_state, "epistemic_uncertainty", 0.0)
        if epistemic > 0.3:
            factors["epistemic_risk"] = epistemic
        else:
            factors["epistemic_risk"] = 0.0

        # 10. CVAR (Conditional Value at Risk) - Probabilistic Tail Modeling
        if recent_returns and len(recent_returns) >= 10:
            var_99, cvar_99 = self._compute_tail_risk(recent_returns)
            factors["var_99"] = var_99
            factors["cvar"] = cvar_99
        else:
            factors["var_99"] = 0.0
            factors["cvar"] = 0.0
        
        return factors

    
    def _compute_risk_manifold(self, risk_factors: Dict[str, float]) -> float:
        """
        Compute nonlinear risk manifold:
        Risk = Σ(w_i * f_i) + nonlinearity_factor * Σ(w_i * f_i)^2
        """
        # Linear component: weighted sum of risk factors
        linear_risk = 0.0
        for factor_name, weight in self.risk_weights.items():
            factor_value = risk_factors.get(factor_name, 0.0)
            linear_risk += weight * factor_value
         
        # Nonlinear component: enhances risk sensitivity
        nonlinear_risk = self.nonlinearity_factor * (linear_risk ** 2)
         
        # Apply risk sensitivity scaling
        total_risk = self.risk_sensitivity * (linear_risk + nonlinear_risk)
         
        # Ensure bounds [0, 1]
        return np.clip(total_risk, 0.0, 1.0)
    
    def _determine_risk_level(self, risk_factors: Dict[str, float]) -> RiskLevel:
        """Determine risk level based on LVR-style protection thresholds"""
        # Check each risk factor against thresholds
        drawdown = risk_factors.get("drawdown", 0.0)
        daily_loss = risk_factors.get("daily_loss", 0.0)
        leverage = risk_factors.get("leverage_ratio", 0.0)
        
        # Check for leverage-specific risks first (for leveraged trading)
        if leverage >= self.leverage_critical:
            return RiskLevel.LEVEL_4_CRITICAL
        elif leverage >= self.leverage_danger:
            return RiskLevel.LEVEL_3_DANGER
        elif leverage >= self.leverage_warning:
            return RiskLevel.LEVEL_2_WARNING
        
        # Level 4: Critical (manual intervention)
        if (drawdown >= self.drawdown_critical or 
            daily_loss >= self.daily_loss_critical or 
            leverage >= self.leverage_critical):
            return RiskLevel.LEVEL_4_CRITICAL
        
        # Level 3: Danger (close all positions)
        if (drawdown >= self.drawdown_danger or 
            daily_loss >= self.daily_loss_danger or 
            leverage >= self.leverage_danger):
            return RiskLevel.LEVEL_3_DANGER
        
        # Level 2: Warning (restrict trading)
        if (drawdown >= self.drawdown_warning or 
            daily_loss >= self.daily_loss_warning or 
            leverage >= self.leverage_warning):
            return RiskLevel.LEVEL_2_WARNING
        
        # Level 1: Caution (reduce size)
        # Also check other factors that might warrant caution
        volatility = risk_factors.get("volatility", 0.0)
        liquidity = risk_factors.get("liquidity_score", 0.0)
        concentration = risk_factors.get("concentration_risk", 0.0)
        correlation = risk_factors.get("correlation_risk", 0.0)
        
        if (drawdown > 0.02 or daily_loss > 0.015 or leverage > 0.25 or
            volatility > 0.3 or liquidity < 0.3 or 
            concentration > 0.25 or correlation > 0.5):
            return RiskLevel.LEVEL_1_CAUTION
        
        # Level 0: Normal
        return RiskLevel.LEVEL_0_NORMAL
    
    def _compute_risk_gradient(self, risk_factors: Dict[str, float], belief_state: Dict) -> np.ndarray:
        """
        Compute risk gradient ∇R - how risk changes with trading actions
        This informs the aggression controller about risk sensitivity
        """
        # Gradient components: [∂R/∂aggression, ∂R/∂position_size, ...]
        # For simplicity, we'll compute a scalar gradient representing overall risk sensitivity
        
        # Base gradient increases with most risk factors
        base_gradient = (
            0.1 * risk_factors.get("drawdown", 0.0) +
            0.1 * risk_factors.get("daily_loss", 0.0) +
            0.15 * risk_factors.get("leverage_ratio", 0.0) +
            0.2 * risk_factors.get("volatility", 0.0) +
            0.1 * (1.0 - risk_factors.get("liquidity_score", 0.0)) +  # Inverse liquidity
            0.15 * risk_factors.get("correlation_risk", 0.0) +
            0.1 * risk_factors.get("concentration_risk", 0.0)
        )
        
        # Modulate by belief state uncertainty (more uncertainty = more cautious)
        total_uncertainty = (
            belief_state.get("aleatoric_uncertainty", 0.0) + 
            belief_state.get("epistemic_uncertainty", 0.0)
        )
        uncertainty_factor = 1.0 + total_uncertainty  # Higher uncertainty = higher gradient
        
        # Modulate by aggression level (more aggressive = more sensitive to risk increases)
        aggression_factor = 1.0 + 0.3 * belief_state.get("aggression_level", 0.5)
        
        # Risk gradient as scalar (would be vector in full implementation)
        gradient_scalar = base_gradient * uncertainty_factor * aggression_factor
        
        # Return as numpy array for compatibility
        return np.array([gradient_scalar])
    
    def _determine_protective_action(self, risk_level: RiskLevel, risk_factors: Dict[str, float]) -> str:
        """Determine protective action based on risk level and factors"""
        # Calculate starting risk score
        risk_score = risk_level.value
        
        # REGIME ADAPTIVE RISK: Reduce leverage in high volatility/crisis regimes
        # Safely access regime from risk_factors
        regime = risk_factors.get("regime", "NORMAL")
        volatility = risk_factors.get("volatility", 0)
        if regime == "CRISIS" or volatility > 0.6:
            # Increase risk score for volatile markets
            risk_score += 0.3
            self.logger.warning(f"Risk score increased by 0.3 due to high volatility/crisis regime")
        
        # Leverage margin call protection
        leverage_ratio = risk_factors.get("leverage_ratio", 0.0)
        if leverage_ratio >= self.leverage_critical:
            return "LIQUIDATION_RISK"  # Immediate liquidation risk at max leverage
        elif leverage_ratio >= self.leverage_danger:
            return "REDUCE_LEVERAGE"  # Reduce leverage immediately
        
        # Check for other critical risks
        if risk_level == RiskLevel.LEVEL_4_CRITICAL:
            return "MANUAL_INTERVENTION"
        elif risk_level == RiskLevel.LEVEL_3_DANGER:
            return "CLOSE_ALL_HALT"
        elif risk_level == RiskLevel.LEVEL_2_WARNING:
            return "REDUCE_SIZE"
        elif risk_level == RiskLevel.LEVEL_1_CAUTION:
            return "CAUTION"
        else:
            return "NONE"
    
    def calculate_portfolio_leverage(self, portfolio_value: float, positions: Dict[str, float], prices: Dict[str, float]) -> float:
        """Calculate actual portfolio leverage from positions"""
        if portfolio_value <= 0:
            return 0.0
        
        total_exposure = 0.0
        for symbol, position_size in positions.items():
            price = prices.get(symbol, 0.0)
            if price > 0:
                position_value = abs(position_size * price)
                total_exposure += position_value
        
        return total_exposure / portfolio_value
    
    def _compute_risk_factor_contributions(
        self, 
        risk_factors: Dict[str, float]
    ) -> Dict[str, float]:
        """Compute each risk factor's contribution to overall risk"""
        contributions = {}
        total_weighted_risk = 0.0
        
        # Calculate weighted contributions
        for factor_name, weight in self.risk_weights.items():
            factor_value = risk_factors.get(factor_name, 0.0)
            contribution = weight * factor_value
            contributions[factor_name] = contribution
            total_weighted_risk += contribution
        
        # Normalize to show percentage contributions
        if total_weighted_risk > 0:
            for factor_name in contributions:
                contributions[factor_name] = (contributions[factor_name] / total_weighted_risk) * 100.0
        
        return contributions
    
    def calculate_uncertainty_stop_loss(
        self,
        entry_price: float,
        action: str,
        aleatoric_uncertainty: float,
        multiplier: float = 2.0
    ) -> float:
        """
        Compute a stop-loss price based on the noise floor (aleatoric uncertainty).
        The stop is set to 2x the estimated irreducible noise.
        """
        # Aleatoric uncertainty represents the standard deviation of noise
        # Stop distance = price * (uncertainty * multiplier)
        stop_distance = entry_price * (aleatoric_uncertainty * multiplier)
        
        if action == "BUY":
            return entry_price - stop_distance
        elif action == "SELL":
            return entry_price + stop_distance
        return entry_price
    
    def _compute_tail_risk(self, recent_returns: Optional[List[float]]) -> Tuple[float, float]:
        """
        Compute Value at Risk (VaR) and Conditional Value at Risk (CVaR)
        using historical simulation.
        """
        if not recent_returns or len(recent_returns) < 30:
            return 0.0, 0.0
        
        returns = np.sort(recent_returns)
        
        # 99% VaR (1% quantile)
        var_99_idx = int(0.01 * len(returns))
        var_99 = abs(returns[var_99_idx]) if var_99_idx < len(returns) else 0.0
        
        # CVaR (Expected Shortfall) - Mean of returns below VaR
        tail_losses = returns[:var_99_idx + 1]
        cvar_99 = abs(np.mean(tail_losses)) if tail_losses else var_99
        
        return var_99, cvar_99
    
    def get_risk_trends(self) -> Dict[str, Dict]:
        """Get trend analysis for each risk factor"""
        trends = {}
        for factor_name, history in self.risk_history.items():
            if len(history) >= 2:
                recent_avg = np.mean(history[-10:]) if len(history) >= 10 else np.mean(history)
                older_avg = np.mean(history[-20:-10]) if len(history) >= 20 else np.mean(history[:len(history)//2]) if len(history) >= 2 else history[0] if history else 0.0
                
                if older_avg != 0:
                    change_pct = ((recent_avg - older_avg) / abs(older_avg)) * 100
                else:
                    change_pct = 0.0 if recent_avg == 0 else 100.0
                
                trends[factor_name] = {
                    "current": recent_avg,
                    "change_percent": change_pct,
                    "trend": "increasing" if change_pct > 5 else "decreasing" if change_pct < -5 else "stable",
                    "samples": len(history)
                }
            else:
                trends[factor_name] = {
                    "current": history[0] if history else 0.0,
                    "change_percent": 0.0,
                    "trend": "insufficient_data",
                    "samples": len(history)
                }
        
        return trends
    
    def run_stress_test(
        self,
        current_positions: Dict[str, float],
        current_prices: Dict[str, float],
        stress_scenarios: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Run stress tests on current portfolio (Phase 5.2 - 10/10 Upgrade).
        
        Args:
            current_positions: Dict of symbol -> quantity
            current_prices: Dict of symbol -> current price
            stress_scenarios: List of stress scenarios (uses defaults if None)
            
        Returns:
            Dictionary with stress test results
        """
        if stress_scenarios is None:
            stress_scenarios = [
                {"name": "Market Crash (-20%)", "shock_pct": -0.20, "vol_multiplier": 3.0},
                {"name": "Moderate Decline (-10%)", "shock_pct": -0.10, "vol_multiplier": 2.0},
                {"name": "Slight Decline (-5%)", "shock_pct": -0.05, "vol_multiplier": 1.5},
                {"name": "Liquidity Crisis", "shock_pct": -0.15, "vol_multiplier": 5.0, "liquidity_shock": 0.2},
                {"name": "Flash Crash (-30%)", "shock_pct": -0.30, "vol_multiplier": 10.0},
            ]
        
        results = {"scenarios": [], "portfolio_value": 0.0, "worst_case_loss": 0.0}
        
        # Calculate current portfolio value
        portfolio_value = 0.0
        for symbol, qty in current_positions.items():
            price = current_prices.get(symbol, 0.0)
            portfolio_value += abs(qty * price)
        results["portfolio_value"] = portfolio_value
        
        worst_loss = 0.0
        
        for scenario in stress_scenarios:
            scenario_name = scenario["name"]
            shock_pct = scenario["shock_pct"]
            vol_mult = scenario.get("vol_multiplier", 1.0)
            liquidity_shock = scenario.get("liquidity_shock", 1.0)
            
            # Calculate portfolio loss under stress
            total_loss = 0.0
            position_losses = {}
            
            for symbol, qty in current_positions.items():
                current_price = current_prices.get(symbol, 0.0)
                if current_price <= 0:
                    continue
                
                # Apply price shock
                stressed_price = current_price * (1 + shock_pct)
                
                # Calculate position P&L
                if qty > 0:  # LONG
                    position_pnl = (stressed_price - current_price) * qty
                else:  # SHORT
                    position_pnl = (current_price - stressed_price) * abs(qty)
                
                # Apply volatility multiplier (increases loss in stressed conditions)
                if position_pnl < 0:
                    position_pnl *= vol_mult
                
                # Apply liquidity shock (further adverse price movement)
                if position_pnl < 0 and liquidity_shock < 1.0:
                    position_pnl *= (2.0 - liquidity_shock)  # Amplify losses
                
                position_losses[symbol] = {
                    "quantity": qty,
                    "current_price": current_price,
                    "stressed_price": stressed_price,
                    "pnl": position_pnl,
                }
                total_loss += position_pnl
            
            scenario_result = {
                "scenario": scenario_name,
                "portfolio_loss": total_loss,
                "portfolio_loss_pct": total_loss / portfolio_value if portfolio_value > 0 else 0,
                "positions": position_losses,
            }
            results["scenarios"].append(scenario_result)
            
            if total_loss < worst_loss:
                worst_loss = total_loss
        
        results["worst_case_loss"] = worst_loss
        results["worst_case_loss_pct"] = worst_loss / portfolio_value if portfolio_value > 0 else 0
        
        self.logger.warning(f"Stress test complete. Worst case loss: {worst_loss:.2f} ({results['worst_case_loss_pct']*100:.1f}%)")
        return results
    
    def calculate_max_drawdown(self, equity_curve: List[float]) -> Dict[str, float]:
        """
        Calculate maximum drawdown from equity curve (Phase 5.1).
        
        Args:
            equity_curve: List of portfolio values over time
            
        Returns:
            Dict with max_drawdown, max_drawdown_pct, and duration
        """
        if not equity_curve or len(equity_curve) < 2:
            return {"max_drawdown": 0.0, "max_drawdown_pct": 0.0, "max_duration": 0}
        
        peak = equity_curve[0]
        max_dd = 0.0
        max_dd_pct = 0.0
        current_dd_start = 0
        max_dd_duration = 0
        
        for i, value in enumerate(equity_curve):
            if value > peak:
                peak = value
                current_dd_start = i
            else:
                dd = peak - value
                dd_pct = dd / peak if peak > 0 else 0
                
                if dd > max_dd:
                    max_dd = dd
                    max_dd_pct = dd_pct
                    max_dd_duration = i - current_dd_start
        
        return {
            "max_drawdown": max_dd,
            "max_drawdown_pct": max_dd_pct,
            "max_duration": max_dd_duration,
        }

# Example usage and testing
if __name__ == "__main__":
    import time
    
    # Create unified risk manager
    risk_manager = RiskManifold()
    
    print("Unified Risk Management System Demo:")
    print("=" * 40)
    
    # Simulate different market conditions
    scenarios = [
        {
            "name": "Normal Market Conditions",
            "belief_state": {
                "expected_return": 0.001,
                "expected_return_uncertainty": 0.0005,
                "aleatoric_uncertainty": 0.001,
                "epistemic_uncertainty": 0.0008,
                "regime_probabilities": [0.1, 0.2, 0.4, 0.2, 0.05, 0.03, 0.01, 0.01],
                "volatility_estimate": 0.12,
                "liquidity_estimate": 0.8,
                "drawdown": 0.02,
                "entropy": 0.6
            },
            "portfolio_state": {
                "drawdown": 0.02,
                "daily_pnl": 0.005,
                "leverage_ratio": 0.3,
                "total_value": 100000.0
            },
            "market_data": {
                "volatility": 0.12,
                "spread_bps": 1.5,
                "liquidity": 0.7
            },
            "recent_returns": [0.001, -0.0005, 0.002, -0.001, 0.0015] * 4  # 20 returns
        },
        {
            "name": "Elevated Risk Conditions",
            "belief_state": {
                "expected_return": 0.0005,
                "expected_return_uncertainty": 0.001,
                "aleatoric_uncertainty": 0.002,
                "epistemic_uncertainty": 0.0015,
                "regime_probabilities": [0.05, 0.1, 0.2, 0.3, 0.2, 0.1, 0.03, 0.02],
                "volatility_estimate": 0.25,
                "liquidity_estimate": 0.5,
                "drawdown": 0.06,
                "entropy": 1.2
            },
            "portfolio_state": {
                "drawdown": 0.06,
                "daily_pnl": -0.01,
                "leverage_ratio": 0.6,
                "total_value": 95000.0
            },
            "market_data": {
                "volatility": 0.25,
                "spread_bps": 3.0,
                "liquidity": 0.4
            },
            "recent_returns": [-0.002, 0.0005, -0.003, 0.001, -0.002] * 4  # 20 returns
        },
        {
            "name": "High Risk Conditions",
            "belief_state": {
                "expected_return": -0.001,
                "expected_return_uncertainty": 0.002,
                "aleatoric_uncertainty": 0.004,
                "epistemic_uncertainty": 0.002,
                "regime_probabilities": [0.02, 0.05, 0.1, 0.2, 0.3, 0.2, 0.1, 0.03],
                "volatility_estimate": 0.35,
                "liquidity_estimate": 0.3,
                "drawdown": 0.12,
                "entropy": 1.8
            },
            "portfolio_state": {
                "drawdown": 0.12,
                "daily_pnl": -0.025,
                "leverage_ratio": 0.85,
                "total_value": 80000.0
            },
            "market_data": {
                "volatility": 0.35,
                "spread_bps": 5.0,
                "liquidity": 0.2
            },
            "recent_returns": [-0.004, 0.001, -0.005, 0.002, -0.003] * 4  # 20 returns
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}:")
        print("-" * 30)
        
        # Assess risk
        assessment = risk_manager.assess_risk(
            belief_state=scenario["belief_state"],
            portfolio_state=scenario["portfolio_state"],
            market_data=scenario["market_data"],
            recent_returns=scenario["recent_returns"]
        )
        
        print(f"Risk Level: {assessment.risk_level.name} ({assessment.risk_level.value})")
        print(f"Risk Score: {assessment.risk_score:.3f}")
        print(f"CVaR: {assessment.cvar:.4f}")
        print(f"Volatility: {assessment.volatility:.3f}")
        print(f"Drawdown: {assessment.drawdown:.3f}")
        print(f"Leverage Ratio: {assessment.leverage_ratio:.3f}")
        print(f"Liquidity Score: {assessment.liquidity_score:.3f}")
        print(f"Concentration Risk: {assessment.concentration_risk:.3f}")
        print(f"Correlation Risk: {assessment.correlation_risk:.3f}")
        print(f"Protective Action: {assessment.protective_action}")
        print(f"Risk Gradient: [{assessment.risk_gradient[0]:.4f}]")
        
        # Show top risk factor contributions
        if assessment.metadata.get("risk_factor_contributions"):
            print("Top Risk Contributions:")
            contributions = assessment.metadata["risk_factor_contributions"]
            sorted_contributions = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
            for factor, pct in sorted_contributions[:3]:  # Top 3
                print(f"  {factor}: {pct:.1f}%")
        
        time.sleep(0.1)
    
    # Show risk trends
    print("\nRisk Trends:")
    print("-" * 20)
    trends = risk_manager.get_risk_trends()
    for factor, trend_info in trends.items():
        if trend_info["samples"] > 0:
            print(f"{factor}: {trend_info['trend']} ({trend_info['change_percent']:+.1f}%)")


class MicroFlexRiskManager:
    """
    Micro-Flex Risk Manager (Phase 2 - Micro-Flex Plan)
    Scales from $10 to $10M with intelligent position sizing.
    Implements tiered Kelly-scaling based on account size.
    Enhanced with correlation calculation and portfolio heat monitoring.
    """
    
    # Correlation matrix for major assets (simplified)
    # In production, this would be calculated from historical price data
    ASSET_CORRELATIONS = {
        'BTCUSDT': {'ETHUSDT': 0.85, 'SOLUSDT': 0.65, 'BNBUSDT': 0.70, 'XRPUSDT': 0.45, 'ADAUSDT': 0.50},
        'ETHUSDT': {'BTCUSDT': 0.85, 'SOLUSDT': 0.70, 'BNBUSDT': 0.65, 'XRPUSDT': 0.40, 'ADAUSDT': 0.55},
        'SOLUSDT': {'BTCUSDT': 0.65, 'ETHUSDT': 0.70, 'BNBUSDT': 0.60, 'XRPUSDT': 0.35, 'ADAUSDT': 0.45},
        'BNBUSDT': {'BTCUSDT': 0.70, 'ETHUSDT': 0.65, 'SOLUSDT': 0.60, 'XRPUSDT': 0.50, 'ADAUSDT': 0.48},
        'XRPUSDT': {'BTCUSDT': 0.45, 'ETHUSDT': 0.40, 'SOLUSDT': 0.35, 'BNBUSDT': 0.50, 'ADAUSDT': 0.70},
        'ADAUSDT': {'BTCUSDT': 0.50, 'ETHUSDT': 0.55, 'SOLUSDT': 0.45, 'BNBUSDT': 0.48, 'XRPUSDT': 0.70},
    }
    
    # Sector classification for diversification
    ASSET_SECTORS = {
        'BTCUSDT': 'store_of_value',
        'ETHUSDT': 'smart_contract',
        'SOLUSDT': 'smart_contract',
        'BNBUSDT': 'exchange',
        'XRPUSDT': 'payment',
        'ADAUSDT': 'smart_contract',
        'DOGEUSDT': 'payment',
        'MATICUSDT': 'scaling',
        'LINKUSDT': 'infrastructure',
        'DOTUSDT': 'interoperability',
        'AVAXUSDT': 'smart_contract',
        'UNIUSDT': 'defi',
        'ATOMUSDT': 'interoperability',
        'LTCUSDT': 'payment',
        'ETCUSDT': 'smart_contract',
    }
    
    def __init__(self, account_balance: float = 10.0):
        self.balance = account_balance
        self.min_position_value = 10.0  # $10 minimum notional
        
        # Account tier definitions
        self.tiers = {
            'micro': {'min': 10, 'max': 100, 'kelly': 0.50, 'max_leverage': 25},
            'small': {'min': 100, 'max': 1000, 'kelly': 0.25, 'max_leverage': 20},
            'medium': {'min': 1000, 'max': 100000, 'kelly': 0.10, 'max_leverage': 15},
            'large': {'min': 100000, 'max': float('inf'), 'kelly': 0.05, 'max_leverage': 10}
        }
        
        self.current_tier = self._get_tier(account_balance)
        
        # Confidence-based leverage (within user 15x-25x constraint)
        self.confidence_leverage = {
            'high': 25,    # >0.75 confidence
            'medium': 20,  # 0.60-0.75 confidence
            'low': 15      # <0.60 confidence (minimum)
        }
        
        # Portfolio heat tracking
        self.open_positions = {}  # symbol -> {quantity, entry_price, side, timestamp}
        self.portfolio_heat = 0.0  # 0.0 to 1.0
        self.max_positions = 3  # Max concurrent positions
        self.max_portfolio_heat = 0.80  # Maximum heat before rejecting trades
        self.correlation_limit = 0.60  # Max correlation exposure (BTC/ETH)
        
    def calculate_correlation_risk(self, new_symbol: str) -> float:
        """
        Calculate correlation risk of adding a new position.
        
        Args:
            new_symbol: Symbol of the proposed new position
            
        Returns:
            Correlation risk score (0.0 to 1.0)
        """
        if not self.open_positions:
            return 0.0  # No existing positions = no correlation risk
        
        total_correlation = 0.0
        count = 0
        
        for existing_symbol in self.open_positions.keys():
            # Get correlation from matrix, default to 0.3 if not found
            corr = self.ASSET_CORRELATIONS.get(new_symbol, {}).get(existing_symbol, 0.3)
            total_correlation += corr
            count += 1
        
        avg_correlation = total_correlation / count if count > 0 else 0.0
        
        # Check BTC/ETH combined exposure (only if we have BTC/ETH positions)
        btc_eth_exposure = 0.0
        total_exposure = 0.0
        
        for symbol, pos in self.open_positions.items():
            pos_value = abs(pos['quantity'] * pos['entry_price'])
            if pos_value == 0:
                pos_value = self.balance * 0.10  # Estimate if not set
            total_exposure += pos_value
            
            if symbol in ['BTCUSDT', 'ETHUSDT']:
                btc_eth_exposure += pos_value
        
        # Only check BTC/ETH ratio if we have BTC/ETH positions
        if btc_eth_exposure > 0 and total_exposure > 0:
            btc_eth_ratio = btc_eth_exposure / total_exposure
        else:
            btc_eth_ratio = 0.0
        
        # Return average correlation with existing positions
        # BTC/ETH ratio is checked separately in can_open_position()
        return avg_correlation
    
    def calculate_portfolio_heat(self) -> float:
        """
        Calculate current portfolio heat (0.0 to 1.0).
        Considers: number of positions, correlation, concentration.
        
        Returns:
            Portfolio heat score
        """
        if not self.open_positions:
            self.portfolio_heat = 0.0
            return 0.0
        
        # Factor 1: Position count (3 positions = 0.6 heat)
        position_count_heat = len(self.open_positions) / self.max_positions * 0.6
        
        # Factor 2: Correlation heat
        correlation_heat = 0.0
        symbols = list(self.open_positions.keys())
        if len(symbols) >= 2:
            total_corr = 0.0
            pairs = 0
            for i in range(len(symbols)):
                for j in range(i + 1, len(symbols)):
                    corr = self.ASSET_CORRELATIONS.get(symbols[i], {}).get(symbols[j], 0.3)
                    total_corr += corr
                    pairs += 1
            correlation_heat = (total_corr / pairs) * 0.3 if pairs > 0 else 0.0
        
        # Factor 3: Concentration heat (single asset > 50% = max heat)
        total_value = sum(abs(pos['quantity'] * pos['entry_price']) 
                         for pos in self.open_positions.values())
        max_position_value = max(abs(pos['quantity'] * pos['entry_price']) 
                                for pos in self.open_positions.values())
        concentration_heat = (max_position_value / total_value) * 0.1 if total_value > 0 else 0.0
        
        self.portfolio_heat = min(1.0, position_count_heat + correlation_heat + concentration_heat)
        return self.portfolio_heat
    
    def add_position(self, symbol: str, quantity: float, entry_price: float, side: str = "BUY"):
        """Add a position to tracking."""
        self.open_positions[symbol] = {
            'quantity': quantity,
            'entry_price': entry_price,
            'side': side,
            'timestamp': time.time()
        }
        self.calculate_portfolio_heat()  # Recalculate heat
    
    def remove_position(self, symbol: str):
        """Remove a position from tracking."""
        if symbol in self.open_positions:
            del self.open_positions[symbol]
            self.calculate_portfolio_heat()  # Recalculate heat
    
    def can_open_position(self, symbol: str, max_correlation: float = 0.60) -> tuple:
        """
        Check if we can open a new position.
        
        Args:
            symbol: Proposed symbol
            max_correlation: Maximum allowed correlation
            
        Returns:
            (can_open: bool, reason: str, adjusted_kelly: float)
        """
        # Check max positions
        if len(self.open_positions) >= self.max_positions:
            return False, f"Max positions reached ({self.max_positions})", 0.0
        
        # Check portfolio heat
        current_heat = self.calculate_portfolio_heat()
        if current_heat >= self.max_portfolio_heat:
            return False, f"Portfolio heat too high ({current_heat:.2f})", 0.0
        
        # Check correlation risk - but allow if it's the SECOND position
        correlation_risk = self.calculate_correlation_risk(symbol)
        
        # Allow up to 2 positions even with high correlation
        # Only block if we already have 2+ positions AND correlation is too high
        if len(self.open_positions) >= 2 and correlation_risk > max_correlation:
            return False, f"Correlation risk too high ({correlation_risk:.2f})", 0.0
        
        # Calculate adjusted Kelly based on heat
        tier_settings = self.tiers[self.current_tier]
        base_kelly = tier_settings['kelly']
        
        # Reduce Kelly as heat increases (heat=0.6 → 70% of base kelly)
        heat_adjustment = 1.0 - (current_heat * 0.5)
        adjusted_kelly = base_kelly * max(0.3, heat_adjustment)  # Minimum 30% of base
        
        # Diversification bonus for uncorrelated assets
        if correlation_risk < 0.40:
            adjusted_kelly *= 1.2  # 20% bonus for uncorrelated
        elif correlation_risk > 0.50 and len(self.open_positions) >= 2:
            adjusted_kelly *= 0.8  # 20% penalty for correlated
        
        return True, "OK", adjusted_kelly
    
    def _get_tier(self, balance: float) -> str:
        """Determine account tier based on balance."""
        if balance < 100:
            return 'micro'
        elif balance < 1000:
            return 'small'
        elif balance < 100000:
            return 'medium'
        else:
            return 'large'
    
    def calculate_position_size(self, confidence: float, leverage: int = None,
                               current_price: float = 100.0,
                               volatility: float = 0.02,
                               liquidity: float = 1.0) -> Dict[str, Any]:
        """
        Calculate position size using Kelly-scaling tailored to account tier.
        Implements dynamic leverage optimization (Phase 3).
        
        Args:
            confidence: Signal confidence (0.0 to 1.0)
            leverage: Override leverage (must be 15-25 per user constraint)
            current_price: Current asset price
            volatility: Current market volatility (e.g., 0.02 = 2% daily)
            liquidity: Market liquidity score (0.0 to 1.0, 1.0 = full liquidity)
            
        Returns:
            Dictionary with position details
        """
        # Get tier settings
        tier_settings = self.tiers[self.current_tier]
        kelly_fraction = tier_settings['kelly']
        
        # Determine base leverage based on confidence or override
        if leverage is not None:
            # Enforce user constraint: 15x-25x
            base_leverage = max(15, min(25, leverage))
        else:
            if confidence >= 0.75:
                base_leverage = self.confidence_leverage['high']
            elif confidence >= 0.60:
                base_leverage = self.confidence_leverage['medium']
            else:
                base_leverage = self.confidence_leverage['low']
        
        # Phase 3: Dynamic Leverage Optimizer
        # Adjust leverage based on volatility (higher vol = reduce leverage)
        vol_adjustment = 1.0
        if volatility > 0.05:  # High volatility (>5% daily)
            vol_adjustment = 0.6  # Reduce to 60%
        elif volatility > 0.03:  # Medium volatility
            vol_adjustment = 0.8  # Reduce to 80%
        
        # Adjust leverage based on liquidity (lower liquidity = reduce leverage)
        liq_adjustment = 1.0
        if liquidity < 0.3:  # Very low liquidity
            liq_adjustment = 0.5  # Reduce to 50%
        elif liquidity < 0.6:  # Low liquidity
            liq_adjustment = 0.75  # Reduce to 75%
        
        # Apply adjustments (ensure stays within 15x-25x)
        actual_leverage = int(base_leverage * vol_adjustment * liq_adjustment)
        actual_leverage = max(15, min(25, actual_leverage))
        
        # Calculate position value
        position_value = self.balance * kelly_fraction * actual_leverage
        
        # Ensure minimum position value
        if position_value < self.min_position_value:
            position_value = self.min_position_value
        
        quantity = position_value / current_price
        
        return {
            "leverage": actual_leverage,
            "position_value": position_value,
            "quantity": quantity,
            "kelly_fraction": kelly_fraction,
            "tier": self.current_tier,
            "balance": self.balance,
            "vol_adjustment": vol_adjustment,
            "liq_adjustment": liq_adjustment,
            "base_leverage": base_leverage
        }
    
    def update_balance(self, new_balance: float):
        """Update account balance and recalculate tier."""
        self.balance = new_balance
        self.current_tier = self._get_tier(new_balance)
    
    def calculate_stop_loss(self, entry_price: float, side: str = "BUY") -> Dict[str, Any]:
        """
        Calculate dynamic stop-loss based on account tier and ATR.
        For micro accounts: 2% stop (aggressive)
        For large accounts: 0.5% stop (conservative)
        """
        if self.current_tier == 'micro':
            stop_pct = 0.02  # 2% stop
        elif self.current_tier == 'small':
            stop_pct = 0.015  # 1.5% stop
        elif self.current_tier == 'medium':
            stop_pct = 0.010  # 1% stop
        else:  # large
            stop_pct = 0.005  # 0.5% stop
        
        if side == "BUY":
            stop_price = entry_price * (1 - stop_pct)
        else:  # SELL (short)
            stop_price = entry_price * (1 + stop_pct)
        
        return {
            "stop_price": stop_price,
            "stop_pct": stop_pct,
            "risk_amount": self.balance * stop_pct
        }
    
    def should_trade(self, daily_loss: float, max_daily_loss_pct: float = 0.05) -> bool:
        """
        Check if trading should continue based on daily loss limits.
        CFA Standard III(C) - Suitability: Hard limits on daily losses.
        """
        daily_loss_limit = self.balance * max_daily_loss_pct
        
        if abs(daily_loss) >= daily_loss_limit:
            return False  # Stop trading for the day
        
        return True
    
    def detect_market_regime(self, prices: List[float], window: int = 20) -> Dict[str, Any]:
        """
        Detect market regime (Phase 4 - Micro-Flex Plan).
        Classifies as BULL/BEAR/SIDEWAYS with volatility level.
        
        Args:
            prices: List of recent prices (last 'window' prices)
            window: Lookback period for regime detection
            
        Returns:
            Dictionary with regime info and trading multipliers
        """
        if len(prices) < window:
            return {"regime": "UNKNOWN", "trade_multiplier": 1.0, "skip_trade": False}
        
        recent_prices = prices[-window:]
        
        # Calculate returns
        returns = [(recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1] 
                   for i in range(1, len(recent_prices))]
        
        # Calculate metrics
        avg_return = np.mean(returns)
        volatility = np.std(returns) * np.sqrt(365)  # Annualized
        
        # Determine regime
        if avg_return > 0.001:  # >0.1% daily
            if volatility > 0.05:  # >5% annualized vol
                regime = "BULL_HIGH_VOL"
            else:
                regime = "BULL_LOW_VOL"
        elif avg_return < -0.001:  # <-0.1% daily
            if volatility > 0.05:
                regime = "BEAR_HIGH_VOL"
            else:
                regime = "BEAR_LOW_VOL"
        else:
            regime = "SIDEWAYS"
        
        # Regime-based multipliers (Phase 4)
        regime_multipliers = {
            "BULL_LOW_VOL": {"lev_mult": 1.2, "pos_mult": 1.5, "skip": False},
            "BULL_HIGH_VOL": {"lev_mult": 0.8, "pos_mult": 1.0, "skip": False},
            "BEAR_LOW_VOL": {"lev_mult": 1.0, "pos_mult": 1.2, "skip": False},
            "BEAR_HIGH_VOL": {"lev_mult": 0.6, "pos_mult": 0.5, "skip": True},  # Skip trades
            "SIDEWAYS": {"lev_mult": 1.1, "pos_mult": 1.3, "skip": False},
            "UNKNOWN": {"lev_mult": 1.0, "pos_mult": 1.0, "skip": False}
        }
        
        mults = regime_multipliers.get(regime, regime_multipliers["UNKNOWN"])
        
        return {
            "regime": regime,
            "avg_return": float(avg_return),
            "volatility": float(volatility),
            "leverage_multiplier": mults["lev_mult"],
            "position_multiplier": mults["pos_mult"],
            "skip_trade": mults["skip"],
            "confidence_threshold": 0.75 if "HIGH_VOL" in regime else 0.60
        }
    
    def should_trade_regime(self, regime_info: Dict[str, Any], 
                            expected_value: float = 0.0) -> bool:
        """
        Determine if we should trade based on regime + expected value.
        Phase 4: Skip trades when regime is unfavorable.
        """
        # Skip if regime says so (BEAR_HIGH_VOL)
        if regime_info.get("skip_trade", False):
            return False
        
        # Skip if expected value too low
        if expected_value < 0.005:  # Less than 0.5% expected return
            return False
        
        return True


class AutoCompoundingEngine:
    """
    Auto-Compounding Engine (Phase 5 - Micro-Flex Plan).
    Automatically compounds profits and withdraws at thresholds.
    Implements CFA Standard III(C) - Suitability (withdrawal protection).
    """
    
    def __init__(self, starting_balance: float = 10.0,
                 withdraw_thresholds: List[float] = None):
        self.balance = starting_balance
        self.starting_balance = starting_balance
        
        # Default withdrawal thresholds
        if withdraw_thresholds is None:
            self.withdraw_thresholds = [100.0, 1000.0, 10000.0, 100000.0]
        else:
            self.withdraw_thresholds = sorted(withdraw_thresholds)
        
        self.withdrawn = 0.0
        self.daily_returns = []
        self.max_balance = starting_balance
        self.max_drawdown_pct = 0.0
        
    def compound(self, daily_return: float) -> Dict[str, Any]:
        """
        Compound the balance by daily return.
        
        Args:
            daily_return: Decimal return (0.01 = 1%)
            
        Returns:
            Dictionary with compounding results
        """
        # Apply return
        self.balance *= (1 + daily_return)
        
        # Track daily returns
        self.daily_returns.append(daily_return)
        if len(self.daily_returns) > 90:  # Keep 90 days
            self.daily_returns.pop(0)
        
        # Update max balance and drawdown
        if self.balance > self.max_balance:
            self.max_balance = self.balance
        
        current_drawdown = (self.max_balance - self.balance) / self.max_balance
        if current_drawdown > self.max_drawdown_pct:
            self.max_drawdown_pct = current_drawdown
        
        # Check for withdrawal
        withdraw_amount = self._check_withdrawal()
        
        return {
            "balance": self.balance,
            "daily_return": daily_return,
            "withdraw_amount": withdraw_amount,
            "total_withdrawn": self.withdrawn,
            "max_drawdown_pct": self.max_drawdown_pct,
            "days_compounded": len(self.daily_returns)
        }
    
    def _check_withdrawal(self) -> float:
        """
        Check if we should withdraw profits at thresholds.
        Only withdraw profits above starting balance + thresholds.
        """
        for threshold in self.withdraw_thresholds:
            if self.balance >= threshold and self.balance - self.withdrawn > threshold:
                # Withdraw to the threshold
                withdraw_amount = self.balance - threshold
                if withdraw_amount > 0:
                    self.balance -= withdraw_amount
                    self.withdrawn += withdraw_amount
                    print(f"WITHDRAWAL: ${withdraw_amount:.2f} (balance now ${self.balance:.2f})")
                    return withdraw_amount
        return 0.0
    
    def calculate_projection(self, days: int = 30, 
                             expected_daily_return: float = 0.08) -> Dict[str, Any]:
        """
        Project future balance based on expected daily return.
        
        Args:
            days: Number of days to project
            expected_daily_return: Expected daily return (0.08 = 8%)
            
        Returns:
            Dictionary with projection results
        """
        projection = []
        balance = self.balance
        
        for day in range(1, days + 1):
            balance *= (1 + expected_daily_return)
            withdraw_at = None
            
            for threshold in self.withdraw_thresholds:
                if balance >= threshold and balance - (self.withdrawn + sum(p.get('withdraw', 0) for p in projection)) > threshold:
                    withdraw = balance - threshold
                    balance = threshold
                    self.withdrawn += withdraw
                    withdraw_at = withdraw
            
            projection.append({
                "day": day,
                "balance": balance,
                "return": expected_daily_return,
                "withdraw": withdraw_at or 0.0
            })
        
        return {
            "starting_balance": self.balance,
            "expected_daily_return": expected_daily_return,
            "projection": projection,
            "final_balance": projection[-1]["balance"] if projection else self.balance,
            "total_return_pct": ((projection[-1]["balance"] if projection else self.balance) / self.balance - 1) * 100
        }