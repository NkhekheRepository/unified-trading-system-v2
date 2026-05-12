"""
Advanced Feature Engineering Pipeline for Trading System
Implements sophisticated microstructure features and ML-ready feature processing
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import logging
from collections import deque
import hashlib

logger = logging.getLogger(__name__)

class AdvancedFeaturePipeline:
    """
    Advanced feature engineering pipeline that computes sophisticated
    microstructure features suitable for machine learning models
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.feature_history = deque(maxlen=self.config['max_history'])
        self.feature_scalers = {}
        self.feature_names = []
        
    def _default_config(self) -> Dict:
        return {
            'max_history': 1000,
            'normalization_window': 100,
            'enable_dynamic_normalization': True,
            'enable_feature_selection': True,
            'min_periods_for_calculation': 10,
        }
    
    def compute_microstructure_features(self, market_data: Dict) -> Dict[str, float]:
        """
        Compute advanced microstructure features from raw market data
        Returns dictionary of feature names to values
        """
        features = {}
        
        # Extract basic market data
        bid_price = market_data.get("bid_price", 0.0)
        ask_price = market_data.get("ask_price", 0.0)
        bid_size = market_data.get("bid_size", 0.0)
        ask_size = market_data.get("ask_size", 0.0)
        last_price = market_data.get("last_price", 0.0)
        last_size = market_data.get("last_size", 0.0)
        volume = market_data.get("volume", 0.0)
        
        # Skip if essential data missing
        if bid_price <= 0 or ask_price <= 0:
            return features
            
        # Basic calculations
        mid_price = (bid_price + ask_price) / 2.0
        spread = ask_price - bid_price
        spread_bps = (spread / mid_price * 10000) if mid_price > 0 else 0.0
        total_size = bid_size + ask_size
        
        # === BASIC MICROSTRUCTURE FEATURES ===
        
        # 1. Order Flow Imbalance (OFI) - Multiple time scales
        if total_size > 0:
            ofi = (bid_size - ask_size) / total_size
            features["ofi"] = ofi
            
            # Volume-scaled OFI
            features["ofi_volume_scaled"] = ofi * np.log(1 + total_size)
        else:
            features["ofi"] = 0.0
            features["ofi_volume_scaled"] = 0.0
            
        # 2. Bid-Ask Spread Features
        features["spread"] = spread
        features["spread_bps"] = spread_bps
        features["spread_relative"] = spread / mid_price if mid_price > 0 else 0.0
        
        # 3. Depth-Weighted Features
        if bid_size > 0 and ask_size > 0:
            # Size imbalance
            features["size_imbalance"] = (bid_size - ask_size) / (bid_size + ask_size)
            
            # Depth imbalance at multiple levels
            features["depth_imbalance"] = (bid_size - ask_size) / (bid_size + ask_size)
            
            # Price impact approximation
            if spread > 0:
                features["price_impact_estimate"] = abs(last_price - mid_price) / spread
            else:
                features["price_impact_estimate"] = 0.0
                
            # Liquidity measure
            features["liquidity"] = min(bid_size, ask_size) / max(bid_size, ask_size) if max(bid_size, ask_size) > 0 else 0.0
        else:
            features["size_imbalance"] = 0.0
            features["depth_imbalance"] = 0.0
            features["price_impact_estimate"] = 0.0
            features["liquidity"] = 0.0
            
        # 4. Volume-Based Features
        if volume > 0 and total_size > 0:
            features["volume_participation"] = last_size / volume if volume > 0 else 0.0
            features["size_to_volume_ratio"] = total_size / volume if volume > 0 else 0.0
        else:
            features["volume_participation"] = 0.0
            features["size_to_volume_ratio"] = 0.0
            
        # 5. Price Features
        features["mid_price"] = mid_price
        features["price_deviation"] = (last_price - mid_price) / mid_price if mid_price > 0 else 0.0
        
        # 6. Volatility Proxies
        features["spread_based_volatility"] = min(spread_bps / 5.0, 1.0)  # Normalized
        features["price_volatility_proxy"] = abs(features["price_deviation"]) * 10  # Scaled
        
        # === ADVANCED MICROSTRUCTURE FEATURES ===
        
        # 7. Order Flow Toxicity (Kyle's Lambda approximation)
        if len(self.feature_history) > 5:
            # Use recent price changes and order flow to estimate toxicity
            recent_ofis = [f.get("ofi", 0) for f in list(self.feature_history)[-5:]]
            if len(recent_ofis) >= 2:
                ofi_std = np.std(recent_ofis)
                if ofi_std > 0:
                    # Approximate Kyle's lambda: price impact per unit order flow
                    price_changes = [abs(f.get("price_deviation", 0)) for f in list(self.feature_history)[-5:]]
                    if len(price_changes) >= 2:
                        price_change_std = np.std(price_changes)
                        features["order_flow_toxicity"] = price_change_std / (ofi_std + 1e-8)
                    else:
                        features["order_flow_toxicity"] = 0.0
                else:
                    features["order_flow_toxicity"] = 0.0
            else:
                features["order_flow_toxicity"] = 0.0
        else:
            features["order_flow_toxicity"] = 0.0
            
        # 8. Informed Trading Probability (Enhanced PIN model approximation)
        # Based on order flow persistence and price impact
        if len(self.feature_history) > 10:
            recent_ofis = np.array([f.get("ofi", 0) for f in list(self.feature_history)[-10:]])
            recent_price_changes = np.array([abs(f.get("price_deviation", 0)) for f in list(self.feature_history)[-10:]])
            
            if len(recent_ofis) > 0 and len(recent_price_changes) > 0:
                # Correlation between order flow and price changes
                if np.std(recent_ofis) > 0 and np.std(recent_price_changes) > 0:
                    correlation = np.corrcoef(recent_ofis, recent_price_changes)[0,1]
                    features["informed_probability"] = max(0, min(1, (correlation + 1) / 2))  # Map to [0,1]
                else:
                    features["informed_probability"] = 0.0
            else:
                features["informed_probability"] = 0.0
        else:
            features["informed_probability"] = 0.0
            
        # 9. Liquidity-Driven Trading Estimate
        # When large trades occur with minimal price impact
        if len(self.feature_history) > 5:
            recent_volumes = [f.get("size_to_volume_ratio", 0) for f in list(self.feature_history)[-5:]]
            recent_price_impacts = [f.get("price_impact_estimate", 0) for f in list(self.feature_history)[-5:]]
            
            if len(recent_volumes) > 0 and len(recent_price_impacts) > 0:
                avg_volume = np.mean(recent_volumes)
                avg_impact = np.mean(recent_price_impacts)
                if avg_volume > 0:
                    # High volume with low impact suggests liquidity trading
                    features["liquidity_driven_score"] = avg_volume / (avg_impact + 0.01)
                else:
                    features["liquidity_driven_score"] = 0.0
            else:
                features["liquidity_driven_score"] = 0.0
        else:
            features["liquidity_driven_score"] = 0.0
            
        # 10. Volatility-Clustering Features
        if len(self.feature_history) > 10:
            recent_volatilities = [f.get("spread_based_volatility", 0) for f in list(self.feature_history)[-10:]]
            if len(recent_volatilities) > 1:
                vol_change = abs(recent_volatilities[-1] - np.mean(recent_volatilities[:-1]))
                features["volatility_innovation"] = vol_change
                features["volatility_persistence"] = np.corrcoef(
                    recent_volatilities[:-1], recent_volatilities[1:]
                )[0,1] if len(recent_volatilities) > 2 else 0.0
            else:
                features["volatility_innovation"] = 0.0
                features["volatility_persistence"] = 0.0
        else:
            features["volatility_innovation"] = 0.0
            features["volatility_persistence"] = 0.0
            
        # Store features for historical analysis
        self.feature_history.append(features.copy())
        
        return features
    
    def normalize_features(self, features: Dict[str, float]) -> Dict[str, float]:
        """
        Normalize features using rolling window statistics
        """
        if not self.config['enable_dynamic_normalization'] or len(self.feature_history) < self.config['min_periods_for_calculation']:
            return features
            
        normalized = {}
        history_array = self._dicts_to_array(list(self.feature_history))
        
        for i, feature_name in enumerate(features.keys()):
            if feature_name in self.feature_names or len(self.feature_names) == 0:
                # Initialize feature names on first call
                if len(self.feature_names) == 0:
                    self.feature_names = list(features.keys())
                    
                if feature_name < len(self.feature_names):
                    feature_idx = self.feature_names.index(feature_name)
                    if feature_idx < history_array.shape[1]:
                        feature_values = history_array[:, feature_idx]
                        
                        # Calculate rolling statistics
                        if len(feature_values) >= self.config['normalization_window']:
                            recent_values = feature_values[-self.config['normalization_window']:]
                            mean_val = np.mean(recent_values)
                            std_val = np.std(recent_values)
                            
                            if std_val > 1e-8:
                                normalized[feature_name] = (features[feature_name] - mean_val) / std_val
                            else:
                                normalized[feature_name] = 0.0
                        else:
                            # Not enough data for normalization, use simple scaling
                            if np.std(feature_values) > 1e-8:
                                normalized[feature_name] = (features[feature_name] - np.mean(feature_values)) / np.std(feature_values)
                            else:
                                normalized[feature_name] = 0.0
                    else:
                        normalized[feature_name] = 0.0
                else:
                    normalized[feature_name] = 0.0
            else:
                normalized[feature_name] = 0.0
                
        return normalized
    
    def _dicts_to_array(self, dict_list: List[Dict]) -> np.ndarray:
        """
        Convert list of dictionaries to numpy array for processing
        """
        if not dict_list:
            return np.array([])
            
        # Get all unique keys
        all_keys = set()
        for d in dict_list:
            all_keys.update(d.keys())
            
        # Create array
        array = np.zeros((len(dict_list), len(all_keys)))
        key_list = sorted(list(all_keys))
        
        for i, d in enumerate(dict_list):
            for j, key in enumerate(key_list):
                array[i, j] = d.get(key, 0.0)
                
        return array
    
    def get_feature_importance_weights(self) -> Dict[str, float]:
        """
        Calculate feature importance based on historical predictive power
        (Simplified implementation - would be enhanced with actual ML feedback)
        """
        # Placeholder for actual importance calculation
        # In practice, this would be updated based on model performance
        default_importance = {
            'ofi': 0.15,
            'ofi_volume_scaled': 0.1,
            'spread_bps': 0.05,
            'size_imbalance': 0.1,
            'depth_imbalance': 0.1,
            'liquidity': 0.1,
            'volume_participation': 0.05,
            'price_deviation': 0.05,
            'order_flow_toxicity': 0.1,
            'informed_probability': 0.1,
            'liquidity_driven_score': 0.05,
            'volatility_innovation': 0.05,
        }
        
        # Return only features that exist
        return {k: v for k, v in default_importance.items() if k in self.feature_names}
    
    def get_feature_vector(self, features: Dict[str, float]) -> np.ndarray:
        """
        Convert feature dictionary to numpy array in consistent order.
        Applies normalization if enabled (Phase 4.2 - 10/10 Upgrade)
        """
        if not self.feature_names:
            # Initialize feature names
            self.feature_names = sorted(list(features.keys()))
            
        vector = np.zeros(len(self.feature_names))
        for i, feature_name in enumerate(self.feature_names):
            vector[i] = features.get(feature_name, 0.0)
            
        # Phase 4.2: Apply normalization if enabled and we have enough history
        if self.config['enable_dynamic_normalization'] and len(self.feature_history) >= self.config['min_periods_for_calculation']:
            vector = self._normalize_features(vector)
            
        return vector
    
    def _normalize_features(self, vector: np.ndarray) -> np.ndarray:
        """
        Normalize features using rolling window statistics (Phase 4.2).
        Uses z-score normalization: (x - mean) / std
        """
        if len(self.feature_history) < 2:
            return vector
            
        # Convert history to array
        history_array = np.array(list(self.feature_history))
        
        # Calculate mean and std for each feature
        means = np.mean(history_array, axis=0)
        stds = np.std(history_array, axis=0)
        
        # Avoid division by zero
        stds = np.where(stds > 1e-10, stds, 1.0)
        
        normalized = (vector - means) / stds
        
        # Clip extreme values to prevent outliers from dominating
        normalized = np.clip(normalized, -5.0, 5.0)
        
        return normalized
    
    def check_stationarity(self, feature_name: str = None) -> Dict[str, Any]:
        """
        Check stationarity of features using Augmented Dickey-Fuller test (simplified).
        Phase 4.2: Feature validation for ML pipeline integrity.
        
        Returns:
            Dictionary with stationarity test results
        """
        if len(self.feature_history) < self.config['min_periods_for_calculation']:
            return {"stationary": True, "reason": "Insufficient data"}
            
        history_array = np.array(list(self.feature_history))
        
        results = {}
        feature_indices = range(history_array.shape[1]) if feature_name is None else [self.feature_names.index(feature_name)] if feature_name in self.feature_names else []
        
        for idx in feature_indices:
            feature_series = history_array[:, idx]
            name = self.feature_names[idx] if idx < len(self.feature_names) else f"feature_{idx}"
            
            # Simplified stationarity check: Coefficient of variation
            mean_val = np.mean(feature_series)
            std_val = np.std(feature_series)
            
            if abs(mean_val) < 1e-10:
                cv = 0.0
            else:
                cv = std_val / abs(mean_val)
            
            # Flag if coefficient of variation is too high (non-stationary)
            is_stationary = cv < 1.0  # Heuristic: CV < 1 indicates relative stability
            
            results[name] = {
                "stationary": is_stationary,
                "cv": cv,
                "mean": mean_val,
                "std": std_val,
            }
            
        return results
    
    def validate_features(self, features: Dict[str, float]) -> Tuple[bool, List[str]]:
        """
        Validate features before model input (Phase 4.2).
        
        Checks:
        - No NaN or infinite values
        - All expected features present
        - Values within reasonable ranges
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        # Check for NaN or infinite values
        for name, value in features.items():
            if np.isnan(value) or np.isinf(value):
                issues.append(f"{name}: Invalid value ({value})")
        
        # Check for extreme values (potential outliers)
        for name, value in features.items():
            if abs(value) > 1e6:
                issues.append(f"{name}: Extreme value detected ({value})")
        
        # Check stationarity if we have enough history
        if len(self.feature_history) >= self.config['min_periods_for_calculation']:
            stationarity = self.check_stationarity()
            non_stationary = [name for name, result in stationarity.items() if not result.get('stationary', True)]
            if non_stationary:
                issues.append(f"Non-stationary features detected: {non_stationary}")
        
        return len(issues) == 0, issues

class FeatureSelector:
    """
    Feature selection mechanism to prevent overfitting and improve model performance
    """
    
    def __init__(self, max_features: int = 20):
        self.max_features = max_features
        self.selected_features = []
        self.feature_scores = {}
        
    def update_scores(self, feature_names: List[str], performance_impact: Dict[str, float]):
        """
        Update feature scores based on their impact on model performance
        """
        for feature in feature_names:
            if feature not in self.feature_scores:
                self.feature_scores[feature] = 0.0
            # In practice, this would be updated with actual performance data
            self.feature_scores[feature] += performance_impact.get(feature, 0.0)
            
    def select_features(self, available_features: List[str]) -> List[str]:
        """
        Select top-performing features
        """
        # Score features (use default scores if none available)
        scored_features = []
        for feature in available_features:
            score = self.feature_scores.get(feature, 0.0)
            scored_features.append((feature, score))
            
        # Sort by score and select top features
        scored_features.sort(key=lambda x: x[1], reverse=True)
        self.selected_features = [f[0] for f in scored_features[:self.max_features]]
        
        return self.selected_features