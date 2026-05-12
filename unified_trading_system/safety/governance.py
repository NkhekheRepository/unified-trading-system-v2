"""
Safety and Governance Layer for Trading System
Implements pre-trade risk checks, emergency stops, and audit trails
"""

import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import os
import uuid

logger = logging.getLogger(__name__)

class SafetyStatus(Enum):
    """Safety check status"""
    SAFE = "SAFE"
    WARNING = "WARNING"
    DANGER = "DANGER"
    BLOCKED = "BLOCKED"

class TradingAction(Enum):
    """Trading action types"""
    ALLOW = "ALLOW"
    REDUCE = "REDUCE"
    BLOCK = "BLOCK"
    EMERGENCY_STOP = "EMERGENCY_STOP"

@dataclass
class SafetyCheckResult:
    """Result of safety check"""
    action: str
    status: str
    message: str
    risk_score: float
    violations: List[str] = field(default_factory=list)
    reduction_factor: float = 1.0
    check_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

class AuditEntry:
    """Audit trail entry"""
    def __init__(self, 
                 timestamp: float,
                 event_type: str,
                 details: Dict,
                 status: str,
                 check_id: str = None):
        self.timestamp = timestamp
        self.event_type = event_type
        self.details = details
        self.status = status
        self.check_id = check_id or str(uuid.uuid4())[:8]
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'event_type': self.event_type,
            'details': self.details,
            'status': self.status,
            'check_id': self.check_id
        }

class SafetyGovernor:
    """
    Comprehensive safety and governance system for trading operations
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        
        self.emergency_stop_active = False
        self.max_daily_loss_triggered = False
        self.position_limit_triggered = False
        
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.daily_volume = 0.0
        
        self.audit_log = []
        self.safety_violations = []
        
        self.risk_check_count = 0
        self.blocks_count = 0
        
    def _default_config(self) -> Dict:
        return {
            'max_position_pct': 0.1,           # 10% max position per trade
            'max_portfolio_pct': 0.3,         # 30% max total portfolio
            'max_daily_loss_pct': 0.05,       # 5% max daily loss
            'max_daily_trades': 50,              # 50 max trades per day
            'max_daily_volume': 1000000,         # $1M max daily volume
            'min_trade_interval_seconds': 5,      # 5 second minimum between trades
            'enable_position_checks': True,
            'enable_loss_checks': True,
            'enable_volume_checks': True,
            'enable_correlation_checks': True,
            'block_on_emergency': True,
            'auto_emergency_stop': True,
        }
    
    def check_pre_trade(self, 
                      trade_params: Dict,
                      current_positions: Dict[str, float],
                      portfolio_value: float = 100000) -> SafetyCheckResult:
        """
        Perform comprehensive pre-trade safety checks
        """
        violations = []
        risk_factors = []
        reduction_factor = 1.0
        action = TradingAction.ALLOW.value
        
        if self.emergency_stop_active:
            return SafetyCheckResult(
                action=TradingAction.EMERGENCY_STOP.value,
                status=SafetyStatus.BLOCKED.value,
                message="Emergency stop is active - all trading blocked",
                risk_score=1.0,
                violations=["EMERGENCY_STOP_ACTIVE"],
                reduction_factor=0.0
            )
        
        # Check 1: Position limits
        if self.config['enable_position_checks']:
            position_pct = trade_params.get('quantity', 0) / portfolio_value if portfolio_value > 0 else 0
            
            if position_pct > self.config['max_position_pct']:
                violations.append(f"Position size {position_pct:.2%} exceeds max {self.config['max_position_pct']:.2%}")
                risk_factors.append(position_pct / self.config['max_position_pct'])
            
            # Check total portfolio exposure
            total_exposure = sum(current_positions.values()) / portfolio_value if portfolio_value > 0 else 0
            new_exposure = total_exposure + position_pct
            
            if new_exposure > self.config['max_portfolio_pct']:
                violations.append(f"Total portfolio exposure {new_exposure:.2%} would exceed max {self.config['max_portfolio_pct']:.2%}")
                risk_factors.append(new_exposure / self.config['max_portfolio_pct'])
                # Reduce position to fit
                available_pct = self.config['max_portfolio_pct'] - total_exposure
                reduction_factor = min(1.0, available_pct / position_pct) if position_pct > 0 else 1.0
        
        # Check 2: Daily loss limits
        if self.config['enable_loss_checks']:
            if self.daily_pnl < -self.config['max_daily_loss_pct'] * portfolio_value:
                violations.append(f"Daily loss {abs(self.daily_pnl):.2f} exceeds max {self.config['max_daily_loss_pct'] * portfolio_value:.2f}")
                risk_factors.append(abs(self.daily_pnl) / (self.config['max_daily_loss_pct'] * portfolio_value))
        
        # Check 3: Trade frequency limits
        if self.config.get('enable_frequency_checks', True):
            if self.daily_trades >= self.config['max_daily_trades']:
                violations.append(f"Daily trade count {self.daily_trades} at max {self.config['max_daily_trades']}")
                risk_factors.append(1.0)
        
        # Check 4: Volume limits
        if self.config['enable_volume_checks']:
            trade_value = trade_params.get('quantity', 0) * trade_params.get('price', 0)
            if self.daily_volume + trade_value > self.config['max_daily_volume']:
                violations.append(f"Daily volume would exceed max {self.config['max_daily_volume']}")
                risk_factors.append((self.daily_volume + trade_value) / self.config['max_daily_volume'])
        
        # Check 5: Model confidence
        model_confidence = trade_params.get('signal_confidence', 1.0)
        if model_confidence < 0.3:
            violations.append(f"Low model confidence: {model_confidence:.2f}")
            risk_factors.append((1 - model_confidence))
        
        # Determine action based on violations
        if violations:
            risk_score = max(risk_factors) if risk_factors else 1.0
            
            if risk_score > 0.9:  # High risk
                action = TradingAction.BLOCK.value
                status = SafetyStatus.BLOCKED.value
                message = f"Trade blocked: {violations[0]}"
                self.blocks_count += 1
            elif risk_score > 0.5:  # Medium risk
                action = TradingAction.REDUCE.value
                status = SafetyStatus.WARNING.value
                message = f"Position reduced by factor {reduction_factor:.2f}"
            else:  # Low risk
                action = TradingAction.ALLOW.value
                status = SafetyStatus.WARNING.value
                message = f"Trade allowed with warnings: {', '.join(violations)}"
        
        else:
            # No violations - check risk score for warnings
            risk_score = max(risk_factors) if risk_factors else 0.0
            
            if risk_score > 0:
                status = SafetyStatus.WARNING.value
                message = f"Trade allowed but risk elevated: {risk_score:.2f}"
            else:
                status = SafetyStatus.SAFE.value
                message = "Trade passes all safety checks"
        
        # Log audit entry
        self._add_audit_entry(
            event_type="PRE_TRADE_CHECK",
            details=trade_params,
            status=status
        )
        
        result = SafetyCheckResult(
            action=action,
            status=status,
            message=message,
            risk_score=risk_score if risk_factors else 0.0,
            violations=violations,
            reduction_factor=reduction_factor
        )
        
        self.risk_check_count += 1
        
        return result
    
    def update_daily_stats(self, pnl: float = 0, trades: int = 0, volume: float = 0):
        """
        Update daily statistics
        """
        self.daily_pnl += pnl
        self.daily_trades += trades
        self.daily_volume += volume
        
        # Check if daily loss limit triggered
        if self.daily_pnl < -self.config['max_daily_loss_pct']:
            self.max_daily_loss_triggered = True
            
            if self.config['auto_emergency_stop']:
                self.trigger_emergency_stop("Daily loss limit exceeded")
    
    def reset_daily_stats(self):
        """
        Reset daily statistics (called at start of new trading day)
        """
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.daily_volume = 0.0
        self.max_daily_loss_triggered = False
        self.position_limit_triggered = False
        
        logger.info("Daily statistics reset")
    
    def trigger_emergency_stop(self, reason: str):
        """
        Trigger emergency stop
        """
        self.emergency_stop_active = True
        
        self._add_audit_entry(
            event_type="EMERGENCY_STOP",
            details={'reason': reason},
            status="ACTIVE"
        )
        
        logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
    
    def clear_emergency_stop(self, reason: str = "Manual clear"):
        """
        Clear emergency stop (manual intervention required)
        """
        self.emergency_stop_active = False
        
        self._add_audit_entry(
            event_type="EMERGENCY_STOP_CLEARED",
            details={'reason': reason},
            status="CLEARED"
        )
        
        logger.info(f"Emergency stop cleared: {reason}")
    
    def _add_audit_entry(self, event_type: str, details: Dict, status: str):
        """
        Add entry to audit log
        """
        entry = AuditEntry(
            timestamp=datetime.now().timestamp(),
            event_type=event_type,
            details=details,
            status=status
        )
        
        self.audit_log.append(entry.to_dict())
        
        # Keep only recent entries
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-10000:]
    
    def get_audit_log(self, 
                   event_type: Optional[str] = None,
                   limit: int = 100) -> List[Dict]:
        """
        Get audit log entries
        """
        if event_type:
            filtered = [e for e in self.audit_log if e['event_type'] == event_type]
            return filtered[-limit:]
        
        return self.audit_log[-limit:]
    
    def get_safety_summary(self) -> Dict[str, Any]:
        """
        Get safety system summary
        """
        return {
            'emergency_stop_active': self.emergency_stop_active,
            'max_daily_loss_triggered': self.max_daily_loss_triggered,
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'daily_volume': self.daily_volume,
            'risk_checks_performed': self.risk_check_count,
            'total_blocks': self.blocks_count,
            'recent_violations': self.safety_violations[-10:]
        }
    
    def save_audit_log(self, filepath: str):
        """
        Save audit log to file
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump({
                'audit_log': self.audit_log,
                'safety_summary': self.get_safety_summary()
            }, f, indent=2, default=str)
        
        logger.info(f"Audit log saved to {filepath}")
    
    def load_audit_log(self, filepath: str):
        """
        Load audit log from file
        """
        if not os.path.exists(filepath):
            logger.warning(f"Audit log file {filepath} not found")
            return
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.audit_log = data.get('audit_log', [])
        
        logger.info(f"Audit log loaded from {filepath}")

class ModelSafetyWrapper:
    """
    Safety wrapper for ML model predictions
    """
    
    def __init__(self, base_confidence: float = 0.5, max_leverage: float = 2.0):
        self.base_confidence = base_confidence
        self.max_leverage = max_leverage
        
    def apply_safety_to_prediction(self, 
                               prediction: float, 
                               uncertainty: float,
                               regime: str = None) -> Tuple[float, float]:
        """
        Apply safety adjustments to model prediction
        
        Returns:
            adjusted_prediction: Prediction after safety adjustments
            adjusted_confidence: Confidence after safety adjustments
        """
        # Step 1: Reduce prediction magnitude based on uncertainty
        uncertainty_factor = 1.0 - min(uncertainty, 0.8)  # At most 80% reduction
        
        adjusted_prediction = prediction * uncertainty_factor
        
        # Step 2: Apply confidence floor
        adjusted_confidence = max(self.base_confidence, 1.0 - uncertainty)
        
        # Step 3: Limit leverage in uncertain regimes
        if regime in ['CRISIS', 'BEAR_HIGH_VOL', 'HIGH_VOLATILITY']:
            adjusted_prediction *= 0.5
            adjusted_confidence *= 0.7
        
        return adjusted_prediction, adjusted_confidence
    
    def get_confidence_bounds(self, prediction: float) -> Tuple[float, float]:
        """
        Get confidence interval bounds for prediction
        """
        # Asymmetric bounds based on prediction direction
        if prediction > 0:
            lower = prediction * 0.5
            upper = prediction * 1.5
        else:
            lower = prediction * 1.5
            upper = prediction * 0.5
        
        return lower, upper

def create_safety_governor(config: Optional[Dict] = None) -> SafetyGovernor:
    """
    Factory function to create safety governor
    """
    return SafetyGovernor(config)

def create_model_safety_wrapper(**kwargs) -> ModelSafetyWrapper:
    """
    Factory function to create model safety wrapper
    """
    return ModelSafetyWrapper(**kwargs)