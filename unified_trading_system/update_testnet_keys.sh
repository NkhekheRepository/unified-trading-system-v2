#!/bin/bash
# Quick Testnet Key Updater
# Usage: ./update_testnet_keys.sh <API_KEY> <API_SECRET>

if [ $# -ne 2 ]; then
    echo "Usage: $0 <API_KEY> <API_SECRET>"
    echo ""
    echo "Get keys from: https://testnet.binance.vision/ (login with GitHub)"
    exit 1
fi

API_KEY=$1
API_SECRET=$2

cat > /home/nkhekhe/unified_trading_system/.env << EOF
# Unified Trading System - API Keys for Testnet
BINANCE_TESTNET_API_KEY=$API_KEY
BINANCE_TESTNET_API_SECRET=$API_SECRET
BINANCE_TESTNET=true
EOF

echo "✅ Keys updated in .env"
echo ""
echo "Restarting trading system..."
cd /home/nkhekhe/unified_trading_system
./stop_production.sh 2>/dev/null
sleep 2
./deploy_production.sh > /dev/null 2>&1 &
sleep 5
echo "✅ System restarted with new keys"
echo ""
echo "Check status: tail -f logs/trading.log"
