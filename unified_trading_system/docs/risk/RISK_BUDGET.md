# Risk Budget

Complete risk management framework, leverage constraints, drawdown waterfall, and position limits for the Unified Trading System.

---

## 1. Leverage Constraints (User Mandated)

The system enforces a **15x–25x leverage range** as a hard constraint from the user.

| Parameter | Value | Location | Notes |
|-----------|-------|----------|-------|
| **Min Leverage** | `15x` | `config/unified.yaml:29` | USER CONSTRAINT: Minimum |
| **Default Leverage** | `20x` | `config/unified.yaml:30` | Used for medium confidence |
| **Max Leverage** | `25x` | `config/unified.yaml:28` | USER CONSTRAINT: Maximum |
| **Emergency** | `false` | `config/unified.yaml:26` | Disabled after 10/10 upgrade |

### 1.1 Dynamic Leverage Selection (`continuous_trading_loop_binance.py:557`)

```python
leverage_to_use = int(self._leverage_multiplier)  # Default: 20.0
```

**Confidence-Based Tiering** (from `config/unified.yaml:57`):

| Confidence Range | Leverage | Rationale |
|----------------|----------|------------|
| `≥0.94` | **25x** (Max) | High confidence → max exposure |
| `[0.88, 0.94)` | **20x** (Default) | Medium confidence |
| `[0.80, 0.88)` | **15x** (Min) | Low confidence → min exposure |
| `<0.80` | **REJECT** | Below threshold |

### 1.2 Balance-Based Leverage Override (`continuous_trading_loop_binance.py:476`)

```python
if cross_wallet_balance > 0:
    self._leverage_multiplier = 20.0
elif wallet_balance > 0:
    self._leverage_multiplier = 20.0
else:
    self._leverage_multiplier = 40.0  # Emergency fallback (WARNING: exceeds constraint)
    # FIX NEEDED: Cap at 25x per user constraint
```

**⚠️ Known Issue:** Emergency fallback sets 40x, violating the 25x max constraint.

---

## 2. Position Limits

### 2.1 Per-Position Cap

| Parameter | Value | Location |
|-----------|-------|----------|
| **Max Position Size** | `$500 USD` | `continuous_trading_loop_binance.py:559` |
| **Config Default** | `0.1 BTC` (~$6,000 at $60k BTC) | `TradingConfig.max_position_size` |
| **Safety Governor Cap** | `10% of portfolio` | `safety/governance.py:90` |

**Calculation** (`continuous_trading_loop_binance.py:1402`):

```python
def calculate_safe_notional(balance, symbol):
    if balance >= 1000:    # Testnet tier
        return min(balance * 0.10, 500.0)   # Cap at $500
    elif balance >= 100:   # Medium tier
        return balance * 0.10
    elif balance >= 10:    # Small account
        return balance * 0.15
    else:                  # Emergency
        return max(balance * 0.20, 1.0)
```

### 2.2 Concurrent Position Limit

| Parameter | Value | Location |
|-----------|-------|----------|
| **Max Positions** | `5` | `config/unified.yaml:31` |
| **Current Open** | Checked via `self._open_positions` | `continuous_trading_loop_binance.py:340` |

### 2.3 Portfolio Heat

| Parameter | Value | Location |
|-----------|-------|----------|
| **Max Heat** | `80%` | `config/unified.yaml:51` |
| **Warning Heat** | `60%` | `config/unified.yaml:52` |
| **Decay Rate** | `10% per closed position` | `config/unified.yaml:53` |

---

## 3. Drawdown Waterfall

### 3.1 Thresholds (`risk/unified_risk_manager.py:56`)

| Level | Drawdown % | Risk Level | Action |
|-------|--------------|------------|--------|
| **Warning** | `3%` | LEVEL_1_CAUTION | Reduce position size by 25% |
| **Danger** | `5%` | LEVEL_2_WARNING | Restrict new trades |
| **Critical** | `7%` | LEVEL_3_DANGER | Close all positions |
| **Emergency** | `10%` | LEVEL_4_CRITICAL | Emergency stop + manual intervention |

### 3.2 Daily Loss Limits

| Parameter | Value | Location |
|-----------|-------|----------|
| **Daily Loss Limit** | `5%` of account | `config/unified.yaml:34` |
| **Config (Testnet)** | `$10,000` | `TradingConfig.max_daily_loss` |
| **Config (Live)** | `$5,000` | `create_live_trading_loop()` |

### 3.3 Drawdown Waterfall Implementation

```
Account Balance: $4,919.50
       ↓
Portfolio Value = Balance × Leverage (20x) = $98,390
       ↓
Daily Loss Limit (5%) = $4,919.50 × 0.05 = $245.98
       ↓
  ├─ If loss ≥ $123 (3%): WARNING → reduce size 25%
  ├─ If loss ≥ $246 (5%): DANGER → block new trades
  ├─ If loss ≥ $344 (7%): CRITICAL → close all positions
  └─ If loss ≥ $492 (10%): EMERGENCY STOP → manual intervention
```

---

## 4. Risk Manifold (Nonlinear Risk Surface)

Implementation in `risk/unified_risk_manager.py:41`.

### 4.1 Risk Assessment Output

```python
RiskAssessment {
    risk_level: RiskLevel       # LEVEL_0 → LEVEL_4
    risk_score: float           # [0, 1] overall score
    cvar: float                  # Conditional Value at Risk
    volatility: float            # Estimated σ
    drawdown: float              # Current drawdown %
    leverage_ratio: float        # Current leverage usage
    liquidity_score: float       # Market liquidity [0, 1]
    concentration_risk: float    # Position concentration
    correlation_risk: float      # Portfolio correlation
    risk_gradient: np.ndarray    # ∂risk/∂action
    protective_action: str       # Recommended action
    timestamp: int
}
```

### 4.2 Risk Gradient (Control Barrier Theory)

```
∇Risk = [∂risk/∂position_size, ∂risk/∂leverage, ∂risk/∂concentration]
```

Used by the **Aggression Controller** (`decision/aggression_controller.py`) to adjust trading intensity via Lyapunov control.

---

## 5. Safety Governor (Pre-Trade Checks)

Implementation in `safety/governance.py:66`.

### 5.1 Check Results

```python
SafetyCheckResult {
    action: str             # ALLOW | REDUCE | BLOCK | EMERGENCY_STOP
    status: str            # SAFE | WARNING | DANGER | BLOCKED
    message: str
    risk_score: float
    violations: List[str]
    reduction_factor: float  # 0.0–1.0
    check_id: str
}
```

### 5.2 Violation Types

| Violation | Threshold | Action |
|------------|-----------|--------|
| **Concentration** | `>30%` in single position | BLOCK |
| **Total Exposure** | `>80%` of portfolio | REDUCE to limit |
| **Daily Loss** | `>5%` of daily limit | EMERGENCY_STOP |
| **Daily Trades** | `>50` per day | BLOCK |
| **Min Interval** | `<5 seconds` between trades | DELAY |

### 5.3 Check Flow

```
New Trade Request
       ↓
├─ Concentration Check → <30% of portfolio?
├─ Total Exposure Check → <80% of portfolio?
├─ Daily Loss Check → <5% of daily limit?
├─ Daily Trades Check → <50 trades today?
└─ Min Interval Check → >5s since last trade?
       ↓
   [ALL PASS] → ALLOW
   [SOME FAIL] → REDUCE (with reduction_factor)
   [CRITICAL] → EMERGENCY_STOP
```

---

## 6. Portfolio Heat Management

### 6.1 Heat Calculation

```
Heat = Σ (position_value / portfolio_value) for all open positions
     = weighted exposure percentage
```

### 6.2 Heat Levels

| Heat % | Status | Action |
|--------|--------|--------|
| `<60%` | Normal | Continue trading |
| `60–80%` | Warning | Reduce new position sizes by 50% |
| `>80%` | Danger | Block all new positions |

---

## 7. Emergency Risk Control

Implementation in `emergency_risk_control.py`.

### 7.1 Emergency Triggers

| Trigger | Condition | Action |
|---------|-----------|--------|
| **Max Drawdown** | `>7%` | Close all positions + stop system |
| **Max Leverage** | `>48x` (Warning), `>50x` (Danger) | Force deleveraging |
| **Max Daily Loss** | `>8%` (Critical) | Emergency shutdown |
| **Correlation Spike** | `>80%` correlation | Diversification enforced |

### 7.2 Emergency Stop (`continuous_trading_loop_binance.py:1757`)

```python
async def shutdown(self):
    self._running = False
    if self.health_server:
        self.health_server.stop()
    await send_system_status_alert(
        component="trading_loop",
        status="stopped",
        details={"cycles_completed": self._cycle_count, ...}
    )
```

---

## 8. Risk-Adjusted Performance Metrics

### 8.1 Risk-Adjusted Position Sizing

```
Adjused_Size = Base_Size
               × Regime_Multiplier [0.3x–1.2x]
               × Hourly_Multiplier [0.3x–1.3x]
               × Streak_Multiplier [0.5x–1.2x]
               × Kelly_Fraction [0.0–0.1]
```

### 8.2 Value at Risk (VaR) & Conditional VaR

| Metric | Current | Target |
|--------|---------|--------|
| **95% VaR** | ~3% daily | <2% |
| **CVaR (95%)** | ~5% tail loss | <3% |
| **Max Drawdown** | <15% | <10% |
| **Sharpe Ratio** | ~1.2 | ≥3.0 |

---

## 9. Stress Testing

### 9.1 Scenario Analysis

| Scenario | Expected Impact | Mitigation |
|----------|-----------------|------------|
| **Market Crash (-30%)** | 40x leverage → liquidation at -2.5% | Stop-loss at -3%, max 25x |
| **Flash Crash (-10%)** | Auto-liquidation | Safety Governor blocks new positions |
| **High Volatility (+5σ)** | Regime → CRISIS → 0.3x multiplier | Preserve capital |
| **Liquidity Dry-Up** | Slippage >50bps | Dynamic position size reduction |

### 9.2 Monte Carlo Simulation (Recommended Addition)

```
Run 10,000 simulations:
  - Random walk with μ = expected_return, σ = volatility
  - Apply regime transitions
  - Apply Kelly position sizing
  → Output: 95% confidence interval for max drawdown
```

---

## 10. Risk Reporting

### 10.1 Real-Time Risk Dashboard (Prometheus)

Available at `http://localhost:9090/metrics`:

| Metric | Description |
|--------|-------------|
| `risk_score` | Current overall risk [0, 1] |
| `drawdown_percent` | Current drawdown % |
| `leverage_usage` | Current leverage ratio |
| `portfolio_heat` | Current heat % |
| `open_positions` | Number of open positions |
| `daily_pnl` | Realized P&L today |

### 10.2 Risk Alerts (Telegram)

Sent via `send_risk_alert()`:

```
🚨 Risk Alert: [Violation Type]
Component: trading_loop
Status: CRITICAL
Details: {
  "risk_score": 0.85,
  "drawdown": "6.2%",
  "action": "CLOSE_ALL_POSITIONS"
}
```

---

## 11. Regulatory & Compliance (CFA Standards)

### 11.1 Disclosure Requirements

| Item | Status | Location |
|------|--------|----------|
| **Leverage Disclosure** | ✅ In all reports | `config/unified.yaml:28` |
| **Max Drawdown Scenarios** | ✅ Documented | `CFA_ATTESTATION.md` |
| **Stress Test Results** | 🔴 TODO | Add Monte Carlo |
| **Performance Disclaimer** | ✅ In logs | `observability/logging.py:99` |

### 11.2 Risk Limits Warning

> **⚠️ 15x–25x Leverage Notice:**  
> Trading at 20x leverage means a **5% adverse move** wipes out **100% of margin**.  
> Max drawdown of 15% can occur in **3 consecutive losing trades**.  
> This is **NOT suitable for live trading** without:
> - Reducing leverage to ≤5x
> - Increasing account balance to ≥$50,000
> - Implementing daily loss circuit breakers

---

*Document Version: 1.0 | Date: 2026-05-04 | System: v3.2.0*
