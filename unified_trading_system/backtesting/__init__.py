"""
Backtesting Module for Unified Trading System
Contains walk-forward validation and performance analysis
"""

from backtesting.walk_forward import WalkForwardBacktester, ParameterOptimizer, create_walk_forward_backtester

__all__ = [
    'WalkForwardBacktester',
    'ParameterOptimizer',
    'create_walk_forward_backtester',
]

__version__ = '1.0.0'