# Getting Started for Data Engineers

As a data engineer, you'll focus on the data pipelines, data quality, storage, and how to extend or modify the data handling components of the system.

## 30-Minute Quick Start

### Objective: Understand and Explore the Data Pipeline

#### Minutes 0-5: Setup and Initial Data Observation
```bash
# Clone and setup (if not done)
git clone [repository-url]
cd unified_trading_system
pip install -r requirements.txt

# Start system to observe data flow
./start_system.sh &
```

#### Minutes 5-10: Examine Data Generation and Flow
```bash
# Look at the market data generation (simulated)
cat continuous_trading_loop.py | grep -A10 "_fetch_market_data"

# Check what data flows between components
grep -r "market_data\|belief_state" --include="*.py" perception/ decision/ | head -10
```

#### Minutes 10-20: Explore Data Structures and Storage
```bash
# Look at belief state definition (core data structure)
cat perception/belief_state.py | head -50

# Check how data is persisted (journals, logs, etc.)
ls logs/
cat logs/trade_journal.json | head -5 2>/dev/null || echo "Journal file will be created during execution"

# Check configuration for data handling
cat config/learning_high_wr.yaml | grep -E "log|monitor|storage"
```

#### Minutes 20-25: Experiment with Data Pipeline
```bash
# Create a simple test to see data structures
python -c "
import sys
sys.path.append('.')
from perception.belief_state import BeliefStateEstimator, BeliefState
import json
import time

# Create estimator
estimator = BeliefStateEstimator()

# Generate sample market data at different times
for i in range(3):
    market_data = {
        'bid_price': 50000.0 + i*10,
        'ask_price': 50010.0 + i*10,
        'bid_size': 1.5 + i*0.5,
        'ask_size': 1.0 + i*0.3,
        'last_price': 50005.0 + i*5,
        'last_size': 2.0 + i*0.5
    }
    
    belief_state = estimator.update(market_data)
    
    # Convert to dictionary for inspection
    bs_dict = belief_state.to_dict()
    print(f'\\nTime {i+1} Belief State:')
    print(f'  Timestamp: {bs_dict[\"timestamp\"]}')
    print(f'  Expected Return: {bs_dict[\"expected_return\"]:.6f}')
    print(f'  Confidence: {bs_dict[\"confidence\"]:.4f}')
    print(f'  Regime Probs Sum: {sum(bs_dict[\"regime_probabilities\"]):.4f}')
    
   ۍ
    # Show a few microstructure features
    features = bs_dict['microstructure_features']
    print(f'  OFI: {features.get(\"ofI\", 0):.4f}')
    print(f'  I*: {features.get(\"I_star\", 0):.4f}')
    print(f'  L*: {features.get(\"L_star\", 0):.4f}')
"
```

#### Minutes 25-30: Check Logging and Data Persistence
```bash
# Examine logging structure
cat observability/logging.py | head -30

# Check what gets logged
grep -A5 -B5 "def.*log\|logger\." observability/logging.py | head -20

# Look at trade journaling (if implemented)
find . -name "*.py" -exec grep -l "journal\|Journal" {} \;
```

### Key Data Components to Explore

1. **Market Data Pipeline**
   - Input: Raw market data (simulated or real)
   - Processing: Feature extraction in perception layer
   - Output: Belief states with microstructure features and regime probabilities

2. **Core Data Structures**
   - `BeliefState`: Central data structure flowing through the system
   - `TradingSignal`: Output of decision layer, input to risk/execution
   - `ExecutionIntent`: Risk-approved signals converted to execution plans
   - `ExecutionResult`: Outcomes from execution attempts

3. **Data Storage and Persistence**
   - **Trade Journal**: `logs/trade_journal.json` - Persistent record of trades
   - **Logs**: Structured JSON logs in `logs/` directory
   - **Metrics**: Time-series data available via Prometheus endpoint
   - **Configuration**: YAML files in `config/` directory

4. **Data Flow Between Layers**
   ```
   Market Data → Perception (Belief State) → 
   Decision (Trading Signal) → Risk (Approved Intent) → 
   Execution (Order) → Feedback (Performance) → 
   Adaptation (Model Updates) ↔ Observability (Monitoring)
   ```

### Next Steps for Data Engineers

1. **Deepen Your Understanding of Data Handling**
   - Read the [architecture overview](./architecture/overview.md) focusing on data flow
   - Examine the belief state data structure in detail
   - Study the logging and metrics systems for data emission practices

2. **Experiment with Data Pipeline Enhancements**
   - Add alternative data sources (different exchanges, data types)
   - Implement data validation and quality checks at ingestion
   - Add data transformation pipelines for alternative features
   - Experiment with different data serialization formats (Apache Arrow, Parquet, etc.)

3. **Build Extended Data Capabilities**
   - Implement a feature store for reusable feature pipelines
   - Add data lineage tracking for reproducibility
   - Implement data quality monitoring and alerting
   - Add data archiving and retention policies
   - Create data APIs for external consumption

4. **Enhance Monitoring and Observability**
   - Add custom metrics for data pipeline health
   - Implement data drift detection for input data
   - Add data quality scoring and monitoring
   - Implement latency monitoring for data pipeline stages

### Quick Reference: Core Data Structures

#### BeliefState (perception/belief_state.py)
| Field | Type | Description |
|-------|------|-------------|
| `expected_return` | float | Predicted asset return |
| `expected_return_uncertainty` | float | Uncertainty in expected return |
| `aleatoric_uncertainty` | float | Irreducible market uncertainty |
| `epistemic_uncertainty` | float | Reducible model uncertainty |
| `regime_probabilities` | List[float] | Probability distribution over 8 market regimes |
| `microstructure_features` | Dict[str, float] | OFI, I*, L*, S*, depth imbalance, etc. |
| `volatility_estimate` | float | Estimated market volatility |
| `liquidity_estimate` | float | Estimated market liquidity |
| `momentum_signal` | float | Price momentum indicator |
| `volume_signal` | float | Volume-based signal |
| `timestamp` | int | Nanoseconds since epoch |
| `confidence` | float | Overall belief state confidence (0-1) |

#### TradingSignal (decision/signal_generator.py)
| Field | Type | Description |
|-------|------|-------------|
| `symbol` | str | Trading pair (e.g., "BTC/USDT") |
| `action` | str | "BUY" or "SELL" |
| `quantity` | float | Order size |
| `confidence` | float | Signal confidence (0-1) |
| `expected_return` | float | Expected return from signal |
| `timestamp` | float | Unix timestamp |
| `regime` | RegimeType | Current market regime |
| `signal_strength` | float | Normalized signal strength |

#### Trade Journal Entry (inferred from usage)
| Field | Type | Description |
|-------|------|-------------|
| `trade_id` | str | Unique identifier for the trade |
| `symbol` | str | Trading pair |
| `side` | str | "BUY" or "SELL" |
| `quantity` | float | Trade size |
| `entry_price` | float | Entry price |
| `exit_price` | float | Exit price |
| `pnl` | float | Profit and loss |
| `timestamp` | int | Trade timestamp |
| `metadata` | Dict | Additional trade information |

### Data Engineering Best Practices for this System

1. **Data Quality**
   - Validate incoming market data for completeness and correctness
   - Implement schema validation for all data structures
   - Add data profiling to understand distributions and anomalies
   - Implement data lineage tracking for reproducibility

2. **Data Pipeline Design**
   - Use immutable data structures where possible (like BeliefState)
   - Implement proper error handling and dead letter queues
   - Add data buffering for handling temporary downstream slowness
   - Implement backpressure mechanisms to prevent overload

3. **Storage and Retrieval**
   - Choose appropriate storage formats for different data types
   - Implement partitioning strategies for time-series data
   - Add indexing strategies for common query patterns
   - Consider compression for historical data storage

4. **Monitoring and Observability**
   - Track data freshness and latency
   - Monitor data volume and throughput
   - Track error rates and data quality metrics
   - Implement data drift detection for input features