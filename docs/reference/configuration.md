# Configuration Reference

This document provides a complete reference to the configuration system of the Unified Trading System. It covers all configuration options, their valid values, default settings, and how they affect system behavior.

## Configuration System Overview

The Unified Trading System uses a hierarchical configuration system based on YAML files. Configuration can be:

1. **Loaded from files**: YAML files in the `config/` directory
2. **Overridden by environment variables**: Using the `.env` file
3. **Modified at runtime**: Through the ConfigManager API
4. **Validated**: Against schemas to prevent invalid configurations

## Configuration File Structure

Configuration files are organized by function and environment:

```
config/
├── unified.yaml                 # Base configuration (all environments)
├── learning.yaml                # Learning-oriented configuration
├── learning_high_wr.yaml        # High win rate learning configuration
├── environments/                # Environment-specific overrides
│   ├── development.yaml         # Development environment
│   ├── staging.yaml             # Staging environment
│   └── production.yaml          # Production environment
└── config_manager.py            # Configuration management logic
```

## Configuration Loading Order

The system loads configuration in this order:
1. Base configuration (`unified.yaml`)
2. Specific configuration file (e.g., `learning_high_wr.yaml`)
3. Environment-specific overrides (from `environments/` directory)
4. Environment variables (from `.env` file)
5. Runtime overrides (via ConfigManager API)

Later sources override earlier ones.

## Complete Configuration Reference

### System Section
Basic system identification and metadata.

```yaml
system:
  name: "Unified Trading System"
  version: "1.0.0"
  environment: "development"  # development, staging, production
  debug: false                # Enable debug mode
```

| Parameter | Type | Default | Valid Values | Description |
|-----------|------|---------|--------------|-------------|
| `name` | string | "Unified Trading System" | Any string | System identifier |
| `version` | string | "1.0.0" | Semantic version | System version |
| `environment` | string | "development" | development, staging, production | Deployment environment |
| `debug` | boolean | false | true, false | Enable debug mode |

### Perception Layer Configuration
Configuration for market data processing and belief state formation.

```yaml
perception:
  feature_extraction:
    enabled: true
    lookback_period: 20  # Number of periods to consider for feature calculation
    ofi_weight: 0.2
    i_star_weight: 0.15
    l_star_weight: 0.15
    s_star_weight: 0.1
    depth_imbalance_weight: 0.1
    volume_imbalance_weight: 0.1
    price_momentum_weight: 0.1
    volatility_estimate_weight: 0.1
    
  regime_detection:
    n_regimes: 8
    transition_matrix_prior: 0.125  # Prior probability for each regime
    emission_covariance_prior: 0.1
    
  data_sources:
    primary: "simulated"  # simulated, binance, coinbase, kraken
    backup: ["binance", "coinbase"]
    update_frequency: 1.0  # Seconds between updates
    
  validation:
    enabled: true
    max_price_change_per_second: 0.1  # 10% max change per second
    min_spread_bps: 0.1
    max_spread_bps: 1000.0
```

| Parameter | Type | Default | Valid Values | Description |
|-----------|------|---------|--------------|-------------|
| `feature_extraction.enabled` | boolean | true | true, false | Enable microstructure feature extraction |
| `feature_extraction.lookback_period` | integer | 20 | 1-100 | Periods to consider for feature calculation |
| `feature_extraction.ofi_weight` | float | 0.2 | 0.0-1.0 | Weight for OFI in belief formation |
| `feature_extraction.i_star_weight` | float | 0.15 | 0.0-1.0 | Weight for I* in belief formation |
| `feature_extraction.l_star_weight` | float | 0.15 | 0.0-1.0 | Weight for L* in belief formation |
| `feature_extraction.s_star_weight` | float | 0.1 | 0.0-1.0 | Weight for S* in belief formation |
| `feature_extraction.depth_imbalance_weight` | float | 0.1 | 0.0-1.0 | Weight for depth imbalance in belief formation |
| `feature_extraction.volume_imbalance_weight` | float | 0.1 | 0.0-1.0 | Weight for volume imbalance in belief formation |
| `feature_extraction.price_momentum_weight` | float | 0.1 | 0.0-1.0 | Weight for price momentum in belief formation |
| `feature_extraction.volatility_estimate_weight` | float | 0.1 | 0.0-1.0 | Weight for volatility estimate in belief formation |
| `regime_detection.n_regimes` | integer | 8 | 2-16 | Number of market regimes to detect |
| `regime_detection.transition_matrix_prior` | float | 0.125 | 0.0-1.0 | Prior probability for each regime |
| `regime_detection.emission_covariance_prior` | float | 0.1 | 0.0-1.0 | Prior for emission covariance |
| `data_sources.primary` | string | "simulated" | simulated, binance, coinbase, kraken, etc. | Primary data source |
| `data_sources.backup` | list | ["binance", "coinbase"] | List of exchange names | Backup data sources |
| `data_sources.update_frequency` | float | 1.0 | 0.1-60.0 | Seconds between market data updates |
| `validation.enabled` | boolean | true | true, false | Enable market data validation |
| `validation.max_price_change_per_second` | float | 0.1 | 0.0-1.0 | Maximum allowed price change per second |
| `validation.min_spread_bps` | float | 0.1 | 0.0-1000.0 | Minimum allowed spread in basis points |
| `validation.max_spread_bps` | float | 1000.0 | 0.0-1000.0 | Maximum allowed spread in basis points |

### Decision Layer Configuration
Configuration for signal generation and aggression control.

```yaml
decision:
  signal_generation:
    # Core thresholds
    min_confidence_threshold: 0.45
    min_expected_return: 0.003
    min_uncertainty: 0.05
    max_uncertainty: 0.20
    
    # Signal strength and position sizing
    min_signal_strength: 0.005
    position_scaling_factor: 1.0
    
    # Uncertainty gates (by regime)
    epistemic_gates:
      crisis: 0.10
      volatile: 0.15
      bear: 0.20
      recovery: 0.25
      bull: 0.30
      
    aleatoric_gates:
      crisis: 0.05
      volatile: 0.10
      bear: 0.15
      recovery: 0.20
      bull: 0.25
      
    # Quality scoring bonuses/penalties
    epistemic_bonus_thresholds:
      excellent: 0.05   # < 5% epistemic = +0.15
      good: 0.10        # < 10% = +0.10
      moderate: 0.15     # < 15% = +0.05
      neutral: 0.25      # < 25% = 0.0
      poor: 0.35         # < 35% = -0.05
      reject: 1.0        # >= 35% = -0.15
      
    aleatoric_bonus_thresholds:
      excellent: 0.03   # < 3% aleatoric = +0.10
      good: 0.07         # < 7% = +0.05
      neutral: 0.15      # < 15% = 0.0
      moderate: 0.25     # < 25% = -0.03
      poor: 1.0         # >= 25% = -0.10
      
    # Side bias (prefer BUY)
    buy_bias: 0.02
    
    # Symbol weights (higher for more liquid/proven symbols)
    symbol_weights:
      BTC/USDT: 1.0
      ETH/USDT: 0.9
      BNB/USDT: 0.8
      SOL/USDT: 0.8
      ADA/USDT: 0.6
      XRP/USDT: 0.6
      DOGE/USDT: 0.6
      MATIC/USDT: 0.6
      DOT/USDT: 0.7
      AVAX/USDT: 0.7
      LINK/USDT: 0.7
      UNI/USDT: 0.6
      LTC/USDT: 0.7
      BCH/USDT: 0.7
      ATOM/USDT: 0.6
      ETC/USDT: 0.6
      XLM/USDT: 0.5
      ALGO/USDT: 0.5
      VET/USDT: 0.5
      FIL/USDT: 0.6
      
    # Adaptive threshold adjustments by regime
    regime_threshold_adjustments:
      bull: -0.05
      bear: 0.05
      volatile: 0.10
      crisis: 0.15
      recovery: 0.02
      
    # Existing settings
    volatility_scaling: true
    regime_filters: true
    filter_by_uncertainty: true
    
  aggression_controller:
    # Core learning parameters
    kappa: 0.1          # Learning rate for aggression updates
    lambda_: 0.05       # Rate of aggression decay toward target
    beta_max: 0.5       # Maximum aggression level
    eta: 0.01           # Execution stress sensitivity
    alpha_target: 0.5   # Target aggression level
    
    # Stability parameters
    lyapunov_weight: 0.5  # Weight of Lyapunov term in stability analysis
    min_aggression: 0.0   # Minimum allowed aggression level
    max_aggression: 1.0   # Maximum allowed aggression level
```

| Parameter | Type | Default | Valid Values | Description |
|-----------|------|---------|--------------|-------------|
| `signal_generation.min_confidence_threshold` | float | 0.45 | 0.0-1.0 | Minimum belief state confidence to generate signal |
| `signal_generation.min_expected_return` | float | 0.003 | 0.0-1.0 | Minimum expected return magnitude to act on |
| `signal_generation.min_uncertainty` | float | 0.05 | 0.0-1.0 | Minimum uncertainty threshold |
| `signal_generation.max_uncertainty` | float | 0.20 | 0.0-1.0 | Maximum uncertainty threshold |
| `signal_generation.min_signal_strength` | float | 0.005 | 0.0-1.0 | Minimum signal strength to act on |
| `signal_generation.position_scaling_factor` | float | 1.0 | 0.0-10.0 | Scaling factor for position sizes |
| `signal_generation.epistemic_gates.*` | float | Varies by regime | 0.0-1.0 | Maximum epistemic uncertainty allowed by regime |
| `signal_generation.aleatoric_gates.*` | float | Varies by regime | 0.0-1.0 | Maximum aleatoric uncertainty allowed by regime |
| `signal_generation.epistemic_bonus_thresholds.*` | float | Varies | 0.0-1.0 | Epistemic uncertainty thresholds for bonuses |
| `signal_generation.aleatoric_bonus_thresholds.*` | float | Varies | 0.0-1.0 | Aleatoric uncertainty thresholds for bonuses |
| `signal_generation.buy_bias` | float | 0.02 | -0.5 to 0.5 | Preference for BUY vs SELL signals (positive = favors BUY) |
| `signal_generation.symbol_weights.*` | float | Varies by symbol | 0.0-2.0 | Relative weight for each symbol in signal generation |
| `signal_generation.regime_threshold_adjustments.*` | float | Varies by regime | -0.2 to 0.2 | Adjustment to thresholds by market regime |
| `signal_generation.volatility_scaling` | boolean | true | true, false | Scale thresholds by volatility |
| `signal_generation.regime_filters` | boolean | true | true, false | Filter signals by regime compatibility |
| `signal_generation.filter_by_uncertainty` | boolean | true | true, false | Filter signals by uncertainty levels |
| `aggression_controller.kappa` | float | 0.1 | 0.01-0.5 | Learning rate for aggression updates |
| `aggression_controller.lambda_` | float | 0.05 | 0.001-0.2 | Rate of aggression decay toward target |
| `aggression_controller.beta_max` | float | 0.5 | 0.1-1.0 | Maximum aggression level |
| `aggression_controller.eta` | float | 0.01 | 0.001-0.1 | Execution stress sensitivity |
| `aggression_controller.alpha_target` | float | 0.5 | 0.0-1.0 | Target aggression level |
| `aggression_controller.lyapunov_weight` | float | 0.5 | 0.0-1.0 | Weight of Lyapunov term in stability analysis |
| `aggression_controller.min_aggression` | float | 0.0 | 0.0-1.0 | Minimum allowed aggression level |
| `aggression_controller.max_aggression` | float | 1.0 | 0.0-1.0 | Maximum allowed aggression level |

### Execution Layer Configuration
Configuration for order execution and smart order routing.

```yaml
execution:
  smart_order_router:
    execution_eta: 0.01
    market_impact_factor: 0.1
    latency_base: 5
    slippage_factor: 0.05
    
    # Order type preferences
    order_type_preferences:
      MARKET: 0.2
      LIMIT: 0.5
      STOP_LIMIT: 0.1
      ICEBERG: 0.1
      TWAP: 0.05
      VWAP: 0.05
      
    # Venue characteristics
    venue_characteristics:
      primary:
        latency: 2
        fill_rate: 0.95
        slippage_factor: 0.03
        market_impact: 0.02
      secondary:
        latency: 5
        fill_rate: 0.85
        slippage_factor: 0.05
        market_impact: 0.04
      dark_pool:
        latency: 10
        fill_rate: 0.60
        slippage_factor: 0.01
        market_impact: 0.005
```

| Parameter | Type | Default | Valid Values | Description |
|-----------|------|---------|--------------|-------------|
| `execution.smart_order_router.execution_eta` | float | 0.01 | 0.001-0.2 | Execution feedback gain |
| `execution.smart_order_router.market_impact_factor` | float | 0.1 | 0.0-1.0 | Market impact scaling factor |
| `execution.smart_order_router.latency_base` | int | 5 | 1-100 | Base latency in milliseconds |
| `execution.smart_order_router.slippage_factor` | float | 0.05 | 0.0-1.0 | Base slippage factor |
| `execution.smart_order_router.order_type_preferences.*` | float | Varies by type | 0.0-1.0 | Preference weight for each order type |
| `execution.smart_order_router.venue_characteristics.primary.latency` | int | 2 | 1-1000 | Primary venue latency in ms |
| `execution.smart_order_router.venue_characteristics.primary.fill_rate` | float | 0.95 | 0.0-1.0 | Primary venue fill rate |
| `execution.smart_order_router.venue_characteristics.primary.slippage_factor` | float | 0.03 | 0.0-1.0 | Primary venue slippage factor |
| `execution.smart_order_router.venue_characteristics.primary.market_impact` | float | 0.02 | 0.0-1.0 | Primary venue market impact |
| `execution.smart_order_router.venue_characteristics.secondary.latency` | int | 5 | 1-1000 | Secondary venue latency in ms |
| `execution.smart_order_router.venue_characteristics.secondary.fill_rate` | float | 0.85 | 0.0-1.0 | Secondary venue fill rate |
| `execution.smart_order_router.venue_characteristics.secondary.slippage_factor` | float | 0.05 | 0.0-1.0 | Secondary venue slippage factor |
| `execution.smart_order_router.venue_characteristics.secondary.market_impact` | float | 0.04 | 0.0-1.0 | Secondary venue market impact |
| `execution.smart_order_router.venue_characteristics.dark_pool.latency` | int | 10 | 1-1000 | Dark pool latency in ms |
| `execution.smart_order_router.venue_characteristics.dark_pool.fill_rate` | float | 0.60 | 0.0-1.0 | Dark pool fill rate |
| `execution.smart_order_router.venue_characteristics.dark_pool.slippage_factor` | float | 0.01 | 0.0-1.0 | Dark pool slippage factor |
| `execution.smart_order_router.venue_characteristics.dark_pool.market_impact` | float | 0.005 | 0.0-1.0 | Dark pool market impact |

### Risk Layer Configuration
Configuration for risk management and protection systems.

```yaml
risk:
  risk_manifold:
    # Risk manifold parameters
    risk_sensitivity: 1.0
    nonlinearity_factor: 0.5
    
    # LVR protection level thresholds
    drawdown_warning: 0.05    # 5% drawdown -> Level 1
    drawdown_danger: 0.10     # 10% drawdown -> Level 2
    drawdown_critical: 0.15   # 15% drawdown -> Level 3
    
    daily_loss_warning: 0.03  # 3% daily loss -> Level 1
    daily_loss_danger: 0.05   # 5% daily loss -> Level 2
    daily_loss_critical: 0.08 # 8% daily loss -> Level 3
    
    leverage_warning: 25.0
    leverage_danger: 28.0
    leverage_critical: 30.0
    
    # Correlation and concentration thresholds
    correlation_warning: 0.6  # 60% correlation -> Level 1
    correlation_danger: 0.8   # 80% correlation -> Level 2
    concentration_warning: 0.3 # 30% in single position -> Level 1
    concentration_danger: 0.5  # 50% in single position -> Level 2
    
    # Risk factor weights (must sum to 1.0)
    risk_weights:
      drawdown: 0.25
      daily_loss: 0.20
      leverage_ratio: 0.15
      volatility: 0.15
      liquidity_score: 0.10
      concentration_risk: 0.10
      correlation_risk: 0.05
      
  position_sizing:
    # Position sizing based on signal quality
    high_quality: 0.10       # Quality >= 0.70 - conservative sizing
    medium_quality: 0.03     # Quality 0.50-0.70 - smaller
    low_quality: 0.005       # Quality < 0.50 - very small (almost none)
    
  risk_controls:
    max_daily_trades: 50
    win_rate_alert: 0.75
    min_signals_per_hour: 10
    leverage_factor: 30.0
```

| Parameter | Type | Default | Valid Values | Description |
|-----------|------|---------|--------------|-------------|
| `risk.risk_manifold.risk_sensitivity` | float | 1.0 | 0.1-5.0 | Overall risk sensitivity scaling |
| `risk.risk_manifold.nonlinearity_factor` | float | 0.5 | 0.0-2.0 | Nonlinearity factor in risk manifold |
| `risk.risk_manifold.drawdown_warning` | float | 0.05 | 0.0-1.0 | Drawdown threshold for Level 1 warning |
| `risk.risk_manifold.drawdown_danger` | float | 0.10 | 0.0-1.0 | Drawdown threshold for Level 2 danger |
| `risk.risk_manifold.drawdown_critical` | float | 0.15 | 0.0-1.0 | Drawdown threshold for Level 3 critical |
| `risk.risk_manifold.daily_loss_warning` | float | 0.03 | 0.0-1.0 | Daily loss threshold for Level 1 warning |
| `risk.risk_manifold.daily_loss_danger` | float | 0.05 | 0.0-1.0 | Daily loss threshold for Level 2 danger |
| `risk.risk_manifold.daily_loss_critical` | float | 0.08 | 0.0-1.0 | Daily loss threshold for Level 3 critical |
| `risk.risk_manifold.leverage_warning` | float | 25.0 | 0.0-100.0 | Leverage threshold for Level 1 warning |
| `risk.risk_manifold.leverage_danger` | float | 28.0 | 0.0-100.0 | Leverage threshold for Level 2 danger |
| `risk.risk_manifold.leverage_critical` | float | 30.0 | 0.0-100.0 | Leverage threshold for Level 3 critical |
| `risk.risk_manifold.correlation_warning` | float | 0.6 | 0.0-1.0 | Correlation threshold for Level 1 warning |
| `risk.risk_manifold.correlation_danger` | float | 0.8 | 0.0-1.0 | Correlation threshold for Level 2 danger |
| `risk.risk_manifold.concentration_warning` | float | 0.3 | 0.0-1.0 | Concentration threshold for Level 1 warning |
| `risk.risk_manifold.concentration_danger` | float | 0.5 | 0.0-1.0 | Concentration threshold for Level 2 danger |
| `risk.risk_manifold.risk_weights.*` | float | Varies by factor | 0.0-1.0 | Weight for each risk factor (should sum to 1.0) |
| `risk.position_sizing.high_quality` | float | 0.10 | 0.0-1.0 | Position size for high quality signals |
| `risk.position_sizing.medium_quality` | float | 0.03 | 0.0-1.0 | Position size for medium quality signals |
| `risk.position_sizing.low_quality` | float | 0.005 | 0.0-1.0 | Position size for low quality signals |
| `risk.risk_controls.max_daily_trades` | int | 50 | 1-1000 | Maximum trades per day |
| `risk.risk_controls.win_rate_alert` | float | 0.75 | 0.0-1.0 | Win rate threshold for alerts |
| `risk.risk_controls.min_signals_per_hour` | int | 10 | 1-1000 | Minimum expected signals per hour |
| `risk.risk_controls.leverage_factor` | float | 30.0 | 1.0-100.0 | Maximum leverage factor allowed |

### Position Sizing Configuration
Configuration for how position sizes are determined based on signal quality.

```yaml
position_sizing:
  # Base position size as fraction of capital
  base_size: 0.1
  
  # Quality-based multipliers
  quality_multipliers:
    excellent: 2.0   # Quality >= 0.9
    good: 1.5        # Quality 0.8-0.9
    fair: 1.0        # Quality 0.7-0.8
    poor: 0.5        # Quality 0.6-0.7
    very_poor: 0.2   # Quality < 0.6
    
  # Uncertainty-based adjustments
  uncertainty_adjustments:
    low_uncertainty: 1.5    # Uncertainty < 0.1
    medium_uncertainty: 1.0   # Uncertainty 0.1-0.2
    high_uncertainty: 0.5     # Uncertainty > 0.2
    
  # Regime-based adjustments
  regime_adjustments:
    bull: 1.2
    bear: 0.8
    volatile: 0.6
    crisis: 0.3
    recovery: 1.0
    sideways_low_vol: 1.1
    sideways_high_vol: 0.9
    
  # Limits
  max_position_size: 0.2
  min_position_size: 0.001
```

| Parameter | Type | Default | Valid Values | Description |
|-----------|------|---------|--------------|-------------|
| `position_sizing.base_size` | float | 0.1 | 0.0-1.0 | Base position size as fraction of capital |
| `position_sizing.quality_multipliers.*` | float | Varies | 0.0-5.0 | Multiplier for each quality level |
| `position_sizing.uncertainty_adjustments.*` | float | Varies | 0.0-5.0 | Multiplier for each uncertainty level |
| `position_sizing.regime_adjustments.*` | float | Varies | 0.0-3.0 | Multiplier for each market regime |
| `position_sizing.max_position_size` | float | 0.2 | 0.0-1.0 | Maximum allowed position size |
| `position_sizing.min_position_size` | float | 0.001 | 0.0-0.1 | Minimum allowed position size |

### Monitoring and Observability Configuration
Configuration for logging, metrics, health checks, and alerting.

```yaml
monitoring:
  # Logging configuration
  logging:
    level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    format: json  # json, text
    max_file_size_mb: 10
    backup_count: 5
    include_context: true
    include_correlation_id: true
    
  # Metrics configuration
  metrics:
    port: 9090
    enabled: true
    prefix: "trading_"
    histogram_buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    
  # Health check configuration
  health:
    port: 8080
    enabled: true
    check_interval: 30.0  # Seconds between health checks
    timeout: 10.0         # Seconds to wait for health check response
    
  # Alerting configuration
  alerting:
    enabled: true
    rate_limiting:
      max_per_minute: 10
      max_per_hour: 100
    channels:
      - log
      # - telegram  # Uncomment and configure .env for Telegram
      # - email     # Uncomment and configure for email
      # - slack     # Uncomment and configure for Slack
      # - webhook   # Uncomment and configure for webhook
    templates:
      trade_execution: "{symbol} {side} {quantity}@{price} - {status}"
      risk_alert: "🚨 {severity}: {message}"
      system_status: "{component}: {status}"
```

| Parameter | Type | Default | Valid Values | Description |
|-----------|------|---------|--------------|-------------|
| `monitoring.logging.level` | string | INFO | DEBUG, INFO, WARNING, ERROR, CRITICAL | Log level |
| `monitoring.logging.format` | string | json | json, text | Log format |
| `monitoring.logging.max_file_size_mb` | int | 10 | 1-100 | Maximum log file size in MB |
| `monitoring.logging.backup_count` | int | 5 | 0-20 | Number of backup log files to keep |
| `monitoring.logging.include_context` | boolean | true | true, false | Include context in log messages |
| `monitoring.logging.include_correlation_id` | boolean | true | true, false | Include correlation ID in log messages |
| `monitoring.metrics.port` | int | 9090 | 1024-65535 | Port for metrics HTTP server |
| `monitoring.metrics.enabled` | boolean | true | true, false | Enable metrics collection and exposition |
| `monitoring.metrics.prefix` | string | trading_ | Any string | Prefix for all metric names |
| `monitoring.metrics.histogram_buckets` | list | [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0] | List of floats | Bucket boundaries for histogram metrics |
| `monitoring.health.port` | int | 8080 | 1024-65535 | Port for health check HTTP server |
| `monitoring.health.enabled` | boolean | true | true, false | Enable health check server |
| `monitoring.health.check_interval` | float | 30.0 | 1.0-300.0 | Seconds between health checks |
| `monitoring.health.timeout` | float | 10.0 | 1.0-60.0 | Seconds to wait for health check response |
| `monitoring.alerting.enabled` | boolean | true | true, false | Enable alerting system |
| `monitoring.alerting.rate_limiting.max_per_minute` | int | 10 | 1-1000 | Maximum alerts per minute per key |
| `monitoring.alerting.rate_limiting.max_per_hour` | int | 100 | 1-10000 | Maximum alerts per hour per key |
| `monitoring.alerting.channels` | list | ["log"] | ["log"], ["telegram"], ["email"], ["slack"], ["webhook"], or combinations | Enabled alerting channels |
| `monitoring.alerting.templates.trade_execution` | string | "{symbol} {side} {quantity}@{price} - {status}" | Any string with placeholders | Template for trade execution alerts |
| `monitoring.alerting.templates.risk_alert` | string | "🚨 {severity}: {message}" | Any string with placeholders | Template for risk alerts |
| `monitoring.alerting.templates.system_status` | string | "{component}: {status}" | Any string with placeholders | Template for system status alerts |

## Environment Variables

The system reads environment variables from a `.env` file in the root directory. These override file-based configurations.

### Required Environment Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `TRADING_MODE` | Trading mode: PAPER, TESTNET, or LIVE | `TESTNET` |
| `SYMBOLS` | Comma-separated list of trading symbols | `BTC/USDT,ETH/USDT` |
| `CYCLE_INTERVAL` | Time between trading cycles in seconds | `30` |

### Optional Environment Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `MAX_POSITION_SIZE` | Maximum position size as fraction of capital | `0.1` |
| `MAX_DAILY_LOSS` | Maximum daily loss allowed | `10000` |
| `MAX_ORDERS_PER_MINUTE` | Maximum order frequency | `10` |
| `ENABLE_ALERTING` | Whether to enable alerting | `true` |
| `HEALTH_CHECK_PORT` | Port for health check server | `8080` |
| `METRICS_PORT` | Port for metrics server | `9090` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token for alerting | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `TELEGRAM_CHAT_IDS` | Comma-separated list of Telegram chat IDs | `123456789,987654321` |

### Example `.env` File
```env
# Trading Configuration
TRADING_MODE=TESTNET
SYMBOLS=BTC/USDT,ETH/USDT,BNB/USDT
CYCLE_INTERVAL=30
MAX_POSITION_SIZE=0.1
MAX_DAILY_LOSS=10000
MAX_ORDERS_PER_MINUTE=10

# Observability
ENABLE_ALERTING=true
HEALTH_CHECK_PORT=8080
METRICS_PORT=9090
LOG_LEVEL=INFO

# Alerting (Telegram example)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_IDS=123456789,987654321
```

## Configuration Validation Rules

The system validates configurations against these rules:

### System Section
- `environment` must be one of: development, staging, production
- `version` must follow semantic versioning format (major.minor.patch)

### Perception Layer
- All feature extraction weights must be non-negative
- The sum of feature extraction weights should ideally be 1.0 (not enforced but recommended)
- `n_regimes` must be >= 2
- `transition_matrix_prior` must be >= 0 and <= 1
- `update_frequency` must be > 0
- `max_price_change_per_second` must be >= 0
- `min_spread_bps` must be >= 0 and <= `max_spread_bps`
- `max_spread_bps` must be >= `min_spread_bps`

### Decision Layer
- `min_confidence_threshold` must be between 0 and 1
- `min_expected_return` must be >= 0
- `min_uncertainty` must be >= 0 and <= `max_uncertainty`
- `max_uncertainty` must be <= 1
- `min_signal_strength` must be >= 0
- All epistemic_gates values must be between 0 and 1
- All aleatoric_gates values must be between 0 and 1
- All epistemic_bonus_thresholds values must be between 0 and 1
- All aleatoric_bonus_thresholds values must be between 0 and 1
- `buy_bias` must be between -1 and 1
- All symbol_weights values must be >= 0
- All regime_threshold_adjustments values must be reasonable (typically -0.2 to 0.2)
- `kappa` must be >= 0
- `lambda_` must be >= 0
- `beta_max` must be between 0 and 1
- `eta` must be >= 0
- `alpha_target` must be between 0 and 1

### Execution Layer
- `execution_eta` must be >= 0
- `market_impact_factor` must be >= 0
- `latency_base` must be >= 1
- `slippage_factor` must be >= 0
- All order_type_preferences values must be >= 0 and ideally sum to 1.0
- All venue characteristics values must be appropriate for their meaning (latency >= 0, fill_rate between 0 and 1, etc.)

### Risk Layer
- `risk_sensitivity` must be >= 0
- `nonlinearity_factor` must be >= 0
- All threshold values must be >= 0
- All threshold values for warning < danger < critical must be ordered correctly
- All risk_weights values must be >= 0 and ideally sum to 1.0
- Position sizing values must be >= 0
- `max_daily_trades` must be >= 1
- `win_rate_alert` must be between 0 and 1
- `min_signals_per_hour` must be >= 1
- `leverage_factor` must be >= 1.0

### Monitoring Section
- `logging.level` must be one of the standard Python logging levels
- `logging.format` must be either "json" or "text"
- `max_file_size_mb` must be >= 1
- `backup_count` must be >= 0
- `metrics.port` must be a valid port number (1024-65535)
- `metrics.enabled` must be boolean
- `histogram_buckets` must be a list of increasing positive numbers
- `health.port` must be a valid port number (1024-65535)
- `health.enabled` must be boolean
- `check_interval` must be > 0
- `timeout` must be > 0
- `alerting.enabled` must be boolean
- `rate_limiting.max_per_minute` must be >= 1
- `rate_limiting.max_per_hour` must be >= `max_per_minute`
- `channels` must be a list of valid channel names
- Template strings must be valid format strings

## Environment-Specific Overrides

### Development Environment (`environments/development.yaml`)
```yaml
system:
  environment: "development"
  debug: true

perception:
  data_sources:
    primary: "simulated"
    update_frequency: 0.5  # Faster updates for development

decision:
  signal_generation:
    min_confidence_threshold: 0.3  # Lower threshold for more signals in dev
    min_expected_return: 0.001

execution:
  smart_order_router:
    latency_base: 1  # Faster execution for testing

risk:
  risk_controls:
    max_daily_trades: 100  # Higher limit for testing
    win_rate_alert: 0.5    # Lower alert threshold for testing

monitoring:
  logging:
    level: "DEBUG"  # More verbose logging in development
  metrics:
    port: 9091  # Different port to avoid conflicts
  health:
    port: 8081
```

### Staging Environment (`environments/staging.yaml`)
```yaml
system:
  environment: "staging"
  debug: false

perception:
  data_sources:
    primary: "simulated"
    update_frequency: 1.0

decision:
  signal_generation:
    min_confidence_threshold: 0.4
    min_expected_return: 0.002

monitoring:
  logging:
    level: "INFO"
  metrics:
    port: 9092
  health:
    port: 8082
```

### Production Environment (`environments/production.yaml`)
```yaml
system:
  environment: "production"
  debug: false

perception:
  data_sources:
    primary: "binance"  # Real data source in production
    update_frequency: 2.0

decision:
  signal_generation:
    min_confidence_threshold: 0.5  # Higher threshold for quality in prod
    min_expected_return: 0.005

risk:
  risk_controls:
    max_daily_trades: 20   # Conservative limit for production
    win_rate_alert: 0.75   # Standard alert threshold
    min_signals_per_hour: 15

monitoring:
  logging:
    level: "WARN"  # Less verbose in production to reduce noise
  metrics:
    port: 9090
  health:
    port: 8080
```

## Configuration Access Patterns

### Using ConfigManager API
```python
from config.config_manager import ConfigManager

# Initialize config manager
config_manager = ConfigManager("config")

# Load configuration
config = config_manager.load_config("learning_high_wr")

# Get specific values
cycle_interval = config_manager.get_config_value(config, "execution.cycle_interval")
max_position = config_manager.get_config_value(config, "risk.max_position_size")
signal_threshold = config_manager.get_config_value(config, "decision.signal_generation.min_confidence_threshold")

# Set configuration values (returns new config dict)
updated_config = config_manager.set_config_value(config, "decision.signal_generation.min_confidence_threshold", 0.5)

# Validate configuration
try:
    config_manager.validate_config(config, "learning_high_wr")
    print("Configuration is valid")
except Exception as e:
    print(f"Configuration validation failed: {e}")
```

### Direct Access (Not Recommended for Production)
```python
# Direct access bypasses validation and type safety
config = {
    "system": {
        "name": "My Trading System",
        "version": "1.0.0",
        "environment": "development"
    },
    "decision": {
        "signal_generation": {
            "min_confidence_threshold": 0.45,
            "min_expected_return": 0.003
        }
    }
}

# Access values directly (no validation)
threshold = config["decision"]["signal_generation"]["min_confidence_threshold"]
```

## Best Practices for Configuration Management

### 1. Environment Separation
- Use separate configuration files for different environments
- Never commit production secrets to version control
- Use environment variables for sensitive data (API keys, passwords)
- Test configuration changes in staging before applying to production

### 2. Version Control
- Keep configuration files in version control
- Use descriptive commit messages for configuration changes
- Tag releases with corresponding configuration versions
- Review configuration changes in pull requests

### 3. Documentation
- Document non-obvious configuration choices
- Explain why certain values were chosen
- Note any external dependencies or constraints
- Update documentation when configuration changes

### 4. Validation
- Always validate configuration before using it
- Test edge cases and extreme values
- Validate after any changes to configuration structure
- Consider implementing configuration validation in CI/CD pipeline

### 5. Security
- Never store secrets in plain text configuration files
- Use environment variables or secret management systems for:
  - API keys
  - Database passwords
  - Private keys
  - Other sensitive credentials
- Restrict file system permissions on configuration files
- Consider encrypting sensitive configuration values

### 6. Change Management
- Make one change at a time to isolate effects
- Test configuration changes thoroughly
- Have a rollback plan for problematic changes
- Monitor system behavior after configuration changes
- Document the reason for each configuration change

### 7. Performance Considerations
- Be aware of performance implications of configuration settings
- Monitor resource usage after significant configuration changes
- Consider the impact of logging levels on I/O and performance
- Evaluate the effect of check intervals on system responsiveness
- Test different values to find optimal settings for your use case

## Configuration Examples

### Minimal Configuration for Testing
```yaml
system:
  name: "Test System"
  version: "1.0.0"
  environment: "development"

perception:
  data_sources:
    primary: "simulated"
    update_frequency: 0.5

decision:
  signal_generation:
    min_confidence_threshold: 0.3
    min_expected_return: 0.001
    min_uncertainty: 0.01
    max_uncertainty: 0.5

execution:
  smart_order_router:
    latency_base: 1

risk:
  risk_controls:
    max_daily_trades: 20
    win_rate_alert: 0.5
    min_signals_per_hour: 5

monitoring:
  logging:
    level: "DEBUG"
  metrics:
    port: 9091
  health:
    port: 8081
```

### High-Frequency Trading Configuration
```yaml
system:
  name: "HFT System"
  version: "1.0.0"
  environment: "production"

perception:
  data_sources:
    primary: "binance"
    update_frequency: 0.1  # 10 updates per second

decision:
  signal_generation:
    min_confidence_threshold: 0.6
    min_expected_return: 0.001
    min_uncertainty: 0.001
    max_uncertainty: 0.5

execution:
  smart_order_router:
    latency_base: 1
    execution_eta: 0.005  # Faster learning

risk:
  risk_controls:
    max_daily_trades: 1000
    max_position_size: 0.02
    max_daily_loss: 5000
    max_orders_per_minute: 100

monitoring:
  logging:
    level: "WARN"  # Reduce logging overhead
  metrics:
    port: 9090
  health:
    port: 8080
    check_interval: 5.0  # More frequent health checks
```

### Long-Term Investment Configuration
```yaml
system:
  name: "Long-Term System"
  version: "1.0.0"
  environment: "production"

perception:
  data_sources:
    primary: "simulated"
    update_frequency: 3600.0  # Once per hour

decision:
  signal_generation:
    min_confidence_threshold: 0.7
    min_expected_return: 0.01
    min_uncertainty: 0.01
    max_uncertainty: 0.5

execution:
  smart_order_router:
    latency_base: 10  # Less concerned about latency

risk:
  risk_controls:
    max_daily_trades: 5
    max_position_size: 0.5
    max_daily_loss: 50000
    max_orders_per_minute: 2
    leverage_factor: 5.0  # Lower leverage for long-term

monitoring:
  logging:
    level: "INFO"
  metrics:
    port: 9090
  health:
    port: 8080
    check_interval: 300.0  # Check every 5 minutes
```

## Configuration Migration and Upgrades

### Version-Specific Configuration
When upgrading between major versions, you may need to:
1. Review released configuration changes
2. Update configuration files to match new schema
3. Remove deprecated parameters
4. Add new required parameters
5. Adjust values for changed defaults or meanings

### Backward Compatibility
The system strives to maintain backward compatibility:
- Minor version updates should not require configuration changes
- Major version updates may require configuration updates
- Deprecation warnings are provided for at least one minor version before removal
- Migration guides are provided for breaking changes

### Configuration Validation During Upgrades
Always validate configuration after upgrades:
```bash
# Validate all configuration files
python -c "
from config.config_manager import ConfigManager
import os

config_dir = 'config'
config_manager = ConfigManager(config_dir)

# Check all yaml files
for filename in os.listdir(config_dir):
    if filename.endswith('.yaml') or filename.endswith('.yml'):
        try:
            config = config_manager.load_config(filename[:-5])  # Remove .yaml/.yml
            config_manager.validate_config(config, filename[:-5])
            print(f'✓ {filename}: Valid')
        except Exception as e:
            print(f'✗ {filename}: Invalid - {e}')
"
```

## Troubleshooting Configuration Issues

### Common Configuration Problems

#### 1. Invalid YAML Syntax
**Symptoms**: Parsing errors on startup
**Solution**: 
- Use a YAML validator to check syntax
- Common issues: incorrect indentation, missing colons, invalid special characters
- Use `yamllint` or online YAML validators

#### 2. Missing Required Fields
**Symptoms**: Validation errors on startup
**Solution**: 
- Check error message for missing field
- Add the required field with appropriate value
- Refer to this documentation for field requirements

#### 3. Invalid Field Types
**Symptoms**: Type conversion errors or unexpected behavior
**Solution**: 
- Ensure values match expected types (string, number, boolean, list, etc.)
- Quote strings that might be confused with numbers
- Use `true`/`false` for booleans, not `True`/`False` or `1`/`0`

#### 4. Values Outside Valid Ranges
**Symptoms**: Validation errors or unstable system behavior
**Solution**: 
- Check this documentation for valid ranges
- Adjust values to be within acceptable limits
- Consider the system behavior implications of extreme values

#### 5. Conflicting Settings
**Symptoms**: Unpredictable system behavior or explicit conflict errors
**Solution**: 
- Look for settings that contradict each other
- Check regime-specific settings vs global settings
- Verify threshold ordering (warning < danger < critical)
- Ensure weights sum to approximately 1.0 where expected

#### 6. Environment Variable Overrides Not Working
**Symptoms**: Configuration not reflecting `.env` file values
**Solution**: 
- Check `.env` file format (KEY=VALUE, one per line)
- Verify variable names match expected names
- Check for typos in variable names
- Ensure `.env` file is in the correct location (project root)
- Some variables may require restart to take effect

### Diagnostic Commands

#### Validate All Configuration Files
```bash
python -c "
from config.config_manager import ConfigManager
import sys
import os

config_dir = sys.argv[1] if len(sys.argv) > 1 else 'config'
config_manager = ConfigManager(config_dir)

print(f'Validating configurations in {config_dir}...')
all_valid = True

for filename in os.listdir(config_dir):
    if filename.endswith('.yaml') or filename.endswith('.yml'):
        config_name = filename[:-5] if filename.endswith('.yaml') else filename[:-4]
        try:
            config = config_manager.load_config(config_name)
            config_manager.validate_config(config, config_name)
            print(f'✓ {config_name}: Valid')
        except Exception as e:
            print(f'✗ {config_name}: Invalid - {e}')
            all_valid = False

if all_valid:
    print('\\nAll configurations are valid!')
else:
    print('\\nSome configurations have errors!')
    sys.exit(1)
"
```

#### Show Effective Configuration
```bash
python -c "
from config.config_manager import ConfigManager
import json
import sys

config_dir = sys.argv[1] if len(sys.argv) > 1 else 'config'
config_file = sys.argv[2] if len(sys.argv) > 2 else 'learning_high_wr'

config_manager = ConfigManager(config_dir)
config = config_manager.load_config(config_file)

print(json.dumps(config, indent=2, default=str))
"
```

#### Check for Unused Configuration Parameters
```bash
# This is more complex and would require analyzing code usage
# For now, rely on code reviews and testing to detect unused parameters
```

## Configuration and Deployment Best Practices

### 1. Environment-Specific Configuration
- Use environment-specific files to handle differences between dev/stage/prod
- Keep environment-specific overrides minimal and focused
- Document why each override is necessary
- Test environment-specific configurations thoroughly

### 2. Secret Management
- Never commit secrets to version control
- Use environment variables for:
  - API keys and secrets
  - Database passwords
  - Private keys
  - Third-party service credentials
- Consider using secret management systems (HashiCorp Vault, AWS Secrets Manager, etc.) for production
- Restrict file permissions on any files containing secrets

### 3. Configuration as Code
- Treat configuration files as code
- Review configuration changes in pull requests
- Test configuration changes in automated pipelines
- Version configuration files with your application code
- Use configuration linters and validators in CI/CD

### 4. Change Management
- Make configuration changes intentionally and deliberately
- Document the reason for each configuration change
- Test configuration changes in isolation when possible
- Have a rollback plan for problematic configuration changes
- Monitor system behavior after configuration changes

### 5. Performance Considerations
- Be aware that some configuration settings affect performance:
  - Logging level (DEBUG increases I/O significantly)
  - Check intervals (more frequent checks increase CPU usage)
  - History sizes (larger histories increase memory usage)
  - Feature complexity (more complex features increase CPU usage)
- Profile system performance with different configurations
- Monitor resource usage after configuration changes

### 6. Security Considerations
- Restrict read permissions on configuration files containing sensitive data
- Consider encrypting highly sensitive configuration values
- Audit configuration access in production environments
- Implement configuration change approval workflows
- Monitor for unauthorized configuration changes

## Configuration Examples by Use Case

### Algorithm Development and Testing
```yaml
system:
  name: "Algorithm Dev System"
  version: "1.0.0"
  environment: "development"
  debug: true

perception:
  data_sources:
    primary: "simulated"
    update_frequency: 0.1  # Fast updates for rapid testing
    
decision:
  signal_generation:
    min_confidence_threshold: 0.2  # Low threshold to generate many signals for testing
    min_expected_return: 0.0001
    min_uncertainty: 0.001
    max_uncertainty: 0.5
    buy_bias: 0.0  # No bias for unbiased testing
    
execution:
  smart_order_router:
    latency_base: 1  # Minimal latency for testing
    
risk:
  risk_controls:
    max_daily_trades: 1000  # High limit for testing
    win_rate_alert: 0.5     # Low alert threshold for testing
    min_signals_per_hour: 1  # Low threshold for testing
    
monitoring:
  logging:
    level: "DEBUG"  # Maximum visibility for development
  metrics:
    port: 9091  # Different port to avoid conflicts
  health:
    port: 8081
```

### Production Deployment (Conservative)
```yaml
system:
  name: "Production Trading System"
  version: "1.0.0"
  environment: "production"
  debug: false

perception:
  data_sources:
    primary: "binance"  # Real exchange data
    update_frequency: 2.0  # Reasonable update frequency
    
decision:
  signal_generation:
    min_confidence_threshold: 0.6  # High threshold for quality
    min_expected_return: 0.005     # Require meaningful expected return
    min_uncertainty: 0.05
    max_uncertainty: 0.25
    buy_bias: 0.01  # Slight BUY bias if desired
    volatility_scaling: true
    regime_filters: true
    
execution:
  smart_order_router:
    latency_base: 5  # Reasonable latency assumptions
    execution_eta: 0.01  # Standard learning rate
    
risk:
  risk_controls:
    max_daily_trades: 20  # Conservative limit
    max_position_size: 0.15  # Reasonable position limit
    max_daily_loss: 50000  # Significant but not catastrophic
    max_orders_per_minute: 30  # Reasonable order frequency
    win_rate_alert: 0.75  # Standard alert threshold
    min_signals_per_hour: 15  # Reasonable minimum
    
monitoring:
  logging:
    level: "WARN"  # Reduced logging to minimize I/O
  metrics:
    port: 9090
  health:
    port: 8080
    check_interval: 30.0  # Standard check interval
```

### Research and Experimentation
```yaml
system:
  name: "Research System"
  version: "1.0.0"
  environment: "development"
  debug: true

perception:
  data_sources:
    primary: "simulated"
    update_frequency: 0.5  # Regular updates
    
  feature_extraction:
    # Enable all features for comprehensive testing
    ofi_weight: 0.2
    i_star_weight: 0.15
    l_star_weight: 0.15
    s_star_weight: 0.1
    depth_imbalance_weight: 0.1
    volume_imbalance_weight: 0.1
    price_momentum_weight: 0.1
    volatility_estimate_weight: 0.1
    
decision:
  signal_generation:
    # Highly configurable for experimentation
    min_confidence_threshold: 0.1  # Very low threshold
    min_expected_return: 0.00001  # Extremely low threshold
    min_uncertainty: 0.001
    max_uncertainty: 0.9  # Very high maximum
    buy_bias: 0.0  # No bias
    volatility_scaling: false  # Disable for testing
    regime_filters: false  # Disable for testing
    
  aggression_controller:
    # Highly tunable for experimentation
    kappa: 0.05  # Lower learning rate
    lambda_: 0.02  # Slower decay to target
    beta_max: 0.8  # Higher maximum aggression
    eta: 0.005  # Lower execution stress sensitivity
    alpha_target: 0.3  # Lower target aggression
    
execution:
  smart_order_router:
    # Configurable execution parameters
    latency_base: 3
    execution_eta: 0.005  # Lower learning rate
    market_impact_factor: 0.05  # Lower impact assumption
    slippage_factor: 0.02  # Lower slippage assumption
    
risk:
  risk_controls:
    max_daily_trades: 50  # Moderate limit
    max_position_size: 0.2  # Reasonable position limit
    max_daily_loss: 20000  # Moderate loss limit
    max_orders_per_minute: 20  # Moderate order frequency
    win_rate_alert: 0.6  # Lower alert threshold
    min_signals_per_hour: 5  # Low minimum
    
monitoring:
  logging:
    level: "DEBUG"  # Maximum visibility
  metrics:
    port: 9092  # Dedicated port for research
  health:
    port: 8082  # Dedicated port for research
```

This completes the configuration reference. With this document, you should be able to:
1. Understand all available configuration options
2. Know the valid values and defaults for each parameter
3. Understand how different sections affect system behavior
4. Create environment-specific configurations
5. Validate configurations before use
6. Troubleshoot configuration-related issues
7. Follow best practices for configuration management