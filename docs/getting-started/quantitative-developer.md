# Getting Started for Quantitative Developers

As a quantitative developer, you'll want to understand how the system generates alpha, how signals are formed, and how to extend or modify the quantitative components.

## 30-Minute Quick Start

### Objective: Examine and Modify Signal Generation

#### Minutes 0-5: Setup and Initial Run
```bash
# Clone and setup (if not done)
git clone [repository-url]
cd unified_trading_system
pip install -r requirements.txt

# Start system in background to observe
./start_system.sh &
```

#### Minutes 5-10: Observe Signal Generation
```bash
# Watch for signal generation in logs
grep -i "signal" logs/trading_system.log | tail -10
```

You should see entries like:
```
INFO:signal_generator:Generated signal for BTC/USDT: BUY 0.015432 @ conf=0.723
```

#### Minutes 10-20: Examine Signal Generation Code
```bash
# Look at the signal generator
cat decision/signal_generator.py | head -50

# Check the configuration that drives signal thresholds
cat config/learning_high_wr.yaml
```

#### Minutes 20-25: Modify Signal Parameters
```bash
# Create a backup of the config
cp config/learning_high_wr.yaml config/learning_high_wr.yaml.backup

# Temporarily relax thresholds to see more signals
sed -i 's/min_confidence_threshold: 0.45/min_confidence_threshold: 0.1/' config/learning_high_wr.yaml
sed -i 's/min_expected_return: 0.003/min_expected_return: 0.0001/' config/learning_high_wr.yaml
```

#### Minutes 25-30: Observe Impact of Changes
```bash
# Restart system to pick up new config
pkill -f "continuous_trading_loop"
./start_system.sh &

# Watch for increased signal activity
grep -i "signal" logs/trading_system.log | tail -20
```

### Key Files to Explore

1. **Signal Generation**: `decision/signal_generator.py`
   - How belief states are converted to trading signals
   - Thresholding logic and filtering mechanisms
   - Position sizing calculations

2. **Belief State Formation**: `perception/belief_state.py`
   - How microstructure features (OFI, I*, L*, S*) are computed
   - How regime probabilities are estimated
   - How expected return and uncertainties are derived

3. **Configuration System**: `config/learning_high_wr.yaml`
   - All tunable parameters for signal generation
   - Regime-specific thresholds and adjustments
   - Symbol weights and exclusions

### Next Steps for Quantitative Developers

1. **Deepen Your Understanding**
   - Read the [research foundations](./research/foundations.md)
   - Examine the microstructure feature computation in detail
   - Study the uncertainty decomposition methods

2. **Experiment with Modifications**
   - Add new microstructure features to perception layer
   - Implement alternative signal generation algorithms
   - Modify the quality scoring system
   - Experiment with different position sizing models

3. **Validate Your Changes**
   - Run the test suite: `python -m pytest tests/test_signal_quality.py -v`
   - Use the integration tests to verify end-to-end functionality: `python -m pytest tests/test_integrated_system.py::TestSystemIntegration::test_end_to_end_processing -v`
   - Monitor performance metrics to ensure changes improve risk-adjusted returns

4. **Contribute Back**
   - Follow the contribution guidelines in [CONTRIBUTING.md](/.github/CONTRIBUTING.md)
   - Submit pull requests for improvements to signal generation or feature engineering

### Quick Reference: Signal Generation Parameters

| Parameter | Description | Typical Range | Effect |
|-----------|-------------|---------------|---------|
| `min_confidence_threshold` | Minimum belief state confidence to generate signal | 0.1 - 0.9 | Lower = more signals, potentially lower quality |
| `min_expected_return` | Minimum expected return magnitude to act on | 0.0001 - 0.01 | Lower = more trades on weaker signals |
| `min_uncertainty` | Minimum total uncertainty allowed | 0.01 - 0.1 | Higher = filters out very certain signals |
| `max_uncertainty` | Maximum total uncertainty allowed | 0.1 - 0.5 | Lower = filters out very uncertain signals |
| `buy_bias` | Preference for BUY vs SELL signals | -0.1 to 0.1 | Positive = favors BUY signals |

Remember to restart the system after changing configuration for changes to take effect!