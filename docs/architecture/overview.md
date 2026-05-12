# System Architecture Overview

This document provides a comprehensive view of the Unified Trading System's architecture, covering its layered design, communication patterns, data flow, and deployment considerations.

## Architectural Philosophy

The Unified Trading System follows a **layered microservices architecture** with clear separation of concerns, designed to:

1. **Isolate Concerns**: Each layer has a single, well-defined responsibility
2. **Enable Independent Development**: Teams can work on different layers simultaneously
3. **Facilitate Testing**: Layers can be tested in isolation with mocks
4. **Support Evolution**: Layers can be updated or replaced without affecting others
5. **Provide Observability**: Each layer emits telemetry for monitoring and debugging

## The Six-Layer Architecture

### 1. Perception Layer
**Purpose**: Transform raw market data into structured belief states

**Responsibilities**:
- Market data ingestion and normalization
- Microstructure feature extraction (OFI, I*, L*, S*)
- Regime detection and probability estimation
- Belief state formation and publishing
- Data validation and quality checking

**Key Components**:
- `BeliefStateEstimator`: Updates belief states using market data
- `Microstructure Feature Engine`: Computes OFI, I*, L*, S* and other features
- `Regime Detector`: Estimates probabilities over 8 market regimes
- `Market Data Factory`: Normalizes data from different sources
- `Event System`: Publishes structured events for loose coupling

**Outputs**: 
- Belief State events containing expected return, uncertainties, regime probabilities, and microstructure features
- Market data quality events
- Feature computation events

### 2. Decision Layer
**Purpose**: Convert belief states into actionable trading signals

**Responsibilities**:
- Signal generation from belief states
- Quality filtering and validation
- Aggression level management
- Signal strength and position sizing calculation
- Signal publishing for downstream consumption

**Key Components**:
- `SignalGenerator`: Filters belief states based on quality criteria
- `AggressionController`: Lyapunov-stable adaptation of trading intensity
- `Signal Quality Assessor`: Multi-uncertainty model evaluation
- `Position Sizing Engine`: Determines appropriate trade sizes
- `Signal Publisher`: Emits trading signals to risk layer

**Inputs**: 
- Belief State events from perception layer
- Aggression feedback from execution layer
- Configuration parameters for filtering and sizing

**Outputs**:
- Trading Signal events containing symbol, action, quantity, confidence, expected return
- Signal rejection events with reasons
- Signal quality metrics

### 3. Risk Layer
**Purpose**: Validate signals against portfolio risk constraints and apply protective actions

**Responsibilities**:
- Risk assessment of proposed signals
- Portfolio risk monitoring and management
- Protective action determination (reduce size, halt trading, etc.)
- Risk limit enforcement and breach response
- Risk attribution and monitoring

**Key Components**:
- `Unified Risk Manifold`: Nonlinear risk computation engine
- `Risk Assessment Engine`: Evaluates signals against current portfolio state
- `Protective Action Determiner`: Selects appropriate responses to risk
- `Risk Limit Enforcer`: Automatically enforces position and loss limits
- `Risk Attribution Engine`: Breaks down risk contributions by factor

**Inputs**:
- Trading Signal events from decision layer
- Portfolio state (positions, P&L, leverage)
- Market data for context
- Risk limit configurations

**Outputs**:
- Approved Execution Intent events (signals that pass risk checks)
- Risk rejection events with protective actions
- Risk assessment events with detailed factor breakdowns
- Risk limit breach alerts

### 4. Execution Layer
**Purpose**: Convert approved intents into executed orders

**Responsibilities**:
- Execution planning based on market conditions
- Order type, timing, and venue selection
- Order lifecycle management (submit, track, fill, cancel)
- Execution simulation and realistic modeling
- Execution feedback for learning and adaptation

**Key Components**:
- `Smart Order Router`: Plans optimal execution strategies
- `Execution Model`: Simulates and predicts execution outcomes
- `Order Manager`: Tracks order lifecycle and handles events
- `Execution Simulator`: Models realistic exchange behavior
- `Feedback Engine`: Extracts learning signals from execution results

**Inputs**:
- Approved Execution Intent events from risk layer
- Market data for execution planning
- Execution feedback from prior trades
- Configuration for execution parameters

**Outputs**:
- Execution Result events showing order outcomes
- Execution feedback signals for aggression controller
- Order lifecycle events (submitted, filled, cancelled, rejected)
- Execution quality metrics (slippage, latency, market impact)

### 5. Feedback Layer
**Purpose**: Monitor performance, extract learning insights, and drive system adaptation

**Responsibilities**:
- Profit and loss attribution and tracking
- Trade classification and labeling
- Performance metric calculation and reporting
- Learning insight generation and pattern recognition
- Concept drift detection and adaptation triggering
- System reliability and error tracking

**Key Components**:
- `PNL Engine`: Tracks realized and unrealized profit and loss
- `Learning Insights Engine`: Identifies patterns in trade outcomes
- `SRE Metrics Engine`: Monitors system reliability and performance
- `Adaptation Engine`: Detects concept drift and model degradation
- `Attribution Engines`: Break down performance by various dimensions
- `Feedback Publisher`: Emits learning signals and metrics

**Inputs**:
- Trade results (entry/exit prices, commissions, timing)
- Position data (current holdings and values)
- Market data (for context and marking-to-market)
- Belief states and execution results (for learning)
- Error events and system health data
- Model information and feature importance data

**Outputs**:
- Performance metric events (P&L, win rate, Sharpe ratio, etc.)
- Learning insight events (patterns, anomalies, recommendations)
- Adaptation trigger events (when concept drift is detected)
- System reliability events (error rates, latency, resource usage)
- Feedback signals for aggression controller and other learners

### 6. Observability Layer
**Purpose**: Provide complete system visibility for monitoring, debugging, and optimization

**Responsibilities**:
- Structured logging with correlation IDs and context
- Prometheus-compatible metrics collection and exposition
- Health checking and system status reporting
- Multi-channel alerting with rate limiting and priority routing
- Debugging and profiling support
- Audit trail and compliance support

**Key Components**:
- `Structured Logger`: JSON-formatted logging with enrichment
- `Metrics Collector`: Prometheus-compatible metric types and collection
- `Health Checker`: HTTP-based health monitoring and aggregation
- `Alert Manager`: Multi-channel alerting with deduplication and routing
- `Correlation ID Manager`: Request tracing across system boundaries
- `Context Propagator`: Automatic enrichment of log entries with context

**Inputs**:
- Log requests from all system layers
- Metric increment/setting requests from all layers
- Health check requests from internal components
- Alert requests from all layers
- System events and state changes
- Environmental and deployment information

**Outputs**:
- Structured JSON logs to files and external systems
- Prometheus-formatted metrics on HTTP endpoint
- Health status JSON on HTTP endpoint
- Alert notifications via configured channels (Telegram, email, etc.)
- Debugging and profiling information
- Audit trails and compliance reports

## Data Flow Through the System

```
Market Data Ingestion
         ↓
[Perception Layer] ───▶ Belief State (expected return, uncertainties, regimes, features)
         ↓
[Decision Layer] ───▶ Trading Signal (symbol, action, quantity, confidence, expected return)
         ↓
[Risk Layer] ───▶ Approved Execution Intent (risk-validated intent)
         ↓
[Execution Layer] ───▶ Execution Result (order status, fill quantity, price, slippage, latency)
         ↓
[Feedback Layer] ───▶ Performance Metrics, Learning Insights, Adaptation Triggers
         ↓
[Observability Layer] ───▶ Logs, Metrics, Health Status, Alerts
         ↕
           Configuration Updates & Operational Commands
```

## Communication Patterns

### 1. Direct Method Calls (Synchronous)
Used for tight coupling where immediate response is needed:
- Layer-to-layer calls within a single trading cycle
- Configuration access and validation
- Factory and utility function calls

### 2. Event-Based Communication (Asynchronous)
Used for loose coupling and extensibility:
- Perception layer publishes market data and belief state events
- Decision layer publishes signal events
- Risk layer publishes intent and rejection events
- Execution layer publishes order lifecycle events
- Feedback layer publishes performance and learning events
- Observability layer consumes events for logging and metrics

### 3. Configuration-Driven Behavior
Used to modify system behavior without code changes:
- All layers read configuration at startup and on reload
- Strategy selection via configuration parameters
- Threshold and limit adjustments via configuration
- Feature toggles and experimental flags

### 4. Shared State and Data Stores
Used for persistent information and cross-cutting concerns:
- Trade journal for persistent trade history
- Log files for systematic event recording
- Metrics storage for time-series data
- Configuration files for system parameters
- Environment variables for deployment-specific settings

## Deployment Architecture

### Single Instance Deployment
The standard deployment runs as a single process containing all layers:
```
┌─────────────────┐
│   Trading       │
│   System        │
│   (Single      │
│    Process)     │
│                 │
├─────────────────┤
│ Perception      │
│ Decision        │
│ Risk            │
│ Execution       │
│ Feedback        │
│ Observability   │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ External Systems│
│ - Exchanges     │
│ - Data Feeds    │
│ - Alert Systems │
│ - Monitoring    │
└─────────────────┘
```

### Multiple Instance Deployment
For running multiple strategies or portfolios:
```
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ Strategy A      │   │ Strategy B      │   │ Strategy C      │
│ Trading System  │   │ Trading System  │   │ Trading System  │
└─────────────────┘   └─────────────────┘   └─────────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────┐
│ Shared Infrastructure                               │
│ - Data Feeds (can be shared or separate)           │
│ - Exchange Connections (typically separate)       │
│ - Monitoring Systems (shared)                     │
│ - Alerting Systems (shared)                       │
└───────────────────────────────────────────────────┘
```

## Scaling Considerations

### Vertical Scaling (Within Instance)
- Increase CPU/memory allocation for higher frequency trading
- Optimize data structures and algorithms for performance
- Tune asyncio settings for I/O bound operations
- Adjust garbage collection and memory management

### Horizontal Scaling (Across Instances)
- Run multiple instances for different strategies/portfolios
- Share data feeds where appropriate (market data is often broadcast)
- Use separate exchange connections to avoid rate limiting
- Share monitoring and alerting infrastructure
- Coordinate via external systems if inter-instance communication needed

### Data and State Considerations
- Each instance maintains its own belief states, positions, and P&L
- Market data can be shared via multicast or separate connections
- Trade journals and logs are instance-specific
- Configuration can be shared or instance-specific
- No shared state between instances by design (reduces coupling)

## Technology Stack and Dependencies

### Core Dependencies
- **Python 3.8+**: Primary implementation language
- **asyncio**: Asynchronous I/O for high-performance networking
- **NumPy**: Numerical computations for mathematical models
- **PyYAML**: Configuration file handling
- **aiohttp**: Asynchronous HTTP client for alerting and APIs
- **prometheus_client**: Metrics exposition (with fallback mocks)

### Development and Testing Dependencies
- **pytest**: Testing framework
- **pytest-asyncio**: Asynchronous test support
- **black**: Code formatting
- **flake8**: Linting and style checking
- **mypy**: Static type checking

### Optional/Environment-Dependent
- **python-dotenv**: Environment variable loading from .env files
- **psutil**: System resource monitoring (for enhanced health checks)
- **APScheduler**: Scheduled task execution (if needed)
- **redis**: Caching and shared state (if extending for shared components)

## Key Architectural Decisions and Trade-offs

### 1. Layered vs Microservices
**Chosen**: Layered architecture within single process
**Why**: 
- Lower latency between layers (in-process calls vs network)
- Simpler deployment and debugging
- Stronger consistency guarantees
- Easier testing and development
**Trade-off**: 
- Less independent scalability of layers
- Single point of failure (mitigated by robust error handling)

### 2. Event-Based vs Direct Calls
**Chosen**: Hybrid approach
- Direct calls for synchronous trading cycle flow
- Events for asynchronous monitoring, logging, and observability
**Why**: 
- Performance for critical path
- Loose coupling for observability and extensibility
- Simplicity for core trading logic

### 3. Centralized vs Distributed Configuration
**Chosen**: Centralized with environment overrides
**Why**: 
- Consistent behavior across instances
- Easy version control and change management
- Simple rollback and comparison
**Trade-off**: 
- Requires instance restart for most changes
- Some parameters could benefit from hot-reloading

### 4. Monolithic Observability vs Separate Services
**Chosen**: Embedded observability layer
**Why**: 
- Guaranteed availability (if trading system runs, observability runs)
- Simplified deployment and configuration
- Consistent data collection and formatting
**Trade-off**: 
- Consumes resources from main trading process
- Less flexible scaling of observability independently
- Potential impact on trading performance if observability overloaded

## Extension Points and Customization

### 1. Perception Layer Extensions
- Add new microstructure features or alternative data sources
- Implement different regime detection methodologies
- Add alternative belief state estimation approaches
- Enhance data validation and quality checking

### 2. Decision Layer Extensions
- Add alternative signal generation algorithms
- Implement different quality scoring models
- Add new position sizing strategies
- Implement alternative aggression control algorithms

### 3. Risk Layer Extensions
- Add new risk factors or alternative risk models
- Implement different protective action strategies
- Add custom limit types or dynamic limit adjustments
- Implement alternative attribution models for risk

### 4. Execution Layer Extensions
- Add new order types or execution algorithms
- Implement alternative venue selection or routing strategies
- Add custom slippage or latency models
- Implement different simulation fidelities

### 5. Feedback Layer Extensions
- Add new performance attribution dimensions
- Implement alternative learning algorithms
- Add new concept drift detection methods
- Implement different feedback signals for various learners

### 6. Observability Layer Extensions
- Add new logging formats or output destinations
- Implement additional metric types or collection methods
- Add custom health checks for external dependencies
- Implement different alerting channels or routing logic

## Data Flow and Serialization Formats

### Internal Data Flow
All internal data flow uses Python objects with these characteristics:
- **Immutable where possible**: BeliefState, TradingSignal use dataclasses
- **Explicitly defined**: All fields and types are declared
- **Serialization capable**: All objects support to_dict()/from_dict() patterns
- **Version tolerant**: Designed to handle missing or extra fields gracefully

### Serialization Formats Used
1. **JSON**: 
   - Primary format for logs and external communication
   - Used in trade journal and structured logging
   - Human readable and widely supported

2. **YAML**:
   - Primary format for configuration files
   - Human readable and supports comments
   - Good for hierarchical data and comments

3. **Prometheus Format**:
   - Standard format for metrics exposition
   - Efficient for time-series data collection
   - Widely supported by monitoring systems

4. **Internal Python Objects**:
   - Used for all intra-process communication
   - Fastest option with no serialization overhead
   - Type safe when using dataclasses and type hints

## Security Considerations

### Authentication and Authorization
- **Internal**: No authentication between layers (trusted context)
- **External**: Depends on connected systems (exchanges, alert services)
- **Configuration**: Protected via file permissions and secret management
- **APIs**: Health and metrics endpoints should be protected in production

### Data Protection
- **At Rest**: Log files and configuration files should be protected by file permissions
- **In Transit**: External communications should use TLS/HTTPS where applicable
- **In Memory**: No special protection (assumes trusted execution environment)
- **Backups**: Should follow organizational data protection policies

### Audit and Compliance
- **Logging**: Complete audit trail of all significant actions
- **Metrics**: Quantitative record of system behavior and performance
- **Health Checks**: Record of system availability and reliability
- **Alerting**: Record of all notifications sent and reasons
- **Configuration**: Version-controlled history of all system parameters

## Failure Modes and Recovery

### Expected Failure Modes
1. **Network Issues**: Exchange connectivity problems
2. **Data Issues**: Corrupted or missing market data
3. **Resource Issues**: Memory, CPU, or disk exhaustion
4. **Logic Issues**: Software bugs or incorrect assumptions
5. **External Issues**: Exchange outages, regulatory changes, market halts

### Recovery Mechanisms
1. **Graceful Degradation**: Continue operation with reduced functionality
2. **Automatic Restart**: Self-healing through process restart
3. **State Reconstruction**: Rebuild state from logs and journals on restart
4. **Manual Intervention**: Operator intervention for unresolved issues
5. **Configuration Rollback**: Revert to known-good configuration

### Data Durability
- **Trade Journal**: Persistent record of all trades (append-only JSON)
- **Log Files**: Complete record of system activity (rotating file logs)
- **Configuration**: Version-controlled in repository
- **State Reconstruction**: Possible from trade journal and logs on restart

## Performance Characteristics

### Latency Profile
- **Market Data to Belief State**: <1ms (CPU-bound computation)
- **Belief State to Signal**: <0.1ms (simple filtering and calculations)
- **Signal to Risk Approval**: <0.1ms (rule-based checks)
- **Risk Approval to Execution Plan**: <0.1ms (simple calculations)
- **Execution Plan to Simulated Result**: <0.1ms (model-based prediction)
- **Full Cycle Time**: Configurable (default 30 seconds, can be reduced to seconds)

### Throughput Capabilities
- **Belief State Updates**: Limited by market data frequency (tick-by-tick or aggregated)
- **Signal Generation**: Proportional to belief state updates and complexity
- **Risk Assessment**: Negligible overhead (simple rule-based checks)
- **Execution Planning**: Very low overhead (formula-based calculations)
- **System Overhead**: Primarily determined by market data frequency and processing complexity

### Resource Utilization
- **CPU**: Primarily used for belief state computation and feature extraction
- **Memory**: Moderate, grows with history size (bounded by configuration)
- **I/O**: Primarily disk writes for logging and journaling
- **Network**: Determined by external data feeds and alert destinations