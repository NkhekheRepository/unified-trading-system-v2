#!/usr/bin/env python3
"""
Monitoring Script for Unified Trading System
Provides real-time monitoring and health checks
"""


import os
import sys
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List
import signal


class UnifiedTradingSystemMonitor:
    """Monitors the unified trading system health and performance"""
    
    def __init__(self, config_path: str = None):
        self.config_path = Path(config_path) if config_path else Path(__file__).parent.parent / "config"
        self.project_root = Path(__file__).parent.parent
        self.running = False
        self.setup_logging()
        
        # Monitoring data
        self.metrics_history = []
        self.alert_history = []
        self.start_time = time.time()
        
        # Alert thresholds (would normally come from config)
        self.alert_thresholds = {
            "latency_high": 100.0,      # ms
            "error_rate_high": 10.0,    # errors/minute
            "drawdown_high": 0.05,      # 5%
            "aggression_stuck": 0.95,   # aggression stuck at high level
            "belief_entropy_high": 2.0, # high entropy = uncertainty
            "update_stalled": 30.0      # seconds without updates
        }
        
        # State tracking
        self.last_update_time = time.time()
        self.latest_metrics = {}
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(self.project_root / "monitoring.log")
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def start_monitoring(self):
        """Start the monitoring loop"""
        self.logger.info("Starting unified trading system monitor...")
        self.running = True
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        monitor_thread.start()
        
        try:
            # Main thread waits for interrupt
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, stopping monitor...")
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.running = False
        self.logger.info("Monitor stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Collect system metrics
                metrics = self._collect_metrics()
                
                # Store metrics
                self.metrics_history.append({
                    "timestamp": time.time(),
                    "metrics": metrics
                })
                
                # Keep history bounded (last 1000 entries)
                if len(self.metrics_history) > 1000:
                    self.metrics_history = self.metrics_history[-500:]
                
                # Check for alerts
                alerts = self._check_alerts(metrics)
                if alerts:
                    self._handle_alerts(alerts)
                
                # Update latest metrics
                self.latest_metrics = metrics
                self.last_update_time = time.time()
                
                # Display status (every 10 seconds)
                if int(time.time()) % 10 == 0:
                    self._display_status()
                
                # Sleep for a bit
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        metrics = {
            "timestamp": time.time(),
            "uptime_seconds": time.time() - self.start_time,
            "system_status": "unknown"
        }
        
        try:
            # Try to import and test system components
            sys.path.insert(0, str(self.project_root))
            
            # Test perception component
            from perception.belief_state import BeliefStateEstimator
            estimator = BeliefStateEstimator()
            
            # Simulate market data for testing
            test_market_data = {
                "bid_price": 50000.0,
                "ask_price": 50010.0,
                "bid_size": 1.0,
                "ask_size": 1.0,
                "last_price": 50005.0,
                "last_size": 1.0
            }
            
            belief_state = estimator.update(test_market_data)
            
            metrics["perception"] = {
                "status": "healthy",
                "belief_state": {
                    "expected_return": belief_state.expected_return,
                    "confidence": belief_state.confidence,
                    "entropy": belief_state.get_entropy(),
                    "volatility_estimate": belief_state.volatility_estimate,
                    "liquidity_estimate": belief_state.liquidity_estimate
                }
            }
            
            # Test decision component
            from decision.aggression_controller import AggressionController
            controller = AggressionController()
            
            aggression_state = controller.update(
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
                signal_strength=0.2
            )
            
            metrics["decision"] = {
                "status": "healthy",
                "aggression_state": {
                    "aggression_level": aggression_state.aggression_level,
                    "aggression_rate": aggression_state.aggression_rate,
                    "signal_strength": 0.2,
                    "risk_gradient": aggression_state.risk_gradient
                }
            }
            
            # Test execution component
            from execution.smart_order_router import ExecutionModel
            execution_model = ExecutionModel()
            
            metrics["execution"] = {
                "status": "healthy",
                "model_params": {
                    "execution_eta": execution_model.execution_eta,
                    "market_impact_factor": execution_model.market_impact_factor,
                    "latency_base": execution_model.latency_base,
                    "slippage_factor": execution_model.slippage_factor
                }
            }
            
            # Test risk component
            from risk.unified_risk_manager import RiskManifold
            risk_manager = RiskManifold()
            
            # Simple risk assessment
            risk_assessment = risk_manager.assess_risk(
                belief_state={
                    "expected_return": belief_state.expected_return,
                    "expected_return_uncertainty": belief_state.expected_return_uncertainty,
                    "aleatoric_uncertainty": belief_state.aleatoric_uncertainty,
                    "epistemic_uncertainty": belief_state.epistemic_uncertainty,
                    "regime_probabilities": belief_state.regime_probabilities,
                    "volatility_estimate": belief_state.volatility_estimate,
                    "liquidity_estimate": belief_state.liquidity_estimate,
                    "drawdown": belief_state.drawdown,
                    "entropy": belief_state.get_entropy()
                },
                portfolio_state={
                    "drawdown": 0.01,
                    "daily_pnl": 0.001,
                    "leverage_ratio": 0.2,
                    "total_value": 100000.0
                },
                market_data={
                    "volatility": belief_state.volatility_estimate,
                    "spread_bps": 2.0,
                    "liquidity": belief_state.liquidity_estimate
                }
            )
            
            metrics["risk"] = {
                "status": "healthy",
                "assessment": {
                    "risk_level": risk_assessment.risk_level.name,
                    "risk_score": risk_assessment.risk_score,
                    "protective_action": risk_assessment.protective_action
                }
            }
            
            # Test feedback component
            from feedback.monitoring_engine import FeedbackLayer
            feedback_layer = FeedbackLayer()
            
            metrics["feedback"] = {
                "status": "healthy",
                "engines": [
                    "pnl_engine",
                    "learning_insights_engine", 
                    "sre_metrics_engine",
                    "adaptation_layer"
                ]
            }
            
            # Test config component
            from config.config_manager import ConfigManager
            config_manager = ConfigManager()
            
            try:
                config = config_manager.load_config()
                metrics["config"] = {
                    "status": "healthy",
                    "loaded": True,
                    "environment": config.get("system", {}).get("environment", "unknown")
                }
            except Exception as e:
                metrics["config"] = {
                    "status": "degraded",
                    "error": str(e),
                    "loaded": False
                }
            
            metrics["system_status"] = "healthy"
            
        except ImportError as e:
            metrics["system_status"] = "degraded"
            metrics["import_error"] = str(e)
            self.logger.warning(f"Import error during monitoring: {e}")
        except Exception as e:
            metrics["system_status"] = "error"
            metrics["error"] = str(e)
            self.logger.error(f"Error collecting metrics: {e}")
        
        return metrics
    
    def _check_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check if any metrics exceed alert thresholds"""
        alerts = []
        
        if metrics.get("system_status") != "healthy":
            alerts.append({
                "type": "system_health",
                "level": "warning" if metrics.get("system_status") == "degraded" else "critical",
                "message": f"System status: {metrics.get('system_status', 'unknown')}",
                "timestamp": time.time()
            })
        
        # Check perception metrics
        perception = metrics.get("perception", {})
        if perception.get("status") == "healthy":
            belief_state = perception.get("belief_state", {})
            
            # Check belief entropy (high entropy = high uncertainty)
            entropy = belief_state.get("entropy", 0.0)
            if entropy > self.alert_thresholds["belief_entropy_high"]:
                alerts.append({
                    "type": "high_entropy",
                    "level": "warning",
                    "message": f"High belief state entropy: {entropy:.3f}",
                    "value": entropy,
                    "threshold": self.alert_thresholds["belief_entropy_high"],
                    "timestamp": time.time()
                })
            
            # Check confidence (very low confidence may indicate problems)
            confidence = belief_state.get("confidence", 1.0)
            if confidence < 0.3:
                alerts.append({
                    "type": "low_confidence",
                    "level": "warning",
                    "message": f"Low belief state confidence: {confidence:.3f}",
                    "value": confidence,
                    "threshold": 0.3,
                    "timestamp": time.time()
                })
        
        # Check decision metrics
        decision = metrics.get("decision", {})
        if decision.get("status") == "healthy":
            aggression_state = decision.get("aggression_state", {})
            
            # Check for stuck aggression (too high for too long)
            aggression_level = aggression_state.get("aggression_level", 0.0)
            if aggression_level > self.alert_thresholds["aggression_stuck"]:
                alerts.append({
                    "type": "high_aggression",
                    "level": "warning",
                    "message": f"Aggression level stuck at high value: {aggression_level:.3f}",
                    "value": aggression_level,
                    "threshold": self.alert_thresholds["aggression_stuck"],
                    "timestamp": time.time()
                })
        
        # Check risk metrics
        risk = metrics.get("risk", {})
        if risk.get("status") == "healthy":
            assessment = risk.get("assessment", {})
            
            # Check risk level
            risk_level_str = assessment.get("risk_level", "LEVEL_0_NORMAL")
            if risk_level_str in ["LEVEL_3_DANGER", "LEVEL_4_CRITICAL"]:
                alerts.append({
                    "type": "high_risk_level",
                    "level": "critical" if risk_level_str == "LEVEL_4_CRITICAL" else "warning",
                    "message": f"High risk level detected: {risk_level_str}",
                    "value": risk_level_str,
                    "threshold": "LEVEL_2_WARNING",
                    "timestamp": time.time()
                })
            
            # Check risk score
            risk_score = assessment.get("risk_score", 0.0)
            if risk_score > 0.8:
                alerts.append({
                    "type": "high_risk_score",
                    "level": "warning",
                    "message": f"High risk score: {risk_score:.3f}",
                    "value": risk_score,
                    "threshold": 0.8,
                    "timestamp": time.time()
                })
        
        # Check for update staleness
        time_since_update = time.time() - self.last_update_time
        if time_since_update > self.alert_thresholds["update_stalled"]:
            alerts.append({
                "type": "update_stalled",
                "level": "warning",
                "message": f"No updates received for {time_since_update:.1f} seconds",
                "value": time_since_update,
                "threshold": self.alert_thresholds["update_stalled"],
                "timestamp": time.time()
            })
        
        return alerts
    
    def _handle_alerts(self, alerts: List[Dict[str, Any]]):
        """Handle triggered alerts"""
        for alert in alerts:
            # Add to alert history
            self.alert_history.append(alert)
            
            # Keep alert history bounded
            if len(self.alert_history) > 100:
                self.alert_history = self.alert_history[-50:]
            
            # Log alert based on level
            if alert["level"] == "critical":
                self.logger.critical(f"ALERT: {alert['message']}")
            elif alert["level"] == "warning":
                self.logger.warning(f"ALERT: {alert['message']}")
            else:
                self.logger.info(f"ALERT: {alert['message']}")
            
            # In a real system, this would also:
            # - Send notifications (email, SMS, Slack, etc.)
            # - Trigger automated responses
            # - Update dashboard indicators
    
    def _display_status(self):
        """Display current system status"""
        os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen
        
        print("=" * 60)
        print("UNIFIED TRADING SYSTEM MONITOR")
        print("=" * 60)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Uptime: {timedelta(seconds=int(time.time() - self.start_time))}")
        print()
        
        if self.latest_metrics:
            status = self.latest_metrics.get("system_status", "unknown")
            status_color = {
                "healthy": "\033[92m",   # Green
                "degraded": "\033[93m",  # Yellow
                "error": "\033[91m",     # Red
                "unknown": "\033[90m"    # Gray
            }.get(status, "\033[0m")
            
            print(f"System Status: {status_color}{status}\033[0m")
            print()
            
            # Perception
            perception = self.latest_metrics.get("perception", {})
            if perception.get("status") == "healthy":
                bs = perception.get("belief_state", {})
                print("PERCEPTION:")
                print(f"  Expected Return: {bs.get('expected_return', 0.0):+.4f}")
                print(f"  Confidence: {bs.get('confidence', 0.0):.3f}")
                print(f"  Entropy: {bs.get('entropy', 0.0):.3f}")
                print(f"  Volatility: {bs.get('volatility_estimate', 0.0):.3f}")
                print(f"  Liquidity: {bs.get('liquidity_estimate', 0.0):.3f}")
                print()
            
            # Decision
            decision = self.latest_metrics.get("decision", {})
            if decision.get("status") == "healthy":
                ag = decision.get("aggression_state", {})
                print("DECISION:")
                print(f"  Aggression Level: {ag.get('aggression_level', 0.0):.3f}")
                print(f"  Aggression Rate: {ag.get('aggression_rate', 0.0):+.4f}")
                print(f"  Signal Strength: {ag.get('signal_strength', 0.0):.3f}")
                print(f"  Risk Gradient: {ag.get('risk_gradient', 0.0):.4f}")
                print()
            
            # Risk
            risk = self.latest_metrics.get("risk", {})
            if risk.get("status") == "healthy":
                assess = risk.get("assessment", {})
                print("RISK:")
                print(f"  Risk Level: {assess.get('risk_level', 'UNKNOWN')}")
                print(f"  Risk Score: {assess.get('risk_score', 0.0):.3f}")
                print(f"  Protective Action: {assess.get('protective_action', 'NONE')}")
                print()
            
            # Recent alerts
            recent_alerts = [a for a in self.alert_history 
                           if time.time() - a["timestamp"] < 300]  # Last 5 minutes
            if recent_alerts:
                print("RECENT ALERTS (Last 5 min):")
                for alert in recent_alerts[-5:]:  # Show last 5
                    time_ago = time.time() - alert["timestamp"]
                    level_symbol = {
                        "critical": "!!",
                        "warning": "!!",
                        "info": "--"
                    }.get(alert["level"], "??")
                    print(f"  [{time_ago:>4.0f}s ago] {level_symbol} {alert['message']}")
                if len(recent_alerts) > 5:
                    print(f"  ... and {len(recent_alerts) - 5} more")
                print()
            else:
                print("NO RECENT ALERTS")
                print()
            
            # System info
            print(f"Metrics Collected: {len(self.metrics_history)}")
            print(f"Total Alerts: {len(self.alert_history)}")
            print(f"Alerts (Last Hour): {len([a for a in self.alert_history if time.time() - a['timestamp'] < 3600])}")
        else:
            print("WAITING FOR FIRST METRICS...")
        
        print()
        print("Press Ctrl+C to stop monitoring")
        print("=" * 60)


def main():
    """Main entry point for monitoring script"""
    monitor = UnifiedTradingSystemMonitor()
    
    def signal_handler(sig, frame):
        print('\nReceived interrupt signal, stopping monitor...')
        monitor.stop_monitoring()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print('\nMonitor stopped by user')
        sys.exit(0)


if __name__ == "__main__":
    main()