#!/bin/bash
# Trading System Manager
# Usage: ./manage.sh start|stop|restart|status

WORKDIR="/home/nkhekhe/unified_trading_system"
SESSION="trading"
LOG="$WORKDIR/logs/trading.log"

start() {
    tmux kill-session -t $SESSION 2>/dev/null
    tmux new-session -d -s $SESSION "cd $WORKDIR && python3 run_enhanced_testnet.py 2>&1 | tee -a $LOG"
    echo "Started in tmux session '$SESSION'"
}

stop() {
    tmux kill-session -t $SESSION 2>/dev/null
    echo "Stopped tmux session"
}

restart() {
    stop
    sleep 2
    start
}

status() {
    if tmux has-session -t $SESSION 2>/dev/null; then
        echo "✅ Trading system RUNNING (tmux: $SESSION)"
        tail -5 $LOG
    else
        echo "❌ Trading system NOT running"
    fi
}

case "$1" in
    start) start ;;
    stop) stop ;;
    restart) restart ;;
    status) status ;;
    *) echo "Usage: $0 start|stop|restart|status" ;;
esac