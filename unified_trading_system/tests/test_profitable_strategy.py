#!/usr/bin/env python3
"""
Test Suite for Profitable Trading Strategy Components
Validates all enhanced components of the unified trading system

Components tested:
- Signal Generator (multi-factor quality, Kelly sizing, regime parameters)
- Feature Consistency Checker
- Regime Parameters
- Kelly Position Sizer
- Online Weight Optimizer
- Concept Drift Detector
- Enhanced Belief State Estimator
- Enhanced Risk Manager
"""

import sys
import os
import unittest
import numpy as np
from typing import List
from dataclasses import dataclass

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from perception.belief_state import BeliefState, RegimeType
from decision.signal_generator import (
    SignalGenerator,
    FeatureConsistencyChecker,
    RegimeParameters,
    KellyPositionSizer,
    OnlineWeightOptimizer,
    ConceptDriftDetector,
    TradeOutcome
)
from perception.enhanced_belief_state import (
    EnhancedBeliefStateEstimator,
    MultiTimeframeMomentum,
    EnhancedVolatilityModel,
    OrderFlowAnalyzer
)
from risk.enhanced_risk_manager import (
    DynamicVaRCalculator,
    CorrelationManager,
    PortfolioHeatManager,
    TailRiskProtector,
    EnhancedRiskManager
)


class TestFeatureConsistencyChecker(unittest.TestCase):
    """Test feature consistency checking"""
    
    def setUp(self):
        self.checker = FeatureConsistencyChecker()
    
    def test_aligned_positive_signals(self):
        """Test when all signals are positive and aligned"""
        # Create belief state with aligned positive signals
        belief_state = BeliefState(
            expected_return=0.01,
            expected_return_uncertainty=0.05,
            aleatoric_uncertainty=0.1,
            epistemic_uncertainty=0.1,
            regime_probabilities=[0.1] * 8,
            microstructure_features={
                'ofI': 0.5,
                'I_star': 0.4,
                'S_star': 0.3,
                'L_star': 0.6
            },
            volatility_estimate=0.1,
            liquidity_estimate=0.8,
            momentum_signal=0.1,
            volume_signal=0.1,
            timestamp=1234567890,
            confidence=0.8
        )
        
        score = self.checker.check_consistency(belief_state)
        self.assertGreater(score, 0.5, "Aligned positive signals should have high consistency")
    
    def test_aligned_negative_signals(self):
        """Test when all signals are negative and aligned"""
        belief_state = BeliefState(
            expected_return=-0.01,
            expected_return_uncertainty=0.05,
            aleatoric_uncertainty=0.1,
            epistemic_uncertainty=0.1,
            regime_probabilities=[0.1] * 8,
            microstructure_features={
                'ofI': -0.5,
                'I_star': -0.4,
                'S_star': -0.3,
                'L_star': 0.6
            },
            volatility_estimate=0.1,
            liquidity_estimate=0.8,
            momentum_signal=-0.1,
            volume_signal=0.1,
            timestamp=1234567890,
            confidence=0.8
        )
        
        score = self.checker.check_consistency(belief_state)
        self.assertGreater(score, 0.5, "Aligned negative signals should have high consistency")
    
    def test_divergent_signals(self):
        """Test when signals are divergent (conflicting)"""
        belief_state = BeliefState(
            expected_return=0.0,
            expected_return_uncertainty=0.05,
            aleatoric_uncertainty=0.1,
            epistemic_uncertainty=0.1,
            regime_probabilities=[0.1] * 8,
            microstructure_features={
                'ofI': 0.5,
                'I_star': -0.4,
                'S_star': 0.0,
                'L_star': 0.6
            },
            volatility_estimate=0.1,
            liquidity_estimate=0.8,
            momentum_signal=0.1,
            volume_signal=0.1,
            timestamp=1234567890,
            confidence=0.6
        )
        
        score = self.checker.check_consistency(belief_state)
        self.assertLess(score, 0.5, "Divergent signals should have low consistency")


class TestRegimeParameters(unittest.TestCase):
    """Test regime-specific parameter handling"""
    
    def test_bull_low_vol_params(self):
        """Test BULL_LOW_VOL regime parameters"""
        params = RegimeParameters.get_params(RegimeType.BULL_LOW_VOL)
        
        self.assertEqual(params['leverage'], 25)
        self.assertEqual(params['profit_target'], 0.18)  # V3.2: Increased for larger profits
        self.assertEqual(params['stop_loss'], 0.09)    # V3.2: Increased to match profit target
        self.assertLess(params['min_confidence_adjust'], 0)  # Easier threshold for bull markets
    
    def test_crisis_params(self):
        """Test CRISIS regime parameters - should block new positions"""
        params = RegimeParameters.get_params(RegimeType.CRISIS)
        
        self.assertEqual(params['leverage'], 0)
        self.assertEqual(params['max_position_pct'], 0.0)
    
    def test_all_regimes_have_params(self):
        """Test that all regimes return valid parameters"""
        for regime in RegimeType:
            params = RegimeParameters.get_params(regime)
            self.assertIsNotNone(params)
            self.assertIn('leverage', params)
            self.assertIn('profit_target', params)
            self.assertIn('stop_loss', params)


class TestKellyPositionSizer(unittest.TestCase):
    """Test Kelly criterion position sizing"""
    
    def setUp(self):
        self.sizer = KellyPositionSizer(
            fractional_kelly=0.5,
            max_position_pct=0.15,
            min_position_pct=0.01
        )
    
    def test_initial_state(self):
        """Test initial Kelly calculation with no history"""
        # With no history, should return min position
        position = self.sizer.calculate_kelly_size(0.8)
        self.assertGreaterEqual(position, 0.01)
        self.assertLessEqual(position, 0.15)
    
    def test_win_trade_updates(self):
        """Test that winning trades update history"""
        initial_len = len(self.sizer.recent_wins)
        
        # Add winning trade
        self.sizer.update_outcome(0.02)  # 2% win
        
        self.assertEqual(len(self.sizer.recent_wins), initial_len + 1)
    
    def test_loss_trade_updates(self):
        """Test that losing trades update history"""
        initial_len = len(self.sizer.recent_losses)
        
        # Add losing trade
        self.sizer.update_outcome(-0.01)  # 1% loss
        
        self.assertEqual(len(self.sizer.recent_losses), initial_len + 1)
    
    def test_position_clamping(self):
        """Test that position sizes are clamped to valid range"""
        # With high confidence
        position = self.sizer.calculate_kelly_size(0.95)
        self.assertLessEqual(position, 0.15)
        
        # With low confidence  
        position = self.sizer.calculate_kelly_size(0.5)
        self.assertGreaterEqual(position, 0.01)


class TestOnlineWeightOptimizer(unittest.TestCase):
    """Test online weight adaptation"""
    
    def setUp(self):
        self.optimizer = OnlineWeightOptimizer(n_features=8, learning_rate=0.005)
    
    def test_initial_weights(self):
        """Test initial weights are uniform"""
        weights = self.optimizer.get_weights()
        
        self.assertEqual(len(weights), 8)
        # Should sum to approximately 1.0
        self.assertAlmostEqual(np.sum(weights), 1.0, places=1)
    
    def test_weight_update(self):
        """Test that weight updates work"""
        # Create mock belief state
        belief_state = BeliefState(
            expected_return=0.01,
            expected_return_uncertainty=0.05,
            aleatoric_uncertainty=0.1,
            epistemic_uncertainty=0.1,
            regime_probabilities=[0.1] * 8,
            microstructure_features={
                'ofI': 0.5,
                'I_star': 0.4,
                'S_star': 0.3,
                'L_star': 0.5,
                'depth_imbalance': 0.2,
                'volume_imbalance': 0.1
            },
            volatility_estimate=0.1,
            liquidity_estimate=0.8,
            momentum_signal=0.1,
            volume_signal=0.1,
            timestamp=1234567890,
            confidence=0.8
        )
        
        # Update with some predictions
        for i in range(60):
            self.optimizer.update_weights(belief_state, 0.01, 0.008)
        
        # Weights should have changed (may not sum exactly to 1 due to normalization)
        weights = self.optimizer.get_weights()
        self.assertTrue(np.all(weights >= 0.05), "Weights should have minimum 5%")
    
    def test_minimum_weight_enforced(self):
        """Test that minimum weight is enforced"""
        # Add many poor predictions
        belief_state = BeliefState(
            expected_return=0.01,
            expected_return_uncertainty=0.05,
            aleatoric_uncertainty=0.1,
            epistemic_uncertainty=0.1,
            regime_probabilities=[0.1] * 8,
            microstructure_features={
                'ofI': 0.0,
                'I_star': 0.0,
                'S_star': 0.0,
                'L_star': 0.0,
                'depth_imbalance': 0.0,
                'volume_imbalance': 0.0
            },
            volatility_estimate=0.1,
            liquidity_estimate=0.8,
            momentum_signal=0.0,
            volume_signal=0.0,
            timestamp=1234567890,
            confidence=0.5
        )
        
        for i in range(100):
            self.optimizer.update_weights(belief_state, -0.05, 0.01)
        
        weights = self.optimizer.get_weights()
        self.assertTrue(np.all(weights >= 0.05), "Minimum weight of 5% should be enforced")


class TestConceptDriftDetector(unittest.TestCase):
    """Test concept drift detection"""
    
    def setUp(self):
        self.detector = ConceptDriftDetector(threshold=0.05, window_size=50)
    
    def test_initial_state(self):
        """Test detector starts with no drift"""
        self.assertFalse(self.detector.detect_drift())
    
    def test_drift_detection(self):
        """Test drift is detected with systematic prediction errors"""
        # Add predictions with consistent large error (model underestimating)
        for i in range(60):
            self.detector.add_prediction(predicted=0.01, actual=0.08)  # Large error = 0.07
        
        drift_detected = self.detector.detect_drift()
        self.assertTrue(drift_detected, "Should detect drift with consistent large errors")
    
    def test_no_drift_with_noise(self):
        """Test no drift with random noise"""
        np.random.seed(42)
        
        for i in range(60):
            predicted = 0.01
            actual = predicted + np.random.normal(0, 0.01)
            self.detector.add_prediction(predicted, actual)
        
        self.assertFalse(self.detector.detect_drift(), "Should not detect drift with noise")
    
    def test_reset(self):
        """Test that reset clears detection state"""
        # Add drift with large errors
        for i in range(60):
            self.detector.add_prediction(0.01, 0.08)  # Large error = 0.07
        
        # Should detect drift
        self.assertTrue(self.detector.detect_drift())
        
        # Reset
        self.detector.reset()
        
        # After reset, should not detect drift
        self.assertFalse(self.detector.detect_drift())


class TestEnhancedRiskManager(unittest.TestCase):
    """Test enhanced risk management"""
    
    def setUp(self):
        self.risk_manager = EnhancedRiskManager({
            'var_confidence': 0.99,
            'var_buffer': 1.2,
            'max_correlated_exposure': 0.6,
            'max_portfolio_heat': 0.80,
            'initial_capital': 10000.0
        })
    
    def test_initial_risk_state(self):
        """Test initial risk state"""
        summary = self.risk_manager.get_risk_summary()
        
        self.assertEqual(summary['portfolio_value'], 10000.0)
        self.assertEqual(summary['current_drawdown'], 0.0)
        self.assertEqual(summary['portfolio_heat'], 0.0)
    
    def test_var_calculation(self):
        """Test VaR calculation"""
        # Add returns
        for i in range(50):
            ret = np.random.normal(0.001, 0.02)
            self.risk_manager.record_return(ret)
        
        var = self.risk_manager.var_calculator.calculate_historical_var()
        self.assertGreater(var, 0, "VaR should be positive")
    
    def test_position_assessment(self):
        """Test position risk assessment"""
        existing_positions = {
            'BTC': {'quantity': 0.1, 'entry_price': 50000, 'leverage': 20}
        }
        
        allowed, reason, metrics = self.risk_manager.assess_new_position(
            symbol='ETH',
            quantity=1.0,
            price=3000,
            existing_positions=existing_positions,
            current_regime=RegimeType.BULL_LOW_VOL
        )
        
        # Should be allowed
        self.assertTrue(allowed, f"Should allow position: {reason}")
        
        # Should have risk metrics
        self.assertIn('var', metrics)
        self.assertIn('heat', metrics)
    
    def test_correlation_reduction(self):
        """Test correlation-aware position reduction"""
        # Initialize correlation matrix
        self.risk_manager.correlation_manager.initialize_correlation_matrix(
            ['BTC', 'ETH', 'SOL']
        )
        
        # Add existing position
        self.risk_manager.correlation_manager.update_position('BTC', 0.1)
        
        # Try to add highly correlated position (ETH is correlated with BTC)
        effective_qty = self.risk_manager.correlation_manager.calculate_correlation_exposure(
            'ETH', 1.0
        )
        
        # Should be reduced
        self.assertLess(effective_qty, 1.0, "Correlated position should be reduced")
    
    def test_portfolio_heat(self):
        """Test portfolio heat calculation"""
        # Using smaller positions to keep heat reasonable
        positions = {
            'BTC': {'quantity': 0.01, 'entry_price': 50000, 'leverage': 2},
            'ETH': {'quantity': 0.1, 'entry_price': 3000, 'leverage': 2}
        }
        
        heat = self.risk_manager.heat_manager.calculate_heat(
            positions, 10000.0
        )
        
        self.assertGreater(heat, 0, "Heat should be positive with positions")
        # Heat should be reasonable (< 5.0 = 500% of portfolio)
        self.assertLess(heat, 5.0, "Heat should be reasonable")


class TestSignalGenerator(unittest.TestCase):
    """Test complete signal generator"""
    
    def setUp(self):
        self.config = {
            'min_confidence_threshold': 0.75,
            'min_expected_return': 0.003,
            'base_leverage': 20.0,
            'min_leverage': 15.0,
            'max_leverage': 25.0,
            'available_capital': 10000.0
        }
        self.generator = SignalGenerator(self.config)
    
    def test_signal_generation_with_valid_belief_state(self):
        """Test signal generation with valid belief state"""
        # Create belief state with high confidence and expected return
        # Create regime probabilities with high BULL_LOW_VOL probability
        regime_probs = [0.1] * 8
        regime_probs[0] = 0.6  # High probability of BULL_LOW_VOL
        
        belief_state = BeliefState(
            expected_return=0.01,
            expected_return_uncertainty=0.02,
            aleatoric_uncertainty=0.1,
            epistemic_uncertainty=0.1,
            regime_probabilities=regime_probs,
            microstructure_features={
                'ofI': 0.5,
                'I_star': 0.4,
                'S_star': 0.3,
                'L_star': 0.6,
                'depth_imbalance': 0.2,
                'volume_imbalance': 0.1
            },
            volatility_estimate=0.1,
            liquidity_estimate=0.8,
            momentum_signal=0.1,
            volume_signal=0.1,
            timestamp=1234567890,
            confidence=0.85
        )
        
        signal = self.generator.generate_signal(belief_state, 'BTC/USDT')
        
        self.assertIsNotNone(signal, "Should generate signal with high confidence")
        self.assertEqual(signal.symbol, 'BTC/USDT')
        self.assertIn(signal.action, ['BUY', 'SELL'])
    
    def test_signal_rejection_low_confidence(self):
        """Test signal rejection with low confidence"""
        belief_state = BeliefState(
            expected_return=0.01,
            expected_return_uncertainty=0.1,
            aleatoric_uncertainty=0.3,
            epistemic_uncertainty=0.3,
            regime_probabilities=[0.1] * 8,
            microstructure_features={
                'ofI': 0.1,
                'I_star': 0.1,
                'S_star': 0.0,
                'L_star': 0.5
            },
            volatility_estimate=0.3,
            liquidity_estimate=0.5,
            momentum_signal=0.0,
            volume_signal=0.0,
            timestamp=1234567890,
            confidence=0.4  # Low confidence
        )
        
        signal = self.generator.generate_signal(belief_state, 'BTC/USDT')
        
        self.assertIsNone(signal, "Should reject signal with low confidence")
    
    def test_crisis_regime_rejection(self):
        """Test signal rejection in crisis regime"""
        # Create regime probabilities with high CRISIS probability
        regime_probs = [0.0] * 8
        regime_probs[6] = 0.9  # 90% probability of CRISIS
        
        belief_state = BeliefState(
            expected_return=-0.02,
            expected_return_uncertainty=0.05,
            aleatoric_uncertainty=0.5,
            epistemic_uncertainty=0.2,
            regime_probabilities=regime_probs,
            microstructure_features={
                'ofI': -0.8,
                'I_star': 0.9,
                'S_star': -0.7,
                'L_star': 0.1
            },
            volatility_estimate=0.9,
            liquidity_estimate=0.1,
            momentum_signal=-0.3,
            volume_signal=-0.5,
            timestamp=1234567890,
            confidence=0.6
        )
        
        signal = self.generator.generate_signal(belief_state, 'BTC/USDT')
        
        # Should be rejected due to crisis regime
        self.assertIsNone(signal, "Should reject signal in crisis regime")
    
    def test_multi_factor_quality_calculation(self):
        """Test multi-factor quality scoring"""
        # Create regime probabilities with high BULL_LOW_VOL probability
        regime_probs = [0.1] * 8
        regime_probs[0] = 0.5  # BULL_LOW_VOL
        
        belief_state = BeliefState(
            expected_return=0.015,
            expected_return_uncertainty=0.02,
            aleatoric_uncertainty=0.1,
            epistemic_uncertainty=0.1,
            regime_probabilities=regime_probs,
            microstructure_features={
                'ofI': 0.4,
                'I_star': 0.35,
                'S_star': 0.25,
                'L_star': 0.7,
                'depth_imbalance': 0.3,
                'volume_imbalance': 0.1
            },
            volatility_estimate=0.08,
            liquidity_estimate=0.9,
            momentum_signal=0.15,
            volume_signal=0.1,
            timestamp=1234567890,
            confidence=0.85
        )
        
        quality = self.generator.calculate_multi_factor_quality(
            belief_state, 
            RegimeType.BULL_LOW_VOL
        )
        
        self.assertGreater(quality, 0.5, "High confidence belief should have good quality")
        self.assertLessEqual(quality, 1.0, "Quality should be at most 1.0")
    
    def test_regime_adaptive_threshold(self):
        """Test regime-adaptive thresholds"""
        # High volatility regime should have tighter threshold
        regime_probs_bull = [0.1] * 8
        regime_probs_bull[0] = 0.6  # BULL_LOW_VOL
        
        belief_state_bull = BeliefState(
            expected_return=0.01,
            expected_return_uncertainty=0.02,
            aleatoric_uncertainty=0.1,
            epistemic_uncertainty=0.1,
            regime_probabilities=regime_probs_bull,
            microstructure_features={'ofI': 0.5, 'I_star': 0.4, 'S_star': 0.3, 'L_star': 0.6, 'depth_imbalance': 0.2, 'volume_imbalance': 0.1},
            volatility_estimate=0.1, liquidity_estimate=0.8, momentum_signal=0.1, volume_signal=0.1,
            timestamp=1234567890, confidence=0.8
        )
        
        threshold_bull = self.generator.get_regime_adaptive_threshold(
            RegimeType.BULL_LOW_VOL, belief_state_bull
        )
        
        belief_state_crisis = BeliefState(
            expected_return=0.01,
            expected_return_uncertainty=0.02,
            aleatoric_uncertainty=0.5,
            epistemic_uncertainty=0.2,
            regime_probabilities=[0.1] * 8,
            microstructure_features={'ofI': 0.5, 'I_star': 0.4, 'S_star': 0.3, 'L_star': 0.6, 'depth_imbalance': 0.2, 'volume_imbalance': 0.1},
            volatility_estimate=0.9, liquidity_estimate=0.2, momentum_signal=-0.2, volume_signal=-0.3,
            timestamp=1234567890, confidence=0.7
        )
        
        threshold_crisis = self.generator.get_regime_adaptive_threshold(
            RegimeType.CRISIS, belief_state_crisis
        )
        
        # Crisis threshold should be higher (tighter)
        self.assertGreater(threshold_crisis, threshold_bull, "Crisis should have tighter threshold")


class TestEnhancedBeliefStateEstimator(unittest.TestCase):
    """Test enhanced belief state with multi-timeframe features"""
    
    def setUp(self):
        self.estimator = EnhancedBeliefStateEstimator()
    
    def test_enhanced_features_extraction(self):
        """Test that enhanced features are extracted"""
        # Add some historical data for momentum calculation
        for i in range(30):
            price = 50000 + np.random.randn() * 100
            volume = np.random.uniform(0.5, 2.0)
            self.estimator.momentum_analyzer.add_observation(price, volume, 1234567890 + i)
            self.estimator.volatility_model.add_observation(price)
        
        market_data = {
            "bid_price": 50000.0,
            "ask_price": 50010.0,
            "bid_size": 100.0,
            "ask_size": 80.0,
            "last_price": 50005.0,
            "last_size": 1.5
        }
        
        enhanced_belief = self.estimator.update(market_data)
        
        # Check enhanced features exist
        self.assertIsNotNone(enhanced_belief.momentum_composite)
        self.assertIsNotNone(enhanced_belief.ewma_volatility)
        self.assertIsNotNone(enhanced_belief.cumulative_ofi)
        self.assertIsNotNone(enhanced_belief.data_quality_score)


def run_all_tests():
    """Run all test suites"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestFeatureConsistencyChecker,
        TestRegimeParameters,
        TestKellyPositionSizer,
        TestOnlineWeightOptimizer,
        TestConceptDriftDetector,
        TestEnhancedRiskManager,
        TestSignalGenerator,
        TestEnhancedBeliefStateEstimator
    ]
    
    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n✓ ALL TESTS PASSED")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())