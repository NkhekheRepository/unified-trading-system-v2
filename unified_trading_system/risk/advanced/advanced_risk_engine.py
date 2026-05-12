"""
Advanced Risk Management Module for Trading System
Implements portfolio VaR, correlation risk, and stress testing
"""

import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from scipy import stats
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class RiskMetrics:
    """Comprehensive risk metrics"""
    var_95: float           # Value at Risk at 95% confidence
    var_99: float           # Value at Risk at 99% confidence
    cvar_95: float          # Conditional VaR
    max_drawdown: float      # Maximum drawdown
    volatility: float       # Portfolio volatility
    sharpe_ratio: float     # Risk-adjusted return
    beta: float            # Portfolio beta
    correlation_risk: float  # Correlation-based risk
    liquidity_risk: float     # Liquidity risk score
    stress_impact: float      # Impact under stressed conditions

class PortfolioRiskAnalyzer:
    """
    Advanced portfolio risk analysis with VaR, correlation, and stress testing
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        
        self.returns_history = []
        self.position_history = []
        self.price_history = {}
        
        self.correlation_matrix = None
        self.covariance_matrix = None
        
        self.stress_scenarios = self._initialize_stress_scenarios()
        
    def _default_config(self) -> Dict:
        return {
            'var_confidence_levels': [0.95, 0.99],
            'lookback_period': 252,  # ~1 year of trading days
            'min_periods_for_calc': 30,
            'update_frequency': 'daily',
            'enable_correlation': True,
            'enable_stress_testing': True,
            'stress_test_multipliers': {
                'market_crash': 0.8,
                'volatility_spike': 2.0,
                'liquidity_crisis': 0.5,
                'correlation_breakdown': 1.5
            }
        }
    
    def _initialize_stress_scenarios(self) -> Dict[str, Dict]:
        """
        Initialize predefined stress scenarios
        """
        return {
            'market_crash': {
                'description': '30% market decline',
                'price_impact': -0.30,
                'volatility_multiplier': 2.0,
                'liquidity_impact': 0.5
            },
            'volatility_spike': {
                'description': 'Volatility doubles',
                'price_impact': -0.10,
                'volatility_multiplier': 2.0,
                'liquidity_impact': 0.7
            },
            'liquidity_crisis': {
                'description': '50% liquidity reduction',
                'price_impact': -0.05,
                'volatility_multiplier': 1.5,
                'liquidity_impact': 0.5
            },
            'correlation_breakdown': {
                'description': 'Correlations increase',
                'price_impact': -0.15,
                'volatility_multiplier': 1.5,
                'liquidity_impact': 0.8
            },
            'inflation_shock': {
                'description': 'Sudden inflation',
                'price_impact': -0.20,
                'volatility_multiplier': 1.8,
                'liquidity_impact': 0.6
            }
        }
    
    def update_returns(self, portfolio_return: float, timestamp: Optional[float] = None):
        """
        Update portfolio returns history
        """
        self.returns_history.append({
            'return': portfolio_return,
            'timestamp': timestamp or datetime.now().timestamp()
        })
        
        # Keep only the needed history
        max_history = self.config['lookback_period']
        if len(self.returns_history) > max_history:
            self.returns_history = self.returns_history[-max_history:]
    
    def update_position(self, symbol: str, quantity: float, price: float):
        """
        Update position for correlation calculation
        """
        if symbol not in self.position_history:
            self.position_history.append({})
            self.price_history[symbol] = []
        
        self.position_history[-1][symbol] = quantity
        self.price_history[symbol].append(price)
        
        # Keep only needed history
        max_history = self.config['lookback_period']
        for symbol in self.price_history:
            if len(self.price_history[symbol]) > max_history:
                self.price_history[symbol] = self.price_history[symbol][-max_history:]
    
    def calculate_var(self, confidence_level: float = 0.95) -> Tuple[float, float]:
        """
        Calculate Value at Risk using historical simulation
        
        Returns:
            var: VaR as positive number (potential loss)
            var_method: Method used
        """
        if len(self.returns_history) < self.config['min_periods_for_calc']:
            return 0.0, "INSUFFICIENT_DATA"
        
        returns = np.array([r['return'] for r in self.returns_history])
        
        # Historical VaR
        var = -np.percentile(returns, (1 - confidence_level) * 100)
        
        return max(0, var), "HISTORICAL"
    
    def calculate_cvar(self, confidence_level: float = 0.95) -> float:
        """
        Calculate Conditional Value at Risk (Expected Shortfall)
        """
        if len(self.returns_history) < self.config['min_periods_for_calc']:
            return 0.0
        
        returns = np.array([r['return'] for r in self.returns_history])
        
        # Find returns worse than VaR
        var_threshold = -np.percentile(returns, (1 - confidence_level) * 100)
        tail_returns = returns[returns <= -var_threshold]
        
        if len(tail_returns) == 0:
            return abs(var_threshold)
        
        # CVaR is average of tail losses
        cvar = -np.mean(tail_returns)
        
        return max(0, cvar)
    
    def calculate_portfolio_volatility(self) -> float:
        """
        Calculate portfolio volatility (annualized)
        """
        if len(self.returns_history) < self.config['min_periods_for_calc']:
            return 0.0
        
        returns = np.array([r['return'] for r in self.returns_history])
        
        # Annualize (assuming daily returns)
        volatility = np.std(returns) * np.sqrt(252)
        
        return volatility
    
    def calculate_max_drawdown(self) -> float:
        """
        Calculate maximum drawdown from peak
        """
        if len(self.returns_history) < 2:
            return 0.0
        
        # Calculate cumulative returns
        cumulative = np.cumprod(1 + np.array([r['return'] for r in self.returns_history]))
        
        # Calculate running maximum
        running_max = np.maximum.accumulate(cumulative)
        
        # Calculate drawdown
        drawdown = (cumulative - running_max) / running_max
        
        # Return maximum drawdown (as positive number)
        return abs(np.min(drawdown)) if np.min(drawdown) < 0 else 0.0
    
    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """
        Calculate Sharpe ratio (annualized)
        """
        if len(self.returns_history) < self.config['min_periods_for_calc']:
            return 0.0
        
        returns = np.array([r['return'] for r in self.returns_history])
        
        # Annualized return and volatility
        mean_return = np.mean(returns) * 252
        volatility = np.std(returns) * np.sqrt(252)
        
        if volatility == 0:
            return 0.0
        
        sharpe = (mean_return - risk_free_rate) / volatility
        
        return sharpe
    
    def calculate_correlation_matrix(self) -> np.ndarray:
        """
        Calculate correlation matrix of positions
        """
        if not self.config['enable_correlation']:
            return np.eye(1)
        
        # Get all symbols with price history
        valid_symbols = []
        prices = []
        
        for symbol, price_list in self.price_history.items():
            if len(price_list) >= self.config['min_periods_for_calc']:
                valid_symbols.append(symbol)
                # Calculate returns
                price_array = np.array(price_list)
                returns = np.diff(price_array) / price_array[:-1]
                returns = np.insert(returns, 0, 0)  # Pad to same length
                prices.append(returns)
        
        if len(valid_symbols) < 2 or len(prices[0]) < self.config['min_periods_for_calc']:
            return np.eye(1) if len(valid_symbols) == 1 else np.eye(len(valid_symbols)) if valid_symbols else np.eye(1)
        
        # Calculate correlation matrix
        prices_array = np.array(prices).T
        correlation = np.corrcoef(prices_array)
        
        self.correlation_matrix = correlation
        
        return correlation
    
    def calculate_correlation_risk(self) -> float:
        """
        Calculate correlation-based risk score
        """
        if self.correlation_matrix is None:
            self.calculate_correlation_matrix()
        
        if self.correlation_matrix is None or len(self.correlation_matrix) < 2:
            return 0.0
        
        # Average absolute correlation (excluding diagonal)
        n = len(self.correlation_matrix)
        mask = ~np.eye(n, dtype=bool)
        avg_correlation = np.mean(np.abs(self.correlation_matrix[mask]))
        
        return avg_correlation
    
    def calculate_liquidity_risk(self, positions: Dict[str, float], 
                                avg_daily_volume: Dict[str, float]) -> float:
        """
        Calculate liquidity risk based on position sizes vs volume
        """
        if not positions or not avg_daily_volume:
            return 0.0
        
        liquidity_risks = []
        
        for symbol, position_value in positions.items():
            volume = avg_daily_volume.get(symbol, 0)
            
            if volume > 0:
                # Days to liquidate at 10% ADV
                adv = volume * 0.1
                days_to_liquidate = abs(position_value) / adv
                
                # Risk increases with days to liquidate
                if days_to_liquidate > 5:
                    risk = min(1.0, (days_to_liquidate - 5) / 20)  # Max out at 25 days
                else:
                    risk = 0.0
                
                liquidity_risks.append(risk)
        
        if not liquidity_risks:
            return 0.0
        
        # Return average liquidity risk
        return np.mean(liquidity_risks)
    
    def calculate_stress_impact(self, scenario_name: str, 
                               portfolio_value: float = 100000) -> float:
        """
        Calculate portfolio impact under stress scenario
        """
        if scenario_name not in self.stress_scenarios:
            logger.warning(f"Unknown stress scenario: {scenario_name}")
            return 0.0
        
        scenario = self.stress_scenarios[scenario_name]
        
        # Calculate impact
        price_impact = scenario['price_impact']
        
        # Impact = position * price change * volatility multiplier
        impact = portfolio_value * price_impact
        
        return impact
    
    def run_stress_tests(self, portfolio_value: float = 100000) -> Dict[str, float]:
        """
        Run all predefined stress tests
        """
        results = {}
        
        for scenario_name in self.stress_scenarios:
            impact = self.calculate_stress_impact(scenario_name, portfolio_value)
            results[scenario_name] = {
                'description': self.stress_scenarios[scenario_name]['description'],
                'impact': impact,
                'impact_pct': impact / portfolio_value if portfolio_value > 0 else 0
            }
        
        return results
    
    def get_comprehensive_risk_metrics(self, portfolio_value: float = 100000) -> RiskMetrics:
        """
        Calculate all risk metrics in one go
        """
        # VaR calculations
        var_95, _ = self.calculate_var(0.95)
        var_99, _ = self.calculate_var(0.99)
        
        # CVaR
        cvar_95 = self.calculate_cvar(0.95)
        
        # Other metrics
        volatility = self.calculate_portfolio_volatility()
        max_drawdown = self.calculate_max_drawdown()
        sharpe_ratio = self.calculate_sharpe_ratio()
        correlation_risk = self.calculate_correlation_risk()
        
        # Run worst stress test
        stress_results = self.run_stress_tests(portfolio_value)
        worst_scenario = max(stress_results.items(), key=lambda x: abs(x[1]['impact']))
        stress_impact = abs(worst_scenario[1]['impact'])
        
        return RiskMetrics(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            max_drawdown=max_drawdown,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            beta=0.0,  # Would need benchmark for real beta
            correlation_risk=correlation_risk,
            liquidity_risk=0.0,  # Would need position data for this
            stress_impact=stress_impact
        )
    
    def get_risk_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive risk report
        """
        metrics = self.get_comprehensive_risk_metrics()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'metrics': {
                'var_95': metrics.var_95,
                'var_99': metrics.var_99,
                'cvar_95': metrics.cvar_95,
                'max_drawdown': metrics.max_drawdown,
                'volatility': metrics.volatility,
                'sharpe_ratio': metrics.sharpe_ratio,
                'correlation_risk': metrics.correlation_risk,
                'stress_impact': metrics.stress_impact
            },
            'stress_tests': self.run_stress_tests(),
            'data_points': len(self.returns_history)
        }
        
        return report
    
    def save_risk_report(self, filepath: str):
        """
        Save risk report to file
        """
        report = self.get_risk_report()
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Risk report saved to {filepath}")
    
    def get_alert_thresholds(self) -> Dict[str, Tuple[float, str]]:
        """
        Get risk alert thresholds
        """
        return {
            'var_95': (0.05, 'WARNING'),
            'var_99': (0.10, 'CRITICAL'),
            'max_drawdown': (0.15, 'WARNING'),
            'volatility': (0.30, 'WARNING'),
            'sharpe_ratio': (0.5, 'WARNING'),
            'correlation_risk': (0.7, 'WARNING'),
        }
    
    def check_risk_alerts(self, portfolio_value: float = 100000) -> List[Dict]:
        """
        Check for risk threshold breaches
        """
        metrics = self.get_comprehensive_risk_metrics()
        thresholds = self.get_alert_thresholds()
        
        alerts = []
        
        # VaR alerts
        var_pct = metrics.var_95 / portfolio_value if portfolio_value > 0 else 0
        if var_pct > thresholds['var_95'][0]:
            alerts.append({
                'type': 'VaR_WARNING',
                'severity': thresholds['var_95'][1],
                'value': var_pct,
                'threshold': thresholds['var_95'][0],
                'message': f"VaR at 95% is {var_pct:.2%}"
            })
        
        # Drawdown alerts
        if metrics.max_drawdown > thresholds['max_drawdown'][0]:
            alerts.append({
                'type': 'DRAWDOWN_WARNING',
                'severity': thresholds['max_drawdown'][1],
                'value': metrics.max_drawdown,
                'threshold': thresholds['max_drawdown'][0],
                'message': f"Max drawdown is {metrics.max_drawdown:.2%}"
            })
        
        # Volatility alerts
        if metrics.volatility > thresholds['volatility'][0]:
            alerts.append({
                'type': 'VOLATILITY_WARNING',
                'severity': thresholds['volatility'][1],
                'value': metrics.volatility,
                'threshold': thresholds['volatility'][0],
                'message': f"Volatility is {metrics.volatility:.2%}"
            })
        
        # Sharpe alerts
        if metrics.sharpe_ratio < thresholds['sharpe_ratio'][0]:
            alerts.append({
                'type': 'SHARPE_WARNING',
                'severity': thresholds['sharpe_ratio'][1],
                'value': metrics.sharpe_ratio,
                'threshold': thresholds['sharpe_ratio'][0],
                'message': f"Sharpe ratio is {metrics.sharpe_ratio:.2f}"
            })
        
        return alerts

def create_portfolio_risk_analyzer(config: Optional[Dict] = None) -> PortfolioRiskAnalyzer:
    """
    Factory function to create portfolio risk analyzer
    """
    return PortfolioRiskAnalyzer(config)