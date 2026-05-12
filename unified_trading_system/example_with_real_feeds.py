"""
Example showing how to use the Unified Trading System with real market data feeds
Demonstrates the next-level capability of connecting to real exchanges
"""

import time
import numpy as np
import sys
import os

# Add the current directory to the Python path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from perception.belt_state import BeliefStateEstimator
from decision.aggression_controller import AggressionController
from execution.smart_order_router import ExecutionModel, ExecutionIntent
from risk.unified_risk_manager import RiskManifold
from feedback.monitoring_engine import FeedbackLayer
from adaptation.drift_detector import AdaptationLayer
from perception.event_system import EventBus, EventFactory, EventType
from perception.market_data_feed import SimulatedMarketDataFeed, MarketDataFeedFactory
from perception.market_data_feed import FeedType, MarketDataUpdate
from config.config_manager import ConfigManager