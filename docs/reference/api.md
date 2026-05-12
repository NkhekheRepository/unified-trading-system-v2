# API Reference

This document provides a detailed reference to the public APIs and interfaces of the Unified Trading System. It covers the main classes, methods, and data structures that developers can use to extend or interact with the system.

## Core Data Structures

### BeliefState (`perception/belief_state.py`)

The central data structure representing the system's view of the market.

#### Fields
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

#### Methods
| Method | Description |
|--------|-------------|
| `to_dict()` | Convert to dictionary for serialization |
| `from_dict(data: Dict) -> BeliefState` | Create from dictionary |
| `get_most_likely_regime() -> Tuple[RegimeType, float]` | Get most likely regime and its probability |
| `get_entropy() -> float` | Calculate entropy of regime probabilities |
| `get_total_uncertainty() -> float` | Get total uncertainty (aleatoric + epistemic) |
| `is_confident(threshold: float = 0.7) -> bool` | Check if belief state is confident enough for trading |

### TradingSignal (`decision/signal_generator.py`)

Represents a trading signal generated from a belief state.

#### Fields
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

#### Methods
| Method | Description |
|--------|-------------|
| *(Standard dataclass methods)* | All standard methods from `@dataclass` decorator |

### ExecutionIntent (`execution/smart_order_router.py`)

Represents an intention to execute a trade (from decision to execution layer).

#### Fields
| Field | Type | Description |
|-------|------|-------------|
| `symbol` | str | Trading pair |
| `side` | str | "BUY" or "SELL" |
| `quantity` | float | Desired quantity |
| `urgency` | float | How urgently to execute [0, 1] |
| `max_slippage` | float | Maximum acceptable slippage |
| `min_time_limit` | float | Minimum time to execute (seconds) |
| `max_time_limit` | float | Maximum time to execute (seconds) |
| `aggression_level` | float | Current aggression level [0, 1] |
| `timestamp` | int | Nanoseconds since epoch |

#### Methods
| Method | Description |
|--------|-------------|
| *(Standard dataclass methods)* | All standard methods from `@dataclass` decorator |

### ExecutionPlan (`execution/smart_order_router.py`)

Represents a planned execution strategy.

#### Fields
| Field | Type | Description |
|-------|------|-------------|
| `symbol` | str | Trading pair |
| `order_type` | OrderType | Type of order to use |
| `quantity` | float | Quantity to execute |
| `price` | Optional[float] | Limit price (None for market orders) |
| `time_in_force` | str | Time in force specification |
| `max_slippage` | float | Maximum acceptable slippage |
| `expected_slippage` | float | Predicted slippage in basis points |
| `expected_latency` | int | Expected latency in milliseconds |
| `expected_cost` | float | Total expected cost in basis points |
| `urgency_score` | float | Computed urgency based on market conditions |
| `side` | str | "BUY" or "SELL" |
| `timestamp` | int | Nanoseconds since epoch |

#### Methods
| Method | Description |
|--------|-------------|
| *(Standard dataclass methods)* | All standard methods from `@dataclass` decorator |

### ExecutionResult (`execution/smart_order_router.py`)

Represents the outcome of an execution attempt.

#### Fields
| Field | Type | Description |
|-------|------|-------------|
| `status` | OrderStatus | Result status |
| `filled_quantity` | float | Amount actually filled |
| `average_price` | float | Average fill price |
| `slippage` | float | Slippage in basis points |
| `latency` | int | Latency in milliseconds |
| `market_impact` | float | Estimated market impact in basis points |
| `timestamp` | int | Nanoseconds since epoch |
| `order_id` | Optional[str] | Exchange order ID |
| `error_message` | Optional[str] | Error message if failed |

#### Methods
| Method | Description |
|--------|-------------|
| *(Standard dataclass methods)* | All standard methods from `@dataclass` decorator |

### RiskAssessment (`risk/unified_risk_manager.py`)

Represents a comprehensive risk assessment.

#### Fields
| Field | Type | Description |
|-------|------|-------------|
| `risk_level` | RiskLevel | Overall risk level |
| `risk_score` | float | Overall risk score [0, 1] |
| `cvar` | float | Conditional Value at Risk |
| `volatility` | float | Estimated volatility |
| `drawdown` | float | Current drawdown |
| `leverage_ratio` | float | Current leverage usage |
| `liquidity_score` | float | Market liquidity [0, 1] |
| `concentration_risk` | float | Position concentration risk |
| `correlation_risk` | float | Portfolio correlation risk |
| `risk_gradient` | np.ndarray | Gradient of risk w.r.t. trading actions |
| `protective_action` | str | Recommended protective action |
| `timestamp` | int | Nanoseconds since epoch |
| `metadata` | Dict[str, Any] | Additional information |

#### Methods
| Method | Description |
|--------|-------------|
| *(Standard dataclass methods)* | All standard methods from `@dataclass` decorator |

## Main System Components

### EnhancedTradingLoop (`continuous_trading_loop.py`)

The main orchestrator that brings all layers together.

#### Constructor
```python
def __init__(self, config: TradingConfig)
```

#### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `config` | TradingConfig | System configuration |

#### Methods
| Method | Description | Returns |
|--------|-------------|---------|
| `async def initialize()` | Initialize the trading loop | `None` |
| `async def start()` | Start the continuous trading loop | `None` |
| `async def _run_cycle() -> TradingCycleResult` | Run a single trading cycle | TradingCycleResult |
| `async def _process_symbol(symbol: str, result: TradingCycleResult)` | Process a single symbol | None |
| `async def _fetch_market_data(symbol: str, expected_return: float = 0.0) -> Dict` | Fetch market data for a symbol | Market data dict |
| `async def _execute_signal(signal: TradingSignal, result: TradingCycleResult)` | Execute a trading signal | None |
| `async def _update_metrics(result: TradingCycleResult)` | Update metrics after cycle | None |
| `async def shutdown()` | Shutdown the trading loop | `None` |
| `async def wait_for_shutdown()` | Wait for shutdown to complete | `None` |

#### Properties
| Property | Type | Description |
|----------|------|-------------|
| `_running` | bool | Whether the loop is currently running |
| `_cycle_count` | int | Number of cycles completed |
| `_start_time` | Optional[float] | Start time timestamp |
| `_shutdown_event` | asyncio.Event | Event that signals shutdown completion |

### TradingConfig (`continuous_trading_loop.py`)

Configuration for the trading loop.

#### Fields
| Field | Type | Description |
|-------|------|-------------|
| `mode` | TradingMode | Trading operation mode (PAPER, TESTNET, LIVE) |
| `symbols` | List[str] | List of trading symbols |
| `cycle_interval` | float | Time between trading cycles (seconds) |
| `max_position_size` | float | Maximum position size as fraction of capital |
| `max_daily_loss` | float | Maximum daily loss allowed |
| `max_orders_per_minute` | int | Maximum order frequency |
| `enable_alerting` | bool | Whether to enable alerting |
| `alerting_channels` | List[str] | Enabled alerting channels |
| `health_check_port` | int | Port for health check server |
| `metrics_port` | int | Port for metrics server |

#### TradingMode Enum
| Value | Description |
|-------|-------------|
| `PAPER` | Simulated trading with no real money |
| `TESTNET` | Connection to exchange testnet |
| `LIVE` | Connection to live exchange (use with caution) |

#### Methods
| Method | Description |
|--------|-------------|
| *(Standard dataclass methods)* | All standard methods from `@dataclass` decorator |

### TradingCycleResult (`continuous_trading_loop.py`)

Result of a single trading cycle.

#### Fields
| Field | Type | Description |
|-------|------|-------------|
| `cycle_id` | str | Unique identifier for this cycle |
| `timestamp` | float | Cycle start time |
| `symbols_processed` | int | Number of symbols processed |
| `signals_generated` | int | Number of signals generated |
| `orders_executed` | int | Number of orders executed |
| `errors` | List[str] | List of error messages |
| `duration_ms` | float | Cycle duration in milliseconds |
| `success` | bool | Whether the cycle completed successfully |

#### Methods
| Method | Description |
|--------|-------------|
| *(Standard dataclass methods)* | All standard methods from `@dataclass` decorator |

## Perception Layer APIs

### BeliefStateEstimator (`perception/belief_state.py`)

Estimates belief state by combining LVR feature computation with POMDP belief updating.

#### Constructor
```python
def __init__(self, n_regimes: int = 8)
```

#### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `n_regimes` | int | Number of market regimes to track |

#### Methods
| Method | Description | Returns |
|--------|-------------|---------|
| `def update(market_data: Dict, prior_belief: Optional[BeliefState] = None) -> BeliefState` | Update belief state with new market data | Updated BeliefState |
| `def _extract_microstructure_features(market_data: Dict) -> Dict[str, float]` | Extract microstructure features from market data | Features dictionary |
| `def _compute_expected_return_and_uncertainty(features: Dict[str, float]) -> Tuple[float, float]` | Compute expected return and uncertainty | (expected_return, return_uncertainty) |
| `def _decompose_uncertainty(features: Dict[str, float], prior_belief: Optional[BeliefState]) -> Tuple[float, float]` | Decompose uncertainty into aleatoric and epistemic | (aleatoric_uncertainty, epistemic_uncertainty) |
| `def _update_regime_probabilities(features: Dict[str, float], prior_belief: Optional[BeliefState]) -> np.ndarray` | Update regime probabilities using Bayes' rule | Updated regime probabilities |
| `def _compute_regime_likelihoods(feature_vector: np.ndarray) -> np.ndarray` | Compute likelihood of features under each regime | Likelihoods array |
| `def _compute_confidence(aleatoric_uncertainty: float, epistemic_uncertainty: float, regime_probabilities: np.ndarray) -> float` | Compute overall confidence | Confidence value |

#### Properties
| Property | Type | Description |
|----------|------|-------------|
| `n_regimes` | int | Number of regimes |
| `regime_transition_matrix` | np.ndarray | Regime transition probabilities |
| `feature_weights` | Dict[str, float] | Weights for different features in belief formation |

## Decision Layer APIs

### SignalGenerator (`decision/signal_generator.py`)

Generates trading signals from belief states.

#### Constructor
```python
def __init__(self, config: Dict = None)
```

#### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `config` | Optional[Dict] | Configuration dictionary |

#### Methods
| Method | Description | Returns |
|--------|-------------|---------|
| `def generate_signals(self, market_data_or_belief_state, symbol_or_belief_states=None) -> List[TradingSignal]` | Generate trading signals | List of TradingSignal objects |
| *(Overloaded method with two calling modes)* | | |
| *Mode 1: Single symbol* | `generate_signals(belief_state: BeliefState, symbol: str)` | List[TradingSignal] |
| *Mode 2: Multiple symbols* | `generate_signals(market_data: Dict, belief_states: Dict[str, BeliefState])` | List[TradingSignal] |

#### Properties
| Property | Type | Description |
|----------|------|-------------|
| `min_confidence_threshold` | float | Minimum confidence to generate signal |
| `min_expected_return` | float | Minimum expected return magnitude |
| `max_position_size` | float | Maximum position size |
| `min_uncertainty` | float | Minimum uncertainty threshold |
| `max_uncertainty` | float | Maximum uncertainty threshold |
| `buy_bias` | float | Preference for BUY vs SELL signals |
| `symbol_weights` | Dict[str, float] | Weights for different symbols |

### TradingSignal (`decision/signal_generator.py`)

(See Core Data Structures section above)

### AggressionController (`decision/aggression_controller.py`)

Dynamically adjusts trading aggression based on execution feedback using Lyapunov stability theory.

#### Constructor
```python
def __init__(self, kappa: float = 0.1, lambda_: float = 0.05, beta_max: float = 0.5, eta: float = 0.01, alpha_target: float = 0.5)
```

#### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `kappa` | float | Learning rate for aggression updates |
| `lambda_` | float | Rate of aggression decay toward target |
| `beta_max` | float | Maximum aggression level |
| `eta` | float | Execution stress sensitivity |
| `alpha_target` | float | Target aggression level |

#### Methods
| Method | Description | Returns |
|--------|-------------|---------|
| `def update(belief_state: Dict, signal_strength: float, execution_feedback: float) -> AggressionState` | Update aggression level based on belief state and execution feedback | AggressionState |
| `def get_stability_info() -> Dict` | Get information about Lyapunov stability properties | Stability info dictionary |
| `def _compute_execution_stress(execution_result: ExecutionResult) -> float` | Compute execution stress from execution result | Execution stress value |

#### Properties
| Property | Type | Description |
|----------|------|-------------|
| `kappa` | float | Learning rate for aggression updates |
| `lambda_` | float | Rate of aggression decay toward target |
| `beta_max` | float | Maximum aggression level |
| `eta` | float | Execution stress sensitivity |
| `alpha_target` | float | Target aggression level |
| `aggression_level` | float | Current aggression level [0, 1] |
| `aggression_rate` | float | Rate of change of aggression level |

### AggressionState (`decision/aggression_controller.py`)

Represents the state of the aggression controller.

#### Fields
| Field | Type | Description |
|-------|------|-------------|
| `aggression_level` | float | Current aggression level |
| `aggression_rate` | float | Rate of change of aggression level |
| `signal_strength` | float | Strength of the signal that triggered update |
| `risk_gradient` | float | Gradient of risk with respect to aggression |
| `execution_feedback` | float | Feedback from execution quality |
| `timestamp` | int | Nanoseconds since epoch |

#### Methods
| Method | Description |
|--------|-------------|
| *(Standard dataclass methods)* | All standard methods from `@dataclass` decorator |

## Risk Layer APIs

### RiskManifold (`risk/unified_risk_manager.py`)

Unified Risk Management System combining LVR's protection levels with Autonomous System's risk manifold and control barrier system.

#### Constructor
```python
def __init__(self(
    self,
    risk_sensitivity: float = 1.0,
    nonlinearity_factor: float = 0.5,
    drawdown_warning: float = 0.05,
    drawdown_danger: float = 0.10,
    drawdown_critical: float = 0.15,
    daily_loss_warning: float = 0.03,
    daily_loss_danger: float = 0.05,
    daily_loss_critical: float = 0.08,
    leverage_warning: float = 25.0,
    leverage_danger: float = 28.0,
    leverage_critical: float = 30.0,
    correlation_warning: float = 0.6,
    correlation_danger: float = 0.8,
    concentration_warning: float = 0.3,
    concentration_danger: float = 0.5,
))
```

#### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `risk_sensitivity` | float | Overall risk sensitivity scaling |
| `nonlinearity_factor` | float | Nonlinearity factor in risk manifold |
| `drawdown_warning` | float | Drawdown threshold for Level 1 warning |
| `drawdown_danger` | float | Drawdown threshold for Level 2 danger |
| `drawdown_critical` | float | Drawdown threshold for Level 3 critical |
| `daily_loss_warning` | float | Daily loss threshold for Level 1 warning |
| `daily_loss_danger` | float | Daily loss threshold for Level 2 danger |
| `daily_loss_critical` | float | Daily loss threshold for Level 3 critical |
| `leverage_warning` | float | Leverage threshold for Level 1 warning |
| `leverage_danger` | float | Leverage threshold for Level 2 danger |
| `leverage_critical` | float | Leverage threshold for Level 3 critical |
| `correlation_warning` | float | Correlation threshold for Level 1 warning |
| `correlation_danger` | float | Correlation threshold for Level 2 danger |
| `concentration_warning` | float | Concentration threshold for Level 1 warning |
| `concentration_danger` | float | Concentration threshold for Level 2 danger |

#### Methods
| Method | Description | Returns |
|--------|-------------|---------|
| `def assess_risk(belief_state: Dict, portfolio_state: Dict, market_data: Dict, current_positions: Dict = None, recent_returns: List[float] = None) -> RiskAssessment` | Assess current risk levels | RiskAssessment object |
| `def _extract_risk_factors(...)` | Extract all relevant risk factors | Risk factors dictionary |
| `def _compute_risk_manifold(risk_factors: Dict[str, float]) -> float` | Compute nonlinear risk manifold | Risk score |
| `def _determine_risk_level(risk_factors: Dict[str, float]) -> RiskLevel` | Determine risk level based on thresholds | RiskLevel enum |
| `def _compute_risk_gradient(risk_factors: Dict[str, float], belief_state: Dict) -> np.ndarray` | Compute risk gradient | Risk gradient array |
| `def _determine_protective_action(risk_level: RiskLevel, risk_factors: Dict[str, float]) -> str` | Determine protective action | Protective action string |
| `def calculate_portfolio_leverage(portfolio_value: float, positions: Dict[str, float], prices: Dict[str, float]) -> float` | Calculate actual portfolio leverage | Leverage ratio |
| `def _compute_risk_factor_contributions(risk_factors: Dict[str, float]) -> Dict[str, float]` | Compute each risk factor's contribution | Contribution dictionary |
| `def calculate_uncertainty_stop_loss(entry_price: float, action: str, aleatoric_uncertainty: float, multiplier: float = 2.0) -> float` | Compute uncertainty-based stop-loss | Stop-loss price |
| `def _update_risk_factor_histories(risk_factors: Dict[str, float]) -> None` | Update histories of risk factors | None |
| `def get_risk_trends() -> Dict[str, Dict]` | Get trend analysis for each risk factor | Risk trends dictionary |

#### Properties
| Property | Type | Description |
|----------|------|-------------|
| `risk_sensitivity` | float | Overall risk sensitivity scaling |
| `nonlinearity_factor` | float | Nonlinearity factor in risk manifold |
| `risk_weights` | Dict[str, float] | Weights for different risk factors |
| `risk_history` | Dict[str, List[float]] | Historical values of risk factors |
| `max_history_length` | int | Maximum length of risk factor histories |

### RiskAssessment (`risk/unified_risk_manager.py`)

(See Core Data Structures section above)

### RiskLevel (`risk/unified_risk_manager.py`)

Enum representing risk levels.

#### Values
| Value | Description |
|-------|-------------|
| `LEVEL_0_NORMAL` | Normal operation |
| `LEVEL_1_CAUTION` | Elevated risk - reduce size |
| `LEVEL_2_WARNING` | High risk - restrict trading |
| `LEVEL_3_DANGER` | Danger - close all positions |
| `LEVEL_4_CRITICAL` | Critical - manual intervention required |

#### Methods
| Method | Description |
|--------|-------------|
| `value` | Get the integer value of the enum |
| `name` | Get the name of the enum |

## Execution Layer APIs

### ExecutionModel (`execution/smart_order_router.py`)

Unified execution model combining LVR's smart order routing with Autonomous System's execution feedback loop.

#### Constructor
```python
def __init__(
    self,
    execution_eta: float = 0.01,
    market_impact_factor: float = 0.1,
    latency_base: int = 5,
    slippage_factor: float = 0.05
)
```

#### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `execution_eta` | float | Execution feedback gain |
| `market_impact_factor` | float | Market impact scaling factor |
| `latency_base` | int | Base latency in milliseconds |
| `slippage_factor | float | Base slippage factor |

#### Methods
| Method | Description | Returns |
|--------|-------------|---------|
| `def plan_execution(execution_intent: ExecutionIntent, market_data: Dict, orderbook_data: Dict = None) -> ExecutionPlan` | Plan execution strategy | ExecutionPlan object |
| `def simulate_execution(execution_plan: ExecutionPlan, market_data: Dict) -> ExecutionResult` | Simulate execution based on plan | ExecutionResult object |
| `def apply_execution_feedback(aggression_level: float, execution_result: ExecutionResult) -> float` | Apply execution feedback to adjust aggression | Updated aggression level |
| `def _compute_execution_stress(execution_result: ExecutionResult) -> float` | Compute execution stress from result | Execution stress value |
| `def _compute_urgency(base_urgency: float, aggression_level: float, volatility: float, liquidity: float) -> float` | Compute execution urgency | Urgency score |
| `def _select_order_type(urgency: float, volatility: float, liquidity: float, spread: float, quantity: float) -> OrderType` | Select appropriate order type | OrderType enum |
| `def _select_time_in_force(min_time: float, max_time: float, urgency: float) -> str` | Select time in force | Time in force string |
| `def _select_venue(execution_plan: ExecutionPlan) -> str` | Select execution venue | Venue name |
| `def _estimate_slippage(order_type: OrderType, quantity: float, volatility: float, liquidity: float, urgency: float) -> float` | Estimate expected slippage | Slippage in basis points |
| `def _estimate_latency(order_type: OrderType, urgency: float) -> int` | Estimate expected latency | Latency in milliseconds |
| `def _estimate_total_cost(expected_slippage: float, expected_latency: int, spread: float) -> float` | Estimate total execution cost | Cost in basis points |
| `def _estimate_market_impact(quantity: float, liquidity: float, venue_market_impact: float) -> float` | Estimate market impact | Market impact in basis points |
| `def _record_execution(plan: ExecutionPlan, result: ExecutionResult, market_data: Dict) -> None` | Record execution for learning and analysis | None |

#### Properties
| Property | Type | Description |
|----------|------|-------------|
| `execution_eta` | float | Execution feedback gain |
| `market_impact_factor` | float | Market impact scaling |
| `latency_base` | int | Base latency in milliseconds |
| `slippage_factor` | float | Base slippage factor |
| `execution_history` | List[Dict] | History of executions for learning |

### ExecutionIntent (`execution/smart_order_router.py`)

(See Core Data Structures section above)

### ExecutionPlan (`execution/smart_order_router.py`)

(See Core Data Structures section above)

### ExecutionResult (`execution/smart_order_router.py`)

(See Core Data Structures section above)

### OrderType (`execution/smart_order_router.py`)

Enum representing order types.

#### Values
| Value | Description |
|-------|-------------|
| `LIMIT` | Limit order |
| `MARKET` | Market order |
| `STOP_LIMIT` | Stop-limit order |
| `ICEBERG` | Iceberg order |
| `TWAP` | Time-weighted average price |
| `VWAP` | Volume-weighted average price |

#### Methods
| Method | Description |
|--------|-------------|
| `value` | Get the string value of the enum |
| `name` | Get the name of the enum |

### OrderStatus (`execution/smart_order_router.py`)

Enum representing order status.

#### Values
| Value | Description |
|-------|-------------|
| `PENDING` | Order created but not yet submitted |
| `SUBMITTED` | Order submitted to exchange |
| `PARTIALLY_FILLED` | Order partially filled |
| `FILLED` | Order completely filled |
| `CANCELLED` | Order cancelled |
| `REJECTED` | Order rejected by exchange |
| `EXPIRED` | Order expired |

#### Methods
| Method | Description |
|--------|-------------|
| `value` | Get the string value of the enum |
| `name` | Get the name of the enum |

## Feedback Layer APIs

### FeedbackLayer (`feedback/__init__.py`)

Main feedback layer coordinating all feedback components.

#### Constructor
```python
def __init__(self)
```

#### Methods
| Method | Description | Returns |
|--------|-------------|---------|
| `def update_all(trade_result: Dict, current_positions: Dict, market_prices: Dict, belief_state: Dict, execution_result: Dict, market_data: Dict, component_latencies: Dict, error_events: List[Dict], system_health: Dict, model_info: Dict) -> List[Dict]` | Update all feedback engines | List of metrics from all engines |
| `def _update_trade_result(...)` | Update P&L engine | P&L metrics |
| `def _update_learning_insights(...)` | Update learning insights engine | Learning insights |
| `def _update_sre_metrics(...)` | Update SRE metrics engine | SRE metrics |
| `def _update_predictive(...)` | Update predictive engine | Predictive metrics |
| `def _update_var(...)` | Update VaR engine | VaR metrics |
| `def _update_factor_attribution(...)` | Update factor attribution engine | Factor attribution metrics |
| `def _update_strategy_optimizer(...)` | Update strategy optimizer engine | Strategy optimizer metrics |
| `def _update_correlation_monitor(...)` | Update correlation monitor engine | Correlation monitor metrics |

## Observation Layer APIs

### TradingLogger (`observability/logging.py`)

Enhanced trading logger with structured output.

#### Constructor
```python
def __init__(self, name: str, log_dir: str = "logs")
```

#### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | str | Logger name |
| `log_dir` | str | Directory for log files |

#### Methods
| Method | Description | Returns |
|--------|-------------|---------|
| `def debug(message: str, **kwargs) -> None` | Log debug message | None |
| `def info(message: str, **kwargs) -> None` | Log info message | None |
| `def warning(message: str, **kwargs) -> None` | Log warning message | None |
| `def error(message: str, exc_info: bool = False, **kwargs) -> None` | Log error message | None |
| `def fatal(message: str, exc_info: bool = True, **kwargs) -> None` | Log fatal message | None |
| `def trade_execution(symbol: str, side: str, quantity: float, price: float, **kwargs) -> None` | Log trade execution | None |
| `def risk_breach(metric: str, value: float, threshold: float, action: str, **kwargs) -> None` | Log risk limit breach | None |
| `def system_alert(component: str, status: str, message: str, **kwargs) -> None` | Log system alert | None |
| `def performance_update(pnl: float, win_rate: float, trades: int, **kwargs) -> None` | Log performance update | None |
| `def strategy_change(old_strategy: str, new_strategy: str, reason: str, **kwargs) -> None` | Log strategy change | None |

#### Properties
| Property | Type | Description |
|----------|------|-------------|
| `name` | str | Logger name |
| `logger` | logging.Logger | Underlying Python logger |
| `log_dir` | str | Log directory path |

### MetricsCollector (`observability/metrics.py`)

Metrics collector with Prometheus integration.

#### Constructor
```python
def __init__(self, port: int = 9090)
```

#### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `port` | int | Port for metrics HTTP server |

#### Methods
| Method | Description | Returns |
|--------|-------------|---------|
| `def start_server() -> None` | Start Prometheus metrics HTTP server | None |
| `def increment_counter(name: str, n: int = 1, **labels) -> None` | Increment a counter metric | None |
| `def set_gauge(name: str, value: float, **labels) -> None` | Set a gauge metric | None |
| `def observe_histogram(name: str, value: float, **labels) -> None` | Observe a histogram metric | None |
| `def record_trade(symbol: str, side: str, quantity: float, price: float, pnl: float = 0) -> None` | Record a trade | None |
| `def record_signal(symbol: str, strategy: str, direction: int) -> None` | Record a signal | None |
| `def record_latency(name: str, latency_seconds: float) -> None` | Record latency | None |
| `def record_error(component: str, error_type: str) -> None` | Record an error | None |
| `def update_position(symbol: str, size: float, value: float, pnl: float) -> None` | Update a position | None |
| `def update_risk(var: float, drawdown: float, leverage: float, concentration: float) -> None` | Update risk metrics | None |

#### Properties
| Property | Type | Description |
|----------|------|-------------|
| `port` | int | Metrics server port |
| `_metrics` | Dict | Internal metrics storage |
| `_start_time` | float | Server start time |

### Health Components (`observability/health.py`)

#### HealthStatus (`observability/health.py`)

Enum representing health status levels.

#### Values
| Value | Description |
|-------|-------------|
| `HEALTHY` | Component is functioning normally |
| `DEGRADED` | Component is functioning with reduced performance |
| `UNHEALTHY` | Component is not functioning properly |
| `UNKNOWN` | Component status cannot be determined |

#### Methods
| Method | Description |
|--------|-------------|
| `value` | Get the string value of the enum |
| `name` | Get the name of the enum |

#### ComponentHealth (`observability/health.py`)

Health status for a single component.

#### Fields
| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Component name |
| `status` | HealthStatus | Current health status |
| `message` | str | Status message |
| `last_check` | float | Last check timestamp |
| `metadata` | Dict[str, Any] | Additional information |

#### Methods
| Method | Description |
|--------|-------------|
| *(Standard dataclass methods)* | All standard methods from `@dataclass` decorator |

#### HealthCheck (`observability/health.py`)

Abstract base class for health checks.

#### Methods
| Method | Description | Returns |
|--------|-------------|---------|
| `def check() -> ComponentHealth` | Perform the health check | ComponentHealth |
| `property name -> str` | Name of the component being checked | Component name |

#### PingHealthCheck (`observability/health.py`)

Check if a host/port is reachable.

#### Constructor
```python
def __init__(self, name: str, host: str, port: int, timeout: float = 5.0)
```

#### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | str | Name of the health check |
| `host` | str | Hostname or IP address |
| `port` | int | Port number |
| `timeout` | float | Timeout in seconds |

#### Methods
| Method | Description | Returns |
|--------|-------------|---------|
| `def check() -> ComponentHealth` | Check if host is reachable | ComponentHealth |

#### LambdaHealthCheck (`observability/health.py`)

Health check with a lambda function.

#### Constructor
```python
def __init__(self, name: str, check_fn: Callable[[], tuple])
```

#### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | str | Name of the health check |
| `check_fn` | Callable[[], tuple] | Function returning (status_str, message, metadata) |

#### Methods
| Method | Description | Returns |
|--------|-------------|---------|
| `def check() -> ComponentHealth` | Run the lambda health check | ComponentHealth |

#### HealthCheckRegistry (`observability/health.py`)

Registry for all health checks.

#### Methods
| Method | Description | Returns |
|--------|-------------|---------|
| `def register(check: HealthCheck) -> None` | Register a health check | None |
| `def unregister(name: str) -> None` | Unregister a health check | None |
| `def check_all() -> Dict[str, ComponentHealth]` | Run all health checks | Dictionary of results |
| `def get_status() -> tuple` | Get overall system status | (overall_status, results_dict) |
| `def to_dict() -> Dict` | Convert to dictionary for JSON serialization | Dictionary representation |

#### HealthServer (`observability/health.py`)

HTTP server for health check endpoints.

#### Constructor
```python
def __init__(self, port: int = 8080)
```

#### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `port` | int | Port for health check server |

#### Methods
| Method | Description | Returns |
|--------|-------------|---------|
| `def register_default_checks(config: Dict) -> None` | Register default health checks | None |
| `def start() -> None` | Start the health check server | None |
| `def _run_server() -> None` | Run the HTTP server | None |
| `def stop() -> None` | Stop the health check server | None |

#### Properties
| Property | Type | Description |
|----------|------|-------------|
| `port` | int | Health check server port |
| `registry` | HealthCheckRegistry | Registry of health checks |
| `_server_thread` | Optional[threading.Thread] | Server thread |
| `_running` | bool | Whether the server is running |

### Alerting Components (`observability/alerting.py`)

#### AlertSeverity (`observability/alerting.py`)

Enum representing alert severity levels.

#### Values
| Value | Description |
|-------|-------------|
| `DEBUG` | Debug-level information |
| `INFO` | Informational message |
| `WARNING` | Warning message |
| `ERROR` | Error message |
| `CRITICAL` | Critical error requiring immediate attention |

#### Methods
| Method | Description |
|-------|-------------|
| `value` | Get the integer value of the enum |
| `name` | Get the name of the enum |

#### AlertChannel (`observability/alerting.py`)

Enum representing available alert channels.

#### Values
| Value | Description |
|-------|-------------|
| `TELEGRAM` | Telegram bot alerts |
| `EMAIL` | Email alerts |
| `SLACK` | Slack notifications |
| `LOG` | Log-based alerts |
| `WEBHOOK` | Webhook alerts |

#### Methods
| Method | Description |
|--------|-------------|
| `value` | Get the string value of the enum |
| `name` | Get the name of the enum |

#### Alert (`observability/alerting.py`)

Represents an alert.

#### Fields
| Field | Type | Description |
|-------|------|-------------|
| `title` | str | Alert title |
| `message` | str | Alert message |
| `severity` | AlertSeverity | Alert severity level |
| `channel` | AlertChannel | Alert delivery channel |
| `timestamp` | datetime | Alert timestamp (UTC) |
| `metadata` | Dict[str, Any] | Additional alert information |
| `correlation_id` | Optional[str] | Correlation ID for tracing |

#### Methods
| Method | Description |
|--------|-------------|
| *(Standard dataclass methods)* | All standard methods from `@dataclass` decorator |

#### AlertRateLimiter (`observability/alerting.py`)

Rate limiter for alerts to prevent spam.

#### Constructor
```python
def __init__(self, max_per_minute: int = 10, max_per_hour: int = 100)
```

#### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `max_per_minute` | int | Maximum alerts per minute per key |
| `max_per_hour` | int | Maximum alerts per hour per key |

#### Methods
| Method | Description | Returns |
|--------|-------------|---------|
| `def is_allowed(alert_key: str) -> bool` | Check if an alert is allowed based on rate limits | Boolean |
| `def _cleanup_old_counts(now: float) -> None` | Remove old entries from rate limit counters | None |

#### TelegramAlertHandler (`observability/alerting.py`)

Telegram bot alert handler.

#### Constructor
```python
def __init__(self, bot_token: str, chat_ids: List[str], parse_mode: str = None)
```

#### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `bot_token` | str | Telegram bot token |
| `chat_ids` | List[str] | List of Telegram chat IDs |
| `parse_mode` | str | Telegram message parse mode |

#### Methods
| Method | Description | Returns |
|--------|-------------|---------|
| `async def send_alert(self, alert: Alert, reply_markup: Optional[Dict] = None) -> bool` | Send alert to Telegram | Success status |
| `def _get_severity_emoji(self, severity: AlertSeverity) -> str` | Get emoji for severity level | Emoji string |
| `def _format_message(self, alert: Alert, emoji: str) -> str` | Format alert message for Telegram | Formatted message string |
| `async def _send_message(self, chat_id: str, text: str, reply_markup: Optional[Dict] = None) -> None` | Send message via Telegram API | None |

#### LogAlertHandler (`observability/alerting.py`)

Log-based alert handler.

#### Constructor
```python
def __init__(self, logger_name: str = "trading.alerts", level: int = logging.WARNING)
```

#### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `logger_name` | str | Logger name for alert logging |
| `level` | int | Logging level for alerts |

#### Methods
| Method | Description | Returns |
|--------|-------------|---------|
| `async def send_alert(self, alert: Alert) -> None` | Send alert to log | None |

#### AlertManager (`observability/alerting.py`)

Central alert management system.

#### Methods
| Method | Description | Returns |
|--------|-------------|---------|
| `@classmethod def get_instance() -> 'AlertManager'` | Get singleton instance | AlertManager instance |
| `def configure_telegram(bot_token: str, chat_ids: List[str]) -> None` | Configure Telegram handler | None |
| `def configure_log(logger_name: str = "trading.alerts") -> None` | Configure log handler | None |
| `def add_filter(filter_func: Callable[[Alert], bool]) -> None` | Add an alert filter | None |
| `async def send_alert(self, alert: Alert, reply_markup: Optional[Dict] = None) -> bool` | Send an alert through configured channels | Success status |
| `def send_alert_sync(self, alert: Alert, reply_markup: Optional[Dict] = None):` | Synchronous wrapper for sending alerts | None |

#### Convenience Functions (`observability/alerting.py`)

| Function | Description | Returns |
|--------|-------------|---------|
| `def create_trading_alert(title: str, message: str, severity: AlertSeverity = AlertSeverity.INFO, metadata: Optional[Dict[str, Any]] = None) -> Alert` | Helper to create trading alerts | Alert object |
| `async def send_trade_execution_alert(symbol: str, side: str, quantity: float, price: float, success: bool, error: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None` | Send trade execution alert | None |
| `async def send_risk_alert(message: str, violation_type: str, details: Dict[str, Any]) -> None` | Send risk management alert | None |
| `async def send_system_status_alert(component: str, status: str, details: Optional[Dict[str, Any]] = None) -> None` | Send system status change alert | None |
| `def configure_alerting_from_env() -> None` | Configure alerting from environment variables | None |

## Configuration System

### ConfigManager (`config/config_manager.py`)

Handles loading, validation, and retrieval of configuration values.

#### Constructor
```python
def __init__(self, config_dir: str)
```

#### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `config_dir` | str | Directory containing configuration files |

#### Methods
| Method | Description | Returns |
|--------|-------------|---------|
| `def load_config(config_name: str = "unified") -> Dict` | Load configuration from file | Configuration dictionary |
| `def get_config_value(config: Dict, key_path: str, default: Any = None) -> Any` | Get nested configuration value | Configuration value |
| `def set_config_value(config: Dict, key_path: str, value: Any) -> Dict` | Set nested configuration value | Updated configuration dictionary |
| `def validate_config(config: Dict, config_name: str) -> None` | Validate configuration against schema | None (raises exception on failure) |
| `@staticmethod def create_default_config(config_dir: str) -> None` | Create default configuration files | None |

#### Configuration File Format
Configuration files are YAML files with the following structure:
```yaml
# Section name
section_name:
  subsection_name:
    parameter_name: parameter_value
    another_parameter: another_value
```

#### Configuration Validation
The system validates:
- Required fields are present
- Field types are correct
- Field values are within acceptable ranges
- Dependencies between fields are satisfied
- No contradictory settings exist

## Exception Types

The system defines several custom exception types for error handling:

### BaseException (`unified_trading_system.exceptions.BaseException`)

Base class for all custom exceptions in the system.

### ConfigurationError (`unified_trading_system.exceptions.ConfigurationError`)

Raised when there is an error in configuration loading or validation.

### PerceptionError (`unified_trading_system.exceptions.PerceptionError`)

Raised when there is an error in the perception layer (market data processing, belief state formation).

### DecisionError (`unified_trading_system.exceptions.DecisionError`)

Raised when there is an error in the decision layer (signal generation, aggression control).

### RiskError (`unified_trading_system.exceptions.RiskError`)

Raised when there is an error in the risk layer (risk assessment, protection).

### ExecutionError (`unified_trading_system.exceptions.ExecutionError`)

Raised when there is an error in the execution layer (order planning, execution).

### FeedbackError (`unified_trading_system.exceptions.FeedbackError`)

Raised when there is an error in the feedback layer (performance monitoring, learning).

### ObservabilityError (`unified_trading_system.exceptions.ObservabilityError`)

Raised when there is an error in the observability layer (logging, metrics, health, alerting).

### AdaptationError (`unified_trading_system.exceptions.AdaptationError`)

Raised when there is an error in the adaptation layer (concept drift detection, model adaptation).

## Usage Examples

### Basic System Initialization
```python
import asyncio
from continuous_trading_loop import create_testnet_trading_loop

async def main():
    # Create a testnet trading loop with default configuration
    loop = create_testnet_trading_loop()
    
    # Initialize the system
    await loop.initialize()
    
    # Start the trading loop
    await loop.start()  # Runs until interrupted

# Run the async main function
asyncio.run(main())
```

### Custom Configuration Initialization
```python
from continuous_trading_loop import EnhancedTradingLoop, TradingConfig, TradingMode
from risk.unified_risk_manager import RiskManifold
from decision.signal_generator import SignalGenerator
from perception.belief_state import BeliefStateEstimator

# Create custom configuration
config = TradingConfig(
    mode=TradingMode.PAPER,
    symbols=["BTC/USDT", "ETH/USDT"],
    cycle_interval=10.0,
    max_position_size=0.1,
    max_daily_loss=5000.0,
    max_orders_per_minute=20,
    enable_alerting=False
)

# Create components with custom configuration
belief_estimator = BeliefStateEstimator()
signal_generator = SignalGenerator({'min_confidence_threshold': 0.5})
risk_manager = RiskManifold()
trading_loop = EnhancedTradingLoop(config)
```

### Component-Level Usage
```python
# Belief state estimation
from perception.belief_state import BeliefStateEstimator

estimator = BeliefStateEstimator()
market_data = {
    'bid_price': 50000.0,
    'ask_price': 50010.0,
    'bid_size': 1.5,
    'ask_size': 1.0,
    'last_price': 50005.0,
    'last_size': 2.0
}
belief_state = estimator.update(market_data)

# Signal generation
from decision.signal_generator import SignalGenerator

signal_gen = SignalGenerator()
signal = signal_gen.generate_signals(belief_state, "BTC/USDT")

# Risk assessment
from risk.unified_risk_manager import RiskManifold

risk_manager = RiskManifold()
portfolio_state = {
    'drawdown': 0.02,
    'daily_pnl': 0.003,
    'leverage_ratio': 0.3,
    'total_value': 100000.0
}
market_data = {
    'volatility': 0.12,
    'spread_bps': 1.5,
    'liquidity': 0.7
}
assessment = risk_manager.assess_risk(
    belief_state=belief_state.to_dict(),
    portfolio_state=portfolio_state,
    market_data=market_data
)

# Execution planning
from execution.smart_order_router import ExecutionModel, ExecutionIntent

execution_model = ExecutionModel()
intent = ExecutionIntent(
    symbol="BTC/USDT",
    side="BUY",
    quantity=0.01,
    urgency=0.5,
    max_slippage=5.0,
    min_time_limit=1.0,
    max_time_limit=10.0,
    aggression_level=0.5,
    timestamp=int(time.time() * 1e9)
)
plan = execution_model.plan_execution(intent, {
    'symbol': 'BTC/USDT',
    'mid_price': 50005.0,
    'spread_bps': 2.0,
    'volatility_estimate': 0.15,
    'liquidity_estimate': 0.6
})
```

### Observability Usage
```python
# Logging
from observability.logging import get_logger, info, warning, error

logger = get_logger("my_component")
logger.info("Starting operation", component="my_component", version="1.0")
info("This is an info message", key="value")
warning("This is a warning", metric="value", threshold=1.0)
error("This is an error", exc_info=True)

# Metrics
from observability.metrics import get_metrics, increment_counter, set_gauge

metrics = get_metrics()
increment_counter("trades_executed", 1, symbol="BTC/USDT", side="BUY")
set_gauge("position_size", 0.015, symbol="BTC/USDT")
set_gauge("position_value", 1000.0, symbol="BTC/USDT")

# Health checks
from observability.health import get_health_server, LambdaHealthCheck

health_server = get_health_server(8080)
health_server.registry.register(LambdaHealthCheck(
    "custom_check",
    lambda: ("healthy", "Custom check passed", {"value": 42})
))
health_server.start()

# Alerting
from observability.alerting import (
    get_alert_manager, 
    create_trading_alert,
    send_trade_execution_alert,
    send_risk_alert,
    send_system_status_alert
)

# Send a trading alert
alert_manager = get_alert_manager()
alert_manager.configure_log()  # Enable logging alerts

alert = create_trading_alert(
    title="Test Alert",
    message="This is a test alert",
    severity=AlertSeverity.INFO
)
await alert_manager.send_alert(alert)

# Send trade execution alert
await send_trade_execution_alert(
    symbol="BTC/USDT",
    side="BUY",
    quantity=0.01,
    price=50000.0,
    success=True
)

# Send risk alert
await send_risk_alert(
    message="Position size limit approaching",
    violation_type="position_limit_warning",
    details={
        "current_position": 0.09,
        "limit": 0.1,
        "utilization": 0.9
    }
)

# Send system status alert
await send_system_status_alert(
    component="trading_loop",
    status="healthy",
    details={
        "cycles_completed": 42,
        "uptime_seconds": 3600
    }
)
```

## Error Handling and Logging Conventions

### Error Handling
The system follows these error handling conventions:

1. **Specific Exceptions**: Use specific exception types rather than generic Exception
2. **Contextual Information**: Include relevant context in exception messages
3. **Logging**: Log exceptions at appropriate levels (error for unexpected, warning for expected)
4. **Recovery**: Attempt recovery when possible, fail safely when not
5. **Propagation**: Allow exceptions to propagate to appropriate handling layers

### Logging Levels
The system uses standard Python logging levels:

| Level | When to Use |
|-------|-------------|
| `DEBUG` | Detailed information for diagnosing problems |
| `INFO` | Confirmation that things are working as expected |
| `WARNING` | Indication that something unexpected happened |
| `ERROR` | Due to a more serious problem, the software has not been able to perform some function |
| `CRITICAL` | A serious error, indicating that the program itself may be unable to continue running |

### Logging Best Practices
- Include relevant contextual information in log messages
- Use structured logging for machine readability
- Log at appropriate levels to avoid noise
- Include correlation IDs for request tracing
- Log both expected and unexpected events for complete audit trail

## Version Compatibility and Stability

### API Stability Guarantees
- **Major Version Changes**: May break backward compatibility
- **Minor Version Changes**: Should maintain backward compatibility for public APIs
- **Patch Version Changes**: Bug fixes and internal improvements, fully backward compatible

### Deprecation Policy
- Deprecated APIs will be marked with warnings for at least one minor version
- Deprecated APIs will be removed after the deprecation period
- Migration guides will be provided for breaking changes

### Experimental Features
- Features marked as experimental may change or be removed without notice
- Experimental features are opt-in and not enabled by default
- Feedback on experimental features is encouraged

## Performance Characteristics

### Time Complexity
- **Belief State Update**: O(f) where f is number of features
- **Signal Generation**: O(s) where s is number of symbols being processed
- **Risk Assessment**: O(r) where r is number of risk factors
- **Execution Planning**: O(1) - primarily formula-based calculations
- **Full System Cycle**: O(n × (f + s + r)) where n is number of cycles

### Space Complexity
- **Belief State Storage**: O(1) per symbol being tracked
- **History Storage**: O(h) where h is history size (bounded by configuration)
- **Metrics Storage**: O(m) where m is number of metric types
- **Log Storage**: O(l) where l is number of log entries (rotating files)

### Latency Characteristics
- **Component-to-Component Latency**: Typically <1ms for in-process calls
- **Full Trading Cycle Latency**: Configurable, default 30 seconds
- **External API Latency**: Depends on connected services (exchange, alerting, etc.)
- **Metrics Exposure Latency**: Typically <10ms for Prometheus scraping

These performance characteristics make the system suitable for:
- High-frequency trading strategies (with reduced cycle intervals)
- Medium-frequency trading (default settings)
- Low-frequency trading (increased cycle intervals)
- Research and backtesting (flexible configuration)