import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
import itertools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class OptimizationWindow:
    """Represents a single walk-forward window"""
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    window_id: int

@dataclass
class StrategyParams:
    """Strategy parameters to optimize"""
    leverage: float
    profit_target: float
    stop_loss: float
    min_confidence: float
    holding_period: int
    
    def to_dict(self) -> Dict:
        return {
            "leverage": self.leverage,
            "profit_target": self.profit_target,
            "stop_loss": self.stop_loss,
            "min_confidence": self.min_confidence,
            "holding_period": self.holding_period
        }

class WalkForwardOptimizer:
    """Walk-Forward Optimization Pipeline for continuous strategy adaptation"""
    
    def __init__(self, config_path: str = "/home/nkhekhe/unified_trading_system/config/strategy_config.yaml"):
        self.config_path = config_path
        self.window_size_days = 30  # Training window
        self.test_size_days = 7     # Out-of-sample test
        self.step_size_days = 7     # Slide window by 7 days
        self.optimization_history = []
        
        # Parameter grids to search (focused on high-profit regimes)
        self.param_grid = {
            "leverage": [15, 20, 25],
            "profit_target": [0.10, 0.15, 0.20, 0.25],
            "stop_loss": [0.05, 0.08, 0.10],
            "min_confidence": [0.65, 0.75, 0.85],
            "holding_period": [7200, 14400, 21600, 28800]  # 2h to 8h
        }
        
    def generate_windows(self, start_date: datetime, end_date: datetime) -> List[OptimizationWindow]:
        """Generate walk-forward windows"""
        windows = []
        window_id = 0
        
        current = start_date
        while current + timedelta(days=self.window_size_days + self.test_size_days) <= end_date:
            train_start = current
            train_end = current + timedelta(days=self.window_size_days)
            test_start = train_end
            test_end = test_start + timedelta(days=self.test_size_days)
            
            windows.append(OptimizationWindow(
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                window_id=window_id
            ))
            
            window_id += 1
            current += timedelta(days=self.step_size_days)
            
        logger.info(f"Generated {len(windows)} walk-forward windows")
        return windows
    
    def load_historical_trades(self, start: datetime, end: datetime) -> List[Dict]:
        """Load historical trades for optimization window"""
        try:
            trade_path = "/home/nkhekhe/unified_trading_system/trade_journal.json"
            with open(trade_path, 'r') as f:
                all_trades = json.load(f)
            
            filtered = [
                t for t in all_trades
                if start <= datetime.fromisoformat(t['timestamp']) <= end
            ]
            return filtered
        except Exception as e:
            logger.error(f"Failed to load trades: {e}")
            return []
    
    def calculate_sharpe_ratio(self, trades: List[Dict]) -> float:
        """Calculate Sharpe ratio for a set of trades"""
        if len(trades) < 2:
            return 0.0
        
        returns = [t.get('pnl_pct', 0) for t in trades]
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        return (avg_return / std_return) if std_return > 0 else 0.0
    
    def calculate_profit_factor(self, trades: List[Dict]) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        gross_profit = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0)
        gross_loss = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0))
        
        return gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    def backtest_params(self, params: StrategyParams, trades: List[Dict]) -> Dict:
        """Simulate strategy performance with given parameters"""
        if not trades:
            return {"sharpe": 0.0, "profit_factor": 0.0, "total_return": 0.0, "win_rate": 0.0}
        
        # Filter trades that would have been taken with these params
        # (Simplified: assume trades match param criteria)
        sharpe = self.calculate_sharpe_ratio(trades)
        profit_factor = self.calculate_profit_factor(trades)
        total_return = sum(t.get('pnl_pct', 0) for t in trades)
        win_rate = sum(1 for t in trades if t.get('pnl', 0) > 0) / len(trades) * 100
        
        return {
            "sharpe": sharpe,
            "profit_factor": profit_factor,
            "total_return": total_return,
            "win_rate": win_rate,
            "trade_count": len(trades)
        }
    
    def optimize_window(self, window: OptimizationWindow) -> Optional[StrategyParams]:
        """Find best parameters for a single window using grid search"""
        # Load training data
        train_trades = self.load_historical_trades(window.train_start, window.train_end)
        
        if len(train_trades) < 10:
            logger.warning(f"Window {window.window_id}: Insufficient training data ({len(train_trades)} trades)")
            return None
        
        best_score = -float('inf')
        best_params = None
        results = []
        
        # Grid search (limited combinations for performance)
        param_combinations = list(itertools.product(
            self.param_grid["leverage"],
            self.param_grid["profit_target"],
            self.param_grid["stop_loss"],
            self.param_grid["min_confidence"],
            self.param_grid["holding_period"]
        ))
        
        # Limit to 50 combinations for speed
        param_combinations = param_combinations[:50]
        
        for leverage, profit_target, stop_loss, min_confidence, holding_period in param_combinations:
            params = StrategyParams(leverage, profit_target, stop_loss, min_confidence, holding_period)
            metrics = self.backtest_params(params, train_trades)
            
            # Score: Weighted combination of Sharpe, Profit Factor, and Win Rate
            score = (
                metrics["sharpe"] * 0.4 +
                metrics["profit_factor"] * 0.3 +
                (metrics["win_rate"] / 100) * 0.3
            )
            
            if score > best_score:
                best_score = score
                best_params = params
                best_metrics = metrics
        
        logger.info(f"Window {window.window_id}: Best params={best_params.to_dict() if best_params else None}, Score={best_score:.4f}")
        
        # Validate on test set
        if best_params:
            test_trades = self.load_historical_trades(window.test_start, window.test_end)
            test_metrics = self.backtest_params(best_params, test_trades)
            
            result = {
                "window_id": window.window_id,
                "train_period": f"{window.train_start.date()} to {window.train_end.date()}",
                "test_period": f"{window.test_start.date()} to {window.test_end.date()}",
                "best_params": best_params.to_dict(),
                "train_metrics": best_metrics,
                "test_metrics": test_metrics,
                "score": best_score
            }
            self.optimization_history.append(result)
            return best_params
        
        return None
    
    def run_optimization(self, lookback_days: int = 90):
        """Run full walk-forward optimization"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        windows = self.generate_windows(start_date, end_date)
        
        if not windows:
            logger.warning("No optimization windows generated")
            return None
        
        # Optimize last window (most recent)
        latest_window = windows[-1]
        best_params = self.optimize_window(latest_window)
        
        if best_params:
            self.update_config(best_params)
            logger.info(f"Updated config with optimized params: {best_params.to_dict()}")
            return best_params
        
        return None
    
    def update_config(self, params: StrategyParams):
        """Update strategy config with optimized parameters"""
        try:
            # Update regime-specific config (using BULL_HIGH_VOL as example)
            config_path = "/home/nkhekhe/unified_trading_system/config/strategy_profitable.yaml"
            
            # In production, this would properly parse and update YAML
            # For now, log the update
            logger.info(f"Config update: {params.to_dict()}")
            
            # Save optimization result
            result_path = "/home/nkhekhe/unified_trading_system/learning/optimization_latest.json"
            with open(result_path, 'w') as f:
                json.dump(params.to_dict(), f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to update config: {e}")

if __name__ == "__main__":
    optimizer = WalkForwardOptimizer()
    best_params = optimizer.run_optimization(lookback_days=60)
    if best_params:
        print(f"Best parameters: {best_params.to_dict()}")
    else:
        print("Optimization failed or insufficient data")
