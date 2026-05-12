#!/usr/bin/env python3
"""
Position Monitoring and Risk Assessment
Real-time monitoring of portfolio exposure and risk metrics
"""

import json
import os
import sys
import time
from datetime import datetime
from collections import defaultdict
import numpy as np

class PositionMonitor:
    def __init__(self, config_path="/home/nkhekhe/unified_trading_system/config/unified.yaml"):
        self.config_path = config_path
        self.positions = {}
        self.total_exposure = 0
        self.portfolio_value = 0
        self.leverage_usage = 0
        
    def load_positions(self, positions_data):
        """Load positions from JSON data"""
        self.positions = positions_data
        self.total_exposure = sum(float(p.get('notional', 0)) for p in positions_data.values())
        self.portfolio_value = self.total_exposure / self.leverage_usage if self.leverage_usage > 0 else self.total_exposure
        
    def calculate_concentration_risk(self):
        """Calculate position concentration metrics"""
        if not self.positions:
            return {"risk_level": "LOW", "max_concentration": 0}
            
        position_values = [p.get('market_value', 0) for p in self.positions.values()]
        total_value = sum(position_values)
        
        if total_value == 0:
            return {"risk_level": "LOW", "max_concentration": 0}
            
        concentrations = [pv / total_value for pv in position_values]
        max_concentration = max(concentrations)
        
        if max_concentration > 0.5:
            return {"risk_level": "CRITICAL", "max_concentration": max_concentration}
        elif max_concentration > 0.3:
            return {"risk_level": "HIGH", "max_concentration": max_concentration}
        elif max_concentration > 0.2:
            return {"risk_level": "MEDIUM", "max_concentration": max_concentration}
        else:
            return {"risk_level": "LOW", "max_concentration": max_concentration}
            
    def check_risk_limits(self, risk_config):
        """Check if any risk limits are violated"""
        violations = []
        
        max_position_pct = risk_config.get("max_position_pct", 0.1)
        max_portfolio_pct = risk_config.get("max_portfolio_pct", 0.3)
        
        # Check position size limits
        max_position_value = max_position_pct * self.portfolio_value
        for symbol, position in self.positions.items():
            if position.get('market_value', 0) > max_position_value:
                violations.append({
                    "type": "POSITION_SIZE",
                    "symbol": symbol,
                    "value": position.get('market_value', 0),
                    "limit": max_position_value,
                    "message": f"Position {symbol} exceeds size limit"
                })
        
        # Check portfolio exposure limits  
        if self.leverage_usage > 0:
            portfolio_pct = self.total_exposure / self.portfolio_value
            if portfolio_pct > max_portfolio_pct:
                violations.append({
                    "type": "PORTFOLIO_EXP",
                    "value": portfolio_pct,
                    "limit": max_portfolio_pct,
                    "message": f"Portfolio exposure {portfolio_pct:.1%} exceeds limit"
                })
        
        return violations
        
    def monitor_loop(self):
        """Main monitoring loop"""
        print(f"[{datetime.now()}] Position monitoring started")
        
        while True:
            try:
                # Load current positions
                positions_data = self._get_positions()
                self.load_positions(positions_data)
                
                # Calculate metrics
                concentration = self.calculate_concentration_risk()
                violations = self.check_risk_limits()
                
                # Log metrics
                print(f"[{datetime.now()}] Portfolio Value: ${self.portfolio_value:.2f}")
                print(f"[{datetime.now()}] Total Exposure: ${self.total_exposure:.2f}")
                print(f"[{datetime.now()}] Max Concentration: {concentration['max_concentration']:.2%}")
                print(f"[{datetime.now()}] Leverage: {self.leverage_usage:.2f}x")
                
                if violations:
                    print(f"[{datetime.now()}] ALERT: {len(violations)} risk violations detected")
                    for v in violations:
                        print(f"  - {v}")
                
                time.sleep(10)  # Check every 10 seconds
                
            except KeyboardInterrupt:
                print("Monitoring stopped")
                break
            except Exception as e:
                print(f"Error in monitoring: {e}")
                time.sleep(60)  # Retry after 1 minute
                
    def _get_positions(self):
        """Get positions from API or local state"""
        return self.positions

if __name__ == "__main__":
    # Load emergency config
    sys.path.insert(0, "/home/nkhekhe/unified_trading_system")
    from config_manager import ConfigManager
    config_m = ConfigManager()
    config = config_m.get_merged_config()
    
    monitor = PositionMonitor()
    monitor.monitor_loop()