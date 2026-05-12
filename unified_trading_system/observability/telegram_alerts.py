"""
Enhanced Alerting System for Unified Trading System
Modern, professional-grade Telegram alerts with rich formatting and context.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


class AlertCategory(Enum):
    """Alert categories for different stakeholders"""
    TRADE = "trade"           # Traders/Portfolio Managers
    RISK = "risk"             # Risk Management
    SYSTEM = "system"          # DevOps/System Admin
    PERFORMANCE = "performance"  # P&L, Strategy Performance
    STRATEGY = "strategy"      # Quant/Research
    COMPLIANCE = "compliance"   # Compliance/Regulatory


class AlertPriority(Enum):
    """Alert priority levels (P0 = Critical)"""
    P0_CRITICAL = 0   # Immediate action required
    P1_HIGH = 1       # Urgent attention needed
    P2_MEDIUM = 2      # Should be reviewed
    P3_LOW = 3        # Informational
    P4_DEBUG = 4      # Developer only


class StakeholderGroup(Enum):
    """Target stakeholder groups"""
    TRADER = "trader"
    RISK_MANAGER = "risk_manager"
    QUANT = "quant"
    MANAGER = "manager"
    DEVOPS = "devops"


@dataclass
class AlertAction:
    """Suggested action for an alert"""
    label: str
    description: str
    urgency: str  # "immediate", "within_1h", "within_1d"
    optional: bool = False


@dataclass
class AlertContext:
    """Contextual information for alerts"""
    symbol: Optional[str] = None
    regime: Optional[str] = None
    confidence: Optional[float] = None
    expected_return: Optional[float] = None
    epistemic_uncertainty: Optional[float] = None
    aleatoric_uncertainty: Optional[float] = None
    current_pnl: Optional[float] = None
    daily_pnl: Optional[float] = None
    drawdown: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    win_rate: Optional[float] = None
    exposure: Optional[float] = None
    var_95: Optional[float] = None
    liquidity_score: Optional[float] = None
    latency_ms: Optional[float] = None
    error_rate: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnhancedAlert:
    """Enhanced alert with rich formatting and context"""
    title: str
    message: str
    summary: str = ""
    severity_name: str = "INFO"
    category: AlertCategory = AlertCategory.TRADE
    priority: AlertPriority = AlertPriority.P2_MEDIUM
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None
    context: Optional[AlertContext] = None
    actions: List[AlertAction] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    links: Dict[str, str] = field(default_factory=dict)


class TelegramFormatter:
    """Modern Telegram message formatter"""
    
    SEVERITY_COLORS = {
        "DEBUG": "⚪",
        "INFO": "🔵",
        "WARNING": "🟡",
        "ERROR": "🔴",
        "CRITICAL": "🚨",
    }
    
    PRIORITY_LABELS = {
        AlertPriority.P0_CRITICAL: ("🔴 P0", "CRITICAL"),
        AlertPriority.P1_HIGH: ("🟠 P1", "HIGH"),
        AlertPriority.P2_MEDIUM: ("🟡 P2", "MEDIUM"),
        AlertPriority.P3_LOW: ("🟢 P3", "LOW"),
        AlertPriority.P4_DEBUG: ("⚪ P4", "DEBUG"),
    }
    
    CATEGORY_EMOJI = {
        AlertCategory.TRADE: "📊",
        AlertCategory.RISK: "🚨",
        AlertCategory.SYSTEM: "🔧",
        AlertCategory.PERFORMANCE: "💹",
        AlertCategory.STRATEGY: "🔬",
        AlertCategory.COMPLIANCE: "⚖️",
    }
    
    @classmethod
    def format(cls, alert: EnhancedAlert, stakeholder: StakeholderGroup = None) -> str:
        """Format an enhanced alert as Telegram message"""
        
        if stakeholder == StakeholderGroup.DEVOPS:
            return cls._format_devops(alert)
        elif stakeholder == StakeholderGroup.QUANT:
            return cls._format_quant(alert)
        elif stakeholder == StakeholderGroup.RISK_MANAGER:
            return cls._format_risk(alert)
        elif stakeholder == StakeholderGroup.MANAGER:
            return cls._format_executive(alert)
        else:
            return cls._format_trader(alert)
    
    @classmethod
    def _format_trader(cls, alert: EnhancedAlert) -> str:
        """Format for traders/portfolio managers"""
        lines = []
        
        priority_icon, priority_name = cls.PRIORITY_LABELS.get(alert.priority, ("⚪", "INFO"))
        severity_icon = cls.SEVERITY_COLORS.get(alert.severity_name, "🔵")
        category_icon = cls.CATEGORY_EMOJI.get(alert.category, "📊")
        
        header = f"{severity_icon} {priority_icon} {category_icon} {alert.title}"
        lines.append(header)
        lines.append("━" * min(len(header), 40))
        
        if alert.summary:
            lines.append(f"📋 {alert.summary}")
            lines.append("")
        
        lines.append(alert.message)
        
        if alert.context:
            lines.append("")
            lines.append(cls._format_metrics(alert.context))
        
        if alert.actions:
            lines.append("")
            lines.append(cls._format_actions(alert.actions))
        
        lines.append("")
        lines.append(f"⏰ {alert.timestamp.strftime('%H:%M:%S UTC')}")
        
        return "\n".join(lines)
    
    @classmethod
    def _format_risk(cls, alert: EnhancedAlert) -> str:
        """Format for risk managers"""
        lines = []
        
        priority_icon, priority_name = cls.PRIORITY_LABELS.get(alert.priority, ("⚪", "INFO"))
        
        lines.append(f"🚨 {priority_icon} RISK ALERT: {alert.title}")
        lines.append("━" * 38)
        
        if alert.summary:
            lines.append(f"⚠️ {alert.summary}")
            lines.append("")
        
        lines.append(alert.message)
        
        if alert.context:
            lines.append("")
            lines.append(cls._format_risk_metrics(alert.context))
        
        if alert.actions:
            lines.append("")
            lines.append(cls._format_actions(alert.actions))
        
        lines.append("")
        lines.append(f"⏰ {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        return "\n".join(lines)
    
    @classmethod
    def _format_quant(cls, alert: EnhancedAlert) -> str:
        """Format for quant researchers"""
        lines = []
        
        priority_icon, priority_name = cls.PRIORITY_LABELS.get(alert.priority, ("⚪", "INFO"))
        
        lines.append(f"🔬 {priority_icon} {alert.title}")
        lines.append("━" * 38)
        
        if alert.summary:
            lines.append(f"📊 {alert.summary}")
            lines.append("")
        
        lines.append(alert.message)
        
        if alert.context:
            lines.append("")
            lines.append(cls._format_quant_metrics(alert.context))
        
        if alert.actions:
            lines.append("")
            lines.append(cls._format_actions(alert.actions))
        
        lines.append("")
        lines.append(f"⏰ {alert.timestamp.strftime('%H:%M:%S UTC')}")
        
        if alert.tags:
            lines.append(f"Tags: {', '.join(alert.tags)}")
        
        return "\n".join(lines)
    
    @classmethod
    def _format_devops(cls, alert: EnhancedAlert) -> str:
        """Format for DevOps/system admins"""
        lines = []
        
        lines.append(f"🔧 SYSTEM ALERT: {alert.title}")
        lines.append("━" * 38)
        
        lines.append(alert.message)
        
        if alert.context:
            lines.append("")
            lines.append(cls._format_system_metrics(alert.context))
        
        if alert.actions:
            lines.append("")
            lines.append(cls._format_troubleshooting(alert.actions))
        
        lines.append("")
        lines.append(f"⏰ {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        if alert.correlation_id:
            lines.append(f"ID: {alert.correlation_id[:16]}")
        
        return "\n".join(lines)
    
    @classmethod
    def _format_executive(cls, alert: EnhancedAlert) -> str:
        """Format for executives/managers"""
        lines = []
        
        priority_icon, priority_name = cls.PRIORITY_LABELS.get(alert.priority, ("⚪", "INFO"))
        
        lines.append(f"📌 {priority_icon} {alert.title}")
        lines.append("━" * 38)
        
        if alert.summary:
            lines.append(alert.summary)
        else:
            lines.append(alert.message)
        
        if alert.context and alert.context.current_pnl is not None:
            lines.append("")
            pnl_str = f"${alert.context.current_pnl:,.0f}" if alert.context.current_pnl else "N/A"
            lines.append(f"💰 Current P&L: {pnl_str}")
        
        if alert.actions:
            lines.append("")
            lines.append("📋 Next Steps:")
            for i, action in enumerate(alert.actions[:2], 1):
                lines.append(f"  {i}. {action.label}")
        
        lines.append("")
        lines.append(f"⏰ {alert.timestamp.strftime('%H:%M:%S UTC')}")
        
        return "\n".join(lines)
    
    @classmethod
    def _format_metrics(cls, ctx: AlertContext) -> str:
        """Format metrics for traders"""
        lines = ["📊 Metrics:"]
        
        if ctx.regime:
            lines.append(f"  Regime: {ctx.regime}")
        if ctx.confidence is not None:
            lines.append(f"  Confidence: {ctx.confidence:.1%}")
        if ctx.expected_return is not None:
            lines.append(f"  Expected Return: {ctx.expected_return:.4%}")
        if ctx.epistemic_uncertainty is not None:
            lines.append(f"  Epistemic Unc: {ctx.epistemic_uncertainty:.3f}")
        if ctx.aleatoric_uncertainty is not None:
            lines.append(f"  Aleatoric Unc: {ctx.aleatoric_uncertainty:.3f}")
        
        return "\n".join(lines)
    
    @classmethod
    def _format_risk_metrics(cls, ctx: AlertContext) -> str:
        """Format risk metrics"""
        lines = ["📊 Risk Metrics:"]
        
        if ctx.drawdown is not None:
            dd_str = f"{ctx.drawdown:.1%}"
            lines.append(f"  Drawdown: {dd_str}")
        if ctx.exposure is not None:
            lines.append(f"  Exposure: {ctx.exposure:.0%}")
        if ctx.var_95 is not None:
            lines.append(f"  VaR (95%): ${ctx.var_95:,.0f}")
        if ctx.liquidity_score is not None:
            lines.append(f"  Liquidity: {ctx.liquidity_score:.2f}")
        
        return "\n".join(lines)
    
    @classmethod
    def _format_quant_metrics(cls, ctx: AlertContext) -> str:
        """Format quant metrics"""
        lines = ["📈 Model Metrics:"]
        
        if ctx.win_rate is not None:
            lines.append(f"  Win Rate: {ctx.win_rate:.1%}")
        if ctx.sharpe_ratio is not None:
            lines.append(f"  Sharpe: {ctx.sharpe_ratio:.2f}")
        if ctx.epistemic_uncertainty is not None:
            lines.append(f"  Epistemic Unc: {ctx.epistemic_uncertainty:.3f}")
        if ctx.aleatoric_uncertainty is not None:
            lines.append(f"  Aleatoric Unc: {ctx.aleatoric_uncertainty:.3f}")
        
        return "\n".join(lines)
    
    @classmethod
    def _format_system_metrics(cls, ctx: AlertContext) -> str:
        """Format system metrics"""
        lines = ["📊 System Metrics:"]
        
        if ctx.latency_ms is not None:
            lines.append(f"  Latency: {ctx.latency_ms:.0f}ms")
        if ctx.error_rate is not None:
            lines.append(f"  Error Rate: {ctx.error_rate:.2%}")
        
        return "\n".join(lines)
    
    @classmethod
    def _format_actions(cls, actions: List[AlertAction]) -> str:
        """Format suggested actions"""
        lines = ["⚡ Actions:"]
        for action in actions[:3]:
            urgent_marker = "⚠️" if action.urgency == "immediate" else "  "
            lines.append(f"  {urgent_marker}• {action.label}")
            if action.description:
                lines.append(f"      {action.description}")
        return "\n".join(lines)
    
    @classmethod
    def _format_troubleshooting(cls, actions: List[AlertAction]) -> str:
        """Format troubleshooting steps"""
        lines = ["🔧 Troubleshooting:"]
        for i, action in enumerate(actions[:4], 1):
            lines.append(f"  {i}. {action.label}")
        return "\n".join(lines)


class AlertContextEnricher:
    """Enrich alerts with contextual information"""
    
    @staticmethod
    def enrich_trade(alert: EnhancedAlert, belief_state: Dict = None, 
                     execution_result: Dict = None) -> EnhancedAlert:
        """Enrich trade alerts with belief state and execution context"""
        
        if belief_state:
            ctx = AlertContext(
                symbol=belief_state.get("symbol"),
                regime=belief_state.get("regime"),
                confidence=belief_state.get("confidence"),
                expected_return=belief_state.get("expected_return"),
                epistemic_uncertainty=belief_state.get("epistemic_uncertainty"),
                aleatoric_uncertainty=belief_state.get("aleatoric_uncertainty"),
            )
            alert.context = ctx
            
            if belief_state.get("confidence", 0) < 0.4:
                alert.actions.append(AlertAction(
                    label="Review signal confidence",
                    description="Confidence below threshold - verify market conditions",
                    urgency="within_1h"
                ))
        
        if execution_result:
            if alert.context:
                alert.context.latency_ms = execution_result.get("latency")
                alert.context.error_rate = 1.0 if not execution_result.get("success") else 0.0
        
        return alert
    
    @staticmethod
    def enrich_risk(alert: EnhancedAlert, risk_assessment: Dict = None,
                   portfolio_state: Dict = None) -> EnhancedAlert:
        """Enrich risk alerts with risk context"""
        
        if risk_assessment:
            ctx = AlertContext(
                drawdown=risk_assessment.get("drawdown"),
                exposure=risk_assessment.get("leverage_ratio"),
                var_95=risk_assessment.get("cvar"),
                liquidity_score=risk_assessment.get("liquidity_score"),
            )
            alert.context = ctx
            
            drawdown = risk_assessment.get("drawdown", 0)
            if drawdown > 0.08:
                alert.priority = AlertPriority.P0_CRITICAL
                alert.actions.append(AlertAction(
                    label="STOP TRADING IMMEDIATELY",
                    description="Drawdown exceeds 8% limit",
                    urgency="immediate",
                    optional=False
                ))
        
        return alert
    
    @staticmethod
    def enrich_performance(alert: EnhancedAlert, metrics: Dict = None) -> EnhancedAlert:
        """Enrich performance alerts with metrics"""
        
        if metrics:
            ctx = AlertContext(
                current_pnl=metrics.get("current_pnl"),
                daily_pnl=metrics.get("daily_pnl"),
                sharpe_ratio=metrics.get("sharpe_ratio"),
                win_rate=metrics.get("win_rate"),
                drawdown=metrics.get("drawdown"),
            )
            alert.context = ctx
        
        return alert


class ActionSuggester:
    """Suggest actions based on alert type and context"""
    
    @classmethod
    def suggest_for_trade(cls, alert: EnhancedAlert) -> List[AlertAction]:
        """Suggest actions for trade alerts"""
        actions = []
        
        if alert.context and alert.context.confidence:
            if alert.context.confidence < 0.4:
                actions.append(AlertAction(
                    label="Verify market conditions",
                    description="Confidence low - check for regime change",
                    urgency="within_1h"
                ))
        
        if alert.context and alert.context.epistemic_uncertainty:
            if alert.context.epistemic_uncertainty > 0.3:
                actions.append(AlertAction(
                    label="Reduce position size",
                    description="High uncertainty - consider smaller positions",
                    urgency="immediate"
                ))
        
        return actions
    
    @classmethod
    def suggest_for_risk(cls, alert: EnhancedAlert) -> List[AlertAction]:
        """Suggest actions for risk alerts"""
        actions = []
        
        if alert.context:
            if alert.context.drawdown and alert.context.drawdown > 0.05:
                actions.append(AlertAction(
                    label="Reduce positions by 30%",
                    description="Drawdown approaching limit",
                    urgency="immediate"
                ))
            
            if alert.context.exposure and alert.context.exposure > 25:
                actions.append(AlertAction(
                    label="Close lever positions",
                    description="Leverage ratio elevated",
                    urgency="immediate"
                ))
        
        return actions
    
    @classmethod
    def suggest_for_system(cls, alert: EnhancedAlert) -> List[AlertAction]:
        """Suggest actions for system alerts"""
        actions = [
            AlertAction(
                label="Check system health dashboard",
                description="Verify all components responding",
                urgency="within_1h"
            ),
            AlertAction(
                label="Review recent logs",
                description="Check for pattern of errors",
                urgency="within_1d"
            ),
        ]
        return actions


def create_trade_alert(
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    success: bool,
    belief_state: Dict = None,
    error: Optional[str] = None,
) -> EnhancedAlert:
    """Create an enhanced trade alert"""
    
    if success:
        title = f"Trade Filled: {symbol}"
        summary = f"{side} {quantity:.4f} @ ${price:,.2f}"
        severity = "INFO"
        priority = AlertPriority.P3_LOW
    else:
        title = f"Trade Failed: {symbol}"
        summary = f"Order rejected - {error or 'Unknown error'}"
        severity = "ERROR"
        priority = AlertPriority.P1_HIGH
    
    alert = EnhancedAlert(
        title=title,
        message=summary,
        summary=f"Order {side} | Qty: {quantity:.4f} | Price: ${price:,.2f}",
        severity_name=severity,
        category=AlertCategory.TRADE,
        priority=priority,
    )
    
    if belief_state:
        alert = AlertContextEnricher.enrich_trade(alert, belief_state)
    
    return alert


def create_risk_alert(
    violation_type: str,
    message: str,
    details: Dict[str, Any],
    risk_assessment: Dict = None,
) -> EnhancedAlert:
    """Create an enhanced risk alert"""
    
    alert = EnhancedAlert(
        title=f"Risk Alert: {violation_type}",
        message=message,
        summary=f"Risk violation detected - {violation_type}",
        severity_name="CRITICAL",
        category=AlertCategory.RISK,
        priority=AlertPriority.P0_CRITICAL,
    )
    
    if risk_assessment:
        alert = AlertContextEnricher.enrich_risk(alert, risk_assessment)
    
    alert.actions = ActionSuggester.suggest_for_risk(alert)
    
    return alert


def create_system_alert(
    component: str,
    status: str,
    details: Dict[str, Any] = None,
) -> EnhancedAlert:
    """Create an enhanced system alert"""
    
    severity = "WARNING" if status != "healthy" else "INFO"
    priority = AlertPriority.P2_MEDIUM if status == "healthy" else AlertPriority.P1_HIGH
    
    alert = EnhancedAlert(
        title=f"System: {component} - {status.upper()}",
        message=f"Component '{component}' is now {status}",
        severity_name=severity,
        category=AlertCategory.SYSTEM,
        priority=priority,
    )
    
    if details:
        alert.context = AlertContext(
            latency_ms=details.get("latency"),
            error_rate=details.get("error_rate"),
        )
    
    return alert


def create_performance_alert(
    metric_name: str,
    value: float,
    threshold: float,
    is_positive: bool = True,
    metrics: Dict = None,
) -> EnhancedAlert:
    """Create an enhanced performance alert"""
    
    direction = "📈" if is_positive else "📉"
    severity = "INFO" if is_positive else "WARNING"
    priority = AlertPriority.P3_LOW if is_positive else AlertPriority.P2_MEDIUM
    
    alert = EnhancedAlert(
        title=f"{direction} Performance: {metric_name}",
        message=f"{metric_name}: {value:.3f} (threshold: {threshold:.3f})",
        severity_name=severity,
        category=AlertCategory.PERFORMANCE,
        priority=priority,
    )
    
    if metrics:
        alert = AlertContextEnricher.enrich_performance(alert, metrics)
    
    return alert


async def send_enhanced_alert(
    alert: EnhancedAlert,
    stakeholder: StakeholderGroup = None,
    bot_token: str = None,
    chat_ids: List[str] = None,
) -> bool:
    """Send an enhanced alert to Telegram"""
    
    if not bot_token or not chat_ids:
        from observability.alerting import AlertManager, configure_alerting_from_env
        configure_alerting_from_env()
        manager = AlertManager.get_instance()
        handler = manager.handlers.get("telegram")
        if handler:
            bot_token = handler.bot_token
            chat_ids = handler.chat_ids
    
    if not bot_token or not chat_ids:
        return False
    
    message = TelegramFormatter.format(alert, stakeholder)
    
    import aiohttp
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    success = True
    for chat_id in chat_ids:
        try:
            payload = {"chat_id": chat_id, "text": message}
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        success = False
        except Exception:
            success = False
    
    return success


if __name__ == "__main__":
    test_alert = create_trade_alert(
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
    
    print("=== TRADER FORMAT ===")
    print(TelegramFormatter.format(test_alert, StakeholderGroup.TRADER))
    print()
    
    print("=== RISK MANAGER FORMAT ===")
    risk_alert = create_risk_alert(
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
    print(TelegramFormatter.format(risk_alert, StakeholderGroup.RISK_MANAGER))
    print()
    
    print("=== QUANT FORMAT ===")
    quant_alert = create_performance_alert(
        metric_name="Win Rate",
        value=0.783,
        threshold=0.75,
        is_positive=True,
        metrics={
            "win_rate": 0.783,
            "sharpe_ratio": 1.45,
            "current_pnl": 24500,
        }
    )
    print(TelegramFormatter.format(quant_alert, StakeholderGroup.QUANT))
    print()
    
    print("=== EXECUTIVE FORMAT ===")
    print(TelegramFormatter.format(test_alert, StakeholderGroup.MANAGER))
    print()
    
    print("=== DEVOPS FORMAT ===")
    sys_alert = create_system_alert(
        component="Binance WebSocket",
        status="DEGRADED",
        details={"latency": 245, "error_rate": 0.032}
    )
    print(TelegramFormatter.format(sys_alert, StakeholderGroup.DEVOPS))