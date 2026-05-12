"""
Simple example demonstrating the unified trading system components working together.
Run from within the unified_trading_system directory.
"""

import time
import numpy as np
from perception.belief_state import BeliefStateEstimator
from decision.aggression_controller import AggressionController
from execution.smart_order_router import ExecutionModel, ExecutionIntent
from risk.unified_risk_manager import RiskManifold
from feedback.monitoring_engine import FeedbackLayer
from adaptation.drift_detector import AdaptationLayer
from perception.event_system import EventBus, EventFactory, EventType
from config.config_manager import ConfigManager

def run_simple_demo():
    """Run a simple demonstration of the unified trading system."""
    
    print("🚀 Unified Trading System - Simple Demonstration")
    print("=" * 55)
    
    # Ensure default configuration exists
    ConfigManager.create_default_config()
    print("✅ Configuration initialized")
    
    # Initialize all components
    event_bus = EventBus()
    belief_estimator = BeliefStateEstimator()
    aggression_controller = AggressionController()
    execution_model = ExecutionModel()
    risk_manager = RiskManifold()
    feedback_layer = FeedbackLayer()
    adaptation_layer = AdaptationLayer()
    
    print("✅ All components initialized")
    
    # Track events for demonstration
    received_events = []
    
    # Simple event handler for demonstration
    def event_handler(event):
        received_events.append(event)
        # Only show first few events to avoid too much output
        if len(received_events) <= 3:
            timestamp = event.metadata.timestamp / 1e9  # Convert to seconds
            print(f"📡 Event: {event.event_type.value} at {timestamp:.3f}s")
    
    # Subscribe to key events
    for event_type in [EventType.BELIEF_STATE_UPDATE, EventType.AGGRESSION_UPDATE, 
                      EventType.RISK_ASSESSMENT, EventType.TRADE_EXECUTED]:
        event_bus.subscribe(event_type, event_handler)
    
    print("✅ Event subscriptions configured")
    print("-" * 55)
    
    # Run a few iterations of the trading loop
    print("🔄 Running trading loop iterations...")
    
    for i in range(5):
        print(f"\nIteration {i+1}:")
        
        # 1. Simulate market data
        market_data = {
            "bid_price": 50000.0 + np.random.normal(0, 10),
            "ask_price": 50010.0 + np.random.normal(0, 10),
            "bid_size": np.random.uniform(1.0, 3.0),
            "ask_size": np.random.uniform(1.0, 3.0),
            "last_price": 50005.0 + np.random.normal(0, 5),
            "last_size": np.random.uniform(0.5, 2.0),
            "volume": np.random.uniform(50.0, 150.0),
            "mid_price": 50005.0 + np.random.normal(0, 5),
            "spread_bps": abs(np.random.normal(2.0, 0.5)),
            "volatility_estimate": np.clip(0.15 + np.random.normal(0, 0.03), 0.05, 0.3),
            "liquidity_estimate": np.clip(0.6 + np.random.normal(0, 0.1), 0.2, 0.9)
        }
        
        # 2. Perception: Update belief state
        belief_state = belief_estimator.update(market_data)
        belief_event = EventFactory.create_belief_state_update(
            expected_return=belief_state.expected_return,
            expected_return_uncertainty=belief_state.expected_return_uncertainty,
            aleatoric_uncertainty=belief_state.aleatoric_uncertainty,
            epistemic_uncertainty=belief_state.epistemic_uncertainty,
            regime_probabilities=belief_state.regime_probabilities
        )
        event_bus.publish(belief_event)
        
        # 3. Decision: Update aggression
        aggression_state = aggression_controller.update(
            belief_state={
                "expected_return": belief_state.expected_return,
                "expected_return_uncertainty": belief_state.expected_return_uncertainty,
                "aleatoric_uncertainty": belief_state.aleatoric_uncertainty,
                "epistemic_uncertainty": belief_state.epistemic_uncertainty,
                "regime_probabilities": belief_state.regime_probabilities,
                "volatility_estimate": belief_state.volatility_estimate,
                "liquidity_estimate": belief_state.liquidity_estimate,
                "momentum_signal": belief_state.momentum_signal,
                "volume_signal": belief_state.volume_signal,
                "confidence": belief_state.confidence
            },
            signal_strength=0.2 + 0.3 * np.random.random(),
            execution_feedback=0.0
        )
        aggression_event = EventFactory.create_aggression_update(
            aggression_level=aggression_state.aggression_level,
            signal_strength=0.2 + 0.3 * np.random.random(),
            risk_gradient=aggression_state.risk_gradient,
            aggression_rate=aggression_state.aggression_rate,
            execution_feedback=0.0
        )
        event_bus.publish(aggression_event)
        
        # 4. Risk: Assess risk
        portfolio_state = {
            "drawdown": max(0.0, -np.random.exponential(0.01)),
            "daily_pnl": np.random.normal(0.0002, 0.005),
            "leverage_ratio": np.clip(0.25 + np.random.normal(0, 0.1), 0.0, 0.8),
            "total_value": 100000.0 + np.random.normal(0, 2000)
        }
        
        risk_assessment = risk_manager.assess_risk(
            belief_state={
                "expected_return": belief_state.expected_return,
                "expected_return_uncertainty": belief_state.expected_return_uncertainty,
                "aleatoric_uncertainty": belief_state.aleatoric_uncertainty,
                "epistemic_uncertainty": belief_state.epistemic_uncertainty,
                "regime_probabilities": belief_state.regime_probabilities,
                "volatility_estimate": belief_state.volatility_estimate,
                "liquidity_estimate": belief_state.liquidity_estimate,
                "entropy": belief_state.get_entropy()
            },
            portfolio_state=portfolio_state,
            market_data={
                "volatility": belief_state.volatility_estimate,
                "spread_bps": market_data["spread_bps"],
                "liquidity": belief_state.liquidity_estimate
            }
        )
        
        risk_event = EventFactory.create_risk_assessment(
            risk_level=risk_assessment.risk_level.value,
            cvar=risk_assessment.cvar,
            volatility=risk_assessment.volatility,
            drawdown=risk_assessment.drawdown,
            leverage_ratio=risk_assessment.leverage_ratio,
            liquidity_score=risk_assessment.liquidity_score,
            correlation_risk=risk_assessment.correlation_risk,
            protective_action=risk_assessment.protective_action
        )
        event_bus.publish(risk_event)
        
        # 5. Execution: Create and simulate plan if conditions allow
        if (aggression_state.aggression_level > 0.1 and 
            risk_assessment.protective_action in ["NONE", "REDUCE_SIZE"]):
            
            execution_intent = ExecutionIntent(
                symbol="BTCUSDT",
                side="BUY" if belief_state.expected_return > 0 else "SELL",
                quantity=min(0.005 * belief_state.liquidity_estimate * 1000, 2.0),
                urgency=min(aggression_state.aggression_level + 0.1, 1.0),
                max_slippage=5.0,
                min_time_limit=1.0,
                max_time_limit=5.0,
                aggression_level=aggression_state.aggression_level,
                timestamp=int(time.time() * 1e9)
            )
            
            plan = execution_model.plan_execution(execution_intent, {
                "symbol": "BTCUSDT",
                "mid_price": market_data["mid_price"],
                "spread_bps": market_data["spread_bps"],
                "volatility_estimate": belief_state.volatility_estimate,
                "liquidity_estimate": belief_state.liquidity_estimate
            })
            
            execution_result = execution_model.simulate_execution(plan, {
                "symbol": "BTCUSDT",
                "mid_price": market_data["mid_price"],
                "spread_bps": market_data["spread_bps"],
                "volatility_estimate": belief_state.volatility_estimate,
                "liquidity_estimate": belief_state.liquidity_estimate
            })
            
            if execution_result.filled_quantity > 0:
                trade_event = EventFactory.create_trade_executed(
                    symbol="BTCUSDT",
                    side=execution_intent.side,
                    quantity=execution_result.filled_quantity,
                    price=execution_result.average_price,
                    timestamp=execution_result.timestamp,
                    commission=0.5,
                    slippage=execution_result.slippage,
                    latency=execution_result.latency
                )
                event_bus.publish(trade_event)
                
                # 6. Feedback: Process trade result
                trade_result = {
                    "timestamp": execution_result.timestamp,
                    "symbol": "BTCUSDT",
                    "side": execution_intent.side,
                    "filled_quantity": execution_result.filled_quantity,
                    "average_price": execution_result.average_price,
                    "commission": 0.5
                }
                
                current_positions = {
                    "BTCUSDT": {
                        "quantity": execution_result.filled_quantity,
                        "avg_price": execution_result.average_price
                    }
                } if execution_result.filled_quantity > 0 else {}
                
                market_prices = {"BTCUSDT": market_data["last_price"]}
                
                component_latencies = {
                    "perception": 2.0,
                    "decision": 1.5,
                    "execution": execution_result.latency,
                    "feedback": 1.0
                }
                
                feedback_layer.update_all(
                    trade_result=trade_result,
                    current_positions=current_positions,
                    market_prices=market_prices,
                    belief_state={
                        "expected_return": belief_state.expected_return,
                        "expected_return_uncertainty": belief_state.expected_return_uncertainty,
                        "aleatoric_uncertainty": belief_state.aleatoric_uncertainty,
                        "epistemic_uncertainty": belief_state.epistemic_uncertainty,
                        "regime_probabilities": belief_state.regime_probabilities,
                        "volatility_estimate": belief_state.volatility_estimate,
                        "liquidity_estimate": belief_state.liquidity_estimate,
                        "momentum_signal": belief_state.momentum_signal,
                        "volume_signal": belief_state.volume_signal,
                        "confidence": belief_state.confidence
                    },
                    execution_result={
                        "status": execution_result.status.value,
                        "filled_quantity": execution_result.filled_quantity,
                        "average_price": execution_result.average_price,
                        "slippage": execution_result.slippage,
                        "latency": execution_result.latency,
                        "market_impact": execution_result.market_impact
                    },
                    market_data={
                        "signal_strength": 0.2 + 0.3 * np.random.random(),
                        "volatility_estimate": belief_state.volatility_estimate,
                        "liquidity_estimate": belief_state.liquidity_estimate,
                        "spread_bps": market_data["spread_bps"]
                    },
                    component_latencies=component_latencies,
                    error_events=[],
                    system_health={
                        "perception": True,
                        "decision": True,
                        "execution": True,
                        "feedback": True
                    },
                    model_info={
                        "model_version": "v1.0.0",
                        "feature_importance": {
                            "ofI": 0.2,
                            "I_star": 0.15,
                            "volatility": 0.15,
                            "liquidity": 0.15,
                            "momentum": 0.1,
                            "volume": 0.1,
                            "regime_probs": 0.1
                        }
                    }
                )
        
        # Brief pause between iterations
        time.sleep(0.5)
    
    # Summary
    print("-" * 55)
    print("📊 DEMONSTRATION SUMMARY")
    print("-" * 55)
    print(f"Total Events Processed: {len(received_events)}")
    print(f"Belief State Updates: {len([e for e in received_events if e.event_type == EventType.BELIEF_STATE_UPDATE])}")
    print(f"Aggression Updates: {len([e for e in received_events if e.event_type == EventType.AGGRESSION_UPDATE])}")
    print(f"Risk Assessments: {len([e for e in received_events if e.event_type == EventType.RISK_ASSESSMENT])}")
    print(f"Trades Executed: {sum(1 for e in received_events if e.event_type == EventType.TRADE_EXECUTED)}")
    print()
    print("🎯 Key Takeaways:")
    print("   • All components communicate through the unified event system")
    print("   • Data flows sequentially: Market → Perception → Decision → Risk → Execution → Feedback")
    print("   • Adaptation layer monitors for concept drift and model degradation")
    print("   • Configuration management ensures consistent system behavior")
    print("   • Feedback loop enables continuous learning and improvement")
    print()
    print("✅ Demonstration completed successfully!")
    print("💡 To run a live trading system, connect real market data feeds and execution APIs")

if __name__ == "__main__":
    run_simple_demo()