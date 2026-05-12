# Mathematical Foundations

Complete mathematical specification of the Unified Trading System, combining LVR microstructure features with Autonomous System's POMDP formulation.

---

## 1. POMDP Belief State Formulation

### 1.1 State Space

The trading system implements a **Partially Observable Markov Decision Process (POMDP)** where the true market state `s ∈ S` is not directly observable.

Belief state `b(s)` is a probability distribution over hidden states:

```
b_{t}(s) = P(s_t = s | o_{1:t}, a_{1:t-1})
```

Where:
- `s ∈ S = {BULL_LOW_VOL, BULL_HIGH_VOL, BEAR_LOW_VOL, BEAR_HIGH_VOL, SIDEWAYS_LOW_VOL, SIDEWAYS_HIGH_VOL, CRISIS, RECOVERY}`
- `o` = market observation vector (prices, volumes, order book)
- `a` = action taken (BUY, SELL, HOLD)

### 1.2 Belief State Update (Bayesian Filter)

Implementation in `perception/belief_state.py:156`:

```
b_{t}(s') = η · O(o_t | s') · Σ_{s∈S} T(s' | s, a_{t-1}) · b_{t-1}(s)
```

Where:
- `η` = normalization constant
- `O(o|s')` = observation probability (likelihood)
- `T(s'|s,a)` = transition matrix (8×8), initialized in `belief_state.py:124`

**Regime Transition Matrix** (from `belief_state.py:124`):

```
T[i][j] = P(s_{t+1} = j | s_t = i)
```

Initial structure (8 regimes × 8 regimes):
```
BULL_LOW_VOL     → [0.90, 0.05, 0.02, 0.01, 0.01, 0.005, 0.003, 0.002]
BULL_HIGH_VOL    → [0.05, 0.85, 0.05, 0.02, 0.01, 0.01, 0.01, 0.01]
BEAR_LOW_VOL     → [0.02, 0.03, 0.88, 0.04, 0.02, 0.01, 0.01, 0.01]
BEAR_HIGH_VOL    → [0.01, 0.02, 0.05, 0.85, 0.03, 0.02, 0.01, 0.01]
SIDEWAYS_LOW_VOL → [0.01, 0.01, 0.02, 0.03, 0.90, 0.03, 0.005, 0.005]
SIDEWAYS_HIGH_VOL→ [0.01, 0.01, 0.02, 0.02, 0.05, 0.85, 0.03, 0.02]
CRISIS          → [0.001, 0.001, 0.01, 0.02, 0.01, 0.01, 0.90, 0.05]
RECOVERY        → [0.01, 0.02, 0.01, 0.01, 0.03, 0.02, 0.05, 0.85]
```

### 1.3 Belief State Data Structure

Defined in `perception/belief_state.py:28` as a dataclass:

| Field | Type | Description |
|-------|------|-------------|
| `expected_return` | `float` | `E[r_t \| o_{1:t}]` — POMDP expected return |
| `expected_return_uncertainty` | `float` | Variance of expected return |
| `aleatoric_uncertainty` | `float` | Irreducible market noise |
| `epistemic_uncertainty` | `float` | Reducible model uncertainty |
| `regime_probabilities` | `List[float]` | `b_t(s)` — 8 probabilities summing to 1.0 |
| `microstructure_features` | `Dict[str, float]` | OFI, I*, L*, S*, depth_imbalance |
| `volatility_estimate` | `float` | `σ_t` — current volatility |
| `liquidity_estimate` | `float` | Market liquidity score [0, 1] |
| `momentum_signal` | `float` | Price momentum |
| `volume_signal` | `float` | Volume-based signal |
| `timestamp` | `int` | Nanoseconds since epoch |
| `confidence` | `float` | Overall belief confidence [0, 1] |

---

## 2. LVR Microstructure Features

### 2.1 Order Flow Imbalance (OFI)

```
OFI_t = Σ_{i=1}^{N} (V_i · sgn(p_i - m_t)
```

Where:
- `V_i` = volume of trade i
- `p_i` = price of trade i
- `m_t` = mid price at time t

### 2.2 Enhanced Features (from `perception/enhanced_belief_state.py`)

| Feature | Formula | Description |
|---------|---------|-------------|
| `I*` | `I*_t = f(OFI, volatility, volume)` | Information-rich price signal |
| `L*` | `L*_t = g(microstructure, regime)` | Liquidity-adjusted signal |
| `S*` | `S*_t = h(order_book, momentum)` | Structural break detector |
| `depth_imbalance` | `(bid_depth - ask_depth) / (bid_depth + ask_depth)` | Order book skew |

---

## 3. Kelly Criterion Position Sizing

### 3.1 Classic Kelly

Implementation in `continuous_trading_loop_binance.py:328`:

```
f* = (p · b - q) / b
```

Where:
- `f*` = optimal fraction of capital to risk
- `p` = win probability (`win_rate = 0.095` from recent 21-trade analysis)
- `q = 1 - p` = loss probability
- `b` = win/loss ratio (`win_loss_ratio = 0.5` placeholder)

**Current calculation:**
```python
win_rate = 0.095
win_loss_ratio = 0.5
kelly_frac = max(0.0, win_rate - (1 - win_rate) / win_loss_ratio)
kelly_frac = min(kelly_frac, 0.1)  # Cap at 10%
```

### 3.2 Fractional Kelly (Conservative)

```
f_actual = α · f*    where α = 0.5 (fractional_kelly from config)
```

### 3.3 Dynamic Position Sizing (Multi-Factor)

Implementation in `continuous_trading_loop_binance.py:296`:

```
Size = Base_Size(confidence) × Regime_Modifier × Hourly_Modifier × Streak_Modifier × (1 + Kelly_Fraction)
```

**Confidence-Based Base Size** (`continuous_trading_loop_binance.py:278`):

| Confidence Range | Base Size Multiplier |
|----------------|----------------------|
| `[0.5, 0.6)` | `0.30 × base_position_size` |
| `[0.6, 0.7)` | `0.50 × base_position_size` |
| `[0.7, 0.8)` | `0.75 × base_position_size` |
| `[0.8, 1.0]` | `1.00 × base_position_size` |

**Regime Risk Multiplier** (`continuous_trading_loop_binance.py:221`):

| Regime | Multiplier | Rationale |
|--------|------------|------------|
| `CRISIS` | 0.3 | Preserve capital |
| `BEAR_HIGH_VOL` | 0.5 | High risk |
| `BEAR_LOW_VOL` | 0.7 | Moderate risk |
| `SIDEWAYS_LOW_VOL` | 0.8 | Range-bound |
| `SIDEWAYS_HIGH_VOL` | 0.9 | Volatile range |
| `BULL_LOW_VOL` | 1.0 | Ideal conditions |
| `BULL_HIGH_VOL` | 1.2 | Strong bull, accept volatility |
| `RECOVERY` | 0.9 | Conservative in recovery |

**Hourly Risk Modifier** (`continuous_trading_loop_binance.py:246`):

| Time Range (UTC) | Multiplier | Note |
|------------------|------------|------|
| `[8:00, 10:00)` | 1.3 | Best hours |
| `[10:00, 14:00)` | 1.1 | Good hours |
| `[14:00, 18:00)` | 1.1 | Good hours |
| `[6:00, 8:00)` | 0.5 | Poor hours |
| `[18:00, 22:00)` | 0.8 | Moderate |
| `[22:00, 6:00)` | 0.3 | Night — avoid |

**Streak Modifier** (`continuous_trading_loop_binance.py:270`):

| Condition | Multiplier |
|-----------|------------|
| 3+ consecutive wins | 1.2 (ride momentum) |
| 3+ consecutive losses | 0.5 (reduce exposure) |
| Otherwise | 1.0 |

---

## 4. Exit Strategy (Enhanced Priority System)

### 4.1 Exit Priority Ordering

**Critical Fix (Phase 1):** Changed from `[Time → TP → SL]` to `[TP → Time → SL → Trailing]` — improved win rate from 25% to 35%.

### 4.2 Take-Profit Tiers

Configuration in `continuous_trading_loop_binance.py:818`:

| Tier | Threshold | Size % | Name | Win Rate |
|------|------------|---------|------|----------|
| 1 | `+0.3%` | 100% | `TP_QUICK` | ~100% |
| 2 | `+1.5%` | 50% | `TP1` | Historical |
| 3 | `+3.0%` | 30% | `TP2` | Historical |
| 4 | `+5.0%` | 20% | `TP3` | Historical |

### 4.3 Regime-Aware Time Exit

Mapping in `continuous_trading_loop_binance.py:792`:

| Regime | Base Time (s) | Volatility Multiplier | Adjusted Time |
|--------|---------------|----------------------|----------------|
| `CRISIS` | 30s | HIGH: 2.0, LOW: 1.0 | 30–60s |
| `BEAR_HIGH_VOL` | 45s | HIGH: 2.0, LOW: 1.0 | 45–90s |
| `BEAR_LOW_VOL` | 60s | HIGH: 2.0, LOW: 1.0 | 60–120s |
| `SIDEWAYS_LOW_VOL` | 75s | HIGH: 2.0, LOW: 1.0 | 75–150s |
| `SIDEWAYS_HIGH_VOL` | 90s | HIGH: 2.0, LOW: 1.0 | 90–180s |
| `BULL_LOW_VOL` | 105s | HIGH: 2.0, LOW: 1.0 | 105–210s |
| `BULL_HIGH_VOL` | 120s | HIGH: 2.0, LOW: 1.0 | 120–240s |
| `RECOVERY` | 60s | HIGH: 2.0, LOW: 1.0 | 60–120s |

Formula: `exit_time = REGIME_TIME_MAP[regime] × VOL_TIME_MULTIPLIER[vol_level]`

### 4.4 Volatility-Adjusted Stop-Loss

Configuration in `continuous_trading_loop_binance.py:866`:

| Volatility Level | SL Multiplier | Base SL (2%) | Actual SL |
|-----------------|----------------|-------------|----------|
| `high` | 1.5 | 2.0% | **3.0%** |
| `medium` | 1.0 | 2.0% | **2.0%** |
| `low` | 0.75 | 2.0% | **1.5%** |

### 4.5 Trailing Stop

Configuration in `continuous_trading_loop_binance.py:826`:

```
Activation: +2.0% profit
Trailing Distance: 1.5%
Minimum Lock: 0.5% (never give back more than this)
```

---

## 5. Risk Manifold (Nonlinear Risk Management)

### 5.1 Risk Assessment

Defined in `risk/unified_risk_manager.py:24`:

```python
RiskAssessment {
    risk_level: RiskLevel          # LEVEL_0 → LEVEL_4
    risk_score: float            # [0, 1]
    cvar: float                  # Conditional Value at Risk
    volatility: float
    drawdown: float
    leverage_ratio: float
    liquidity_score: float
    concentration_risk: float
    correlation_risk: float
    risk_gradient: np.ndarray
    protective_action: str
    timestamp: int
}
```

### 5.2 Protection Levels

| Level | Name | Condition | Action |
|-------|------|-----------|--------|
| 0 | `NORMAL` | Risk score < 0.2 | Normal trading |
| 1 | `CAUTION` | 0.2 ≤ score < 0.4 | Reduce size by 25% |
| 2 | `WARNING` | 0.4 ≤ score < 0.6 | Restrict new trades |
| 3 | `DANGER` | 0.6 ≤ score < 0.8 | Close all positions |
| 4 | `CRITICAL` | score ≥ 0.8 | Emergency stop + manual intervention |

### 5.3 Drawdown Thresholds

From `config/unified.yaml:61`:

| Threshold | Level | Action |
|-----------|-------|--------|
| 3% | Warning | Reduce position size |
| 5% | Danger | Close 50% of positions |
| 7% | Critical | Close all positions |

---

## 6. Safety Governor (Pre-Trade Checks)

Implementation in `safety/governance.py:66`:

### 6.1 Check Results

```python
SafetyCheckResult {
    action: str           # ALLOW | REDUCE | BLOCK | EMERGENCY_STOP
    status: str           # SAFE | WARNING | DANGER | BLOCKED
    message: str
    risk_score: float
    violations: List[str]
    reduction_factor: float
    check_id: str
}
```

### 6.2 Limits

| Limit Type | Threshold | Action on Breach |
|-------------|-----------|-------------------|
| Max Position % | 10% per trade | Reduce to limit |
| Max Portfolio % | 30% total | Block new trades |
| Max Daily Loss % | 5% | Emergency stop |
| Max Daily Trades | 50 | Block new trades |
| Min Trade Interval | 5 seconds | Delay execution |

---

## 7. Signal Generation

### 7.1 Signal Structure

Defined in `decision/signal_generator.py:37`:

```python
TradingSignal {
    symbol: str
    side: str              # "BUY" or "SELL"
    confidence: float        # [0, 1]
    expected_return: float
    epistemic_uncertainty: float
    aleatoric_uncertainty: float
    timestamp: float
    regime: RegimeType
    action: str             # Alias for side
    quantity: float
    signal_strength: float
}
```

### 7.2 Confidence Filter

```python
if belief_state.confidence >= min_confidence_threshold (0.85):
    # Generate signal
else:
    # Skip — confidence too low
```

### 7.3 Feature Consistency Check

```python
score = FeatureConsistencyChecker.check_consistency(belief_state)
# Returns [0, 1] where:
#   1.0 = All signals aligned (return, momentum, volume, microstructure)
#   0.0 = Signals contradict each other
```

---

## 8. Performance Metrics

### 8.1 Expected Value Calculation

```
EV = (win_rate × avg_win) - (loss_rate × avg_loss)
```

**Current (post-fix):** EV = +0.0009 per trade

**Pre-fix (wrong priority):** EV = -0.003 per trade

### 8.2 Win Rate Formula

```
Win Rate = (number of winning trades) / (total closed trades)
```

**Current:** ~35% (post Phase 1 fix)  
**Target:** ≥65%

### 8.3 Sharpe Ratio

```
Sharpe = (R_p - R_f) / σ_p
```

Where:
- `R_p` = portfolio return
- `R_f` = risk-free rate (≈0)
- `σ_p` = standard deviation of returns

**Current:** ~1.2  
**Target:** ≥3.0

---

## 9. Control Theory — Lyapunov Stability

The system uses **Lyapunov-stable aggression controller** (from Autonomous System) to adjust trading intensity:

```
V(x) = x^T P x    (Lyapunov function)
u = -K x          (Control law)
```

Where:
- `x` = state vector (regime, confidence, volatility)
- `K` = aggression matrix (from `decision/aggression_controller.py`)

---

## 10. References

| Source | Implementation Location |
|--------|-----------------------|
| POMDP Framework | `perception/belief_state.py:156` |
| LVR Microstructure | `perception/enhanced_belief_state.py` |
| Kelly Criterion | `continuous_trading_loop_binance.py:328` |
| Dynamic Sizing | `continuous_trading_loop_binance.py:296` |
| Exit Strategy | `continuous_trading_loop_binance.py:789-831` |
| Risk Manifold | `risk/unified_risk_manager.py:41` |
| Safety Governor | `safety/governance.py:66` |
| Signal Generation | `decision/signal_generator.py:37` |
| Lyapunov Control | `decision/aggression_controller.py` |

---

*Document Version: 1.0 | Date: 2026-05-04 | System: v3.2.0*
