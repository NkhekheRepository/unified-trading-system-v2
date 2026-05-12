#!/usr/bin/env python3
"""
Main system runner for Unified HFT Trading System
Runs all components as a production service targeting 70%+ daily profits
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime
import os

# Add system to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from perception.async_data_feed import AsyncWebSocketManager, get_optimized_event_loop
from execution.rl_execution_agent import QLearningExecutionAgent
from risk.hedging_engine import HedgingEngine
from scoring.score_system import PerformanceScorer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/nkhekhe/unified_trading_system/logs/system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingSystemRunner:
    """Orchestrates all system components"""
    
    def __init__(self):
        self.running = False
        self.components = {}
        self.loop = None
        
    async def start_async_data_feed(self):
        """Start async WebSocket data feed"""
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
        manager = AsyncWebSocketManager(symbols)
        
        def print_tick(tick):
            logger.info(f"Tick: {tick.symbol} @ ${tick.price:.2f}")
        
        manager.add_callback(print_tick)
        
        self.components['async_feed'] = manager
        await manager.start()
    
    async def run_rl_agent_loop(self):
        """Run RL agent in continuous learning loop"""
        agent = QLearningExecutionAgent()
        logger.info("RL Execution Agent started")
        
        while self.running:
            # Agent runs in background, learning from execution results
            await asyncio.sleep(60)  # Check every minute
            logger.info(f"RL Agent Status: {agent.execution_count} executions, "
                      f"{agent.total_slippage_saved:.2f} bps saved")
    
    async def run_hedging_loop(self):
        """Run hedging engine monitor"""
        engine = HedgingEngine()
        logger.info("Hedging Engine started")
        
        while self.running:
            evaluation = engine.evaluate_hedging_need()
            if evaluation['needs_hedge'] and evaluation['hedge_action']:
                logger.info(f"Hedge needed: {evaluation['hedge_action']}")
            await asyncio.sleep(30)  # Check every 30 seconds
    
    async def run_scorer_loop(self):
        """Run performance scorer periodically"""
        scorer = PerformanceScorer()
        logger.info("Performance Scorer started")
        
        while self.running:
            report = scorer.generate_report()
            logger.info(f"Performance: {report['rating']} ({report['composite_score']:.1f}) - "
                       f"Daily Profit: {report['daily_profit_pct']:.2f}% "
                       f"(Target: 70%+)")
            await asyncio.sleep(3600)  # Run hourly
    
    async def start(self):
        """Start all system components"""
        self.running = True
        logger.info("=" * 50)
        logger.info("Starting Unified HFT Trading System")
        logger.info("Target: 70%+ Daily Profits")
        logger.info("=" * 50)
        
        # Create tasks for all components
        tasks = [
            asyncio.create_task(self.start_async_data_feed()),
            asyncio.create_task(self.run_rl_agent_loop()),
            asyncio.create_task(self.run_hedging_loop()),
            asyncio.create_task(self.run_scorer_loop())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("System shutdown requested")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop all components gracefully"""
        logger.info("Stopping all components...")
        self.running = False
        
        for name, component in self.components.items():
            if hasattr(component, 'stop'):
                await component.stop()
                logger.info(f"Stopped {name}")
        
        logger.info("All components stopped")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    raise KeyboardInterrupt

if __name__ == "__main__":
    # Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    runner = TradingSystemRunner()
    
    # Get optimized event loop
    loop = get_optimized_event_loop()
    
    try:
        loop.run_until_complete(runner.start())
    except KeyboardInterrupt:
        logger.info("Shutdown by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        loop.close()
        logger.info("System stopped")
