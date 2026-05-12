"""
Health Check System for the Unified Trading System
Provides HTTP-based health checks for all components.
"""

import time
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json
import socket


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status for a single component"""
    name: str
    status: HealthStatus
    message: str = ""
    last_check: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class HealthCheck(ABC):
    """Base class for health checks"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the component being checked"""
        pass
    
    @abstractmethod
    def check(self) -> ComponentHealth:
        """Perform the health check"""
        pass


class PingHealthCheck(HealthCheck):
    """Check if a host/port is reachable"""
    
    def __init__(self, name: str, host: str, port: int, timeout: float = 5.0):
        self._name = name
        self.host = host
        self.port = port
        self.timeout = timeout
    
    @property
    def name(self) -> str:
        return self._name
    
    def check(self) -> ComponentHealth:
        """Check if the host is reachable"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            
            if result == 0:
                return ComponentHealth(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message=f"Connected to {self.host}:{self.port}",
                    metadata={"host": self.host, "port": self.port}
                )
            else:
                return ComponentHealth(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Cannot connect to {self.host}:{self.port}",
                    metadata={"host": self.host, "port": self.port, "error_code": result}
                )
        except Exception as e:
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                metadata={"host": self.host, "port": self.port, "error": str(e)}
            )


class LambdaHealthCheck(HealthCheck):
    """Health check with a lambda function"""
    
    def __init__(self, name: str, check_fn: Callable[[], tuple]):
        self._name = name
        self.check_fn = check_fn
    
    @property
    def name(self) -> str:
        return self._name
    
    def check(self) -> ComponentHealth:
        """Run the lambda health check"""
        try:
            status_str, message, metadata = self.check_fn()
            return ComponentHealth(
                name=self.name,
                status=HealthStatus(status_str),
                message=message,
                metadata=metadata or {}
            )
        except Exception as e:
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                metadata={"error": str(e)}
            )


class HealthCheckRegistry:
    """Registry for all health checks"""
    
    def __init__(self):
        self._checks: Dict[str, HealthCheck] = {}
        self._last_results: Dict[str, ComponentHealth] = {}
        self._check_lock = threading.Lock()
    
    def register(self, check: HealthCheck) -> None:
        """Register a health check"""
        with self._check_lock:
            self._checks[check.name] = check
    
    def unregister(self, name: str) -> None:
        """Unregister a health check"""
        with self._check_lock:
            self._checks.pop(name, None)
            self._last_results.pop(name, None)
    
    def check_all(self) -> Dict[str, ComponentHealth]:
        """Run all health checks"""
        results = {}
        with self._check_lock:
            for name, check in self._checks.items():
                results[name] = check.check()
            self._last_results = results
        return results
    
    def get_status(self) -> tuple:
        """Get overall system status"""
        results = self.check_all()
        
        # Count statuses
        healthy_count = sum(1 for h in results.values() if h.status == HealthStatus.HEALTHY)
        degraded_count = sum(1 for h in results.values() if h.status == HealthStatus.DEGRADED)
        unhealthy_count = sum(1 for h in results.values() if h.status == HealthStatus.UNHEALTHY)
        
        total = len(results)
        
        # Determine overall status
        if unhealthy_count > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED
        elif healthy_count == total:
            overall_status = HealthStatus.HEALTHY
        else:
            overall_status = HealthStatus.UNKNOWN
        
        return overall_status, results
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        overall_status, results = self.get_status()
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "components": {
                name: {
                    "status": h.status.value,
                    "message": h.message,
                    "last_check": h.last_check,
                    "metadata": h.metadata
                }
                for name, h in results.items()
            }
        }


class HealthServer:
    """HTTP server for health check endpoints"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.registry = HealthCheckRegistry()
        self._server_thread: Optional[threading.Thread] = None
        self._running = False
    
    def register_default_checks(self, config: Dict) -> None:
        """Register default health checks"""
        # Exchange connectivity checks (example)
        if config.get("exchanges", {}).get("binance", {}).get("enabled"):
            self.registry.register(PingHealthCheck(
                "exchange_binance",
                config["exchanges"]["binance"].get("host", "testnet.binance.vip"),
                config["exchanges"]["binance"].get("port", 443)
            ))
        
        if config.get("exchanges", {}).get("coinbase", {}).get("enabled"):
            self.registry.register(PingHealthCheck(
                "exchange_coinbase",
                config["exchanges"]["coinbase"].get("host", "api.exchange.coinbase.com"),
                config["exchanges"]["coinbase"].get("port", 443)
            ))
        
        # System resource checks (using lambdas)
        import psutil
        try:
            self.registry.register(LambdaHealthCheck(
                "system_memory",
                lambda: (
                    "healthy" if psutil.virtual_memory().percent < 90 else "degraded",
                    f"Memory usage: {psutil.virtual_memory().percent}%",
                    {"usage_percent": psutil.virtual_memory().percent}
                )
            ))
            
            self.registry.register(LambdaHealthCheck(
                "system_disk",
                lambda: (
                    "healthy" if psutil.disk_usage('/').percent < 90 else "degraded",
                    f"Disk usage: {psutil.disk_usage('/').percent}%",
                    {"usage_percent": psutil.disk_usage('/').percent}
                )
            ))
        except ImportError:
            # psutil not available, skip system checks
            pass
    
    def start(self) -> None:
        """Start the health check server"""
        if self._running:
            return
        
        self._running = True
        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()
    
    def _run_server(self) -> None:
        """Run the HTTP server"""
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler
            
            class HealthHandler(BaseHTTPRequestHandler):
                registry = self.registry
                
                def do_GET(self):
                    if self.path == "/health":
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(
                            self.registry.to_dict()
                        ).encode())
                    elif self.path == "/health/json":
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(
                            self.registry.to_dict()
                        ).encode())
                    else:
                        self.send_response(404)
                        self.end_headers()
                
                def log_message(self, format, *args):
                    pass  # Suppress logging
            
            server = HTTPServer(("", self.port), HealthHandler)
            print(f"Health check server started on port {self.port}")
            
            while self._running:
                server.handle_request()
                
        except Exception as e:
            print(f"Health server error: {e}")
    
    def stop(self) -> None:
        """Stop the health check server"""
        self._running = False
        if self._server_thread:
            self._running = False


# Global health server
_health_server: Optional[HealthServer] = None


def get_health_server(port: int = 8080) -> HealthServer:
    """Get or create the global health server"""
    global _health_server
    if _health_server is None:
        _health_server = HealthServer(port)
    return _health_server


def register_health_check(check: HealthCheck) -> None:
    """Register a health check with the global server"""
    get_health_server().registry.register(check)


# Example usage
if __name__ == "__main__":
    # Create health server
    server = get_health_server(8080)
    
    # Register some health checks
    server.registry.register(PingHealthCheck(
        "exchange_mock",
        "google.com",
        443
    ))
    
    server.registry.register(LambdaHealthCheck(
        "custom_check",
        lambda: ("healthy", "Custom check passed", {"value": 42})
    ))
    
    # Run health checks
    print("Running health checks...")
    status, results = server.registry.get_status()
    print(f"Overall status: {status.value}")
    
    for name, health in results.items():
        print(f"  {name}: {health.status.value} - {health.message}")
    
    # Start health server in background
    print("\nStarting health server...")
    server.start()
    
    print("Health check demonstration complete!")
    print("Endpoints available:")
    print("  - GET /health - Overall health status")
    print("  - GET /health/json - JSON health status")