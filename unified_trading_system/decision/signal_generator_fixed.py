#!/usr/bin/env python3
"""
Fixed signal generator with all 20 symbols and real price capability
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timezone

# Try to import optional dependencies
try:
    from sklearn.ensemble import RandomForestClassifier
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logging.warning("sklearn not available, some ML features disabled")

from .belief_state import BeliefState
from .signal_generator import TradingSignal

logger = logging.getLogger(__name__)


class SignalGenerator:
    def __init__(self, config: Dict):
        self.config = config
        
        # Core parameters
        self.min_confidence_threshold = self.config.get('min_confidence_threshold', 0.45)
        self.min_expected_return = self.config.get('min_expected_return', 0.001)
        self.max_position_size = self.config.get('max_position_size', 0.1)
        self.min_uncertainty = self.config.get('min_uncertainty', 0.08)
        self.max_uncertainty = self.config.get('max_uncertainty', 0.25)
        self.buy_bias = self.config.get('buy_bias', 0.02)
        
        # Symbol weights for all 20 futures symbols
        self.symbol_weights = self.config.get('symbol_weights', {
            'BTC/USDT': 1.0, 'ETH/USDT': 0.9, 'BNB/USDT': 0.8, 'SOL/USDT': 0.8,
            'ADA/USDT': 0.6, 'XRP/USDT': 0.6, 'DOGE/USDT': 0.6, 'MATIC/USDT': 0.6,
            'DOT/USDT': 0.7, 'AVAX/USDT': 0.7, 'LINK/USDT': 0.7, 'UNI/USDT': 0.6,
            'LTC/USDT': 0.7, 'BCH/USDT': 0.7, 'ATOM/USDT': 0.6, 'ETC/USDT': 0.6,
            'XLM/USDT': 0.5, 'ALGO/USDT': 0.5, 'VET/USDT': 0.5, 'FIL/USDT': 0.6
        })
        
        # ML models (simplified for this fix)
        self.models = {}
        self.feature_importance = {}
        
        logger.info("Signal Generator initialized with 20-symbol support")

    def generate_signals(self, market_data: Dict, belief_states: Dict[str, BeliefState]) -> List[TradingSignal]:
        """Generate trading signals for all symbols with real market data"""
        signals = []
        
        # Process each symbol that has belief state data
        for symbol, belief_state in belief_states.items():
            # Skip if no market data for this symbol
            if symbol not in market_data:
                continue
                
            # Get symbol-specific configuration
            symbol_weight = self.symbol_weights.get(symbol, 0.5)
            
            # Extract key metrics from belief state
            confidence = belief_state.confidence
            expected_return = belief_state.expected_return
            uncertainty = belief_state.uncertainty
            regime = belief_state.regime
            
            # Apply symbol weight to expected return
            weighted_expected_return = expected_return * symbol_weight
            
            # Check confidence threshold
            is_confident = confidence >= self.min_confidence_threshold
            
            # Check if signal meets minimum criteria
            if abs(weighted_expected_return) < self.min_expected_return:
                continue
                
            if uncertainty < self.min_uncertainty or uncertainty > self.max_uncertainty:
                continue
                
            if not is_confident:
                continue
            
            # Determine action based on weighted expected return
            if weighted_expected_return > self.min_expected_return:
                action = "BUY"
            elif weighted_expected_return < -self.min_expected_return:
                action = "SELL"
            else:
                continue  # Skip neutral signals
            
            # Calculate signal strength (0-1 scale)
            signal_strength = min(abs(weighted_expected_return) / 0.01, 1.0)  # Normalize to 1% return
            
            # Calculate position size based on risk parameters
            base_quantity = self.max_position_size
            adjusted_quantity = base_quantity * signal_strength * symbol_weight
            
            # Create trading signal
            signal = TradingSignal(
                symbol=symbol,
                action=action,
                quantity=adjusted_quantity,
                confidence=confidence,
                expected_return=weighted_expected_return,
                timestamp=belief_state.timestamp,
                regime=regime,
                signal_strength=signal_strength
            )
            
            signals.append(signal)
        
        return signals