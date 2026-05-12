# Getting Started with the Unified Trading System

This guide will help you get the Unified Trading System up and running in under 30 minutes, regardless of your role or background.

## Prerequisites

Before you begin, ensure you have:

- Python 3.8 or higher
- Git installed
- Access to a terminal/command line
- Approximately 30 minutes of time

## Installation

### Step 1: Clone the Repository

```bash
git clone [repository-url]
cd unified_trading_system
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Verify Installation

```bash
python -c "import unified_trading_system; print('Import successful')"
```

## Quick Start Options

Choose the method that best fits your role and goals:

### Option 1: Basic Paper Trading (Recommended for First Run)

This runs the system in simulated mode with no real money at risk.

```bash
# Make scripts executable if needed
chmod +x start_system.sh

# Start the system
./start_system.sh
```

You should see output indicating the system is initializing and beginning trading cycles.

### Option 2: Direct Python Execution

```bash
python continuous_trading_loop.py
```

### Option 3: Testnet Mode (Simulated Exchange Connection)

```bash
python run_testnet.py
```

## Verifying the System is Working

### Check the Logs

In another terminal window, run:

```bash
# Follow the main system log
tail -f logs/system.log

# In another tab/window:
tail -f logs/trading_system.log
```

You should see entries like:
```
INFO:trading_loop:Starting trading loop
INFO:trading_loop:Trading loop initialized in PAPER mode
INFO:trading_loop:Started cycle_1: 2 signals, 0 orders in 150.3ms
```

### Check Health Endpoints

```bash
# Check system health
curl -s http://localhost:8080/health | jq .

# Check detailed health
curl -s http://localhost:8080/health/json | jq .
```

### Check Metrics (if enabled)

```bash
curl -s http://localhost:9090/metrics | head -20
```

## Expected Behavior Timeline

| Time | What to Expect |
|------|----------------|
| 0-2 min | System initialization, component loading, health checks startup |
| 2-10 min | Market data simulation begins, belief state estimation, initial signal generation |
| 10-20 min | First trading signals generated, risk assessment, potential order execution (in PAPER mode) |
| 20-30 min | Ongoing trading cycles, performance metrics collection, system health monitoring |

## Role-Specific Quick Start Guides

Choose your role for a tailored getting started experience:

- [Quantitative Developer](./quantitative-developer.md)
- [Software Architect](./software-architect.md)
- [AI/ML Engineer](./ai-ml-engineer.md)
- [Data Engineer](./data-engineer.md)
- [SRE/DevOps](./sre.md)
- [Capital Allocator/Hedge Fund Manager](./capital-allocator.md)
- [UX Designer](./ux-designer.md)

## Common Issues and Troubleshooting

### Problem: Import Errors
**Solution:** Ensure all dependencies are installed: `pip install -r requirements.txt`

### Problem: Port Conflicts (Address already in use)
**Solution:** Change ports in your `.env` file:
```env
HEALTH_CHECK_PORT=8081
METRICS_PORT=9091
```

### Problem: No Signals Being Generated
**Solution:** For initial testing, temporarily relax thresholds in `config/learning_high_wr.yaml`:
```yaml
min_confidence_threshold: 0.1
min_expected_return: 0.0001
```

### Problem: System Appears Stuck or Unresponsive
**Solution:** 
1. Check logs for error messages
2. Verify health endpoint is responding: `curl http://localhost:8080/health`
3. Restart the system if needed: `Ctrl+C` then rerun your start command

## Next Steps

After getting the system running:

1. Explore the logs to understand how signals are generated and trades executed
2. Experiment with different configurations in the `config/` directory
3. Review the source code to understand how specific components work
4. Run the test suite: `python -m pytest tests/`
5. Check out the role-specific guides for deeper dives based on your interests

## Need Help?

If you encounter issues not covered here:
1. Check the [troubleshooting guide](./reference/troubleshooting.md)
2. Review the source code comments for implementation details
3. Look at the test files in the `tests/` directory for usage examples