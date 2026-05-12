#!/bin/bash
# Smart Testnet Launcher - Waits for valid API keys then auto-starts
# Get keys: https://testnet.binance.vision/ (login with GitHub)

ENV_FILE="/home/nkhekhe/unified_trading_system/.env"
SYSTEM_DIR="/home/nkhekhe/unified_trading_system"

echo "========================================="
echo "SMART TESTNET LAUNCHER"
echo "Target: 70%+ Daily Profits"
echo "========================================="
echo ""

while true; do
    # Check if .env exists and has keys
    if [ -f "$ENV_FILE" ]; then
        source "$ENV_FILE"
        
        # Test if keys are valid (simple check)
        if [ ${#BINANCE_TESTNET_API_KEY} -gt 20 ] && [ ${#BINANCE_TESTNET_API_SECRET} -gt 20 ]; then
            echo "[$(date)] Found API keys, testing connection..."
            
            # Quick test with Python
            TEST_RESULT=$(cd "$SYSTEM_DIR" && python3 -c "
import os, sys
from binance.client import Client
from dotenv import load_dotenv
load_dotenv()
try:
    client = Client(os.getenv('BINANCE_TESTNET_API_KEY'), os.getenv('BINANCE_TESTNET_API_SECRET'), testnet=True)
    account = client.get_account()
    print('SUCCESS')
except Exception as e:
    print(f'FAILED: {str(e)[:50]}')
" 2>&1)
            
            if [[ "$TEST_RESULT" == "SUCCESS" ]]; then
                echo "[$(date)] ✅ API keys valid! Starting trading system..."
                cd "$SYSTEM_DIR"
                ./deploy_production.sh > /dev/null 2>&1 &
                sleep 5
                echo "[$(date)] ✅ System started! Monitor: tail -f logs/trading.log"
                break
            else
                echo "[$(date)] ❌ API keys invalid: $TEST_RESULT"
                echo "[$(date)] Get new keys from: https://testnet.binance.vision/"
                echo "[$(date)] Then update: nano $ENV_FILE"
            fi
        else
            echo "[$(date)] ⏳ Waiting for valid API keys in .env..."
            echo "[$(date)] Get keys: https://testnet.binance.vision/ (login with GitHub)"
        fi
    else
        echo "[$(date)] ⏳ Waiting for .env file..."
    fi
    
    echo "[$(date)] Checking again in 30 seconds... (Ctrl+C to stop)"
    sleep 30
done

echo ""
echo "========================================="
echo "SYSTEM IS RUNNING!"
echo "Monitor: tail -f $SYSTEM_DIR/logs/trading.log"
echo "Performance: python3 $SYSTEM_DIR/scoring/score_system.py"
echo "========================================="
