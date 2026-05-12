"""
Trade Journaling System for ML-based Trading
Records trade outcomes and provides data for machine learning model training.
"""

import json
import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class TradeRecord:
    """Detailed record of a single trade for learning purposes"""
    trade_id: str
    symbol: str
    side: str
    entry_time: float
    exit_time: Optional[float] = None
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    quantity: float = 0.0
    predicted_return: float = 0.0
    actual_return: Optional[float] = None
    uncertainty: float = 0.0
    pnl: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "OPEN"  # OPEN, CLOSED, CANCELLED
    
    # Data provenance tracking (Phase 1.2 - 10/10 Upgrade)
    is_synthetic: bool = False  # Flag to distinguish real vs synthetic trades
    data_source: str = "live"  # "live", "testnet", "simulated", "backtest"
    execution_venue: str = "unknown"  # "binance", "binance_testnet", "paper", "simulation"

class TradeJournal:
    """
    Persistent trade journal that records trading events and calculates
    outcomes for ML model training.
    """
    
    def __init__(self, storage_path: str = "logs/trade_journal.json"):
        self.storage_path = storage_path
        self.trades: Dict[str, TradeRecord] = {}
        self._load_journal()

    def _load_journal(self):
        """Load existing journal from disk"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    for tid, record in data.items():
                        self.trades[tid] = TradeRecord(**record)
                logger.info(f"Loaded {len(self.trades)} trades from journal")
            except Exception as e:
                logger.error(f"Failed to load trade journal: {e}")

    def save_journal(self):
        """Save current journal to disk"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump({tid: asdict(r) for tid, r in self.trades.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save trade journal: {e}")

    def record_entry(self, trade_id: str, symbol: str, side: str, quantity: float, 
                     entry_price: float, predicted_return: float, uncertainty: float, 
                     metadata: Optional[Dict] = None):
        """Record the start of a trade"""
        self.trades[trade_id] = TradeRecord(
            trade_id=trade_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            predicted_return=predicted_return,
            uncertainty=uncertainty,
            entry_time=datetime.now(timezone.utc).timestamp(),
            metadata=metadata or {},
            status="OPEN"
        )
        self.save_journal()

    def record_exit(self, trade_id: str, exit_price: float, 
                   metadata: Optional[Dict] = None):
        """Record the exit of a trade and calculate return"""
        if trade_id not in self.trades:
            logger.warning(f"Trade ID {trade_id} not found in journal")
            return

        trade = self.trades[trade_id]
        if trade.status != "OPEN":
            logger.warning(f"Trade {trade_id} is already {trade.status}")
            return

        # Calculate REAL P&L from actual market exit price
        if trade.side == "BUY":
            actual_return = (exit_price - trade.entry_price) / trade.entry_price
        else:  # SELL
            actual_return = (trade.entry_price - exit_price) / trade.entry_price
        
        pnl = actual_return * trade.entry_price * trade.quantity

        trade.exit_price = exit_price
        trade.actual_return = actual_return
        trade.pnl = pnl
        trade.exit_time = datetime.now(timezone.utc).timestamp()
        trade.status = "CLOSED"
        
        if metadata:
            trade.metadata.update(metadata)

        self.save_journal()

    def get_training_data(self, use_synthetic: bool = False) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract completed trades as features (predicted) and targets (actual)
        for model retraining.
        
        Args:
            use_synthetic: If True, include synthetic trades (default: False for clean training)
        
        Returns:
            Tuple of (predictions, targets) as numpy arrays
        """
        # Filter closed trades - by default EXCLUDE synthetic trades for clean training
        if use_synthetic:
            closed_trades = [t for t in self.trades.values() if t.status == "CLOSED"]
        else:
            closed_trades = [t for t in self.trades.values() 
                           if t.status == "CLOSED" and not t.is_synthetic]
        
        if not closed_trades:
            logger.warning(f"No {'synthetic ' if not use_synthetic else ''}closed trades available for training")
            return np.array([]), np.array([])
        
        # Using predicted return as feature and actual return as target
        predictions = np.array([t.predicted_return for t in closed_trades])
        targets = np.array([t.actual_return for t in closed_trades])
        
        logger.info(f"Training data: {len(closed_trades)} trades (synthetic={'allowed' if use_synthetic else 'filtered'})")
        return predictions, targets
    
    def get_data_provenance_summary(self) -> Dict[str, Any]:
        """
        Get summary of data provenance - real vs synthetic trade counts
        """
        closed = [t for t in self.trades.values() if t.status == "CLOSED"]
        real = [t for t in closed if not t.is_synthetic]
        synthetic = [t for t in closed if t.is_synthetic]
        
        real_wins = sum(1 for t in real if t.actual_return and t.actual_return > 0)
        synth_wins = sum(1 for t in synthetic if t.actual_return and t.actual_return > 0)
        
        return {
            "total_closed": len(closed),
            "real_trades": len(real),
            "synthetic_trades": len(synthetic),
            "real_win_rate": real_wins / len(real) if real else 0,
            "synthetic_win_rate": synth_wins / len(synthetic) if synthetic else 0,
            "data_purity": len(real) / len(closed) if closed else 0,
        }

    def get_trade(self, trade_id: str) -> Optional[TradeRecord]:
        """Get a specific trade by ID
        
        Args:
            trade_id: Trade identifier
            
        Returns:
            TradeRecord if found, None otherwise
        """
        return self.trades.get(trade_id)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Calculate journal-level performance metrics"""
        closed_trades = [t for t in self.trades.values() if t.status == "CLOSED"]
        if not closed_trades:
            return {"total_trades": 0}
        
        returns = np.array([t.actual_return for t in closed_trades])
        pnl = np.array([t.pnl for t in closed_trades])
        
        return {
            "total_trades": len(closed_trades),
            "win_rate": np.mean(returns > 0),
            "avg_return": np.mean(returns),
            "total_pnl": np.sum(pnl),
            "sharpe_ratio": np.mean(returns) / np.std(returns) if len(returns) > 1 else 0
        }

    def get_benched_symbols(self, win_rate_threshold: float = 0.60) -> List[str]:
        """Identify symbols with win rate below the required threshold"""
        symbol_stats = {}
        closed_trades = [t for t in self.trades.values() if t.status == "CLOSED"]
        
        for trade in closed_trades:
            sym = trade.symbol
            if sym not in symbol_stats:
                symbol_stats[sym] = {"wins": 0, "total": 0}
            
            symbol_stats[sym]["total"] += 1
            if trade.actual_return > 0:
                symbol_stats[sym]["wins"] += 1
        
        benched = []
        for sym, stats in symbol_stats.items():
            wr = stats["wins"] / stats["total"] if stats["total"] > 0 else 0
            if wr < win_rate_threshold:
                benched.append(sym)
        
        return benched
