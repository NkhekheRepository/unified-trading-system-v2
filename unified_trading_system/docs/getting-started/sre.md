# Getting Started for SRE/DevOps

As an SRE or DevOps engineer, you'll focus on system reliability, monitoring, deployment, scaling, and operational aspects of the Unified Trading System.

## 30-Minute Quick Start

### Objective: Setup Monitoring, Observe System Health, and Practice Operational Procedures

#### Minutes 0-5: Setup and Initial Monitoring Configuration
```bash
# Clone and setup (if not done)
git clone [repository-url]
cd unified_trading_system
pip install -r requirements.txt

# Examine observability components
ls -la observability/
cat observability/logging.py | head -20
cat observability/metrics.py | head -20
cat observability/health.py | head -20
cat observability/alerting.py | head -20
```

#### Minutes 5-10: Start System with Monitoring Enabled
```bash
# Start the system (health and metrics servers start automatically)
./start_system.sh &

# Give it a moment to start all services
sleep 3

# Verify all services are running
ps aux | grep python | grep -v grep
```

#### Minutes 10-15: Check Health Endpoints
```bash
# Basic health check
curl -s http://localhost:8080/health | jq .

# Detailed health check
curl -s http://localhost:8080/health/json | jq .

# Check individual component health (example)
curl -s http://localhost:8080/health | jq -r '.components[] | select(.name == "executor") | .status'
```

#### Minutes 15-20: Examine Metrics and Logging
```bash
# Check that metrics are being served
curl -s http://localhost:9090/metrics | grep "trading_" | head -10

# Check structured logging
tail -f logs/system.log | head -5

# In another tab, force an error to see logging
# (In another session, you could trigger an error condition)
```

#### Minutes 20-25: Practice Alerting Configuration
```bash
# Check alerting configuration in environment
cat .env.example | grep -i "telegram\|alert"

# Look at alerting code to understand how it works
cat observability/alerting.py | grep -A10 -B5 "send_alert\|configure_alerting"
```

#### Minutes 25-30: Practice Operational Procedures
```bash
# Practice graceful shutdown
pkill -f "continuous_trading_loop"
# Wait a moment, then check logs for shutdown sequence
sleep 2
tail -n 20 logs/system.log

# Practice restart
./start_system.sh &

# Verify it came back up cleanly
curl -s http://localhost:8080/health | jq .status
```

### Key Operational Components to Explore

1. **Observability Stack**
   - **Logging**: `observability/logging.py` - Structured JSON logging with correlation IDs
   - **Metrics**: `observability/metrics.py` - Prometheus-compatible metrics collection
   - **Health Checks**: `observability/health.py` - HTTP-based health monitoring
   - **Alerting**: `observability/alerting.py` - Multi-channel alerting with rate limiting

2. **Deployment and Process Management**
   - **Startup Scripts**: `start_system.sh`, `start_trading.sh`
   - **Execution Scripts**: `run_continuous_loop.py`, `run_testnet.py`
   - **Configuration**: `config/` directory with environment-specific overrides

3. **Reliability Features**
   - Graceful startup and shutdown procedures
   - Error handling and recovery mechanisms
   - Rate limiting to prevent exchange bans
   - Circuit breaker patterns in external communications
   - Health checks for automatic failure detection

### Next Steps for SRE/DevOps Engineers

1. **Deepen Your Operational Understanding**
   - Read the [architecture overview](./architecture/overview.md) focusing on deployment and operations
   - Examine the observability stack in detail
   - Study the deployment scripts and configuration management

2. **Experiment with Operational Enhancements**
   - Add custom health checks for external dependencies
   - Implement advanced alert routing and suppression rules
   - Add chaos engineering experiments for failure injection
   - Implement blue-green deployment strategies
   - Add feature flagging capabilities for safe rollouts

3. **Build Production-Ready Operations**
   - Implement log aggregation and retention policies
   - Add dashboard integrations (Grafana, Kibana, etc.)
   - Implement automated scaling based on load metrics
   - Add security scanning and vulnerability management
   - Create runbooks for common operational procedures

4. **Establish Observability Best Practices**
   - Define service level objectives (SLOs) and service level indicators (SLIs)
   - Implement error budget tracking and alerting
   - Add distributed tracing for cross-service requests
   - Implement synthetic monitoring for user journey validation
   - Create comprehensive dashboards for different stakeholder views

### Quick Reference: Key Operational Files and Ports

#### Default Ports
| Service | Port | Purpose |
|---------|------|---------|
| Health Check Server | 8080 | HTTP endpoints for system and component health |
| Metrics Server | 9090 | Prometheus-formatted metrics for monitoring systems |
| Trade Journal | N/A | File-based JSON logs in `logs/trade_journal.json` |
| System Logs | N/A | Structured JSON logs in `logs/system.log` and logs/*.log |

#### Key Configuration for Operations
```yaml
# In config/learning_high_wr.yaml (monitoring section)
monitoring:
  health_check_port: 8081   # Change from default if needed
  metrics_port: 9091        # Change from default if needed
  log_level: INFO           # DEBUG, INFO, WARNING, ERROR
```

#### Key Observability Components

| Component | File | Purpose |
|-----------|------|---------|
| **Logging System** | `observability/logging.py` | Structured JSON logging, correlation IDs, trading-specific methods |
| **Metrics Collection** | `observability/metrics.py` | Prometheus-compatible metrics, system and trading metrics |
| **Health Monitoring** | `observability/health.py` | HTTP health endpoints, component health checks, aggregation |
| **Alerting System** | `observability/alerting.py` | Multi-channel alerting, rate limiting, priority routing, contextual intelligence |

#### Essential Operational Commands

| Command | Purpose |
|---------|---------|
| `./start_system.sh` | Start the complete trading system |
| `pkill -f "continuous_trading_loop"` | Gracefully stop the trading system |
| `tail -f logs/system.log` | Monitor system logs in real-time |
| `curl http://localhost:8080/health` | Check overall system health |
| `curl http://localhost:8080/health/json` | Get detailed component health |
| `curl http://localhost:9090/metrics` | Retrieve Prometheus metrics |
| `docker-compose up -d` | (If using Docker) Start all services |

### Common Operational Procedures

#### Starting the System
```bash
# Normal startup
./start_system.sh

# Start in background and disown
./start_system.sh &
disown

# Start with specific environment (if using env files)
ENV=production ./start_system.sh
```

#### Stopping the System
```bash
# Graceful shutdown (preferred)
pkill -f "continuous_trading_loop"

# Force stop (if needed)
pkill -9 -f "continuous_trading_loop"

# Check if stopped
ps aux | grep "[c]ontinuous_trading_loop"
```

#### Checking System Status
```bash
# Health endpoint (quick check)
curl -s http://localhost:8080/health | jq .status

# Detailed health (component level)
curl -s http://localhost:8080/health/json | jq '.components[] | {name: .name, status: .status.value}'

# Process check
ps aux | grep "[c]ontinuous_trading_loop" | grep -v grep

# Log monitoring (recent errors)
grep -i error logs/system.log | tail -10

# Performance metrics
curl -s http://localhost:9090/metrics | grep "pnl\|trade\|signal" | tail -10
```

#### Log Management
```bash
# View recent logs
tail -n 50 logs/system.log

# Follow logs in real-time
tail -f logs/system.log

# Search for specific events
grep "TRADE" logs/system.log | tail -10

# Check log sizes
du -h logs/*

# Rotate logs manually (if needed)
mv logs/system.log logs/system.log.$(date +%Y%m%d%H%M%T)
# System will create new log file on next write
```

#### Metrics Monitoring
```bash
# Get all trading-related metrics
curl -s http://localhost:9090/metrics | grep "trading_"

# Get P&L metrics
curl -s http://localhost:9090/metrics | grep "pnl"

# Get trading frequency metrics
curl -s http://localhost:9090/metrics | grep "trade\|signal"

# Get system metrics
curl -s http://localhost:9090/metrics | grep "system_"

# Get error metrics
curl -s http://localhost:9090/metrics | grep "error"
```

### Advanced Operational Topics

1. **High Availability Deployment**
   - Running multiple instances for different strategies/portfolios
   - Load balancing considerations (if applicable)
   - Failover and disaster recovery procedures
   - Data consistency and synchronization between instances

2. **Security Operations**
   - Secret management for API keys and credentials
   - Network security and firewall considerations
   - Audit logging and compliance requirements
   - Vulnerability scanning and patch management

3. **Performance Optimization**
   - Resource utilization monitoring and optimization
   - Bottleneck identification and resolution
   - Caching strategies for frequently accessed data
   - Database connection pooling and optimization

4. **Incident Response**
   - Alert routing and escalation procedures
   - Incident command structure and communication protocols
   - Post-mortem analysis and improvement tracking
   - Chaos engineering and failure injection testing
