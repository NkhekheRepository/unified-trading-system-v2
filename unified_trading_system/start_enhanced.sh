#!/usr/bin/env bash
# Load env vars from .env
set -a
source "$(dirname "$0")/.env"
set +a
# Start enhanced testnet loop in background, redirect logs
nohup python3 "$(dirname "$0")/run_enhanced_testnet.py" > "$(dirname "$0")/enhanced_loop.log" 2>&1 & echo $! > "$(dirname "$0")/enhanced_loop.pid"
