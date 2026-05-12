"""
Lyapunov-Stable Aggression Controller for Unified Trading System
Implements the core decision-making component from the Autonomous System
with integration of LVR's signal processing and risk management
"""


import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import time


@dataclass
class AggressionState:
    """State of the aggression controller"""
    aggression_level: float          # Current aggression level [0, 1]
    aggression_rate: float          # Rate of change of aggression
    signal_strength: float          # Input signal strength
    risk_gradient: float            # Gradient of risk with respect to aggression
    execution_feedback: float       # Feedback from execution quality
    timestamp: int                  # Nanoseconds since epoch


class AggressionController:
    """
    Lyapunov-stable aggression controller implementing:
    dα/dt = f(z_t, signal_strength) − κ·α_t − λ·∇R_t + η·ExecutionFeedback_t
    
    With stability guarantees via Lyapunov function V(α) = (α - α_target)²/2
    """
    
    def __init__(
        self,
        kappa: float = 0.1,           # Aggression decay rate
        lambda_: float = 0.05,        # Risk gradient sensitivity
        beta_max: float = 0.5,        # Maximum aggression change rate
        eta: float = 0.01,            # Execution feedback gain
        alpha_target: float = 0.5     # Target aggression level
    ):
        self.kappa = kappa
        self.lambda_ = lambda_
        self.beta_max = beta_max
        self.eta = eta
        self.alpha_target = alpha_target
        
        # State variables
        self.aggression_level = alpha_target
        self.aggression_rate = 0.0
        self.last_update_time = int(time.time() * 1e9)
        
        # For stability monitoring
        self.lyapunov_history = []
        
    def update(
        self,
        belief_state: Dict,
        signal_strength: float,
        execution_feedback: float = 0.0,
        dt: Optional[float] = None
    ) -> AggressionState:
        """
        Update aggression level based on belief state and inputs
        
        Args:
            belief_state: Current belief state from perception layer
            signal_strength: Trading signal strength (from LVR's alpha processor)
            execution_feedback: Feedback from execution quality
            dt: Time step (if None, computed from timestamp)
            
        Returns:
            Updated aggression state
        """
        current_time = int(time.time() * 1e9)
        
        # Compute time step if not provided
        if dt is None:
            if self.last_update_time > 0:
                dt = (current_time - self.last_update_time) / 1e9  # Convert to seconds
            else:
                dt = 0.01  # Default 10ms
        
        # Extract components from belief state
        expected_return = belief_state.get("expected_return", 0.0)
        total_uncertainty = belief_state.get("aleatoric_uncertainty", 0.0) + \
                           belief_state.get("epistemic_uncertainty", 0.0)
        
        # Compute risk gradient (∇R_t) - how risk changes with aggression
        risk_gradient = self._compute_risk_gradient(belief_state)
        
        # Compute signal processing function f(z_t, signal_strength)
        # This combines the expected return signal with uncertainty weighting
        signal_processing = self._compute_signal_processing(
            expected_return, 
            total_uncertainty, 
            signal_strength
        )
        
        # Compute aggression dynamics
        # dα/dt = f(z_t, signal_strength) − κ·α_t − λ·∇R_t + η·ExecutionFeedback_t
        aggression_derivative = (
            signal_processing 
            - self.kappa * self.aggression_level 
            - self.lambda_ * risk_gradient 
            + self.eta * execution_feedback
        )
        
        # Apply rate limiting: |dα/dt| ≤ β_max
        aggression_derivative = np.clip(
            aggression_derivative, 
            -self.beta_max, 
            self.beta_max
        )
        
        # Update aggression level (Euler integration)
        new_aggression = self.aggression_level + aggression_derivative * dt
        
        # Ensure aggression stays in bounds [0, 1]
        new_aggression = np.clip(new_aggression, 0.0, 1.0)
        
        # Compute actual rate of change
        actual_rate = (new_aggression - self.aggression_level) / dt if dt > 0 else 0.0
        
        # Update state
        self.aggression_level = new_aggression
        self.aggression_rate = actual_rate
        self.last_update_time = current_time
        
        # Compute Lyapunov function for stability monitoring
        lyapunov = self._compute_lyapunov_function()
        self.lyapunov_history.append(lyapunov)
        # Keep history bounded
        if len(self.lyapunov_history) > 1000:
            self.lyapunov_history = self.lyapunov_history[-1000:]
        
        # Create and return aggression state
        aggression_state = AggressionState(
            aggression_level=self.aggression_level,
            aggression_rate=self.aggression_rate,
            signal_strength=signal_strength,
            risk_gradient=risk_gradient,
            execution_feedback=execution_feedback,
            timestamp=current_time
        )
        
        return aggression_state
    
    def _compute_signal_processing(
        self, 
        expected_return: float, 
        total_uncertainty: float, 
        signal_strength: float
    ) -> float:
        """
        Compute the signal processing function f(z_t, signal_strength)
        This transforms the raw signal into aggression-driving component
        """
        # Signal strength weighting by expected return and uncertainty
        # Higher expected return increases aggression response to signal
        # Higher uncertainty decreases aggression response to signal (more cautious)
        
        # Normalize expected return to [-1, 1] range (typical returns)
        normalized_return = np.tanh(expected_return * 10)  # Scale factor for tanh
        
        # Uncertainty weighting: higher uncertainty reduces signal response
        uncertainty_weight = np.exp(-total_uncertainty * 5)  # Exponential decay
        
        # Combine signal strength with return expectation and uncertainty
        signal_processing = (
            signal_strength * 
            (0.5 + 0.5 * normalized_return) *  # Bias toward positive signals when expected return positive
            uncertainty_weight
        )
        
        return signal_processing
    
    def _compute_risk_gradient(self, belief_state: Dict) -> float:
        """
        Compute risk gradient ∇R_t - how risk changes with aggression
        Higher aggression typically increases risk, so this is usually positive
        """
        # Extract risk-related components from belief state
        volatility = belief_state.get("volatility_estimate", 0.1)
        liquidity = belief_state.get("liquidity_estimate", 0.5)
        regime_entropy = belief_state.get("entropy", 1.0)  # Would be computed from regime probs
        
        # Base risk gradient increases with volatility and decreases with liquidity
        base_gradient = 0.1 + 0.5 * volatility - 0.3 * liquidity
        
        # Regime uncertainty increases risk sensitivity
        regime_factor = 1.0 + 0.2 * regime_entropy  # Higher entropy = higher risk sensitivity
        
        # Current aggression level affects risk sensitivity (more aggressive = more sensitive to risk increases)
        aggression_factor = 1.0 + 0.5 * self.aggression_level
        
        risk_gradient = base_gradient * regime_factor * aggression_factor
        
        return risk_gradient
    
    def _compute_lyapunov_function(self) -> float:
        """
        Compute Lyapunov function V(α) = (α - α_target)²/2
        For stability analysis: dV/dt ≤ 0 indicates stability
        """
        return 0.5 * (self.aggression_level - self.alpha_target) ** 2
    
    def get_lyapunov_derivative(self) -> float:
        """
        Compute derivative of Lyapunov function
        dV/dt = (α - α_target) * dα/dt
        Negative values indicate stability (converging to target)
        """
        if len(self.lyapunov_history) < 2:
            return 0.0
            
        # Approximate derivative
        if len(self.lyapunov_history) >= 2:
            v_current = self.lyapunov_history[-1]
            v_previous = self.lyapunov_history[-2]
            # Assuming roughly constant dt, approximate derivative
            dt_approx = 0.01  # 10ms default
            if dt_approx > 0:
                return (v_current - v_previous) / dt_approx
        return 0.0
    
    def is_stable(self, threshold: float = -1e-4) -> bool:
        """
        Check if the system is stable based on Lyapunov derivative
        dV/dt < threshold indicates stability
        """
        return self.get_lyapunov_derivative() < threshold
    
    def apply_execution_feedback(
        self,
        aggression_level: float,
        execution_stress: float,
        eta: Optional[float] = None
    ) -> float:
        """
        Apply execution feedback to adjust aggression level
        Based on Autonomous System's execution feedback law:
        α_{t+1} = α_t − η · ExecutionStress_t
        
        Args:
            aggression_level: Current aggression level
            execution_stress: Measured execution stress (slippage, latency, etc.)
            eta: Execution feedback gain (uses self.eta if None)
            
        Returns:
            Updated aggression level after execution feedback
        """
        if eta is None:
            eta = self.eta
            
        # Execution stress reduces aggression (poor execution -> lower aggression)
        updated_aggression = aggression_level - eta * execution_stress
        
        # Ensure bounds
        updated_aggression = np.clip(updated_aggression, 0.0, 1.0)
        
        return updated_aggression
    
    def get_stability_info(self) -> Dict:
        """Get information about system stability"""
        lyapunov = self._compute_lyapunov_function()
        lyapunov_derivative = self.get_lyapunov_derivative()
        
        return {
            "aggression_level": self.aggression_level,
            "aggression_rate": self.aggression_rate,
            "lyapunov_function": lyapunov,
            "lyapunov_derivative": lyapunov_derivative,
            "is_stable": self.is_stable(),
            "kappa": self.kappa,
            "lambda_": self.lambda_,
            "beta_max": self.beta_max,
            "eta": self.eta,
            "alpha_target": self.alpha_target
        }


# Example usage and testing
if __name__ == "__main__":
    import time
    
    # Create aggression controller
    controller = AggressionController(
        kappa=0.1,
        lambda_=0.05,
        beta_max=0.5,
        eta=0.01,
        alpha_target=0.5
    )
    
    # Simulate belief state (would come from perception layer)
    belief_state = {
        "expected_return": 0.001,      # 0.1% expected return
        "expected_return_uncertainty": 0.0005,
        "aleatoric_uncertainty": 0.001,
        "epistemic_uncertainty": 0.0008,
        "regime_probabilities": [0.1, 0.2, 0.4, 0.2, 0.05, 0.03, 0.01, 0.01],
        "volatility_estimate": 0.15,
        "liquidity_estimate": 0.7,
        "momentum_signal": 0.05,
        "volume_signal": 0.02
    }
    
    print("Aggression Controller Dynamics:")
    print("=" * 40)
    
    # Simulate multiple updates
    for i in range(10):
        # Simulate varying signal strength and execution feedback
        signal_strength = 0.3 + 0.2 * np.sin(i * 0.5)  # Oscillating signal
        execution_feedback = np.random.normal(0, 0.02)  # Random execution feedback
        
        # Update aggression level
        aggression_state = controller.update(
            belief_state=belief_state,
            signal_strength=signal_strength,
            execution_feedback=execution_feedback
        )
        
        # Get stability info
        stability_info = controller.get_stability_info()
        
        print(f"Step {i+1}:")
        print(f"  Aggression Level: {aggression_state.aggression_level:.4f}")
        print(f"  Aggression Rate: {aggression_state.aggression_rate:.4f}")
        print(f"  Signal Strength: {signal_strength:.4f}")
        print(f"  Execution Feedback: {execution_feedback:.4f}")
        print(f"  Lyapunov: {stability_info['lyapunov_function']:.6f}")
        print(f"  Lyapunov Derivative: {stability_info['lyapunov_derivative']:.6f}")
        print(f"  Stable: {stability_info['is_stable']}")
        print()
        
        # Small delay to simulate time passing
        time.sleep(0.01)