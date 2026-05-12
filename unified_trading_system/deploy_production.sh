#!/bin/bash
# Production Deployment Script for Unified HFT Trading System
# Target: 70%+ Daily Profits with Risk Management
# Author: Principal Quant/Architect Team

set -e  # Exit on error

# Configuration
SYSTEM_DIR="/home/nkhekhe/unified_trading_system"
LOG_DIR="$SYSTEM_DIR/logs"
PID_DIR="$SYSTEM_DIR/.pids"
SCORING_DIR="$SYSTEM_DIR/scoring"
LEARNING_DIR="$SYSTEM_DIR/learning"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN} Unified HFT Trading System Deployment${NC}"
echo -e "${GREEN} Target: 70%+ Daily Profits${NC}"
echo -e "${GREEN}=========================================${NC}"

# Create necessary directories
mkdir -p "$LOG_DIR" "$PID_DIR" "$SCORING_DIR" "$LEARNING_DIR"
echo -e "${YELLOW}[$(date)] Creating directories...${NC}"

# Load environment variables
if [ -f "$SYSTEM_DIR/.env" ]; then
    source "$SYSTEM_DIR/.env"
    echo -e "${GREEN}[$(date)] Loaded environment variables${NC}"
else
    echo -e "${RED}[$(date)] ERROR: .env file not found in $SYSTEM_DIR${NC}"
    exit 1
fi

# Check Python dependencies
echo -e "${YELLOW}[$(date)] Checking Python dependencies...${NC}"
pip install -q --user --break-system-packages websockets aiohttp numpy pyyaml 2>&1 | tee -a "$LOG_DIR/deploy.log"
pip install -q --user uvloop 2>&1 | tee -a "$LOG_DIR/deploy.log" || echo "uvloop not available, using default asyncio"

# Function to start a component
start_component() {
    local name=$1
    local script=$2
    local log_file=$3
    
    echo -e "${YELLOW}[$(date)] Starting $name...${NC}"
    nohup python3 "$script" >> "$LOG_DIR/$log_file" 2>&1 &
    local pid=$!
    echo $pid > "$PID_DIR/${name}.pid"
    echo -e "${GREEN}[$(date)] $name started with PID $pid${NC}"
    sleep 2  # Give component time to initialize
}

# Start Walk-Forward Optimizer (runs daily)
echo -e "${YELLOW}[$(date)] Starting Walk-Forward Optimizer (daily cron)...${NC}"
(crontab -l 2>/dev/null; echo "0 0 * * * cd $SYSTEM_DIR && python3 $LEARNING_DIR/walk_forward_optimizer.py >> $LOG_DIR/optimizer.log 2>&1") | crontab -

# Start Performance Scoring System (runs every hour)
echo -e "${YELLOW}[$(date)] Starting Performance Scorer (hourly)...${NC}"
(crontab -l 2>/dev/null; echo "0 * * * * cd $SYSTEM_DIR && python3 $SCORING_DIR/score_system.py >> $LOG_DIR/scoring.log 2>&1") | crontab -

# Start Main Trading System with all enhancements (Confluence, Hedging, RL)
echo -e "${YELLOW}[$(date)] Starting Unified HFT Trading System...${NC}"
if [ -f "$SYSTEM_DIR/continuous_trading_loop_binance.py" ]; then
    start_component "main_trading" "$SYSTEM_DIR/continuous_trading_loop_binance.py" "trading.log"
elif [ -f "$SYSTEM_DIR/run_continuous_loop.py" ]; then
    start_component "main_trading" "$SYSTEM_DIR/run_continuous_loop.py" "trading.log"
else
    echo -e "${RED}[$(date)] ERROR: Main trading loop script not found${NC}"
    exit 1
fi

# Verify all components are running
echo -e "${YELLOW}[$(date)] Verifying components...${NC}"
sleep 5
for pid_file in "$PID_DIR"/*.pid; do
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null; then
            component=$(basename "$pid_file" .pid)
            echo -e "${GREEN}[$(date)] $component is running (PID: $pid)${NC}"
        else
            component=$(basename "$pid_file" .pid)
            echo -e "${RED}[$(date)] WARNING: $component is not running${NC}"
        fi
    fi
done

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN} Deployment Complete!${NC}"
echo -e "${GREEN} System is now running.${NC}"
echo -e "${YELLOW} Check logs in: $LOG_DIR${NC}"
echo -e "${YELLOW} Performance reports: $SCORING_DIR${NC}"
echo -e "${GREEN}=========================================${NC}"

# Keep script running to handle signals
trap 'echo -e "${YELLOW}[$(date)] Shutting down all components...${NC}"; kill $(cat "$PID_DIR"/*.pid 2>/dev/null) 2>/dev/null; exit 0' SIGTERM SIGINT

wait
