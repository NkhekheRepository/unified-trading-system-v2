"""
Unified Feedback Layer for Integrated Trading System
Combines LVR's 8 monitoring engines with Autonomous System's validation and learning systems
"""


import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import time
import json


class MetricType(Enum):
    """Types of metrics tracked"""
    PNL = "PNL"
    LEARNING_INSIGHTS = "LEARNING_INSIGHTS"
    SRE_METRICS = "SRE_METRICS"
    PREDICTIVE = "PREDICTIVE"
    VAR = "VAR"
    FACTOR_ATTRIBUTION = "FACTOR_ATTRIBUTION"
    STRATEGY_OPTIMIZER = "STRATEGY_OPTIMIZER"
    CORRELATION_MONITOR = "CORRELATION_MONITOR"
    VALIDATION_METRICS = "VALIDATION_METRICS"
    DRIFT_DETECTION = "DRIFT_DETECTION"


@dataclass
class UnifiedMetric:
    """Unified metric structure"""
    metric_type: MetricType
    name: str
    value: float
    timestamp: int  # nanoseconds since epoch
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PNLEngine:
    """
    Unified P&L Engine combining:
    1. LVR's real-time P&L tracking with mark-to-market
    2. Autonomous System's performance metrics
    3. Advanced risk-adjusted performance measures
    """
    
    def __init__(self):
        self.trade_history = []
        self.position_history = []
        self.pnl_history = []
        self.high_water_mark = 0.0
        self.max_drawdown = 0.0
        
    def update(
        self,
        trade_result: Dict,
        current_positions: Dict,
        market_prices: Dict
    ) -> UnifiedMetric:
        """
        Update P&L calculations
        
        Args:
            trade_result: Result of latest trade
            current_positions: Current portfolio positions
            market_prices: Current market prices for mark-to-market
            
        Returns:
            P&L metric
        """
        # Record trade
        if trade_result.get("filled_quantity", 0) > 0:
            self.trade_history.append({
                "timestamp": trade_result.get("timestamp", int(time.time() * 1e9)),
                "symbol": trade_result.get("symbol", ""),
                "side": trade_result.get("side", ""),
                "quantity": trade_result.get("filled_quantity", 0),
                "price": trade_result.get("average_price", 0.0),
                "commission": trade_result.get("commission", 0.0)
            })
        
        # Calculate realized P&L from trades
        realized_pnl = self._calculate_realized_pnl()
        
        # Calculate unrealized P&L from positions
        unrealized_pnl = self._calculate_unrealized_pnl(current_positions, market_prices)
        
        # Total P&L
        total_pnl = realized_pnl + unrealized_pnl
        
        # Update high water mark and drawdown
        self.high_water_mark = max(self.high_water_mark, total_pnl)
        current_drawdown = self.high_water_mark - total_pnl
        self.max_drawdown = max(self.max_drawdown, current_drawdown)
        
        # Calculate performance metrics
        sharpe_ratio = self._calculate_sharpe_ratio()
        sortino_ratio = self._calculate_sortino_ratio()
        calmar_ratio = self._calculate_calmar_ratio()
        
        # Record in history
        self.pnl_history.append({
            "timestamp": int(time.time() * 1e9),
            "total_pnl": total_pnl,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "drawdown": current_drawdown
        })
        
        # Keep history bounded
        if len(self.pnl_history) > 10000:
            self.pnl_history = self.pnl_history[-5000:]
        
        # Create unified metric
        return UnifiedMetric(
            metric_type=MetricType.PNL,
            name="total_pnl",
            value=total_pnl,
            timestamp=int(time.time() * 1e9),
            tags={},
            metadata={
                "realized_pnl": realized_pnl,
                "unrealized_pnl": unrealized_pnl,
                "drawdown": current_drawdown,
                "max_drawdown": self.max_drawdown,
                "sharpe_ratio": sharpe_ratio,
                "sortino_ratio": sortino_ratio,
                "calmar_ratio": calmar_ratio,
                "trade_count": len(self.trade_history)
            }
        )
    
    def _calculate_realized_pnl(self) -> float:
        """Calculate realized P&L from completed trades"""
        # Simplified: sum of (sell_price - buy_price) * quantity for round trips
        # In practice, would use proper FIFO/LIFO accounting
        return sum([
            trade.get("pnl", 0.0) 
            for trade in self.trade_history 
            if "pnl" in trade
        ])
    
    def _calculate_unrealized_pnl(
        self, 
        positions: Dict, 
        market_prices: Dict
    ) -> float:
        """Calculate unrealized P&L from current positions"""
        unrealized_pnl = 0.0
        
        for symbol, position in positions.items():
            if symbol in market_prices:
                # Simplified: assumes position dict has quantity and avg_price
                quantity = position.get("quantity", 0.0)
                avg_price = position.get("avg_price", 0.0)
                market_price = market_prices[symbol]
                
                if quantity != 0 and avg_price > 0:
                    unrealized_pnl += quantity * (market_price - avg_price)
        
        return unrealized_pnl
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio from P&L history"""
        if len(self.pnl_history) < 2:
            return 0.0
        
        # Extract P&L changes (returns)
        pnl_values = [entry["total_pnl"] for entry in self.pnl_history]
        returns = np.diff(pnl_values)
        
        if len(returns) < 2:
            return 0.0
        
        # Annualize assuming daily data (would adjust based on actual frequency)
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return > 0:
            # Assuming 252 trading days per year
            sharpe = np.sqrt(252) * mean_return / std_return
        else:
            sharpe = 0.0
            
        return sharpe
    
    def _calculate_sortino_ratio(self) -> float:
        """Calculate Sortino ratio (downside deviation)"""
        if len(self.pnl_history) < 2:
            return 0.0
        
        pnl_values = [entry["total_pnl"] for entry in self.pnl_history]
        returns = np.diff(pnl_values)
        
        if len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        downside_returns = [r for r in returns if r < mean_return]
        
        if len(downside_returns) > 0:
            downside_deviation = np.std(downside_returns)
            if downside_deviation > 0:
                # Assuming 252 trading days per year
                sortino = np.sqrt(252) * mean_return / downside_deviation
            else:
                sortino = 0.0
        else:
            sortino = 0.0
            
        return sortino
    
    def _calculate_calmar_ratio(self) -> float:
        """Calculate Calmar ratio (annual return / max drawdown)"""
        if self.max_drawdown == 0:
            return 0.0
        
        # Annualized return (simplified)
        if len(self.pnl_history) < 2:
            annual_return = 0.0
        else:
            # Simple approximation: (final - initial) / time period
            initial_pnl = self.pnl_history[0]["total_pnl"]
            final_pnl = self.pnl_history[-1]["total_pnl"]
            # Would need actual time period for proper annualization
            total_return = final_pnl - initial_pnl
            annual_return = total_return * 252 / len(self.pnl_history)  # Rough approximation
        
        if self.max_drawdown > 0:
            calmar = annual_return / self.max_drawdown
        else:
            calmar = 0.0
            
        return calmar


class LearningInsightsEngine:
    """
    Unified Learning Insights Engine combining:
    1. LVR's pattern detection and performance attribution
    2. Autonomous System's offline RL insights
    3. Feature importance and model diagnostics
    """
    
    def __init__(self):
        self.feature_history = []
        self.performance_attribution = {}
        self.patterns_detected = []
        
    def update(
        self,
        belief_state: Dict,
        execution_result: Dict,
        market_data: Dict,
        model_info: Dict = None
    ) -> UnifiedMetric:
        """
        Update learning insights
        
        Args:
            belief_state: Current belief state
            execution_result: Latest execution result
            market_data: Current market data
            model_info: Information about current model/learning system
            
        Returns:
            Learning insights metric
        """
        # Record feature importance if available
        if model_info and "feature_importance" in model_info:
            self.feature_history.append({
                "timestamp": int(time.time() * 1e9),
                "features": model_info["feature_importance"]
            })
        
        # Update performance attribution
        self._update_performance_attribution(execution_result, market_data)
        
        # Detect patterns
        new_patterns = self._detect_patterns(
            belief_state, 
            execution_result, 
            market_data
        )
        self.patterns_detected.extend(new_patterns)
        
        # Calculate insight score (combined measure of learning value)
        insight_score = self._calculate_insight_score()
        
        # Keep history bounded
        if len(self.feature_history) > 1000:
            self.feature_history = self.feature_history[-500:]
        if len(self.patterns_detected) > 100:
            self.patterns_detected = self.patterns_detected[-50:]
        
        # Create unified metric
        return UnifiedMetric(
            metric_type=MetricType.LEARNING_INSIGHTS,
            name="insight_score",
            value=insight_score,
            timestamp=int(time.time() * 1e9),
            tags={},
            metadata={
                "feature_count": len(self.feature_history[-1]["features"]) if self.feature_history else 0,
                "patterns_detected": len(self.patterns_detected),
                "attribution_sources": len(self.performance_attribution),
                "model_version": model_info.get("model_version", "unknown") if model_info else "unknown"
            }
        )
    
    def _update_performance_attribution(
        self, 
        execution_result: Dict, 
        market_data: Dict
    ):
        """Update performance attribution analysis"""
        # Simplified attribution: categorize P&L sources
        # In practice, would use more sophisticated factor models
        
        pnl = execution_result.get("pnl", 0.0)
        slippage = execution_result.get("slippage", 0.0)
        latency = execution_result.get("latency", 0)
        
        # Attribute to different sources
        if abs(pnl) > 0.01:  # Significant P&L
            # Determine if due to signal, execution, or market
            signal_strength = market_data.get("signal_strength", 0.0)
            if abs(signal_strength) > 0.3:
                self.performance_attribution["signal"] = self.performance_attribution.get("signal", 0.0) + pnl
            else:
                self.performance_attribution["market"] = self.performance_attribution.get("market", 0.0) + pnl
        
        if abs(slippage) > 0.1:  # Significant slippage
            self.performance_attribution["execution"] = self.performance_attribution.get("execution", 0.0) - abs(slippage)
        
        # Time-based attributes
        if latency > 10:  # High latency
            self.performance_attribution["latency_cost"] = self.performance_attribution.get("latency_cost", 0.0) - latency * 0.001
    
    def _detect_patterns(
        self,
        belief_state: Dict,
        execution_result: Dict,
        market_data: Dict
    ) -> List[Dict]:
        """Detect patterns in trading behavior"""
        patterns = []
        
        # Pattern 1: Signal persistence
        if "signal_history" in belief_state:
            # Would check for persistent signal directions
            pass
        
        # Pattern 2: Time-of-day effects
        # Would check for intraday patterns
        
        # Pattern 3: Regime-dependent performance
        regime_prob = belief_state.get("regime_probabilities", [])
        if len(regime_prob) > 0:
            dominant_regime = np.argmax(regime_prob)
            regime_confidence = regime_prob[dominant_regime]
            if regime_confidence > 0.7:
                patterns.append({
                    "type": "dominant_regime",
                    "regime": int(dominant_regime),
                    "confidence": regime_confidence,
                    "timestamp": int(time.time() * 1e9)
                })
        
        return patterns
    
    def _calculate_insight_score(self) -> float:
        """Calculate overall insight score"""
        # Combine multiple factors:
        # 1. Feature diversity (more features = more insights)
        # 2. Pattern detection rate
        # 3. Attribution clarity
        
        feature_score = 0.0
        if self.feature_history:
            latest_features = self.feature_history[-1].get("features", {})
            feature_score = min(len(latest_features) / 10.0, 1.0)  # Normalize to max 10 features
        
        pattern_score = min(len(self.patterns_detected) / 20.0, 1.0)  # Normalize to max 20 patterns
        
        # Attribution score: how well we can attribute performance
        attributed_pnl = sum(abs(v) for v in self.performance_attribution.values())
        total_pnl = sum(abs(v) for v in self.performance_attribution.values()) + 0.001  # Avoid division by zero
        attribution_score = min(attributed_pnl / total_pnl, 1.0) if total_pnl > 0 else 0.0
        
        insight_score = (
            0.4 * feature_score +
            0.3 * pattern_score +
            0.3 * attribution_score
        )
        
        return insight_score


class SREMetricsEngine:
    """
    Unified SRE (Site Reliability Engineering) Metrics Engine
    Combines LVR's monitoring with Autonomous System's SRE metrics
    """
    
    def __init__(self):
        self.latency_history = []
        self.error_history = []
        self.uptime_history = []
        self.start_time = time.time()
        
    def update(
        self,
        component_latencies: Dict[str, float],
        error_events: List[Dict],
        system_health: Dict[str, bool]
    ) -> UnifiedMetric:
        """
        Update SRE metrics
        
        Args:
            component_latencies: Latency measurements for each component
            error_events: Recent error events
            system_health: Health status of each component
            
        Returns:
            SRE metrics
        """
        # Record latencies
        timestamp = int(time.time() * 1e9)
        for component, latency in component_latencies.items():
            self.latency_history.append({
                "timestamp": timestamp,
                "component": component,
                "latency_ms": latency
            })
        
        # Record errors
        for error in error_events:
            self.error_history.append({
                "timestamp": timestamp,
                "component": error.get("component", "unknown"),
                "error_type": error.get("error_type", "unknown"),
                "severity": error.get("severity", "low")
            })
        
        # Calculate system uptime
        current_uptime = time.time() - self.start_time
        self.uptime_history.append({
            "timestamp": timestamp,
            "uptime_seconds": current_uptime
        })
        
        # Calculate metrics
        avg_latency = self._calculate_average_latency()
        p95_latency = self._calculate_percentile_latency(95)
        p99_latency = self._calculate_percentile_latency(99)
        error_rate = self._calculate_error_rate()
        uptime_percentage = self._calculate_uptime_percentage()
        
        # Keep history bounded
        cutoff_time = time.time() - 3600  # Keep last hour
        self.latency_history = [
            x for x in self.latency_history 
            if x["timestamp"] > cutoff_time * 1e9
        ]
        self.error_history = [
            x for x in self.error_history 
            if x["timestamp"] > cutoff_time * 1e9
        ]
        self.uptime_history = [
            x for x in self.uptime_history 
            if x["timestamp"] > cutoff_time * 1e9
        ]
        
        # Create unified metric (using 95th percentile latency as primary metric)
        return UnifiedMetric(
            metric_type=MetricType.SRE_METRICS,
            name="p95_latency_ms",
            value=p95_latency,
            timestamp=int(time.time() * 1e9),
            tags={},
            metadata={
                "avg_latency_ms": avg_latency,
                "p95_latency_ms": p95_latency,
                "p99_latency_ms": p99_latency,
                "error_rate": error_rate,
                "uptime_percentage": uptime_percentage,
                "total_errors": len(self.error_history),
                "components_monitored": len(component_latencies)
            }
        )
    
    def _calculate_average_latency(self) -> float:
        """Calculate average latency"""
        if not self.latency_history:
            return 0.0
        
        latencies = [entry["latency_ms"] for entry in self.latency_history]
        return np.mean(latencies)
    
    def _calculate_percentile_latency(self, percentile: float) -> float:
        """Calculate percentile latency"""
        if not self.latency_history:
            return 0.0
        
        latencies = [entry["latency_ms"] for entry in self.latency_history]
        return np.percentile(latencies, percentile)
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate (errors per minute)"""
        if len(self.error_history) < 2:
            return 0.0
        
        # Calculate errors per second over last 5 minutes
        cutoff_time = time.time() - 300  # 5 minutes ago
        recent_errors = [
            x for x in self.error_history 
            if x["timestamp"] > cutoff_time * 1e9
        ]
        
        if len(recent_errors) == 0:
            return 0.0
        
        # Errors per second
        eps = len(recent_errors) / 300.0
        # Convert to errors per minute
        return eps * 60.0
    
    def _calculate_uptime_percentage(self) -> float:
        """Calculate system uptime percentage"""
        if len(self.uptime_history) < 2:
            return 100.0
        
        # Simplified: assume system started healthy and track downtime from errors
        # In practice, would track explicit health checks
        recent_errors = [
            x for x in self.error_history 
            if x["timestamp"] > (time.time() - 3600) * 1e9  # Last hour
        ]
        
        # Simple penalty: 1% downtime per error in last hour (capped at 50% downtime)
        error_penalty = min(len(recent_errors) * 1.0, 50.0)
        uptime_percentage = 100.0 - error_penalty
        
        return max(uptime_percentage, 0.0)


# Placeholder classes for other monitoring engines (would be fully implemented in practice)
class PredictiveEngine:
    def __init__(self): pass
    def update(self, *args, **kwargs): 
        return UnifiedMetric(MetricType.PREDICTIVE, "placeholder", 0.0, int(time.time() * 1e9))

class VaREngine:
    def __init__(self): pass
    def update(self, *args, **kwargs): 
        return UnifiedMetric(MetricType.VAR, "placeholder", 0.0, int(time.time() * 1e9))

class FactorAttributionEngine:
    def __init__(self): pass
    def update(self, *args, **kwargs): 
        return UnifiedMetric(MetricType.FACTOR_ATTRIBUTION, "placeholder", 0.0, int(time.time() * 1e9))

class StrategyOptimizerEngine:
    def __init__(self): pass
    def update(self, *args, **kwargs): 
        return UnifiedMetric(MetricType.STRATEGY_OPTIMIZER, "placeholder", 0.0, int(time.time() * 1e9))

class CorrelationMonitorEngine:
    def __init__(self): pass
    def update(self, *args, **kwargs): 
        return UnifiedMetric(MetricType.CORRELATION_MONITOR, "placeholder", 0.0, int(time.time() * 1e9))


class FeedbackLayer:
    """
    Unified Feedback Layer that coordinates all monitoring and learning engines
    """
    
    def __init__(self):
        self.pnl_engine = PNLEngine()
        self.learning_insights_engine = LearningInsightsEngine()
        self.sre_metrics_engine = SREMetricsEngine()
        self.predictive_engine = PredictiveEngine()
        self.var_engine = VaREngine()
        self.factor_attribution_engine = FactorAttributionEngine()
        self.strategy_optimizer_engine = StrategyOptimizerEngine()
        self.correlation_monitor_engine = CorrelationMonitorEngine()
        
        # Metric history
        self.metric_history = []
        
        # Alert thresholds (would be configurable)
        self.alert_thresholds = {
            "pnl_drawdown": 0.05,  # 5% drawdown triggers alert
            "sre_latency_p95": 100.0,  # 100ms p95 latency
            "sre_error_rate": 10.0,   # 10 errors per minute
            "learning_insight_stagnation": 0.1  # Low insight score
        }
    
    def update_all(
        self,
        trade_result: Dict,
        current_positions: Dict,
        market_prices: Dict,
        belief_state: Dict,
        execution_result: Dict,
        market_data: Dict,
        component_latencies: Dict[str, float],
        error_events: List[Dict],
        system_health: Dict[str, bool],
        model_info: Dict = None
    ) -> List[UnifiedMetric]:
        """
        Update all feedback engines and return metrics
        
        Returns:
            List of unified metrics from all engines
        """
        metrics = []
        
        # Update P&L engine
        pnl_metric = self.pnl_engine.update(trade_result, current_positions, market_prices)
        metrics.append(pnl_metric)
        
        # Update learning insights engine
        learning_metric = self.learning_insights_engine.update(
            belief_state, execution_result, market_data, model_info
        )
        metrics.append(learning_metric)
        
        # Update SRE metrics engine
        sre_metric = self.sre_metrics_engine.update(
            component_latencies, error_events, system_health
        )
        metrics.append(sre_metric)
        
        # Update other engines (placeholders)
        predictive_metric = self.predictive_engine.update()
        metrics.append(predictive_metric)
        
        var_metric = self.var_engine.update()
        metrics.append(var_metric)
        
        factor_attribution_metric = self.factor_attribution_engine.update()
        metrics.append(factor_attribution_metric)
        
        strategy_optimizer_metric = self.strategy_optimizer_engine.update()
        metrics.append(strategy_optimizer_metric)
        
        correlation_monitor_metric = self.correlation_monitor_engine.update()
        metrics.append(correlation_monitor_metric)
        
        # Record all metrics
        self.metric_history.extend(metrics)
        
        # Keep history bounded
        if len(self.metric_history) > 1000:
            self.metric_history = self.metric_history[-500:]
        
        # Check for alerts
        self._check_alerts(metrics)
        
        return metrics
    
    def _check_alerts(self, metrics: List[UnifiedMetric]):
        """Check if any metrics exceed alert thresholds"""
        for metric in metrics:
            if metric.metric_type == MetricType.PNL and metric.name == "total_pnl":
                # Check drawdown threshold
                drawdown = metric.metadata.get("drawdown", 0.0)
                if drawdown > self.alert_thresholds["pnl_drawdown"]:
                    print(f"ALERT: High drawdown detected: {drawdown:.2%}")
            
            elif metric.metric_type == MetricType.SRE_METRICS:
                # Check latency threshold
                if metric.name == "p95_latency_ms":
                    latency = metric.value
                    if latency > self.alert_thresholds["sre_latency_p95"]:
                        print(f"ALERT: High latency detected: {latency:.2f}ms")
                
                # Check error rate threshold
                error_rate = metric.metadata.get("error_rate", 0.0)
                if error_rate > self.alert_thresholds["sre_error_rate"]:
                    print(f"ALERT: High error rate detected: {error_rate:.2f} errors/min")
            
            elif metric.metric_type == MetricType.LEARNING_INSIGHTS:
                # Check insight stagnation
                if metric.name == "insight_score":
                    insight_score = metric.value
                    if insight_score < self.alert_thresholds["learning_insight_stagnation"]:
                        print(f"ALERT: Learning insights stagnating: {insight_score:.3f}")


# Example usage and testing
if __name__ == "__main__":
    import time
    
    # Create feedback layer
    feedback_layer = FeedbackLayer()
    
    # Simulate data for updating feedback systems
    trade_result = {
        "timestamp": int(time.time() * 1e9),
        "symbol": "BTCUSDT",
        "side": "BUY",
        "filled_quantity": 1.5,
        "average_price": 50000.0,
        "commission": 5.0
    }
    
    current_positions = {
        "BTCUSDT": {
            "quantity": 1.5,
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
        "regime_probabilities": [0.1, 0.2, 0.4, 0.2, 0.05, 0.03, 0.01, 0.01],
        "volatility_estimate": 0.15,
        "liquidity_estimate": 0.7,
        "momentum_signal": 0.05,
        "volume_signal": 0.02,
        "confidence": 0.8
    }
    
    execution_result = {
        "timestamp": int(time.time() * 1e9),
        "status": "FILLED",
        "filled_quantity": 1.5,
        "average_price": 50000.0,
        "slippage": 1.5,  # 1.5 basis points
        "latency": 8,     # 8 milliseconds
        "market_impact": 0.8  # 0.8 basis points
    }
    
    market_data = {
        "signal_strength": 0.4,
        "volatility_estimate": 0.15,
        "liquidity_estimate": 0.6,
        "spread_bps": 2.0
    }
    
    component_latencies = {
        "perception": 2.5,  # ms
        "decision": 1.2,    # ms
        "execution": 3.1,   # ms
        "feedback": 0.8     # ms
    }
    
    error_events = []
    
    system_health = {
        "perception": True,
        "decision": True,
        "execution": True,
        "feedback": True
    }
    
    model_info = {
        "model_version": "v1.2.3",
        "feature_importance": {
            "ofI": 0.25,
            "I_star": 0.20,
            "volatility_estimate": 0.15,
            "liquidity_estimate": 0.15,
            "momentum_signal": 0.10,
            "volume_signal": 0.05,
            "regime_probabilities": 0.10
        }
    }
    
    print("Feedback Layer Update:")
    print("=" * 30)
    
    # Update all feedback systems
    metrics = feedback_layer.update_all(
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
    
    print(f"Generated {len(metrics)} metrics:")
    for metric in metrics:
        print(f"  {metric.metric_type.value}.{metric.name}: {metric.value}")
        if metric.metadata:
            for key, value in list(metric.metadata.items())[:3]:  # Show first 3 metadata items
                print(f"    {key}: {value}")
        print()