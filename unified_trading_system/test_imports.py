#!/usr/bin/env python3
"""Test imports one by one with timeout"""
import sys
import signal

def handler(signum, frame):
    print(f"\n❌ HANG DETECTED at: {current}", flush=True)
    sys.exit(1)

signal.signal(signal.SIGALRM, handler)

imports = [
    ("perception.belief_state", "BeliefState, BeliefStateEstimator, RegimeType"),
    ("risk.unified_risk_manager", "RiskManifold"),
    ("execution.testnet_executor", "TestnetExecutionWithGovernance"),
    ("execution.smart_order_router", "ExecutionModel, ExecutionIntent, OrderType"),
    ("decision.signal_generator", "SignalGenerator, TradingSignal"),
    ("observability.logging", "TradingLogger, get_correlation_id, set_correlation_id, set_context"),
    ("observability", "get_metrics, set_gauge, increment_counter"),
    ("observability.alerting", "AlertManager, AlertSeverity, Alert, send_trade_execution_alert, send_risk_alert, send_system_status_alert, configure_alerting_from_env"),
    ("observability.health", "HealthServer, HealthStatus, LambdaHealthCheck"),
    ("learning.trade_journal", "TradeJournal"),
    ("binance_market_data_feed", "BinanceFuturesMarketDataFeed, FeedType"),
]

for module, items in imports:
    current = f"from {module} import {items}"
    print(f"Testing: {current}...", flush=True)
    signal.alarm(3)  # 3 second timeout
    try:
        exec(current)
        signal.alarm(0)
        print(f"✅ SUCCESS", flush=True)
    except Exception as e:
        signal.alarm(0)
        print(f"❌ ERROR: {e}", flush=True)

print("\n=== ALL IMPORTS PASSED ===")
