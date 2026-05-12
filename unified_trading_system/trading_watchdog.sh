#!/bin/bash
LOG_DIR="/home/nkhekhe/unified_trading_system/logs"
LOG_FILE="$LOG_DIR/trading_loop.log"
SCRIPT_DIR="/home/nkhekhe/unified_trading_system"
MAX_RESTARTS=999999
RESTART_DELAY=3
CHECK_INTERVAL=10

echo "🚀 Trading System Watchdog Started at $(date)"

restart_count=0

restart_trading() {
    local count=$1
    echo "[$(date)] Restarting trading system (attempt $count)..."
    
    # Kill any existing process
    pkill -f "continuous_trading_loop_binance" 2>/dev/null || true
    sleep 2
    
    # Start new process
    cd "$SCRIPT_DIR"
    nohup python3 continuous_trading_loop_binance.py >> "$LOG_FILE" 2>&1 &
    echo $! > "$SCRIPT_DIR/.trading_pid"
    
    echo "[$(date)] Trading system started with PID $(cat $SCRIPT_DIR/.trading_pid)"
}

# Initial start
restart_trading 1
restart_count=1

# Main watchdog loop
while true; do
    sleep $CHECK_INTERVAL
    
    # Check if process is running
    if [ -f "$SCRIPT_DIR/.trading_pid" ]; then
        PID=$(cat "$SCRIPT_DIR/.trading_pid")
        if ! kill -0 "$PID" 2>/dev/null; then
            echo "[$(date)] Process $PID not running - restarting..."
            
            # Check if we hit max restarts
            if [ $restart_count -ge $MAX_RESTARTS ]; then
                echo "[FATAL] Max restarts reached. Exiting."
                exit 1
            fi
            
            ((restart_count++))
            restart_trading $restart_count
            sleep 5  # Give it time to initialize
        else
            # Check log for recent activity
            last_activity=$(tail -1 "$LOG_FILE" 2>/dev/null | cut -d'Z' -f1)
            if [ -n "$last_activity" ]; then
                echo "[$(date)] System running (PID $PID), last activity: $last_activity"
            fi
        fi
    else
        echo "[$(date)] No PID file - starting fresh..."
        restart_trading $restart_count
        ((restart_count++))
    fi
done