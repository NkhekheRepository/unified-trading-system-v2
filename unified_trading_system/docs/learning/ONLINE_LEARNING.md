# Online Learning & Adaptation#

Complete documentation of the online learning loop, drift detection, model versioning, and ensemble methods in the Unified Trading System.

---

## 1. Learning Loop Overview#

```
Trade Executed (Binance API)
       ↓
TradeJournal.record_exit() → logs/trade_journal.json
       │
       ├─ TradeRecord with pnl, metadata, provenance
       │
       └─ Triggers model retraining (every N trades)
              ↓
       ├─ EnsembleTrainer.train_ensemble()
       │    ├─ train_xgboost()      → XGBoost model
       │    ├─ train_lstm()         → LSTM (PyTorch)
       │    ├─ train_transformer()  → Transformer (PyTorch)
       │    └─ train_random_forest() → RandomForest (sklearn)
       │
       └─ ModelRegistry.register_model()
            ├─ Version created (incremental ID)
            ├─ Metrics computed (win_rate, Sharpe, etc.)
            └─ Promoted to production if better than current
```

---

## 2. Online Adaptation (Continuous Learning Loop)#

### 2.1 Feedback Layer (`continuous_learning_loop.py`)#

**Status:** Exists but currently **uses `continuous_trading_loop` (not `binance` version)**.

| Parameter | Value | Location |
|-----------|-------|----------|
| **Update Frequency** | Every 20 closed trades | `config/unified.yaml:172` |
| **Learning Rate** | `0.008` | `config/unified.yaml:144` |
| **Min Samples** | 30 | `config/unified.yaml:143` |
| **Min Weight** | `0.08` | `config/unified.yaml:177` |
| **Max History** | 800 trades | `config/unified.yaml:178` |

### 2.2 Rolling Win Rate Calculation#

Implementation in `continuous_learning_loop.py:630`:

```python
def get_rolling_win_rate(self, n: int = 20) -> float:
    recent = [t for t in self.trades.values()
                if t.status == "CLOSED"][-n:]
    wins = sum(1 for t in recent if t.pnl > 0)
    return wins / len(recent) if recent else 0.0
```

---

## 3. Drift Detection#

### 3.1 DriftDetector (`learning/regime_detector.py:356`)#

```python
class HiddenMarkovRegimeDetector:
    """HMM using Baum-Welch / Viterbi"""
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__(n_regimes=8)` | Config | None | 356 |
| `fit(features)` | np.ndarray | Self | Baum-Welch | 356 |
| `predict_regime(features)` | np.ndarray | `(regime, posteriors)` | Viterbi | 397 |

### 3.2 Drift Detection Parameters#

From `config/unified.yaml:181`:

| Parameter | Value | Severity Level |
|-----------|-------|---------------|
| **Threshold** | `0.03` | Trigger for drift check |
| **Window Size** | 80 trades | Rolling window |
| **Minor** | `0.2` | Log warning, continue |
| **Moderate** | `0.5` | Reduce confidence threshold |
| **Severe** | `0.8` | Re-initialize models |

**Drift Score Calculation:**
```
drift_score = |μ_current_window - μ_historical| / σ_historical
```

---

## 4. Model Versioning (`learning/model_registry.py`)#

### 4.1 ModelVersion Dataclass (line 19)#

```python
@dataclass
class ModelVersion:
    name: str                    # 'xgboost', 'lstm', 'transformer', 'rf'
    version_id: str              # 'v1.0.0', 'v1.0.1', etc.
    model_type: str
    metrics: Dict[str, float]    # {'win_rate': 0.65, 'sharpe': 1.2, ...}
    created_at: float
    is_active: bool = False
    is_production: bool = False
```

### 4.2 ModelRegistry Methods (line 30)#

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__(base_path)` | str | None | 35 |
| `register_model(name, version_id, model, metrics)` | ... | `bool` | Register new version | 91 |
| `activate_model(name, version_id)` | str, str | `bool` | Set as active | 129 |
| `promote_to_production(name, version_id)` | str, str | `bool` | Set as production | 167 |
| `rollback(name)` | str | `bool` | Roll to previous prod | 210 |
| `get_active_version(name)` | str | `Optional[ModelVersion]` | Get active | 232 |
| `get_production_version(name)` | str | `Optional[ModelVersion]` | Get prod | 247 |
| `get_model_versions(name)` | str | `List[ModelVersion]` | List all | 262 |
| `compare_versions(name)` | str | `Dict[str, Any]` | Compare metrics | 268 |
| `cleanup_old_versions(name, keep_n=5)` | str, int | `int` | Delete old | 295 |

---

## 5. A/B Testing (`learning/model_registry.py:333`)#

### 5.1 ABTestManager#

```python
class ABTestManager:
    """Manages A/B testing of models"""
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__(registry)` | ModelRegistry | None | 333 |
| `start_test(name, version_a, version_b, traffic_split=0.5)` | ... | `str` (test_id) | Start A/B | 
| `record_result(test_id, version, outcome)` | str, str, Dict | None | Record outcome | 
| `get_test_results(test_id)` | str | `Dict[str, Any]` | Get results + winner | 

### 5.2 A/B Test Flow#

```
Start A/B Test: version_A (current) vs version_B (new)
       ↓
Split traffic: 50% → version_A, 50% → version_B
       ↓
Record outcomes: {trade_id, version, pnl, win/loss}
       ↓
After N trades (e.g., 100):
       ├─ version_A: win_rate = 62%
       └─ version_B: win_rate = 68% → WINNER
              ↓
       promote_to_production(version_B)
```

---

## 6. Ensemble Training (`learning/ensemble_trainer.py`)#

### 6.1 EnsembleTrainer Methods (line 18)#

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__(config)` | Dict | None | 24 |
| `load_real_trades()` | None | `(X, y)` | Load from TradeJournal | 38 |
| `train_xgboost(X, y)` | np.ndarray, np.ndarray | `Dict` | XGBoost | 114 |
| `train_lstm(X, y)` | np.ndarray, np.ndarray | `Dict` | LSTM (PyTorch) | 153 |
| `train_transformer(X, y)` | np.ndarray, np.ndarray | `Dict` | Transformer | 211 |
| `train_random_forest(X, y)` | np.ndarray, np.ndarray | `Dict` | RandomForest | 239 |
| `_simulate_model(name, X, y)` | str, ... | `Dict` | Evaluate single | 266 |
| `_calculate_win_rate(y_true, y_pred)` | np.ndarray, np.ndarray | `float` | Win rate % | 284 |
| `train_ensemble()` | None | `Dict[str, Any]` | Train all 4 | 294 |

### 6.2 Ensemble Combination#

```python
# From ensemble_trainer.py:294
def train_ensemble(self) -> Dict[str, Any]:
    results = {}
    results['xgboost'] = self.train_xgboost(X, y)
    results['lstm'] = self.train_lstm(X, y)
    results['transformer'] = self.train_transformer(X, y)
    results['rf'] = self.train_random_forest(X, y)
    
    # Combine predictions (weighted by win_rate)
    # Return best model + ensemble metadata
    return results
```

**Weighting Formula:**
```
final_prediction = Σ (model_i.prediction × model_i.win_rate) / Σ win_rates
```

---

## 7. Return Prediction (`learning/return_predictor.py`)#

### 7.1 ReturnPredictor (PyTorch NN)#

```python
class ReturnPredictor(nn.Module):
    """Ensemble return predictor"""
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__(input_size=10, hidden_size=64, num_layers=2)` | Config | None | 103 |
| `forward(x)` | torch.Tensor [B,seq,features] | torch.Tensor [B,1] | 120 |
| `predict_return(feature_vector, context)` | np.ndarray, Dict | `Dict` | Main API | 242 |
| `train_batch(sequences, targets)` | torch.Tensor, torch.Tensor | `float` (loss) | 265 |
| `validate_batch(sequences, targets)` | torch.Tensor, torch.Tensor | `float` (loss) | 292 |
| `save(filepath)` | str | None | Save model | 315 |
| `load(filepath)` | str | None | Load model | 331 |
| `prepare_sequence(feature_vector)` | np.ndarray | torch.Tensor [1,seq,features] | 231 |

---

## 8. Regime Detection (`learning/regime_detector.py`)#

### 8.1 Two Implementations#

| Class | Algorithm | Location | Use Case |
|-------|-----------|----------|----------|
| `RegimeDetector` | KMeans + GaussianMixture | `regime_detector.py:10` | Fast, sklearn-based |
| `HiddenMarkovRegimeDetector` | HMM (Baum-Welch) | `regime_detector.py:356` | Accurate, full POMDP |

### 8.2 RegimeDetector Methods (line 10)#

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__(n_regimes=8, feature_dim=10)` | Config | None | 15 |
| `fit(features)` | np.ndarray | Self | GMM/KMeans | 66 |
| `predict_regime(features)` | np.ndarray | `(regime_idx, probs, metadata)` | Main | 97 |
| `predict_next_regime(current_regime)` | int | `(next_regime, prob)` | Markov | 237 |

---

## 9. Kronos Integration (`learning/kronos_integration.py`)#

### 9.1 KronosIntegration#

```python
class KronosIntegration:
    """Integrates Kronos time-series models"""
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__(config: KronosConfig)` | Config | None | 44 |
| `load()` | None | `bool` | Load Kronos | 59 |
| `update_market_data(price, volume, timestamp)` | floats | None | Update state | 129 |
| `predict_regime()` | None | `Dict[str, Any]` | Regime forecast | 142 |
| `predict_volatility(horizon)` | int=20 | `Dict[str, float]` | Vol forecast | 185 |
| `predict_returns(horizon)` | int=5 | `Dict[str, float]` | Return forecast | 249 |
| `detect_anomaly()` | None | `Dict[str, Any]` | Anomaly score | 217 |
| `get_kronos_status()` | None | `Dict[str, Any]` | Status | 340 |
| `save_state(filepath)` | str | None | Save | 356 |
| `load_state(filepath)` | str | None | Load | 377 |

---

## 10. Feature Pipeline (`learning/feature_pipeline.py`)#

### 10.1 AdvancedFeaturePipeline (line 16)#

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__(config)` | Dict | None | 22 |
| `compute_microstructure_features(market_data)` | Dict | `Dict[str, float]` | OFI, I*, L*, S* | 37 |
| `normalize_features(features)` | Dict[str,float] | `Dict[str, float]` | Z-score | 200 |
| `get_feature_importance_weights()` | None | `Dict[str, float]` | Current weights | 268 |
| `get_feature_vector(features)` | Dict[str,float] | np.ndarray | Feature array | 293 |
| `check_stationarity(feature_name)` | str | `Dict[str, Any]` | ADF test | 337 |
| `validate_features(features)` | Dict[str,float] | `(bool, List[str])` | Validate | 378 |

### 10.2 FeatureSelector (line 411)#

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__(max_features=20)` | int | None | 416 |
| `update_scores(feature_names, performance_impact)` | List, Dict | None | Update | 421 |
| `select_features(available_features)` | List[str] | `List[str]` | Top N | 431 |

---

## 11. Learning Configuration (`config/learning.yaml`)#

```yaml
# From config/learning.yaml
learning:
  enabled: true
  adaptation_rate: 0.008
  min_samples: 30
  update_frequency: 1800  # seconds (30 min)
  
  weight_optimization:
    enabled: true
    learning_rate: 0.008
    min_weight: 0.08
    max_history: 800
  
  drift_detection:
    enabled: true
    threshold: 0.03
    window_size: 80
    severity_levels:
      minor: 0.2
      moderate: 0.5
      severe: 0.8
```

---

## 12. Retraining Trigger Conditions#

| Condition | Trigger | Action |
|-----------|---------|--------|
| **Every N Trades** | `update_frequency=1800s` | Retrain all models |
| **Drift Score** | `>0.03` threshold | Check severity level |
| **Win Rate Drop** | `<config.min_confidence_threshold` | Reduce confidence requirement |
| **Sharpe Drop** | `<1.0` | Re-initialize ensemble |
| **Manual** | Admin command | Force retrain |

---

## 13. Model Performance Metrics#

### 13.1 Tracked Metrics#

| Metric | Description | Target |
|--------|-------------|--------|
| **Win Rate** | `wins / total_closed` | ≥65% |
| **Sharpe Ratio** | `(R_p - R_f) / σ_p` | ≥3.0 |
| **Max Drawdown** | `max(peak - trough)` | <10% |
| **Profit Factor** | `gross_profit / |gross_loss|` | ≥4.0 |
| **Expectancy** | `(win_rate × avg_win) - (loss_rate × avg_loss)` | ≥+0.005 |

### 13.2 Model Comparison (`model_registry.compare_versions()`)#

```python
comparison = registry.compare_versions('xgboost')
# Returns:
{
  'versions': [
    {'version': 'v1.0.0', 'win_rate': 0.62, 'sharpe': 1.1, ...},
    {'version': 'v1.0.1', 'win_rate': 0.68, 'sharpe': 1.3, ...},  # ← BEST
  ],
  'best_version': 'v1.0.1',
  'improvement': '+6% win rate, +0.2 Sharpe'
}
```

---

## 14. Learning Loop Status#

**Current Status:**

| Item | Status |
|------|--------|
| **Online Learning** | ⚠️ `continuous_learning_loop.py` exists but uses non-binance loop |
| **Drift Detection** | ✅ Implemented in `regime_detector.py` |
| **Model Versioning** | ✅ `ModelRegistry` fully implemented |
| **A/B Testing** | ✅ `ABTestManager` available |
| **Ensemble Training** | ✅ 4 model types supported |
| **Win Rate** | ~35% (target: ≥65%) |
| **Retraining Frequency** | Every 30 min / 20 trades |

**⚠️ Gap:** The `continuous_learning_loop.py` (non-binance version) should be merged with `continuous_trading_loop_binance.py` to enable online learning with real Binance data.

---

*Document Version: 1.0 | Date: 2026-05-04 | System: v3.2.0*
