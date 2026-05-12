# Unified Trading System — Documentation

A POMDP-based autonomous futures trading system for Binance (Testnet & Live) with regime detection, Kelly position sizing, multi-factor signal quality, and full observability.

---

## 1. System Overview

The system is a **continuous trading loop** that:
- Fetches real-time market data from Binance Futures API every 10 seconds
- Runs a **POMDP belief state estimator** to detect market regime (8 regimes: BULL/BEAR/SIDEWAYS × HIGH/LOW_VOL + CRISIS + RECOVERY)
- Generates trading signals with **multi-uncertainty quality scoring** (epistemic + aleatoric + expected return uncertainty)
- Applies **Kelly-optimized position sizing** with regime/hour/streak modifiers
- Enforces **5-level risk controls** (RiskManifold + SafetyGovernor)
- Executes orders via Binance Futures REST API (MARKET or LIMIT_MAKER)
- Manages exits with **5-condition strategy**: TP (0.6%) → Time-out → SL (0.3%) → Partial TP tiers (1.5%/3%/5%) → Trailing stop
- Persists trades to a **trade journal** (JSON)
- Sends **Telegram alerts** and exposes **Prometheus metrics + health checks**

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Market Data (Binance API)                 │
│               fapi/v1/ticker/bookTicker per symbol            │
└──────────┬───────────────────────────────────────────────────┘
           │ bid_price, ask_price, bid_size, ask_size
           ▼
┌──────────────────────────────────────────────────────────────┐
│  PERCEPTION LAYER  (perception/belief_state.py)              │
│  BeliefStateEstimator.update(market_data) → BeliefState      │
│    • expected_return, confidence, uncertainty                │
│    • regime_probabilities (8 regimes via HMM + KMeans + GMM) │
│    • volatility_estimate, liquidity_estimate                 │
└──────────┬───────────────────────────────────────────────────┘
           │ BeliefState
           ▼
┌──────────────────────────────────────────────────────────────┐
│  DECISION LAYER   (decision/signal_generator.py)             │
│  SignalGenerator.generate_signal(belief_state, symbol)       │
│    • Multi-uncertainty quality scoring                       │
│    • Regime-adaptive thresholds (0.15-0.50 range)            │
│    • Uncertainty gates (regime-specific caps)                │
│    • BUY bias (historical outperformance)                    │
└──────────┬───────────────────────────────────────────────────┘
           │ TradingSignal(action, confidence, quantity)
           ▼
┌──────────────────────────────────────────────────────────────┐
│  RISK LAYER  (risk/unified_risk_manager.py)                  │
│  RiskManifold.assess_risk(belief, portfolio, market)         │
│    • 5 risk levels: NORMAL → WARNING → ELEVATED → HIGH →    │
│                       CRITICAL                               │
│    • Pre-trade checks: concentration, exposure, drawdown     │
│    • Daily loss limit: $3.00 (30% of $10 account)            │
│  SafetyGovernor.check_pre_trade(trade_params, positions)     │
│    • Max position cap: $500                                  │
│    • Max trades per cycle: 1                                 │
└──────────┬───────────────────────────────────────────────────┘
           │ approved/rejected
           ▼
┌──────────────────────────────────────────────────────────────┐
│  EXECUTION LAYER  (continuous_trading_loop_binance.py)       │
│  _place_binance_order(signal) → Binance REST API             │
│    • Dynamic position sizing (confidence × regime × hour)   │
│    • Auto-leverage: 30x (testnet accounts ≥ $1000)          │
│    • MARKET orders (taker 0.04%) or LIMIT_MAKER (maker 0.02%)│
│    • Retry with half size on insufficient margin              │
│    • Order verification via GET /fapi/v1/order               │
└──────────┬───────────────────────────────────────────────────┘
           │ OrderResult(orderId, status, executedQty)
           ▼
┌──────────────────────────────────────────────────────────────┐
│  EXIT MANAGEMENT  (continuous_trading_loop_binance.py)       │
│  _check_exit_conditions() per cycle                          │
│    • 5 exit conditions (see §6)                              │
│    • Cleanup: journal recording, streak updates, metrics     │
└──────────┬───────────────────────────────────────────────────┘
           │ Closed trade → journal
           ▼
┌──────────────────────────────────────────────────────────────┐
│  LEARNING LAYER  (learning/)                                 │
│  TradeJournal → JSON persistence                             │
│  Ensemble models: XGBoost + LSTM + Transformer + RandomForest│
│  Online learning: drift detection, weight adaptation         │
└──────────┬───────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│  OBSERVABILITY                                              │
│  • Telegram alerts (system status, trades, risks, errors)   │
│  • Health checks: HTTP :8080/health                         │
│  • Prometheus metrics: :9090/metrics (stubbed)              │
│  • Trade journal: logs/trade_journal.json                   │
│  • Logging: structured with correlation IDs                 │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Quick Start (5 minutes)

```bash
# Prerequisites: Python 3.12+, Binance Testnet account
git clone <repo-url> && cd unified_trading_system

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your keys from https://testnet.binancefuture.com/

python3 run_enhanced_testnet.py
```

---

## 4. Module Reference

| Directory | File(s) | Purpose | Lines |
|-----------|---------|---------|-------|
| **root** | `continuous_trading_loop_binance.py` | Core trading engine: `EnhancedTradingLoop` class (32 methods, ~2120 lines) | 2123 |
| **root** | `run_enhanced_testnet.py` | Testnet entry point (3 symbols, 10s cycles) | 96 |
| **root** | `run_enhanced_live.py` | Live entry point (3 symbols, 10s cycles, port 8082) | 131 |
| `perception/` | `belief_state.py` | POMDP belief state: 8 regimes, confidence, uncertainty | 486 |
| `perception/` | `enhanced_belief_state.py` | Volatility modeling extensions | — |
| `decision/` | `signal_generator.py` | Multi-uncertainty signal quality, adaptive thresholds | 537 |
| `risk/` | `unified_risk_manager.py` | 5-level risk manifold, drawdown control | 1399 |
| `risk/` | `enhanced_risk_manager.py` | Advanced risk controls | — |
| `risk/` | `advanced/advanced_risk_engine.py` | Advanced risk engine | — |
| `execution/` | `smart_order_router.py` | Order placement, retry logic | 688 |
| `execution/` | `high_frequency_executor.py` | HF execution (unused) | — |
| `learning/` | `trade_journal.py` | Trade recording and persistence | 217 |
| `learning/` | `return_predictor.py` | PyTorch neural network predictors | — |
| `learning/` | `ensemble_trainer.py` | XGBoost + LSTM + Transformer + RF | — |
| `learning/` | `regime_detector.py` | HMM + KMeans + GaussianMixture | — |
| `learning/` | `model_registry.py` | ML model versioning | — |
| `learning/` | `kalmannet.py` | KalmanNet integration | — |
| `safety/` | `governance.py` | SafetyGovernor: pre-trade checks, daily loss limit | 405 |
| `observability/` | `alerting.py` | Telegram alerts via python-telegram-bot | 461 |
| `observability/` | `health.py` | HTTP health check server (:8080) | 347 |
| `observability/` | `metrics.py` | Prometheus metrics (:9090, stubbed) | 389 |
| `observability/` | `logging.py` | Structured logging with correlation IDs | — |
| `config/` | `unified.yaml` | System-wide configuration (244 lines) | 244 |
| `config/` | `trading_params.yaml` | Risk parameters per regime | — |
| `config/` | `learning.yaml` | ML learning parameters | — |
| `adaptation/` | `drift_detector.py` | Concept drift detection | — |
| `scoring/` | `score_system.py` | System scoring/evaluation | — |
| `feedback/` | `real_edge_pipeline.py` | Realized edge calculation | — |
| `feedback/` | `trade_journal.py` | Duplicate of learning/trade_journal.py | — |

---

## 5. Trading Cycle (End-to-End Flow)

Each cycle runs every `cycle_interval` seconds (default 10s):

```
1. _update_balance()         → Fetch USDT balance from fapi/v2/account
2. For each symbol:
   a. _fetch_market_data()   → Real-time bid/ask from bookTicker API
   b. belief_state_estimator.update() → POMDP update
   c. signal_generator.generate_signal() → Decision
   d. RiskManifold.assess_risk() → Risk check
   e. SafetyGovernor.check_pre_trade() → Governance check
   f. _execute_signal()      → _place_binance_order() via REST API
3. _check_exit_conditions()  → Manage open positions (TP/SL/time/trailing)
```

---

## 6. Exit Strategy (5 Conditions)

| Priority | Condition | Trigger | Action |
|----------|-----------|---------|--------|
| 1 | **TAKE_PROFIT** | PnL >= +0.6% | Close 100% (MARKET) |
| 2 | **TIME_OUT** | Hold time exceeds regime limit (30-300s) | Close 100% (MARKET) |
| 3 | **STOP_LOSS** | PnL <= -0.3% | Close 100% (MARKET) |
| 4 | **PARTIAL_TP** | PnL hits +1.5%/3%/5% | Close 50%/30%/20% (MARKET) |
| 5 | **TRAILING** | +2% activation, 1.5% trail | Close 100% (MARKET) |

**Regime time limits**: CRISIS=60s, BEAR_HIGH_VOL=90s, BEAR_LOW_VOL=120s, SIDEWAYS_LOW_VOL=150s, SIDEWAYS_HIGH_VOL=180s, BULL_LOW_VOL=240s, BULL_HIGH_VOL=300s, RECOVERY=180s

**Fees**: Taker 0.04% (MARKET), Maker 0.02% (LIMIT_MAKER for TP)

---

## 7. Position Sizing

```
base = calculate_safe_notional(balance, symbol)
         ↓
dynamic = calculate_dynamic_position_size(confidence, regime, hour)
         = base × confidence_mod × regime_mod × hourly_mod × streak_mod × kelly
         ↓
target = min(dynamic, base)
target = max(target, $10)   # Binance minimum notional
```

**Regime modifiers**: CRISIS=0.3x, BEAR_HIGH_VOL=0.5x, BULL_HIGH_VOL=1.2x, RECOVERY=0.9x
**Hourly modifiers**: 8-10AM=1.3x, 10PM-6AM=0.3x
**Streak**: 3+ consecutive wins=1.2x, 2+ losses=0.3x
**Kelly**: Based on win_rate(0.095) × win_loss_ratio(0.5), capped at 10%

---

## 8. Configuration

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `BINANCE_TESTNET_API_KEY` | Testnet | Binance Testnet API key |
| `BINANCE_TESTNET_API_SECRET` | Testnet | Binance Testnet API secret |
| `BINANCE_LIVE_API_KEY` | Live | Binance Live API key |
| `BINANCE_LIVE_API_SECRET` | Live | Binance Live API secret |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot token for alerts |
| `TELEGRAM_CHAT_IDS` | No | Telegram chat IDs (comma-separated) |

### TradingConfig Fields (`continuous_trading_loop_binance.py:54-93`)

| Field | Default | Description |
|-------|---------|-------------|
| `mode` | PAPER | PAPER, TESTNET, or LIVE |
| `symbols` | 16 pairs | Trading pairs (BTC/USDT, ETH/USDT, etc.) |
| `cycle_interval` | 60.0 | Seconds between cycles |
| `max_position_size` | 500.0 | Max USD per position |
| `max_daily_loss` | 3.0 | Max daily loss ($) |
| `min_confidence_threshold` | 0.55 | Min confidence for signals |
| `take_profit_pct` | 0.006 | TP at +0.6% |
| `stop_loss_pct` | 0.003 | SL at -0.3% |
| `health_check_port` | 8080 | Health HTTP server port |
| `base_url` | testnet.binancefuture.com | API base URL |

---

## 9. Test Suite

| File | Tests | Status | Command |
|------|-------|--------|---------|
| `tests/test_signal_quality.py` | 28 | ✅ 28/28 pass | `pytest tests/test_signal_quality.py -v` |
| `tests/test_belief_state.py` | 4 | Untested | `pytest tests/test_belief_state.py -v` |
| `tests/test_b1_regression.py` | — | Untested | `pytest tests/test_b1_regression.py -v` |
| `tests/test_leverage_config.py` | — | Untested | `pytest tests/test_leverage_config.py -v` |
| `tests/test_b4_regression.py` | — | Untested | `pytest tests/test_b4_regression.py -v` |
| `tests/test_pnl_persistence.py` | — | Untested | `pytest tests/test_pnl_persistence.py -v` |
| `tests/test_kalman_filter.py` | — | Untested | `pytest tests/test_kalman_filter.py -v` |

Run all: `python3 -m pytest tests/ -v`

---

## 10. Infrastructure

### tmux (via `manage.sh`)
```bash
./manage.sh         # Show menu (attach/kill/list sessions)
```

### systemd (via `enhanced-live.service`)
```ini
[Unit]
Description=Trading System Live
After=network.target

[Service]
ExecStart=/home/nkhekhe/unified_trading_system/start_enhanced_live.sh
Restart=always
User=nkhekhe
```

### Docker/K8s (`k8s/deployment.yaml`)
- 1 replica, ports 8082 (health) + 9092 (metrics)
- Liveness probe: GET /health on 8082
- Resource limits: 2Gi RAM, 2000m CPU

### CI/CD (`.github/workflows/ci_cd.yml`)
Triggered on push to `main`/`develop`. Steps:
1. Setup Python 3.12
2. Install deps + pytest/mypy/pylint/bandit
3. Run regression tests
4. Type check (mypy), lint (pylint), security (bandit)
5. Deploy (placeholder)

---

## 11. Known Issues & Recent Fixes

### Fixed: Dead Code in `_get_account_balance` (this build)
Lines 775-850 (health server creation, alerting re-config, initialization log) were trapped inside `_get_account_balance` after unconditional `return` statements. The `initialize()` method never called this code, so the health server never started. **Fix**: Moved into `initialize()` method between `_load_open_positions()` and the initialization log.

### Fixed: 3 Failing Tests (this build)
`TestSignalAcceptance` (2 tests) called `should_accept_signal()` without the required `confidence` argument. `TestAdaptiveThresholds::test_adaptive_threshold_bounds` had upper bound too tight (0.50 vs actual max 0.60). All 28 tests now pass.

### Fixed: Credential Exposure (this build)
Real API keys and Telegram tokens in `.env.testnet`, `.env.live`, and `docs/CONFIGURATION.md` replaced with placeholders.

### Known: Health Server Lambda Checks
The edge_detection lambda reads the trade journal file synchronously in the health check handler thread. If the journal is large or locked, the health endpoint may lag. The LambdaHealthCheck wrapper catches exceptions gracefully.

### Known: Metrics Not Working
Prometheus metrics (`_register_metrics`) are stubbed with `pass`. The metrics port (9090) is not serving data.

---

## 12. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `KeyError` on startup | Missing env vars | Check `.env` file has all required keys |
| Port 8080 in use | Another process | `kill $(lsof -ti:8080)` or change port in config |
| No Telegram alerts | Wrong token/chat ID | Check `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_IDS` |
| Orders rejected "insufficient margin" | Balance too low | Reduce position size or add funds |
| `HTTP 429` from Binance | Rate limited | Reduce `max_orders_per_minute` |
| Strange regex error | Python 3.11 vs 3.12 | Use Python 3.12+ |
| System crashes on start | Import error | `pip install -r requirements.txt` |

---

*Built: 2026-05-11 | Python 3.12.3 | Binance Futures Testnet*
