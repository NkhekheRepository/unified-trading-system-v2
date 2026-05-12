#!/bin/bash
# Robust startup script for unified trading system - LIVE TRADING
# Ensures process stays alive and logs properly
# Uses separate directories and ports to avoid conflicts with testnet

cd /home/nkhekhe/unified_trading_system

# Kill any existing live instances
pkill -f "continuous_trading_loop_binance.py.*live" 2>/dev/null
sleep 2

# Set environment for live trading
export SYSTEM_ENV="live"
# API keys should be set externally for security:
# export BINANCE_API_KEY="your_live_api_key_here"
# export BINANCE_API_SECRET="your_live_api_secret_here"

# Start the system with proper output handling
echo "$(date): Starting unified trading system with Binance LIVE Account..."

# Run in background with nohup, proper output redirection
nohup python3 -u continuous_trading_loop_binance.py > logs/live/binance_trading.log 2>&1 &
PID=$!

# Disown to prevent SIGHUP
disown $PID

echo "$(date): Started with PID $PID"
echo $PID > logs/live/system.pid

# Wait a moment and verify it's running
sleep 5

if ps -p $PID > /dev/null 2>&1; then
    echo "✅ LIVE System is running with PID $PID"
    echo "📊 View logs: tail -f logs/live/binance_trading.log"
    echo "📈 Health check: http://localhost:8082/health"
    echo "📊 Metrics: http://localhost:9092/metrics"
else
    echo "❌ LIVE System failed to start. Checking logs..."
    tail -20 logs/live/binance_trading.log
    exit 1
fi