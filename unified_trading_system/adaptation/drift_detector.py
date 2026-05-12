"""
Adaptation Layer for Unified Trading System
Combines LVR's learning system with Autonomous System's drift detection and adaptation
"""


import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import deque
import hashlib
import json
import time


class AdaptationType(Enum):
    """Types of adaptation"""
    DRIFT_DETECTION = "DRIFT_DETECTION"
    MODEL_UPDATE = "MODEL_UPDATE"
    REGIME_ADAPTATION = "REGIME_ADAPTATION"
    PARAMETER_TUNING = "PARAMETER_TUNING"


@dataclass
class AdaptationEvent:
    """Event indicating system adaptation is needed"""
    adaptation_type: AdaptationType
    trigger_reason: str
    confidence: float  # 0-1, confidence in adaptation need
    suggested_actions: List[str]
    timestamp: int  # nanoseconds since epoch
    metadata: Dict[str, Any] = field(default_factory=dict)


class DriftDetector:
    """
    Unified Drift Detector combining:
    1. LVR's concept drift detection
    2. Autonomous System's KL-divergence based drift detection
    3. Statistical process control for early warning
    """
    
    def __init__(
        self,
        tau_drift: float = 0.1,           # KL divergence drift threshold
        warning_threshold: float = 0.05,   # Early warning threshold
        window_size: int = 100,            # Window for computing statistics
        min_samples: int = 30              # Minimum samples needed
    ):
        self.tau_drift = tau_drift
        self.warning_threshold = warning_threshold
        self.window_size = window_size
        self.min_samples = min_samples
        
        # Reference distribution (training/live baseline)
        self.reference_data = []
        self.reference_mean = None
        self.reference_std = None
        
        # Current window data
        self.current_data = []
        
        # Historical drift scores for trend analysis
        self.drift_history = []
        
        # Adaptation history
        self.adaptation_history = []
        
        # Is detector initialized
        self.is_initialized = False
    
    def initialize_reference(self, data: List[float]):
        """Initialize reference distribution from training data"""
        if len(data) < self.min_samples:
            raise ValueError(f"Need at least {self.min_samples} samples to initialize reference")
        
        self.reference_data = data.copy()
        self.reference_mean = np.mean(data)
        self.reference_std = np.std(data)
        self.is_initialized = True
        
        # Also set as current data initially
        self.current_data = data.copy()
    
    def update(self, new_data: List[float]) -> Tuple[bool, float, Dict]:
        """
        Update drift detection with new data
        
        Args:
            new_data: New observations
            
        Returns:
            Tuple of (drift_detected, drift_score, diagnostic_info)
        """
        if not self.is_initialized:
            # If not initialized, treat new data as reference
            self.initialize_reference(new_data)
            return False, 0.0, {"status": "initialized_as_reference"}
        
        # Add new data to current window
        self.current_data.extend(new_data)
        
        # Keep window size bounded
        if len(self.current_data) > self.window_size:
            self.current_data = self.current_data[-self.window_size:]
        
        # Need minimum samples for detection
        if len(self.current_data) < self.min_samples:
            return False, 0.0, {"status": "insufficient_samples", "current_samples": len(self.current_data)}
        
        # Compute drift score using multiple methods
        kl_divergence = self._compute_kl_divergence()
        wasserstein_distance = self._compute_wasserstein_distance()
        ks_statistic = self._compute_ks_statistic()
        
        # Combined drift score (weighted average)
        drift_score = (
            0.5 * kl_divergence +
            0.3 * wasserstein_distance +
            0.2 * ks_statistic
        )
        
        # Determine if drift is detected
        drift_detected = drift_score > self.tau_drift
        warning_issued = drift_score > self.warning_threshold
        
        # Update drift history
        self.drift_history.append(drift_score)
        if len(self.drift_history) > 1000:
            self.drift_history = self.drift_history[-500:]
        
        # Diagnostic information
        diagnostic_info = {
            "kl_divergence": kl_divergence,
            "wasserstein_distance": wasserstein_distance,
            "ks_statistic": ks_statistic,
            "drift_score": drift_score,
            "tau_drift": self.tau_drift,
            "warning_threshold": self.warning_threshold,
            "drift_detected": drift_detected,
            "warning_issued": warning_issued,
            "reference_mean": self.reference_mean,
            "reference_std": self.reference_std,
            "current_mean": np.mean(self.current_data),
            "current_std": np.std(self.current_data),
            "reference_size": len(self.reference_data),
            "current_size": len(self.current_data),
            "drift_trend": self._compute_drift_trend()
        }
        
        # If drift detected, record adaptation event
        if drift_detected:
            adaptation_event = self._create_adaptation_event(drift_score, diagnostic_info)
            self.adaptation_history.append(adaptation_event)
            
            # Keep adaptation history bounded
            if len(self.adaptation_history) > 100:
                self.adaptation_history = self.adaptation_history[-50:]
        
        return drift_detected, drift_score, diagnostic_info
    
    def _compute_kl_divergence(self) -> float:
        """Compute KL divergence between reference and current distributions"""
        # Discretize distributions for KL divergence calculation
        try:
            # Create histogram bins based on reference data range
            if self.reference_std > 0:
                bin_width = self.reference_std / 5  # 5 bins per std dev
                bins = np.arange(
                    self.reference_mean - 3 * self.reference_std,
                    self.reference_mean + 4 * self.reference_std,
                    bin_width
                )
            else:
                # Fallback if std dev is zero
                bins = np.linspace(-1, 1, 21)
            
            # Compute histograms
            ref_hist, _ = np.histogram(self.reference_data, bins=bins, density=True)
            curr_hist, _ = np.histogram(self.current_data, bins=bins, density=True)
            
            # Add small epsilon to avoid zeros
            epsilon = 1e-10
            ref_hist = ref_hist + epsilon
            curr_hist = curr_hist + epsilon
            
            # Renormalize
            ref_hist = ref_hist / np.sum(ref_hist)
            curr_hist = curr_hist / np.sum(curr_hist)
            
            # Compute KL divergence: sum(p * log(p/q))
            kl_div = np.sum(ref_hist * np.log(ref_hist / curr_hist))
            
            return max(kl_div, 0.0)  # KL divergence is non-negative
            
        except Exception:
            # Fallback to simpler method if histogram fails
            return self._simple_distance_metric()
    
    def _compute_wasserstein_distance(self) -> float:
        """Compute Wasserstein distance (Earth Mover's Distance)"""
        try:
            # 1-D Wasserstein distance is L1 distance between CDFs
            # Sort both datasets
            ref_sorted = np.sort(self.reference_data)
            curr_sorted = np.sort(self.current_data)
            
            # Interpolate to common quantiles
            n_quantiles = min(len(ref_sorted), len(curr_sorted), 100)
            if n_quantiles < 2:
                return 0.0
            
            ref_quantiles = np.percentile(ref_sorted, np.linspace(0, 100, n_quantiles))
            curr_quantiles = np.percentile(curr_sorted, np.linspace(0, 100, n_quantiles))
            
            # Wasserstein distance is L1 distance between quantile functions
            wasserstein = np.mean(np.abs(ref_quantiles - curr_quantiles))
            
            return wasserstein
            
        except Exception:
            return self._simple_distance_metric()
    
    def _compute_ks_statistic(self) -> float:
        """Compute Kolmogorov-Smirnov statistic"""
        try:
            from scipy import stats
            ks_stat, _ = stats.ks_2samp(self.reference_data, self.current_data)
            return ks_stat
        except ImportError:
            # Fallback implementation
            return self._simple_distance_metric()
        except Exception:
            return self._simple_distance_metric()
    
    def _simple_distance_metric(self) -> float:
        """Simple distance metric as fallback"""
        if self.reference_std == 0:
            return 0.0
        
        ref_mean = self.reference_mean
        curr_mean = np.mean(self.current_data)
        
        # Normalized absolute difference
        distance = abs(curr_mean - ref_mean) / self.reference_std
        return distance
    
    def _compute_drift_trend(self) -> str:
        """Compute trend in drift scores"""
        if len(self.drift_history) < 5:
            return "insufficient_data"
        
        # Simple linear trend on recent drift scores
        recent_scores = self.drift_history[-10:]  # Last 10 scores
        x = np.arange(len(recent_scores))
        try:
            slope = np.polyfit(x, recent_scores, 1)[0]
            if slope > 0.01:
                return "increasing"
            elif slope < -0.01:
                return "decreasing"
            else:
                return "stable"
        except:
            return "unknown"
    
    def _create_adaptation_event(
        self, 
        drift_score: float, 
        diagnostic_info: Dict
    ) -> AdaptationEvent:
        """Create adaptation event when drift is detected"""
        # Determine adaptation type based on drift characteristics
        if drift_score > self.tau_drift * 2:
            adaptation_type = AdaptationType.MODEL_UPDATE
            trigger_reason = "Significant distribution drift detected"
            confidence = min(drift_score / (self.tau_drift * 3), 1.0)
        elif drift_score > self.tau_drift:
            adaptation_type = AdaptationType.DRIFT_DETECTION
            trigger_reason = "Moderate distribution drift detected"
            confidence = min(drift_score / self.tau_drift, 1.0)
        else:
            adaptation_type = AdaptationType.PARAMETER_TUNING
            trigger_reason = "Minor statistical deviation detected"
            confidence = drift_score / self.tau_drift
        
        # Suggested actions based on drift type and magnitude
        suggested_actions = []
        if adaptation_type == AdaptationType.MODEL_UPDATE:
            suggested_actions.extend([
                "Retrain models with recent data",
                "Consider feature engineering updates",
                "Validate with out-of-sample testing"
            ])
        elif adaptation_type == AdaptationType.DRIFT_DETECTION:
            suggested_actions.extend([
                "Increase model validation frequency",
                "Consider ensemble methods",
                "Monitor performance closely"
            ])
        else:
            suggested_actions.extend([
                "Fine-tune hyperparameters",
                "Check data quality",
                "Validate assumptions"
            ])
        
        # Add regime-specific suggestions if available
        if "current_mean" in diagnostic_info and "reference_mean" in diagnostic_info:
            mean_shift = diagnostic_info["current_mean"] - diagnostic_info["reference_mean"]
            if abs(mean_shift) > 0.5 * diagnostic_info.get("reference_std", 1.0):
                suggested_actions.append("Significant mean shift detected - check for regime change")
        
        return AdaptationEvent(
            adaptation_type=adaptation_type,
            trigger_reason=trigger_reason,
            confidence=confidence,
            suggested_actions=suggested_actions,
            timestamp=int(time.time() * 1e9),
            metadata=diagnostic_info
        )
    
    def get_adaptation_history(self) -> List[AdaptationEvent]:
        """Get history of adaptation events"""
        return self.adaptation_history.copy()
    
    def get_drift_diagnostics(self) -> Dict:
        """Get current drift diagnostics"""
        if len(self.drift_history) == 0:
            return {
                "status": "no_data",
                "samples_in_reference": len(self.reference_data) if hasattr(self, 'reference_data') else 0,
                "samples_in_current": len(self.current_data) if hasattr(self, 'current_data') else 0
            }
        
        recent_drift = self.drift_history[-1] if self.drift_history else 0.0
        avg_drift = np.mean(self.drift_history[-10:]) if len(self.drift_history) >= 10 else np.mean(self.drift_history) if self.drift_history else 0.0
        
        return {
            "current_drift_score": recent_drift,
            "average_drift_score": avg_drift,
            "drift_detected": recent_drift > self.tau_drift,
            "warning_level": recent_drift > self.warning_threshold,
            "tau_drift": self.tau_drift,
            "warning_threshold": self.warning_threshold,
            "samples_in_reference": len(self.reference_data),
            "samples_in_current": len(self.current_data),
            "drift_trend": self._compute_drift_trend()
        }


class ModelAdapter:
    """
    Model Adapter for updating models based on drift detection
    Combines LVR's adaptive learning with Autonomous System's offline RL updates
    """
    
    def __init__(self):
        self.adaptation_history = []
        self.model_versions = []
        self.performance_history = []
    
    def adapt_model(
        self,
        current_model: Any,
        adaptation_event: AdaptationEvent,
        new_data: List[Dict],
        performance_feedback: Dict = None
    ) -> Tuple[Any, Dict]:
        """
        Adapt model based on adaptation event
        
        Args:
            current_model: Current model to adapt
            adaptation_event: Event triggering adaptation
            new_data: Recent data for retraining
            performance_feedback: Feedback on current model performance
            
        Returns:
            Tuple of (adapted_model, adaptation_info)
        """
        adaptation_info = {
            "timestamp": int(time.time() * 1e9),
            "adaptation_type": adaptation_event.adaptation_type.value,
            "trigger_reason": adaptation_event.trigger_reason,
            "confidence": adaptation_event.confidence,
            "actions_taken": [],
            "performance_before": performance_feedback or {},
            "model_version_before": getattr(current_model, "version", "unknown")
        }
        
        # Based on adaptation type, take appropriate actions
        if adaptation_event.adaptation_type == AdaptationType.DRIFT_DETECTION:
            # Mild drift: increase validation frequency, monitor closely
            adapted_model = self._apply_mild_adaptation(current_model, adaptation_event)
            adaptation_info["actions_taken"].append("increased_validation_frequency")
            adaptation_info["actions_taken"].append("enhanced_monitoring")
            
        elif adaptation_event.adaptation_type == AdaptationType.MODEL_UPDATE:
            # Significant drift: retrain or update model
            adapted_model = self._retrain_model(current_model, new_data, adaptation_event)
            adaptation_info["actions_taken"].append("model_retrained")
            adaptation_info["actions_taken"].append("validation_updated")
            
        elif adaptation_event.adaptation_type == AdaptationType.REGIME_ADAPTATION:
            # Regime change: adjust model parameters or switch models
            adapted_model = self._adapt_for_regime_change(current_model, adaptation_event, new_data)
            adaptation_info["actions_taken"].append("regime_adaptation_applied")
            
        else:  # PARAMETER_TUNING
            # Minor adaptation: fine-tune hyperparameters
            adapted_model = self._fine_tune_hyperparameters(current_model, adaptation_event, new_data)
            adaptation_info["actions_taken"].append("hyperparameters_fine_tuned")
        
        # Record adaptation
        self.adaptation_history.append(adaptation_info)
        self.model_versions.append(getattr(adapted_model, "version", "unknown"))
        
        # Keep history bounded
        if len(self.adaptation_history) > 100:
            self.adaptation_history = self.adaptation_history[-50:]
        if len(self.model_versions) > 100:
            self.model_versions = self.model_versions[-50:]
        
        adaptation_info["model_version_after"] = getattr(adapted_model, "version", "unknown")
        
        return adapted_model, adaptation_info
    
    def _apply_mild_adaptation(self, model: Any, event: AdaptationEvent) -> Any:
        """Apply mild adaptation for drift detection"""
        # In practice, this might:
        # - Increase validation frequency
        # - Adjust confidence thresholds
        # - Enable additional monitoring
        # For now, return the model unchanged but log the adaptation
        return model
    
    def _retrain_model(self, model: Any, new_data: List[Dict], event: AdaptationEvent) -> Any:
        """Retrain model with new data"""
        # In practice, this would:
        # 1. Prepare training data from new_data
        # 2. Retrain model parameters
        # 3. Validate on hold-out set
        # 4. Update model version
        
        # For demonstration, we'll simulate by updating a version attribute
        if hasattr(model, "version"):
            # Increment version number
            try:
                version_parts = model.version.split(".")
                if len(version_parts) >= 3:
                    version_parts[-1] = str(int(version_parts[-1]) + 1)
                    model.version = ".".join(version_parts)
                else:
                    model.version = "1.0.1"
            except:
                model.version = "1.0.1"
        else:
            model.version = "1.0.1"
        
        # Simulate training time
        # time.sleep(0.1)  # Would be actual training time
        
        return model
    
    def _adapt_for_regime_change(
        self, 
        model: Any, 
        event: AdaptationEvent, 
        new_data: List[Dict]
    ) -> Any:
        """Adapt model for regime change"""
        # In practice, this might:
        # 1. Switch to regime-specific model
        # 2. Adjust model architecture
        # 3. Change feature set
        # 4. Update priors in Bayesian models
        
        # For demonstration, add regime adaptation marker
        if not hasattr(model, "adaptations"):
            model.adaptations = []
        model.adaptations.append({
            "type": "regime_adaptation",
            "timestamp": int(time.time() * 1e9),
            "trigger": event.trigger_reason
        })
        
        return model
    
    def _fine_tune_hyperparameters(
        self, 
        model: Any, 
        event: AdaptationEvent, 
        new_data: List[Dict]
    ) -> Any:
        """Fine-tune hyperparameters"""
        # In practice, this would:
        # 1. Run hyperparameter optimization
        # 2. Validate on validation set
        # 3. Update model with best parameters
        
        # For demonstration, add hyperparameter tuning marker
        if not hasattr(model, "hyperparameter_history"):
            model.hyperparameter_history = []
        model.hyperparameter_history.append({
            "timestamp": int(time.time() * 1e9),
            "trigger": event.trigger_reason,
            "adaptation_confidence": event.confidence
        })
        
        return model


class AdaptationLayer:
    """
    Unified Adaptation Layer that coordinates drift detection and model adaptation
    """
    
    def __init__(
        self,
        tau_drift: float = 0.1,
        warning_threshold: float = 0.05
    ):
        self.drift_detector = DriftDetector(tau_drift=tau_drift, warning_threshold=warning_threshold)
        self.model_adapter = ModelAdapter()
        
        # Track what we're monitoring for drift
        self.monitored_metrics = {
            "belief_state_entropy": [],
            "prediction_errors": [],
            "feature_distributions": {},
            "performance_metrics": []
        }
        
        # Adaptation state
        self.is_adapting = False
        self.last_adaptation_time = 0
        self.adaptation_cooldown = 300  # 5 minutes minimum between adaptations
    
    def update_and_check_adaptation(
        self,
        belief_state: Dict,
        prediction_errors: List[float],
        feature_data: Dict[str, List[float]],
        performance_metrics: List[float],
        current_model: Any = None
    ) -> Tuple[bool, List[AdaptationEvent], Any]:
        """
        Update adaptation layer and check if adaptation is needed
        
        Returns:
            Tuple of (adaptation_occurred, adaptation_events, potentially_updated_model)
        """
        current_time = int(time.time() * 1e9)
        
        # Check cooldown period
        if (current_time - self.last_adaptation_time) < self.adaptation_cooldown * 1e9:
            # Still in cooldown, don't adapt
            return False, [], current_model
        
        adaptation_events = []
        adapted_model = current_model
        
        # 1. Check belief state entropy for drift
        entropy = belief_state.get("entropy", 0.0)
        if entropy > 0:  # Only check if we have entropy data
            self.monitored_metrics["belief_state_entropy"].append(entropy)
            # Keep window bounded
            if len(self.monitored_metrics["belief_state_entropy"]) > 1000:
                self.monitored_metrics["belief_state_entropy"] = self.monitored_metrics["belief_state_entropy"][-500:]
            
            drift_detected, drift_score, diagnostics = self.drift_detector.update(
                self.monitored_metrics["belief_state_entropy"]
            )
            if drift_detected:
                event = self.drift_detector._create_adaptation_event(drift_score, diagnostics)
                adaptation_events.append(event)
        
        # 2. Check prediction errors for drift
        if prediction_errors:
            self.monitored_metrics["prediction_errors"].extend(prediction_errors)
            # Keep window bounded
            if len(self.monitored_metrics["prediction_errors"]) > 1000:
                self.monitored_metrics["prediction_errors"] = self.monitored_metrics["prediction_errors"][-500:]
            
            drift_detected, drift_score, diagnostics = self.drift_detector.update(
                self.monitored_metrics["prediction_errors"]
            )
            if drift_detected:
                event = self.drift_detector._create_adaptation_event(drift_score, diagnostics)
                adaptation_events.append(event)
        
        # 3. Check feature distributions for drift
        for feature_name, values in feature_data.items():
            if feature_name not in self.monitored_metrics["feature_distributions"]:
                self.monitored_metrics["feature_distributions"][feature_name] = []
            
            self.monitored_metrics["feature_distributions"][feature_name].extend(values)
            # Keep window bounded
            if len(self.monitored_metrics["feature_distributions"][feature_name]) > 1000:
                self.monitored_metrics["feature_distributions"][feature_name] = \
                    self.monitored_metrics["feature_distributions"][feature_name][-500:]
            
            # Initialize detector for this feature if needed
            feature_key = f"feature_{feature_name}"
            if feature_key not in self.monitored_metrics or not self.monitored_metrics[feature_key]:
                # Initialize with first batch of data
                initial_data = self.monitored_metrics["feature_distributions"][feature_name][:min(50, len(self.monitored_metrics["feature_distributions"][feature_name]))]
                if len(initial_data) >= 30:  # Minimum samples
                    try:
                        # Would create a detector for this feature in practice
                        pass
                    except:
                        pass  # Skip if initialization fails
            
            # For simplicity, we'll just check the first few features
            if len(adaptation_events) < 2:  # Limit to avoid too many adaptations at once
                # Simplified check: just look at mean shift
                feature_values = self.monitored_metrics["feature_distributions"][feature_name]
                if len(feature_values) >= 30:
                    # Simple mean-based check (would use proper drift detector in practice)
                    recent_mean = np.mean(feature_values[-20:]) if len(feature_values) >= 20 else np.mean(feature_values)
                    # Would compare to reference mean in practice
        
        # 4. Check performance metrics for drift
        if performance_metrics:
            self.monitored_metrics["performance_metrics"].extend(performance_metrics)
            # Keep window bounded
            if len(self.monitored_metrics["performance_metrics"]) > 1000:
                self.monitored_metrics["performance_metrics"] = self.monitored_metrics["performance_metrics"][-500:]
            
            drift_detected, drift_score, diagnostics = self.drift_detector.update(
                self.monitored_metrics["performance_metrics"]
            )
            if drift_detected:
                event = self.drift_detector._create_adaptation_event(drift_score, diagnostics)
                adaptation_events.append(event)
        
        # If any adaptations triggered, apply them
        if adaptation_events and current_model is not None:
            # Sort by confidence (highest first)
            adaptation_events.sort(key=lambda x: x.confidence, reverse=True)
            
            # Apply the most confident adaptation
            primary_event = adaptation_events[0]
            self.is_adapting = True
            
            try:
                # Prepare recent data for adaptation
                recent_data = []
                recent_data.extend(self.monitored_metrics["belief_state_entropy"][-50:])
                recent_data.extend(self.monitored_metrics["prediction_errors"][-50:])
                recent_data.extend(self.monitored_metrics["performance_metrics"][-50:])
                
                # Adapt model
                adapted_model, adaptation_info = self.model_adapter.adapt_model(
                    current_model, primary_event, recent_data
                )
                
                # Record that adaptation occurred
                self.last_adaptation_time = current_time
                self.is_adapting = False
                
                # Add adaptation info to events
                for event in adaptation_events:
                    event.metadata["adaptation_applied"] = True
                    event.metadata["adaptation_info"] = adaptation_info
                    
            except Exception as e:
                # If adaptation fails, log error and continue with original model
                self.is_adapting = False
                print(f"Adaptation failed: {e}")
                # Still return the events so they can be logged/monitored
        
        adaptation_occurred = len(adaptation_events) > 0
        
        return adaptation_occurred, adaptation_events, adapted_model
    
    def get_adaptation_status(self) -> Dict:
        """Get current adaptation status"""
        return {
            "is_adapting": self.is_adapting,
            "last_adaptation_time": self.last_adaptation_time,
            "adaptation_cooldown_seconds": self.adaptation_cooldown / 1e9,
            "time_since_last_adaptation": (int(time.time() * 1e9) - self.last_adaptation_time) / 1e9 if self.last_adaptation_time > 0 else 0,
            "drift_detector_diagnostics": self.drift_detector.get_drift_diagnostics(),
            "recent_adaptations": [
                {
                    "type": event.adaptation_type.value,
                    "reason": event.trigger_reason,
                    "confidence": event.confidence,
                    "timestamp": event.timestamp
                }
                for event in self.drift_detector.get_adaptation_history()[-5:]  # Last 5 adaptations
            ]
        }


# Example usage and testing
if __name__ == "__main__":
    import time
    
    # Create adaptation layer
    adaptation_layer = AdaptationLayer(
        tau_drift=0.1,
        warning_threshold=0.05
    )
    
    # Simulate a model (simple class for demonstration)
    class SimpleModel:
        def __init__(self):
            self.version = "1.0.0"
            self.parameters = {"learning_rate": 0.01, "threshold": 0.5}
    
    model = SimpleModel()
    
    print("Adaptation Layer Demo:")
    print("=" * 30)
    
    # Initialize drift detector with reference data (simulating training period)
    print("Initializing reference distribution...")
    reference_data = np.random.normal(0, 1, 50)  # Normal distribution N(0,1)
    adaptation_layer.drift_detector.initialize_reference(reference_data.tolist())
    print(f"Reference initialized: mean={np.mean(reference_data):.3f}, std={np.std(reference_data):.3f}")
    
    # Simulate normal operation (no drift)
    print("\nSimulating normal operation...")
    for i in range(5):
        belief_state = {
            "entropy": 0.5 + 0.1 * np.random.random(),  # Entropy around 0.5
            "confidence": 0.7 + 0.2 * np.random.random()
        }
        prediction_errors = np.random.normal(0, 0.1, 5).tolist()  # Small errors
        feature_data = {
            "ofI": np.random.normal(0, 0.2, 5).tolist(),
            "volatility": np.abs(np.random.normal(0.1, 0.02, 5)).tolist()
        }
        performance_metrics = np.random.normal(0.001, 0.002, 5).tolist()  # Small positive returns
        
        occurred, events, updated_model = adaptation_layer.update_and_check_adaptation(
            belief_state=belief_state,
            prediction_errors=prediction_errors,
            feature_data=feature_data,
            performance_metrics=performance_metrics,
            current_model=model
        )
        
        if occurred:
            print(f"Adaptation triggered! {len(events)} events")
            for event in events:
                print(f"  - {event.adaptation_type.value}: {event.trigger_reason}")
        else:
            print(f"No adaptation needed (check {i+1}/5)")
        
        model = updated_model  # Use potentially updated model
        time.sleep(0.01)
    
    # Simulate drift conditions (change in distribution)
    print("\nSimulating drift conditions...")
    for i in range(5):
        # Gradually shift the distribution
        shift_amount = 0.3 * (i + 1) / 5  # Up to 0.3 shift
        belief_state = {
            "entropy": 0.6 + 0.1 * np.random.random(),  # Slightly higher entropy
            "confidence": 0.6 - 0.1 * (i / 5)  # Decreasing confidence
        }
        # Prediction errors with increasing mean and variance
        prediction_errors = np.random.normal(shift_amount, 0.1 + 0.1 * i, 5).tolist()
        feature_data = {
            "ofI": np.random.normal(shift_amount * 0.5, 0.25, 5).tolist(),
            "volatility": np.abs(np.random.normal(0.15 + shift_amount * 0.3, 0.03, 5)).tolist()
        }
        # Performance degrading
        performance_metrics = np.random.normal(-0.001 * (i + 1), 0.003, 5).tolist()
        
        occurred, events, updated_model = adaptation_layer.update_and_check_adaptation(
            belief_state=belief_state,
            prediction_errors=prediction_errors,
            feature_data=feature_data,
            performance_metrics=performance_metrics,
            current_model=model
        )
        
        if occurred:
            print(f"DRIFT DETECTED! {len(events)} adaptation events:")
            for event in events:
                print(f"  - {event.adaptation_type.value}: {event.trigger_reason}")
                print(f"    Confidence: {event.confidence:.3f}")
                print(f"    Actions: {', '.join(event.suggested_actions[:2])}...")
        else:
            print(f"No adaptation (check {i+1}/5)")
        
        model = updated_model  # Use potentially updated model
        time.sleep(0.01)
    
    # Show final status
    print("\nFinal Adaptation Status:")
    status = adaptation_layer.get_adaptation_status()
    print(f"Currently adapting: {status['is_adapting']}")
    print(f"Time since last adaptation: {status['time_since_last_adaptation']:.1f} seconds")
    print(f"Drift detected: {status['drift_detector_diagnostics']['drift_detected']}")
    print(f"Current drift score: {status['drift_detector_diagnostics']['current_drift_score']:.4f}")
    print(f"Model version: {model.version}")
    if hasattr(model, "adaptations"):
        print(f"Model adaptations: {len(model.adaptations)}")
    if hasattr(model, "hyperparameter_history"):
        print(f"Hyperparameter updates: {len(model.hyperparameter_history)}")