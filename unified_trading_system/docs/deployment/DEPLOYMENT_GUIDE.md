# Deployment Guide#

Complete deployment guide for the Unified Trading System using tmux, systemd, Docker, and manual methods.

---

## 1. Deployment Methods Comparison#

| Method | Persistence | Boot Start | Ease of Use | Best For |
|-----------|--------------|------------|--------------|----------|
| **tmux** | ✅ Yes | Manual | ⭐⭐⭐⭐⭐ | Development, testing |
| **systemd** | ✅ Yes | ✅ Yes | ⭐⭐⭐ | Production server |
| **Docker** | ✅ Yes | ✅ Yes | ⭐⭐ | One-command deploy |
| **Manual** | ❌ No | Manual | ⭐ | Quick testing |

---

## 2. Method A: tmux (Recommended for Development)#

### 2.1 Setup#

```bash
# Make manage.sh executable
chmod +x manage.sh

# Check script contents
cat manage.sh
# Expected: start, stop, restart, status functions
```

### 2.2 Commands#

```bash
# Start in tmux session 'trading'
./manage.sh start
# Creates: tmux new-session -d -s trading "cd $WORKDIR && python3 run_enhanced_testnet.py 2>&1 | tee -a $LOG"

# Check status
./manage.sh status
# Expected: ✅ Trading system RUNNING (tmux: trading)
# Shows last 5 lines of log

# Attach to session (view output)
tmux attach -t trading

# Inside tmux:
  - Press Ctrl+B then D to detach (keeps running)
  - Press Ctrl+B then X to kill session

# Stop
./manage.sh stop
# Runs: tmux kill-session -t trading

# Restart
./manage.sh restart
# Runs: stop → wait 2s → start
```

### 2.3 Log Location#

```bash
# Main log (from manage.sh)
tail -f logs/trading.log

# Trading loop log
tail -f logs/final.log

# Systemd-style: see SRE_RUNBOOK.md
```

---

## 3. Method B: systemd (Production Server)#

### 3.1 Create Service File#

```bash
sudo nano /etc/systemd/system/unified-trading.service
```

**Paste:**
```ini
[Unit]
Description=Unified Trading System
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=nkhekhe
WorkingDirectory=/home/nkhekhe/unified_trading_system
Environment="PATH=/home/nkhekhe/unified_trading_system/.venv/bin:/usr/bin:/bin"
ExecStartPre=/bin/sleep 10
ExecStart=/home/nkhekhe/unified_trading_system/.venv/bin/python3 /home/nkhekhe/unified_trading_system/run_enhanced_testnet.py
Restart=always
RestartSec=10
StandardOutput=append:/home/nkhekhe/unified_trading_system/logs/trading.log
StandardError=append:/home/nkhekhe/unified_trading_system/logs/trading.log

[Install]
WantedBy=multi-user.target
```

### 3.2 Enable & Start#

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable at boot
sudo systemctl enable unified-trading.service

# Start now
sudo systemctl start unified-trading.service

# Check status
sudo systemctl status unified-trading.service
# Expected: Active: active (running) since ...
```

### 3.3 Logs#

```bash
# Follow logs (like tail -f)
sudo journalctl -u unified-trading -f

# Last 100 lines
sudo journalctl -u unified-trading -n 100

# Since boot
sudo journalctl -u unified-trading -b
```

### 3.4 Management#

```bash
# Stop
sudo systemctl stop unified-trading

# Start
sudo systemctl start unified-trading;

# Restart
sudo systemctl restart unified-trading;

# Disable (no auto-start at boot)
sudo systemctl disable unified-trading
```

---

## 4. Method C: Docker (One-Command Deploy)#

### 4.1 Create Dockerfile#

```bash
nano Dockerfile
```

**Paste:**
```dockerfile
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy requirements first (leverage cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Default command
CMD ["python3", "run_enhanced_testnet.py"]
```

### 4.2 Build & Run#

```bash
# Build image
docker build -t unified-trading:latest .

# Run (with env file)
docker run -d \
  --name unified-trading \
  --restart unless-stopped \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  unified-trading:latest

# View logs
docker logs -f unified-trading

# Stop
docker stop unified-trading;

# Remove
docker rm unified-trading;
```

### 4.3 Docker Compose (Optional)#

```bash
nano docker-compose.yml
```

```yaml
version: '3.8'

services:
  trading:
    build: .
    container_name: unified-trading
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    ports:
      - "8080:8080"   # Health (after fix)
      - "9090:9090"   # Metrics
```

**Run:**
```bash
docker-compose up -d
docker-compose logs -f
docker-compose down
```

---

## 5. Method D: Manual (Quick Testing)#

```bash
# Activate venv
source .venv/bin/activate;

# Run directly
python3 run_enhanced_testnet.py

# Stop: Ctrl+C
```

---

## 6. Health Check Setup#

### 6.1 Before Deployment#

**⚠️ Known Issue:** `observability/health.py:256` uses `http.server` which **blocks asyncio**.  
Health endpoint at `:8080` will NOT respond until fixed.

**Fix (Tier 1 #4):**
```python
# In observability/health.py, replace:
from http.server import HTTPServer, BaseHTTPRequestHandler;

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

### 6.2 Verify Health After Fix#

```bash
# From any deployment method
curl http://localhost:8080/health

# Expected JSON:
# {
#   "status": "healthy",
#   "components": {...}
# }
```

---

## 7. Metrics Endpoint#

**Available at:** `http://localhost:9090/metrics`

```bash
curl http://localhost:9090/metrics | grep -E "trading_|risk_|health_"
```

**Key Metrics:**
| Metric | Description |
|--------|-------------|
| `trading_cycles_total` | Total cycles |
| `trading_signals_total` | Signals generated |
| `trading_orders_total` | Orders executed |
| `trading_pnl` | Current P&L |
| `risk_score` | Risk score [0, 1] |
| `risk_drawdown_percent` | Drawdown % |

---

## 8. Pre-Deployment Checklist#

| Check | Command | Expected |
|-------|---------|----------|
| OS packages | `python3.12 --version` | 3.12.x |
| Repo cloned | `ls run_enhanced_testnet.py` | File exists |
| venv active | `which python` | .../.venv/bin/python |
| Depps installed | `pip list \| grep aiohttp` | aiohttp 3.13.5 |
| .env configured | `grep BINANCE_TESTNET_API_KEY .env` | Not empty |
| Imports work | `python3 -c "from run_enhanced_testnet import main"` | No error |
| Port free | `curl -s http://localhost:8080/health` | After fix: JSON |
| Logs dir exists | `ls logs/` | Directory exists |

---

## 9. Post-Deployment Verification#

```bash
# 1. Process running?
ps aux | grep run_enhanced_testnet | grep -v grep;

# 2. Cycles executing?
tail -5 logs/final.log | grep "Completed cycle";

# 3. Balance available?
grep "crossWalletBalance\|Using" logs/final.log | tail -1;

# 4. Telegram alert received?
# Check Telegram app for "🔔 TEST: System Restart" message;

# 5. Health check (after fix)?
curl http://localhost:8080/health | python3 -m json.tool;

# 6. Metrics?
curl http://localhost:9090/metrics | head -20;
```

---

## 10. Deployment Architecture Diagram#

```
┌──────────────────────────────────────────────────────────┐
│                    SERVER                              │
│              (Ubuntu 22.04 / Debian 12)                │
│                                                │
│  ┌──────────────────────────────────────────────┐  │
│  │            .venv/ (Python 3.12)               │  │
│  │                                        │  │
│  │  run_enhanced_testnet.py (PID XXXXX)     │  │
│  │      ↓                                   │  │
│  │  EnhancedTradingLoop()                   │  │
│  │      ├─ _fetch_exchange_info()             │  │
│  │      ├─ _load_open_positions()            │  │
│  │      ├─ HealthServer.start() (:8080)     │  │
│  │      └─ loop.start() → while running:       │  │
│  │           └─ _run_cycle() every 10s        │  │
│  │                ├─ 12 symbols              │  │
│  │                ├─ Binance API calls         │  │
│  │                └─ Exit checks              │  │
│  └──────────────────────┬───────────────────────┘  │
│                          │                             │
│           ┌──────────────┴──────────────┐         │
│           │     logs/                       │         │
│           │     ├─ final.log                  │         │
│           │     ├─ trade_journal.json          │         │
│           │     └─ trading.log (tmux)          │         │
│           └──────────────────────────────────────┘         │
│                                                │
│  Ports: :8080 (health), :9090 (metrics)                   │
└──────────────────────────────────────────────────────────┘
```

---

## 11. Scaling Considerations#

| Item | Current | Recommendation |
|------|---------|---------------|
| **Symbols** | 12 | ≤20 (API rate limits) |
| **Cycle Interval** | 10s | ≥5s (Binance rate limit: 1200/min) |
| **Max Positions** | 5 | ≤10 (margin requirements) |
| **Leverage** | 20x | ≤25x (user constraint) |
| **Logs** | File-based | Add logrotate, consider ELK stack |
| **State** | In-memory | Use Redis for distributed state |
| **Database** | JSON (TradeJournal) | Migrate to SQLite/PostgreSQL >10K trades |

---

*Deployment Guide Version: 1.0 | Date: 2026-05-04 | System: v3.2.0*
