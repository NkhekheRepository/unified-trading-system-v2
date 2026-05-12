# Unified Autonomous Trading System – Technical Documentation

*(Version 2.0 – Phase 1 Exit Optimization)*

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [System Architecture](#2-system-architecture)
3. [Infrastructure & OS Setup](#3-infrastructure--os-setup)
4. [Installation](#4-installation)
5. [Configuration](#5-configuration)
6. [Running the System](#6-running-the-system)
7. [How It Works](#7-how-it-works)
8. [Testing & Validation](#8-testing--validation)
9. [Risk Management & Exit Logic](#9-risk-management--exit-logic)
10. [Performance Metrics](#10-performance-metrics)
11. [Backup & Rollback](#11-backup--rollback)
12. [FAQ](#12-faq)

---

## 1. System Overview

| Attribute | Value |
|-----------|-------|
| **Project Name** | Unified Autonomous Trading System (UATS) |
| **Exchange** | Binance Futures Testnet |
| **Trading Pairs** | 12 (BTC, ETH, BNB, SOL, ADA, XRP, DOGE, DOT, AVAX, LINK, LTC, BCH) |
| **Language** | Python 3.12+ |
| **Architecture** | Async/Await Event Loop |
| **Control Theory** | Stochastic Optimal Control (POMDP) |
| **Position Sizing** | Risk-Coupled Kelly Criterion |
| **Current WR** | ~35% (post Phase 1 fix) |
| **Target WR** | ≥65% |

---

## 2. System Architecture

### 2.1 Component Flow

```
MARKET DATA (Binance) 
       ↓
PERCEPTION LAYER (BeliefState)
       ↓
REGIME DETECTOR (HMM)
       ↓
RISK MANIFOLD
       ↓
AGGRESSION CONTROLLER (POMDP)
       ↓
RISK GOVERNOR (CVaR, Max Drawdown)
       ↓
POSITION SIZER (Kelly)
       ↓
SIGNAL GENERATOR (Confidence Filter)
       ↓
EXECUTION (Smart Order Router)
       ↓
TRADE JOURNAL (Learning)
       ↓
DRIFT DETECTOR (Adaptation)
```

### 2.2 Key Modules

| Module | File | Purpose |
|--------|------|---------|
| Entry Point | `run_enhanced_testnet.py` | Loads config, starts loop |
| Core Loop | `continuous_trading_loop_binance.py` | 1,857 lines – order management, exit logic |
| Signal Gen | `decision/signal_generator.py` | Confidence filtering (0.85 threshold) |
| Risk Manager | `risk/unified_risk_manager.py` | Position sizing, drawdown |
| Belief State | `perception/belief_state.py` | Market state estimation |
| Execution | `execution/smart_order_router.py` | Order placement |
| Observability | `observability/*.py` | Logging, alerts, health |
| Trade Journal | `learning/trade_journal.py` | Persistent trade record |

---

## 3. Infrastructure & OS Setup

### 3.1 OS Requirements

| Item | Specification |
|------|-------------|
| OS | Ubuntu 22.04 LTS / Debian 12 (or any modern Linux) |
| Kernel | ≥5.4 |
| Python | 3.12+ (tested on 3.12) |
| RAM | ≥2 GB recommended |
| Disk | ≥10 GB |
| Network | Stable internet (for Binance API) |

### 3.2 System Packages

```bash
sudo apt update && sudo apt install -y git python3-pip python3-venv tmux
```

### 3.3 Python Packages

```bash
pip install aiohttp numpy pandas yaml python-dotenv
```

---

## 4. Installation

### 4.1 Clone Repository

```bash
git clone https://github.com/your-org/unified-trading-system.git
cd unified-trading-system
```

### 4.2 Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install aiohttp numpy pandas yaml python-dotenv
```

### 4.3 Configure API Keys

```bash
cp .env.example .env
nano .env
# Fill in your Binance Testnet API Key and Secret
```

---

## 5. Configuration

### 5.1 `.env` File

| Variable | Description |
|----------|-------------|
| `BINANCE_API_KEY` | Testnet API key |
| `BINANCE_API_SECRET` | Testnet secret |
| `BINANCE_TESTNET_URL` | `https://testnet.binancefuture.com` |
| `LOG_LEVEL` | `INFO` (or `DEBUG`) |

### 5.2 TradingConfig (in `continuous_trading_loop_binance.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_confidence_threshold` | 0.85 | Signal confidence cutoff |
| `take_profit_pct` | 0.003 | +0.3% take profit |
| `stop_loss_pct` | 0.005 | -0.5% stop loss |
| `max_trades_per_cycle` | 1 | One trade per cycle |
| `cycle_interval` | 10.0 | Seconds between cycles |
| `regime_direction_filter` | True | Block SELL in RECOVERY regime |
| `max_position_size` | 0.1 | 10% of capital max |

---

## 6. Running the System

### 6.1 Development Mode

```bash
source .venv/bin/activate
python run_enhanced_testnet.py
```

### 6.2 Production (tmux)

```bash
chmod +x manage.sh
./manage.sh start
```

### 6.3 View Logs

```bash
tail -f logs/trading_loop.log
```

### 6.4 Stop System

```bash
./manage.sh stop
```

### 6.5 Health Check

```bash
python check_health.py
```

---

## 7. How It Works

### 7.1 Market Data Flow

1. **Perception** – Fetches live prices, volumes, order book from Binance
2. **Belief State** – Calculates expected return, uncertainty, momentum
3. **Regime Detection** – Classifies market as BULL/BEAR/SIDEWAYS
4. **Risk Manifold** – Computes risk pressure vector
5. **Aggression Controller** – Updates POMDP state
6. **Risk Governor** – Enforces CVaR and max drawdown
7. **Signal Generator** – Generates BUY/SELL with confidence filter
8. **Execution** – Places orders via Binance API
9. **Journal** – Records trade outcomes

### 7.2 Exit Logic (Critical)

The system evaluates exits in this priority order:

```
1. TAKE-PROFIT (+0.3%)    ← PRIORITY 1 (most important)
2. TIME-OUT (regime-based)  ← PRIORITY 2 
3. STOP-LOSS (-0.3%)       ← PRIORITY 3
4. TRAILING STOP           ← PRIORITY 4
```

**Phase 1 Fix:** Previously, TIME-OUT fired before +0.3% TP could execute, causing 25% win-rate. After reordering priorities, win-rate improved to ~35%.

### 7.3 Position Sizing

Kelly Criterion: `size = fractional_kelly * (WR * R - (1-WR)) / R`

Where:
- `WR` = historical win rate
- `R` = average win / average loss

---

## 8. Testing & Validation

### 8.1 Unit Tests

```bash
pytest -v
```

### 8.2 Integration Test

```bash
python test_integration.py
```

### 8.3 Health Check

```bash
python check_health.py
```

### 8.4 Performance Validation

```bash
python compute_performance.py
```

---

## 9. Risk Management & Exit Logic

### 9.1 Risk Governor Rules

| Rule | Threshold |
|------|----------|
| CVaR | ≤5% |
| Max Drawdown | ≤15% |
| Max Daily Loss | $10,000 |
| Max Orders/Min | 20 |

### 9.2 Exit Parameters

| Exit Type | Trigger | Priority |
|----------|---------|---------|
| Take-Profit | +0.3% P&L | 1 |
| Time-Out | 300s (adjusted by regime) | 2 |
| Stop-Loss | -0.3% P&L | 3 |
| Trailing Stop | +2% → -0.5% drop | 4 |

### 9.3 Expected Value Calculation

Pre-fix: `-0.003` (negative)
Post-fix: `+0.0009` (positive)

---

## 10. Performance Metrics

### 10.1 Current (Phase 1)

| Metric | Value |
|--------|-------|
| Total Trades | 2,348 |
| Win Rate | ~25% overall, ~35% post-fix |
| TP Hits | 60%+ of wins |
| Unrealized P&L | ≈+$1,011 |
| Expected Value | +0.0009/trade |

### 10.2 Targets

| Metric | Target |
|--------|--------|
| Win Rate | ≥65% |
| Sharpe Ratio | ≥1.5 |
| Max Drawdown | <15% |
| CVaR (95%) | <5% |

---

## 11. Backup & Rollback

### 11.1 Git Workflow

```bash
# Commit changes
git add .
git commit -m "Phase 1 exit priority fix"

# Tag release
git tag -a v1.0-phase1-fix -m "Take-profit priority fix"

# Rollback
git reset --hard v1.0-phase1-fix
```

### 11.2 Trade Journal Backup

```bash
cp logs/trade_journal.json logs/trade_journal_$(date +%Y%m%d).json
```

---

## 12. FAQ

| Q | A |
|---|---|
| **Do I need real money?** | No – this runs on Binance Testnet with fake money. |
| **Can I use live exchange?** | Yes – change `BINANCE_TESTNET_URL` to production endpoint. Never use real money until backtesting is complete. |
| **What if system crashes?** | The `watchdog.py` script auto-restarts. Check `system.pid`. |
| **How do I adjust confidence?** | Edit `min_confidence_threshold` in `TradingConfig`. |
| **How do I change symbols?** | Update `symbols` list in `TradingConfig`. |
| **Where are logs?** | `logs/trading_loop.log`, `logs/trade_journal.json`. |
| **What is the win-rate target?** | 65%+ (currently ~35% post-fix). |
| **Can I run without tmux?** | Yes – just `python run_enhanced_testnet.py` in a terminal. |
| **How often does it trade?** | Every `cycle_interval` seconds (default 10s), up to `max_trades_per_cycle`. |
| **Is it legal to use?** | This is for educational/demo purposes. Check your local regulations. |

---

## Appendix: File Reference

| File | Lines | Purpose |
|------|-------|---------|
| `run_enhanced_testnet.py` | 103 | Entry point |
| `continuous_trading_loop_binance.py` | 1,857 | Core loop, exit logic |
| `decision/signal_generator.py` | 494 | Signal generation |
| `risk/unified_risk_manager.py` | ~500 | Risk controls |
| `perception/belief_state.py` | ~300 | Market estimation |
| `execution/smart_order_router.py` | ~400 | Order execution |
| `learning/trade_journal.py` | ~200 | Trade recording |
| `manage.sh` | 41 | tmux manager |
| `watchdog.py` | ~100 | Auto-restart |

---

*Last Updated: 2026-04-29*
*Version: 2.0 Phase 1*