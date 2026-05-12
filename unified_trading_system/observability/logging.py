"""
Structured Logging System for the Unified Trading System
Provides JSON-formatted structured logging with correlation IDs and context enrichment.
"""

import json
import logging
import sys
import uuid
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
import os


class LogLevel(Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"
    CRITICAL = "CRITICAL"


# Context variable for correlation ID
_correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


# Context variables for additional context
_context_vars: ContextVar[Dict[str, Any]] = ContextVar('context_vars', default={})


def get_correlation_id() -> str:
    """Get or create a correlation ID for the current request/operation"""
    cid = _correlation_id.get()
    if cid is None:
        cid = str(uuid.uuid4())
        _correlation_id.set(cid)
    return cid


def set_correlation_id(correlation_id: str) -> None:
    """Set a specific correlation ID for the current context"""
    _correlation_id.set(correlation_id)


def get_context() -> Dict[str, Any]:
    """Get additional context for the current context"""
    return _context_vars.get()


def set_context(**kwargs) -> None:
    """Set additional context variables"""
    current = _context_vars.get()
    current.update(kwargs)
    _context_vars.set(current)


def clear_context() -> None:
    """Clear all additional context"""
    _context_vars.set({})


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        # Build base log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add correlation ID if available
        cid = _correlation_id.get()
        if cid:
            log_entry["correlation_id"] = cid
        
        # Add context variables
        ctx = _context_vars.get()
        if ctx:
            log_entry["context"] = ctx
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if self.include_extra:
            extra_fields = {
                k: v for k, v in record.__dict__.items()
                if not k.startswith('_') and k not in ['name', 'msg', 'args', 'created', 'filename', 'funcName', 'levelname', 'levelno', 'lineno', 'module', 'msecs', 'pathname', 'process', 'processName', 'relativeCreated', 'exc_info', 'exc_text', 'stack_info', 'thread', 'threadName', 'message', 'asctime']
            }
            if extra_fields:
                log_entry["extra"] = extra_fields
        
        # Phase 6.1 (10/10 Upgrade): Add performance disclaimer for trading logs
        # CFA Standard VI: Disclosure of simulated results
        if record.name in ['trading_loop', 'trade_journal', 'risk_manager']:
            log_entry["disclaimer"] = "Performance metrics based on Testnet data. Not indicative of live trading results. Past performance does not guarantee future results."
            log_entry["data_source"] = "testnet"  # Mark data source
            log_entry["cf_a_compliance"] = {"standard_I_C": True, "standard_VI": True}
        
        return json.dumps(log_entry)


class TradingLogger:
    """Enhanced trading logger with structured output"""
    
    def __init__(self, name: str, log_dir: str = "logs"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.log_dir = log_dir
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """Set up the logger with handlers"""
        # Clear existing handlers
        self.logger.handlers.clear()
        self.logger.setLevel(logging.DEBUG)
        
        # Create log directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Console handler with structured formatter (human readable)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler with JSON formatter
        file_handler = RotatingFileHandler(
            os.path.join(self.log_dir, f"{self.name}.log"),
            maxBytes=10_000_000,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        json_formatter = StructuredFormatter()
        file_handler.setFormatter(json_formatter)
        self.logger.addHandler(file_handler)
        
        # Error file handler
        error_handler = RotatingFileHandler(
            os.path.join(self.log_dir, f"{self.name}_error.log"),
            maxBytes=5_000_000,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(json_formatter)
        self.logger.addHandler(error_handler)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with context"""
        if kwargs:
            set_context(**kwargs)
        self.logger.debug(message)
        if kwargs:
            clear_context()
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with context"""
        if kwargs:
            set_context(**kwargs)
        self.logger.info(message)
        if kwargs:
            clear_context()
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with context"""
        if kwargs:
            set_context(**kwargs)
        self.logger.warning(message)
        if kwargs:
            clear_context()
    
    def error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """Log error message with optional exception info"""
        if kwargs:
            set_context(**kwargs)
        self.logger.error(message, exc_info=exc_info)
        if kwargs:
            clear_context()
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with context"""
        if kwargs:
            set_context(**kwargs)
        self.logger.critical(message)
        if kwargs:
            clear_context()
    
    def fatal(self, message: str, exc_info: bool = True, **kwargs) -> None:
        """Log fatal/critical message"""
        if kwargs:
            set_context(**kwargs)
        self.logger.critical(message, exc_info=exc_info)
        if kwargs:
            clear_context()
    
    # Trading-specific logging methods
    def trade_execution(self, symbol: str, side: str, quantity: float, price: float, **kwargs) -> None:
        """Log trade execution"""
        self.info(
            f"TRADE | {symbol} | {side} | {quantity}@{price}",
            event="trade_execution",
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            **kwargs
        )
    
    def risk_breach(self, metric: str, value: float, threshold: float, action: str, **kwargs) -> None:
        """Log risk limit breach"""
        self.warning(
            f"RISK_BREACH | {metric}: {value} (threshold: {threshold}) | Action: {action}",
            event="risk_breach",
            metric=metric,
            value=value,
            threshold=threshold,
            action=action,
            **kwargs
        )
    
    def system_alert(self, component: str, status: str, message: str, **kwargs) -> None:
        """Log system alert"""
        self.warning(
            f"SYSTEM_ALERT | {component} | {status} | {message}",
            event="system_alert",
            component=component,
            status=status,
            message=message,
            **kwargs
        )
    
    def performance_update(self, pnl: float, win_rate: float, trades: int, **kwargs) -> None:
        """Log performance update"""
        self.info(
            f"PERFORMANCE | PnL: {pnl:.4f} | Win Rate: {win_rate:.2f}% | Trades: {trades}",
            event="performance",
            pnl=pnl,
            win_rate=win_rate,
            trades=trades,
            **kwargs
        )
    
    def strategy_change(self, old_strategy: str, new_strategy: str, reason: str, **kwargs) -> None:
        """Log strategy change"""
        self.info(
            f"STRATEGY_CHANGE | {old_strategy} -> {new_strategy} | Reason: {reason}",
            event="strategy_change",
            old_strategy=old_strategy,
            new_strategy=new_strategy,
            reason=reason,
            **kwargs
        )


# Global logger instance
_trading_logger: Optional[TradingLogger] = None


def get_logger(name: str = "trading") -> TradingLogger:
    """Get or create the global trading logger"""
    global _trading_logger
    if _trading_logger is None:
        _trading_logger = TradingLogger(name)
    return _trading_logger


# Convenience functions
def debug(message: str, **kwargs) -> None:
    get_logger().debug(message, **kwargs)


def info(message: str, **kwargs) -> None:
    get_logger().info(message, **kwargs)


def warning(message: str, **kwargs) -> None:
    get_logger().warning(message, **kwargs)


def error(message: str, exc_info: bool = False, **kwargs) -> None:
    get_logger().error(message, exc_info=exc_info, **kwargs)


def fatal(message: str, exc_info: bool = True, **kwargs) -> None:
    get_logger().fatal(message, exc_info=exc_info, **kwargs)


# Trading-specific logging
def log_trade(symbol: str, side: str, quantity: float, price: float, **kwargs) -> None:
    get_logger().trade_execution(symbol, side, quantity, price, **kwargs)


def log_risk_breach(metric: str, value: float, threshold: float, action: str, **kwargs) -> None:
    get_logger().risk_breach(metric, value, threshold, action, **kwargs)


def log_system_alert(component: str, status: str, message: str, **kwargs) -> None:
    get_logger().system_alert(component, status, message, **kwargs)


def log_performance(pnl: float, win_rate: float, trades: int, **kwargs) -> None:
    get_logger().performance_update(pnl, win_rate, trades, **kwargs)


def log_strategy_change(old_strategy: str, new_strategy: str, reason: str, **kwargs) -> None:
    get_logger().strategy_change(old_strategy, new_strategy, reason, **kwargs)


# Example usage
if __name__ == "__main__":
    logger = get_logger("test_logger")
    
    # Basic logging with correlation ID
    cid = get_correlation_id()
    print(f"Correlation ID: {cid}")
    
    # Log messages
    logger.info("Starting trading system")
    logger.warning("High latency detected", latency_ms=150)
    logger.error("Failed to connect to exchange", error="Connection timeout")
    
    # Trading-specific logging
    logger.trade_execution("BTCUSDT", "BUY", 0.5, 50000.0)
    logger.risk_breach("DRAWDOWN", 0.15, 0.10, "REDUCE_SIZE")
    logger.system_alert("EXCHANGE", "DEGRADED", "High latency")
    logger.performance_update(0.025, 65.0, 42)
    logger.strategy_change("MEAN_REVERSION", "MOMENTUM", "Performance degradation")
    
    print("Logging demonstration complete!")