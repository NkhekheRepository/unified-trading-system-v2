"""
ML Model Monitoring and Alerting Module for Trading System
Monitors model performance, drift detection, and generates alerts
"""

import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import deque
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class ModelHealthStatus:
    """Health status of ML model"""
    model_name: str
    status: str  # HEALTHY, DEGRADED, CRITICAL
    drift_detected: bool
    accuracy_score: float
    prediction_variance: float
    last_calibration: Optional[datetime]
    last_update: datetime

class MLDistributionMonitor:
    """
    Monitors input features and output distributions for drift detection
    """
    
    def __init__(self, 
                 window_size: int = 1000,
                 drift_threshold: float = 0.1,
                 alert_threshold: float = 0.2):
        self.window_size = window_size
        self.drift_threshold = drift_threshold
        self.alert_threshold = alert_threshold
        
        self.feature_history = {}
        self.prediction_history = deque(maxlen=window_size)
        self.target_history = deque(maxlen=window_size)
        
        self.baseline_statistics = {}
        self.drift_scores = {}
        self.alert_history = []
        
    def update_feature_statistics(self, features: Dict[str, float]):
        """
        Update feature statistics with new features
        """
        for feature_name, value in features.items():
            if feature_name not in self.feature_history:
                self.feature_history[feature_name] = deque(maxlen=self.window_size)
            
            self.feature_history[feature_name].append(value)
        
        # Check for drift if we have enough history
        if len(list(self.feature_history.values())[0]) >= self.window_size // 2:
            self._detect_feature_drift()
    
    def _detect_feature_drift(self):
        """
        Detect drift in feature distributions using statistical tests
        """
        for feature_name, values in self.feature_history.items():
            if len(values) < self.window_size:
                continue
            
            # Compare recent window to baseline
            recent_values = list(values)[-self.window_size//2:]
            baseline_values = list(values)[:self.window_size//2]
            
            # Update baseline if not set
            if feature_name not in self.baseline_statistics:
                self.baseline_statistics[feature_name] = {
                    'mean': np.mean(baseline_values),
                    'std': np.std(baseline_values) if len(baseline_values) > 1 else 1.0
                }
            
            # Calculate drift score (KL divergence approximation)
            baseline = self.baseline_statistics[feature_name]
            recent_mean = np.mean(recent_values)
            recent_std = np.std(recent_values) if len(recent_values) > 1 else 1.0
            
            if baseline['std'] > 0 and recent_std > 0:
                # Normalized mean shift
                mean_shift = abs(recent_mean - baseline['mean']) / baseline['std']
                # Normalized std change
                std_change = abs(recent_std - baseline['std']) / baseline['std']
                
                # Combined drift score
                drift_score = (mean_shift + std_change) / 2
            else:
                drift_score = 0.0
            
            self.drift_scores[feature_name] = drift_score
    
    def check_drift_alerts(self) -> List[Dict]:
        """
        Check for drift that exceeds thresholds and generate alerts
        """
        alerts = []
        
        for feature_name, drift_score in self.drift_scores.items():
            if drift_score > self.alert_threshold:
                alert = {
                    'type': 'FEATURE_DRIFT',
                    'severity': 'CRITICAL',
                    'feature': feature_name,
                    'drift_score': drift_score,
                    'threshold': self.alert_threshold,
                    'timestamp': datetime.now().isoformat()
                }
                alerts.append(alert)
                self.alert_history.append(alert)
            elif drift_score > self.drift_threshold:
                alert = {
                    'type': 'FEATURE_DRIFT',
                    'severity': 'WARNING',
                    'feature': feature_name,
                    'drift_score': drift_score,
                    'threshold': self.drift_threshold,
                    'timestamp': datetime.now().isoformat()
                }
                alerts.append(alert)
                self.alert_history.append(alert)
        
        return alerts
    
    def get_drift_summary(self) -> Dict[str, Any]:
        """
        Get summary of drift detection
        """
        if not self.drift_scores:
            return {'status': 'NO_DATA', 'features_monitored': 0}
        
        max_drift = max(self.drift_scores.values()) if self.drift_scores else 0
        avg_drift = np.mean(list(self.drift_scores.values())) if self.drift_scores else 0
        
        return {
            'status': 'CRITICAL' if max_drift > self.alert_threshold else \
                     'WARNING' if max_drift > self.drift_threshold else 'HEALTHY',
            'max_drift': max_drift,
            'avg_drift': avg_drift,
            'features_monitored': len(self.drift_scores),
            'baseline_statistics': self.baseline_statistics,
            'drift_scores': self.drift_scores
        }

class MLPredictionMonitor:
    """
    Monitors prediction accuracy and generates model health alerts
    """
    
    def __init__(self, 
                 accuracy_window: int = 100,
                 prediction_threshold: float = 0.5,
                 degradation_threshold: float = 0.1):
        self.accuracy_window = accuracy_window
        self.prediction_threshold = prediction_threshold
        self.degradation_threshold = degradation_threshold
        
        self.predictions = deque(maxlen=accuracy_window)
        self.actuals = deque(maxlen=accuracy_window)
        self.confidences = deque(maxlen=accuracy_window)
        
        self.performance_history = []
        self.alert_history = []
        
    def record_prediction(self, 
                         prediction: float, 
                         actual: float,
                         confidence: float = 1.0):
        """
        Record a prediction and its actual outcome
        """
        self.predictions.append(prediction)
        self.actuals.append(actual)
        self.confidences.append(confidence)
        
        # Update performance history periodically
        if len(self.predictions) >= self.accuracy_window:
            self._update_performance()
    
    def _update_performance(self):
        """
        Update performance metrics
        """
        if len(self.predictions) < self.accuracy_window:
            return
        
        preds = np.array(list(self.predictions))
        acts = np.array(list(self.actuals))
        confs = np.array(list(self.confidences))
        
        # Directional accuracy
        pred_direction = (preds > 0).astype(int)
        actual_direction = (acts > 0).astype(int)
        directional_accuracy = np.mean(pred_direction == actual_direction)
        
        # Error metrics
        mse = np.mean((preds - acts) ** 2)
        mae = np.mean(np.abs(preds - acts))
        rmse = np.sqrt(mse)
        
        # Confidence calibration
        # Are higher confidence predictions more accurate?
        high_conf_mask = confs > np.median(confs)
        if np.sum(high_conf_mask) > 0:
            high_conf_accuracy = np.mean(
                pred_direction[high_conf_mask] == actual_direction[high_conf_mask]
            )
            low_conf_accuracy = np.mean(
                pred_direction[~high_conf_mask] == actual_direction[~high_conf_mask]
            )
            calibration_score = high_conf_accuracy - low_conf_accuracy
        else:
            calibration_score = 0.0
        
        # Store performance
        performance = {
            'timestamp': datetime.now().isoformat(),
            'directional_accuracy': directional_accuracy,
            'mse': mse,
            'mae': mae,
            'rmse': rmse,
            'calibration_score': calibration_score,
            'n_samples': len(preds)
        }
        
        self.performance_history.append(performance)
        
        # Check for degradation
        if len(self.performance_history) >= 2:
            recent_perf = self.performance_history[-1]
            previous_perf = self.performance_history[-2]
            
            accuracy_change = recent_perf['directional_accuracy'] - previous_perf['directional_accuracy']
            
            if abs(accuracy_change) > self.degradation_threshold:
                alert = {
                    'type': 'ACCURACY_DEGRADATION',
                    'severity': 'CRITICAL' if abs(accuracy_change) > 0.2 else 'WARNING',
                    'previous_accuracy': previous_perf['directional_accuracy'],
                    'recent_accuracy': recent_perf['directional_accuracy'],
                    'change': accuracy_change,
                    'timestamp': datetime.now().isoformat()
                }
                self.alert_history.append(alert)
    
    def get_current_accuracy(self) -> float:
        """
        Get current prediction accuracy
        """
        if len(self.performance_history) == 0:
            return 0.0
        
        return self.performance_history[-1]['directional_accuracy']
    
    def get_accuracy_trend(self) -> str:
        """
        Get accuracy trend (improving, stable, degrading)
        """
        if len(self.performance_history) < 3:
            return "UNKNOWN"
        
        recent_accuracies = [p['directional_accuracy'] for p in self.performance_history[-3:]]
        
        if recent_accuracies[-1] > recent_accuracies[0] + self.degradation_threshold:
            return "IMPROVING"
        elif recent_accuracies[-1] < recent_accuracies[0] - self.degradation_threshold:
            return "DEGRADING"
        else:
            return "STABLE"
    
    def check_prediction_alerts(self) -> List[Dict]:
        """
        Check for prediction-based alerts
        """
        alerts = []
        
        if len(self.performance_history) == 0:
            return alerts
        
        current_perf = self.performance_history[-1]
        
        # Check for low accuracy
        if current_perf['directional_accuracy'] < 0.45:
            alerts.append({
                'type': 'LOW_ACCURACY',
                'severity': 'CRITICAL',
                'accuracy': current_perf['directional_accuracy'],
                'threshold': 0.45,
                'timestamp': datetime.now().isoformat()
            })
        elif current_perf['directional_accuracy'] < 0.50:
            alerts.append({
                'type': 'LOW_ACCURACY',
                'severity': 'WARNING',
                'accuracy': current_perf['directional_accuracy'],
                'threshold': 0.50,
                'timestamp': datetime.now().isoformat()
            })
        
        # Check for calibration issues
        if current_perf['calibration_score'] < -0.1:
            alerts.append({
                'type': 'CALIBRATION_ISSUE',
                'severity': 'WARNING',
                'calibration_score': current_perf['calibration_score'],
                'timestamp': datetime.now().isoformat()
            })
        
        # Check for accuracy degradation
        if len(self.performance_history) >= 2:
            accuracy_change = (current_perf['directional_accuracy'] - 
                            self.performance_history[-2]['directional_accuracy'])
            if accuracy_change < -self.degradation_threshold:
                alerts.append({
                    'type': 'ACCURACY_DROP',
                    'severity': 'WARNING',
                    'change': accuracy_change,
                    'timestamp': datetime.now().isoformat()
                })
        
        return alerts
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary
        """
        if not self.performance_history:
            return {'status': 'NO_DATA', 'samples_recorded': 0}
        
        current = self.performance_history[-1]
        recent_trend = self.get_accuracy_trend()
        
        return {
            'status': 'HEALTHY' if current['directional_accuracy'] > 0.55 else \
                     'DEGRADED' if current['directional_accuracy'] > 0.45 else 'CRITICAL',
            'current_accuracy': current['directional_accuracy'],
            'accuracy_trend': recent_trend,
            'mse': current['mse'],
            'mae': current['mae'],
            'calibration_score': current['calibration_score'],
            'samples_recorded': current['n_samples'],
            'performance_history_length': len(self.performance_history)
        }

class MLModelMonitor:
    """
    Comprehensive ML model monitoring system
    """
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.distribution_monitor = MLDistributionMonitor()
        self.prediction_monitor = MLPredictionMonitor()
        
        self.status = "HEALTHY"
        self.health_score = 1.0
        self.last_health_check = None
        self.overall_alerts = []
        
    def record_features(self, features: Dict[str, float]):
        """
        Record input features for distribution monitoring
        """
        self.distribution_monitor.update_feature_statistics(features)
    
    def record_prediction(self, prediction: float, actual: float, confidence: float = 1.0):
        """
        Record prediction and actual outcome
        """
        self.prediction_monitor.record_prediction(prediction, actual, confidence)
    
    def check_health(self) -> ModelHealthStatus:
        """
        Check overall model health
        """
        # Get distribution drift summary
        drift_summary = self.distribution_monitor.get_drift_summary()
        
        # Get prediction performance summary
        prediction_summary = self.prediction_monitor.get_performance_summary()
        
        # Determine status
        if drift_summary['status'] == 'CRITICAL' or prediction_summary['status'] == 'CRITICAL':
            status = 'CRITICAL'
        elif drift_summary['status'] == 'WARNING' or prediction_summary['status'] == 'DEGRADED':
            status = 'DEGRADED'
        else:
            status = 'HEALTHY'
        
        self.status = status
        
        # Calculate overall health score
        drift_penalty = 0.0
        if drift_summary['status'] == 'WARNING':
            drift_penalty = 0.2
        elif drift_summary['status'] == 'CRITICAL':
            drift_penalty = 0.5
        
        prediction_penalty = 0.0
        if prediction_summary['status'] == 'DEGRADED':
            prediction_penalty = 0.2
        elif prediction_summary['status'] == 'CRITICAL':
            prediction_penalty = 0.5
        
        self.health_score = max(0, 1.0 - drift_penalty - prediction_penalty)
        
        # Gather alerts
        self.overall_alerts = []
        
        drift_alerts = self.distribution_monitor.check_drift_alerts()
        self.overall_alerts.extend(drift_alerts)
        
        prediction_alerts = self.prediction_monitor.check_prediction_alerts()
        self.overall_alerts.extend(prediction_alerts)
        
        self.last_health_check = datetime.now()
        
        return ModelHealthStatus(
            model_name=self.model_name,
            status=status,
            drift_detected=drift_summary['status'] != 'HEALTHY',
            accuracy_score=prediction_summary.get('current_accuracy', 0.0),
            prediction_variance=prediction_summary.get('mse', 0.0),
            last_calibration=None,
            last_update=datetime.now()
        )
    
    def get_model_health_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive model health summary
        """
        return {
            'model_name': self.model_name,
            'status': self.status,
            'health_score': self.health_score,
            'last_check': self.last_health_check.isoformat() if self.last_health_check else None,
            'distribution_health': self.distribution_monitor.get_drift_summary(),
            'prediction_health': self.prediction_monitor.get_performance_summary(),
            'active_alerts': len(self.overall_alerts),
            'recent_alerts': self.overall_alerts[-10:]
        }
    
    def should_retrain(self) -> Tuple[bool, str]:
        """
        Determine if model should be retrained based on health metrics
        """
        if self.status == 'CRITICAL':
            return True, 'Model status is CRITICAL'
        
        if self.health_score < 0.5:
            return True, f'Health score below threshold: {self.health_score:.2f}'
        
        drift_summary = self.distribution_monitor.get_drift_summary()
        if drift_summary['max_drift'] > 0.3:
            return True, f'Feature drift exceeds threshold: {drift_summary["max_drift"]:.2f}'
        
        prediction_summary = self.prediction_monitor.get_performance_summary()
        if prediction_summary.get('accuracy_trend') == 'DEGRADING':
            return True, 'Accuracy is degrading'
        
        if prediction_summary.get('current_accuracy', 0) < 0.45:
            return True, f'Accuracy below threshold: {prediction_summary["current_accuracy"]:.2f}'
        
        return False, 'Model is healthy'
    
    def save_state(self, filepath: str):
        """
        Save monitoring state to file
        """
        state = {
            'model_name': self.model_name,
            'status': self.status,
            'health_score': self.health_score,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
            'drift_scores': self.distribution_monitor.drift_scores,
            'baseline_statistics': self.distribution_monitor.baseline_statistics,
            'performance_history': self.prediction_monitor.performance_history[-100:]
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2, default=str)
        
        logger.info(f"ML model monitor state saved to {filepath}")
    
    def load_state(self, filepath: str):
        """
        Load monitoring state from file
        """
        if not os.path.exists(filepath):
            logger.warning(f"State file {filepath} not found")
            return
        
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        self.model_name = state['model_name']
        self.status = state['status']
        self.health_score = state['health_score']
        if state.get('last_health_check'):
            self.last_health_check = datetime.fromisoformat(state['last_health_check'])
        
        self.distribution_monitor.drift_scores = state.get('drift_scores', {})
        self.distribution_monitor.baseline_statistics = state.get('baseline_statistics', {})
        self.prediction_monitor.performance_history = state.get('performance_history', [])
        
        logger.info(f"ML model monitor state loaded from {filepath}")

class EnsembleMonitor:
    """
    Monitors multiple ML models in an ensemble
    """
    
    def __init__(self):
        self.models = {}
    
    def register_model(self, model_name: str) -> MLModelMonitor:
        """
        Register a new model for monitoring
        """
        monitor = MLModelMonitor(model_name)
        self.models[model_name] = monitor
        
        logger.info(f"Registered model for monitoring: {model_name}")
        
        return monitor
    
    def get_model_monitor(self, model_name: str) -> Optional[MLModelMonitor]:
        """
        Get monitor for a specific model
        """
        return self.models.get(model_name)
    
    def check_ensemble_health(self) -> Dict[str, Any]:
        """
        Check health of entire ensemble
        """
        if not self.models:
            return {'status': 'NO_MODELS'}
        
        healthy_models = sum(1 for m in self.models.values() if m.status == 'HEALTHY')
        degraded_models = sum(1 for m in self.models.values() if m.status == 'DEGRADED')
        critical_models = sum(1 for m in self.models.values() if m.status == 'CRITICAL')
        
        avg_health_score = np.mean([m.health_score for m in self.models.values()])
        
        # Determine ensemble status
        if critical_models > 0:
            status = 'CRITICAL'
        elif degraded_models > len(self.models) / 2:
            status = 'DEGRADED'
        else:
            status = 'HEALTHY'
        
        return {
            'status': status,
            'total_models': len(self.models),
            'healthy_models': healthy_models,
            'degraded_models': degraded_models,
            'critical_models': critical_models,
            'average_health_score': avg_health_score,
            'model_details': {name: m.get_model_health_summary() for name, m in self.models.items()}
        }
    
    def get_models_needing_retrain(self) -> List[Tuple[str, str]]:
        """
        Get list of models that need retraining
        """
        needs_retrain = []
        
        for model_name, monitor in self.models.items():
            should_retrain, reason = monitor.should_retrain()
            if should_retrain:
                needs_retrain.append((model_name, reason))
        
        return needs_retrain

def create_ml_model_monitor(model_name: str) -> MLModelMonitor:
    """
    Factory function to create ML model monitor
    """
    return MLModelMonitor(model_name)

def create_ensemble_monitor() -> EnsembleMonitor:
    """
    Factory function to create ensemble monitor
    """
    return EnsembleMonitor()