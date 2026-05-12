# Data Pipeline

Complete data flow documentation from Binance API → BeliefState → TradeJournal with provenance chain for the Unified Trading System.

---

## 1. Market Data Ingestion Flow

### 1.1 Data Source: Binance Testnet API

**Primary endpoint:** `https://testnet.binancefuture.com/fapi/v1/ticker/bookTicker`
**Backup:** `https://testnet.binancefuture.com/fapi/v2/account` (balance/positions)

Implementation in `continuous_trading_loop_binance.py:1344`:

```python
async def _get_real_market_data(symbol: str) -> Dict:
    url = f"{self.base_url}/fapi/v1/ticker/bookTicker?symbol={binance_symbol}"
    async with session.get(url) as resp:
        data = await resp.json()
        return {
            "bid_price": float(data.get("bidPrice", 0)),
            "ask_price": float(data.get("askPrice", 0)),
            "bid_size": float(data.get("bidQty", 0)),
            "ask_size": float(data.get("askQty", 0)),
            "last_price": 0.0,
            "last_size": 0.0,
        }
```

### 1.2 Data Refresh Rate

| Item | Value |
|------|-------|
| **Cycle Interval** | 10 seconds |
| **Symbols** | 12 (BTC, ETH, BNB, SOL, ADA, XRP, DOGE, DOT, AVAX, LINK, LTC, BCH) |
| **API Calls/Cycle** | 12 (1 per symbol) + 1 balance check = 13 calls |
| **Rate Limit** | 20 orders/minute (configurable) |

---

## 2. Data Transformation Pipeline

### 2.1 Raw Market Data → BeliefState

```
Market Data JSON (from Binance API)
       ↓
_perception/belief_state.py:156_ → BeliefStateEstimator.update()
       │
       ├─ Regime Transition: b_t(s') = η · O(o|s') · T(s'|s,a) · b_{t-1}(s)
       │   └─ Output: regime_probabilities[8] (sum=1.0)
       │
       ├─ LVR Features: compute_microstructure_features()
       │   ├─ OFI (Order Flow Imbalance)
       │   ├─ I* (Information-rich signal)
       │   ├─ L* (Liquidity-adjusted signal)
       │   └─ S* (Structural break detector)
       │
       ├─ Volatility Estimate: σ_t
       ├─ Momentum Signal: price momentum
       └─ Volume Signal: volume-based signal
       ↓
BeliefState (dataclass, 11 fields)
       ├─ expected_return: float
       ├─ confidence: float [0, 1]
       ├─ regime_probabilities: List[float] (8)
       ├─ volatility_estimate: float
       ├─ microstructure_features: Dict[str, float]
       └─ timestamp: int (nanoseconds)
```

### 2.2 BeliefState Data Structure

Defined in `perception/belief_state.py:28`:

| Field | Type | Description | Used By |
|-------|------|-------------|----------|
| `expected_return` | `float` | POMDP E[r_t \| o_{1:t}]` | SignalGenerator |
| `expected_return_uncertainty` | `float` | Variance of expected return | RiskManager |
| `aleatoric_uncertainty` | `float` | Irreducible noise | RiskManager |
| `epistemic_uncertainty` | `float` | Reducible model error | RiskManager |
| `regime_probabilities` | `List[float]` | 8 regime probabilities | SignalGenerator, Exit Logic |
| `microstructure_features` | `Dict[str, float]` | OFI, I*, L*, S* | SignalGenerator |
| `volatility_estimate` | `float` | σ_t | Exit Logic (SL calc) |
| `liquidity_estimate` | `float` | [0, 1] score | Position Sizing |
| `momentum_signal` | `float` | Price momentum | SignalGenerator |
| `volume_signal` | `float` | Volume signal | SignalGenerator |
| `timestamp` | `int` | Nanoseconds epoch | All |
| `confidence` | `float` | Overall [0, 1] | SignalGenerator, Position Sizing |

---

## 3. Feature Store (AdvancedFeaturePipeline)

Implementation in `learning/feature_pipeline.py:16`:

### 3.1 Available Features

| Feature | Source | Type | Used In |
|---------|--------|------|----------|
| `OFI` | Order Flow Imbalance | `float` | Regime Detection |
| `I_star` | Information Signal | `float` | Signal Generation |
| `L_star` | Liquidity Signal | `float` | Position Sizing |
| `S_star` | Structural Break | `float` | Risk Management |
| `depth_imbalance` | Order Book Skew | `float` | Signal Generation |
| `momentum` | Price Momentum | `float` | Signal Generation |
| `volume_signal` | Volume Anomaly | `float` | Signal Generation |
| `volatility` | σ_t estimate | `float` | Exit Logic |
| `regime_prob_0` through `regime_prob_7` | HMM output | `float` each | Signal Generation |

### 3.2 Feature Normalization

```python
# From learning/feature_pipeline.py:200
def normalize_features(features: Dict[str, float]) -> Dict[str, float]:
    # Z-score normalization using running mean/std
    for name in features:
        if name in self.means and self.stds[name] > 0:
            features[name] = (features[name] - self.means[name]) / self.stds[name]
    return features
```

### 3.3 Feature Importance Weights

```python
# From learning/feature_pipeline.py:268
def get_feature_importance_weights() -> Dict[str, float]:
    return {
        'momentum': 0.25,
        'volatility': 0.20,
        'OFI': 0.15,
        'I_star': 0.15,
        'volume': 0.10,
        'L_star': 0.10,
        'S_star': 0.05,
    }
```

---

## 4. Trade Journal (Persistence Layer)

Implementation in `learning/trade_journal.py:39`:

### 4.1 Data Provenance Chain

```
Trade Execution (Binance API)
       ↓
EnhancedTradingLoop._execute_signal()
       ↓
TradeJournal.record_entry() → logs/trade_journal.json
       │
       ├─ TradeRecord.trade_id: "trade_<timestamp>"
       ├─ TradeRecord.symbol: "BTC/USDT"
       ├─ TradeRecord.side: "BUY" | "SELL"
       ├─ TradeRecord.entry_price: float
       ├─ TradeRecord.quantity: float
       ├─ TradeRecord.predicted_return: float
       ├─ TradeRecord.uncertainty: float
       ├─ TradeRecord.status: "OPEN" | "CLOSED" | "CANCELLED"
       │
       └─ Data Provenance (Phase 1.2 - CFA Compliance):
           ├─ TradeRecord.is_synthetic: bool  # False for real Binance trades
           ├─ TradeRecord.data_source: str    # "testnet" | "live" | "simulated"
           └─ TradeRecord.execution_venue: str  # "binance_testnet" | "paper"
       ↓
TradeJournal.record_exit() → Update trade_journal.json
       │
       ├─ TradeRecord.exit_price: float
       ├─ TradeRecord.pnl: float  # (exit - entry) / entry
       └─ TradeRecord.metadata: Dict  # exit_reason, binance_order_id, etc.
```

### 4.2 JSON Storage Format

Location: `logs/trade_journal.json`

```json
{
  "trade_1777853136000": {
    "trade_id": "trade_1777853136000",
    "symbol": "BTC/USDT",
    "side": "BUY",
    "entry_time": 1777853136.0,
    "exit_time": 1777853196.0,
    "entry_price": 60123.45,
    "exit_price": 60142.78,
    "quantity": 0.001,
    "predicted_return": 0.003,
    "actual_return": 0.0032,
    "uncertainty": 0.12,
    "pnl": 0.01933,
    "status": "CLOSED",
    "is_synthetic": false,
    "data_source": "testnet",
    "execution_venue": "binance_testnet",
    "metadata": {
      "exit_reason": "TAKE_PROFIT_0.3",
      "binance_order_id": 123456789,
      "confidence": 0.89,
      "cycle": 34250
    }
  }
}
```

### 4.3 Loading Behavior

```python
# From learning/trade_journal.py:50
def _load_journal(self):
    if os.path.exists(self.storage_path):
        with open(self.storage_path, 'r') as f:
            data = json.load(f)  # ⚠️ O(n) — loads ALL trades!
            for tid, record in data.items():
                self.trades[tid] = TradeRecord(**record)
```

**⚠️ Performance Issue:** `json.load()` loads entire file into memory. With 2,348+ trades (current), this is ~1-2MB. Recommendation: migrate to SQLite after 10,000 trades.

---

## 5. Data Provenance & Compliance

### 5.1 Provenance Summary

Available via `TradeJournal.get_data_provenance_summary()`:

```python
{
    "total_closed": 1615,
    "real_trades": 304,       # 18.9% (trades with real P&L)
    "synthetic_trades": 1311, # 81.1% (filtered out by default)
    "real_win_rate": 0.217,      # 21.7% (actual performance)
    "synthetic_win_rate": 0.859, # 85.9% (fake - for reference only)
    "data_purity": 0.189          # 18.9% pure data
}
```

### 5.2 CFA Compliance (Phase 1 Upgrade)

| Standard | Implementation | Location |
|----------|--------------|----------|
| **I(C) Misrepresentation** | `is_synthetic=False` for all new trades | `trade_journal.py:35` |
| **VI Disclosure** | Performance disclaimer in all logs | `observability/logging.py:99` |
| **Data Transparency** | `data_source`, `execution_venue` tracked | `trade_journal.py:36-37` |
| **Synthetic Filter** | `get_training_data(use_synthetic=False)` default | `trade_journal.py:146` |

---

## 6. Data Flow Diagrams

### 6.1 Complete Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BINANCE TESTNET API                              │
│  https://testnet.binancefuture.com/fapi/v1/ticker/bookTicker │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│              _get_real_market_data() [continuous_trading_loop_binance.py:1344] │
│  Input: symbol ("BTC/USDT")                                      │
│  Output: {bid_price, ask_price, bid_size, ask_size}            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│         BeliefStateEstimator.update() [perception/belief_state.py:156] │
│  POMDP Update: b_t(s') = η · O(o|s') · T(s'|s,a) · b_{t-1}(s) │
│  Output: BeliefState (11 fields)                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
              ┌────────────────┬────────────────┬────────────────┐
              ▼                ▼                ▼                ▼
       ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
       │SignalGen│    │RiskMgr  │    │ExitLogic│    │Position │
       │.generate│    │.assess  │    │._check   │    │Sizing   │
       │_signal()│    │_risk()  │    │_exit_   │    │.calculate│
       └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘
            │                │                │                │
            ▼                ▼                ▼                ▼
       TradingSignal    RiskAssessment   Exit Reason    Position Size
       (action,        (level,         ("TP",        (dynamic,
        confidence,      score,         "TIME",      regime-mod,
        quantity)      action)        "SL")      hourly-mod)
                                        │
                                        ▼
                              ┌────────────────────────┐
                              │  _execute_signal()              │
                              │  → _place_binance_order()      │
                              │  → Binance API POST /order    │
                              └────────────┬───────────────────┘
                                           │
                                           ▼
                              ┌──────────────────────────────────────┐
                              │  TradeJournal.record_entry()           │
                              │  → logs/trade_journal.json          │
                              │  Fields: trade_id, symbol, side,   │
                              │  entry_price, quantity, metadata     │
                              │  Provenance: is_synthetic=False   │
                              └──────────────────────────────────────┘
```

---

## 7. Data Quality Metrics

### 7.1 Current Statistics

| Metric | Value | Source |
|--------|-------|--------|
| **Total Trades** | 2,348+ | `trade_journal.json` |
| **Closed Trades** | 1,615 | Provenance summary |
| **Real Trades** | 304 (18.9%) | `is_synthetic=False` |
| **Synthetic Trades** | 1,311 (81.1%) | Filtered by default |
| **Real Win Rate** | 21.7% | `actual_return > 0` |
| **Synthetic Win Rate** | 85.9% | FAKE — removed in Phase 1 |
| **Data Purity** | 18.9% | `real_trades / total_closed` |

### 7.2 Data Validation

```python
# From learning/trade_journal.py
def validate_trade(trade: TradeRecord) -> Tuple[bool, List[str]]:
    errors = []
    if trade.entry_price <= 0:
        errors.append("Invalid entry price")
    if trade.quantity <= 0:
        errors.append("Invalid quantity")
    if trade.status not in ["OPEN", "CLOSED", "CANCELLED"]:
        errors.append("Invalid status")
    if trade.data_source not in ["live", "testnet", "simulated", "backtest"]:
        errors.append("Invalid data_source")
    return len(errors) == 0, errors
```

---

## 8. Data Export & Analysis

### 8.1 Export for ML Training

```python
# From learning/trade_journal.py:146
def get_training_data(use_synthetic: bool = False) -> Tuple[np.ndarray, np.ndarray]:
    trades = [t for t in self.trades.values()
             if t.status == "CLOSED"
             and (use_synthetic or not t.is_synthetic)]
    
    X = np.array([[t.entry_price, t.quantity, t.predicted_return, ...]
                  for t in trades])
    y = np.array([t.actual_return for t in trades])
    return X, y
```

### 8.2 Performance Analysis

```bash
# Run from project root
python3 compute_performance.py
# Output:
#   Total Trades: 2348
#   Win Rate: 21.7% (real trades only)
#   Expected Value: +0.0009 per trade
#   Max Drawdown: <15%
```

---

## 9. Data Retention Policy

| Data Type | Retention | Location | Notes |
|----------|-----------|----------|-------|
| **Trade Journal** | Indefinite | `logs/trade_journal.json` | Grows unbounded (⚠️ migrate to SQLite >10K) |
| **Cycle Logs** | 30 days | `logs/final.log` | Rotated via logrotate |
| **Performance Metrics** | 90 days | Prometheus TSDB | `logs/*.json` (learning results) |
| **Health Checks** | 7 days | Prometheus TSDB | `:9090/metrics` |

---

*Document Version: 1.0 | Date: 2026-05-04 | System: v3.2.0*
