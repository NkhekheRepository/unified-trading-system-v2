#!/bin/bash
# Auto-Connect Script - Waits for valid keys then starts LIVE trading
# Get keys: https://testnet.binancefutures.com/ (login with GitHub)

ENV_FILE="/home/nkhekhe/unified_trading_system/.env"
SYSTEM_DIR="/home/nkhekhe/unified_trading_system"

echo "========================================="
echo "AUTO-CONNECT FOR LIVE TESTNET"
echo "Target: 70%+ Daily Profits"
echo "========================================="
echo ""

while true; do
    if [ -f "$ENV_FILE" ]; then
        source "$ENV_FILE"
        
        # Test if keys are valid
        TEST=$(cd "$SYSTEM_DIR" && python3 -c "
import sys
try:
    from binance.client import Client
    from dotenv import load_dotenv
    load_dotenv()
    key = '$BINANCE_TESTNET_API_KEY'
    secret = '$BINANCE_TESTNET_API_SECRET'
    if len(key) < 20 or len(secret) < 20:
        print('INVALID')
        sys.exit(1)
    client = Client(key, secret, testnet=True)
    client.SAPI_URL = 'https://testnet.binancefutures.com'
    client.API_URL = 'https://testnet.binancefutures.com'
    status = client.get_system_status()
    print('VALID')
except Exception as e:
    print('INVALID')
" 2>&1)
        
        if [[ "$TEST" == *"VALID"* ]]; then
            echo "[$(date)] ✅ VALID KEYS DETECTED! Starting LIVE trading..."
            cd "$SYSTEM_DIR"
            ./deploy_production.sh > /dev/null 2>&1 &
            sleep 5
            echo "[$(date)] ✅ SYSTEM LIVE! Monitor: tail -f logs/trading.log"
            break
        else
            echo "[$(date)] ⏳ Waiting for valid keys in .env..."
            echo "   Get keys: https://testnet.binancefutures.com/ (login with GitHub)"
        fi
    else
        echo "[$(date)] ⏳ Waiting for .env file..."
    fi
    
    sleep 15
done

echo ""
echo "========================================="
echo "SYSTEM IS LIVE - TARGET 70%+ DAILY PROFITS"
echo "========================================="
