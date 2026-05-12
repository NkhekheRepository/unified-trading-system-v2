#!/usr/bin/env python3
"""
Integrated Demo: Belief State to Signal Generation Pipeline
Shows the complete process from market data to trading signals.
"""

import time
import json
import numpy as np
from typing import Dict, List

from perception.belief_state import BeliefStateEstimator, RegimeType
from decision.signal_generator import SignalGenerator, TradingSignal
from execution.smart_order_router import ExecutionModel, ExecutionIntent
from execution.testnet_executor import TestnetExecutionWithGovernance
from risk.unified_risk_manager import RiskManifold


def generate_market_scenarios() -> List[Dict]:
    """Generate realistic market data scenarios for testing"""
    scenarios = []
    
    # Scenario 1: Strong buy pressure
    scenarios.append({
        "name": "Strong Buy Pressure",
        "data": {
            "bid_price": 50000.0,
            "ask_price": 50000.5,
            "bid_size": 25.0,
            "ask_size": 5.0,
            "last_price": 50000.3,
            "last_size": 20.0
        }
    })
    
    # Scenario 2: Strong sell pressure  
    scenarios.append({
        "name": "Strong Sell Pressure",
        "data": {
            "bid_price": 50000.0,
            "ask_price": 50000.5,
            "bid_size": 5.0,
            "ask_size": 25.0,
            "last_price": 49999.7,
            "last_size": 20.0
        }
    })
    
    # Scenario 3: Neutral with slight buy bias
    scenarios.append({
        "name": "Neutral with Buy Bias",
        "data": {
            "bid_price": 50000.0,
            "ask_price": 50000.5,
            "bid_size": 15.0,
            "ask_size": 10.0,
            "last_price": 50000.2,
            "last_size": 8.0
        }
    })
    
    # Scenario 4: High volatility (wide spread)
    scenarios.append({
        "name": "High Volatility",
        "data": {
            "bid_price": 50000.0,
            "ask_price": 50002.0,
            "bid_size": 10.0,
            "ask_size": 10.0,
            "last_price": 50001.0,
            "last_size": 5.0
        }
    })
    
    return scenarios


def print_belief_state_details(belief_state):
    """Print detailed belief state information"""
    print(f"  Confidence: {belief_state.confidence:.4f}")
    print(f"  Expected Return: {belief_state.expected_return:.4f}")
    print(f"  Return Uncertainty: {belief_state.expected_return_uncertainty:.4f}")
    print(f"  Volatility Estimate: {belief_state.volatility_estimate:.4f}")
    print(f"  Liquidity Estimate: {belief_state.liquidity_estimate:.4f}")
    
    # Regime probabilities
    print(f"  Regime Probabilities:")
    regime_probs = list(zip(range(8), belief_state.regime_probabilities))
    regime_probs.sort(key=lambda x: x[1], reverse=True)
    for i, prob in regime_probs[:3]:
        regime = list(RegimeType)[i]
        print(f"    {regime.name}: {prob:.4f}")
    
    # Key microstructure features
    print(f"  Key Microstructure Features:")
    for feature in ["ofI", "I_star", "L_star", "S_star"]:
        if feature in belief_state.microstructure_features:
            print(f"    {feature}: {belief_state.microstructure_features[feature]:.4f}")


def print_signal_details(signal: TradingSignal):
    """Print trading signal details"""
    print(f"    Symbol: {signal.symbol}")
    print(f"    Action: {signal.action}")
    print(f"    Quantity: {signal.quantity:.6f}")
    print(f"    Confidence: {signal.confidence:.4f}")
    print(f"    Expected Return: {signal.expected_return:.4f}")
    print(f"    Signal Strength: {signal.signal_strength:.4f}")
    print(f"    Regime: {signal.regime.name}")


async def demonstrate_complete_pipeline():
    """Demonstrate the complete trading pipeline"""
    print("=" * 70)
    print("INTEGRATED TRADING SYSTEM DEMO")
    print("Pipeline: Market Data -> Belief State -> Signal -> Execution")
    print("=" * 70)
    
    # Initialize components
    estimator = BeliefStateEstimator()
    generator = SignalGenerator({
        'min_confidence_threshold': 0.3,
        'min_expected_return': 0.0005,
        'max_position_size': 0.1,
        'volatility_scaling': True,
        'regime_filters': True
    })
    
    risk_manager = RiskManifold()
    execution_model = ExecutionModel()
    executor = TestnetExecutionWithGovernance()
    
    # Generate market scenarios
    scenarios = generate_market_scenarios()
    
    for scenario in scenarios:
        print(f"\n{'=' * 70}")
        print(f"SCENARIO: {scenario['name']}")
        print(f"{'=' * 70}")
        
        # Step 1: Process market data into belief state
        market_data = scenario['data']
        belief_state = estimator.update(market_data)
        
        print(f"\n1. BELIEF STATE ESTIMATION:")
        print_belief_state_details(belief_state)
        
        # Step 2: Generate trading signals
        symbol = "BTC/USDT"
        signals = generator.generate_signals(belief_state, symbol)
        
        print(f"\n2. SIGNAL GENERATION:")
        print(f"   Signals generated: {len(signals)}")
        
        if not signals:
            print(f"   Reason: {'Confidence too low' if not belief_state.is_confident(generator.min_confidence_threshold) else 'Expected return below threshold'}")
            continue
        
        for i, signal in enumerate(signals):
            print(f"\n   Signal {i+1}:")
            print_signal_details(signal)
            
            # Step 3: Risk assessment
            print(f"\n3. RISK ASSESSMENT:")
            risk_assessment = risk_manager.assess_risk({
                'symbol': signal.symbol,
                'action': signal.action,
                'quantity': signal.quantity,
                'confidence': signal.confidence
            })
            
            print(f"   Risk Level: {risk_assessment.risk_level.name}")
            print(f"   Risk Score: {risk_assessment.risk_score:.4f}")
            if risk_assessment.protective_action:
                print(f"   Protective Action: {risk_assessment.protective_action}")
            
            # Step 4: Execution planning (if risk allows)
            if risk_assessment.risk_level.value < 2:  # Less than WARNING
                print(f"\n4. EXECUTION PLANNING:")
                
                # Create execution intent
                intent = ExecutionIntent(
                    symbol=signal.symbol,
                    side=signal.action,
                    quantity=signal.quantity,
                    urgency=signal.confidence,
                    max_slippage=0.001,
                    min_time_limit=10,
                    max_time_limit=60,
                    aggression_level=0.5,
                    timestamp=int(time.time() * 1000)
                )
                
                # Generate execution plan
                plan = execution_model.plan_execution(intent)
                
                print(f"   Order Type: {plan.order_type.name}")
                print(f"   Target Price: {plan.price:.2f}")
                print(f"   Time Limit: {plan.time_limit}s")
                print(f"   Splits: {plan.splits_count}")
                
                # Step 5: Simulate execution
                print(f"\n5. EXECUTION SIMULATION:")
                
                # Get simulated market data
                sim_market_data = {
                    "mid_price": 50000.0,
                    "bid_price": 49999.5,
                    "ask_price": 50000.5,
                    "volume": 1000000,
                    "liquidity_estimate": 0.5
                }
                
                result = execution_model.simulate_execution(plan, sim_market_data)
                
                print(f"   Status: {result.status.name}")
                print(f"   Filled Quantity: {result.filled_quantity:.6f}")
                print(f"   Average Price: {result.average_price:.2f}")
                print(f"   Slippage: {result.slippage:.4f}%")
                print(f"   Market Impact: {result.market_impact:.2f}")
                
                # Step 6: Testnet execution demonstration
                print(f"\n6. TESTNET EXECUTION DEMO:")
                try:
                    testnet_result = await executor.execute_intent(intent)
                    print(f"   Testnet Result: {testnet_result.status.name}")
                    print(f"   Avg Price: {testnet_result.average_price:.2f}")
                    print(f"   Filled Qty: {testnet_result.filled_quantity:.6f}")
                except Exception as e:
                    print(f"   Testnet Error: {e}")
            else:
                print(f"\n4. EXECUTION BLOCKED by risk manager")
        
        print(f"\n{'=' * 70}")
    
    print(f"\n{'=' * 70}")
    print("DEMO COMPLETED")
    print("=" * 70)
    
    # Show final testnet state
    print(f"\nFINAL TESTNET STATE:")
    balance = await executor.get_balance()
    positions = await executor.get_positions()
    
    print(f"  Balance: {balance}")
    print(f"  Positions: {positions}")


def run_continuous_demo_mode():
    """Run a continuous demonstration with simulated market updates"""
    print("=" * 70)
    print("CONTINUOUS DEMO MODE")
    print("Simulating real-time market updates")
    print("Press Ctrl+C to stop")
    print("=" * 70)
    
    estimator = BeliefStateEstimator()
    generator = SignalGenerator({
        'min_confidence_threshold': 0.3,
        'min_expected_return': 0.0005,
        'max_position_size': 0.1
    })
    
    # Base market data
    base_price = 50000.0
    
    cycle = 0
    try:
        while True:
            cycle += 1
            
            # Simulate market fluctuations
            import random
            
            price_change = random.gauss(0, 0.001) * base_price
            bid_size = random.uniform(5, 20)
            ask_size = random.uniform(5, 20)
            
            # Occasionally create strong imbalances
            if random.random() < 0.2:
                if random.random() < 0.5:
                    bid_size *= 3  # Strong bid
                else:
                    ask_size *= 3  # Strong ask
            
            market_data = {
                "bid_price": base_price + price_change * 0.9995,
                "ask_price": base_price + price_change * 1.0005,
                "bid_size": bid_size,
                "ask_size": ask_size,
                "last_price": base_price + price_change,
                "last_size": random.uniform(5, 15)
            }
            
            # Process through pipeline
            belief_state = estimator.update(market_data)
            signals = generator.generate_signals(belief_state, "BTC/USDT")
            
            print(f"\nCycle {cycle}:")
            print(f"  Price: ${base_price + price_change:.2f}")
            print(f"  Bid/Ask Size: {bid_size:.1f}/{ask_size:.1f}")
            print(f"  Expected Return: {belief_state.expected_return:.4f}")
            print(f"  Confidence: {belief_state.confidence:.4f}")
            print(f"  Signals: {len(signals)}")
            
            if signals:
                for signal in signals:
                    print(f"    → {signal.action} {signal.quantity:.6f} BTC")
            
            time.sleep(2)  # Wait 2 seconds between cycles
            
    except KeyboardInterrupt:
        print("\n\nDemo stopped.")


if __name__ == "__main__":
    import asyncio
    
    print("Choose demo mode:")
    print("1. Complete pipeline demonstration")
    print("2. Continuous real-time simulation")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(demonstrate_complete_pipeline())
    elif choice == "2":
        run_continuous_demo_mode()
    else:
        print(f"Invalid choice: {choice}")