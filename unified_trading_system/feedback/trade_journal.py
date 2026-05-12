"""
Trade Journal Module for Trading System
Tracks all trades with full attribution for learning and performance analysis
"""

import numpy as np
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import os
import csv
from collections import defaultdict
import uuid

logger = logging.getLogger(__name__)

class TradeDirection(Enum):
    BUY = "BUY"
    SELL = "SELL"

class TradeOutcome(Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    BREAK_EVEN = "BREAK_EVEN"
    OPEN = "OPEN"

class TradeStatus(Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

@dataclass
class Trade:
    """Complete trade record with all attributes"""
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    symbol: str = ""
    direction: str = ""  # BUY or SELL
    entry_price: float = 0.0
    exit_price: float = 0.0
    quantity: float = 0.0
    entry_time: Optional[float] = None
    exit_time: Optional[float] = None
    status: str = "PENDING"
    pnl: float = 0.0
    pnl_pct: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    
    # Signal attributes
    signal_confidence: float = 0.0
    signal_expected_return: float = 0.0
    signal_regime: str = ""
    signal_strength: float = 0.0
    
    # Execution attributes
    execution_type: str = "MARKET"
    execution_quality: float = 0.0
    fill_latency_ms: float = 0.0
    
    # Market conditions at entry
    market_volatility: float = 0.0
    market_liquidity: float = 0.0
    spread_bps: float = 0.0
    
    # Notes
    notes: str = ""
    tags: List[str] = field(default_factory=list)

class TradeJournal:
    """
    Comprehensive trade journal for tracking and analyzing trading performance
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.trades = []
        self.open_positions = {}
        self.symbol_stats = defaultdict(lambda: {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'max_win': 0.0,
            'max_loss': 0.0,
            'avg_holding_period': 0.0,
        })
        self.regime_stats = defaultdict(lambda: {
            'total_trades': 0,
            'winning_trades': 0,
            'total_pnl': 0.0,
        })
        self.signal_performance = defaultdict(lambda: {
            'trades': 0,
            'total_pnl': 0.0,
            'avg_pnl': 0.0,
        })
        
    def _default_config(self) -> Dict:
        return {
            'max_trades': 10000,
            'save_interval_minutes': 30,
            'enable_auto_save': True,
            'save_path': './logs/trade_journal.json',
            'csv_save_path': './logs/trades.csv',
            'enable_performance_tracking': True,
            'enable_regime_analysis': True,
            'enable_signal_analysis': True,
        }
    
    def open_trade(self, 
                 symbol: str,
                 direction: str,
                 entry_price: float,
                 quantity: float,
                 signal_attributes: Dict,
                 market_conditions: Dict) -> str:
        """
        Open a new trade and return trade ID
        """
        trade = Trade(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            quantity=quantity,
            entry_time=datetime.now().timestamp(),
            status="OPEN",
            signal_confidence=signal_attributes.get('confidence', 0.0),
            signal_expected_return=signal_attributes.get('expected_return', 0.0),
            signal_regime=signal_attributes.get('regime', ''),
            signal_strength=signal_attributes.get('signal_strength', 0.0),
            market_volatility=market_conditions.get('volatility', 0.0),
            market_liquidity=market_conditions.get('liquidity', 0.0),
            spread_bps=market_conditions.get('spread_bps', 0.0),
            execution_type=signal_attributes.get('execution_type', 'MARKET'),
        )
        
        self.trades.append(trade)
        self.open_positions[symbol] = trade
        
        # Update symbol stats
        self.symbol_stats[symbol]['total_trades'] += 1
        
        logger.info(f"Opened trade {trade.trade_id}: {direction} {quantity} {symbol} @ {entry_price}")
        
        return trade.trade_id
    
    def close_trade(self,
                symbol: str,
                exit_price: float,
                exit_time: Optional[float] = None,
                commission: float = 0.0,
                slippage: float = 0.0,
                execution_quality: float = 0.0,
                fill_latency_ms: float = 0.0) -> Optional[str]:
        """
        Close an existing trade
        """
        if symbol not in self.open_positions:
            logger.warning(f"No open position found for {symbol}")
            return None
        
        trade = self.open_positions[symbol]
        trade.exit_price = exit_price
        trade.exit_time = exit_time or datetime.now().timestamp()
        trade.status = "CLOSED"
        trade.commission = commission
        trade.slippage = slippage
        trade.execution_quality = execution_quality
        trade.fill_latency_ms = fill_latency_ms
        
        # Calculate P&L
        if trade.direction == "BUY":
            trade.pnl = (exit_price - trade.entry_price) * trade.quantity - commission - slippage
        else:  # SELL
            trade.pnl = (trade.entry_price - exit_price) * trade.quantity - commission - slippage
        
        # Calculate P&L percentage
        if trade.entry_price > 0:
            trade.pnl_pct = trade.pnl / (trade.entry_price * trade.quantity) * 100
        
        # Update outcome
        if trade.pnl > 0:
            trade.outcome = "WIN"
        elif trade.pnl < 0:
            trade.outcome = "LOSS"
        else:
            trade.outcome = "BREAK_EVEN"
        
        # Update symbol stats
        stats = self.symbol_stats[symbol]
        stats['total_pnl'] += trade.pnl
        if trade.pnl > 0:
            stats['winning_trades'] += 1
            stats['max_win'] = max(stats['max_win'], trade.pnl)
            if stats['avg_win'] == 0:
                stats['avg_win'] = trade.pnl
            else:
                stats['avg_win'] = (stats['avg_win'] * (stats['winning_trades'] - 1) + trade.pnl) / stats['winning_trades']
        else:
            stats['losing_trades'] += 1
            stats['max_loss'] = min(stats['max_loss'], trade.pnl)
            if stats['avg_loss'] == 0:
                stats['avg_loss'] = trade.pnl
            else:
                stats['avg_loss'] = (stats['avg_loss'] * (stats['losing_trades'] - 1) + trade.pnl) / stats['losing_trades']
        
        # Update regime stats
        if self.config['enable_regime_analysis'] and trade.signal_regime:
            regime = trade.signal_regime
            self.regime_stats[regime]['total_trades'] += 1
            self.regime_stats[regime]['total_pnl'] += trade.pnl
            if trade.pnl > 0:
                self.regime_stats[regime]['winning_trades'] += 1
        
        # Update signal performance
        if self.config['enable_signal_analysis']:
            signal_key = f"{trade.direction}_{trade.execution_type}"
            self.signal_performance[signal_key]['trades'] += 1
            self.signal_performance[signal_key]['total_pnl'] += trade.pnl
        
        # Remove from open positions
        del self.open_positions[symbol]
        
        logger.info(f"Closed trade {trade.trade_id}: {symbol} @ {exit_price}, P&L: {trade.pnl:.2f}")
        
        return trade.trade_id
    
    def cancel_trade(self, symbol: str) -> bool:
        """
        Cancel an open trade
        """
        if symbol not in self.open_positions:
            return False
        
        trade = self.open_positions[symbol]
        trade.status = "CANCELLED"
        trade.exit_time = datetime.now().timestamp()
        
        del self.open_positions[symbol]
        
        logger.info(f"Cancelled trade {trade.trade_id}: {symbol}")
        
        return True
    
    def get_performance_summary(self, 
                           start_time: Optional[float] = None,
                           end_time: Optional[float] = None,
                           symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive performance summary
         """
        # Filter trades
        filtered_trades = self.trades.copy()
        
        if start_time:
            filtered_trades = [t for t in filtered_trades if t.entry_time >= start_time]
        if end_time:
            filtered_trades = [t for t in filtered_trades if t.entry_time <= end_time]
        if symbol:
            filtered_trades = [t for t in filtered_trades if t.symbol == symbol]
        
        if not filtered_trades:
            return {
                'total_trades': 0,
                'closed_trades': 0,
                'open_positions': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0,
            }
        
        closed_trades = [t for t in filtered_trades if t.status == "CLOSED"]
        open_trades = [t for t in filtered_trades if t.status == "OPEN"]
        
        if not closed_trades:
            return {
                'total_trades': len(filtered_trades),
                'closed_trades': len(closed_trades),
                'open_positions': len(open_trades),
                'total_pnl': 0.0,
                'win_rate': 0.0,
            }
        
        wins = [t for t in closed_trades if t.pnl > 0]
        losses = [t for t in closed_trades if t.pnl < 0]
        
        total_pnl = sum(t.pnl for t in closed_trades)
        win_rate = len(wins) / len(closed_trades) if closed_trades else 0
        
        # Calculate holding periods
        holding_periods = []
        for t in closed_trades:
            if t.entry_time and t.exit_time:
                holding_periods.append(t.exit_time - t.entry_time)
        
        avg_holding_period = np.mean(holding_periods) / 60 if holding_periods else 0  # Convert to minutes
        
        # Calculate additional metrics
        avg_win = np.mean([t.pnl for t in wins]) if wins else 0
        avg_loss = np.mean([t.pnl for t in losses]) if losses else 0
        max_win = max([t.pnl for t in wins]) if wins else 0
        max_loss = min([t.pnl for t in losses]) if losses else 0
        
        # Risk metrics
        returns = [t.pnl_pct for t in closed_trades]
        if returns:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
            max_drawdown = self._calculate_max_drawdown(closed_trades)
        else:
            sharpe_ratio = 0
            max_drawdown = 0
        
        summary = {
            'total_trades': len(filtered_trades),
            'closed_trades': len(closed_trades),
            'open_positions': len(open_trades),
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_win': max_win,
            'max_loss': max_loss,
            'avg_holding_period_min': avg_holding_period,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0,
            'expectancy': (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss)),
        }
        
        return summary
    
    def get_regime_performance(self) -> Dict[str, Dict]:
        """
        Get performance breakdown by market regime
        """
        return {regime: dict(stats) for regime, stats in self.regime_stats.items()}
    
    def get_signal_performance(self) -> Dict[str, Dict]:
        """
        Get performance breakdown by signal type
        """
        # Calculate average P&L for each signal type
        for signal_key, stats in self.signal_performance.items():
            if stats['trades'] > 0:
                stats['avg_pnl'] = stats['total_pnl'] / stats['trades']
        
        return {signal: dict(stats) for signal, stats in self.signal_performance.items()}
    
    def get_symbol_performance(self, symbol: str) -> Dict[str, Any]:
        """
        Get performance for a specific symbol
        """
        return dict(self.symbol_stats.get(symbol, {}))
    
    def get_trade_by_id(self, trade_id: str) -> Optional[Trade]:
        """
        Find a trade by its ID
        """
        for trade in self.trades:
            if trade.trade_id == trade_id:
                return trade
        return None
    
    def get_open_positions(self) -> Dict[str, Trade]:
        """
        Get all currently open positions
        """
        return self.open_positions.copy()
    
    def get_recent_trades(self, n: int = 10) -> List[Trade]:
        """
        Get the N most recent trades
        """
        # Sort by entry time (most recent first)
        sorted_trades = sorted(self.trades, key=lambda t: t.entry_time or 0, reverse=True)
        return sorted_trades[:n]
    
    def get_best_trades(self, n: int = 10) -> List[Trade]:
        """
        Get the N best trades by P&L
         """
        return sorted(self.trades, key=lambda t: t.pnl, reverse=True)[:n]
    
    def get_worst_trades(self, n: int = 10) -> List[Trade]:
        """
        Get the N worst trades by P&L
        """
        return sorted(self.trades, key=lambda t: t.pnl)[:n]
    
    def _calculate_max_drawdown(self, trades: List[Trade]) -> float:
        """
        Calculate maximum drawdown from trade list
        """
        if not trades:
            return 0.0
        
        # Sort by exit time
        sorted_trades = sorted(trades, key=lambda t: t.exit_time or 0)
        
        cumulative_pnl = 0.0
        peak = 0.0
        max_drawdown = 0.0
        
        for trade in sorted_trades:
            cumulative_pnl += trade.pnl
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            drawdown = peak - cumulative_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown
    
    def save_to_file(self, filepath: Optional[str] = None):
        """
        Save trades to JSON file
        """
        filepath = filepath or self.config['save_path']
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Convert trades to serializable format
        trades_data = []
        for trade in self.trades:
            trade_dict = asdict(trade)
            trades_data.append(trade_dict)
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump({
                'trades': trades_data,
                'summary': self.get_performance_summary(),
                'regime_performance': self.get_regime_performance(),
                'signal_performance': self.get_signal_performance(),
            }, f, indent=2, default=str)
        
        logger.info(f"Saved {len(trades_data)} trades to {filepath}")
    
    def save_to_csv(self, filepath: Optional[str] = None):
        """
        Save trades to CSV file for easier analysis
        """
        filepath = filepath or self.config['csv_save_path']
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        if not self.trades:
            logger.warning("No trades to save")
            return
        
        # Get field names from first trade
        trade_dict = asdict(self.trades[0])
        fieldnames = list(trade_dict.keys())
        
        # Write to CSV
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for trade in self.trades:
                trade_dict = asdict(trade)
                writer.writerow(trade_dict)
        
        logger.info(f"Saved {len(self.trades)} trades to {filepath}")
    
    def load_from_file(self, filepath: str):
        """
        Load trades from JSON file
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File {filepath} not found")
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Restore trades
        self.trades = []
        for trade_dict in data.get('trades', []):
            trade = Trade(**trade_dict)
            self.trades.append(trade)
            if trade.status == "OPEN":
                self.open_positions[trade.symbol] = trade
        
        # Recalculate stats
        self.symbol_stats.clear()
        for trade in self.trades:
            if trade.status == "CLOSED":
                self.symbol_stats[trade.symbol]['total_trades'] += 1
                self.symbol_stats[trade.symbol]['total_pnl'] += trade.pnl
                if trade.pnl > 0:
                    self.symbol_stats[trade.symbol]['winning_trades'] += 1
                else:
                    self.symbol_stats[trade.symbol]['losing_trades'] += 1
        
        logger.info(f"Loaded {len(self.trades)} trades from {filepath}")
    
    def get_attribution_analysis(self) -> Dict[str, Any]:
        """
        Perform attribution analysis to identify what drives performance
        """
        closed_trades = [t for t in self.trades if t.status == "CLOSED"]
        
        if not closed_trades:
            return {'error': 'No closed trades for analysis'}
        
        # Group by different factors
        by_direction = defaultdict(list)
        by_regime = defaultdict(list)
        by_execution_type = defaultdict(list)
        
        for trade in closed_trades:
            by_direction[trade.direction].append(trade)
            by_regime[trade.signal_regime].append(trade)
            by_execution_type[trade.execution_type].append(trade)
        
        # Calculate performance for each group
        def calc_stats(trades_list):
            if not trades_list:
                return {}
            pnls = [t.pnl for t in trades_list]
            return {
                'count': len(trades_list),
                'total_pnl': sum(pnls),
                'avg_pnl': np.mean(pnls),
                'win_rate': len([p for p in pnls if p > 0]) / len(pnls),
            }
        
        attribution = {
            'by_direction': {k: calc_stats(v) for k, v in by_direction.items()},
            'by_regime': {k: calc_stats(v) for k, v in by_regime.items()},
            'by_execution_type': {k: calc_stats(v) for k, v in by_execution_type.items()},
        }
        
        return attribution
    
    def get_learning_insights(self) -> List[Dict]:
        """
        Generate insights for model learning
        """
        insights = []
        
        # Get performance summary
        summary = self.get_performance_summary()
        
        # Generate insights based on performance
        if summary['win_rate'] > 0.6:
            insights.append({
                'type': 'high_win_rate',
                'message': f"High win rate: {summary['win_rate']:.1%}",
                'action': 'Continue current strategy'
            })
        
        if summary['win_rate'] < 0.4:
            insights.append({
                'type': 'low_win_rate',
                'message': f"Win rate below 50%: {summary['win_rate']:.1%}",
                'action': 'Review signal generation'
            })
        
        if summary['sharpe_ratio'] > 2:
            insights.append({
                'type': 'excellent_risk_adjusted',
                'message': f"Strong Sharpe ratio: {summary['sharpe_ratio']:.2f}",
                'action': 'Consider increasing position sizes'
            })
        
        # Regime analysis
        regime_perf = self.get_regime_performance()
        for regime, stats in regime_perf.items():
            if stats['total_trades'] >= 5:
                regime_win_rate = stats['winning_trades'] / stats['total_trades']
                if regime_win_rate > 0.7:
                    insights.append({
                        'type': 'regime_outperformance',
                        'message': f"Strong performance in {regime} regime: {regime_win_rate:.1%} win rate",
                        'action': f'Increase exposure in {regime} regime'
                    })
                elif regime_win_rate < 0.3:
                    insights.append({
                        'type': 'regime_underperformance',
                        'message': f"Weak performance in {regime} regime: {regime_win_rate:.1%} win rate",
                        'action': f'Reduce exposure in {regime} regime'
                    })
        
        return insights

def create_trade_journal(config: Optional[Dict] = None) -> TradeJournal:
    """
    Factory function to create a trade journal
    """
    return TradeJournal(config)