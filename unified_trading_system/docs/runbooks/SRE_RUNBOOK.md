# SRE Runbook

Site Reliability Engineering runbook for the Unified Trading System. Scenarios, incident response, and operational procedures.

---

## 1. System Overview

| Attribute | Value |
|-----------|-------|
| **Process Name** | `python3 run_enhanced_testnet.py` |
| **tmux Session** | `trading` |
| **PID** | Check: `ps aux \| grep run_enhanced_testnet \| grep -v grep` |
| **Health Endpoint** | `http://localhost:8080/health` (⚠️ KNOWN ISSUE — not responding) |
| **Metrics Endpoint** | `http://localhost:9090/metrics` |
| **Log Location** | `logs/final.log` (main), `logs/trade_journal.json` |
| **Config Files** | `.env`, `config/unified.yaml`, `config/trading_params.yaml` |
| **Python Version** | 3.12.3 |
| **Virtual Env** | `.venv/` (activate: `source .venv/bin/activate`) |

---

## 2. Health Check Procedures

### 2.1 Check if System is Running

```bash
# Method 1: Process check
ps aux | grep "run_enhanced_testnet" | grep -v grep
# Expected: Shows PID, e.g., nkhekhe 1031751 ... python3 run_enhanced_testnet.py

# Method 2: tmux session check
tmux ls
# Expected: trading: 1 window (attached)

# Method 3: Log activity
tail -5 logs/final.log
# Expected: "Completed cycle_NNNNN" messages every ~10s
```

### 2.2 Health Endpoint (After Fix)

```bash
# Check health (after Tier 1 #4 fix — switch to aiohttp.web)
curl -s http://localhost:8080/health | python3 -m json.tool
```

**Expected Response:**
```json
{
  "status": "healthy",
  "components": {
    "executor": {"status": "healthy", "message": "Executor is operational"},
    "belief_state": {"status": "healthy", "confidence": 0.89},
    "risk_manager": {"status": "healthy", "message": "Risk manager is operational"}
  }
}
```

### 2.3 Prometheus Metrics

```bash
curl -s http://localhost:9090/metrics | grep -E "trading_|risk_|health_"
```

**Key Metrics:**

| Metric | Description |
|--------|-------------|
| `trading_cycles_total` | Total cycles completed |
| `trading_signals_total` | Total signals generated |
| `trading_orders_total` | Total orders executed |
| `trading_pnl` | Current P&L |
| `risk_score` | Current risk score [0, 1] |
| `risk_drawdown_percent` | Current drawdown % |
| `health_status` | 0=healthy, 1=unhealthy |

---

## 3. Incident Response Scenarios

### 3.1 PROCESS CRASHED

**Detection:**
```bash
ps aux | grep run_enhanced_testnet | grep -v grep
# Returns nothing
```

**Resolution (3 options):**

| Method | Command | Use Case |
|--------|---------|----------|
| **tmux restart** | `./manage.sh restart` | Preferred — preserves session |
| **tmux start** | `./manage.sh start` | If restart fails |
| **Auto-restart loop** | Built-in: 1000 retries, 5s delay | `continuous_trading_loop_binance.py:1926` |

**Verify Recovery:**
```bash
tail -20 logs/final.log | grep -E "Starting|initialized|started"
```

---

### 3.2 HEALTH ENDPOINT NOT RESPONDING

**Detection:**
```bash
curl -s --connect-timeout 2 http://localhost:8080/health
# Returns: curl: (7) Failed to connect to localhost port 8080
```

**Root Cause:** `observability/health.py:256` uses `http.server.HTTPServer` which **blocks the asyncio event loop**.

**Resolution (Tier 1 #4 — Apply Fix):**

```python
# In observability/health.py, replace:
from http.server import HTTPServer, BaseHTTPRequestHandler
# With:
from aiohttp import web, run_app

class HealthServer:
    async def start(self):
        app = web.Application()
        app.router.add_get('/health', self._health_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()  # ✅ Non-blocking
```

**Verify Fix:**
```bash
curl http://localhost:8080/health
# Expected: JSON response with "status": "healthy"
```

---

### 3.3 ALL SYMBOLS SKIP — "NO AVAILABLE MARGIN"

**Detection:**
```bash
tail -50 logs/final.log | grep "No available margin"
# Shows: "⚠️ No available margin — waiting for positions to close"
```

**Root Cause:** All margin is tied up in open positions. `current_balance` > 0 but `available_balance` = 0.

**Resolution:**

```bash
# 1. Check open positions via Binance API (or logs)
cat logs/trade_journal.json | python3 -m json.tool | grep -A5 '"status": "OPEN"'

# 2. Manually close positions via Binance Testnet UI:
# https://testnet.binancefuture.com/en/futures/BTCUSDT

# 3. Or wait — system checks exit conditions every 10s:
# TP @ +0.3%, Time (regime-based), SL @ -0.3%, Trailing @ +2%
```

**Verify Recovery:**
```bash
tail -5 logs/final.log | grep "Using crossWalletBalance"
# Expected: "✅ Using crossWalletBalance: $XXXX.XX, leverage: 20.0x"
```

---

### 3.4 TELEGRAM ALERTS NOT RECEIVED

**Detection:**
- No startup alert in Telegram chat
- No trade execution alerts

**Root Cause:** Wrong `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_IDS` in `.env`.

**Resolution:**

```bash
# 1. Verify .env has correct values
grep TELEGRAM .env
# Expected:
# TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
# TELEGRAM_CHAT_IDS=your_telegram_chat_id_here

# 2. Verify bot is active
# Message @BotFather → /mybots → Check bot status

# 3. Get correct Chat ID
# Message your bot, then visit:
# https://api.telegram.org/bot<TOKEN>/getUpdates
# Find: "chat":{"id": <YOUR_CHAT_ID>}

# 4. Reconfigure alerting
python3 -c "
from observability.alerting import configure_alerting_from_env
configure_alerting_from_env()
print('Telegram configured')
"

# 5. Test alert
python3 -c "
import asyncio
from observability.alerting import send_system_status_alert
asyncio.run(send_system_status_alert('test', 'started', {'msg': 'Test'}))
"
```

---

### 3.5 HIGH ERROR RATE IN LOGS

**Detection:**
```bash
tail -100 logs/final.log | grep "ERROR\|Exception\|failed"
```

**Common Causes & Fixes:**

| Error | Cause | Fix |
|-------|------|-----|
| `401 Unauthorized` | Wrong API key/secret | Verify `.env` keys match https://testnet.binancefuture.com/ |
| `Insufficient margin` | Position size too large | Reduce `max_position_size` in `TradingConfig` |
| `JSON parse error` | Binance API down / rate limit | Wait 5 minutes; check https://binance.statuspage.io/ |
| `No module named 'X'` | Missing dependency | `pip install -r requirements.txt` |

---

## 4. Operational Procedures

### 4.1 Starting the System

```bash
# Method A: Direct (development)
cd /home/nkhekhe/unified_trading_system
source .venv/bin/activate
python3 run_enhanced_testnet.py

# Method B: tmux (recommended for persistence)
./manage.sh start
# Attach: tmux attach -t trading
# Detach: Ctrl+B then D

# Method C: systemd (boot persistence — TODO: create service file)
sudo systemctl start unified-trading
```

### 4.2 Stopping the System

```bash
# Method A: Ctrl+C (if running in foreground)
# Press Ctrl+C in the terminal

# Method B: tmux stop
./manage.sh stop

# Method C: Kill process
ps aux | grep run_enhanced_testnet | grep -v grep | awk '{print $2}' | xargs kill

# Method D: systemd
sudo systemctl stop unified-trading
```

### 4.3 Restarting the System

```bash
./manage.sh restart
# Equivalent to: stop → wait 2s → start
```

### 4.4 Viewing Logs

```bash
# Main trading log
tail -f logs/final.log

# Trade journal (all trades)
cat logs/trade_journal.json | python3 -m json.tool | less

# Performance analysis
python3 compute_performance.py

# Systemd logs (if using systemd)
sudo journalctl -u unified-trading -f
```

---

## 5. Monitoring & Alerting

### 5.1 Key Metrics to Monitor

| Metric | Threshold | Action |
|--------|-----------|--------|
| **Cycle Time** | >1000ms | Investigate API latency |
| **Win Rate** | <20% over 100 trades | Review signal generator params |
| **Drawdown** | >5% daily | Check risk manager settings |
| **Open Positions** | >5 | Reduce `max_positions` |
| **Error Rate** | >10 errors/cycle | Investigate API connectivity |

### 5.2 Telegram Alerts Received

| Alert | Trigger |
|-------|---------|
| `🔔 TEST: System Restart` | System startup |
| `✅ System initialized!` | After `loop.initialize()` |
| `🚀 Trading started!` | After `loop.start()` |
| `🚀 ENHANCED TRADING SYSTEM v2.0` | Entry point start |
| `Trade EXECUTED: ...` | Successful order |
| `Trade FAILED: ...` | Failed order |
| `🚨 Risk Alert: ...` | Risk threshold breached |

---

## 6. Backup & Recovery

### 6.1 Trade Journal Backup

```bash
# Backup trade journal (daily cron job)
cp logs/trade_journal.json logs/trade_journal_$(date +%Y%m%d).json

# Keep last 30 days
find logs/ -name "trade_journal_*.json" -mtime +30 -delete
```

### 6.2 Configuration Backup

```bash
# Backup configs (weekly)
tar -czf config_backup_$(date +%Y%m%d).tar.gz config/ .env
```

### 6.3 Git Workflow

```bash
# Save current state
git add .
git commit -m "Checkpoint: Current state before changes"
git tag -a v3.2.0-$(date +%Y%m%d) -m "Snapshot"

# Rollback
git reset --hard v3.2.0-YYYYMMDD
```

---

## 7. Performance Baseline

| Metric | Current | Target |
|--------|---------|--------|
| **Cycles Completed** | 34,333+ | N/A (increasing) |
| **Cycle Time** | ~400ms | <500ms |
| **Win Rate** | ~35% | ≥65% |
| **Expected Value** | +0.0009/trade | ≥+0.005 |
| **Balance** | $4,919.50 | N/A (varies) |
| **Leverage** | 20x | 15-25x range |
| **Open Positions** | 0-5 | <5 |

---

## 8. Known Issues & Technical Debt

| Issue | Impact | Priority | Fix Location |
|--------|---------|----------|---------------|
| **Health endpoint dead** | Monitoring blind spot | P0 | `observability/health.py:256` — use `aiohttp.web` |
| **Hardcoded paths** | Not portable | P1 | Multiple files — use `os.path.dirname(__file__)` |
| **TradeJournal O(n) load** | Slow startup @10K+ trades | P1 | `trade_journal.py:50` — migrate to SQLite |
| **http.server blocks asyncio** | Health check dead | P0 | `health.py` — switch to `aiohttp` |
| **Duplicate `create_live_trading_loop()`** | Code bug | P1 | `continuous_trading_loop_binance.py:1848` — renamed to `create_live_trading_loop_v2()` |
| **40x leverage fallback** | Violates 25x max constraint | P1 | `continuous_trading_loop_binance.py:492` — cap at 25x |

---

## 9. Escalation Matrix

| Severity | Condition | Response Time | Action |
|----------|-----------|----------------|--------|
| **P0 — Critical** | System crashed, health endpoint dead | Immediate | Restart, apply health fix |
| **P1 — High** | Error rate >10%, win rate <20% | <1 hour | Investigate logs, adjust params |
| **P2 — Medium** | Single trade failure, minor bug | <1 day | Log issue, schedule fix |
| **P3 — Low** | Documentation gap, code cleanup | <1 week | Add to backlog |

---

## 10. Contact & References

| Resource | Location |
|----------|----------|
| **README** | `README.md` |
| **Installation Guide** | `docs/INSTALLATION.md` |
| **Configuration Reference** | `docs/CONFIGURATION.md` |
| **Portability Checklist** | `docs/PORTABILITY.md` |
| **Mathematical Foundations** | `docs/research/MATHEMATICAL_FOUNDATIONS.md` |
| **Risk Budget** | `docs/risk/RISK_BUDGET.md` |
| **ML API Complete** | `docs/reference/ML_API_COMPLETE.md` |
| **Algorithm Analysis** | `docs/research/ALGORITHM_ANALYSIS.md` |
| **Data Pipeline** | `docs/data/DATA_PIPELINE.md` |
| **CFA Attestation** | `docs/compliance/CFA_ATTESTATION.md` |
| **Troubleshooting** | `docs/reference/TROUBLESHOOTING.md` |

---

*Runbook Version: 1.0 | Date: 2026-05-04 | System: v3.2.0 | SRE: nkhekhe@server*
