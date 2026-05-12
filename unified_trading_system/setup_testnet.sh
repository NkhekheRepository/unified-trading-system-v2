#!/bin/bash
echo "======================================="
echo "BINANCE TESTNET API SETUP"
echo "======================================="
echo ""
echo "To get Testnet API keys:"
echo "1. Go to: https://testnet.binance.vision/"
echo "2. Log in with GitHub"
echo "3. Create API Key (HMAC SHA256)"
echo "4. Copy Key and Secret"
echo ""
read -p "Enter your Testnet API Key: " API_KEY
read -p "Enter your Testnet API Secret: " API_SECRET

# Save to .env file
cat > .env << EOFF
BINANCE_TESTNET_API_KEY=$API_KEY
BINANCE_TESTNET_API_SECRET=$API_SECRET
EOFF

echo ""
echo "✓ API keys saved to .env"
echo ""
echo "Now run: python3 live_testnet_trade_test.py"
