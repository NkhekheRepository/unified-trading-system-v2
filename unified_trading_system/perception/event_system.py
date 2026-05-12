"""
Unified Event System for the Integrated Trading System
Combines LVR's event sourcing with Autonomous System's structured communication
"""


import json
import uuid
import time
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Union
from datetime import datetime


class EventType(Enum):
    """Unified event types combining both systems"""
    MARKET_DATA_UPDATE = "MARKET_DATA_UPDATE"
    BELIEF_STATE_UPDATE = "BELIEF_STATE_UPDATE"
    FEATURES_COMPUTED = "FEATURES_COMPUTED"
    REGIME_DETECTED = "REGIME_DETECTED"
    AGGRESSION_UPDATE = "AGGRESSION_UPDATE"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    EXECUTION_INTENT = "EXECUTION_INTENT"
    TRADE_EXECUTED = "TRADE_EXECUTED"
    PERFORMANCE_METRIC = "PERFORMANCE_METRIC"
    LEARNING_UPDATE = "LEARNING_UPDATE"
    SYSTEM_HEALTH = "SYSTEM_HEALTH"
    ERROR_EVENT = "ERROR_EVENT"


@dataclass(frozen=True)
class EventMetadata:
    """Immutable event metadata"""
    event_id: str
    timestamp: int  # nanoseconds since epoch
    trace_id: str
    version: int
    source_component: str


@dataclass(frozen=True)
class UnifiedEvent:
    """Immutable unified event combining LVR and Autonomous System approaches"""
    metadata: EventMetadata
    event_type: EventType
    payload: Dict[str, Any]

    def to_dict(self):
        """Convert event to dictionary for serialization"""
        return {
            "event_id": self.metadata.event_id,
            "timestamp": self.metadata.timestamp,
            "trace_id": self.metadata.trace_id,
            "event_type": self.event_type.value,
            "version": self.metadata.version,
            "source_component": self.metadata.source_component,
            "payload": self.payload
        }

    def to_json(self):
        """Convert event to JSON string"""
        return json.dumps(self.to_dict(), separators=(',', ':'))

    @classmethod
    def from_dict(cls, data):
        """Create event from dictionary"""
        metadata = EventMetadata(
            event_id=data["event_id"],
            timestamp=data["timestamp"],
            trace_id=data["trace_id"],
            version=data["version"],
            source_component=data["source_component"]
        )
        return cls(
            metadata=metadata,
            event_type=EventType(data["event_type"]),
            payload=data["payload"]
        )

    @classmethod
    def from_json(cls, json_str):
        """Create event from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)


class EventFactory:
    """Factory for creating unified events"""

    @staticmethod
    def create_market_data_update(
        symbol: str,
        bid_price: float,
        ask_price: float,
        bid_size: float = 0.0,
        ask_size: float = 0.0,
        last_price: float = 0.0,
        last_size: float = 0.0,
        source_component: str = "market_data_feed"
    ):
        """Create a market data update event"""
        return UnifiedEvent(
            metadata=EventMetadata(
                event_id=str(uuid.uuid4()),
                timestamp=time.time_ns(),
                trace_id=str(uuid.uuid4()),
                version=1,
                source_component=source_component
            ),
            event_type=EventType.MARKET_DATA_UPDATE,
            payload={
                "symbol": symbol,
                "bid_price": bid_price,
                "ask_price": ask_price,
                "bid_size": bid_size,
                "ask_size": ask_size,
                "last_price": last_price,
                "last_size": last_size
            }
        )

    @staticmethod
    def create_belief_state_update(
        expected_return: float,
        expected_return_uncertainty: float,
        aleatoric_uncertainty: float,
        epistemic_uncertainty: float,
        regime_probabilities: list,
        source_component: str = "belief_state_estimator"
    ):
        """Create a belief state update event"""
        return UnifiedEvent(
            metadata=EventMetadata(
                event_id=str(uuid.uuid4()),
                timestamp=time.time_ns(),
                trace_id=str(uuid.uuid4()),
                version=1,
                source_component=source_component
            ),
            event_type=EventType.BELIEF_STATE_UPDATE,
            payload={
                "expected_return": expected_return,
                "expected_return_uncertainty": expected_return_uncertainty,
                "aleatoric_uncertainty": aleatoric_uncertainty,
                "epistemic_uncertainty": epistemic_uncertainty,
                "regime_probabilities": regime_probabilities
            }
        )

    @staticmethod
    def create_features_computed(
        symbol: str,
        ofI: float,
        I_star: float,
        L_star: float,
        S_star: float,
        depth_imbalance: float = 0.0,
        volume_imbalance: float = 0.0,
        price_momentum: float = 0.0,
        volatility_estimate: float = 0.0,
        source_component: str = "feature_processor"
    ):
        """Create a features computed event"""
        return UnifiedEvent(
            metadata=EventMetadata(
                event_id=str(uuid.uuid4()),
                timestamp=time.time_ns(),
                trace_id=str(uuid.uuid4()),
                version=1,
                source_component=source_component
            ),
            event_type=EventType.FEATURES_COMPUTED,
            payload={
                "symbol": symbol,
                "ofI": ofI,
                "I_star": I_star,
                "L_star": L_star,
                "S_star": S_star,
                "depth_imbalance": depth_imbalance,
                "volume_imbalance": volume_imbalance,
                "price_momentum": price_momentum,
                "volatility_estimate": volatility_estimate
            }
        )

    @staticmethod
    def create_regime_detected(
        symbol: str,
        regime_id: int,
        regime_confidence: float,
        regime_probabilities: list,
        features_used: list,
        source_component: str = "regime_detector"
    ):
        """Create a regime detected event"""
        return UnifiedEvent(
            metadata=EventMetadata(
                event_id=str(uuid.uuid4()),
                timestamp=time.time_ns(),
                trace_id=str(uuid.uuid4()),
                version=1,
                source_component=source_component
            ),
            event_type=EventType.REGIME_DETECTED,
            payload={
                "symbol": symbol,
                "regime_id": regime_id,
                "regime_confidence": regime_confidence,
                "regime_probabilities": regime_probabilities,
                "features_used": features_used
            }
        )

    @staticmethod
    def create_aggression_update(
        aggression_level: float,
        signal_strength: float,
        risk_gradient: float,
        aggression_rate: float = 0.0,
        execution_feedback: float = 0.0,
        source_component: str = "aggression_controller"
    ):
        """Create an aggression update event"""
        return UnifiedEvent(
            metadata=EventMetadata(
                event_id=str(uuid.uuid4()),
                timestamp=time.time_ns(),
                trace_id=str(uuid.uuid4()),
                version=1,
                source_component=source_component
            ),
            event_type=EventType.AGGRESSION_UPDATE,
            payload={
                "aggression_level": aggression_level,
                "signal_strength": signal_strength,
                "risk_gradient": risk_gradient,
                "aggression_rate": aggression_rate,
                "execution_feedback": execution_feedback
            }
        )

    @staticmethod
    def create_risk_assessment(
        risk_level: int,
        cvar: float,
        volatility: float,
        drawdown: float,
        liquidity_score: float,
        correlation_risk: float,
        leverage_ratio: float,
        protective_action: str,
        source_component: str = "risk_manager"
    ):
        """Create a risk assessment event"""
        return UnifiedEvent(
            metadata=EventMetadata(
                event_id=str(uuid.uuid4()),
                timestamp=time.time_ns(),
                trace_id=str(uuid.uuid4()),
                version=1,
                source_component=source_component
            ),
            event_type=EventType.RISK_ASSESSMENT,
            payload={
                "risk_level": risk_level,
                "risk_metrics": {
                    "cvar": cvar,
                    "volatility": volatility,
                    "drawdown": drawdown,
                    "liquidity_score": liquidity_score,
                    "correlation_risk": correlation_risk,
                    "leverage_ratio": leverage_ratio
                },
                "protective_action": protective_action
            }
        )

    @staticmethod
    def create_execution_intent(
        symbol: str,
        side: str,
        quantity: float,
        order_type: str,
        price: float = 0.0,
        time_in_force: str = "GTC",
        urgency: float = 0.5,
        source_component: str = "execution_planner"
    ):
        """Create an execution intent event"""
        return UnifiedEvent(
            metadata=EventMetadata(
                event_id=str(uuid.uuid4()),
                timestamp=time.time_ns(),
                trace_id=str(uuid.uuid4()),
                version=1,
                source_component=source_component
            ),
            event_type=EventType.EXECUTION_INTENT,
            payload={
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "order_type": order_type,
                "price": price,
                "time_in_force": time_in_force,
                "urgency": urgency
            }
        )

    @staticmethod
    def create_trade_executed(
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        timestamp: int,
        commission: float = 0.0,
        slippage: float = 0.0,
        latency: int = 0,
        source_component: str = "executor"
    ):
        """Create a trade executed event"""
        return UnifiedEvent(
            metadata=EventMetadata(
                event_id=str(uuid.uuid4()),
                timestamp=time.time_ns(),
                trace_id=str(uuid.uuid4()),
                version=1,
                source_component=source_component
            ),
            event_type=EventType.TRADE_EXECUTED,
            payload={
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "timestamp": timestamp,
                "commission": commission,
                "slippage": slippage,
                "latency": latency
            }
        )

    @staticmethod
    def create_performance_metric(
        timestamp: int,
        pnl: float,
        unrealized_pnl: float,
        realized_pnl: float,
        drawdown: float,
        sharpe_ratio: float = 0.0,
        win_rate: float = 0.0,
        profit_factor: float = 0.0,
        total_trades: int = 0,
        winning_trades: int = 0,
        source_component: str = "pnl_engine"
    ):
        """Create a performance metric event"""
        return UnifiedEvent(
            metadata=EventMetadata(
                event_id=str(uuid.uuid4()),
                timestamp=time.time_ns(),
                trace_id=str(uuid.uuid4()),
                version=1,
                source_component=source_component
            ),
            event_type=EventType.PERFORMANCE_METRIC,
            payload={
                "timestamp": timestamp,
                "pnl": pnl,
                "unrealized_pnl": unrealized_pnl,
                "realized_pnl": realized_pnl,
                "drawdown": drawdown,
                "sharpe_ratio": sharpe_ratio,
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "total_trades": total_trades,
                "winning_trades": winning_trades
            }
        )

    @staticmethod
    def create_learning_update(
        model_version: str,
        performance_improvement: float,
        uncertainty_reduction: float,
        feature_importance: dict = None,
        hyperparameters: dict = None,
        source_component: str = "learning_system"
    ):
        """Create a learning update event"""
        return UnifiedEvent(
            metadata=EventMetadata(
                event_id=str(uuid.uuid4()),
                timestamp=time.time_ns(),
                trace_id=str(uuid.uuid4()),
                version=1,
                source_component=source_component
            ),
            event_type=EventType.LEARNING_UPDATE,
            payload={
                "model_version": model_version,
                "performance_improvement": performance_improvement,
                "uncertainty_reduction": uncertainty_reduction,
                "feature_importance": feature_importance or {},
                "hyperparameters": hyperparameters or {}
            }
        )


class EventBus:
    """
    Unified event bus combining LVR's Redis/PostgreSQL approach
    with Autonomous System's structured event handling
    """

    def __init__(self, redis_client=None, postgres_client=None):
        self.redis_client = redis_client
        self.postgres_client = postgres_client
        self.subscribers = {}  # event_type -> list of callbacks
        self.event_store = []  # In-memory store for recent events (would be PostgreSQL in production)

    def subscribe(self, event_type: EventType, callback):
        """Subscribe to events of a specific type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    def publish(self, event: UnifiedEvent):
        """Publish an event to all subscribers"""
        # Store event (in production, this would go to PostgreSQL)
        self.event_store.append(event)
        
        # Keep only recent events in memory (last 10000)
        if len(self.event_store) > 10000:
            self.event_store = self.event_store[-10000:]

        # Notify subscribers
        if event.event_type in self.subscribers:
            for callback in self.subscribers[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    # In production, this would go to error handling/monitoring
                    print(f"Error in event callback: {e}")

        # In production, also publish to Redis for real-time distribution
        if self.redis_client:
            try:
                self.redis_client.publish(
                    f"events:{event.event_type.value}",
                    event.to_json()
                )
            except Exception as e:
                print(f"Error publishing to Redis: {e}")

    def replay_events(self, start_index: int = 0, end_index: int = None):
        """Replay events from the store (LVR's replay capability)"""
        if end_index is None:
            end_index = len(self.event_store)
        return self.event_store[start_index:end_index]

    def get_recent_events(self, count: int = 100):
        """Get recent events"""
        return self.event_store[-count:] if len(self.event_store) >= count else self.event_store[:]