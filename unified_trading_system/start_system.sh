#!/bin/bash
# Robust startup script for unified trading system
# Ensures process stays alive and logs properly

cd /home/nkhekhe/unified_trading_system

# Kill any existing instances
pkill -f "continuous_trading_loop_binance.py" 2>/dev/null
sleep 2

# Start the system with proper output handling
echo "$(date): Starting unified trading system with Binance Testnet..."

# Run in background with nohup, proper output redirection
nohup python3 -u continuous_trading_loop_binance.py > logs/binance_trading.log 2>&1 &
PID=$!

# Disown to prevent SIGHUP
disown $PID

echo "$(date): Started with PID $PID"
echo $PID > logs/system.pid

# Wait a moment and verify it's running
sleep 5

if ps -p $PID > /dev/null 2>&1; then
    echo "✅ System is running with PID $PID"
    echo "📊 View logs: tail -f logs/binance_trading.log"
else
    echo "❌ System failed to start. Checking logs..."
    tail -20 logs/binance_trading.log
    exit 1
fi
