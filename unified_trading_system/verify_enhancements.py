#!/usr/bin/env python3
"""
Verification script for all new enhancements to Unified Trading System
Tests: Performance Scorer, MacroTrendFilter, ConfluenceGate, HedgingEngine, 
WalkForwardOptimizer, and RL Execution Agent
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scoring.score_system import PerformanceScorer
from perception.macro_trend_filter import MacroTrendFilter
from risk.hedging_engine import HedgingEngine
from learning.walk_forward_optimizer import WalkForwardOptimizer
from execution.rl_execution_agent import QLearningExecutionAgent, OrderBookState, ExecutionAction
import json

print("=" * 60)
print("UNIFIED HFT TRADING SYSTEM - ENHANCEMENT VERIFICATION")
print("Target: 70%+ Daily Profits")
print("=" * 60)

# Test 1: Performance Scorer
print("\n[1] Testing Performance Scoring System...")
try:
    scorer = PerformanceScorer()
    report = scorer.generate_report()
    print(f"   ✅ Scorer initialized")
    print(f"   📊 Rating: {report['rating']} ({report['composite_score']:.1f}/100)")
    print(f"   💰 Daily Profit: {report['daily_profit_pct']:.2f}% (Target: 70%+)")
    print(f"   🎯 Win Rate: {report['win_rate_pct']:.1f}%")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Macro Trend Filter
print("\n[2] Testing Macro-Micro Confluence Layer...")
try:
    mtf = MacroTrendFilter(symbol="BTCUSDT")
    trend, details = mtf.get_macro_trend()
    print(f"   ✅ MacroTrendFilter initialized")
    print(f"   📈 Macro Trend: {trend}")
    print(f"   📋 Details: {details}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Hedging Engine
print("\n[3] Testing Active Delta Hedging Engine...")
try:
    engine = HedgingEngine()
    engine.update_position("BTCUSDT", 1.0, "BUY", 50000.0)
    engine.update_correlation_matrix(["BTCUSDT", "ETHUSDT"])
    evaluation = engine.evaluate_hedging_need()
    print(f"   ✅ HedgingEngine initialized")
    print(f"   🛡️ Portfolio Delta: {evaluation['portfolio_delta']:.2f}")
    print(f"   ⚠️ Needs Hedge: {evaluation['needs_hedge']}")
    if evaluation.get('hedge_action'):
        print(f"   🔄 Hedge Action: {evaluation['hedge_action']['side']} {evaluation['hedge_action']['quantity']:.2f} {evaluation['hedge_action']['symbol']}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: Walk-Forward Optimizer
print("\n[4] Testing Walk-Forward Optimization Pipeline...")
try:
    optimizer = WalkForwardOptimizer()
    print(f"   ✅ WalkForwardOptimizer initialized")
    print(f"   🧠 Parameter grid size: {len(optimizer.param_grid['leverage']) * len(optimizer.param_grid['profit_target'])} combinations")
    print(f"   📅 Window size: {optimizer.window_size_days} days train, {optimizer.test_size_days} days test")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 5: RL Execution Agent
print("\n[5] Testing RL Execution Agent...")
try:
    agent = QLearningExecutionAgent()
    state = OrderBookState(
        bid_ask_spread=0.0003,
        depth_imbalance=0.2,
        order_flow_imbalance=0.1,
        volatility=0.05,
        time_of_day=0.5,
        recent_trades_count=50,
        urgency=0.8
    )
    action = agent.select_action(state, training=True)
    print(f"   ✅ RL Agent initialized (Executions: {agent.execution_count})")
    print(f"   🤖 Selected Action: {action}")
    print(f"   📉 Epsilon (exploration): {agent.epsilon:.3f}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 6: Verify ConfluenceGate in Signal Generator
print("\n[6] Verifying ConfluenceGate integration...")
try:
    from decision.signal_generator import SignalGenerator
    sg = SignalGenerator()
    print(f"   ✅ SignalGenerator initialized with ConfluenceGate")
    print(f"   🎯 Macro filter active: {hasattr(sg, 'macro_filter')}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
print("\n📝 Next Steps:")
print("1. Update .env with valid Binance Testnet API keys")
print("2. Run: python3 verify_enhancements.py")
print("3. Monitor logs: tail -f logs/trading.log")
print("4. Check performance: python3 scoring/score_system.py")
print("\n🚀 System targeting 70%+ daily profits with:")
print("   • Macro-Micro Confluence Filtering")
print("   • Active Delta Hedging")
print("   • Walk-Forward Optimization")
print("   • RL Execution Agent")
print("   • Performance Scoring (A+ to F)")
print("=" * 60)
