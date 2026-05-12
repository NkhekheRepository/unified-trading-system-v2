#!/bin/bash
# Stop Script for Unified HFT Trading System
# Gracefully shuts down all components

SYSTEM_DIR="/home/nkhekhe/unified_trading_system"
PID_DIR="$SYSTEM_DIR/.pids"
LOG_DIR="$SYSTEM_DIR/logs"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=========================================${NC}"
echo -e "${YELLOW} Stopping Unified HFT Trading System${NC}"
echo -e "${YELLOW}=========================================${NC}"

# Function to stop a component
stop_component() {
    local name=$1
    local pid_file="$PID_DIR/${name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${YELLOW}[$(date)] Stopping $name (PID: $pid)...${NC}"
            kill -TERM $pid 2>/dev/null
            sleep 2
            # Force kill if still running
            if ps -p $pid > /dev/null 2>&1; then
                echo -e "${RED}[$(date)] Force killing $name...${NC}"
                kill -9 $pid 2>/dev/null
            fi
            rm -f "$pid_file"
            echo -e "${GREEN}[$(date)] $name stopped${NC}"
        else
            echo -e "${YELLOW}[$(date)] $name was not running${NC}"
            rm -f "$pid_file"
        fi
    else
        echo -e "${YELLOW}[$(date)] No PID file found for $name${NC}"
    fi
}

# Stop all components
stop_component "main_trading"
stop_component "async_data_feed"
stop_component "rl_execution_agent"
stop_component "hedging_engine"

# Stop scorer and optimizer (background loops)
echo -e "${YELLOW}[$(date)] Stopping background loops...${NC}"
pkill -f "score_system.py" 2>/dev/null
pkill -f "walk_forward_optimizer.py" 2>/dev/null

# Remove cron jobs
echo -e "${YELLOW}[$(date)] Removing cron jobs...${NC}"
(crontab -l 2>/dev/null | grep -v "walk_forward_optimizer.py" | grep -v "score_system.py") | crontab -

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN} All components stopped${NC}"
echo -e "${YELLOW} Logs preserved in: $LOG_DIR${NC}"
echo -e "${GREEN}=========================================${NC}"
