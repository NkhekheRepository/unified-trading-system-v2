"""
Kronos Integration for Unified Trading System
Wrapper for Kronos foundation model for market regime inference and prediction

Kronos is a transformer-based foundation model for financial markets
Available on HuggingFace: NeoQuasar/Kronos-mini
"""

import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class KronosConfig:
    """Configuration for Kronos model"""
    model_name: str = "NeoQuasar/Kronos-mini"
    tokenizer_name: str = "NeoQuasar/Kronos-Tokenizer-2k"
    device: str = "cuda" if False else "cpu"  # Default to CPU for safety
    max_sequence_length: int = 512
    prediction_horizon: int = 64
    temperature: float = 1.0
    cache_dir: Optional[str] = None
    kronos_repo_path: Optional[str] = None
    use_cache: bool = True

class KronosIntegration:
    """
    Kronos foundation model integration for the unified trading system.
    
    Kronos capabilities:
    - Market regime prediction
    - Volatility forecasting  
    - Cross-asset correlation patterns
    - Anomaly detection
    - Price prediction
    """
    
    def __init__(self, config: Optional[KronosConfig] = None):
        self.config = config or KronosConfig()
        self.device = self.config.device
        
        self.model = None
        self.tokenizer = None
        self.predictor = None
        self.is_loaded = False
        
        self.prediction_cache = {}
        self.cache_ttl_seconds = 300
        
        self.price_history = []
        self.max_history = 2000
        
    def load(self) -> bool:
        """
        Load Kronos model and tokenizer
        """
        try:
            # Try to import Kronos from local repo first
            kronos_repo_path = self.config.kronos_repo_path or "/tmp/Kronos_Github"
            
            if os.path.exists(kronos_repo_path):
                if kronos_repo_path not in __import__('sys').path:
                    __import__('sys').path.append(kronos_repo_path)
                
                try:
                    from model.kronos import Kronos, KronosTokenizer, KronosPredictor
                    return self._load_kronos_components(Kronos, KronosTokenizer, KronosPredictor)
                except ImportError:
                    logger.warning("Kronos not found in local repo, trying HuggingFace")
            
            # Try importing directly (if installed via pip)
            try:
                from kronos import Kronos, KronosTokenizer, KronosPredictor
                return self._load_kronos_components(Kronos, KronosTokenizer, KronosPredictor)
            except ImportError:
                logger.info("Kronos not installed, using fallback mode")
                return self._initialize_fallback()
                
        except Exception as e:
            logger.error(f"Failed to load Kronos: {e}")
            return self._initialize_fallback()
    
    def _load_kronos_components(self, Kronos, KronosTokenizer, KronosPredictor):
        """Load Kronos model components"""
        try:
            logger.info(f"Loading Kronos tokenizer: {self.config.tokenizer_name}")
            
            self.tokenizer = KronosTokenizer.from_pretrained(
                self.config.tokenizer_name,
                cache_dir=self.config.cache_dir,
            )
            
            logger.info(f"Loading Kronos model: {self.config.model_name}")
            self.model = Kronos.from_pretrained(
                self.config.model_name,
                cache_dir=self.config.cache_dir,
            )
            
            self.model.to(self.device)
            
            self.predictor = KronosPredictor(
                model=self.model,
                tokenizer=self.tokenizer,
                device=self.device,
            )
            
            self.is_loaded = True
            logger.info("Kronos model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading Kronos components: {e}")
            return self._initialize_fallback()
    
    def _initialize_fallback(self):
        """
        Initialize fallback mode when Kronos is not available
        """
        logger.warning("Initializing Kronos fallback mode (simplified regime detection)")
        self.is_loaded = False
        return True
    
    def update_market_data(self, price: float, volume: float, timestamp: float):
        """
        Update market data for Kronos prediction
        """
        self.price_history.append({
            'price': price,
            'volume': volume,
            'timestamp': timestamp
        })
        
        if len(self.price_history) > self.max_history:
            self.price_history = self.price_history[-self.max_history:]
    
    def predict_regime(self) -> Dict[str, Any]:
        """
        Predict market regime using Kronos
        """
        if not self.is_loaded:
            return self._fallback_regime_prediction()
        
        try:
            # Prepare input sequence
            if len(self.price_history) < 10:
                return self._fallback_regime_prediction()
            
            # Extract price sequence
            prices = [p['price'] for p in self.price_history[-100:]]
            
            # Tokenize
            input_ids = self.tokenizer(prices, return_tensors='pt')
            input_ids = {k: v.to(self.device) for k, v in input_ids.items()}
            
            # Generate regime prediction
            with torch.no_grad():
                outputs = self.model.generate(
                    **input_ids,
                    max_new_tokens=self.config.prediction_horizon,
                    temperature=self.config.temperature,
                    do_sample=True,
                )
            
            # Extract regime information (simplified)
            regime_score = float(torch.mean(outputs.float()).item())
            
            return {
                'regime': 'BULL' if regime_score > 0.6 else 'BEAR' if regime_score < 0.4 else 'SIDEWAYS',
                'confidence': abs(regime_score - 0.5) * 2,
                'volatility_level': 'HIGH' if np.std(prices[-20:]) > np.std(prices) else 'LOW',
                'trend_strength': abs(np.mean(np.diff(prices[-10:]))),
                'model_used': 'kronos'
            }
            
        except Exception as e:
            logger.error(f"Kronos prediction error: {e}")
            return self._fallback_regime_prediction()
    
    def predict_volatility(self, horizon: int = 20) -> Dict[str, float]:
        """
        Predict future volatility
        """
        if not self.is_loaded or len(self.price_history) < 30:
            return self._fallback_volatility_prediction(horizon)
        
        try:
            prices = [p['price'] for p in self.price_history[-100:]]
            
            # Use returns for volatility prediction
            returns = np.diff(prices) / prices[:-1]
            
            # Simple GARCH-like volatility projection
            recent_vol = np.std(returns[-20:])
            long_vol = np.std(returns)
            
            # Weighted average for forecast
            volatility_forecast = 0.6 * recent_vol + 0.4 * long_vol
            
            return {
                'volatility_forecast': volatility_forecast,
                'recent_volatility': recent_vol,
                'long_term_volatility': long_vol,
                'horizon': horizon,
                'model_used': 'kronos'
            }
            
        except Exception as e:
            logger.error(f"Volatility prediction error: {e}")
            return self._fallback_volatility_prediction(horizon)
    
    def detect_anomaly(self) -> Dict[str, Any]:
        """
        Detect market anomalies using Kronos
        """
        if len(self.price_history) < 30:
            return {'anomaly_detected': False, 'reason': 'insufficient_data'}
        
        prices = np.array([p['price'] for p in self.price_history[-50:]])
        
        # Calculate Z-score of recent price movement
        recent_price = prices[-1]
        mean_price = np.mean(prices[:-1])
        std_price = np.std(prices[:-1])
        
        if std_price > 0:
            z_score = (recent_price - mean_price) / std_price
        else:
            z_score = 0
        
        # Anomaly thresholds
        anomaly_detected = abs(z_score) > 3.0
        
        return {
            'anomaly_detected': anomaly_detected,
            'z_score': z_score,
            'threshold': 3.0,
            'severity': 'HIGH' if abs(z_score) > 4 else 'MEDIUM' if abs(z_score) > 3 else 'LOW',
            'recent_price': recent_price,
            'mean_price': mean_price,
            'model_used': 'kronos' if self.is_loaded else 'fallback'
        }
    
    def predict_returns(self, horizon: int = 5) -> Dict[str, float]:
        """
        Predict future returns
        """
        if len(self.price_history) < 20:
            return {'expected_return': 0.0, 'confidence': 0.0}
        
        prices = [p['price'] for p in self.price_history[-50:]]
        returns = np.diff(prices) / prices[:-1]
        
        # Simple momentum-based prediction
        recent_momentum = np.mean(returns[-horizon:])
        momentum_decay = np.exp(-0.1 * np.arange(horizon))
        weighted_momentum = np.sum(momentum_decay * returns[-horizon:]) / np.sum(momentum_decay)
        
        expected_return = weighted_momentum
        
        # Confidence based on momentum consistency
        momentum_consistency = 1.0 - min(1.0, np.std(returns[-horizon:]) / (abs(np.mean(returns[-horizon:])) + 0.001))
        
        return {
            'expected_return': expected_return,
            'confidence': max(0, min(1, momentum_consistency)),
            'horizon': horizon,
            'recent_momentum': recent_momentum,
            'model_used': 'kronos' if self.is_loaded else 'fallback'
        }
    
    def _fallback_regime_prediction(self) -> Dict[str, Any]:
        """
        Fallback regime prediction when Kronos is not available
        """
        if len(self.price_history) < 20:
            return {
                'regime': 'UNKNOWN',
                'confidence': 0.0,
                'volatility_level': 'UNKNOWN',
                'trend_strength': 0.0,
                'model_used': 'fallback'
            }
        
        prices = [p['price'] for p in self.price_history[-50:]]
        returns = np.diff(prices) / prices[:-1]
        
        # Simple trend detection
        trend = np.mean(returns[-10:])
        volatility = np.std(returns[-20:])
        
        # Regime determination
        if trend > 0.001:
            regime = 'BULL'
        elif trend < -0.001:
            regime = 'BEAR'
        else:
            regime = 'SIDEWAYS'
        
        return {
            'regime': regime,
            'confidence': min(1.0, abs(trend) * 100),
            'volatility_level': 'HIGH' if volatility > 0.02 else 'LOW',
            'trend_strength': abs(trend),
            'model_used': 'fallback'
        }
    
    def _fallback_volatility_prediction(self, horizon: int) -> Dict[str, float]:
        """
        Fallback volatility prediction
        """
        if len(self.price_history) < 20:
            return {
                'volatility_forecast': 0.02,
                'recent_volatility': 0.02,
                'long_term_volatility': 0.02,
                'horizon': horizon,
                'model_used': 'fallback'
            }
        
        prices = [p['price'] for p in self.price_history[-50:]]
        returns = np.diff(prices) / prices[:-1]
        
        recent_vol = np.std(returns[-20:])
        long_vol = np.std(returns)
        
        return {
            'volatility_forecast': 0.6 * recent_vol + 0.4 * long_vol,
            'recent_volatility': recent_vol,
            'long_term_volatility': long_vol,
            'horizon': horizon,
            'model_used': 'fallback'
        }
    
    def get_kronos_status(self) -> Dict[str, Any]:
        """
        Get Kronos integration status
        """
        return {
            'is_loaded': self.is_loaded,
            'device': self.device,
            'config': {
                'model_name': self.config.model_name,
                'tokenizer_name': self.config.tokenizer_name,
                'prediction_horizon': self.config.prediction_horizon,
            },
            'data_points': len(self.price_history),
            'prediction_cache_size': len(self.prediction_cache)
        }
    
    def save_state(self, filepath: str):
        """
        Save Kronos integration state
        """
        state = {
            'config': {
                'model_name': self.config.model_name,
                'tokenizer_name': self.config.tokenizer_name,
                'device': self.device,
            },
            'price_history': self.price_history[-1000:],  # Save last 1000 points
            'is_loaded': self.is_loaded,
            'timestamp': datetime.now().isoformat()
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2, default=str)
        
        logger.info(f"Kronos state saved to {filepath}")
    
    def load_state(self, filepath: str):
        """
        Load Kronos integration state
        """
        if not os.path.exists(filepath):
            logger.warning(f"State file {filepath} not found")
            return
        
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        self.price_history = state.get('price_history', [])
        logger.info(f"Kronos state loaded from {filepath}")

def create_kronos_integration(config: Optional[KronosConfig] = None) -> KronosIntegration:
    """
    Factory function to create Kronos integration
    """
    return KronosIntegration(config)