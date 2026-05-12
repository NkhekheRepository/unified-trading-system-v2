#!/bin/bash
#
# Trading System Auto-Restart Wrapper
# Ensures the trading system runs continuously with auto-restart on failure
#

SCRIPT_DIR="/home/nkhekhe/unified_trading_system"
LOG_FILE="$SCRIPT_DIR/logs/trading_system.log"
PID_FILE="$SCRIPT_DIR/logs/trading_system.pid"
PYTHON_BIN="/usr/bin/python3"

# Restart settings
MAX_RESTARTS=1000  # Max restarts per hour
RESTART_DELAY=10    # Seconds between restarts

# Binance API Keys (must be set as environment variables)
if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_API_SECRET" ]; then
    echo "ERROR: BINANCE_API_KEY and BINANCE_API_SECRET must be set as environment variables"
    echo "Usage: export BINANCE_API_KEY='your_api_key' BINANCE_API_SECRET='your_api_secret'"
    echo "       $0 start"
    exit 1
fi

start_trading_system() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | Starting trading system..." >> "$LOG_FILE"
    
    cd "$SCRIPT_DIR"
    nohup $PYTHON_BIN continuous_trading_loop_binance.py >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    
    local pid=$(cat "$PID_FILE")
    echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | Trading system started with PID: $pid" >> "$LOG_FILE"
}

stop_trading_system() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | Stopping trading system (PID: $pid)..." >> "$LOG_FILE"
            kill "$pid" 2>/dev/null
            sleep 3
        fi
        rm -f "$PID_FILE"
    fi
}

check_system() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') | WARNING | Process $pid not running, needs restart" >> "$LOG_FILE"
            return 1
        fi
        return 0
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') | WARNING | No PID file found" >> "$LOG_FILE"
        return 1
    fi
}

restart_trading_system() {
    stop_trading_system
    sleep "$RESTART_DELAY"
    start_trading_system
}

# Main loop
case "$1" in
    start)
        if check_system; then
            echo "Trading system is already running (PID: $(cat $PID_FILE))"
            exit 0
        fi
        start_trading_system
        echo "Trading system started"
        ;;
    stop)
        stop_trading_system
        echo "Trading system stopped"
        ;;
    restart)
        stop_trading_system
        sleep 2
        start_trading_system
        echo "Trading system restarted"
        ;;
    status)
        if check_system; then
            echo "Trading system is running (PID: $(cat $PID_FILE))"
        else
            echo "Trading system is NOT running"
        fi
        ;;
    monitor)
        # Continuous monitoring with auto-restart
        echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | Starting monitor mode..." >> "$LOG_FILE"
        restarts=0
        while true; do
            if ! check_system; then
                ((restarts++))
                if [ $restarts -gt $MAX_RESTARTS ]; then
                    echo "$(date '+%Y-%m-%d %H:%M:%S') | ERROR | Too many restarts ($restarts), exiting..." >> "$LOG_FILE"
                    exit 1
                fi
                echo "$(date '+%Y-%m-%d %H:%M:%S') | WARNING | Restarting trading system (attempt $restarts)..." >> "$LOG_FILE"
                restart_trading_system
            fi
            sleep 30
        done
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|monitor}"
        exit 1
        ;;
esac