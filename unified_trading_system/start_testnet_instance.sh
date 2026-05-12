#!/bin/bash
# Start unified_trading_system TESTNET instance with its own API key
cd /home/nkhekhe/unified_trading_system

# Use testnet instance's dedicated .env file
if [ -f testnet/.env ]; then
    source testnet/.env
fi

echo "Starting TESTNET instance with API key: ${BINANCE_API_KEY:0:10}..."
exec python3 continuous_trading_loop_binance.py testnet
