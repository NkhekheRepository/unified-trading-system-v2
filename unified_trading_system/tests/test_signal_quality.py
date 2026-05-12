"""
Signal Generator Quality Scoring Tests
Tests for multi-uncertainty quality scoring model
"""

import unittest
import numpy as np
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from decision.signal_generator import SignalGenerator


class TestSignalQualityScoring(unittest.TestCase):
    """Test the multi-uncertainty signal quality scoring model"""
    
    def setUp(self):
        self.generator = SignalGenerator({
            'min_confidence_threshold': 0.35,
            'symbol_weights': {'BTC/USDT': 1.0, 'ETH/USDT': 0.7}
        })
    
    def test_epistemic_bonus_low_uncertainty(self):
        """Test that low epistemic uncertainty gives positive bonus"""
        bonus = self.generator._compute_epistemic_bonus(0.03)
        self.assertEqual(bonus, 0.15)
    
    def test_epistemic_bonus_moderate_uncertainty(self):
        """Test that moderate epistemic uncertainty gives smaller bonus"""
        bonus = self.generator._compute_epistemic_bonus(0.12)
        self.assertEqual(bonus, 0.05)
    
    def test_epistemic_bonus_neutral_uncertainty(self):
        """Test that neutral epistemic uncertainty gives no bonus"""
        bonus = self.generator._compute_epistemic_bonus(0.20)
        self.assertEqual(bonus, 0.0)
    
    def test_epistemic_bonus_high_uncertainty(self):
        """Test that high epistemic uncertainty gives penalty"""
        bonus = self.generator._compute_epistemic_bonus(0.45)
        self.assertEqual(bonus, -0.15)
    
    def test_aleatoric_bonus_low_uncertainty(self):
        """Test that low aleatoric uncertainty gives positive bonus"""
        bonus = self.generator._compute_aleatoric_penalty(0.01)
        self.assertEqual(bonus, 0.10)
    
    def test_aleatoric_bonus_moderate_uncertainty(self):
        """Test that moderate aleatoric uncertainty gives smaller bonus"""
        bonus = self.generator._compute_aleatoric_penalty(0.03)
        self.assertEqual(bonus, 0.05)
    
    def test_aleatoric_bonus_neutral_uncertainty(self):
        """Test that neutral aleatoric uncertainty gives no bonus"""
        bonus = self.generator._compute_aleatoric_penalty(0.15)
        self.assertEqual(bonus, -0.03)
    
    def test_aleatoric_bonus_high_uncertainty(self):
        """Test that high aleatoric uncertainty gives penalty"""
        bonus = self.generator._compute_aleatoric_penalty(0.25)
        self.assertEqual(bonus, -0.10)
    
    def test_return_uncertainty_bonus_low(self):
        """Test return uncertainty bonus with low uncertainty"""
        bonus = self.generator._compute_return_uncertainty_bonus(0.01)
        self.assertEqual(bonus, 0.10)
    
    def test_return_uncertainty_bonus_high(self):
        """Test return uncertainty bonus with high uncertainty"""
        bonus = self.generator._compute_return_uncertainty_bonus(0.30)
        self.assertEqual(bonus, -0.10)
    
    def test_calculate_signal_quality_high_quality(self):
        """Test quality calculation for high-quality signal"""
        quality = self.generator.calculate_signal_quality(
            confidence=0.70,
            action="BUY",
            symbol="BTC/USDT",
            epistemic_uncertainty=0.05,
            aleatoric_uncertainty=0.02,
            expected_return_uncertainty=0.02
        )
        self.assertGreaterEqual(quality, 0.60)
        self.assertLessEqual(quality, 1.0)
    
    def test_calculate_signal_quality_low_quality(self):
        """Test quality calculation for low-quality signal"""
        quality = self.generator.calculate_signal_quality(
            confidence=0.30,
            action="SELL",
            symbol="BTC/USDT",
            epistemic_uncertainty=0.45,
            aleatoric_uncertainty=0.25,
            expected_return_uncertainty=0.30
        )
        self.assertLessEqual(quality, 0.30)
    
    def test_calculate_signal_quality_buy_bias(self):
        """Test that BUY signals get bias"""
        buy_quality = self.generator.calculate_signal_quality(
            confidence=0.50,
            action="BUY",
            symbol="BTC/USDT",
            epistemic_uncertainty=0.10,
            aleatoric_uncertainty=0.05,
            expected_return_uncertainty=0.05
        )
        sell_quality = self.generator.calculate_signal_quality(
            confidence=0.50,
            action="SELL",
            symbol="BTC/USDT",
            epistemic_uncertainty=0.10,
            aleatoric_uncertainty=0.05,
            expected_return_uncertainty=0.05
        )
        self.assertGreater(buy_quality, sell_quality)
    
    def test_calculate_signal_quality_symbol_weight(self):
        """Test that symbol weights affect quality"""
        btc_quality = self.generator.calculate_signal_quality(
            confidence=0.50,
            action="BUY",
            symbol="BTC/USDT",
            epistemic_uncertainty=0.10,
            aleatoric_uncertainty=0.05,
            expected_return_uncertainty=0.05
        )
        eth_quality = self.generator.calculate_signal_quality(
            confidence=0.50,
            action="BUY",
            symbol="ETH/USDT",
            epistemic_uncertainty=0.10,
            aleatoric_uncertainty=0.05,
            expected_return_uncertainty=0.05
        )
        self.assertGreater(btc_quality, eth_quality)
    
    def test_calculate_signal_quality_bounds(self):
        """Test that quality is always in [0, 1]"""
        for _ in range(100):
            confidence = np.random.uniform(0.1, 0.9)
            epistemic = np.random.uniform(0.0, 0.5)
            aleatoric = np.random.uniform(0.0, 0.5)
            expected_unc = np.random.uniform(0.0, 0.5)
            
            quality = self.generator.calculate_signal_quality(
                confidence=confidence,
                action="BUY",
                symbol="BTC/USDT",
                epistemic_uncertainty=epistemic,
                aleatoric_uncertainty=aleatoric,
                expected_return_uncertainty=expected_unc
            )
            self.assertGreaterEqual(quality, 0.0)
            self.assertLessEqual(quality, 1.0)


class TestAdaptiveThresholds(unittest.TestCase):
    """Test adaptive confidence thresholds"""
    
    def setUp(self):
        self.generator = SignalGenerator({'min_confidence_threshold': 0.35})
    
    def test_adaptive_threshold_bull_regime(self):
        """Test that bull regime lowers threshold"""
        from perception.belief_state import RegimeType
        threshold = self.generator.get_adaptive_threshold(RegimeType.BULL_LOW_VOL)
        self.assertLess(threshold, 0.35)
    
    def test_adaptive_threshold_crisis_regime(self):
        """Test that crisis regime raises threshold"""
        from perception.belief_state import RegimeType
        threshold = self.generator.get_adaptive_threshold(RegimeType.CRISIS)
        self.assertGreater(threshold, 0.35)
    
    def test_adaptive_threshold_uncertainty_penalty(self):
        """Test that uncertainty increases threshold"""
        from perception.belief_state import RegimeType
        low_unc_threshold = self.generator.get_adaptive_threshold(
            RegimeType.BULL_LOW_VOL,
            epistemic_uncertainty=0.05,
            aleatoric_uncertainty=0.02
        )
        high_unc_threshold = self.generator.get_adaptive_threshold(
            RegimeType.BULL_LOW_VOL,
            epistemic_uncertainty=0.30,
            aleatoric_uncertainty=0.20
        )
        self.assertGreater(high_unc_threshold, low_unc_threshold)
    
    def test_adaptive_threshold_bounds(self):
        """Test that threshold stays in bounds"""
        from perception.belief_state import RegimeType
        for _ in range(100):
            epistemic = np.random.uniform(0.0, 0.5)
            aleatoric = np.random.uniform(0.0, 0.5)
            
            threshold = self.generator.get_adaptive_threshold(
                RegimeType.CRISIS,
                epistemic_uncertainty=epistemic,
                aleatoric_uncertainty=aleatoric
            )
            self.assertGreaterEqual(threshold, 0.15)
            self.assertLessEqual(threshold, 1.0)


class TestUncertaintyGates(unittest.TestCase):
    """Test uncertainty gates"""
    
    def setUp(self):
        self.generator = SignalGenerator()
    
    def test_gate_crisis_strict(self):
        """Test that crisis regime has strictest gates"""
        from perception.belief_state import RegimeType
        result = self.generator.get_uncertainty_gate(
            epistemic_uncertainty=0.08,
            aleatoric_uncertainty=0.04,
            regime=RegimeType.CRISIS
        )
        self.assertTrue(result)
        
        result_fail = self.generator.get_uncertainty_gate(
            epistemic_uncertainty=0.15,
            aleatoric_uncertainty=0.10,
            regime=RegimeType.CRISIS
        )
        self.assertFalse(result_fail)
    
    def test_gate_bull_lenient(self):
        """Test that bull regime has most lenient gates"""
        from perception.belief_state import RegimeType
        result = self.generator.get_uncertainty_gate(
            epistemic_uncertainty=0.25,
            aleatoric_uncertainty=0.12,
            regime=RegimeType.BULL_LOW_VOL
        )
        self.assertTrue(result)
    
    def test_gate_epistemic_fail(self):
        """Test gate fails when epistemic too high"""
        from perception.belief_state import RegimeType
        result = self.generator.get_uncertainty_gate(
            epistemic_uncertainty=0.50,
            aleatoric_uncertainty=0.05,
            regime=RegimeType.BULL_LOW_VOL
        )
        self.assertFalse(result)
    
    def test_gate_aleatoric_fail(self):
        """Test gate fails when aleatoric too high"""
        from perception.belief_state import RegimeType
        result = self.generator.get_uncertainty_gate(
            epistemic_uncertainty=0.10,
            aleatoric_uncertainty=0.50,
            regime=RegimeType.BULL_LOW_VOL
        )
        self.assertFalse(result)


class TestSignalAcceptance(unittest.TestCase):
    """Test signal acceptance logic"""
    
    def setUp(self):
        self.generator = SignalGenerator({
            'min_confidence_threshold': 0.35
        })
    
    def test_should_accept_high_quality(self):
        """Test that high quality signals are accepted"""
        accepted = self.generator.should_accept_signal(
            confidence=0.70,
            action="BUY",
            symbol="BTC/USDT",
            epistemic_uncertainty=0.05,
            aleatoric_uncertainty=0.02,
            expected_return_uncertainty=0.02,
        )
        self.assertTrue(accepted)
    
    def test_should_accept_low_quality(self):
        """Test that low quality signals are rejected"""
        accepted = self.generator.should_accept_signal(
            confidence=0.30,
            action="SELL",
            symbol="BTC/USDT",
            epistemic_uncertainty=0.45,
            aleatoric_uncertainty=0.25,
            expected_return_uncertainty=0.30,
        )
        self.assertFalse(accepted)


class TestPositionSizing(unittest.TestCase):
    """Test position sizing with quality"""
    
    def setUp(self):
        self.generator = SignalGenerator({
            'max_position_size': 0.10
        })
    
    def test_high_quality_full_size(self):
        """Test that high quality gets full size"""
        quantity = self.generator.adjust_position_size(
            action="BUY",
            symbol="BTC/USDT",
            base_quantity=0.10,
            epistemic_uncertainty=0.05,
            aleatoric_uncertainty=0.02,
            expected_return_uncertainty=0.02,
            base_confidence=0.70
        )
        self.assertGreaterEqual(abs(quantity), 2.0)
    
    def test_low_quality_minimal_size(self):
        """Test that low quality gets minimal size"""
        quantity = self.generator.adjust_position_size(
            action="BUY",
            symbol="BTC/USDT",
            base_quantity=0.10,
            epistemic_uncertainty=0.45,
            aleatoric_uncertainty=0.25,
            expected_return_uncertainty=0.30,
            base_confidence=0.30
        )
        self.assertLessEqual(abs(quantity), 1.0)
    
    def test_position_leverage(self):
        """Test that leverage is applied correctly"""
        quantity = self.generator.adjust_position_size(
            action="BUY",
            symbol="BTC/USDT",
            base_quantity=0.05,
            epistemic_uncertainty=0.10,
            aleatoric_uncertainty=0.05,
            expected_return_uncertainty=0.05,
            base_confidence=0.50
        )
        self.assertGreater(quantity, 0.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)