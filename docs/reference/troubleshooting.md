# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Unified Trading System.

## Getting Started with Troubleshooting

When you encounter an issue, follow this systematic approach:

1. **Identify the symptom**: What exactly is wrong or unexpected?
2. **Check the logs**: Look for error messages or unusual patterns
3. **Verify system health**: Use health endpoints to check component status
4. **Check metrics**: Look for abnormal patterns in performance metrics
5. **Reproduce the issue**: Try to consistently reproduce the problem
6. **Isolate the cause**: Determine which component or configuration is responsible
7. **Apply a fix**: Implement the solution
8. **Verify the fix**: Confirm the issue is resolved
9. **Document the solution**: Record what was learned for future reference

## Common Issues and Solutions

### System Won't Start

#### Symptoms
- Process exits immediately after starting
- No output or error messages
- Process fails to bind to ports

#### Possible Causes and Solutions

| Cause | Diagnosis | Solution |
|-------|-----------|----------|
| **Missing Dependencies** | Check startup output for import errors | `pip install -r requirements.txt` |
| **Port Already in Use** | Error message indicating port conflict | Change port in config or stop conflicting process |
| **Invalid Configuration** | Validation error during startup | Fix configuration errors using config reference |
| **Permission Issues** | Permission denied errors when accessing files | Check file permissions and ownership |
| **Environment Issues** | Missing environment variables or incorrect values | Check `.env` file and environment setup |

#### Diagnostic Commands
```bash
# Check if required dependencies are installed
pip list | grep -E "(numpy|yaml|aiohttp)"

# Check if ports are already in use
netstat -tulpn | grep -E ":8080|:9090"

# Try to start with verbose output to see where it fails
python -c "
import sys
import traceback
try:
    from continuous_trading_loop import create_testnet_trading_loop
    loop = create_testnet_trading_loop()
    print('Import successful')
except Exception as e:
    print(f'Import failed: {e}')
    traceback.print_exc()
"
```

### No Signals Being Generated

#### Symptoms
- System runs but shows "0 signals generated" in logs
- No trading activity observed
- Belief states are being updated but no signals produced

#### Possible Causes and Solutions

| Cause | Diagnosis | Solution |
|-------|-----------|----------|
| **Thresholds Too High** | Check signal generation thresholds in config | Lower `min_confidence_threshold` or `min_expected_return` |
| **Wrong Market Conditions** | Check if uncertainty or other filters are blocking signals | Examine uncertainty values and regime compatibility |
| **Symbol Not Configured** | Verify the symbol you expect to trade is in symbols list | Add symbol to configuration or check symbol name spelling |
| **Data Issues** | Check if market data is being processed correctly | Verify belief state values are reasonable |
| **Timing Issues** | Check if you're looking at the right time window | Wait for system to process enough data cycles |

#### Diagnostic Commands
```bash
# Check current signal generation parameters
grep -A5 -B5 "signal_generation" config/learning_high_wr.yaml

# Look for belief state updates in logs
grep -i "belief_state\|expected_return" logs/system.log | head -10

# Check what symbols are configured
grep -i "symbols" config/learning_high_wr.yaml

# Create a simple test to verify signal generation logic
python -c "
import sys
sys.path.append('.')
from decision.signal_generator import SignalGenerator
from perception.belief_state import BeliefState

# Create signal generator with default config
signal_gen = SignalGenerator()

# Create a test belief state that should generate a signal
belief_state = BeliefState(
    expected_return=0.005,
    expected_return_uncertainty=0.001,
    aleatoric_uncertainty=0.01,
    epistemic_uncertainty=0.008,
    regime_probabilities=[0.1]*8,
    microstructure_features={'ofI': 0.5, 'I_star': 0.3},
    volatility_estimate=0.15,
    liquidity_estimate=0.6,
    momentum_signal=0.1,
    volume_signal=0.05,
    timestamp=1234567890,
    confidence=0.8
)

# Try to generate a signal
signals = signal_gen.generate_signals(belief_state, 'BTC/USDT')
print(f'Generated {len(signals)} signals')
if signals:
    s = signals[0]
    print(f'Signal: {s.action} {s.quantity} {s.symbol} @ conf={s.confidence:.3f}')
else:
    print('No signals generated - checking why...')
    print(f'Confidence: {belief_state.confidence} (threshold: {signal_gen.min_confidence_threshold})')
    print(f'Expected return: {belief_state.expected_return} (threshold: {signal_gen.min_expected_return})')
    uncertainty = belief_state.aleatoric_uncertainty + belief_state.epistemic_uncertainty
    print(f'Total uncertainty: {uncertainty} (range: {signal_gen.min_uncertainty}-{signal_gen.max_uncertainty}')
"
```

### Poor Performance or Losses

#### Symptoms
- System is losing money consistently
- Win rate is unacceptably low
- Expectancy is negative or too low
- Drawdowns are excessive

#### Possible Causes and Solutions

| Cause | Diagnosis | Solution |
|-------|-----------|----------|
| **Incorrect Thresholds** | Signal quality filters too loose or tight | Adjust confidence, expected return, and uncertainty thresholds |
| **Feature Engineering Issues** | Microstructure features not predictive for your market | Examine which features are most/least correlated with returns |
| **Regime Mismatch** | System not adapting correctly to market regimes | Check regime detection and probability estimation |
| **Execution Problems** | Poor execution eating into profits | Examine slippage, latency, and fill rates |
| **Risk Management Too Tight** | Position sizing too small or limits too restrictive | Review position sizing and risk limits |
| **Learning Not Working** | Aggression controller not adapting properly | Check execution feedback and learning parameters |
| **Market Condition Changes** | System not adapting to changing markets | Check concept drift detection and adaptation triggers |
| **Data Quality Issues** | Garbage in, garbage out | Verify market data quality and completeness |

#### Diagnostic Commands
```bash
# Check performance metrics
curl -s http://localhost:9090/metrics | grep -E "pnl|expectancy|win_rate|sharpe"

# Check recent trades and their outcomes
tail -f logs/trading_system.log | grep -i "trade\|executed\|filled"

# Check belief state quality over time
grep -i "belief_state\|confidence\|expected_return" logs/system.log | tail -20

# Check risk assessments
grep -i "risk_level\|risk_score\|protective_action" logs/system.log | tail -10

# Check execution quality
grep -i "slippage\|latency\|market_impact\|filled_quantity" logs/trading_system.log | tail -10

# Create a performance analysis script
cat > /tmp/check_perf.py << 'EOF'
import sys
sys.path.append('.')
from collections import defaultdict
import re
import json

# Parse trading log for performance metrics
trades = []
with open('logs/trading_system.log', 'r') as f:
    for line in f:
        if 'TRADE' in line:
            # Extract trade information from log line
            # This is a simplified example - adjust based on actual log format
            if 'BUY' in line or 'SELL' in line:
                trades.append(line.strip())

print(f'Found {len(trades)} trade log entries')

# Calculate basic statistics if we have enough data
if len(trades) > 5:
    print('Sufficient data for basic analysis')
else:
    print('Limited data available - may need more time for meaningful statistics')
EOF
python /tmp/check_perf.py
rm /tmp/check_perf.py
```

### System Hanging or Unresponsive

#### Symptoms
- System appears to freeze or stop responding
- No new log entries for extended period
- Health checks may fail or timeout
- CPU usage may be at 100% or 0%

#### Possible Causes and Solutions

| Cause | Diagnosis | Solution |
|-------|-----------|----------|
| **Infinite Loop** | CPU at 100%, no progress in logs | Look for unbounded loops in code |
| **Deadlock** | CPU at 0%, threads waiting on each other | Check threading and asyncio usage |
| **External Blocking** | Waiting on network, file I/O, or external service | Check exchange connectivity, alerting services |
| **Resource Exhaustion** | Out of memory, file descriptors, etc. | Check system resource usage |
| **Exception Handling** | Uncaught exception causing silent failure | Check logs for exceptions before hanging |
| **Configuration Issue** | Invalid setting causing unexpected behavior | Review recent configuration changes |

#### Diagnostic Commands
```bash
# Check system resource usage
ps aux | grep python
top -b -n 1 | grep python

# Check thread states (if core dump available)
# Or check what the process is doing
python -c "
import psutil
import sys

# Find python processes related to our system
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if 'python' in proc.info['name'].lower() and any('trading' in arg.lower() for arg in proc.info['cmdline']):
            print(f'PID: {proc.info[\"pid\"]}')
            print(f'Command: {\" \".join(proc.info[\"cmdline\"])}')
            print(f'Status: {proc.status()}')
            print(f'CPU: {proc.cpu_percent()}%')
            print(f'Memory: {proc.memory_info().rss / 1024 / 1024:.2f} MB')
            print(f'Threads: {proc.num_threads()}')
            print('---')
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
"

# Check recent log entries before the hang
tail -n 50 logs/system.log

# Try to kill and restart if needed
# pkill -f "continuous_trading_loop"  # Uncomment if needed
# sleep 2
# ./start_system.sh &  # Uncomment if needed
```

### Alerting Not Working

#### Symptoms
- Not receiving expected alerts
- Alerts arriving when they shouldn't
- Alert formatting issues

#### Possible Causes and Solutions

| Cause | Diagnosis | Solution |
|-------|-----------|----------|
| **Misconfiguration** | Alerting not properly configured | Check `.env` file and alerting configuration |
| **Rate Limiting** | Alerts being blocked by rate limiter | Check alert rate and limits |
| **Channel Issues** | Problems with specific alert channels (Telegram, email, etc.) | Test each channel individually |
| **Template Problems** | Alert message formatting errors | Check alert templates and available data |
| **Permission Issues** | Lack of permissions to send alerts | Check API keys, tokens, and service permissions |
| **Network Issues** | Cannot reach alerting service | Check network connectivity and firewall settings |

#### Diagnostic Commands
```bash
# Check alerting configuration
cat .env | grep -i "telegram\|alert"
grep -A10 -B5 "alerting" config/learning_high_wr.yaml

# Check if alert manager is initializing correctly
python -c "
import sys
sys.path.append('.')
from observability.alerting import AlertManager, create_trading_alert

try:
    manager = AlertManager.get_instance()
    print('Alert manager initialized successfully')
    
    # Test creating an alert
    alert = create_trading_alert(
        title='Test Alert',
        message='This is a test alert',
        severity=2  # WARNING
    )
    print(f'Alert created: {alert.title} - {alert.message}')
    
    # Check what channels are configured
    print(f'Configured channels: {list(manager.handlers.keys())}')
    
except Exception as e:
    print(f'Alert manager initialization failed: {e}')
    import traceback
    traceback.print_exc()
"

# Test alert sending (use with caution in production)
# python -c "
# import sys
# import asyncio
# sys.path.append('.')
# from observability.alerting import send_trade_execution_alert
#
# async def test_alert():
#     await send_trade_execution_alert(
#         symbol='BTC/USDT',
#         side='BUY',
#         quantity=0.001,
#         price=50000.0,
#         success=True
#     )
#     print('Test alert sent')
#
# asyncio.run(test_alert())
# "
```

### High Resource Usage

#### Symptoms
- System using excessive CPU, memory, disk, or network
- Other applications affected by resource consumption
- System becoming slow or unresponsive over time

#### Possible Causes and Solutions

| Cause | Diagnosis | Solution |
|-------|-----------|----------|
| **Logging Too Verbose** | DEBUG level generating too much log data | Increase logging level to INFO or WARN |
| **History Too Large** | Unbounded growth in data structures | Check history limits and cleanup procedures |
| **Inefficient Algorithms** | O(n²) or worse algorithms in hot paths | Profile code to find bottlenecks |
| **Memory Leaks** | Memory growing continuously over time | Monitor memory usage over extended periods |
| **Excessive Frequency** | System running too frequently for the task | Increase cycle interval or add throttling |
| **Duplicate Work** | Same work being done multiple times | Check for redundant computations |
| **I/O Bottlenecks** | Slow disk or network operations | Check I/O wait times and consider buffering/async |

#### Diagnostic Commands
```bash
# Monitor resource usage over time
cat > /tmp/monitor_resources.py << 'EOF'
import time
import psutil
import sys

def get_trading_processes():
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python' in proc.info['name'].lower() and any('trading' in arg.lower() for arg in proc.info['cmdline']):
                processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return processes

print("Monitoring resource usage (press Ctrl+C to stop)...")
try:
    while True:
        processes = get_trading_processes()
        if not processes:
            print("No trading processes found")
            time.sleep(5)
            continue
            
        total_cpu = 0.0
        total_memory = 0.0
        for proc in processes:
            try:
                cpu = proc.cpu_percent()
                memory = proc.memory_info().rss / 1024 / 1024  # MB
                total_cpu += cpu
                total_memory += memory
                print(f"PID {proc.info['pid']}: CPU {cpu:.1f}%, Memory {memory:.1f} MB")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        print(f"TOTAL: CPU {total_cpu:.1f}%, Memory {total_memory:.1f} MB")
        print("-" * 40)
        time.sleep(5)
except KeyboardInterrupt:
    print("\\nMonitoring stopped")
EOF
python /tmp/monitor_resources.py
rm /tmp/monitor_resources.py
```

### Data or State Corruption

#### Symptoms
- System behaving inconsistently with its inputs
- Impossible state combinations observed
- Data appearing corrupted or incorrectly formatted
- Recovery from restart not working as expected

#### Possible Causes and Solutions

| Cause | Diagnosis | Solution |
|-------|-----------|----------|
| **Race Conditions** | Inconsistent state due to concurrent access | Review threading and asyncio usage |
| **Invalid State Transitions** | Moving between states that shouldn't be possible | Add state validation and transition checking |
| **Data Corruption** | Data becoming corrupted during processing or storage | Add data validation and checksums |
| **Serialization Issues** | Problems converting between formats | Check serialization/deserialization logic |
| **Initializer Issues** | Objects not being initialized correctly | Review constructors and factory methods |
| **Boundary Condition Errors** | Errors at edges of valid ranges | Add boundary checking and testing |
| **Memory Corruption** | Rare but possible memory issues | Run memory tests and consider restarting |

#### Diagnostic Commands
```bash
# Check belief state validity
python -c "
import sys
sys.path.append('.')
from perception.belief_state import BeliefState

# Test valid belief state creation
try:
    bs = BeliefState(
        expected_return=0.001,
        expected_return_uncertainty=0.0005,
        aleatoric_uncertainty=0.001,
        epistemic_uncertainty=0.0008,
        regime_probabilities=[0.125]*8,
        microstructure_features={'ofI': 0.0, 'I_star': 0.0},
        volatility_estimate=0.15,
        liquidity_estimate=0.6,
        momentum_signal=0.0,
        volume_signal=0.0,
        timestamp=1234567890,
        confidence=0.7
    )
    print('Valid belief state created')
    print(f'Confidence: {bs.confidence}')
    print(f'Regime probs sum: {sum(bs.regime_probabilities):.6f}')
    
    # Test invalid belief state (should still be created but may be problematic)
    bs_invalid = BeliefState(
        expected_return=2.0,  # Unrealistic return
        expected_return_uncertainty=-0.1,  # Negative uncertainty (invalid)
        regime_probabilities=[0.2, 0.3, 0.4, 0.2],  # Only 4 probs instead of 8
        confidence=1.5  # Confidence > 1 (invalid)
    )
    print('\\nInvalid belief state created (as expected)')
    print(f'Expected return: {bs_invalid.expected_return}')
    print(f'Expected return uncertainty: {bs_invalid.expected_return_uncertainty}')
    print(f'Regime probs count: {len(bs_invalid.regime_probabilities)}')
    print(f'Confidence: {bs_invalid.confidence}')
except Exception as e:
    print(f'Error creating belief state: {e}')
    import traceback
    traceback.print_exc()
"

# Check trade journal validity (if it exists)
if os.path.exists('logs/trade_journal.json'):
    print('\\nChecking trade journal...')
    try:
        with open('logs/trade_journal.json', 'r') as f:
            data = json.load(f)
            print(f'Trade journal has {len(data) if isinstance(data, list) else 1} entries')
            if isinstance(data, list) and len(data) > 0:
                first = data[0]
                print(f'First entry keys: {list(first.keys()) if isinstance(first, dict) else \"Not a dict\"}')
    except Exception as e:
        print(f'Error reading trade journal: {e}')
else:
    print('\\nTrade journal file not found yet')
"

# Check log file integrity
if os.path.exists('logs/system.log'):
    print('\\nChecking system log...')
    try:
        with open('logs/system.log', 'r') as f:
            lines = f.readlines()
            print(f'System log has {len(lines)} lines')
            if len(lines) > 0:
                print(f'First line: {lines[0][:100]}...')
                print(f'Last line: {lines[-1][-100:]}...')
    except Exception as e:
        print(f'Error reading system log: {e}')
else:
    print('\\nSystem log file not found')
"
```

### Configuration Issues

#### Symptoms
- System not behaving as expected based on configuration
- Configuration changes not taking effect
- Confusing or contradictory behavior

#### Possible Causes and Solutions

| Cause | Diagnosis | Solution |
|-------|-----------|----------|
| **Wrong Configuration File** | Loading unexpected configuration file | Check which file is actually being loaded |
| **Caching Issues** | Old configuration being cached | Restart system after configuration changes |
| **Override Conflicts** | Environment variables or other sources overriding file config | Check override precedence and sources |
| **Type Conversion Issues** | Values being interpreted as wrong type | Check value types in configuration files |
| **Path Issues** | Looking for configuration in wrong directory | Verify configuration directory path |
| **Syntax Errors** | Invalid YAML or JSON preventing parsing | Validate configuration file syntax |
| **Reference Issues** | Referencing non-existent sections or keys | Check configuration structure and references |

#### Diagnostic Commands
```bash
# Check what configuration is actually being loaded
python -c "
import sys
sys.path.append('.')
from config.config_manager import ConfigManager
import os

config_dir = 'config'
config_manager = ConfigManager(config_dir)

# Try loading different configurations
configs_to_try = ['unified', 'learning_high_wr', 'learning']
for config_name in configs_to_try:
    try:
        config = config_manager.load_config(config_name)
        print(f'Successfully loaded {config_name}')
        # Show a few key values to verify
        env = config_manager.get_config_value(config, 'system.environment', 'NOT_FOUND')
        cycle_int = config_manager.get_config_value(config, 'execution.cycle_interval', 'NOT_FOUND')
        conf_thresh = config_manager.get_config_value(config, 'decision.signal_generation.min_confidence_threshold', 'NOT_FOUND')
        print(f'  Environment: {env}')
        print(f'  Cycle interval: {cycle_int}')
        print(f'  Confidence threshold: {conf_thresh}')
    except Exception as e:
        print(f'Failed to load {config_name}: {e}')
"

# Check for override sources
cat .env 2>/dev/null || echo "No .env file found"
echo "---"
env | grep -i "trading\|signal\|risk\|exec\|monit\|alert" || echo "No relevant environment variables found"

# Validate configuration syntax
python -c "
import yaml
import sys
import os

config_dir = 'config'
print('Checking YAML syntax in configuration files...')
all_good = True

for filename in os.listdir(config_dir):
    if filename.endswith('.yaml') or filename.endswith('.yml'):
        filepath = os.path.join(config_dir, filename)
        try:
            with open(filepath, 'r') as f:
                yaml.safe_load(f)
            print(f'✓ {filename}: Valid YAML')
        except yaml.YAMLError as e:
            print(f'✗ {filename}: Invalid YAML - {e}')
            all_good = False
        except Exception as e:
            print(f'✗ {filename}: Error reading file - {e}')
            all_good = False

if all_good:
    print('\\nAll configuration files have valid YAML syntax')
else:
    print('\\nSome configuration files have YAML syntax errors')
    sys.exit(1)
"
```

## Advanced Troubleshooting

### Enabling Debug Mode

To get more detailed information for troubleshooting:

1. **Increase Logging Level**
   ```bash
   # In .env file or environment
   LOG_LEVEL=DEBUG
   
   # Or in config file
   monitoring:
     logging:
       level: DEBUG
   ```

2. **Enable Specific Component Debugging**
   ```bash
   # Add debug flags to specific components if available
   # Or modify logging configuration to include specific loggers
   ```

3. **Use Python Debugging Tools**
   ```bash
   # Start with debugging enabled
   python -m pdb continuous_trading_loop.py
   
   # Or use IDE debugging
   # Or add breakpoint() calls in code
   ```

### Profiling Performance

To identify performance bottlenecks:

1. **CPU Profiling**
   ```bash
   # Using cProfile
   python -m cProfile -s cumulative continuous_trading_loop.py
   
   # Using line_profiler (if installed)
   kernprof -l -v continuous_trading_loop.py
   ```

2. **Memory Profiling**
   ```bash
   # Using memory_profiler
   mprof run continuous_trading_loop.py
   mprof plot
   
   # Using objgraph or similar
   ```

3. **I/O Profiling**
   ```bash
   # Check what files are being accessed
   lsof -p <pid>
   
   # Monitor disk I/O
   iostat -xz 1
   ```

### Analyzing Logs for Patterns

1. **Time Series Analysis**
   ```bash
   # Extract timestamps and events for analysis
   grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}' logs/system.log | head -5
   
   # Count events by hour
   grep -oE '[0-9]{2}:[0-9]{2}:[0-9]{2}' logs/system.log | cut -d: -f1 | sort | uniq -c | sort -nr
   ```

2. **Event Correlation**
   ```bash
   # Find sequences of events
   grep -B2 -A2 "signal_generated" logs/system.log | head -20
   
   # Look for patterns before and after events
   grep -B5 -A5 "ORDER_FILLED" logs/system.log | head -30
   ```

### Creating Minimal Reproducible Examples

When reporting issues, create a minimal example that reproduces the problem:

1. **Isolate the Component**
   - Identify which layer or component is responsible
   - Create a test that uses only that component

2. **Use Simulated Data**
   - Replace real market data with simulated or fixed data
   - Remove external dependencies

3. **Reduce Complexity**
   - Remove unnecessary features or functionality
   - Focus on the specific problematic behavior

4. **Provide Clear Instructions**
   - Document exactly how to reproduce the issue
   - Include expected vs actual behavior
   - List environment and version information

#### Example Minimal Reproducible Issue Report
```
Issue: Signal generation not working for high confidence beliefs

Environment:
- Python 3.9.5
- Unified Trading System commit abc123
- Linux Ubuntu 20.04

Steps to Reproduce:
1. Start system with default configuration
2. Wait for belief state with confidence > 0.8 to be generated
3. Observe that no signal is generated despite high confidence

Expected Behavior:
Signal should be generated when confidence > min_confidence_threshold (0.45)

Actual Behavior:
No signal generated even with confidence = 0.92

Minimal Test Case:
```python
import sys
sys.path.append('.')
from perception.belief_state import BeliefState
from decision.signal_generator import SignalGenerator

# Create components
signal_gen = SignalGenerator()

# Create belief state that should definitely generate a signal
belief_state = BeliefState(
    expected_return=0.01,
    expected_return_uncertainty=0.001,
    aleatoric_uncertainty=0.001,
    epistemic_uncertainty=0.001,
    regime_probabilities=[0.125]*8,
    microstructure_features={'ofI': 0.0, 'I_star': 0.0},
    volatility_estimate=0.1,
    liquidity_estimate=0.9,
    momentum_signal=0.0,
    volume_signal=0.0,
    timestamp=1234567890,
    confidence=0.92  # Well above threshold of 0.45
)

# Try to generate signal
signals = signal_gen.generate_signals(belief_state, 'TEST/USDT')
print(f'Generated {len(signals)} signals')

# Expected: 1 signal
# Actual: 0 signals (the bug)
```

Additional Information:
- Belief state entropy: [calculated value]
- Market regime: [detected regime]
- Current timestamp: [time]
- Workaround: Temporarily lowering min_confidence_threshold to 0.1 makes it work
```

## When to Seek Help

Contact the development team or consult the community when:

1. **You've exhausted the troubleshooting steps above**
2. **The issue involves core system functionality you cannot safely modify**
3. **You suspect a bug in the core algorithms or architecture**
4. **The issue persists across multiple environments and configurations**
5. **You need clarification on intended behavior or design decisions**
6. **You want to suggest improvements or new features**

### Information to Include When Seeking Help

When asking for help, please include:

1. **Clear Problem Description**
   - What you expected to happen
   - What actually happened
   - Steps to reproduce the issue

2. **Environment Information**
   - System version and commit hash
   - Python version and platform
   - Relevant configuration files (with secrets removed)
   - Environment variables (with secrets removed)

3. **Diagnostic Information**
   - Logs from around the time of the issue
   - Metrics snapshots if available
   - Health check results
   - Any error messages or exception traces
   - Resource usage information

4. **What You've Already Tried**
   - Troubleshooting steps you've attempted
   - Configuration changes you've tried
   - Workarounds you've discovered
   - Why those attempts didn't resolve the issue

5. **Expected Resolution**
   - What you consider an acceptable solution
   - Any constraints or requirements for the fix
   - Preferred timeline for resolution

Following this troubleshooting guide should help you resolve most issues you encounter with the Unified Trading System. Remember to always start with the simplest explanations and work your way up to more complex issues.