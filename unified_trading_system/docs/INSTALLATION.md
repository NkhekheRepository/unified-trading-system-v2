# Installation Guide

Complete step-by-step installation guide to set up the Unified Trading System on a fresh server from zero to running.

---

## Prerequisites Checklist

| Item | Requirement | Verify Command |
|------|--------------|---------------|
| **OS** | Ubuntu 22.04+ / Debian 12+ | `cat /etc/os-release` |
| **Kernel** | ≥5.4 | `uname -r` |
| **Python** | 3.12+ (3.12.3 recommended) | `python3.12 --version` |
| **RAM** | ≥2 GB | `free -h` |
| **Disk** | ≥10 GB free | `df -h /` |
| **Network** | Stable internet (Binance API) | `curl -s https://testnet.binancefuture.com` |
| **sudo access** | Required for OS packages | `sudo whoami` (should return `root`) |

---

## Step 1: OS Packages

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
    git \
    python3.12 \
    python3.12-venv \
    python3-pip \
    tmux \
    curl \
    build-essential \
    libssl-dev \
    libffi-dev \
    ca-certificates
```

**Verify:**
```bash
python3.12 --version
# Expected: Python 3.12.x

tmux -V
# Expected: tmux x.x (version)
```

---

## Step 2: Clone Repository

```bash
# Replace <repository-url> with your actual Git repository URL
git clone <repository-url> unified_trading_system
cd unified_trading_system
```

**Verify:**
```bash
ls run_enhanced_testnet.py
# Expected: run_enhanced_testnet.py (file exists)
```

---

## Step 3: Create Virtual Environment

```bash
# Create virtual environment
python3.12 -m venv .venv

# Activate it (DO THIS IN EVERY NEW TERMINAL)
source .venv/bin/activate

# Verify activation
which python
# Expected: /home/user/unified_trading_system/.venv/bin/python
```

**⚠️ Important:** Always run `source .venv/bin/activate` before running any Python commands.

---

## Step 4: Install ALL Dependencies (14 Packages)

The `requirements.txt` now contains **14 packages** (upgraded from 5):

```bash
# Upgrade pip first
pip install --upgrade pip

# Install all dependencies with pinned versions
pip install -r requirements.txt
```

**Verify all 14 packages:**
```bash
python3 -c "
import aiohttp, numpy, pandas, yaml, dotenv
import prometheus_client, psutil
import torch, xgboost, sklearn, scipy
import websockets, requests
print('✅ All 14 core packages installed')
"

# Check versions match installed
pip list | grep -E "aiohttp|numpy|pandas|PyYAML|python-dotenv|prometheus|psutil|torch|xgboost|scikit|scipy|websockets|requests"
```

**Expected output includes:**
```
aiohttp             3.13.5
numpy                2.4.4
pandas               3.0.2
PyYAML              6.0.1
python-dotenv       1.2.2
prometheus_client    0.25.0
psutil               5.9.0+
torch                2.11.0+cpu
xgboost              3.2.0
scikit-learn         1.5.0+
scipy                1.17.1
websockets           10.4.0
requests             2.31.0
```

---

## Step 5: Configure Environment Variables

### 5.1 Get Binance Testnet API Keys:

1. Go to: https://testnet.binancefuture.com/
2. Log in or create account
3. Navigate to **API Management** → **Create API Key**
4. Copy the **API Key** and **Secret Key** immediately (secret shown only once!)

### 5.2 Create `.env` file:

```bash
cp .env.example .env
nano .env
```

**Fill in your keys:**
```bash
BINANCE_TESTNET_API_KEY=your_api_key_here
BINANCE_TESTNET_API_SECRET=your_api_secret_here
BINANCE_TESTNET=true
TESTNET_BASE_URL=https://testnet.binancefuture.com
```

### 5.3 (Optional) Configure Telegram Alerts:

1. Message `@BotFather` on Telegram
2. Send `/newbot` → follow prompts → copy the **Bot Token**
3. Message your new bot → visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Find `"chat":{"id":` → copy the number (**Chat ID**)

Add to `.env`:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_IDS=your_chat_id_here
```

**Verify `.env`:**
```bash
grep BINANCE_TESTNET_API_KEY .env
# Expected: BINANCE_TESTNET_API_KEY=your_... (not empty)

grep TELEGRAM_BOT_TOKEN .env  # If using Telegram
# Expected: TELEGRAM_BOT_TOKEN=your_... (not empty)
```

---

## Step 6: Verify All Imports

```bash
python3 -c "
import sys
sys.path.insert(0, '.')
from continuous_trading_loop_binance import TradingConfig, TradingMode, EnhancedTradingLoop
from observability.alerting import send_system_status_alert, configure_alerting_from_env
from observability.health import HealthServer, HealthStatus, LambdaHealthCheck
from perception.belief_state import BeliefState, BeliefStateEstimator, RegimeType
from risk.unified_risk_manager import RiskManifold
from execution.smart_order_router import ExecutionModel, ExecutionIntent, OrderType
from decision.signal_generator import SignalGenerator, TradingSignal
from learning.trade_journal import TradeJournal
from safety.governance import SafetyGovernor
from config.config_manager import ConfigManager, ConfigValidationError
print('✅ ALL 11 CORE MODULE IMPORTS: PASS')
"
```

**Expected output:** `✅ ALL 11 CORE MODULE IMPORTS: PASS`

---

## Step 7: Run the System

### Option A: Direct (Development)

```bash
# Make sure venv is active
source .venv/bin/activate

# Run
python3 run_enhanced_testnet.py
```

### Option B: tmux (Recommended for Persistence)

```bash
# Make manage.sh executable
chmod +x manage.sh

# Start in tmux session
./manage.sh start

# Attach to session to view output
tmux attach -t trading

# Detach: Press Ctrl+B, then press D
```

**Verify it's running:**
```bash
ps aux | grep run_enhanced_testnet | grep -v grep
# Expected: Shows PID and process info

tail -5 logs/final.log
# Expected: "Starting cycle_NNNN" messages every ~10s
```

---

## Step 8: Check Telegram Startup Alert

If you configured Telegram, you should receive:
```
🔔 TEST: System Restart
Trading system started - testing Telegram alerts
```

If not received:
```bash
# Verify Telegram config
grep TELEGRAM .env

# Test alerting
python3 -c "
import sys; sys.path.insert(0, '.')
from observability.alerting import configure_alerting_from_env, send_system_status_alert
configure_alerting_from_env()
import asyncio
asyncio.run(send_system_status_alert('test', 'started', {'msg': 'Test'}))
"
```

---

## Step 9: Verify Trading Activity

```bash
tail -20 logs/final.log
```

**Expected output includes:**
```
✅ Using crossWalletBalance: $XXXX.XX, leverage: 20.0x
Starting cycle_NNN...
Completed cycle_NNN: X signals, Y orders
```

---

## Common Installation Issues

| Issue | Cause | Fix |
|-------|------|-----|
| `python3.12: command not found` | Python 3.12 not installed | `sudo apt install python3.12` |
| `No module named 'aiohttp'` | `requirements.txt` not installed | `pip install -r requirements.txt` |
| `401 Unauthorized` | Wrong API key/secret | Re-check keys from testnet.binancefuture.com |
| `Permission denied` | Script not executable | `chmod +x manage.sh` |
| `ModuleNotFoundError` | venv not activated | `source .venv/bin/activate` |
| `TELEGRAM_BOT_TOKEN not found` | Using old code | Ensure hardcoded secrets removed (Tier 1 fix) |

---

## Quick Verification Checklist

After installation, run these commands in order:

```bash
# 1. OS
python3.12 --version  # → 3.12.x

# 2. Repository
ls run_enhanced_testnet.py  # → file exists

# 3. Virtual env
which python  # → .../.venv/bin/python

# 4. Dependencies
python3 -c "import aiohttp, numpy, pandas; print('✅')"  # → ✅

# 5. Environment
grep BINANCE_TESTNET_API_KEY .env  # → not empty

# 6. Imports
python3 -c "from continuous_trading_loop_binance import EnhancedTradingLoop; print('✅')"  # → ✅

# 7. Run
./manage.sh start  # → starts in tmux

# 8. Verify
ps aux | grep run_enhanced_testnet | grep -v grep  # → shows PID

# 9. Check logs
tail -5 logs/final.log  # → "Completed cycle_NNN"
```

All 9 checks should pass ✅

---

## Directory Structure After Installation

```
unified_trading_system/
├── .venv/                          # Virtual environment (gitignored)
├── run_enhanced_testnet.py          # Entry point
├── continuous_trading_loop_binance.py  # Core engine
├── requirements.txt                  # 14 dependencies
├── .env                            # Your API keys (gitignored)
├── .env.example                     # Template (committed)
├── config/
│   ├── unified.yaml                # System config (244 lines)
│   ├── trading_params.yaml          # Risk multipliers
│   └── learning.yaml                # Learning parameters
├── logs/                           # Created on first run
│   ├── final.log                   # Main log
│   └── trade_journal.json           # Trade records
├── docs/                            # Documentation (15 documents)
└── manage.sh                       # tmux manager
```

---

*Installation Guide Version: 1.0 | Date: 2026-05-04 | System: v3.2.0*
