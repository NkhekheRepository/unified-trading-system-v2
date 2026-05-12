"""
Tests for Enhanced Telegram Alerts
Tests for the modernized alerting system
"""

import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from observability.telegram_alerts import (
    EnhancedAlert,
    AlertCategory,
    AlertPriority,
    StakeholderGroup,
    AlertContext,
    AlertAction,
    TelegramFormatter,
    AlertContextEnricher,
    ActionSuggester,
    create_trade_alert,
    create_risk_alert,
    create_system_alert,
    create_performance_alert,
)


class TestAlertDataStructures(unittest.TestCase):
    """Test enhanced alert data structures"""
    
    def test_create_basic_alert(self):
        """Test basic alert creation"""
        alert = EnhancedAlert(
            title="Test Alert",
            message="This is a test message",
            severity_name="INFO",
            category=AlertCategory.TRADE,
            priority=AlertPriority.P2_MEDIUM,
        )
        
        self.assertEqual(alert.title, "Test Alert")
        self.assertEqual(alert.severity_name, "INFO")
        self.assertEqual(alert.category, AlertCategory.TRADE)
        self.assertEqual(alert.priority, AlertPriority.P2_MEDIUM)
    
    def test_alert_context(self):
        """Test alert context data"""
        ctx = AlertContext(
            symbol="BTC/USDT",
            regime="BULL_LOW_VOL",
            confidence=0.72,
            expected_return=0.0015,
            epistemic_uncertainty=0.08,
            aleatoric_uncertainty=0.03,
        )
        
        self.assertEqual(ctx.symbol, "BTC/USDT")
        self.assertEqual(ctx.regime, "BULL_LOW_VOL")
        self.assertAlmostEqual(ctx.confidence, 0.72)
    
    def test_alert_actions(self):
        """Test alert actions"""
        action1 = AlertAction(
            label="Reduce position size",
            description="High uncertainty detected",
            urgency="immediate",
        )
        
        self.assertEqual(action1.label, "Reduce position size")
        self.assertEqual(action1.urgency, "immediate")
        self.assertFalse(action1.optional)


class TestAlertCategories(unittest.TestCase):
    """Test alert categories"""
    
    def test_all_categories_defined(self):
        """Test all categories are defined"""
        expected = ["trade", "risk", "system", "performance", "strategy", "compliance"]
        actual = [c.value for c in AlertCategory]
        for expected_cat in expected:
            self.assertIn(expected_cat, actual)
    
    def test_priority_levels(self):
        """Test priority levels P0-P4"""
        expected = ["P0_CRITICAL", "P1_HIGH", "P2_MEDIUM", "P3_LOW", "P4_DEBUG"]
        for expected_pri in expected:
            self.assertTrue(any(p.name == expected_pri for p in AlertPriority))


class TestStakeholderGroups(unittest.TestCase):
    """Test stakeholder groups"""
    
    def test_all_stakeholders_defined(self):
        """Test all stakeholder groups"""
        expected = ["trader", "risk_manager", "quant", "manager", "devops"]
        actual = [s.value for s in StakeholderGroup]
        for expected_st in expected:
            self.assertIn(expected_st, actual)


class TestTelegramFormatter(unittest.TestCase):
    """Test Telegram message formatter"""
    
    def test_format_trader_alert(self):
        """Test trader format"""
        alert = create_trade_alert(
            symbol="BTC/USDT",
            side="BUY",
            quantity=0.1,
            price=50000.0,
            success=True,
            belief_state={
                "symbol": "BTC/USDT",
                "regime": "BULL_LOW_VOL",
                "confidence": 0.72,
                "expected_return": 0.0015,
                "epistemic_uncertainty": 0.08,
                "aleatoric_uncertainty": 0.03,
            }
        )
        
        formatted = TelegramFormatter.format(alert, StakeholderGroup.TRADER)
        
        self.assertIn("BTC/USDT", formatted)
        self.assertIn("BUY", formatted)
        self.assertIn("$50,000.00", formatted)
        self.assertIn("BULL_LOW_VOL", formatted)
        self.assertIn("72.0%", formatted)
    
    def test_format_risk_alert(self):
        """Test risk manager format"""
        alert = create_risk_alert(
            violation_type="DRAWDOWN_WARNING",
            message="Drawdown approaching limit",
            details={},
            risk_assessment={
                "drawdown": 0.042,
                "leverage_ratio": 0.72,
                "cvar": 48000,
                "liquidity_score": 0.72,
            }
        )
        
        formatted = TelegramFormatter.format(alert, StakeholderGroup.RISK_MANAGER)
        
        self.assertIn("RISK ALERT", formatted)
        self.assertIn("DRAWDOWN_WARNING", formatted)
        self.assertIn("4.2%", formatted)
        self.assertIn("P0", formatted)
    
    def test_format_system_alert(self):
        """Test system/devops format"""
        alert = create_system_alert(
            component="Binance WebSocket",
            status="DEGRADED",
            details={"latency": 245, "error_rate": 0.032}
        )
        
        formatted = TelegramFormatter.format(alert, StakeholderGroup.DEVOPS)
        
        self.assertIn("SYSTEM ALERT", formatted)
        self.assertIn("Binance WebSocket", formatted)
        self.assertIn("245ms", formatted)
    
    def test_format_performance_alert(self):
        """Test quant/performance format"""
        alert = create_performance_alert(
            metric_name="Win Rate",
            value=0.783,
            threshold=0.75,
            is_positive=True,
            metrics={
                "win_rate": 0.783,
                "sharpe_ratio": 1.45,
            }
        )
        
        formatted = TelegramFormatter.format(alert, StakeholderGroup.QUANT)
        
        self.assertIn("Win Rate", formatted)
        self.assertIn("78.3%", formatted)
        self.assertIn("Sharpe", formatted)
    
    def test_format_executive_alert(self):
        """Test executive format"""
        alert = create_trade_alert(
            symbol="ETH/USDT",
            side="SELL",
            quantity=1.0,
            price=3000.0,
            success=True,
        )
        
        formatted = TelegramFormatter.format(alert, StakeholderGroup.MANAGER)
        
        self.assertIn("ETH/USDT", formatted)
        self.assertIn("SELL", formatted)


class TestAlertCreation(unittest.TestCase):
    """Test alert creation functions"""
    
    def test_create_successful_trade_alert(self):
        """Test successful trade alert"""
        alert = create_trade_alert(
            symbol="BTC/USDT",
            side="BUY",
            quantity=0.1,
            price=50000.0,
            success=True,
        )
        
        self.assertEqual(alert.title, "Trade Filled: BTC/USDT")
        self.assertEqual(alert.severity_name, "INFO")
        self.assertEqual(alert.priority, AlertPriority.P3_LOW)
        self.assertEqual(alert.category, AlertCategory.TRADE)
    
    def test_create_failed_trade_alert(self):
        """Test failed trade alert"""
        alert = create_trade_alert(
            symbol="BTC/USDT",
            side="BUY",
            quantity=0.1,
            price=0,
            success=False,
            error="Insufficient margin",
        )
        
        self.assertEqual(alert.title, "Trade Failed: BTC/USDT")
        self.assertEqual(alert.severity_name, "ERROR")
        self.assertEqual(alert.priority, AlertPriority.P1_HIGH)
    
    def test_create_risk_alert(self):
        """Test risk alert"""
        alert = create_risk_alert(
            violation_type="DRAWDOWN_WARNING",
            message="Drawdown approaching limit",
            details={},
            risk_assessment={
                "drawdown": 0.042,
                "leverage_ratio": 0.72,
            }
        )
        
        self.assertIn("Risk Alert", alert.title)
        self.assertEqual(alert.severity_name, "CRITICAL")
        self.assertEqual(alert.priority, AlertPriority.P0_CRITICAL)
    
    def test_create_performance_alert(self):
        """Test performance alert"""
        alert = create_performance_alert(
            metric_name="Sharpe Ratio",
            value=1.45,
            threshold=1.0,
            is_positive=True,
        )
        
        self.assertIn("Sharpe Ratio", alert.title)
        self.assertEqual(alert.severity_name, "INFO")


class TestContextEnricher(unittest.TestCase):
    """Test alert context enrichment"""
    
    def test_enrich_trade_with_belief_state(self):
        """Test enriching trade with belief state"""
        alert = EnhancedAlert(
            title="Test",
            message="Test",
        )
        
        belief_state = {
            "symbol": "BTC/USDT",
            "regime": "BULL_LOW_VOL",
            "confidence": 0.72,
            "expected_return": 0.0015,
            "epistemic_uncertainty": 0.08,
            "aleatoric_uncertainty": 0.03,
        }
        
        enriched = AlertContextEnricher.enrich_trade(alert, belief_state)
        
        self.assertIsNotNone(enriched.context)
        self.assertEqual(enriched.context.symbol, "BTC/USDT")
        self.assertEqual(enriched.context.confidence, 0.72)


class TestActionSuggester(unittest.TestCase):
    """Test action suggestion engine"""
    
    def test_suggest_for_trade_low_confidence(self):
        """Test suggestions for low confidence trade"""
        alert = EnhancedAlert(
            title="Test",
            message="Test",
            context=AlertContext(confidence=0.3),
        )
        
        actions = ActionSuggester.suggest_for_trade(alert)
        
        self.assertGreater(len(actions), 0)
        self.assertTrue(any("market" in a.label.lower() for a in actions))
    
    def test_suggest_for_risk_high_drawdown(self):
        """Test suggestions for high drawdown"""
        alert = EnhancedAlert(
            title="Test",
            message="Test",
            context=AlertContext(drawdown=0.08),
        )
        
        actions = ActionSuggester.suggest_for_risk(alert)
        
        self.assertGreater(len(actions), 0)


class TestVisualFormatting(unittest.TestCase):
    """Test visual formatting elements"""
    
    def test_priority_labels(self):
        """Test priority label formatting"""
        self.assertEqual(TelegramFormatter.PRIORITY_LABELS[AlertPriority.P0_CRITICAL][0], "🔴 P0")
        self.assertEqual(TelegramFormatter.PRIORITY_LABELS[AlertPriority.P3_LOW][0], "🟢 P3")
    
    def test_severity_colors(self):
        """Test severity color mapping"""
        self.assertEqual(TelegramFormatter.SEVERITY_COLORS["INFO"], "🔵")
        self.assertEqual(TelegramFormatter.SEVERITY_COLORS["ERROR"], "🔴")
        self.assertEqual(TelegramFormatter.SEVERITY_COLORS["WARNING"], "🟡")
    
    def test_category_emoji(self):
        """Test category emoji mapping"""
        self.assertEqual(TelegramFormatter.CATEGORY_EMOJI[AlertCategory.TRADE], "📊")
        self.assertEqual(TelegramFormatter.CATEGORY_EMOJI[AlertCategory.RISK], "🚨")
        self.assertEqual(TelegramFormatter.CATEGORY_EMOJI[AlertCategory.SYSTEM], "🔧")


if __name__ == '__main__':
    unittest.main(verbosity=2)