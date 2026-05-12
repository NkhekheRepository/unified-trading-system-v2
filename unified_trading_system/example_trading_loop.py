"""
Example Trading Loop for the Unified Trading System
This demonstrates how to connect all components together in a basic trading loop.
"""

import time
import numpy as np
import sys
import os

# Add the unified_trading_system directory to the Python path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

from unified_trading_system.perception.belief_state import BeliefStateEstimator
from unified_trading_system.decision.aggression_controller import AggressionController
from unified_trading_system.execution.smart_order_router import ExecutionModel, ExecutionIntent
from unified_trading_system.risk.unified_risk_manager import RiskManifold
from unified_trading_system.feedback.monitoring_engine import FeedbackLayer
from unified_trading_system.adaptation.drift_detector import AdaptationLayer
from unified_trading_system.perception.event_system import EventBus, EventFactory, EventType
from unified_trading_system.config.config_manager import ConfigManager

def run_example_trading_loop(duration_seconds=30):
    """
    Run a basic example trading loop showing how all components work together.
    
    This is a simplified example that demonstrates the core flow:
    Market Data -> Perception -> Decision -> Risk -> Execution -> Feedback -> Adaptation
    """
    
    print("Starting Unified Trading System Example Loop")
    print("=" * 50)
    
    # Ensure default configuration exists
    ConfigManager.create_default_config()
    
    # Initialize all components
    event_bus = EventBus()
    belief_estimator = BeliefStateEstimator()
    aggression_controller = AggressionController()
    execution_model = ExecutionModel()
    risk_manager = RiskManifold()
    feedback_layer = FeedbackLayer()
    adaptation_layer = AdaptationLayer()
    config_manager = ConfigManager()
    
    # Track events for demonstration
    received_events = []
    
    # Subscribe to key events for monitoring
    def event_handler(event):
        received_events.append(event)
        if len(received_events) <= 5:  # Only show first few events to avoid spam
            print(f"� Ereignisse: {event.event_type.value} from {event.metadata.source_component}")
    
    for event_type in [EventType.BELIEF_STATE_UPDATE, EventType.AGGRESSION_UPDATE, 
                      EventType.RISK_ASSESSMENT, EventType.TRADE_EXECUTED]:
        event_bus.subscribe(event_type, event_handler)
    
    # Initialize belief state estimator with some reference data
    print("\n🔧 Initializing system components...")
    
    # Simulation parameters
    start_time = time.time()
    update_interval = 1.0  # seconds
    last_update = start_time
    
    print("▶️  Starting trading loop (press Ctrl+C to stop early)")
    print("-" * 50)
    
    try:
        iteration = 0
        while time.time() - start_time < duration_seconds:
            iteration += 1
            current_time = time.time()
            
            # Simulate market data arrival (in practice, this would come from a feed)
            # Generate some realistic-looking market data
            base_price = 50000.0
            price_noise = np.random.normal(0, 100.0)  # $100 std dev noise
            mid_price = base_price + price_noise
            spread = abs(np.random.normal(2.0, 0.5))  # ~2 bps spread
            
            market_data = {
                "bid_price": mid_price - spread/2,
                "ask_price": mid_price + spread/2,
                "bid_size": np.random.uniform(1.0, 5.0),
                "ask_size": np.random.uniform(1.0, 5.0),
                "last_price": mid_price,
                "last_size": np.random.uniform(0.5, 2.0),
                "volume": np.random.uniform(50.0, 200.0),
                "mid_price": mid_price,
                "spread_bps": spread,
                "volatility_estimate": 0.15 + np.random.normal(0, 0.05),
                "liquidity_estimate": np.clip(0.5 + np.random.normal(0, 0.2), 0.1, 0.9)
            }
            
            # 1. PERCEPTION LAYER: Process market data to update belief state
            belief_state = belief_estimator.update(market_data)
            
            # Publish belief state update
            belief_event = EventFactory.create_belief_state_update(
                expected_return=belief_state.expected_return,
                expected_return_uncertainty=belief_state.expected_return_uncertainty,
                aleatoric_uncertainty=belief_state.aleatoric_uncertainty,
                epistemic_uncertainty=belief_state.epistemic_uncertainty,
                regime_probabilities=belief_state.regime_probabilities
            )
            event_bus.publish(belief_event)
            
            # 2. DECISION LAYER: Update aggression level based on belief state
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
                signal_strength=0.2 + 0.3 * np.random.random(),  # Simulated alpha signal
                execution_feedback=0.0  # Would come from previous execution results
            )
            
            # Publish aggression update
            aggression_event = EventFactory.create_aggression_update(
                aggression_level=aggression_state.aggression_level,
                signal_strength=0.2 + 0.3 * np.random.random(),
                risk_gradient=aggression_state.risk_gradient,
                aggression_rate=aggression_state.aggression_rate,
                execution_feedback=0.0
            )
            event_bus.publish(aggression_event)
            
            # 3. RISK MANAGEMENT: Assess current risk levels
            portfolio_state = {
                "drawdown": max(0.0, -np.random.exponential(0.02)),  # Simulate some drawdown
                "daily_pnl": np.random.normal(0.0005, 0.01),  # Small daily P&L
                "leverage_ratio": np.clip(0.3 + np.random.normal(0, 0.2), 0.0, 1.0),
                "total_value": 100000.0 + np.random.normal(0, 5000)  # Fluctuating portfolio value
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
            
            # Publish risk assessment
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
            
            # 4. EXECUTION LAYER: Create and simulate execution plan if conditions are right
            execution_result = None
            trade_executed = False
            
            # Only trade if aggression is sufficient and risk allows it
            if (aggression_state.aggression_level > 0.15 and 
                risk_assessment.protective_action in ["NONE", "REDUCE_SIZE"]):
                
                # Create execution intent from decision layer
                execution_intent = ExecutionIntent(
                    symbol="BTCUSDT",
                    side="BUY" if belief_state.expected_return > 0 else "SELL",
                    quantity=min(0.01 * belief_state.liquidity_estimate * 1000, 5.0),  # Size based on liquidity
                    urgency=min(aggression_state.aggression_level + 0.1, 1.0),
                    max_slippage=10.0,
                    min_time_limit=1.0,
                    max_time_limit=10.0,
                    aggression_level=aggression_state.aggression_level,
                    timestamp=int(time.time() * 1e9)
                )
                
                # Plan execution
                plan = execution_model.plan_execution(execution_intent, {
                    "symbol": "BTCUSDT",
                    "mid_price": market_data["mid_price"],
                    "spread_bps": market_data["spread_bps"],
                    "volatility_estimate": belief_state.volatility_estimate,
                    "liquidity_estimate": belief_state.liquidity_estimate
                })
                
                # Simulate execution
                execution_result = execution_model.simulate_execution(plan, {
                    "symbol": "BTCUSDT",
                    "mid_price": market_data["mid_price"],
                    "spread_bps": market_data["spread_bps"],
                    "volatility_estimate": belief_state.volatility_estimate,
                    "liquidity_estimate": belief_state.liquidity_estimate
                })
                
                # Publish trade executed if filled
                if execution_result.filled_quantity > 0:
                    trade_executed = True
                    trade_event = EventFactory.create_trade_executed(
                        symbol="BTCUSDT",
                        side=execution_intent.side,
                        quantity=execution_result.filled_quantity,
                        price=execution_result.average_price,
                        timestamp=execution_result.timestamp,
                        commission=1.0,
                        slippage=execution_result.slippage,
                        latency=execution_result.latency
                    )
                    event_bus.publish(trade_event)
                    
                    # 5. FEEDBACK LAYER: Process trade results
                    trade_result = {
                        "timestamp": execution_result.timestamp,
                        "symbol": "BTCUSDT",
                        "side": execution_intent.side,
                        "filled_quantity": execution_result.filled_quantity,
                        "average_price": execution_result.average_price,
                        "commission": 1.0
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
                    
                    feedback_metrics = feedback_layer.update_all(
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
            
            # 6. ADAPTATION LAYER: Periodically check for need to adapt
            if iteration % 10 == 0:  # Check every 10 iterations
                # Prepare some sample data for adaptation checking
                belief_states = [{
                    "expected_return": belief_state.expected_return + np.random.normal(0, 0.001),
                    "expected_return_uncertainty": belief_state.expected_return_uncertainty,
                    "aleatoric_uncertainty": belief_state.aleatoric_uncertainty,
                    "epistemic_uncertainty": belief_state.epistemic_uncertainty,
                    "regime_probabilities": belief_state.regime_probabilities,
                    "volatility_estimate": belief_state.volatility_estimate + np.random.normal(0, 0.02),
                    "liquidity_estimate": belief_state.liquidity_estimate + np.random.normal(0, 0.05),
                    "momentum_signal": belief_state.momentum_signal,
                    "volume_signal": belief_state.volume_signal,
                    "confidence": belief_state.confidence
                } for _ in range(5)]
                
                prediction_errors = [np.random.normal(0, 0.005) for _ in range(20)]
                feature_data = {
                    "ofI": [np.random.normal(0, 0.1) for _ in range(20)],
                    "volatility": [abs(np.random.normal(0.1, 0.03)) for _ in range(20)]
                }
                performance_metrics = [np.random.normal(0.001, 0.005) for _ in range(20)]
                
                adaptation_occurred, adaptation_events, _ = adaptation_layer.update_and_check_adaptation(
                    belief_state=belief_states[-1] if belief_states else {},
                    prediction_errors=prediction_errors,
                    feature_data=feature_data,
                    performance_metrics=performance_metrics,
                    current_model=None  # In practice, you'd pass your actual model here
                )
                
                if adaptation_occurred:
                    print(f"🔄 Adaptation triggered! {len(adaptation_events)} events")
                    for event in adaptation_events[:2]:  # Show first 2 events
                        print(f"   - {event.adaptation_type.value}: {event.trigger_reason}")
            
            # Print periodic status update
            if iteration % 20 == 0:
                elapsed = time.time() - start_time
                print(f"⏱️  Iteration {iteration} | "
                      f"Elapsed: {elapsed:.1f}s | "
                      f"Price: ${mid_price:.2f} | "
                      f"Aggression: {aggression_state.aggression_level:.3f} | "
                      f"Risk: {risk_assessment.risk_level.name} | "
                      f"Events: {len(received_events)}")
            
            # Wait for next update interval
            time.sleep(max(0, update_interval - (time.time() - current_time)))
            
    except KeyboardInterrupt:
        print("\n⏹️  Trading loop stopped by user")
    except Exception as e:
        print(f"\n❌ Error in trading loop: {e}")
        import traceback
        traceback.print_exc()
    
    # Final statistics
    elapsed_total = time.time() - start_time
    print("\n" + "=" * 50)
    print("📊 TRADING LOOP SUMMARY")
    print("=" * 50)
    print(f"Duration: {elapsed_total:.1f} seconds")
    print(f"Iterations: {iteration}")
    print(f"Events Received: {len(received_events)}")
    if iteration > 0:
        print(f"Average Frequency: {iteration/elapsed_total:.1f} Hz")
    print(f"Belief State Updates: {len([e for e in received_events if e.event_type == EventType.BELIEF_STATE_UPDATE])}")
    print(f"Aggression Updates: {len([e for e in received_events if e.event_type == EventType.AGGRESSION_UPDATE])}")
    print(f"Risk Assessments: {len([e for e in received_events if e.event_type == EventType.RISK_ASSESSMENT])}")
    print(f"Trades Executed: {sum(1 for e in received_events if e.event_type == EventType.TRADE_EXECUTED)}")
    print("=" * 50)
    print("✅ Example trading loop completed successfully!")

if __name__ == "__main__":
    # Run the example trading loop for 30 seconds
    # You can adjust the duration as needed
    run_example_trading_loop(duration_seconds=30)