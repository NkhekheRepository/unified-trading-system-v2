# Portability Checklist — Bring System to Current Configuration

Complete step-by-step checklist to **replicate the current running system** on a fresh server.  
Follow these 12 steps in order. Each step has a **verification command** — run it before proceeding.

---

## PREREQUISITES

- [ ] A fresh Ubuntu 22.04+ / Debian 12+ server
- [ ] `sudo` access
- [ ] Your **Binance Testnet API Key + Secret** (from https://testnet.binancefuture.com/)
- [ ] (Optional) Telegram bot token from `@BotFather` + your Chat ID

---

## STEP 1: OS Setup

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
    libffi-dev
```

**Verify:**
```bash
python3.12 --version
# Expected: Python 3.12.x
```

---

## STEP 2: Clone Repository

```bash
git clone <your-repository-url> unified_trading_system
cd unified_trading_system
```

**Verify:**
```bash
ls run_enhanced_testnet.py
# Expected: run_enhanced_testnet.py
```

---

## STEP 3: Create Virtual Environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

**Verify:**
```bash
which python
# Expected: /home/user/unified_trading_system/.venv/bin/python
```

---

## STEP 4: Install ALL Dependencies

The `requirements.txt` now contains **14 packages** (previously only 5):

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Verify all 14 packages:**
```bash
python3 -c "
import aiohttp, numpy, pandas, yaml, dotenv
import prometheus_client, psutil
import torch, xgboost, sklearn, scipy
import websockets, requests
print('✅ All 14 packages installed')
"
```

---

## STEP 5: Configure Binance Testnet API Keys

### 5a. Get your API keys:
1. Go to https://testnet.binancefuture.com/
2. Log in / create account
3. Navigate to **API Management** → **Create API Key**
4. Copy the **API Key** and **Secret Key**

### 5b. Create `.env` file:
```bash
cp .env.example .env
nano .env
```

Fill in:
```bash
BINANCE_TESTNET_API_KEY=your_api_key_here
BINANCE_TESTNET_API_SECRET=your_api_secret_here
BINANCE_TESTNET=true
TESTNET_BASE_URL=https://testnet.binancefuture.com
```

**Verify:**
```bash
grep BINANCE_TESTNET_API_KEY .env
# Expected: BINANCE_TESTNET_API_KEY=your_a... (not empty)
```

---

## STEP 6: (Optional) Configure Telegram Alerts

### 6a. Create a Telegram bot:
1. Message `@BotFather` on Telegram
2. Send `/newbot` → follow prompts → copy the **Bot Token**

### 6b. Get your Chat ID:
1. Message your new bot
2. Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Find `"chat":{"id":` → copy the number

### 6c. Add to `.env`:
```bash
nano .env
# Add these lines:
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_IDS=your_chat_id_here
```

**Verify:**
```bash
grep TELEGRAM_BOT_TOKEN .env
# Expected: TELEGRAM_BOT_TOKEN=...
```

---

## STEP 7: Verify All Imports

```bash
python3 -c "
import sys
sys.path.insert(0, '.')
from continuous_trading_loop_binance import TradingConfig, TradingMode, EnhancedTradingLoop
from observability.alerting import send_system_status_alert, configure_alerting_from_env
from perception.belief_state import BeliefState, BeliefStateEstimator, RegimeType
from risk.unified_risk_manager import RiskManifold
from decision.signal_generator import SignalGenerator, TradingSignal
from execution.smart_order_router import ExecutionModel, ExecutionIntent, OrderType
from learning.trade_journal import TradeJournal
from safety.governance import SafetyGovernor
from config.config_manager import ConfigManager
print('✅ All 11 core module imports: PASS')
"
```

**Expected output:** `✅ All 11 core module imports: PASS`

---

## STEP 8: Run the System

### Option A: Direct (Development)
```bash
python3 run_enhanced_testnet.py
```

### Option B: tmux (Recommended for Persistence)
```bash
chmod +x manage.sh
./manage.sh start
# View: tmux attach -t trading
# Detach: Ctrl+B then D
```

**Verify it's running:**
```bash
ps aux | grep run_enhanced_testnet.py | grep -v grep
# Expected: Shows the Python process with PID
```

---

## STEP 9: Check Telegram Startup Alert

You should receive a Telegram message:
```
🔔 TEST: System Restart
Trading system started - testing Telegram alerts
```

If you don't receive it, check:
```bash
grep TELEGRAM_BOT_TOKEN .env
grep TELEGRAM_CHAT_IDS .env
python3 -c "from observability.alerting import configure_alerting_from_env; configure_alerting_from_env()"
```

---

## STEP 10: Verify Trading Activity

```bash
tail -20 logs/final.log
```

**Expected output includes:**
```
✅ Using crossWalletBalance: $XXXX.XX, leverage: 20.0x
Starting cycle_XXXXX...
Completed cycle_XXXXX: X signals, Y orders
```

---

## STEP 11: (Optional) Check Health & Metrics

### Health Check (after fix in Tier 1):
```bash
curl http://localhost:8080/health
```

### Prometheus Metrics:
```bash
curl http://localhost:9090/metrics
```

---

## STEP 12: Save Your Configuration

```bash
# Document your setup
cat > SETUP_INFO.md << 'EOF'
# My Trading System Setup

- Server: <your-server-details>
- OS: Ubuntu 22.04
- Python: 3.12.3
- Binance Testnet: CONFIGURED
- Telegram Alerts: CONFIGURED/NOT CONFIGURED
- Started: $(date)
- PID: $(ps aux | grep run_enhanced_testnet.py | grep -v grep | awk '{print $2}')
EOF

cat SETUP_INFO.md
```

---

## ROLLBACK / RESTART CHECKLIST

If the system stops:

```bash
# Check status
./manage.sh status

# Restart
./manage.sh restart

# Or manually:
ps aux | grep run_enhanced_testnet.py | grep -v grep | awk '{print $2}' | xargs kill
python3 run_enhanced_testnet.py &

# View logs
tail -f logs/final.log
```

---

## CONFIGURATION FILES SUMMARY

| File | Purpose | Gitignored? | Action |
|------|---------|--------------|--------|
| `.env` | API keys + Telegram | ✅ YES | Create from `.env.example` with YOUR keys |
| `config/unified.yaml` | System + risk config | ❌ NO | Already configured (v3.2.0) — review if needed |
| `config/trading_params.yaml` | Risk multipliers | ❌ NO | Already configured — no changes needed |
| `config/learning.yaml` | Learning parameters | ❌ NO | Already configured |

---

## PORTABILITY VERIFICATION

After completing all 12 steps, verify:

| Check | Command | Expected |
|-------|---------|----------|
| Process running | `ps aux \| grep run_enhanced` | Shows PID |
| Cycles executing | `tail logs/final.log \| grep Completed` | Shows cycle_NNNNN |
| Balance available | `grep crossWallet logs/final.log \| tail -1` | Shows $XXXX.XX |
| Telegram alert | Check Telegram app | "System Restart" message |
| Imports work | Step 7 command | "PASS" |
| Dependencies | `pip list \| wc -l` | 14+ packages |

---

## COMMON MIGRATION ISSUES

| Issue | Cause | Fix |
|-------|------|-----|
| `No module named 'aiohttp'` | `requirements.txt` not installed | `pip install -r requirements.txt` |
| `401 Unauthorized` | Wrong API key/secret | Re-check keys from testnet.binancefuture.com |
| `No available margin` | All margin tied up | Wait for positions to close; check `logs/trade_journal.json` |
| No Telegram alert | Wrong bot token/chat ID | Verify with `@BotFather` and `getUpdates` |
| Health endpoint not responding | Known issue — `http.server` blocks asyncio | Apply Tier 1 fix (use `aiohttp.web`) |

---

*Portability checklist version: 1.0 | Date: 2026-05-04 | System: v3.2.0*
