#!/bin/bash
# Start unified_trading_system LIVE instance with its own API key
cd /home/nkhekhe/unified_trading_system

# Use live instance's dedicated .env file
if [ -f live/.env ]; then
    source live/.env
fi

echo "Starting LIVE instance with API key: ${BINANCE_API_KEY:0:10}..."
exec python3 continuous_trading_loop_binance.py live
