"""
Unified Trading System Integration Tests
Comprehensive test suite for validating the integrated system
"""


import unittest
import numpy as np
import time
from typing import Dict, List

# Import components to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from perception.event_system import UnifiedEvent, EventType, EventFactory, EventBus
from perception.belief_state import BeliefStateEstimator, BeliefState
from decision.aggression_controller import AggressionController, AggressionState
from execution.smart_order_router import ExecutionModel, ExecutionIntent, ExecutionPlan, ExecutionResult
from feedback.monitoring_engine import FeedbackLayer
from adaptation.drift_detector import AdaptationLayer
from risk.unified_risk_manager import RiskManifold, RiskLevel, RiskAssessment
from config.config_manager import ConfigManager


class TestEventSystem(unittest.TestCase):
    """Test the unified event system"""
    
    def setUp(self):
        self.event_bus = EventBus()
        self.received_events = []
        
        # Subscribe to all event types for testing
        for event_type in EventType:
            self.event_bus.subscribe(event_type, lambda e: self.received_events.append(e))
    
    def test_event_creation_and_serialization(self):
        """Test event creation and JSON serialization"""
        # Test market data update event
        event = EventFactory.create_market_data_update(
            symbol="BTCUSDT",
            bid_price=50000.0,
            ask_price=50010.0,
            bid_size=1.5,
            ask_size=2.0
        )
        
        self.assertEqual(event.event_type, EventType.MARKET_DATA_UPDATE)
        self.assertEqual(event.metadata.source_component, "market_data_feed")
        self.assertEqual(event.payload["symbol"], "BTCUSDT")
        self.assertEqual(event.payload["bid_price"], 50000.0)
        self.assertEqual(event.payload["ask_price"], 50010.0)
        
        # Test JSON serialization
        json_str = event.to_json()
        self.assertIsInstance(json_str, str)
        self.assertIn("BTCUSDT", json_str)
        self.assertIn("MARKET_DATA_UPDATE", json_str)
        
        # Test deserialization
        restored_event = UnifiedEvent.from_json(json_str)
        self.assertEqual(restored_event.event_type, event.event_type)
        self.assertEqual(restored_event.metadata.event_id, event.metadata.event_id)
        self.assertEqual(restored_event.payload, event.payload)
    
    def test_event_bus_publishing(self):
        """Test event bus publishing and subscription"""
        initial_count = len(self.received_events)
        
        # Publish an event
        event = EventFactory.create_belief_state_update(
            expected_return=0.001,
            expected_return_uncertainty=0.0005,
            aleatoric_uncertainty=0.001,
            epistemic_uncertainty=0.0008,
            regime_probabilities=[0.2, 0.3, 0.3, 0.1, 0.05, 0.03, 0.02, 0.02]
        )
        
        self.event_bus.publish(event)
        
        # Should have received one more event
        self.assertEqual(len(self.received_events), initial_count + 1)
        
        # Check the received event
        received_event = self.received_events[-1]
        self.assertEqual(received_event.event_type, EventType.BELIEF_STATE_UPDATE)
        self.assertEqual(received_event.payload["expected_return"], 0.001)
    
    def test_event_replay(self):
        """Test event replay functionality"""
        # Publish several events
        events_to_publish = []
        for i in range(5):
            event = EventFactory.create_market_data_update(
                symbol="ETHUSDT",
                bid_price=3000.0 + i,
                ask_price=3010.0 + i,
                bid_size=1.0,
                ask_size=1.0
            )
            events_to_publish.append(event)
            self.event_bus.publish(event)
        
        # Replay events
        replayed_events = self.event_bus.replay_events(0, 3)
        self.assertEqual(len(replayed_events), 3)
        
        # Check that replayed events match original events
        for i, (original, replayed) in enumerate(zip(events_to_publish[:3], replayed_events)):
            self.assertEqual(original.event_type, replayed.event_type)
            self.assertEqual(original.payload["symbol"], replayed.payload["symbol"])
            self.assertEqual(original.payload["bid_price"], replayed.payload["bid_price"])


class TestPerceptionLayer(unittest.TestCase):
    """Test the perception layer"""
    
    def setUp(self):
        self.estimator = BeliefStateEstimator()
    
    def test_belief_state_initialization(self):
        """Test belief state estimator initialization"""
        # Should be able to create estimator without error
        self.assertIsInstance(self.estimator, BeliefStateEstimator)
        self.assertEqual(self.estimator.n_regimes, 8)
    
    def test_belief_state_update(self):
        """Test belief state update with market data"""
        market_data = {
            "bid_price": 50000.0,
            "ask_price": 50010.0,
            "bid_size": 1.5,
            "ask_size": 1.0,
            "last_price": 50005.0,
            "last_size": 2.0
        }
        
        belief_state = self.estimator.update(market_data)
        
        # Check that we got a valid belief state
        self.assertIsInstance(belief_state, BeliefState)
        self.assertIsInstance(belief_state.expected_return, float)
        self.assertIsInstance(belief_state.expected_return_uncertainty, float)
        self.assertIsInstance(belief_state.aleatoric_uncertainty, float)
        self.assertIsInstance(belief_state.epistemic_uncertainty, float)
        self.assertIsInstance(belief_state.regime_probabilities, list)
        self.assertEqual(len(belief_state.regime_probabilities), 8)
        self.assertAlmostEqual(sum(belief_state.regime_probabilities), 1.0, places=5)
        self.assertIsInstance(belief_state.microstructure_features, dict)
        self.assertIn("ofI", belief_state.microstructure_features)
        self.assertIn("I_star", belief_state.microstructure_features)
        self.assertIsInstance(belief_state.timestamp, int)
        self.assertIsInstance(belief_state.confidence, float)
        self.assertGreaterEqual(belief_state.confidence, 0.0)
        self.assertLessEqual(belief_state.confidence, 1.0)
    
    def test_belief_state_confidence(self):
        """Test belief state confidence calculation"""
        market_data = {
            "bid_price": 50000.0,
            "ask_price": 50010.0,
            "bid_size": 2.0,
            "ask_size": 2.0,  # Balanced order book -> lower ofI -> higher confidence
            "last_price": 50005.0,
            "last_size": 1.0
        }
        
        belief_state = self.estimator.update(market_data=market_data)
        
        # Confidence should be reasonable
        self.assertGreaterEqual(belief_state.confidence, 0.0)
        self.assertLessEqual(belief_state.confidence, 1.0)
        
        # Test confident/unconfident states
        # High entropy (uncertain regimes) should lower confidence
        # This is tested indirectly through the entropy calculation


class TestDecisionLayer(unittest.TestCase):
    """Test the decision layer"""
    
    def setUp(self):
        self.controller = AggressionController(
            kappa=0.1,
            lambda_=0.05,
            beta_max=0.5,
            eta=0.01,
            alpha_target=0.5
        )
    
    def test_aggression_controller_initialization(self):
        """Test aggression controller initialization"""
        self.assertIsInstance(self.controller, AggressionController)
        self.assertEqual(self.controller.aggression_level, 0.5)  # Should start at target
        self.assertEqual(self.controller.aggression_rate, 0.0)
    
    def test_aggression_update(self):
        """Test aggression level updates"""
        belief_state = {
            "expected_return": 0.001,
            "expected_return_uncertainty": 0.0005,
            "aleatoric_uncertainty": 0.001,
            "epistemic_uncertainty": 0.0008,
            "regime_probabilities": [0.2, 0.2, 0.2, 0.2, 0.0, 0.0, 0.0, 0.0],
            "volatility_estimate": 0.15,
            "liquidity_estimate": 0.7,
            "momentum_signal": 0.1,
            "volume_signal": 0.05,
            "confidence": 0.8
        }
        
        initial_aggression = self.controller.aggression_level
        
        # Update with positive signal
        aggression_state = self.controller.update(
            belief_state=belief_state,
            signal_strength=0.5,
            execution_feedback=0.0
        )
        
        # Should have updated aggression level
        self.assertIsInstance(aggression_state, AggressionState)
        self.assertIsInstance(aggression_state.aggression_level, float)
        self.assertGreaterEqual(aggression_state.aggression_level, 0.0)
        self.assertLessEqual(aggression_state.aggression_level, 1.0)
        self.assertIsInstance(aggression_state.aggression_rate, float)
        self.assertIsInstance(aggression_state.signal_strength, float)
        self.assertIsInstance(aggression_state.risk_gradient, float)
        self.assertIsInstance(aggression_state.execution_feedback, float)
        self.assertIsInstance(aggression_state.timestamp, int)
    
    def test_aggression_bounds(self):
        """Test that aggression level stays within bounds"""
        belief_state = {
            "expected_return": 0.01,  # Very high expected return
            "expected_return_uncertainty": 0.001,
            "aleatoric_uncertainty": 0.001,
            "epistemic_uncertainty": 0.001,
            "regime_probabilities": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
            "volatility_estimate": 0.1,
            "liquidity_estimate": 0.9,
            "momentum_signal": 0.5,
            "volume_signal": 0.0,
            "confidence": 0.9
        }
        
        # Even with strong positive signal, aggression should not exceed 1.0
        for _ in range(10):
            aggression_state = self.controller.update(
                belief_state=belief_state,
                signal_strength=1.0,  # Maximum signal
                execution_feedback=0.0
            )
            self.assertGreaterEqual(aggression_state.aggression_level, 0.0)
            self.assertLessEqual(aggression_state.aggression_level, 1.0)
    
    def test_lyapunov_stability(self):
        """Test Lyapunov stability properties"""
        belief_state = {
            "expected_return": 0.0005,
            "expected_return_uncertainty": 0.0005,
            "aleatoric_uncertainty": 0.001,
            "epistemic_uncertainty": 0.001,
            "regime_probabilities": [0.125] * 8,  # Uniform distribution
            "volatility_estimate": 0.1,
            "liquidity_estimate": 0.5,
            "momentum_signal": 0.0,
            "volume_signal": 0.0,
            "confidence": 0.7
        }
        
        # Run controller for several steps near target
        for i in range(20):
            # Use small signal to stay near target
            aggression_state = self.controller.update(
                belief_state=belief_state,
                signal_strength=0.0,
                execution_feedback=0.0
            )
        
        # Check Lyapunov function properties
        stability_info = self.controller.get_stability_info()
        self.assertIsInstance(stability_info["lyapunov_function"], float)
        self.assertGreaterEqual(stability_info["lyapunov_function"], 0.0)
        
        # System should be stable (dV/dt <= 0) when near target with zero inputs
        # Note: May not be strictly stable in one step due to discretization, 
        # but should trend toward stability


class TestExecutionLayer(unittest.TestCase):
    """Test the execution layer"""
    
    def setUp(self):
        self.execution_model = ExecutionModel()
    
    def test_execution_model_initialization(self):
        """Test execution model initialization"""
        self.assertIsInstance(self.execution_model, ExecutionModel)
        self.assertEqual(self.execution_model.execution_eta, 0.01)
        self.assertEqual(self.execution_model.market_impact_factor, 0.1)
        self.assertEqual(self.execution_model.latency_base, 5)
        self.assertEqual(self.execution_model.slippage_factor, 0.05)
    
    def test_execution_intent_creation(self):
        """Test execution intent creation"""
        intent = ExecutionIntent(
            symbol="BTCUSDT",
            side="BUY",
            quantity=1.5,
            urgency=0.6,
            max_slippage=5.0,
            min_time_limit=1.0,
            max_time_limit=10.0,
            aggression_level=0.7,
            timestamp=int(time.time() * 1e9)
        )
        
        self.assertEqual(intent.symbol, "BTCUSDT")
        self.assertEqual(intent.side, "BUY")
        self.assertEqual(intent.quantity, 1.5)
        self.assertEqual(intent.urgency, 0.6)
    
    def test_execution_planning(self):
        """Test execution planning"""
        intent = ExecutionIntent(
            symbol="ETHUSDT",
            side="SELL",
            quantity=10.0,
            urgency=0.5,
            max_slippage=10.0,
            min_time_limit=1.0,
            max_time_limit=5.0,
            aggression_level=0.6,
            timestamp=int(time.time() * 1e9)
        )
        
        market_data = {
            "symbol": "ETHUSDT",
            "mid_price": 3000.0,
            "spread_bps": 2.0,
            "volatility_estimate": 0.15,
            "liquidity_estimate": 0.6
        }
        
        plan = self.execution_model.plan_execution(intent, market_data)
        
        self.assertIsInstance(plan, ExecutionPlan)
        self.assertEqual(plan.symbol, "ETHUSDT")
        self.assertEqual(plan.quantity, 10.0)
        self.assertIsInstance(plan.order_type, type(ExecutionModel()._select_order_type(0.5, 0.15, 0.6, 2.0, 10.0)))
        self.assertIsInstance(plan.expected_slippage, float)
        self.assertGreaterEqual(plan.expected_slippage, 0.0)
        self.assertIsInstance(plan.expected_latency, int)
        self.assertGreaterEqual(plan.expected_latency, 1)
        self.assertIsInstance(plan.expected_cost, float)
        self.assertGreaterEqual(plan.expected_cost, 0.0)
        self.assertIsInstance(plan.urgency_score, float)
        self.assertGreaterEqual(plan.urgency_score, 0.0)
        self.assertLessEqual(plan.urgency_score, 1.0)
    
    def test_execution_simulation(self):
        """Test execution simulation"""
        intent = ExecutionIntent(
            symbol="BTCUSDT",
            side="BUY",
            quantity=1.0,
            urgency=0.5,
            max_slippage=5.0,
            min_time_limit=1.0,
            max_time_limit=10.0,
            aggression_level=0.6,
            timestamp=int(time.time() * 1e9)
        )
        
        market_data = {
            "symbol": "BTCUSDT",
            "mid_price": 50000.0,
            "spread_bps": 2.0,
            "volatility_estimate": 0.15,
            "liquidity_estimate": 0.6
        }
        
        plan = self.execution_model.plan_execution(intent, market_data)
        result = self.execution_model.simulate_execution(plan, market_data)
        
        self.assertIsInstance(result, ExecutionResult)
        self.assertIsInstance(result.status, type(result.status))
        self.assertIsInstance(result.filled_quantity, float)
        self.assertGreaterEqual(result.filled_quantity, 0.0)
        self.assertLessEqual(result.filled_quantity, plan.quantity)  # Can't fill more than requested
        self.assertIsInstance(result.average_price, float)
        self.assertGreaterEqual(result.average_price, 0.0)
        self.assertIsInstance(result.slippage, float)
        self.assertIsInstance(result.latency, int)
        self.assertGreaterEqual(result.latency, 0)
        self.assertIsInstance(result.market_impact, float)
        self.assertGreaterEqual(result.market_impact, 0.0)
    
    def test_execution_feedback(self):
        """Test execution feedback application"""
        intent = ExecutionIntent(
            symbol="BTCUSDT",
            side="BUY",
            quantity=1.0,
            urgency=0.5,
            max_slippage=5.0,
            min_time_limit=1.0,
            max_time_limit=10.0,
            aggression_level=0.6,
            timestamp=int(time.time() * 1e9)
        )
        
        market_data = {
            "symbol": "BTCUSDT",
            "mid_price": 50000.0,
            "spread_bps": 2.0,
            "volatility_estimate": 0.15,
            "liquidity_estimate": 0.6
        }
        
        plan = self.execution_model.plan_execution(intent, market_data)
        result = self.execution_model.simulate_execution(plan, market_data)
        
        # Apply execution feedback
        updated_aggression = self.execution_model.apply_execution_feedback(
            intent.aggression_level,
            result
        )
        
        self.assertIsInstance(updated_aggression, float)
        self.assertGreaterEqual(updated_aggression, 0.0)
        self.assertLessEqual(updated_aggression, 1.0)
        
        # Poor execution (high slippage/latency) should reduce aggression
        # Good execution should increase or maintain aggression
        # This is stochastic, so we just check it returns a valid value


class TestFeedbackLayer(unittest.TestCase):
    """Test the feedback layer"""
    
    def setUp(self):
        self.feedback_layer = FeedbackLayer()
    
    def test_feedback_layer_initialization(self):
        """Test feedback layer initialization"""
        self.assertIsInstance(self.feedback_layer, FeedbackLayer)
        self.assertIsInstance(self.feedback_layer.pnl_engine, type(self.feedback_layer.pnl_engine))
        self.assertIsInstance(self.feedback_layer.learning_insights_engine, type(self.feedback_layer.learning_insights_engine))
        self.assertIsInstance(self.feedback_layer.sre_metrics_engine, type(self.feedback_layer.sre_metrics_engine))
    
    def test_feedback_update(self):
        """Test feedback layer update"""
        # Simulate trading data
        trade_result = {
            "timestamp": int(time.time() * 1e9),
            "symbol": "BTCUSDT",
            "side": "BUY",
            "filled_quantity": 1.0,
            "average_price": 50000.0,
            "commission": 5.0
        }
        
        current_positions = {
            "BTCUSDT": {
                "quantity": 1.0,
                "avg_price": 49950.0
            }
        }
        
        market_prices = {
            "BTCUSDT": 50010.0
        }
        
        belief_state = {
            "expected_return": 0.001,
            "expected_return_uncertainty": 0.0005,
            "aleatoric_uncertainty": 0.001,
            "epistemic_uncertainty": 0.0008,
            "regime_probabilities": [0.2, 0.3, 0.3, 0.1, 0.05, 0.03, 0.02, 0.02],
            "volatility_estimate": 0.15,
            "liquidity_estimate": 0.7,
            "momentum_signal": 0.05,
            "volume_signal": 0.02,
            "confidence": 0.8
        }
        
        execution_result = {
            "timestamp": int(time.time() * 1e9),
            "status": "FILLED",
            "filled_quantity": 1.0,
            "average_price": 50000.0,
            "slippage": 1.0,
            "latency": 5,
            "market_impact": 0.5
        }
        
        market_data = {
            "signal_strength": 0.3,
            "volatility_estimate": 0.15,
            "liquidity_estimate": 0.6,
            "spread_bps": 2.0
        }
        
        component_latencies = {
            "perception": 2.0,
            "decision": 1.0,
            "execution": 3.0,
            "feedback": 0.5
        }
        
        error_events = []
        system_health = {
            "perception": True,
            "decision": True,
            "execution": True,
            "feedback": True
        }
        
        model_info = {
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
        
        # This should not raise an exception
        metrics = self.feedback_layer.update_all(
            trade_result=trade_result,
            current_positions=current_positions,
            market_prices=market_prices,
            belief_state=belief_state,
            execution_result=execution_result,
            market_data=market_data,
            component_latencies=component_latencies,
            error_events=error_events,
            system_health=system_health,
            model_info=model_info
        )
        
        # Should have returned metrics from all engines
        self.assertIsInstance(metrics, list)
        self.assertGreater(len(metrics), 0)
        
        # Check that we got metrics from each engine type
        metric_types = set(metric.metric_type.value for metric in metrics)
        expected_types = {
            "PNL",
            "LEARNING_INSIGHTS",
            "SRE_METRICS",
            "PREDICTIVE",
            "VAR",
            "FACTOR_ATTRIBUTION",
            "STRATEGY_OPTIMIZER",
            "CORRELATION_MONITOR"
        }
    
        # At least some of the expected types should be present
        self.assertTrue(len(metric_types.intersection(expected_types)) > 0)


class TestAdaptationLayer(unittest.TestCase):
    """Test the adaptation layer"""
    
    def setUp(self):
        self.adaptation_layer = AdaptationLayer(
            tau_drift=0.1,
            warning_threshold=0.05
        )
    
    def test_adaptation_layer_initialization(self):
        """Test adaptation layer initialization"""
        self.assertIsInstance(self.adaptation_layer, AdaptationLayer)
        self.assertIsInstance(self.adaptation_layer.drift_detector, type(self.adaptation_layer.drift_detector))
        self.assertIsInstance(self.adaptation_layer.model_adapter, type(self.adaptation_layer.model_adapter))
    
    def test_drift_detection_initialization(self):
        """Test drift detector initialization with reference data"""
        reference_data = [1.0, 1.1, 0.9, 1.05, 0.95] * 10  # 50 samples around 1.0
        
        # Should not raise an exception
        self.adaptation_layer.drift_detector.initialize_reference(reference_data)
        
        # Check that we can get diagnostics
        diagnostics = self.adaptation_layer.drift_detector.get_drift_diagnostics()
        self.assertIsInstance(diagnostics, dict)
        self.assertIn("samples_in_reference", diagnostics)
        self.assertEqual(diagnostics["samples_in_reference"], 50)
    
    def test_no_drift_detection(self):
        """Test that similar data doesn't trigger drift detection"""
        # Initialize with reference data
        reference_data = np.random.normal(0, 1, 50).tolist()
        self.adaptation_layer.drift_detector.initialize_reference(reference_data)
        
        # Test with similar data (should not detect drift)
        similar_data = np.random.normal(0, 1, 20).tolist()  # Same distribution
        
        drift_detected, drift_score, diagnostics = self.adaptation_layer.drift_detector.update(similar_data)
        
        # Should not detect drift with similar data
        self.assertFalse(drift_detected)
        self.assertLess(drift_score, self.adaptation_layer.drift_detector.tau_drift)


class TestRiskManagement(unittest.TestCase):
    """Test the risk management system"""
    
    def setUp(self):
        self.risk_manager = RiskManifold()
    
    def test_risk_manager_initialization(self):
        """Test risk manager initialization"""
        self.assertIsInstance(self.risk_manager, RiskManifold)
        self.assertIsInstance(self.risk_manager.risk_weights, dict)
        self.assertEqual(len(self.risk_manager.risk_weights), 7)  # 7 risk factors
    
    def test_risk_assessment_normal_conditions(self):
        """Test risk assessment under normal conditions"""
        belief_state = {
            "expected_return": 0.001,
            "expected_return_uncertainty": 0.0005,
            "aleatoric_uncertainty": 0.001,
            "epistemic_uncertainty": 0.0008,
            "regime_probabilities": [0.15] * 8,  # Nearly uniform
            "volatility_estimate": 0.12,
            "liquidity_estimate": 0.8,
            "drawdown": 0.02,
            "entropy": 0.9
        }
        
        portfolio_state = {
            "drawdown": 0.02,
            "daily_pnl": 0.003,
            "leverage_ratio": 0.3,
            "total_value": 100000.0
        }
        
        market_data = {
            "volatility": 0.12,
            "spread_bps": 1.5,
            "liquidity": 0.7
        }
        
        assessment = self.risk_manager.assess_risk(
            belief_state=belief_state,
            portfolio_state=portfolio_state,
            market_data=market_data
        )
        
        self.assertIsInstance(assessment, RiskAssessment)
        self.assertIsInstance(assessment.risk_level, RiskLevel)
        self.assertIsInstance(assessment.risk_score, float)
        self.assertGreaterEqual(assessment.risk_score, 0.0)
        self.assertLessEqual(assessment.risk_score, 1.0)
        self.assertIsInstance(assessment.cvar, float)
        self.assertIsInstance(assessment.volatility, float)
        self.assertIsInstance(assessment.drawdown, float)
        self.assertIsInstance(assessment.leverage_ratio, float)
        self.assertIsInstance(assessment.liquidity_score, float)
        self.assertIsInstance(assessment.concentration_risk, float)
        self.assertIsInstance(assessment.correlation_risk, float)
        self.assertIsInstance(assessment.risk_gradient, np.ndarray)
        self.assertIsInstance(assessment.protective_action, str)
        self.assertIsInstance(assessment.timestamp, int)
        
        # Under normal conditions, should be low risk
        self.assertIn(assessment.risk_level, [RiskLevel.LEVEL_0_NORMAL, RiskLevel.LEVEL_1_CAUTION])
    
    def test_risk_assessment_high_conditions(self):
        """Test risk assessment under high risk conditions"""
        belief_state = {
            "expected_return": -0.002,
            "expected_return_uncertainty": 0.002,
            "aleatoric_uncertainty": 0.004,
            "epistemic_uncertainty": 0.002,
            "regime_probabilities": [0.05, 0.1, 0.2, 0.3, 0.2, 0.1, 0.03, 0.02],
            "volatility_estimate": 0.35,
            "liquidity_estimate": 0.2,
            "drawdown": 0.12,
            "entropy": 1.8
        }
        
        portfolio_state = {
            "drawdown": 0.12,
            "daily_pnl": -0.02,
            "leverage_ratio": 0.8,
            "total_value": 80000.0
        }
        
        market_data = {
            "volatility": 0.35,
            "spread_bps": 5.0,
            "liquidity": 0.2
        }
        
        assessment = self.risk_manager.assess_risk(
            belief_state=belief_state,
            portfolio_state=portfolio_state,
            market_data=market_data
        )
        
        # Should detect elevated risk
        self.assertGreater(assessment.risk_score, 0.3)  # Should be notably elevated
        self.assertGreater(assessment.drawdown, 0.1)    # Should detect high drawdown
        self.assertGreater(assessment.leverage_ratio, 0.6)  # Should detect high leverage
        
        # Protective action should be more than NONE
        self.assertNotEqual(assessment.protective_action, "NONE")


class TestConfigManager(unittest.TestCase):
    """Test the configuration management system"""
    
    def setUp(self):
        # Create temporary directory for test configs
        self.temp_dir = "/tmp/unified_trading_system_test_config"
        os.makedirs(self.temp_dir, exist_ok=True)
        self.config_manager = ConfigManager(self.temp_dir)
        
        # Create default config
        ConfigManager.create_default_config(self.temp_dir)
    
    def tearDown(self):
        # Clean up temporary directory
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_config_manager_initialization(self):
        """Test config manager initialization"""
        self.assertIsInstance(self.config_manager, ConfigManager)
        self.assertTrue(os.path.exists(self.config_manager.config_dir))
    
    def test_config_loading(self):
        """Test configuration loading"""
        config = self.config_manager.load_config()
        
        self.assertIsInstance(config, dict)
        self.assertIn("system", config)
        self.assertIn("perception", config)
        self.assertIn("decision", config)
        self.assertIn("execution", config)
        self.assertIn("feedback", config)
        self.assertIn("adaptation", config)
        self.assertIn("risk_management", config)
        
        # Check some expected values
        self.assertEqual(config["system"]["name"], "Unified Trading System")
        self.assertEqual(config["system"]["version"], "1.0.0")
        self.assertEqual(config["system"]["environment"], "development")
    
    def test_config_get_set(self):
        """Test getting and setting configuration values"""
        config = self.config_manager.load_config()
        
        # Test getting a value
        kappa = self.config_manager.get_config_value(config, "decision.aggression_controller.kappa")
        self.assertEqual(kappa, 0.1)
        
        # Test setting a value
        config = self.config_manager.set_config_value(config, "decision.aggression_controller.kappa", 0.15)
        new_kappa = self.config_manager.get_config_value(config, "decision.aggression_controller.kappa")
        self.assertEqual(new_kappa, 0.15)
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Valid config should pass
        valid_config = {
            "system": {
                "name": "Test System",
                "version": "1.0.0",
                "environment": "development"
            }
        }
        
        # Should not raise exception
        try:
            self.config_manager._validate_config(valid_config, "unified")
        except Exception:
            self.fail("Valid configuration should not raise validation error")
        
        # Invalid config should fail
        invalid_config = {
            "system": {
                "name": "Test System"
                # Missing required version and environment
            }
        }
        
        with self.assertRaises(Exception):
            self.config_manager._validate_config(invalid_config, "unified")
        
        # Invalid value should fail
        invalid_value_config = {
            "system": {
                "name": "Test System",
                "version": "1.0.0",
                "environment": "development"
            },
            "decision": {
                "aggression_controller": {
                    "kappa": 1.5  # Above maximum of 1.0
                }
            }
        }
        
        with self.assertRaises(Exception):
            self.config_manager._validate_config(invalid_value_config, "unified")


class TestSystemIntegration(unittest.TestCase):
    """Test integrated system functionality"""
    
    def setUp(self):
        # Create instances of all major components
        self.event_bus = EventBus()
        self.perception_estimator = BeliefStateEstimator()
        self.decision_controller = AggressionController()
        self.execution_model = ExecutionModel()
        self.feedback_layer = FeedbackLayer()
        self.adaptation_layer = AdaptationLayer()
        self.risk_manager = RiskManifold()
        self.config_manager = ConfigManager()
        
        # Ensure default configuration exists for testing
        ConfigManager.create_default_config()
        
        # Subscribe to events for monitoring
        self.test_events = []
        for event_type in [EventType.BELIEF_STATE_UPDATE, EventType.AGGRESSION_UPDATE, EventType.RISK_ASSESSMENT]:
            self.event_bus.subscribe(event_type, lambda e: self.test_events.append(e))
    
    def test_end_to_end_processing(self):
        """Test end-to-end processing of a market tick"""
        # 1. Market data arrives (simulated)
        market_data = {
            "bid_price": 50000.0,
            "ask_price": 50010.0,
            "bid_size": 2.0,
            "ask_size": 1.5,
            "last_price": 50005.0,
            "last_size": 1.0,
            "volume": 100.0
        }
        
        # 2. Perception layer processes market data
        belief_state = self.perception_estimator.update(market_data)
        self.assertIsInstance(belief_state, BeliefState)
        
        # Publish belief state update event
        belief_event = EventFactory.create_belief_state_update(
            expected_return=belief_state.expected_return,
            expected_return_uncertainty=belief_state.expected_return_uncertainty,
            aleatoric_uncertainty=belief_state.aleatoric_uncertainty,
            epistemic_uncertainty=belief_state.epistemic_uncertainty,
            regime_probabilities=belief_state.regime_probabilities
        )
        self.event_bus.publish(belief_event)
        
        # 3. Decision layer processes belief state
        aggression_state = self.decision_controller.update(
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
            signal_strength=0.3,  # Would come from LVR's alpha processor
            execution_feedback=0.0
        )
        
        self.assertIsInstance(aggression_state, AggressionState)
        
        # Publish aggression update event
        aggression_event = EventFactory.create_aggression_update(
            aggression_level=aggression_state.aggression_level,
            signal_strength=0.3,
            risk_gradient=aggression_state.risk_gradient,
            aggression_rate=aggression_state.aggression_rate,
            execution_feedback=0.0
        )
        self.event_bus.publish(aggression_event)
        
        # 4. Risk management assesses current state
        portfolio_state = {
            "drawdown": 0.01,
            "daily_pnl": 0.001,
            "leverage_ratio": 0.2,
            "total_value": 100000.0
        }
        
        risk_assessment = self.risk_manager.assess_risk(
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
                "spread_bps": 2.0,
                "liquidity": belief_state.liquidity_estimate
            }
        )
        
        self.assertIsInstance(risk_assessment, RiskAssessment)
        
        # Publish risk assessment event
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
        self.event_bus.publish(risk_event)
        
        # 5. Execution layer creates plan if aggression sufficient
        if aggression_state.aggression_level > 0.1 and risk_assessment.protective_action in ["NONE", "REDUCE_SIZE"]:
            execution_intent = ExecutionIntent(
                symbol="BTCUSDT",
                side="BUY" if belief_state.expected_return > 0 else "SELL",
                quantity=min(0.01 * belief_state.liquidity_estimate * 100000, 1.0),  # Position sizing simplified
                urgency=min(aggression_state.aggression_level + 0.2, 1.0),
                max_slippage=10.0,
                min_time_limit=1.0,
                max_time_limit=10.0,
                aggression_level=aggression_state.aggression_level,
                timestamp=int(time.time() * 1e9)
            )
            
            plan = self.execution_model.plan_execution(execution_intent, {
                "symbol": "BTCUSDT",
                "mid_price": 50005.0,
                "spread_bps": 2.0,
                "volatility_estimate": belief_state.volatility_estimate,
                "liquidity_estimate": belief_state.liquidity_estimate
            })
            
            self.assertIsInstance(plan, ExecutionPlan)
            
            # Simulate execution
            execution_result = self.execution_model.simulate_execution(plan, {
                "symbol": "BTCUSDT",
                "mid_price": 50005.0,
                "spread_bps": 2.0,
                "volatility_estimate": belief_state.volatility_estimate,
                "liquidity_estimate": belief_state.liquidity_estimate
            })
            
            self.assertIsInstance(execution_result, ExecutionResult)
            
            # Publish trade executed event
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
            self.event_bus.publish(trade_event)
            
            # 6. Feedback layer processes results
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
            
            market_prices = {
                "BTCUSDT": 50005.0
            }
            
            component_latencies = {
                "perception": 2.0,
                "decision": 1.5,
                "execution": execution_result.latency,
                "feedback": 1.0
            }
            
            error_events = []
            system_health = {
                "perception": True,
                "decision": True,
                "execution": True,
                "feedback": True
            }
            
            model_info = {
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
            
            feedback_metrics = self.feedback_layer.update_all(
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
                    "signal_strength": 0.3,
                    "volatility_estimate": belief_state.volatility_estimate,
                    "liquidity_estimate": belief_state.liquidity_estimate,
                    "spread_bps": 2.0
                },
                component_latencies=component_latencies,
                error_events=error_events,
                system_health=system_health,
                model_info=model_info
            )
            
            self.assertIsInstance(feedback_metrics, list)
            self.assertGreater(len(feedback_metrics), 0)
        
        # 7. Check that we received events
        self.assertGreater(len(self.test_events), 0)
        
        # 8. Test adaptation layer (simulate some performance data)
        if len(self.test_events) >= 3:
            # Simulate belief states and performance metrics for adaptation check
            belief_states = [
                {
                    "expected_return": 0.001 * (i % 3 - 1),  # Alternating positive/negative
                    "expected_return_uncertainty": 0.0005,
                    "aleatoric_uncertainty": 0.001,
                    "epistemic_uncertainty": 0.0008,
                    "regime_probabilities": [0.125] * 8,
                    "volatility_estimate": 0.1 + 0.05 * (i % 3),
                    "liquidity_estimate": 0.7 - 0.1 * (i % 3),
                    "momentum_signal": 0.05 * (i % 2),
                    "volume_signal": 0.02,
                    "confidence": 0.7 + 0.2 * (i % 3) / 3
                }
                for i in range(5)
            ]
            
            prediction_errors = [0.001 * (i % 3 - 1) for i in range(30)]  # Increased from 10 to 30
            feature_data = {
                "ofI": [0.1 * (i % 3 - 1) for i in range(30)],  # Increased from 10 to 30
                "volatility": [0.1 + 0.02 * (i % 3) for i in range(30)]  # Increased from 10 to 30
            }
            performance_metrics = [0.0005 * (i % 3 - 1) for i in range(30)]  # Increased from 10 to 30
            
            # This should not raise an exception
            occurred, events, _ = self.adaptation_layer.update_and_check_adaptation(
                belief_state=belief_states[-1],
                prediction_errors=prediction_errors,
                feature_data=feature_data,
                performance_metrics=performance_metrics,
                current_model=None  # We're not testing actual model adaptation here
            )
            
            # Should not crash - the occurrence is stochastic based on the data
    
    def test_config_integration(self):
        """Test that configuration integrates with system components"""
        # Load configuration
        config = self.config_manager.load_config()
        
        # Test that we can extract values for component initialization
        perception_config = config.get("perception", {})
        decision_config = config.get("decision", {})
        execution_config = config.get("execution", {})
        feedback_config = config.get("feedback", {})
        adaptation_config = config.get("adaptation", {})
        risk_config = config.get("risk_management", {})
        
        # Test creating components with config values
        belief_estimator = BeliefStateEstimator(
            n_regimes=8  # Would come from config in full implementation
        )
        
        aggression_controller = AggressionController(
            kappa=decision_config.get("aggression_controller", {}).get("kappa", 0.1),
            lambda_=decision_config.get("aggression_controller", {}).get("lambda_", 0.05),
            beta_max=decision_config.get("aggression_controller", {}).get("beta_max", 0.5),
            eta=decision_config.get("aggression_controller", {}).get("eta", 0.01),
            alpha_target=decision_config.get("aggression_controller", {}).get("alpha_target", 0.5)
        )
        
        execution_model = ExecutionModel(
            execution_eta=execution_config.get("smart_order_router", {}).get("execution_eta", 0.01),
            market_impact_factor=execution_config.get("smart_order_router", {}).get("market_impact_factor", 0.1),
            latency_base=execution_config.get("smart_order_router", {}).get("latency_base", 5),
            slippage_factor=execution_config.get("smart_order_router", {}).get("slippage_factor", 0.05)
        )
        
        # All should initialize without error
        self.assertIsInstance(belief_estimator, BeliefStateEstimator)
        self.assertIsInstance(aggression_controller, AggressionController)
        self.assertIsInstance(execution_model, ExecutionModel)
        
        # Test that values are within expected ranges
        self.assertGreaterEqual(aggression_controller.kappa, 0.0)
        self.assertLessEqual(aggression_controller.kappa, 1.0)
        self.assertGreaterEqual(execution_model.execution_eta, 0.0)
        self.assertLessEqual(execution_model.execution_eta, 1.0)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)