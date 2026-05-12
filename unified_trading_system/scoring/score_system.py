import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logging.basicConfig(
    filename='/home/nkhekhe/unified_trading_system/logs/scoring.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PerformanceScorer:
    """Tracks 70%+ daily profit goal and rates system performance with composite scoring"""
    
    def __init__(self, config_path: str = "/home/nkhekhe/unified_trading_system/scoring/score_config.yaml"):
        self.config = self._load_config(config_path)
        self.trade_journal_path = "/home/nkhekhe/unified_trading_system/trade_journal.json"
        self.score_history: List[Dict] = []
        
    def _load_config(self, config_path: str) -> Dict:
        """Load scoring weights and thresholds"""
        return {
            "weights": {
                "daily_profit": 0.4,      # 40% weight to daily profit target
                "win_rate": 0.2,          # 20% weight to win rate
                "sharpe_ratio": 0.2,      # 20% weight to risk-adjusted returns
                "max_drawdown": 0.2        # 20% penalty weight for drawdown
            },
            "targets": {
                "daily_profit_pct": 70.0,  # 70% daily profit target
                "min_win_rate": 0.6,       # Minimum 60% win rate
                "max_drawdown_pct": 5.0     # Maximum 5% drawdown
            },
            "rating_thresholds": {
                "A+": 90, "A": 80, "B": 70, "C": 60, "D": 40, "F": 0
            }
        }
    
    def load_trades(self, days_back: int = 1) -> List[Dict]:
        """Load recent trades from journal"""
        try:
            with open(self.trade_journal_path, 'r') as f:
                trades = json.load(f)
            cutoff = datetime.now() - timedelta(days=days_back)
            return [t for t in trades if datetime.fromisoformat(t['timestamp']) >= cutoff]
        except Exception as e:
            logger.error(f"Failed to load trades: {e}")
            return []
    
    def calculate_daily_profit_pct(self, trades: List[Dict]) -> float:
        """Calculate daily profit percentage"""
        if not trades:
            return 0.0
        total_profit = sum(t.get('pnl', 0) for t in trades)
        starting_balance = trades[0].get('starting_balance', 1000.0)  # Default if not tracked
        return (total_profit / starting_balance) * 100 if starting_balance > 0 else 0.0
    
    def calculate_win_rate(self, trades: List[Dict]) -> float:
        """Calculate win rate percentage"""
        if not trades:
            return 0.0
        wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
        return (wins / len(trades)) * 100
    
    def calculate_sharpe_ratio(self, trades: List[Dict], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio for trades"""
        if len(trades) < 2:
            return 0.0
        returns = [t.get('pnl_pct', 0) for t in trades]
        avg_return = sum(returns) / len(returns)
        std_dev = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns))
        return (avg_return - risk_free_rate) / std_dev if std_dev > 0 else 0.0
    
    def calculate_max_drawdown(self, trades: List[Dict]) -> float:
        """Calculate maximum drawdown percentage"""
        if not trades:
            return 0.0
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        for t in trades:
            cumulative += t.get('pnl', 0)
            if cumulative > peak:
                peak = cumulative
            dd = (peak - cumulative) / peak * 100 if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        return max_dd
    
    def compute_composite_score(self, daily_profit: float, win_rate: float, 
                               sharpe: float, max_dd: float) -> float:
        """Compute 0-100 composite performance score"""
        weights = self.config["weights"]
        targets = self.config["targets"]
        
        # Daily profit score (capped at 100% of target)
        profit_score = min(daily_profit / targets["daily_profit_pct"], 1.0) * 100
        
        # Win rate score
        win_score = min(win_rate / (targets["min_win_rate"] * 100), 1.0) * 100
        
        # Sharpe score (target Sharpe > 3)
        sharpe_score = min(sharpe / 3.0, 1.0) * 100
        
        # Max drawdown penalty (lower is better)
        dd_penalty = max(0, 100 - (max_dd / targets["max_drawdown_pct"]) * 100)
        
        # Weighted composite
        composite = (
            profit_score * weights["daily_profit"] +
            win_score * weights["win_rate"] +
            sharpe_score * weights["sharpe_ratio"] +
            dd_penalty * weights["max_drawdown"]
        )
        return round(min(composite, 100.0), 2)
    
    def get_rating(self, score: float) -> str:
        """Convert composite score to letter rating"""
        for rating, threshold in sorted(self.config["rating_thresholds"].items(), key=lambda x: -x[1]):
            if score >= threshold:
                return rating
        return "F"
    
    def generate_report(self) -> Dict:
        """Generate full performance report"""
        trades = self.load_trades(days_back=1)
        daily_profit = self.calculate_daily_profit_pct(trades)
        win_rate = self.calculate_win_rate(trades)
        sharpe = self.calculate_sharpe_ratio(trades)
        max_dd = self.calculate_max_drawdown(trades)
        composite = self.compute_composite_score(daily_profit, win_rate, sharpe, max_dd)
        rating = self.get_rating(composite)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "daily_profit_pct": round(daily_profit, 2),
            "target_met": daily_profit >= self.config["targets"]["daily_profit_pct"],
            "win_rate_pct": round(win_rate, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "composite_score": composite,
            "rating": rating,
            "trade_count": len(trades)
        }
        
        logger.info(f"Performance Report: {json.dumps(report)}")
        self.score_history.append(report)
        return report

if __name__ == "__main__":
    scorer = PerformanceScorer()
    report = scorer.generate_report()
    print(json.dumps(report, indent=2))
