"""
Regime Detection Module for Trading System
Implements continuous regime detection using Hidden Markov Models and Gaussian Mixture Models
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
import pickle
import os

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    from sklearn.mixture import GaussianMixture
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    # Fallback to basic implementation
    GaussianMixture = None
    StandardScaler = None

logger = logging.getLogger(__name__)

class RegimeDetector:
    """
    Regime detection using Gaussian Mixture Models for continuous regime characterization
    """
    
    def __init__(self, n_regimes: int = 3, n_features: int = 5, 
                 random_state: int = 42, verbose: int = 0):
        self.n_regimes = n_regimes
        self.n_features = n_features
        self.random_state = random_state
        self.verbose = verbose
        
        # Initialize GMM
        self.gmm = GaussianMixture(
            n_components=n_regimes,
            random_state=random_state,
            verbose=verbose
        )
        
        # For standardization
        self.scaler = StandardScaler()
        
        # Regime characteristics
        self.regime_means = None
        self.regime_covariances = None
        self.regime_weights = None
        
        # Training status
        self.is_fitted = False
        
        # History for transitional probabilities
        self.recent_regimes = []
        self.transition_matrix = np.ones((n_regimes, n_regimes)) / n_regimes
        
        logger.info(f"Initialized RegimeDetector with {n_regimes} regimes")
        
    def fit(self, features: np.ndarray) -> 'RegimeDetector':
        """
        Fit the regime detector to historical feature data
        
        Args:
            features: Array of shape (n_samples, n_features)
            
        Returns:
            self: Fitted detector
        """
        if len(features) < self.n_regimes * 10:
            raise ValueError(f"Need at least {self.n_regimes * 10} samples to fit {self.n_regimes} regimes")
            
        # Standardize features
        features_scaled = self.scaler.fit_transform(features)
        
        # Fit GMM
        self.gmm.fit(features_scaled)
        
        # Extract regime characteristics
        self.regime_means = self.gmm.means_
        self.regime_covariances = self.gmm.covariances_
        self.regime_weights = self.gmm.weights_
        
        self.is_fitted = True
        
        logger.info(f"Fitted RegimeDetector with {len(features)} samples")
        logger.info(f"Regime weights: {self.regime_weights}")
        
        return self
    
    def predict_regime(self, features: np.ndarray) -> Tuple[int, np.ndarray, Dict]:
        """
        Predict regime for given features
        
        Args:
            features: Array of shape (n_samples, n_features) or (n_features,)
            
        Returns:
            regime_labels: Predicted regime labels for each sample
            regime_probabilities: Probability of each regime for each sample
            regime_info: Additional information about regimes
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before predicting regimes")
            
        # Handle single sample case
        if features.ndim == 1:
            features = features.reshape(1, -1)
            
        # Standardize features
        features_scaled = self.scaler.transform(features)
        
        # Get probabilities and predictions
        regime_probabilities = self.gmm.predict_proba(features_scaled)
        regime_labels = self.gmm.predict(features_scaled)
        
        # Calculate additional regime information
        regime_info = self._get_regime_info(features_scaled, regime_labels, regime_probabilities)
        
        # Update recent regimes for transition modeling
        if len(regime_labels) > 0:
            self.recent_regimes.extend(regime_labels.tolist())
            # Keep only recent history
            if len(self.recent_regimes) > 100:
                self.recent_regimes = self.recent_regimes[-100:]
                
            # Update transition matrix
            self._update_transition_matrix()
        
        # Return results
        if len(regime_labels) == 1:
            return regime_labels[0], regime_probabilities[0], regime_info
        else:
            return regime_labels, regime_probabilities, regime_info
    
    def _get_regime_info(self, features_scaled: np.ndarray, 
                        regime_labels: np.ndarray, 
                        regime_probabilities: np.ndarray) -> Dict:
        """
        Get additional information about the detected regimes
        """
        info = {
            'regime_characteristics': [],
            'regime_separation': None,
            'dominant_regime': None,
            'regime_entropy': None
        }
        
        # Characteristics for each regime
        for i in range(self.n_regimes):
            regime_chars = {
                'regime_id': i,
                'weight': float(self.regime_weights[i]),
                'mean': self.regime_means[i].tolist() if self.regime_means is not None else None,
                'variance': np.diag(self.regime_covariances[i]).tolist() if self.regime_covariances is not None else None
            }
            info['regime_characteristics'].append(regime_chars)
        
        # Calculate regime separation (Bhattacharyya distance)
        if self.n_regimes >= 2 and self.regime_means is not None and self.regime_covariances is not None:
            distances = []
            for i in range(self.n_regimes):
                for j in range(i+1, self.n_regimes):
                    # Simplified distance measure
                    diff = self.regime_means[i] - self.regime_means[j]
                    avg_cov = (self.regime_covariances[i] + self.regime_covariances[j]) / 2
                    # Mahalanobis distance approximation
                    try:
                        inv_cov = np.linalg.inv(avg_cov + 1e-6 * np.eye(len(avg_cov)))
                        distance = np.sqrt(np.dot(np.dot(diff, inv_cov), diff))
                        distances.append(distance)
                    except np.linalg.LinAlgError:
                        distances.append(0.0)
            
            info['regime_separation'] = np.mean(distances) if distances else 0.0
        
        # Dominant regime (highest weight)
        if self.regime_weights is not None:
            dominant_idx = np.argmax(self.regime_weights)
            info['dominant_regime'] = int(dominant_idx)
            info['dominant_regime_weight'] = float(self.regime_weights[dominant_idx])
        
        # Entropy of regime distribution (uncertainty measure)
        if len(regime_probabilities) > 0:
            # Average entropy across samples
            entropies = []
            for probs in regime_probabilities:
                # Avoid log(0)
                probs_safe = np.clip(probs, 1e-10, 1.0)
                entropy = -np.sum(probs_safe * np.log(probs_safe))
                entropies.append(entropy)
            info['regime_entropy'] = float(np.mean(entropies))
        
        return info
    
    def _update_transition_matrix(self):
        """
        Update transition probability matrix based on recent regime sequence
        """
        if len(self.recent_regimes) < 2:
            return
            
        # Count transitions
        transition_counts = np.zeros((self.n_regimes, self.n_regimes))
        for i in range(len(self.recent_regimes) - 1):
            from_regime = self.recent_regimes[i]
            to_regime = self.recent_regimes[i + 1]
            transition_counts[from_regime, to_regime] += 1
        
        # Convert to probabilities
        row_sums = transition_counts.sum(axis=1, keepdims=True)
        # Avoid division by zero
        row_sums[row_sums == 0] = 1
        self.transition_matrix = transition_counts / row_sums
        
    def get_transition_probabilities(self, current_regime: int) -> np.ndarray:
        """
        Get transition probabilities from current regime
        
        Args:
            current_regime: Current regime index
            
        Returns:
            transition_probs: Probability of transitioning to each regime
        """
        if 0 <= current_regime < self.n_regimes:
            return self.transition_matrix[current_regime].copy()
        else:
            return np.ones(self.n_regimes) / self.n_regimes
    
    def predict_next_regime(self, current_regime: int) -> Tuple[int, float]:
        """
        Predict most likely next regime
        
        Args:
            current_regime: Current regime index
            
        Returns:
            next_regime: Most likely next regime index
            confidence: Confidence in prediction
        """
        transition_probs = self.get_transition_probabilities(current_regime)
        next_regime = np.argmax(transition_probs)
        confidence = transition_probs[next_regime]
        
        return int(next_regime), float(confidence)
    
    def get_regime_persistence(self, regime_id: int) -> float:
        """
        Get probability of staying in the same regime
        
        Args:
            regime_id: Regime index
            
        Returns:
            persistence: Probability of remaining in the same regime
        """
        if 0 <= regime_id < self.n_regimes:
            return float(self.transition_matrix[regime_id, regime_id])
        else:
            return 1.0 / self.n_regimes
    
    def save_model(self, filepath: str):
        """
        Save the fitted model to file
        """
        if not self.is_fitted:
            raise ValueError("Cannot save unfitted model")
            
        model_data = {
            'n_regimes': self.n_regimes,
            'n_features': self.n_features,
            'random_state': self.random_state,
            'regime_means': self.regime_means,
            'regime_covariances': self.regime_covariances,
            'regime_weights': self.regime_weights,
            'scaler_mean': self.scaler.mean_,
            'scaler_scale': self.scaler.scale_,
            'transition_matrix': self.transition_matrix,
            'recent_regimes': self.recent_regimes,
            'is_fitted': self.is_fitted
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
            
        logger.info(f"Regime detector model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """
        Load a fitted model from file
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file {filepath} not found")
            
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        # Restore attributes
        self.n_regimes = model_data['n_regimes']
        self.n_features = model_data['n_features']
        self.random_state = model_data['random_state']
        self.regime_means = model_data['regime_means']
        self.regime_covariances = model_data['regime_covariances']
        self.regime_weights = model_data['regime_weights']
        self.transition_matrix = model_data['transition_matrix']
        self.recent_regimes = model_data['recent_regimes']
        self.is_fitted = model_data['is_fitted']
        
        # Restore scaler
        self.scaler = StandardScaler()
        self.scaler.mean_ = model_data['scaler_mean']
        self.scaler.scale_ = model_data['scaler_scale']
        
        logger.info(f"Regime detector model loaded from {filepath}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the regime detector
        """
        return {
            'n_regimes': self.n_regimes,
            'n_features': self.n_features,
            'is_fitted': self.is_fitted,
            'regime_weights': self.regime_weights.tolist() if self.regime_weights is not None else None,
            'regime_means': self.regime_means.tolist() if self.regime_means is not None else None,
            'recent_regimes_count': len(self.recent_regimes),
            'transition_matrix': self.transition_matrix.tolist() if hasattr(self, 'transition_matrix') else None
        }

class HiddenMarkovRegimeDetector:
    """
    Alternative regime detection using Hidden Markov Models
    (Simplified implementation - would use hmmlearn in practice)
    """
    
    def __init__(self, n_regimes: int = 3, n_features: int = 5):
        self.n_regimes = n_regimes
        self.n_features = n_features
        # Simplified HMM parameters
        self.start_prob = np.ones(n_regimes) / n_regimes
        self.trans_prob = np.ones((n_regimes, n_regimes)) / n_regimes
        # Emission parameters (mean and covariance for each regime)
        self.means = np.zeros((n_regimes, n_features))
        self.covars = np.array([np.eye(n_features) for _ in range(n_regimes)])
        self.is_fitted = False
        
        logger.info(f"Initialized HiddenMarkovRegimeDetector with {n_regimes} regimes")
    
    def fit(self, features: np.ndarray) -> 'HiddenMarkovRegimeDetector':
        """
        Fit HMM to feature data (simplified implementation)
        """
        # In practice, would use Baum-Welch algorithm or hmmlearn
        # For now, use simple clustering approach similar to GMM
        
        from sklearn.cluster import KMeans
        
        # Cluster the data to initialize regimes
        kmeans = KMeans(n_clusters=self.n_regimes, random_state=42)
        cluster_labels = kmeans.fit_predict(features)
        
        # Set parameters based on clustering
        self.means = kmeans.cluster_centers_
        
        # Calculate covariance for each cluster
        for i in range(self.n_regimes):
            cluster_points = features[cluster_labels == i]
            if len(cluster_points) > 1:
                self.covars[i] = np.cov(cluster_points.T) + 1e-6 * np.eye(self.n_features)
            else:
                self.covars[i] = np.eye(self.n_features)
        
        # Estimate transition matrix from sequence
        if len(cluster_labels) > 1:
            transition_counts = np.zeros((self.n_regimes, self.n_regions))
            for i in range(len(cluster_labels) - 1):
                from_state = cluster_labels[i]
                to_state = cluster_labels[i + 1]
                transition_counts[from_state, to_state] += 1
            
            # Normalize to get probabilities
            row_sums = transition_counts.sum(axis=1, keepdims=True)
            row_sums[row_sums == 0] = 1
            self.trans_prob = transition_counts / row_sums
        
        self.is_fitted = True
        logger.info("Fitted HiddenMarkovRegimeDetector")
        return self
    
    def predict_regime(self, features: np.ndarray) -> Tuple[int, np.ndarray]:
        """
        Predict regime using Viterbi algorithm (simplified)
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before predicting")
        
        # Simplified: just use closest mean for now
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        # Calculate distances to each regime mean
        distances = np.zeros((len(features), self.n_regimes))
        for i in range(self.n_regimes):
            diff = features - self.means[i]
            # Mahalanobis distance approximation
            try:
                inv_cov = np.linalg.inv(self.covars[i] + 1e-6 * np.eye(self.n_features))
                distances[:, i] = np.sqrt(np.sum(np.dot(diff, inv_cov) * diff, axis=1))
            except np.linalg.LinAlgError:
                # Fallback to Euclidean distance
                distances[:, i] = np.linalg.norm(diff, axis=1)
        
        # Predict regime with minimum distance
        regime_labels = np.argmin(distances, axis=1)
        
        # Convert distances to probabilities (simplified)
        # Convert distances to similarities
        similarities = np.exp(-distances)
        # Normalize to get probabilities
        regime_probabilities = similarities / np.sum(similarities, axis=1, keepdims=True)
        
        if len(regime_labels) == 1:
            return regime_labels[0], regime_probabilities[0]
        else:
            return regime_labels, regime_probabilities
    
    def save_model(self, filepath: str):
        """
        Save the fitted model to file
        """
        if not self.is_fitted:
            raise ValueError("Cannot save unfitted model")
            
        model_data = {
            'n_regimes': self.n_regimes,
            'n_features': self.n_features,
            'start_prob': self.start_prob,
            'trans_prob': self.trans_prob,
            'means': self.means,
            'covars': self.covars,
            'is_fitted': self.is_fitted
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
            
        logger.info(f"HMM regime detector model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """
        Load a fitted model from file
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file {filepath} not found")
            
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        # Restore attributes
        self.n_regimes = model_data['n_regimes']
        self.n_features = model_data['n_features']
        self.start_prob = model_data['start_prob']
        self.trans_prob = model_data['trans_prob']
        self.means = model_data['means']
        self.covars = model_data['covars']
        self.is_fitted = model_data['is_fitted']
        
        logger.info(f"HMM regime detector model loaded from {filepath}")

def create_regime_detector(n_regimes: int = 3, method: str = "gmm") -> Any:
    """
    Factory function to create a regime detector
    
    Args:
        n_regimes: Number of regimes to detect
        method: Detection method ('gmm' or 'hmm')
        
    Returns:
        Regime detector instance
    """
    if method.lower() == "gmm":
        return RegimeDetector(n_regimes=n_regimes)
    elif method.lower() == "hmm":
        return HiddenMarkovRegimeDetector(n_regimes=n_regimes)
    else:
        raise ValueError(f"Unknown regime detection method: {method}")

def create_multiscale_regime_detector() -> Dict[str, RegimeDetector]:
    """
    Create a multiscale regime detector that operates at different time scales
    """
    detectors = {
        'short_term': RegimeDetector(n_regimes=3, n_features=5),  # Fast-changing regimes
        'medium_term': RegimeDetector(n_regimes=4, n_features=5), # Medium-term regimes
        'long_term': RegimeDetector(n_regimes=2, n_features=5)    # Slow-changing regimes
    }
    
    return detectors