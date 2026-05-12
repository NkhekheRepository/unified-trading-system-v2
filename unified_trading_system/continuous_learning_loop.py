#!/usr/bin/env python3
"""
Enhanced Continuous Trading Loop with Learning-Optimized Configuration
Uses parameters optimized for maximum learning opportunities.
"""

import asyncio
import logging
import signal
import time
import yaml
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from perception.belief_state import BeliefState, BeliefStateEstimator, RegimeType
from risk.unified_risk_manager import RiskManifold
from execution.testnet_executor import TestnetExecutionWithGovernance
from execution.smart_order_router import ExecutionModel, ExecutionIntent, OrderType
from decision.signal_generator import SignalGenerator, TradingSignal

from observability.logging import (
    TradingLogger,
    get_correlation_id,
    set_correlation_id,
    set_context,
)
from observability import get_metrics, set_gauge, increment_counter, HealthServer
from observability.alerting import (
    AlertManager,
    AlertSeverity,
    Alert,
    send_trade_execution_alert,
    send_risk_alert,
    send_system_status_alert,
    configure_alerting_from_env,
)
from learning.trade_journal import TradeJournal
from learning.return_predictor import create_return_predictor, ReturnPredictorWrapper
from learning.model_trainer import ReturnModelTrainer



class TradingMode(Enum):
    """Trading operation modes"""
    PAPER = "PAPER"
    TESTNET = "TESTNET"
    LIVE = "LIVE"


@dataclass
class LearningTradingConfig:
    """Learning-optimized trading configuration"""
    mode: TradingMode = TradingMode.TESTNET
    
    symbols: List[str] = field(default_factory=lambda: ["BTC/USDT", "ETH/USDT"])
    
    cycle_interval: float = 30.0  # Faster cycles for more data
    
    max_position_size: float = 0.15  # Larger for learning
    max_daily_loss: float = 15000.0  # Higher tolerance for learning
    max_orders_per_minute: int = 15  # More orders for learning
    
    # Signal generation parameters - Standard learning
    signal_min_confidence: float = 0.2  # Lower threshold -> more signals
    signal_min_expected_return: float = 0.0002  # Lower threshold -> more signals
    signal_max_position_size: float = 0.15  # Slightly larger positions
    
    # NEW: High win rate parameters
    signal_min_uncertainty: float = 0.15  # ML model uncertainty threshold
    signal_buy_bias: float = 0.05  # Prefer BUY signals
    enable_quality_filter: bool = True  # Enable quality filtering
    symbol_weights: Dict[str, float] = field(default_factory=lambda: {"BTC/USDT": 1.0, "ETH/USDT": 0.7})
    exclude_symbols: List[str] = field(default_factory=list)  # Symbols to exclude
    
    enable_alerting: bool = True
    alerting_channels: List[str] = field(default_factory=lambda: ["telegram"])
    
    health_check_port: int = 8081
    metrics_port: int = 9091
    log_level: str = "INFO"  # Standard logging for production


@dataclass
class TradingCycleResult:
    """Result of a trading cycle"""
    cycle_id: str
    timestamp: float
    symbols_processed: int
    signals_generated: int
    orders_executed: int
    errors: List[str]
    duration_ms: float
    success: bool


class AdaptiveLearningTradingLoop:
    """
    Adaptive trading loop optimized for learning opportunities
    Generates more signals with lower thresholds to collect more data
    """
    
    def __init__(self, config: LearningTradingConfig):
        self.config = config
        logging.getLogger().setLevel(getattr(logging, self.config.log_level))
        self.logger = TradingLogger("learning_trading_loop")
        
        self.belief_state_estimator = BeliefStateEstimator()
        self.belief_state = BeliefState(
            expected_return=0.0,
            expected_return_uncertainty=0.0,
            aleatoric_uncertainty=0.0,
            epistemic_uncertainty=0.0,
            regime_probabilities=[0.0] * 8,
            microstructure_features={},
            volatility_estimate=0.0,
            liquidity_estimate=0.5,
            momentum_signal=0.0,
            volume_signal=0.0,
            timestamp=0,
            confidence=0.0
        )
        self.risk_manager = RiskManifold()
        
        # Learning-optimized signal generator with high win rate params
        self.signal_generator = SignalGenerator({
            'min_confidence_threshold': config.signal_min_confidence,
            'min_expected_return': config.signal_min_expected_return,
            'max_position_size': config.signal_max_position_size,
            'volatility_scaling': True,
            'regime_filters': False,  # Disable for learning
            # NEW: High win rate parameters
            'min_uncertainty': config.signal_min_uncertainty,
            'buy_bias': config.signal_buy_bias,
            'symbol_weights': config.symbol_weights,
        })
        
        self.executor = TestnetExecutionWithGovernance(
            max_position_size=config.max_position_size,
            max_daily_loss=config.max_daily_loss,
            max_orders_per_minute=config.max_orders_per_minute,
        )
        
        self.metrics = get_metrics()
        self.alert_manager = AlertManager.get_instance()
        self.journal = TradeJournal()
        
        # ML Return Predictor for confidence-based signals
        # We use 10 features as a baseline (e.g. microstructure signals)
        self.return_predictor = create_return_predictor(input_size=10, model_type="tcn")
        
        # ML Trainer for periodic updates
        self.trainer = ReturnModelTrainer(
            model=self.return_predictor,
            journal_path="logs/trade_journal.json",
            batch_size=16,
            epochs=5
        )
        
        self.health_server: Optional[HealthServer] = None
        
        # Learning tracking
        self._running = False
        self._cycle_count = 0
        self._start_time: Optional[float] = None
        self._shutdown_event = asyncio.Event()
        self._signal_history = []  # Track all generated signals
        self._execution_history = []  # Track all executions
    
    async def initialize(self):
        """Initialize the learning trading loop"""
        self.logger.info("Initializing learning-optimized trading loop")
        
        set_context(
            mode=self.config.mode.value,
            symbols=",".join(self.config.symbols),
            strategy="learning_optimized"
        )
        
        if self.config.enable_alerting:
            configure_alerting_from_env()
            await send_system_status_alert(
                component="learning_trading_loop",
                status="initializing",
                details={
                    "strategy": "learning_optimized",
                    "min_confidence_threshold": self.config.signal_min_confidence,
                    "min_expected_return": self.config.signal_min_expected_return,
                }
            )
        
        self.health_server = HealthServer(
            port=self.config.health_check_port,
        )
        self.health_server.start()
        
        self._register_learning_metrics()
        
        self.logger.info(
            f"Learning trading loop initialized in {self.config.mode.value} mode"
        )
        self.logger.info(
            f"Learning parameters: min_confidence={self.config.signal_min_confidence}, "
            f"min_expected_return={self.config.signal_min_expected_return}"
        )
    
    def _register_learning_metrics(self):
        """Register learning-specific metrics"""
        # Learning loop doesn't need to register custom metrics
        # Use existing metrics or log values instead
        self.logger.info(
            f"Learning parameters: min_confidence={self.config.signal_min_confidence}, "
            f"min_expected_return={self.config.signal_min_expected_return}"
        )
    
    async def start(self):
        """Start the continuous learning trading loop"""
        self.logger.info("Starting learning-optimized trading loop")
        self._running = True
        self._start_time = time.time()
        
        await send_system_status_alert(
            component="learning_trading_loop",
            status="running",
            details={
                "mode": self.config.mode.value,
                "strategy": "learning_optimized",
                "symbols": self.config.symbols,
                "cycle_interval": self.config.cycle_interval,
            },
        )
        
        try:
            while self._running:
                await self._run_learning_cycle()
                await asyncio.sleep(self.config.cycle_interval)
        except asyncio.CancelledError:
            self.logger.info("Learning trading loop cancelled")
        except Exception as e:
            self.logger.error(f"Learning trading loop error: {e}")
            await send_system_status_alert(
                component="learning_trading_loop",
                status="error",
                details={"error": str(e)},
            )
        finally:
            await self.shutdown()
    
    async def _run_learning_cycle(self) -> TradingCycleResult:
        """Run a single learning-optimized trading cycle"""
        self._cycle_count += 1
        cycle_id = f"learning_cycle_{self._cycle_count}_{int(time.time())}"
        
        set_correlation_id(cycle_id)
        
        cycle_start = time.time()
        
        result = TradingCycleResult(
            cycle_id=cycle_id,
            timestamp=cycle_start,
            symbols_processed=0,
            signals_generated=0,
            orders_executed=0,
            errors=[],
            duration_ms=0,
        )

        try:
            self.logger.info(f"Starting {cycle_id}")
            
            # Filter out excluded symbols
            filtered_symbols = [
                s for s in self.config.symbols 
                if s not in self.config.exclude_symbols
            ]
            
            # Process symbols in parallel to minimize latency
            symbol_tasks = [
                self._process_symbol_with_learning(symbol, result) 
                for symbol in filtered_symbols
            ]
            results = await asyncio.gather(*symbol_tasks, return_exceptions=True)

            # Count processed symbols (excluding exceptions)
            result.symbols_processed = len([
                r for r in results 
                if not isinstance(r, Exception)
            ])
            
            self.logger.info(
                f"Completed {cycle_id}: {result.signals_generated} learning signals, "
                f"{result.orders_executed} orders in {result.duration_ms:.1f}ms"
            )

        except Exception as e:
            self.logger.error(f"Learning cycle error: {e}")
            result.errors.append(str(e))
            result.success = False

        finally:
            result.duration_ms = (time.time() - cycle_start) * 1000

            # Log learning summary
            if result.signals_generated > 0:
                self.logger.debug(
                    f"Learning cycle {cycle_id} generated {result.signals_generated} signals"
                )
        
        return result
    
    async def _process_symbol_with_learning(self, symbol: str, result: TradingCycleResult):
^        market_data = await self._generate_learning_market_data(symbol)
^        
^        self.belief_state = self.belief_state_estimator.update(market_data)
^        
^        # Log detailed belief state for learning analysis
^        self.logger.debug(
^            f"{symbol}: Learning belief state - "
^            f"Confidence: {self.belief_state.confidence:.4f}, "
^            f"Expected Return: {self.belief_state.expected_return:.6f}, "
^            f"Confidence >= threshold ({self.config.signal_min_confidence}): {self.belief_state.confidence >= self.config.signal_min_confidence}, "
^            f"abs(Expected Return) >= threshold ({self.config.signal_min_expected_return}): {abs(self.belief_state.expected_return) >= self.config.signal_min_expected_return}"
^        )
^        
^        # Generate trading signals with learning-optimized parameters
^        trading_signals = self.signal_generator.generate_signals(self.belief_state, symbol)
^        
^        if trading_signals:
^            result.signals_generated += len(trading_signals)
^            self.logger.info(f"{symbol}: Generated {len(trading_signals)} learning signals")
^            
^            # Track signals for learning analysis
^            for signal in trading_signals:
^                self._signal_history.append({
^                    'cycle': self._cycle_count,
^                    'timestamp': time.time(),
^                    'symbol': signal.symbol,
^                    'action': signal.action,
^                    'quantity': signal.quantity,
^                    'confidence': signal.confidence,
^                    'expected_return': signal.expected_return,
^                    'signal_strength': signal.signal_strength,
^                    'regime': signal.regime.name if hasattr(signal.regime, 'name') else str(signal.regime)
^                })
^            
^            for signal in trading_signals:
^                self.logger.info(
^                    f"{symbol}: Learning signal - {signal.action} {signal.quantity:.6f}, "
^                    f"Confidence: {signal.confidence:.4f}, Strength: {signal.signal_strength:.6f}"
^                )
^                
^                # Learning-optimized risk assessment (more permissive)
^                risk_assessment = self.risk_manager.assess_risk(
^                    belief_state=self.belief_state.to_dict(),
^                    portfolio_state={"cash": 100000.0, "positions": {}},
^                    market_data=market_data,
^                    current_positions={},
^                    recent_returns=[]
^                )
^                
^                # For learning, we allow more risk but still have safety limits
^                if risk_assessment.risk_level.value >= 3:  # ERROR level or higher only
^                    self.logger.warning(
^                        f"Learning signal rejected by risk manager: {risk_assessment.protective_action}"
^                    )
^                    await send_risk_alert(
^                        message=f"Learning signal rejected for {symbol}",
^                        violation_type="risk_check_failed",
^                        details={
^                            "symbol": symbol,
^                            "risk_level": risk_assessment.risk_level.name,
^                            "risk_score": risk_assessment.risk_score,
^                        },
^                    )
^                    continue
                    
                    await self._execute_learning_signal(signal, result, market_data)
            else:
                self.logger.debug(f"{symbol}: No learning signals generated")
        
        except Exception as e:
^        self.logger.error(f"Error processing {symbol} for learning: {e}")
^        result.errors.append(f"{symbol}: {str(e)}")
    
    async def _generate_learning_market_data(self, symbol: str) -> Dict:
        """Generate market data optimized for learning (more frequent imbalances)"""
        import random
        
        base_prices = {
^        "BTC/USDT": 50000.0,
^        "ETH/USDT": 3000.0,
^        "BNB/USDT": 400.0,
^        "SOL/USDT": 100.0,
        }
        
        base_price = base_prices.get(symbol, 100.0)
        
        # Learning-optimized: More frequent and stronger imbalances
        price_change = random.gauss(0, 0.002) * base_price  # More volatility for learning
        current_price = base_price + price_change
        
        # Larger spread variation for learning
        spread_bps = random.uniform(2, 10)  # 2-10 bps
        spread = current_price * spread_bps / 10000
        bid_price = current_price - spread / 2
        ask_price = current_price + spread / 2
        
        # More frequent imbalances for learning (50% chance)
        base_size = random.uniform(5, 10)
        
        if random.random() < 0.5:  # 50% chance of strong imbalance
^        imbalance_strength = random.uniform(2, 5)  # Larger imbalances for learning
^        if random.random() < 0.5:
^            bid_size = base_size * imbalance_strength  # Strong bid
^            ask_size = base_size
^        else:
^            bid_size = base_size
^            ask_size = base_size * imbalance_strength  # Strong ask
        else:
^        bid_size = base_size * random.uniform(0.7, 1.3)
^        ask_size = base_size * random.uniform(0.7, 1.3)
        
        # Last trade information
        last_price_choice = random.random()
        if last_price_choice < 0.4:
^        last_price = bid_price  # Buying pressure
        elif last_price_choice < 0.8:
^        last_price = ask_price  # Selling pressure
        else:
            last_price = current_price  # Neutral
        
        last_size = random.uniform(1, 10)
        
        return {
^        "symbol": symbol,
^        "bid_price": bid_price,
^        "ask_price": ask_price,
^        "bid_size": bid_size,
^        "ask_size": ask_size,
^        "last_price": last_price,
^        "last_size": last_size,
        }
    
    async def _execute_learning_signal(self, signal: TradingSignal, result: TradingCycleResult, market_data: Dict):
        """Execute a learning-optimized trading signal"""
        try:
^        intent = ExecutionIntent(
^            symbol=signal.symbol,
^            side=signal.action,
^            quantity=signal.quantity,
^            urgency=signal.confidence,
^            max_slippage=0.002,  # Higher tolerance for learning
^            min_time_limit=5,  # Faster for learning
^            max_time_limit=30,  # Faster for learning
^            aggression_level=0.6,  # More aggressive for learning
^            timestamp=int(time.time() * 1000),
^        )
^        
^        exec_result = await self.executor.execute_intent(intent)
^        
^        # ML-based return prediction and uncertainty quantification
^        # We generate a feature vector from the belief state and market data
^        feature_vector = np.array([
^            self.belief_state.confidence,
^            self.belief_state.expected_return,
^            self.belief_state.volatility_estimate,
^            self.belief_state.liquidity_estimate,
^            self.belief_state.momentum_signal,
^            self.belief_state.volume_signal,
^            market_data.get("bid_size", 0) / (market_data.get("ask_size", 1) + 1e-6),
^            market_data.get("last_price", 0) - market_data.get("bid_price", 0),
^            market_data.get("ask_price", 0) - market_data.get("last_price", 0),
^            self.belief_state.epistemic_uncertainty
^        ])
^        
^        try:
^            predicted_return, uncertainty = self.return_predictor.predict_return(
^                feature_vector, 
^                return_uncertainty=True
^            )
^        except Exception as e:
^            self.logger.warning(f"ML prediction failed, using defaults: {e}")
^            predicted_return = self.belief_state.expected_return
^            uncertainty = 0.1
^        
^        # Check for NaN
^        if np.isnan(predicted_return):
^            predicted_return = self.belief_state.expected_return
^        if np.isnan(uncertainty) or uncertainty <= 0:
^            uncertainty = 0.1
^        
^        # NEW: Quality-based filtering before execution
^        if self.config.enable_quality_filter:
^            should_execute = self.signal_generator.should_accept_signal(
^                action=signal.action,
^                symbol=signal.symbol,
^                uncertainty=uncertainty,
^                base_confidence=signal.confidence
^            )
^            
^            if not should_execute:
^                self.logger.info(
^                    f"Signal filtered by quality: conf={signal.confidence:.3f}, unc={uncertainty:.3f}, "
^                    f"action={signal.action}, symbol={signal.symbol}"
^                )
^                # Log filtered signal for analysis
^                self._signal_history.append({
^                    'cycle': self._cycle_count,
^                    'timestamp': time.time(),
^                    'symbol': signal.symbol,
^                    'action': signal.action,
^                    'quantity': signal.quantity,
^                    'confidence': signal.confidence,
^                    'expected_return': signal.expected_return,
^                    'signal_strength': signal.signal_strength,
^                    'filtered': True,
^                    'uncertainty': uncertainty,
^                    'regime': signal.regime.name if hasattr(signal.regime, 'name') else str(signal.regime)
^                })
^                return  # Skip execution
^        
^        # Adjust position size based on quality
^        adjusted_quantity = self.signal_generator.adjust_position_size(
^            signal.action, signal.symbol, uncertainty, signal.quantity
^        )
^        signal.quantity = adjusted_quantity
^        
^        # Record entry in journal
^        trade_id = f"trade_{int(time.time() * 1000)}"
^        # Calculate mid price from bid/ask
^        bid_price = market_data.get("bid_price", 0.0)
^        ask_price = market_data.get("ask_price", 0.0)
^        mid_price = (bid_price + ask_price) / 2 if bid_price and ask_price else 0.0
^        
^        self.journal.record_entry(
^            trade_id=trade_id,
^            symbol=signal.symbol,
^            side=signal.action,
^            quantity=signal.quantity,
^            entry_price=mid_price,
^            predicted_return=predicted_return,
^            uncertainty=uncertainty,
^            metadata={'cycle': self._cycle_count, 'confidence': signal.confidence}
^        )
^        
^        # For the learning loop, we simulate immediate exit to collect training data faster
^        await asyncio.sleep(0.1) # Simulate small hold time
^        
^        # Simulated exit price based on simple random walk
^        exit_price = mid_price * (1 + np.random.normal(0, 0.001))
^        self.journal.record_exit(trade_id, exit_price)
^        
^        # Check if execution was successful
^        if exec_result.status.value in ["FILLED", "PARTIALLY_FILLED"]:
^            # Update result metrics
^            result.orders_executed += 1
^            
^            # Track successful execution for learning
^            self._execution_history.append({
^                'cycle': self._cycle_count,
^                'timestamp': time.time(),
^                'symbol': signal.symbol,
^                'action': signal.action,
^                'quantity': signal.quantity,
^                'price': exec_result.average_price,
^                'confidence': signal.confidence,
^                'signal_strength': signal.signal_strength,
^                'execution_quality': exec_result.market_impact
^            })
^            
^            await send_trade_execution_alert(
^                symbol=signal.symbol,
^                side=signal.action,
^                quantity=signal.quantity,
^                price=exec_result.average_price,
^                success=True,
^                metadata={
^                    'learning_cycle': self._cycle_count,
^                    'signal_confidence': signal.confidence,
^                    'signal_strength': signal.signal_strength,
^                }
^            )
^            
^            self.logger.info(
^                f"Learning execution: {signal.action} {signal.quantity} {signal.symbol} "
^                f"@ {exec_result.average_price}"
^            )
^            
^            # Log detailed learning metrics
^            self.logger.debug(
^                f"Learning execution details: "
^                f"slippage={exec_result.slippage:.4f}%, "
^                f"market_impact={exec_result.market_impact:.4f}, "
^                f"execution_time={exec_result.latency / 1000:.2f}s"
^            )
^        else:
^            await send_trade_execution_alert(
^                symbol=signal.symbol,
                    side=signal.action,
                    quantity=signal.quantity,
                    price=0,
                    success=False,
                    error=exec_result.error_message or "Unknown error",
                    metadata={'learning_cycle': self._cycle_count}
                )
                self.logger.warning(f"Learning execution failed: {exec_result.error_message}")
        
        except Exception as e:
            self.logger.error(f"Learning execution error: {e}")
            result.errors.append(f"Learning execution: {str(e)}")
    
    async def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary of learning progress"""
        return {
            "cycles_completed": self._cycle_count,
            "total_signals_generated": len(self._signal_history),
            "total_executions": len(self._execution_history),
            "signal_generation_rate": len(self._signal_history) / max(1, self._cycle_count),
            "execution_rate": len(self._execution_history) / max(1, len(self._signal_history)),
            "signal_confidence_distribution": self._get_confidence_distribution(),
            "recent_signals": self._signal_history[-10:] if self._signal_history else [],
            "recent_executions": self._execution_history[-10:] if self._execution_history else [],
            # NEW: Win rate tracking
            "rolling_win_rate": self.get_rolling_win_rate(20),
            "filtered_signals": len([s for s in self._signal_history if s.get('filtered', False)]),
        }
    
    def get_rolling_win_rate(self, n: int = 20) -> float:
        """Calculate rolling win rate over last n trades
        
        Args:
            n: Number of recent trades to analyze
            
        Returns:
            Win rate as percentage (0-100)
        """
        if len(self._execution_history) < n:
            # Use all available trades if less than n
            n = len(self._execution_history)
        
        if n == 0:
            return 0.0
        
        # Get recent executions
        recent = list(self._execution_history)[-n:]
        
        # Count wins (need journal data for PnL)
        wins = 0
        for exec_record in recent:
            trade_id = f"trade_{int(exec_record['timestamp'] * 1000)}"
            trade = self.journal.get_trade(trade_id)
            if trade and trade.get('pnl', 0) > 0:
                wins += 1
        
        return (wins / n) * 100
    
    def _should_execute_signal(self, signal, uncertainty) -> bool:
        """Determine if signal should be executed based on quality filters
        
        Args:
            signal: TradingSignal
            uncertainty: ML model uncertainty
            
        Returns:
            True if signal should be executed
        """
        if not self.config.enable_quality_filter:
            return True
        
        return self.signal_generator.should_accept_signal(
            action=signal.action,
            symbol=signal.symbol,
            uncertainty=uncertainty,
            base_confidence=signal.confidence
        )
    
    def _get_confidence_distribution(self) -> Dict[str, float]:
        """Get distribution of signal confidence levels"""
        if not self._signal_history:
            return {}
        
        confidences = [s['confidence'] for s in self._signal_history]
        return {
            "mean": sum(confidences) / len(confidences),
            "min": min(confidences),
            "max": max(confidences),
            "std": (
                (sum((c - (sum(confidences) / len(confidences))) ** 2 for c in confidences) / len(confidences)) ** 0.5
                if len(confidences) > 1 else 0
            ),
            "count_below_threshold": len([c for c in confidences if c < self.config.signal_min_confidence]),
        }
    
    async def shutdown(self):
        """Shutdown the learning trading loop"""
        self.logger.info("Shutting down learning trading loop")
        self._running = False
        
        if self.health_server:
            self.health_server.stop()
        
        balance = await self.executor.get_balance()
        positions = await self.executor.get_positions()
        learning_summary = await self.get_learning_summary()
        
        await send_system_status_alert(
            component="learning_trading_loop",
            status="stopped",
            details={
                "cycles_completed": self._cycle_count,
                "uptime_seconds": time.time() - self._start_time if self._start_time else 0,
                "final_balance": balance,
                "final_positions": positions,
                "learning_summary": learning_summary,
            },
        )
        
        # Save learning results
        self._save_learning_results(learning_summary)
        
        self._shutdown_event.set()
    
    def _save_learning_results(self, summary=None):
        """Save learning results to file"""
        import json
        
        if summary is None:
            summary = {}

        learning_data = {
            "config": {
                "signal_min_confidence": self.config.signal_min_confidence,
                "signal_min_expected_return": self.config.signal_min_expected_return,
                "max_position_size": self.config.max_position_size,
            },
            "summary": summary,
            "signal_history": self._signal_history,
            "execution_history": self._execution_history,
            "start_time": self._start_time,
            "end_time": time.time(),
        }
        
        import os
        os.makedirs('logs', exist_ok=True)
        
        with open(f'logs/learning_results_{int(time.time())}.json', 'w') as f:
            json.dump(learning_data, f, indent=2, default=str)
        
        self.logger.info(f"Learning results saved to logs/learning_results_{int(time.time())}.json")
    
    async def wait_for_shutdown(self):
        """Wait for shutdown to complete"""
        await self._shutdown_event.wait()


def create_learning_trading_loop(config_path: str = None) -> AdaptiveLearningTradingLoop:
    """Create a learning-optimized trading loop"""
    if config_path:
        # Load from config file
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
        except Exception as e:
            print(f"Failed to load config from {config_path}: {e}")
            config_data = {}
    else:
        config_data = {}
    
    # Default config with learning optimization
    config = LearningTradingConfig(
        mode=TradingMode.TESTNET,
        symbols=["BTC/USDT", "ETH/USDT"],
        cycle_interval=30.0,
        max_position_size=0.15,
        max_daily_loss=15000.0,
        max_orders_per_minute=15,
        signal_min_confidence=0.2,
        signal_min_expected_return=0.0002,
        signal_max_position_size=0.15,
        enable_alerting=True,
        health_check_port=8081,
        metrics_port=9091,
        log_level="DEBUG"
    )
    
    # Override with loaded config data
    if config_data:
        # Extract signal_generation settings
        signal_config = config_data.get('signal_generation', {})
        
        if signal_config:
            if signal_config.get('min_confidence_threshold'):
                config.signal_min_confidence = signal_config['min_confidence_threshold']
            if signal_config.get('min_expected_return'):
                config.signal_min_expected_return = signal_config['min_expected_return']
            if signal_config.get('min_uncertainty'):
                config.signal_min_uncertainty = signal_config['min_uncertainty']
            if signal_config.get('buy_bias'):
                config.signal_buy_bias = signal_config['buy_bias']
            if signal_config.get('symbols'):
                config.symbols = signal_config['symbols']
            if signal_config.get('symbol_weights'):
                config.symbol_weights = signal_config['symbol_weights']
            if signal_config.get('exclude_symbols'):
                config.exclude_symbols = signal_config.get('exclude_symbols', [])
        
        # Extract other settings
        execution_config = config_data.get('execution', {})
        if execution_config:
            if execution_config.get('cycle_interval'):
                config.cycle_interval = execution_config['cycle_interval']
            if execution_config.get('max_position_size'):
                config.max_position_size = execution_config['max_position_size']
    
    return AdaptiveLearningTradingLoop(config)


async def run_learning_trading_loop(config_path: str = None):
    """Run the learning-optimized trading loop with proper signal handling"""
    loop = create_learning_trading_loop(config_path)
    
    def signal_handler(sig, frame):
        print("\nLearning shutdown signal received")
        loop._running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    await loop.initialize()
    await loop.start()


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Learning-Optimized Trading Loop")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--test", action="store_true", help="Run in test mode")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    )
    
    if args.test:
        print("Testing learning trading loop configuration...")
        loop = create_learning_trading_loop(args.config)
        print(f"Created learning loop with config:")
        print(f"  Signal min confidence: {loop.config.signal_min_confidence}")
        print(f"  Signal min expected return: {loop.config.signal_min_expected_return}")
        print(f"  Cycle interval: {loop.config.cycle_interval}s")
        print(f"  Symbols: {loop.config.symbols}")
        exit(0)
    
    print("=" * 60)
    print("LEARNING-OPTIMIZED TRADING LOOP")
    print("Strategy: Lower thresholds for maximum learning opportunities")
    print("=" * 60)
    
    asyncio.run(run_learning_trading_loop(args.config))