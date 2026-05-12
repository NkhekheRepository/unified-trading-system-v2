# Getting Started for AI/ML Engineers

As an AI/ML engineer, you'll focus on the learning mechanisms, feature engineering, model adaptation, and how to enhance the system's intelligence capabilities.

## 30-Minute Quick Start

### Objective: Explore and Experiment with Learning Mechanisms

#### Minutes 0-5: Setup and Initial Run
```bash
# Clone and setup (if not done)
git clone [repository-url]
cd unified_trading_system
pip install -r requirements.txt

# Start system to observe learning behavior
./start_system.sh &
```

#### Minutes 5-10: Observe Learning and Adaptation Indicators
```bash
# Look for aggression updates (shows learning from execution)
grep -i "aggression" logs/trading_system.log | tail -5

# Check for any adaptation or learning messages
grep -i -E "learn|adapt|drift" logs/system.log | tail -5
```

#### Minutes 10-20: Examine Learning Components
```bash
# Look at the aggression controller (core learning mechanism)
cat decision/aggression_controller.py | head -50

# Check the feedback layer that drives learning insights
ls feedback/
cat feedback/__init__.py

# Look at the adaptation layer for concept drift detection
ls adaptation/
cat adaptation/__init__.py | head -30
```

#### Minutes 20-25: Experiment with Learning Parameters
```bash
# Check current aggression controller configuration
grep -A5 -B5 "aggression_controller" config/learning_high_wr.yaml

# Create a test to see how aggression changes
python -c "
import sys
sys.path.append('.')
from decision.aggression_controller import AggressionController
import numpy as np

# Create controller with default params
ctrl = AggressionController()

# Simulate a series of good executions (should increase aggression)
belief_state = {
    'expected_return': 0.002,
    'expected_return_uncertainty': 0.0005,
    'aleatoric_uncertainty': 0.001,
    'epistemic_uncertainty': 0.0008,
    'regime_probabilities': [0.1]*8,
    'volatility_estimate': 0.15,
    'liquidity_estimate': 0.7,
    'momentum_signal': 0.1,
    'volume_signal': 0.05,
    'confidence': 0.8
}

print('Initial aggression:', ctrl.aggression_level)
for i in range(5):
    state = ctrl.update(
        belief_state=belief_state,
        signal_strength=0.7,
        execution_feedback=0.0  # Perfect execution
    )
    print(f'After good execution {i+1}: {state.aggression_level:.3f}')

print('\\nNow simulating poor executions:')
for i in range(5):
    state = ctrl.update(
        belief_state=belief_state,
        signal_strength=0.7,
        execution_feedback=-0.8  # Poor execution (high stress)
    )
    print(f'After poor execution {i+1}: {state.aggression_level:.3f}')
"
```

#### Minutes 25-30: Feature Engineering Exploration
```bash
# Marcatori microstructure feature computation
cat perception/belief_state.py | grep -A20 "_extract_microstructure_features"

# See what features are currently computed
python -c "
import sys
sys.path.append('.')
from perception.belief_state import BeliefStateEstimator
estimator = BeliefStateEstimator()

# Sample market data
market_data = {
    'bid_price': 50000.0,
    'ask_price': 50010.0,
    'bid_size': 1.5,
    'ask_size': 1.0,
    'last_price': 50005.0,
    'last_size': 2.0
}

belief_state = estimator.update(market_state=market_data)
print('Microstructure features:')
for k, v in belief_state.microstructure_features.items():
    print(f'  {k}: {v:.4f}')
"
```

### Key Learning Components to Explore

1. **Aggression Controller (Primary Learning Mechanism)**
   - File: `decision/aggression_controller.py`
   - Implements: α_{t+1} = α_t − η · ExecutionStress_t
   - Learns optimal aggression level from execution feedback
   - Provides Lyapunov stability guarantees

2. **Feedback Layer (Learning Insights Engine)**
   - Directory: `feedback/`
   - Components: P&L attribution, trade classification, pattern recognition
   - Generates insights for strategy improvement

3. **Adaptation Layer (Concept Drift Detection)**
   - Directory: `adaptation/`
   - Detects changes in market relationships
   - Triggers model updates when significant drift is found

4. **Feature Engineering (Perception Layer)**
   - File: `perception/belief_state.py`
   - Computes microstructure features: OFI, I*, L*, S*
   - Foundation for signal generation and belief formation

### Next Steps for AI/ML Engineers

1. **Deepen Your Understanding of Learning Mechanisms**
   - Read the [research foundations](./research/foundations.md) 
   - Study the mathematical foundations of the aggression controller
   - Examine the feedback layer attribution engines in detail

2. **Experiment with Learning Enhancements**
   - Modify the aggression controller learning rate or formula
   - Add new features to the microstructure computation
   - Implement alternative belief state estimation approaches
   - Experiment with different feature combinations for signal generation

3. **Develop New Learning Capabilities**
   - Add reinforcement learning components for policy optimization
   - Implement ensemble methods for belief state combination
   - Add natural language processing for news/sentiment integration
   - Implement clustering algorithms for regime discovery

4. **Validate Learning Improvements**
   - Run learning-related tests: `python -m pytest tests/ -k "learn" -v`
   - Use ablation studies to measure impact of changes
   - Monitor long-term performance improvements in paper trading
   - Validate statistical significance of any performance changes

### Quick Reference: Learning Mechanism Parameters

#### Aggression Controller (`decision/aggression_controller.py`)
| Parameter | Description | Typical Range | Effect |
|-----------|-------------|---------------|---------|
| `kappa` | Learning rate for aggression updates | 0.01 - 0.2 | Higher = faster adaptation to execution feedback |
| `lambda_` | Rate of aggression decay toward target | 0.005 - 0.05 | Higher = faster return to baseline aggression |
| `beta_max` | Maximum aggression level | 0.3 - 0.7 | Upper bound on aggression |
| `eta` | Execution stress sensitivity | 0.005 - 0.02 | Higher = more aggressive response to poor execution |
| `alpha_target` | Target aggression level | 0.3 - 0.6 | Long-term average aggression level |

#### Feedback and Adaptation
| Component | Purpose | Key Characteristics |
|-----------|---------|---------------------|
| **PNL Engine** | Profit and loss attribution | Breaks down P&L by strategy, symbol, time, trade characteristics |
| **Learning Insights Engine** | Pattern recognition | Identifies characteristics of winning vs losing trades |
| **SRE Metrics Engine** | System reliability | Tracks latency, error rates, resource utilization |
| **Adaptation Layer** | Concept drift detection | Uses statistical tests to detect changing market relationships |

### Experiment Ideas for AI/ML Engineers

1. **Feature Engineering Experiments**
   - Add volume-weighted average price (VWAP) deviation as a feature
   - Implement order book imbalance metrics over different time windows
   - Add volatility regime features based on historical volatility
   - Experiment with technical indicators as additional features

2. **Belief State Enhancements**
   - Implement deep learning approaches for belief state estimation
   - Add attention mechanisms to weigh different microstructure features
   - Experiment with hierarchical belief states (short-term/long-term)
   - Add uncertainty quantification using Bayesian neural networks

3. **Signal Generation Improvements**
   - Implement machine learning models for signal classification
   - Add ensemble methods combining multiple signal generation approaches
   - Experiment with reinforcement learning for signal filtering
   - Implement regime-specific signal generators

4. **Learning Mechanism Enhancements**
   - Add meta-learning to adapt learning rates based on performance volatility
   - Implement online clustering for dynamic regime discovery
   - Add transfer learning capabilities between symbols or timeframes
   - Implement uncertainty-aware exploration strategies