"""
Metrics Collection System for the Unified Trading System
Provides Prometheus-compatible metrics collection and reporting.
"""

import time
import random
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

try:
    from prometheus_client import Counter, Gauge, Histogram, Summary, start_http_server
    PROMETEUS_AVAILABLE = True
except ImportError:
    PROMETEUS_AVAILABLE = False
    # Create mock classes if prometheus_client is not available
    class Counter:
        def __init__(self, name, description, labels=None): pass
        def labels(self, **kwargs): return self
        def inc(self, n=1): pass
    
    class Gauge:
        def __init__(self, name, description, labels=None): pass
        def labels(self, **kwargs): return self
        def inc(self, n=1): pass
        def dec(self, n=1): pass
        def set(self, value): pass
    
    class Histogram:
        def __init__(self, name, description, buckets, labels=None): pass
        def labels(self, **kwargs): return self
        def observe(self, value): pass
    
    class Summary:
        def __init__(self, name, description, labels=None): pass
        def labels(self, **kwargs): return self
        def observe(self, value): pass
    
    def start_http_server(port): pass


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


# Metric definitions
METRICS_CONFIG = {
    # Trading signals
    "signals_generated": {
        "type": MetricType.COUNTER,
        "description": "Total number of trading signals generated",
        "labels": ["symbol", "strategy"]
    },
    "signals_total": {
        "type": MetricType.COUNTER,
        "description": "Total number of trading signals"
    },
     
    # Orders
    "orders_submitted": {
        "type": MetricType.COUNTER,
        "description": "Total number of orders submitted",
        "labels": ["symbol", "side", "order_type"]
    },
    "orders_filled": {
        "type": MetricType.COUNTER,
        "description": "Total number of orders filled",
        "labels": ["symbol", "side"]
    },
    "orders_cancelled": {
        "type": MetricType.COUNTER,
        "description": "Total number of orders cancelled",
        "labels": ["symbol"]
    },
    "orders_rejected": {
        "type": MetricType.COUNTER,
        "description": "Total number of orders rejected",
        "labels": ["symbol", "reason"]
    },
     
    # Positions
    "position_size": {
        "type": MetricType.GAUGE,
        "description": "Current position size",
        "labels": ["symbol"]
    },
    "position_value": {
        "type": MetricType.GAUGE,
        "description": "Current position value in quote currency",
        "labels": ["symbol"]
    },
     
    # P&L
    "pnl_unrealized": {
        "type": MetricType.GAUGE,
        "description": "Unrealized P&L",
        "labels": ["symbol"]
    },
    "pnl_realized": {
        "type": MetricType.GAUGE,
        "description": "Realized P&L",
        "labels": ["symbol"]
    },
    "pnl_daily": {
        "type": MetricType.GAUGE,
        "description": "Daily P&L",
        "labels": []
    },
     
    # Risk metrics
    "risk_var": {
        "type": MetricType.GAUGE,
        "description": "Value at Risk (VaR)",
        "labels": []
    },
    "risk_drawdown": {
        "type": MetricType.GAUGE,
        "description": "Current drawdown",
        "labels": []
    },
    "risk_leverage": {
        "type": MetricType.GAUGE,
        "description": "Current leverage ratio",
        "labels": []
    },
    "risk_concentration": {
        "type": MetricType.GAUGE,
        "description": "Position concentration risk",
        "labels": []
    },
     
    # Latency metrics
    "latency_market_data": {
        "type": MetricType.HISTOGRAM,
        "description": "Market data latency",
        "labels": []
    },
    "latency_signal_generation": {
        "type": MetricType.HISTOGRAM,
        "description": "Signal generation latency",
        "labels": []
    },
    "latency_order_submission": {
        "type": MetricType.HISTOGRAM,
        "description": "Order submission latency",
        "labels": []
    },
     
    # System metrics
    "system_uptime": {
        "type": MetricType.GAUGE,
        "description": "System uptime in seconds",
        "labels": []
    },
    "system_memory_usage": {
        "type": MetricType.GAUGE,
        "description": "Memory usage percentage",
        "labels": []
    },
    "system_cpu_usage": {
        "type": MetricType.GAUGE,
        "description": "CPU usage percentage",
        "labels": []
    },
     
    # Error metrics
    "errors_total": {
        "type": MetricType.COUNTER,
        "description": "Total number of errors",
        "labels": ["component", "error_type"]
    },
     
    # Trading activity
    "trades_daily": {
        "type": MetricType.COUNTER,
        "description": "Number of trades per day",
        "labels": []
    },
    "trades_win": {
        "type": MetricType.COUNTER,
        "description": "Number of winning trades",
        "labels": []
    },
    "trades_loss": {
        "type": MetricType.COUNTER,
        "description": "Number of losing trades",
        "labels": []
    },
     
    # Strategy metrics
    "strategy_confidence": {
        "type": MetricType.GAUGE,
        "description": "Current strategy confidence",
        "labels": ["strategy"]
    },
    "strategy_equity_curve": {
        "type": MetricType.GAUGE,
        "description": "Strategy equity curve value",
        "labels": ["strategy"]
    },
}


class MetricsCollector:
    """Metrics collector with Prometheus integration"""
    
    def __init__(self, port: int = 9090):
        self.port = port
        self._metrics: Dict = {}
        self._start_time = time.time()
        self._initialize_metrics()
    
    def _initialize_metrics(self) -> None:
        """Initialize all configured metrics"""
        if not PROMETEUS_AVAILABLE:
            print("Warning: prometheus_client not available. Metrics will be mocked.")
        
        for name, config in METRICS_CONFIG.items():
            metric_type = config["type"]
            description = config["description"]
            labels = config.get("labels", [])
            
            if metric_type == MetricType.COUNTER:
                if labels:
                    self._metrics[name] = Counter(
                        f"trading_{name}",
                        description,
                        labels
                    )
                else:
                    self._metrics[name] = Counter(
                        f"trading_{name}",
                        description
                    )
            elif metric_type == MetricType.GAUGE:
                if labels:
                    self._metrics[name] = Gauge(
                        f"trading_{name}",
                        description,
                        labels
                    )
                else:
                    self._metrics[name] = Gauge(
                        f"trading_{name}",
                        description
                    )
            elif metric_type == MetricType.HISTOGRAM:
                buckets = config.get("buckets", [0.1, 0.5, 1.0, 5.0, 10.0])
                if labels:
                    self._metrics[name] = Histogram(
                        f"trading_{name}",
                        description,
                        labels,
                        buckets=buckets
                    )
                else:
                    self._metrics[name] = Histogram(
                        f"trading_{name}",
                        description,
                        buckets=buckets
                    )
            elif metric_type == MetricType.SUMMARY:
                self._metrics[name] = Summary(
                    f"trading_{name}",
                    description,
                    labels if labels else None
                )
    
    def start_server(self) -> None:
        """Start the Prometheus metrics HTTP server"""
        if PROMETEUS_AVAILABLE:
            try:
                start_http_server(self.port)
                print(f"Metrics server started on port {self.port}")
            except Exception as e:
                print(f"Failed to start metrics server: {e}")
        else:
            print("Prometheus client not available. Metrics server not started.")
    
    def increment_counter(self, name: str, n: int = 1, **labels) -> None:
        """Increment a counter metric"""
        self._metrics[name].inc(n, **labels)


def increment_counter(name: str, n: int = 1, **labels) -> None:
    """Increment a counter metric"""
    def increment_counter(self, name: str, n: int = 1, **labels) -> None:
        """Increment a counter metric"""
        self._metrics[name].labels(**labels).inc(n)

def increment_counter(name: str, n: int = 1, **labels) -> None:
    """Increment a counter metric"""
    get_metrics()._metrics[name].labels(**labels).inc(n)

def set_gauge(name: str, value: float, **labels) -> None:
    """Set a gauge metric"""
    get_metrics()._metrics[name].labels(**labels).set(value)

def observe_histogram(name: str, value: float, **labels) -> None:
    """Observe a histogram metric"""
    get_metrics()._metrics[name].labels(**labels).observe(value)

def record_trade(symbol: str, side: str, quantity: float, price: float, pnl: float = 0) -> None:
    metrics = get_metrics()
    metrics._metrics["trades_daily"].inc(labels={"side": side})
    metrics._metrics["pnl_realized"].inc(amount=pnl, labels={"symbol": symbol}) if pnl != 0 else None
    metrics._metrics["position_size"].labels(symbol=symbol).set(quantity)
    metrics._metrics["position_value"].labels(symbol=symbol).set(quantity * price)


def record_signal(symbol: str, strategy: str, direction: int) -> None:
    metrics = get_metrics()
    metrics._metrics["signals_generated"].inc(labels={"symbol": symbol, "strategy": strategy})
    metrics._metrics["signals_total"].inc()


def record_latency(name: str, latency_seconds: float) -> None:
    metrics = get_metrics()
    if name in metrics._metrics:
        metrics._metrics[name].observe(latency_seconds)


def record_error(component: str, error_type: str) -> None:
    metrics = get_metrics()
    metrics._metrics["errors_total"].inc(labels={"component": component, "error_type": error_type})


def update_position(symbol: str, size: float, value: float, pnl: float) -> None:
    metrics = get_metrics()
    metrics._metrics["position_size"].labels(symbol=symbol).set(size)
    metrics._metrics["position_value"].labels(symbol=symbol).set(value)
    metrics._metrics["pnl_unrealized"].labels(symbol=symbol).set(pnl)


def update_risk(var: float, drawdown: float, leverage: float, concentration: float) -> None:
    metrics = get_metrics()
    metrics._metrics["risk_var"].set(var)
    metrics._metrics["risk_drawdown"].set(drawdown)
    metrics._metrics["risk_leverage"].set(leverage)
    metrics._metrics["risk_concentration"].set(concentration)


# Global metrics collector instance
_metrics_collector = None


def get_metrics(port: int = 9090) -> MetricsCollector:
    """Get or create the global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(port)
    return _metrics_collector


# Example usage
if __name__ == "__main__":
    # Create metrics collector
    metrics = get_metrics(9090)
    
    # Start metrics server (optional)
    # metrics.start_server()
    
    # Record some example metrics
    print("Recording example metrics...")
    
    # Trading metrics
    record_signal("BTCUSDT", "MOMENTUM", 1)
    record_trade("BTCUSDT", "BUY", 0.5, 50000.0, 250.0)
    record_latency("latencyarket_data", 0.015)  # 15ms
    record_latency("latency_signal_generation", 0.005)  # 5ms
    
    # Position metrics
    update_position("BTCUSDT", 0.5, 25000.0, 1500.0)
    
    # Risk metrics
    update_risk(0.025, 0.03, 0.35, 0.15)
    
    # Error
    record_error("perception", "timeout")
    
    # Update uptime
    metrics.update_uptime()
    
    print("Metrics demonstration complete!")
    print(f"Metrics available at http://localhost:{metrics.port}/metrics (when started)")