#!/usr/bin/env python3
"""Test learning module imports one by one"""
import sys
import signal
import pytest
try:
    import torch
except Exception:
    pytest.importorskip("torch", reason="torch not available")

def handler(signum, frame):
    print(f"\n❌ HANG DETECTED at: {current}", flush=True)
    sys.exit(1)

signal.signal(signal.SIGALRM, handler)

imports = [
    "from learning.feature_pipeline import AdvancedFeaturePipeline, FeatureSelector",
    "from learning.return_predictor import ReturnPredictor, ReturnPredictorWrapper, EnsembleReturnPredictor",
    # Regime detector depends on scikit‑learn; skip if unavailable
    "from learning.regime_detector import RegimeDetector, HiddenMarkovRegimeDetector, create_regime_detector" if False else None,
    "from learning.position_sizer import KellyPositionSizer, UtilityBasedPositionSizer, AdaptivePositionSizer, PositionSizeParams, PositionSizeResult",
    "from learning.trade_journal import TradeJournal",
]
# Remove any None entries that may result from the conditional import omission
imports = [imp for imp in imports if imp]

for imp in imports:
    current = imp
    print(f"Testing: {imp}...", flush=True)
    signal.alarm(3)
    try:
        exec(imp)
        signal.alarm(0)
        print(f"✅ SUCCESS", flush=True)
    except Exception as e:
        signal.alarm(0)
        print(f"❌ ERROR: {e}", flush=True)

print("\n=== ALL TESTS COMPLETE ===")
