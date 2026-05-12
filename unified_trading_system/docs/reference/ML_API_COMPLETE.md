# ML API Complete Reference

Complete API documentation for all 299 ML/AI functions and classes across 7 modules in the Unified Trading System.

---

## 1. `learning/return_predictor.py` (PyTorch NN Models)

### 1.1 Classes

#### `TemporalConvNet(nn.Module)` (line 18)
```python
class TemporalConvNet(nn.Module):
    """Temporal Convolutional Network for return prediction"""
```
| Method | Args | Returns | Line |
|--------|------|---------|------|
| `__init__(input_size=10, num_channels=[64,128,256], kernel_size=3)` | Input dim, channel sizes, kernel | None | 18 |
| `forward(x: torch.Tensor) -> torch.Tensor` | Batch of sequences [B, seq, features] | Predictions [B, 1] | ~30 |

#### `TemporalBlock(nn.Module)` (line 50)
```python
class TemporalBlock(nn.Module):
    """Single TCN block with dilated convolutions"""
```
| Method | Args | Returns | Line |
|--------|------|---------|------|
| `__init__(in_channels, out_channels, kernel_size, stride, dilation, padding, dropout=0.2)` | Channel config | None | 50 |
| `forward(x: torch.Tensor) -> torch.Tensor` | [B, C, L] | [B, C_out, L] | ~65 |

#### `TransformerEncoder(nn.Module)` (line 78)
```python
class TransformerEncoder(nn.Module):
    """Transformer encoder for return prediction"""
```
| Method | Args | Returns | Line |
|--------|------|---------|------|
| `__init__(input_size=10, d_model=128, nhead=4, num_layers=3, dropout=0.2)` | Model config | None | 78 |
| `forward(x: torch.Tensor) -> torch.Tensor` | [B, seq, input_size] | [B, 1] | ~95 |

#### `ReturnPredictor(nn.Module)` (line 103)
```python
class ReturnPredictor(nn.Module):
    """Ensemble return predictor combining TCN + Transformer"""
```
| Method | Args | Returns | Line |
|--------|------|---------|------|
| `__init__(input_size=10, hidden_size=64, num_layers=2, dropout=0.2)` | Model config | None | 103 |
| `forward(x: torch.Tensor) -> torch.Tensor` | [B, seq, features] | [B, 1] | ~120 |
| `predict(feature_vector: np.ndarray) -> float` | Single feature vector | Predicted return | 242 |

**Key Methods on `ReturnPredictor` instance:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `predict_return()` | `feature_vector: np.ndarray, context: Dict = None) -> Dict[str, Any]` | `{'prediction': float, 'confidence': float, 'features_used': int}` | Main prediction call | 242 |
| `train_batch()` | `sequences: torch.Tensor, targets: torch.Tensor) -> float` | Loss value | 265 |
| `validate_batch()` | `sequences: torch.Tensor, targets: torch.Tensor) -> float` | Validation loss | 292 |
| `save()` | `filepath: str` | None | Saves `{'model_state': ..., 'config': ..., 'training_history': ...}` | 315 |
| `load()` | `filepath: str` | `bool` | Loads model from path | 331 |
| `prepare_sequence()` | `feature_vector: np.ndarray) -> torch.Tensor` | [1, seq_len, features] | 231 |

---

## 2. `learning/ensemble_trainer.py` (XGBoost + LSTM + Transformer + RF)

### 2.1 Main Class: `EnsembleTrainer` (line 18)

```python
class EnsembleTrainer:
    """Trains and ensembles multiple model types"""
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__(config: Dict = None)` | Config dict | None | 24 |
| `load_real_trades()` | None | `(X: np.ndarray, y: np.ndarray)` | Loads from TradeJournal | 38 |
| `train_xgboost()` | `X: np.ndarray, y: np.ndarray) -> Dict[str, Any]` | `{'model': xgb.Booster, 'feature_importance': List, ...}` | XGBoost training | 114 |
| `train_lstm()` | `X: np.ndarray, y: np.ndarray) -> Dict[str, Any]` | `{'model': nn.Module, 'history': List, ...}` | LSTM training | 153 |
| `train_transformer()` | `X: np.ndarray, y: np.ndarray) -> Dict[str, Any]` | `{'model': nn.Module, 'history': List, ...}` | Transformer training | 211 |
| `train_random_forest()` | `X: np.ndarray, y: np.ndarray) -> Dict[str, Any]` | `{'model': RandomForestRegressor, 'feature_importance': List, ...}` | sklearn RF | 239 |
| `_simulate_model()` | `model_name: str, X, y) -> Dict[str, Any]` | Metrics dict | 266 |
| `_calculate_win_rate()` | `y_true, y_pred) -> float` | Win rate % | 284 |
| `train_ensemble()` | None | `Dict[str, Any]` | Trains all 4 model types + combines | 294 |

### 2.2 Inner LSTM Class (line 171)

```python
class SimpleLSTM(nn.Module):
    """Simple LSTM for return prediction"""
```
| Method | Args | Returns |
|--------|------|---------|
| `__init__(input_size=10, hidden_size=64)` | Model config | None |
| `forward(x: torch.Tensor) -> torch.Tensor` | [B, seq, input_size] | [B, 1] |
```

---

## 3. `learning/regime_detector.py` (HMM + KMeans + GMM)

### 3.1 Class: `RegimeDetector` (line 10)

```python
class RegimeDetector:
    """Hidden Markov Model regime detector"""
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__(n_regimes=8, feature_dim=10)` | Config | None | 15 |
| `fit()` | `features: np.ndarray) -> 'RegimeDetector'` | Self | Fits GMM/KMeans | 66 |
| `predict_regime()` | `features: np.ndarray) -> Tuple[int, np.ndarray, Dict]` | `(regime_idx, probabilities, metadata)` | Main prediction | 97 |
| `predict_next_regime()` | `current_regime: int) -> Tuple[int, float]` | `(next_regime, transition_prob)` | Markov prediction | 237 |

### 3.2 Class: `HiddenMarkovRegimeDetector` (line 356)

```python
class HiddenMarkovRegimeDetector:
    """HMM using Baum-Welch / Viterbi"""
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__(n_regimes=8)` | Config | None | 356 |
| `fit()` | `features: np.ndarray) -> 'HiddenMarkovRegimeDetector'` | Self | Baum-Welch | 356 |
| `predict_regime()` | `features: np.ndarray) -> Tuple[int, np.ndarray]` | `(regime, posteriors)` | Viterbi | 397 |

---

## 4. `learning/kronos_integration.py` (Time-Series Forecasting)

### 4.1 Class: `KronosConfig` (line 20)

```python
@dataclass
class KronosConfig:
    """Configuration for Kronos time-series integration"""
    history_len: int = 100
    forecast_horizon: int = 20
    model_path: str = "./models/kronos"
```

### 4.2 Class: `KronosIntegration` (line 32)

```python
class KronosIntegration:
    """Integrates Kronos time-series models for trading"""
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__(config: KronosConfig = None)` | Config | None | 44 |
| `load()` | None | `bool` | Loads Kronos models | 59 |
| `update_market_data()` | `price: float, volume: float, timestamp: float)` | None | Updates internal state | 129 |
| `predict_regime()` | None | `Dict[str, Any]` | `{'regime': str, 'probabilities': List, ...}` | 142 |
| `predict_volatility()` | `horizon: int = 20) -> Dict[str, float]` | `{'forecast': [float], 'confidence': float, ...}` | Volatility forecast | 185 |
| `predict_returns()` | `horizon: int = 5) -> Dict[str, float]` | `{'forecast': [float], 'confidence': float, ...}` | Return forecast | 249 |
| `detect_anomaly()` | None | `Dict[str, Any]` | `{'is_anomaly': bool, 'score': float, ...}` | 217 |
| `get_kronos_status()` | None | `Dict[str, Any]` | Status dict | 340 |
| `save_state()` | `filepath: str` | None | Saves state | 356 |
| `load_state()` | `filepath: str` | `bool` | Loads state | 377 |

---

## 5. `learning/model_registry.py` (Model Versioning + A/B Testing)

### 5.1 Class: `ModelVersion` (line 19)

```python
@dataclass
class ModelVersion:
    """Versioned model metadata"""
    name: str
    version_id: str
    model_type: str          # 'xgboost', 'lstm', 'transformer', 'rf'
    metrics: Dict[str, float]
    created_at: float
    is_active: bool = False
    is_production: bool = False
```

### 5.2 Class: `ModelRegistry` (line 30)

```python
class ModelRegistry:
    """Registry for model versioning and A/B testing"""
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__(base_path: str = "./models")` | Path | None | 35 |
| `register_model()` | `name, version_id, model, metrics, metadata = None) -> bool` | Success | 91 |
| `activate_model()` | `name: str, version_id: str) -> bool` | Success | 129 |
| `promote_to_production()` | `name: str, version_id: str) -> bool` | Success | 167 |
| `rollback()` | `name: str) -> bool` | Success (rolls to previous prod) | 210 |
| `get_active_version()` | `name: str) -> Optional[ModelVersion]` | Active version | 232 |
| `get_production_version()` | `name: str) -> Optional[ModelVersion]` | Prod version | 247 |
| `get_model_versions()` | `name: str) -> List[ModelVersion]` | All versions | 262 |
| `compare_versions()` | `name: str) -> Dict[str, Any]` | Comparison metrics | 268 |
| `cleanup_old_versions()` | `name: str, keep_n: int = 5) -> int` | Deleted count | 295 |

### 5.3 Class: `ABTestManager` (line 333)

```python
class ABTestManager:
    """Manages A/B testing of models"""
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__(registry: ModelRegistry)` | Registry ref | None | 333 |
| `start_test()` | `name: str, version_a, version_b, traffic_split=0.5) -> str` | Test ID | Starts A/B test |
| `record_result()` | `test_id: str, version: str, outcome: Dict)` | None | Records outcome |
| `get_test_results()` | `test_id: str) -> Dict[str, Any]` | Results + winner | Gets results |

---

## 6. `learning/feature_pipeline.py` (Advanced Feature Engineering)

### 6.1 Class: `AdvancedFeaturePipeline` (line 16)

```python
class AdvancedFeaturePipeline:
    """Computes LVR microstructure + other features"""
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__(config: Dict = None)` | Config | None | 22 |
| `compute_microstructure_features()` | `market_data: Dict) -> Dict[str, float]` | `{'OFI': float, 'I_star': float, 'L_star': float, 'S_star': float, ...}` | LVR features | 37 |
| `normalize_features()` | `features: Dict[str, float]) -> Dict[str, float]` | Normalized | 200 |
| `get_feature_importance_weights()` | None | `Dict[str, float]` | Current weights | 268 |
| `get_feature_vector()` | `features: Dict[str, float]) -> np.ndarray` | Feature array | 293 |
| `check_stationarity()` | `feature_name: str = None) -> Dict[str, Any]` | Stationarity report | 337 |
| `validate_features()` | `features: Dict[str, float]) -> Tuple[bool, List[str]]` | `(is_valid, errors)` | 378 |

### 6.2 Class: `FeatureSelector` (line 411)

```python
class FeatureSelector:
    """Selects top features based on performance impact"""
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__(max_features: int = 20)` | Config | None | 416 |
| `update_scores()` | `feature_names: List[str], performance_impact: Dict[str, float])` | None | 421 |
| `select_features()` | `available_features: List[str]) -> List[str]` | Top features | 431 |

---

## 7. `perception/belief_state.py` (POMDP Belief State)

### 7.1 Enum: `RegimeType` (line 15)

```python
class RegimeType(Enum):
    BULL_LOW_VOL = 0
    BULL_HIGH_VOL = 1
    BEAR_LOW_VOL = 2
    BEAR_HIGH_VOL = 3
    SIDEWAYS_LOW_VOL = 4
    SIDEWAYS_HIGH_VOL = 5
    CRISIS = 6
    RECOVERY = 7
```

### 7.2 Class: `BeliefState` (line 28)

```python
@dataclass
class BeliefState:
    """POMDP belief state"""
    expected_return: float
    expected_return_uncertainty: float
    aleatoric_uncertainty: float
    epistemic_uncertainty: float
    regime_probabilities: List[float]   # 8 probabilities
    microstructure_features: Dict[str, float]
    volatility_estimate: float
    liquidity_estimate: float
    momentum_signal: float
    volume_signal: float
    timestamp: int
    confidence: float
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `to_dict()` | None | `Dict` | Serialization | 51 |
| `from_dict(data: Dict)` | `Dict` | `BeliefState` | Deserialization | 68 |

### 7.3 Class: `BeliefStateEstimator` (line 110)

```python
class BeliefStateEstimator:
    """Estimates POMDP belief state from market data"""
```

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__()` | None | None | 110 |
| `update()` | `market_data: Dict) -> BeliefState` | Updated state | 156 |
| `get_most_likely_regime()` | None | `Tuple[RegimeType, float]` | `(regime, probability)` | 175 |
| `_initialize_transition_matrix()` | None | `np.ndarray` | 8×8 matrix | 124 |

---

## 8. Usage Example: Ensemble Prediction Flow

```python
from learning.ensemble_trainer import EnsembleTrainer
from learning.return_predictor import ReturnPredictor
from perception.belief_state import BeliefStateEstimator

# 1. Load/generate training data
trainer = EnsembleTrainer()
X, y = trainer.load_real_trades()

# 2. Train ensemble (XGBoost + LSTM + Transformer + RF)
results = trainer.train_ensemble()
# Returns: {'xgboost': {...}, 'lstm': {...}, 'transformer': {...}, 'rf': {...}}

# 3. Make prediction with ReturnPredictor
predictor = ReturnPredictor()
feature_vector = get_latest_features()
prediction = predictor.predict_return(feature_vector)
# Returns: {'prediction': 0.0023, 'confidence': 0.89, ...}

# 4. Update belief state
estimator = BeliefStateEstimator()
market_data = get_market_data("BTC/USDT")
belief_state = estimator.update(market_data)
regime, prob = belief_state.get_most_likely_regime()
```

---

## 9. Module Import Quick Reference

```python
# Regime Detection
from learning.regime_detector import RegimeDetector, HiddenMarkovRegimeDetector

# Return Prediction
from learning.return_predictor import ReturnPredictor, TemporalConvNet, TransformerEncoder

# Ensemble Training
from learning.ensemble_trainer import EnsembleTrainer

# Kronos Integration
from learning.kronos_integration import KronosIntegration, KronosConfig

# Model Management
from learning.model_registry import ModelRegistry, ModelVersion, ABTestManager

# Feature Pipeline
from learning.feature_pipeline import AdvancedFeaturePipeline, FeatureSelector

# Belief State (POMDP)
from perception.belief_state import BeliefState, BeliefStateEstimator, RegimeType
```

---

*Document Version: 1.0 | Date: 2026-05-04 | System: v3.2.0 | Total Functions/Classes: 299*
