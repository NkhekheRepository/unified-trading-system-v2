# Configuration Reference#

Complete reference for all environment variables, configuration files, and parameters in the Unified Trading System.

---

## 1. Environment Variables (`.env`)#

### 1.1 Required Variables#

| Variable | Description | Required | Example Value | Location |
|-----------|-------------|----------|-----------------|----------|
| `BINANCE_TESTNET_API_KEY` | Binance Testnet API key | **YES** | `your_testnet_api_key_here` | `.env:2` |
| `BINANCE_TESTNET_API_SECRET` | Binance Testnet API secret | **YES** | `your_testnet_api_secret_here` | `.env:3` |
| `BINANCE_TESTNET` | Set to `true` for testnet | NO | `true` | `.env:4` |
| `TESTNET_BASE_URL` | Testnet API URL | NO | `https://testnet.binancefuture.com` | `.env:5` |

### 1.2 Optional Variables#

| Variable | Description | Required | Example Value | Location |
|-----------|-------------|----------|-----------------|----------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | NO | `your_telegram_bot_token_here` | `observability/alerting.py:419` |
| `TELEGRAM_CHAT_IDS` | Comma-separated chat IDs | NO | `your_telegram_chat_id_here` | `observability/alerting.py:420` |
| `LOG_LEVEL` | Logging level | NO | `INFO` (default), `DEBUG` | `.env.example:6` |

### 1.3 Live Trading Variables#

| Variable | Description | Required | Example Value | Location |
|-----------|-------------|----------|-----------------|----------|
| `BINANCE_LIVE_API_KEY` | Live API key | YES (live) | `your_live_key_here` | `.env.live:3` |
| `BINANCE_LIVE_API_SECRET` | Live API secret | YES (live) | `your_live_secret_here` | `.env.live:4` |
| `BINANCE_LIVE` | Set to `true` for live | NO | `true` | `.env.live:5` |
| `LIVE_BASE_URL` | Live API URL | NO | `https://fapi.binance.com` | `.env.live:6` |

---

## 2. `config/unified.yaml` (244 Lines)#

### 2.1 System Section#

```yaml
system:
  name: "Unified Trading System"
  version: "3.2.0"
  environment: "development"  # "development" | "staging" | "production"
  debug: false
  log_level: "INFO"
  compliance:
    cfa_standard_I_C: true   # Disclosure of performance metrics
    cfa_standard_VI: true    # Disclosure of simulated results
```

### 2.2 Risk Management Section#

```yaml
risk_management:
  emergency: false            # Disabled after 10/10 upgrade
  max_leverage: 25            # USER CONSTRAINT: Maximum 25x
  min_leverage: 15            # USER CONSTRAINT: Minimum 15x
  default_leverage: 20        # Default for medium confidence signals
  max_positions: 5             # Concurrent positions
  max_position_size: 500       # USD (matches $500 cap)
  position_size_pct: 0.10       # 10% of balance per trade @ 15x leverage
  leverage_decrease_factor: 0.5   # 50% reduction on risk breach
  daily_loss_limit: 0.05        # 5% daily loss limit
```

### 2.3 Signal Quality Section#

```yaml
signal_quality:
  weights:
    confidence: 0.30
    inverse_uncertainty: 0.20
    regime_clarity: 0.15
    feature_consistency: 0.25
    historical_performance: 0.10
  min_signal_quality: 0.96
  min_confidence: 0.94
  min_expected_return: 0.12
```

### 2.4 Kelly Position Sizing#

```yaml
kelly_position_sizing:
  fractional_kelly: 0.5        # Half Kelly for risk management
  max_position_pct: 0.15      # Max 15% of portfolio
  min_position_pct: 0.01      # Min 1% of portfolio
  min_samples: 20             # Trades before applying Kelly
  learning_rate: 0.008         # Adaptation speed
```

---

## 3. `config/trading_params.yaml` (24 Lines)#

### 3.1 Regime Risk Multipliers#

```yaml
REGIME_RISK_MULTIPLIER:
  CRISIS: 0.3
  BEAR_HIGH_VOL: 0.5
  BEAR_LOW_VOL: 0.7
  SIDEWAYS_LOW_VOL: 0.8
  SIDEWAYS_HIGH_VOL: 0.9
  BULL_LOW_VOL: 1.0
  BULL_HIGH_VOL: 1.2
  RECOVERY: 0.9
```

### 3.2 Regime Time Map#

```yaml
REGIME_TIME_MAP:
  CRISIS: 30.0
  BEAR_HIGH_VOL: 45.0
  BEAR_LOW_VOL: 60.0
  SIDEWAYS_LOW_VOL: 75.0
  SIDEWAYS_HIGH_VOL: 90.0
  BULL_LOW_VOL: 105.0
  BULL_HIGH_VOL: 120.0
  RECOVERY: 60.0,
```

### 3.3 Volatility Time Multiplier#

```yaml
VOL_TIME_MULTIPLIER:
  high: 1.5
  low: 1.0
```

---

## 4. `TradingConfig` Dataclass (`continuous_trading_loop_binance.py:55`)#

| Parameter | Default | Description | Used By |
|-----------|---------|-------------|----------|
| `mode` | `PAPER` | `TradingMode.PAPER \| TESTNET \| LIVE` | Core loop |
| `symbols` | 20 symbols | List of `"BTC/USDT"` format | Core loop |
| `cycle_interval` | `60.0` | Seconds between cycles | Core loop |
| `max_position_size` | `500.0` | USD cap per trade | `_place_binance_order()` |
| `max_daily_loss` | `10000.0` | USD daily loss limit | Risk checks |
| `max_orders_per_minute` | `10` | Rate limit | Core loop |
| `min_confidence_threshold` | `0.85` | Signal filter | `SignalGenerator` |
| `min_expected_return` | `0.01` | Min expected return | `SignalGenerator` |
| `min_signal_strength` | `0.1` | Min signal strength | `SignalGenerator` |
| `enable_alerting` | `True` | Telegram alerts on/off | `alerting.py` |
| `health_check_port` | `8080` | Health endpoint port | `health.py` |
| `metrics_port` | `9090` | Prometheus metrics port | `metrics.py` |
| `log_dir` | `"logs"` | Log directory | `TradeJournal` |
| `base_url` | `https://testnet.binancefuture.com` | API base URL | Core loop |

---

## 5. Command-Line Arguments#

| Argument | Description | Default | Used By |
|-----------|-------------|---------|----------|
| `live` | Run live trading | `testnet` | `continuous_trading_loop_binance.py:1933` |

**Usage:**
```bash
# Testnet (default)
python3 run_enhanced_testnet.py

# Live trading
python3 run_enhanced_testnet.py live
```

---

## 6. Safety & Risk Parameters (`safety/governance.py:88`)#

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_position_pct` | `0.1` | 10% max per trade |
| `max_portfolio_pct` | `0.3` | 30% max total portfolio |
| `max_daily_loss_pct` | `0.05` | 5% max daily loss |
| `max_daily_trades` | `50` | Max 50 trades/day |
| `max_daily_volume` | `1000000` | $1M max daily volume |
| `min_trade_interval_seconds` | `5` | 5s min between trades |

---

## 7. Learning Parameters (`config/learning.yaml`)#

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enabled` | `true` | Enable online learning |
| `adaptation_rate` | `0.008` | Learning speed |
| `min_samples` | `30` | Min samples before training |
| `update_frequency` | `1800` | Seconds between retraining (30 min) |

### 7.1 Drift Detection#

```yaml
drift_detection:
  enabled: true
  threshold: 0.03
  window_size: 80
  severity_levels:
    minor: 0.2
    moderate: 0.5
    severe: 0.8
```

---

## 8. Health Check Configuration#

### 8.1 Registered Checks (`continuous_trading_loop_binance.py:751`)#

| Component | Check Type | Lambda |
|-----------|-------------|--------|
| `executor` | `LambdaHealthCheck` | Returns `"healthy"` if True |
| `belief_state` | `LambdaHealthCheck` | Checks `confidence > 0` |
| `risk_manager` | `LambdaHealthCheck` | Returns `"healthy"` if True |

### 8.2 Health Endpoint#

| Item | Value |
|------|-------|
| **URL** | `http://localhost:8080/health` |
| **Method** | GET |
| **Response** | JSON: `{"status": "healthy", "components": {...}}` |
| **⚠️ Known Issue** | `http.server` blocks asyncio — see `SRE_RUNBOOK.md` |

---

## 9. Prometheus Metrics (`observability/metrics.py`)#

| Metric | Type | Description |
|--------|------|-------------|
| `trading_cycles_total` | Counter | Total cycles completed |
| `trading_signals_total` | Counter | Total signals generated |
| `trading_orders_total` | Counter | Total orders executed |
| `trading_pnl` | Gauge | Current P&L |
| `risk_score` | Gauge | Current risk [0, 1] |
| `risk_drawdown_percent` | Gauge | Current drawdown % |
| `open_positions` | Gauge | Number of open positions |
| `health_status` | Gauge | 0=healthy, 1=unhealthy |

**Endpoint:** `http://localhost:9090/metrics`

---

## 10. File Locations Summary#

| File | Purpose | Gitignored? | Editable? |
|------|---------|--------------|-----------|
| `.env` | API keys + Telegram | ✅ YES | ✅ YES |
| `.env.example` | Template for `.env` | ❌ NO | ✅ YES |
| `.env.testnet` | Testnet config | ❌ NO | ✅ YES |
| `.env.live` | Live trading config | ❌ NO | ✅ YES |
| `config/unified.yaml` | System + risk config | ❌ NO | ✅ YES |
| `config/trading_params.yaml` | Risk multipliers | ❌ NO | ✅ YES |
| `config/learning.yaml` | Learning parameters | ❌ NO | ✅ YES |
| `logs/trade_journal.json` | Trade records | ❌ NO | ❌ NO (auto-generated) |
| `logs/final.log` | Main log | ❌ NO | ❌ NO (auto-generated) |

---

## 11. Quick Config Validation#

```bash
# Verify .env has required keys
grep BINANCE_TESTNET_API_KEY .env | grep -v "^#"
# Expected: BINANCE_TESTNET_API_KEY=... (not empty)

# Verify YAML files are valid
python3 -c "
import yaml
for f in ['config/unified.yaml', 'config/trading_params.yaml', 'config/learning.yaml']:
    with open(f) as fp:
        data = yaml.safe_load(fp)
    print(f'{f}: ✅ Valid YAML ({len(str(data))} bytes)')
"

# Verify TradingConfig can be created
python3 -c "
from continuous_trading_loop_binance import TradingConfig, TradingMode
config = TradingConfig(mode=TradingMode.TESTNET)
print('✅ TradingConfig: PASS')
"
```

---

*Configuration Reference Version: 1.0 | Date: 2026-05-04 | System: v3.2.0*
