#!/usr/bin/env python3
"""
Permanent watchdog for run_enhanced_testnet.py
Auto-restarts if process stops
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path

WORKING_DIR = "/home/nkhekhe/unified_trading_system"
LOG_FILE = f"{WORKING_DIR}/logs/trading.log"
PID_FILE = f"{WORKING_DIR}/logs/trading.pid"
SCRIPT = f"{WORKING_DIR}/run_enhanced_testnet.py"
MAX_RESTARTS = 5
RESTART_DELAY = 10

def get_pid():
    try:
        with open(PID_FILE) as f:
            return int(f.read().strip())
    except:
        return None

def is_running(pid):
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] WATCHDOG: {msg}")
    with open(f"{WORKING_DIR}/logs/watchdog.log", "a") as f:
        f.write(f"[{ts}] {msg}\n")

def start_process():
    log(f"Starting {SCRIPT}")
    # Redirect output to log file
    with open(LOG_FILE, "a") as lf:
        proc = subprocess.Popen(
            [sys.executable, SCRIPT],
            cwd=WORKING_DIR,
            stdout=lf,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid
        )
    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))
    log(f"Started with PID {proc.pid}")
    return proc.pid

def signal_handler(signum, frame):
    log(f"Received signal {signum}, shutting down...")
    pid = get_pid()
    if pid and is_running(pid):
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
            time.sleep(2)
        except:
            pass
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    log("Watchdog started")
    restarts = 0
    
    while True:
        pid = get_pid()
        
        if not is_running(pid):
            log(f"Process not running (PID: {pid})")
            restarts += 1
            
            if restarts > MAX_RESTARTS:
                log(f"Too many restarts ({restarts}), waiting 60s before retry")
                time.sleep(60)
                restarts = 0
            
            if restarts <= MAX_RESTARTS:
                start_process()
                time.sleep(RESTART_DELAY)
        else:
            if restarts > 0:
                log("Process recovered")
                restarts = 0
        
        time.sleep(10)