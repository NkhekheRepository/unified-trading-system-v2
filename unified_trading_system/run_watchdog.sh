#!/bin/bash
# Auto-restart wrapper for continuous trading system

LOG_FILE="/home/nkhekhe/unified_trading_system/logs/trading_loop.log"
PID_FILE="/home/nkhekhe/unified_trading_system/.trading_pid"
MAX_RESTARTS=100
RESTART_DELAY=5

echo "🚀 Starting Trading System Watchdog..."

start_trading() {
    cd /home/nkhekhe/unified_trading_system
    source /home/nkhekhe/lvr_trading_system/.env
    
    nohup python3 continuous_trading_loop_binance.py > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "[$(date)] Started trading system with PID $(cat $PID_FILE)"
}

stop_trading() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null
            sleep 2
            kill -9 "$PID" 2>/dev/null
        fi
        rm -f "$PID_FILE"
    fi
}

check_and_restart() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ! kill -0 "$PID" 2>/dev/null; then
            echo "[$(date)] Trading system stopped (PID $PID). Restarting..."
            start_trading
            ((RESTART_COUNT++))
            if [ $RESTART_COUNT -ge $MAX_RESTARTS ]; then
                echo "[$(date)] Max restarts reached. Exiting."
                exit 1
            fi
        fi
    else
        echo "[$(date)] No PID file. Starting..."
        start_trading
        RESTART_COUNT=1
    fi
}

# Initial start
start_trading
RESTART_COUNT=1

# Monitor loop
while true; do
    sleep 10
    check_and_restart
done