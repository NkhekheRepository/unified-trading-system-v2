"""
Alerting System for the Unified Trading System
Provides Telegram integration and multi-channel alerting with rate limiting.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import threading
import queue


class AlertSeverity(Enum):
    """Alert severity levels"""
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4
    CRITICAL = 5


class AlertChannel(Enum):
    """Available alert channels"""
    TELEGRAM = "telegram"
    EMAIL = "email"
    SLACK = "slack"
    LOG = "log"
    WEBHOOK = "webhook"


@dataclass
class Alert:
    """Represents an alert"""
    title: str
    message: str
    severity: AlertSeverity = AlertSeverity.INFO
    channel: AlertChannel = AlertChannel.TELEGRAM
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None


class AlertRateLimiter:
    """Rate limiter for alerts to prevent spam"""
    
    def __init__(self, max_per_minute: int = 10, max_per_hour: int = 100):
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self.minute_counts: Dict[str, List[float]] = defaultdict(list)
        self.hour_counts: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def is_allowed(self, alert_key: str) -> bool:
        """Check if an alert is allowed based on rate limits"""
        with self._lock:
            now = time.time()
            self._cleanup_old_counts(now)
            
            minute_count = len(self.minute_counts[alert_key])
            hour_count = len(self.hour_counts[alert_key])
            
            if minute_count >= self.max_per_minute:
                return False
            if hour_count >= self.max_per_hour:
                return False
            
            self.minute_counts[alert_key].append(now)
            self.hour_counts[alert_key].append(now)
            return True
    
    def _cleanup_old_counts(self, now: float):
        """Remove old entries from rate limit counters"""
        minute_ago = now - 60
        hour_ago = now - 3600
        
        for key in list(self.minute_counts.keys()):
            self.minute_counts[key] = [t for t in self.minute_counts[key] if t > minute_ago]
            if not self.minute_counts[key]:
                del self.minute_counts[key]
        
        for key in list(self.hour_counts.keys()):
            self.hour_counts[key] = [t for t in self.hour_counts[key] if t > hour_ago]
            if not self.hour_counts[key]:
                del self.hour_counts[key]


class TelegramAlertHandler:
    """Telegram bot alert handler"""
    
    def __init__(self, bot_token: str, chat_ids: List[str], parse_mode: str = None):
        self.bot_token = bot_token
        self.chat_ids = chat_ids
        self.parse_mode = parse_mode
        self._logger = logging.getLogger(__name__)
        self._lock = threading.Lock()
    
    async def send_alert(self, alert: Alert, reply_markup: Optional[Dict] = None) -> bool:
        """Send alert to Telegram"""
        if not self.bot_token or not self.chat_ids:
            self._logger.warning("Telegram not configured - missing bot_token or chat_ids")
            return False
        
        emoji = self._get_severity_emoji(alert.severity)
        formatted_message = self._format_message(alert, emoji)
        
        success = True
        for chat_id in self.chat_ids:
            try:
                await self._send_message(chat_id, formatted_message, reply_markup=reply_markup)
            except Exception as e:
                self._logger.error(f"Failed to send Telegram alert to {chat_id}: {e}")
                success = False
        
        return success
    
    def _get_severity_emoji(self, severity: AlertSeverity) -> str:
        """Get emoji for severity level"""
        mapping = {
            AlertSeverity.DEBUG: "🔍",
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.ERROR: "❌",
            AlertSeverity.CRITICAL: "🚨",
        }
        return mapping.get(severity, "ℹ️")
    
    def _format_message(self, alert: Alert, emoji: str) -> str:
        """Format alert message for Telegram using HTML"""
        # Use HTML formatting for a more professional look
        title = f"<b>{emoji} {alert.title}</b>"
        
        # Contextual Intelligence: Extract key metrics from metadata
        # This transforms a raw message into a structured intelligence report
        context_lines = []
        if alert.metadata:
            # Priority metrics for Quant/Hedge Fund managers
            metrics = {
                'symbol': 'Ticker',
                'confidence': 'Confidence',
                'expected_return': 'Exp Return',
                'regime': 'Regime',
                'epistemic_uncertainty': 'Epistemic Unc',
                'aleatoric_uncertainty': 'Aleatoric Unc',
                'side': 'Direction',
                'quantity': 'Size'
            }
            for key, display_name in metrics.items():
                if key in alert.metadata:
                    val = alert.metadata[key]
                    if isinstance(val, float):
                        val = f"{val:.4f}"
                    context_lines.append(f"<code>{display_name}: {val}</code>")
            
            # Add any other metadata not in priority list
            for key, value in alert.metadata.items():
                if key not in metrics:
                    context_lines.append(f"<code>{key}: {value}</code>")

        # Build the final message layout
        lines = [
            title,
            "",
            f"<i>{alert.message}</i>",
            ""
        ]
        
        if context_lines:
            lines.append("<b>📊 Intelligence:</b>")
            lines.append("\n".join(context_lines))
            lines.append("")
        
        lines.append(f"🕒 <code>{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</code>")
        
        if alert.severity in (AlertSeverity.ERROR, AlertSeverity.CRITICAL):
            lines.insert(1, f"<b>⚠️ SEVERITY: {alert.severity.name}</b>")
        
        if alert.correlation_id:
            lines.append(f"🆔 <code>{alert.correlation_id}</code>")
        
        return "\n".join(lines)
    
    async def _send_message(self, chat_id: str, text: str, reply_markup: Optional[Dict] = None):
        """Send message via Telegram API with optional buttons"""
        import aiohttp
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"  # Forced HTML for rich formatting
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    data = await resp.json()
                    raise Exception(f"Telegram API error: {data}")


class LogAlertHandler:
    """Log-based alert handler"""
    
    def __init__(self, logger_name: str = "trading.alerts", level: int = logging.WARNING):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(level)
    
    async def send_alert(self, alert: Alert):
        """Send alert to log"""
        log_level = {
            AlertSeverity.DEBUG: logging.DEBUG,
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL,
        }.get(alert.severity, logging.INFO)
        
        self.logger.log(
            log_level,
            f"[{alert.severity.name}] {alert.title}: {alert.message}",
            extra={"alert_metadata": alert.metadata},
        )


class AlertManager:
    """Central alert management system"""
    
    _instance: Optional['AlertManager'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        self.handlers: Dict[AlertChannel, Any] = {}
        self.rate_limiter = AlertRateLimiter()
        self.alert_queue: queue.Queue = queue.Queue()
        self._logger = logging.getLogger(__name__)
        self._running = False
        self._filters: List[Callable[[Alert], bool]] = []
    
    @classmethod
    def get_instance(cls) -> 'AlertManager':
        """Get singleton instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def configure_telegram(self, bot_token: str, chat_ids: List[str]):
        """Configure Telegram handler"""
        self.handlers[AlertChannel.TELEGRAM] = TelegramAlertHandler(bot_token, chat_ids)
    
    def configure_log(self, logger_name: str = "trading.alerts"):
        """Configure log handler"""
        self.handlers[AlertChannel.LOG] = LogAlertHandler(logger_name)
    
    def add_filter(self, filter_func: Callable[[Alert], bool]):
        """Add an alert filter"""
        self._filters.append(filter_func)
    
    async def send_alert(self, alert: Alert, reply_markup: Optional[Dict] = None) -> bool:
        """Send an alert through configured channels with priority routing"""
        for f in self._filters:
            if not f(alert):
                return False
        
        # Priority Routing: Critical alerts bypass rate limiting and are prioritized
        alert_key = f"{alert.channel.value}:{alert.title}"
        if alert.severity not in (AlertSeverity.CRITICAL, AlertSeverity.ERROR):
            if not self.rate_limiter.is_allowed(alert_key):
                self._logger.debug(f"Alert rate limited: {alert.title}")
                return False
        
        channel = alert.channel
        handler = self.handlers.get(channel)
        
        if handler is None:
            self._logger.warning(f"No handler configured for channel: {channel}")
            return False
        
        try:
            # Pass reply_markup to the handler if supported (e.g., Telegram)
            if hasattr(handler, 'send_alert') and channel == AlertChannel.TELEGRAM:
                await handler.send_alert(alert, reply_markup=reply_markup)
            else:
                await handler.send_alert(alert)
            return True
        except Exception as e:
            self._logger.error(f"Failed to send alert: {e}")
            return False
    
    def send_alert_sync(self, alert: Alert, reply_markup: Optional[Dict] = None):
        """Synchronous wrapper for sending alerts"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.send_alert(alert, reply_markup=reply_markup))
            else:
                loop.run_until_complete(self.send_alert(alert, reply_markup=reply_markup))
        except RuntimeError:
            asyncio.run(self.send_alert(alert, reply_markup=reply_markup))


def create_trading_alert(
    title: str,
    message: str,
    severity: AlertSeverity = AlertSeverity.INFO,
    metadata: Optional[Dict[str, Any]] = None,
) -> Alert:
    """Helper to create trading alerts"""
    from .logging import get_correlation_id, get_context
    
    return Alert(
        title=title,
        message=message,
        severity=severity,
        metadata=metadata or {},
        correlation_id=get_correlation_id(),
    )


async def send_trade_execution_alert(
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    success: bool,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Send trade execution alert"""
    alert_manager = AlertManager.get_instance()
    
    status = "✅ Executed" if success else "❌ Failed"
    severity = AlertSeverity.INFO if success else AlertSeverity.ERROR
    
    # Merge provided metadata with default metadata
    alert_metadata = {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": price,
        "success": success,
    }
    if metadata:
        alert_metadata.update(metadata)
    
    alert = create_trading_alert(
        title=f"Trade {status}: {symbol}",
        message=f"{side} {quantity} {symbol} @ {price}" + (f"\nError: {error}" if error else ""),
        severity=severity,
        metadata=alert_metadata,
    )
    
    await alert_manager.send_alert(alert)


async def send_risk_alert(
    message: str,
    violation_type: str,
    details: Dict[str, Any],
):
    """Send risk management alert"""
    alert_manager = AlertManager.get_instance()
    
    alert = create_trading_alert(
        title=f"🚨 Risk Alert: {violation_type}",
        message=message,
        severity=AlertSeverity.CRITICAL,
        metadata=details,
    )
    alert.channel = AlertChannel.TELEGRAM
    
    await alert_manager.send_alert(alert)


async def send_system_status_alert(
    component: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
):
    """Send system status change alert"""
    alert_manager = AlertManager.get_instance()
    
    emoji = "🟢" if status == "healthy" else "🔴"
    
    alert = create_trading_alert(
        title=f"{emoji} System: {component} - {status.upper()}",
        message=f"Component '{component}' is now {status}",
        severity=AlertSeverity.WARNING if status != "healthy" else AlertSeverity.INFO,
        metadata=details or {},
    )
    
    await alert_manager.send_alert(alert)


def configure_alerting_from_env():
    """Configure alerting from environment variables"""
    from dotenv import load_dotenv
    import os
    
    # Find the .env file in the same directory as this file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, '..', '.env')
    load_dotenv(env_path)
    
    alert_manager = AlertManager.get_instance()
    
    # Force clear handlers to ensure fresh configuration
    alert_manager.handlers.clear()
    
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chats = os.getenv("TELEGRAM_CHAT_IDS", "").split(",")
    telegram_chats = [c.strip() for c in telegram_chats if c.strip()]
    
    logger = logging.getLogger(__name__)
    logger.info(f"Configuring Telegram - token present: {bool(telegram_token)}, chat IDs: {telegram_chats}")
    
    # Clear ALL handlers first to ensure fresh state
    for k in list(alert_manager.handlers.keys()):
        logger.debug(f"Removing handler: {k}")
        del alert_manager.handlers[k]
    
    if telegram_token and telegram_chats:
        alert_manager.configure_telegram(telegram_token, telegram_chats)
        logger.info(f"✅ AFTER configure_telegram - TELEGRAM in handlers: {AlertChannel.TELEGRAM in alert_manager.handlers}")
    
    alert_manager.configure_log()
    logger.info(f"✅ Final handlers: {list(alert_manager.handlers.keys())}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    configure_alerting_from_env()
    
    async def test_alerts():
        manager = AlertManager.get_instance()
        
        await manager.send_alert(create_trading_alert(
            title="Test Alert",
            message="This is a test alert from the trading system",
            severity=AlertSeverity.INFO,
        ))
        
        await send_trade_execution_alert(
            symbol="BTC/USDT",
            side="BUY",
            quantity=0.1,
            price=50000.0,
            success=True,
        )
    
    asyncio.run(test_alerts())
