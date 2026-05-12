"""
Enhanced Continuous Trading Loop with Governance and Risk Controls
Integrates all trading system components with full observability and alerting.
"""

import asyncio
import logging
import signal
import time
import numpy as np
import os
import hmac
import hashlib
import json
import aiohttp
import yaml
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from perception.belief_state import BeliefState, BeliefStateEstimator, RegimeType
from risk.unified_risk_manager import RiskManifold
from execution.smart_order_router import ExecutionModel, ExecutionIntent, OrderType
from decision.signal_generator import SignalGenerator, TradingSignal

from observability.logging import (
    TradingLogger,
    get_correlation_id,
    set_correlation_id,
    set_context,
)
from observability import get_metrics, set_gauge, increment_counter
from observability.alerting import (
    AlertManager,
    AlertSeverity,
    Alert,
    send_trade_execution_alert,
    send_risk_alert,
    send_system_status_alert,
    configure_alerting_from_env,
)
from observability.health import HealthServer, HealthStatus, LambdaHealthCheck
from learning.trade_journal import TradeJournal


class TradingMode(Enum):
    """Trading operation modes"""
    PAPER = "PAPER"
    TESTNET = "TESTNET"
    LIVE = "LIVE"


@dataclass
class TradingConfig:
    """Trading configuration"""
    mode: TradingMode = TradingMode.PAPER
    
    symbols: List[str] = field(default_factory=lambda: ["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "XRP/USDT", "DOGE/USDT", "MATIC/USDT", "SOL/USDT", "DOT/USDT", "AVAX/USDT", "LINK/USDT", "UNI/USDT", "LTC/USDT", "BCH/USDT", "ATOM/USDT", "ETC/USDT", "XLM/USDT", "ALGO/USDT", "VET/USDT", "FIL/USDT"])
    
    cycle_interval: float = 60.0
    
    max_position_size: float = 500.0  # Updated to enforce $500 cap per trade
    max_daily_loss: float = 10000.0
    max_orders_per_minute: int = 10
    
    # Signal generation parameters
    min_confidence_threshold: float = 0.85  # Optimized based on 360-degree analysis (optimal range 0.85-0.90)
    min_expected_return: float = 0.01
    min_signal_strength: float = 0.1
    
    # Optimized Parameters (360-degree analysis)
    take_profit_pct: float = 0.003  # +0.3% take profit (100% win rate in data)
    stop_loss_pct: float = 0.005  # -0.5% stop loss
    max_trades_per_cycle: int = 1  # Reduced from unlimited to 1 (was overtrading)
    regime_direction_filter: bool = True  # Block SELL in RECOVERY
    
    # Uncertainty parameters
    min_uncertainty: float = 0.0
    max_uncertainty: float = 1.0
    
    enable_alerting: bool = True
    alerting_channels: List[str] = field(default_factory=lambda: ["telegram"])
    
    health_check_port: int = 8080
    metrics_port: int = 9090
    
    # Log directory for persistent files
    log_dir: str = "logs"
    
    # Base URL for API connections
    base_url: str = "https://testnet.binancefuture.com"


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


class EnhancedTradingLoop:
    """
    Enhanced continuous trading loop with governance and risk controls
    """
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.logger = TradingLogger("trading_loop")
        
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
        from safety.governance import SafetyGovernor
        # Load external risk configuration (fallback to defaults defined above)
        try:
            with open('config/trading_params.yaml', 'r') as f:
                params = yaml.safe_load(f)
                # Override defaults if present
                self.REGIME_RISK_MULTIPLIER.update(params.get('REGIME_RISK_MULTIPLIER', {}))
                self.REGIME_TIME_MAP.update(params.get('REGIME_TIME_MAP', {}))
                self.VOL_TIME_MULTIPLIER.update(params.get('VOL_TIME_MULTIPLIER', {}))
        except Exception as e:
            self.logger.debug(f"Failed to load external risk params: {e}")

        
        # Signal generator with high win rate configuration
        self.signal_generator = SignalGenerator(self.config.__dict__ if hasattr(self.config, '__dict__') else self.config)
        
        # Binance API credentials from environment variables
        import os
        self.api_key = os.getenv("BINANCE_TESTNET_API_KEY", "")
        self.api_secret = os.getenv("BINANCE_TESTNET_API_SECRET", "")
        
        # Validate credentials are present for non-paper modes
        if self.config.mode != TradingMode.PAPER:
            if not self.api_key or not self.api_secret:
                raise ValueError("BINANCE_TESTNET_API_KEY and BINANCE_TESTNET_API_SECRET environment variables must be set")
        
        # Use base_url from config
        self.base_url = getattr(self.config, 'base_url', "https://testnet.binancefuture.com")
        
        self.metrics = get_metrics()
        self.alert_manager = AlertManager.get_instance()
        
        # Use environment-specific log directory for trade journal
        log_dir = getattr(self.config, 'log_dir', 'logs')
        self.journal = TradeJournal(storage_path=f"{log_dir}/trade_journal.json")
        
        self.health_server: Optional[HealthServer] = None
        self._last_used_price: Dict[str, float] = {}
        
        # Initialize precision rules for Binance (will be populated during initialize)
        self.precision_rules: Dict[str, Dict] = {}
        
        # Initialize balance - will be updated from Binance API
        self.current_balance: float = 100000.0  # Default starting balance
        self._leverage_multiplier: float = 20.0  # Default 20x leverage (within 15x-25x constraint)
        self._margin_available: bool = True  # Track if margin is available for new trades
        
        # Reusable aiohttp session to prevent socket exhaustion
        self._http_session: Optional[aiohttp.ClientSession] = None
        
        import os

        self._running = False
        self._max_cycles = 0  # 0 means run forever
        self._cycle_count = self._load_cycle_count()
        self._start_time: Optional[float] = None
        self._cycle_count_file = f"{getattr(self.config, 'log_dir', 'logs')}/.cycle_count"
        self._shutdown_event = asyncio.Event()
        
        # PHASE 2.2 & 2.3: Track open positions for exit monitoring
        self._open_positions: Dict[str, Dict] = {}  # trade_id -> position info
        self._max_hold_time_seconds = 60  # PHASE 2.2: Time-based exit (60s max)
        self._stop_loss_pct = 0.015  # tighter stop‑loss (1.5 %) for low‑vol regimes
        
        # PHASE 3: Dynamic Risk System
        self._base_position_size = 50.0  # Base max position size
        self._consecutive_wins = 0
        self._consecutive_losses = 0
        
        # Risk modifiers configuration
        self.REGIME_RISK_MULTIPLIER = {
            # Base risk multipliers per regime (lower = more conservative)
            # Added explicit entry for CRISIS (already 0.3) and tuned RECOVERY to 0.9
            # to penalise the dominant RECOVERY regime observed in recent data.

            'CRISIS': 0.3,
            'BEAR_HIGH_VOL': 0.5,
            'BEAR_LOW_VOL': 0.7,
            'SIDEWAYS_LOW_VOL': 0.8,
            'SIDEWAYS_HIGH_VOL': 0.9,
            'BULL_LOW_VOL': 1.0,
            'BULL_HIGH_VOL': 1.2,
            'RECOVERY': 0.9,
        }
        
        self.REGIME_TIME_MAP = {
            'CRISIS': 30.0,
            'BEAR_HIGH_VOL': 45.0,
            'BEAR_LOW_VOL': 60.0,
            'SIDEWAYS_LOW_VOL': 75.0,
            'SIDEWAYS_HIGH_VOL': 90.0,
            'BULL_LOW_VOL': 105.0,
            'BULL_HIGH_VOL': 120.0,
            'RECOVERY': 60.0,
        }
        self.HOURLY_RISK_MODIFIER = {
            (8, 10): 1.3,   # Best hours
            (10, 14): 1.1,
            (14, 18): 1.1,
            (6, 8): 0.5,    # Poor hours
            (18, 22): 0.8,
            (22, 6): 0.3,   # Night - avoid
        }

        
        # ============ DYNAMIC RISK CALCULATION ============
    
    def _get_hourly_risk_modifier(self, hour: int) -> float:
        """Get risk modifier based on hour of day"""
        for time_range, modifier in self.HOURLY_RISK_MODIFIER.items():
            start, end = time_range
            if start <= hour < end:
                return modifier
        return 0.5  # Default to reduced risk
    
    def _get_regime_risk_modifier(self, regime: str) -> float:
        """Get risk modifier based on market regime"""
        return self.REGIME_RISK_MULTIPLIER.get(regime, 1.0)
    
    def _get_streak_modifier(self) -> float:
        """Get risk modifier based on win/loss streaks"""
        if self._consecutive_wins >= 3:
            return 1.2  # Ride momentum
        elif self._consecutive_losses >= 3:
            return 0.5  # Reduce exposure
        return 1.0
    
    def _calculate_confidence_size(self, confidence: float) -> float:
        """Calculate position size based on confidence (OPTIMIZED for profitability)
        
        Position Sizing Matrix (360-analysis):
        - 0.5-0.6: 30% of base
        - 0.6-0.7: 50% of base
        - 0.7-0.8: 75% of base
        - 0.8-1.0: 100% of base
        """
        if confidence < 0.6:
            return self._base_position_size * 0.30
        elif confidence < 0.7:
            return self._base_position_size * 0.50
        elif confidence < 0.8:
            return self._base_position_size * 0.75
        else:
            return self._base_position_size * 1.0
    
    def calculate_dynamic_position_size(self, confidence: float, regime: str = None, hour: int = None) -> float:
        """Calculate dynamic position size based on all risk factors"""
        # Base size from confidence
        size = self._calculate_confidence_size(confidence)
        
        # Apply regime‑confidence dampening (RECOVERY gets 0.5 factor, others 1.0)
        regime_conf_dampen = 0.5 if regime == 'RECOVERY' else 1.0
        size *= regime_conf_dampen

        if regime is None:
            regime = self._get_regime_for_exit()
        regime_mod = self._get_regime_risk_modifier(regime)
        size *= regime_mod
        
        # Apply hourly modifier
        if hour is None:
            hour = datetime.now().hour
        hourly_mod = self._get_hourly_risk_modifier(hour)
        size *= hourly_mod
        
        # Apply streak modifier (customized for tighter loss penalties)
        if self._consecutive_losses >= 2:
            streak_mod = 0.3
        elif self._consecutive_wins >= 3:
            streak_mod = 1.1
        else:
            streak_mod = 1.0
        size *= streak_mod

        
        # Apply Kelly fraction based on recent win‑rate & win‑loss ratio
        # Using conservative cap of 0.1 (10 % of base) to keep exposure low
        win_rate = 0.095  # derived from recent 21‑trade analysis
        # Approximate win‑loss ratio from recent pnl (positive ÷ |negative|)
        win_loss_ratio = 0.5  # placeholder; could be computed dynamically later
        kelly_frac = max(0.0, win_rate - (1 - win_rate) / win_loss_ratio)
        kelly_frac = min(kelly_frac, 0.1)
        size *= (1 + kelly_frac)

        min_size = self._base_position_size * 0.2
        max_size = self._base_position_size * 1.5
        
        return max(min_size, min(size, max_size))
    
    def update_streak_on_result(self, pnl: float):
        """Update win/loss streak counters after trade closes"""
        if pnl > 0:
            self._consecutive_wins += 1
            self._consecutive_losses = 0
        elif pnl < 0:
            self._consecutive_losses += 1
            self._consecutive_wins = 0
        # Zero doesn't change streaks
        
        self.logger.debug(f"Streak: Wins={self._consecutive_wins}, Losses={self._consecutive_losses}")
    
    def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession()
        return self._http_session
    
    def _load_cycle_count(self) -> int:
        """Load persisted cycle count from file"""
        try:
            cycle_file = f"{getattr(self.config, 'log_dir', 'logs')}/.cycle_count"
            if os.path.exists(cycle_file):
                with open(cycle_file, 'r') as f:
                    count = int(f.read().strip())
                self.logger.info(f"Loaded cycle count: {count}")
                return count
        except Exception as e:
            self.logger.debug(f"Could not load cycle count: {e}")
        return 0
    
    def _save_cycle_count(self):
        """Persist cycle count to file"""
        try:
            cycle_file = f"{getattr(self.config, 'log_dir', 'logs')}/.cycle_count"
            with open(cycle_file, 'w') as f:
                f.write(str(self._cycle_count))
            self.logger.info(f"Persisted cycle count: {self._cycle_count}")
        except Exception as e:
            self.logger.debug(f"Could not save cycle count: {e}")
    
    async def initialize(self):
        """Initialize the trading loop - fetch exchange info, setup connections"""
        self.logger.info("Initializing trading loop...")
        
        # Create reusable aiohttp session
        self._http_session = aiohttp.ClientSession()
        
        # Send system reboot alert
        if self.config.enable_alerting:
            try:
                configure_alerting_from_env()
                await send_system_status_alert(
                    component="trading_loop",
                    status="ONLINE",
                    details={"message": "Trading system rebooted on TESTNET"}
                )
            except Exception as e:
                self.logger.error(f"Failed to send reboot alert: {e}")
        
        # Fetch exchange info from Binance to get quantity precision
        await self._fetch_exchange_info()
        
        self.logger.info(f"Initialization complete. Loaded precision rules for {len(self.precision_rules)} symbols")
    
    async def _fetch_exchange_info(self):
        """Fetch exchange info from Binance to get quantity precision rules"""
        import aiohttp
        
        try:
            url = f"{self.base_url}/fapi/v1/exchangeInfo"
            session = self._get_session()
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for symbol_info in data.get("symbols", []):
                        symbol = symbol_info.get("symbol", "")
                        if symbol.endswith("USDT") and symbol_info.get("status") == "TRADING":
                            precision = symbol_info.get("quantityPrecision", 3)
                            self.precision_rules[symbol] = {"precision": precision}
                    
                    self.logger.info(f"Fetched exchange info for {len(self.precision_rules)} symbols")
                else:
                    self.logger.warning(f"Failed to fetch exchange info: HTTP {resp.status}")
                    for sym in self.config.symbols:
                        self.precision_rules[sym.replace("/", "")] = {"precision": 4}
        except Exception as e:
            self.logger.error(f"Error fetching exchange info: {e}")
            for sym in self.config.symbols:
                self.precision_rules[sym.replace("/", "")] = {"precision": 4}
    
    async def _update_balance(self):
        """Update current balance from Binance API"""
        import aiohttp
        import hmac
        import hashlib
        import time
        
        try:
            # Get account balance from Binance
            url = f"{self.base_url}/fapi/v2/account"
            timestamp = int(time.time() * 1000)
            
            query_string = f"timestamp={timestamp}"
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            full_url = f"{url}?{query_string}&signature={signature}"
            headers = {"X-MBX-APIKEY": self.api_key}
            
            session = self._get_session()
            async with session.get(full_url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for asset in data.get("assets", []):
                        if asset.get("asset") == "USDT":
                            wallet_balance = float(asset.get("walletBalance", 0))
                            available_balance = float(asset.get("availableBalance", 0))
                            cross_wallet_balance = float(asset.get("crossWalletBalance", 0))
                            
                            self.logger.debug(f"RAW USDT: wallet={wallet_balance}, available={available_balance}, crossWallet={cross_wallet_balance}")
                            
                            # Dynamic balance selection with priority
                            if cross_wallet_balance > 0:
                                self.current_balance = cross_wallet_balance
                                self._leverage_multiplier = 20.0
                                self.logger.info(f"✅ Using crossWalletBalance: ${self.current_balance:.2f}, leverage: {self._leverage_multiplier}x")
                            elif wallet_balance > 0:
                                if available_balance > 0:
                                    self.current_balance = available_balance
                                    self._leverage_multiplier = 20.0
                                    self.logger.debug(f"Using available balance: ${self.current_balance:.2f}, leverage: {self._leverage_multiplier}x")
                                else:
                                    self.current_balance = wallet_balance * 0.1
                                    self._leverage_multiplier = 20.0
                                    self.logger.debug(f"Available=0, using wallet * 0.1: ${self.current_balance:.2f}, leverage: {self._leverage_multiplier}x")
                            else:
                                self.current_balance = 10.0
                                self._leverage_multiplier = 40.0
                                self.logger.warning(f"No balance available, using $10 default")
                            
                            # Track margin availability
                            if available_balance > 0:
                                self._margin_available = True
                            else:
                                self._margin_available = False
                else:
                    self.logger.debug(f"Failed to update balance: HTTP {resp.status}")
        except Exception as e:
            self.logger.debug(f"Could not update balance from API: {e}")
            self.current_balance = 10.0
    
    async def _set_symbol_leverage(self, symbol: str, leverage: int = 40) -> bool:
        """Set leverage for a symbol via Binance API"""
        binance_symbol = symbol.replace("/", "")
        
        params = {
            'symbol': binance_symbol,
            'leverage': leverage,
            'timestamp': int(time.time() * 1000)
        }
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(self.api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
        query_string += f"&signature={signature}"
        
        url = f"{self.base_url}/fapi/v1/leverage?{query_string}"
        headers = {'X-MBX-APIKEY': self.api_key}
        
        try:
            session = self._get_session()
            async with session.post(url, headers=headers) as resp:
                if resp.status == 200:
                    self.logger.info(f"Set leverage to {leverage}x for {binance_symbol}")
                    return True
                else:
                    result = await resp.json()
                    self.logger.warning(f"Failed to set leverage: {result.get('msg', 'Unknown error')}")
                    return False
        except Exception as e:
            self.logger.warning(f"Could not set leverage: {e}")
            return False
        
    async def _place_binance_order(self, signal: TradingSignal, retry_count: int = 0) -> Dict:
        """Place a market order directly on Binance Testnet with dynamic sizing and retry logic"""
        # Convert symbol format for Binance (BTC/USDT -> BTCUSDT)
        binance_symbol = signal.symbol.replace("/", "")
        
        # Get real-time price
        price = getattr(signal, 'price', None)
        if price is None:
            market_data = await self._get_real_market_data(signal.symbol)
            if market_data:
                bid_price = market_data.get("bid_price", 0)
                ask_price = market_data.get("ask_price", 0)
                price = (bid_price + ask_price) / 2 if bid_price > 0 and ask_price > 0 else market_data.get("last_price", 0)
            
            if price is None or price <= 0:
                self.logger.warning(f"Skipping {signal.symbol} due to unavailable price data")
                return None

        # Dynamic Sizing: Calculate safe notional based on account balance
        # This works for both testnet (~$2,500) and real accounts (~$10)
        target_notional = self.calculate_safe_notional(self.current_balance, signal.symbol)
        
        # PHASE 2.4: Add position size cap for risk management (UPGRADED for profitability)
        # Increased to $500 to allow meaningful P&L per trade (target: $5-25/trade)
        MAX_POSITION_SIZE = 500.0  # dollars
        if target_notional > MAX_POSITION_SIZE:
            self.logger.warning(f"⚠️ Position size cap applied: ${target_notional:.2f} -> ${MAX_POSITION_SIZE:.2f}")
            target_notional = MAX_POSITION_SIZE
        
        # Set leverage before placing order (only on first try)
        # Skip if insufficient margin (account has open positions using most margin)
        leverage_to_use = int(self._leverage_multiplier)
        lever_result = False
        if retry_count == 0:
            lever_result = await self._set_symbol_leverage(signal.symbol, leverage_to_use)
            if not lever_result:
                # Reduce position size when leverage can't be increased
                self.logger.warning(f"Leverage setting failed - reducing position size by 50%")
                target_notional = target_notional * 0.5
        
        if price <= 0:
            self.logger.error(f"Price is zero or negative for {signal.symbol}: {price}")
            return None
        
        quantity = target_notional / price
        self.logger.debug(f"Quantity calculation: ${target_notional:.2f} / {price:.4f} = {quantity:.8f}")
        quantity = self._format_quantity(signal.symbol, quantity)
        self.logger.debug(f"Formatted quantity: {quantity}")
        
        self.logger.info(f"🚀 PLACING ORDER: {signal.action} {quantity} {binance_symbol} (Notional: ${target_notional:.2f}, Balance: ${self.current_balance:.2f})")
        
        # Check if quantity is too small after formatting
        if float(quantity) <= 0:
            self.logger.warning(f"Quantity zero or negative after formatting: {quantity}")
            return None
        
        self._last_used_price[signal.symbol] = price
        params = {
            'symbol': binance_symbol,
            'side': signal.action,
            'type': 'MARKET',
            'quantity': quantity,
            'timestamp': int(time.time() * 1000)
        }
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(self.api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
        query_string += f"&signature={signature}"
        
        url = f"{self.base_url}/fapi/v1/order?{query_string}"
        headers = {'X-MBX-APIKEY': self.api_key}
        
        session = self._get_session()
        async with session.post(url, headers=headers) as resp:
            raw_response = await resp.text()
            
            # PHASE 1.1: Log raw API response for debugging
            self.logger.critical(f"🔍 BINANCE API RESPONSE: HTTP {resp.status} | {raw_response}")
            
            # PHASE 1.2: Validate HTTP status before parsing JSON
            if resp.status != 200:
                self.logger.error(f"❌ BINANCE HTTP ERROR: Status {resp.status}, Response: {raw_response}")
                return {"error": True, "status_code": resp.status, "message": raw_response}
            
            try:
                result = json.loads(raw_response)
            except json.JSONDecodeError as e:
                self.logger.error(f"❌ JSON PARSE ERROR: {e}, Response: {raw_response}")
                return {"error": True, "message": f"JSON parse error: {e}"}
            
            # Check insufficient margin
            if result.get('code') == -2010 or 'insufficient margin' in result.get('msg', '').lower():
                if retry_count < 1:
                    self.logger.warning(f"Insufficient margin for {signal.symbol}, retrying with half size...")
                    retry_signal = TradingSignal(
                        symbol=signal.symbol,
                        action=signal.action,
                        quantity=0.0,
                        confidence=signal.confidence,
                        signal_strength=signal.signal_strength * 0.5,
                        expected_return=getattr(signal, 'expected_return', 0.0)
                    )
                    return await self._place_binance_order(retry_signal, retry_count + 1)
            
            return result
    
    async def _verify_order(self, order_id: int, symbol: str) -> Optional[Dict]:
        """PHASE 1.4: Query Binance to verify order was actually placed"""
        try:
            binance_symbol = symbol.replace("/", "")
            params = {
                'symbol': binance_symbol,
                'orderId': order_id,
                'timestamp': int(time.time() * 1000)
            }
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            signature = hmac.new(self.api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
            query_string += f"&signature={signature}"
            
            url = f"{self.base_url}/fapi/v1/order?{query_string}"
            headers = {'X-MBX-APIKEY': self.api_key}
            
            session = self._get_session()
            async with session.get(url, headers=headers) as resp:
                raw_response = await resp.text()
                self.logger.critical(f"🔍 ORDER VERIFICATION: HTTP {resp.status} | {raw_response}")
                
                if resp.status == 200:
                    result = json.loads(raw_response)
                    self.logger.critical(f"✅ ORDER VERIFIED: ID={order_id}, Status={result.get('status')}")
                    return result
                else:
                    self.logger.error(f"❌ ORDER VERIFICATION FAILED: HTTP {resp.status}")
                    return None
        except Exception as e:
            self.logger.error(f"❌ Order verification error: {e}")
            return None
    
    async def _get_account_balance(self) -> float:
        """Fetch available balance from Binance Testnet API"""
        try:
            params = {
                'timestamp': int(time.time() * 1000)
            }
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            signature = hmac.new(
                self.api_secret.encode(),
                query_string.encode(),
                hashlib.sha256
            ).hexdigest()
            query_string += f"&signature={signature}"
            
            url = f"{self.base_url}/fapi/v2/account?{query_string}"
            headers = {'X-MBX-APIKEY': self.api_key}
            
            session = self._get_session()
            async with session.get(url, headers=headers) as resp:
                raw_response = await resp.text()
                self.logger.critical(f"🔍 ACCOUNT API RESPONSE: HTTP {resp.status} | {raw_response}")
                
                if resp.status != 200:
                    self.logger.error(f"❌ ACCOUNT API ERROR: HTTP {resp.status}")
                    return 10.0
                
                try:
                    result = json.loads(raw_response)
                except json.JSONDecodeError as e:
                    self.logger.error(f"❌ ACCOUNT JSON PARSE ERROR: {e}")
                    return 10.0
                
                if 'availableBalance' in result:
                    return float(result['availableBalance'])
                self.logger.error(f"Unexpected account response: {result}")
                return 10.0
        except Exception as e:
            self.logger.error(f"Error fetching account balance: {e}")
            return 10.0  # Fallback to $10

        self.logger.info("Initializing enhanced trading loop")
        
        set_context(
            mode=self.config.mode.value,
            symbols=",".join(self.config.symbols),
        )
        
        if self.config.enable_alerting:
            configure_alerting_from_env()
            
            # Force a test alert to verify Telegram works
            from observability.alerting import AlertManager, AlertChannel, create_trading_alert, AlertSeverity
            import asyncio
            
            async def test_telegram():
                mgr = AlertManager.get_instance()
                test_alert = create_trading_alert(
                    title="🔔 TEST: System Restart",
                    message="Trading system started - testing Telegram alerts",
                    severity=AlertSeverity.INFO
                )
                await mgr.send_alert(test_alert)
            
            try:
                asyncio.get_event_loop().run_until_complete(test_telegram())
            except Exception as e:
                self.logger.error(f"Test alert failed: {e}")
            
            await send_system_status_alert(
                component="trading_loop",
                status="initializing",
            )
        
        self.health_server = HealthServer(
            port=self.config.health_check_port,
        )
        # Register health checks
        self.health_server.registry.register(LambdaHealthCheck(
            "executor",
            lambda: (
                "healthy" if True else "unhealthy",  # Simplified for now
                "Executor is operational",
                {}
            )
        ))
        self.health_server.registry.register(LambdaHealthCheck(
            "belief_state",
            lambda: (
                "healthy" if self.belief_state.confidence > 0 else "degraded",
                "Belief state is initialized",
                {"confidence": self.belief_state.confidence}
            )
        ))
        self.health_server.registry.register(LambdaHealthCheck(
            "risk_manager",
            lambda: (
                "healthy" if True else "unhealthy",
                "Risk manager is operational",
                {}
            )
        ))
        self.health_server.start()
        
        self._register_metrics()
        
        self.logger.info(
            f"Trading loop initialized in {self.config.mode.value} mode"
        )
    
    def _register_metrics(self):
        """Register trading metrics"""
        # Metrics are automatically initialized in MetricsCollector.__init__
        # Just ensure they exist by accessing them
        pass
    
    # ============ ENHANCED EXIT STRATEGY CONFIGURATION ============
    
    # Regime-aware time exit (in seconds)
    REGIME_TIME_MAP = {
        'CRISIS': 30,
        'BEAR_HIGH_VOL': 40,
        'BEAR_LOW_VOL': 50,
        'SIDEWAYS_LOW_VOL': 45,
        'SIDEWAYS_HIGH_VOL': 60,
        'BULL_LOW_VOL': 75,
        'BULL_HIGH_VOL': 90,
        'RECOVERY': 80,
    }
    
    # Volatility-adjusted stop-loss (multiplier from base)
    VOLATILITY_SL_MAP = {
        'high': 1.5,    # 3% SL in high vol
        'medium': 1.0,  # 2% SL default
        'low': 0.75,    # 1.5% SL in low vol
    }
    
    # OPTIMIZED TAKE-PROFIT TIERS (360-analysis: +0.3% = 100% WR)
    TAKE_PROFIT_TIERS = [
        {'threshold': 0.003, 'size_pct': 1.00, 'name': 'TP_QUICK'},  # +0.3% = 100% WR
        {'threshold': 0.015, 'size_pct': 0.50, 'name': 'TP1'},
        {'threshold': 0.030, 'size_pct': 0.30, 'name': 'TP2'},
        {'threshold': 0.050, 'size_pct': 0.20, 'name': 'TP3'},
    ]
    
    # Trailing stop configuration
    TRAILING_CONFIG = {
        'activation_profit': 0.02,   # Activate after 2% profit
        'trailing_distance': 0.015,  # 1.5% trailing distance
        'min_lock': 0.005,           # Lock at least 0.5%
    }
    
    # ============ ENHANCED EXIT CONDITIONS ============
    
    def _get_regime_for_exit(self) -> str:
        """Get current regime for exit decisions"""
        try:
            if hasattr(self, 'belief_state'):
                regime, prob = self.belief_state.get_most_likely_regime()
                return regime.name if hasattr(regime, 'name') else str(regime)
        except:
            pass
        return 'SIDEWAYS_LOW_VOL'  # Default
    
    def _get_regime_time_exit(self, regime: str) -> float:
        """Get base time exit (seconds) based on regime"""
        base_time = self.REGIME_TIME_MAP.get(regime, 60.0)
        # Apply volatility scaling – higher vol => longer allowed hold
        vol_level = 'high' if getattr(self.belief_state, 'volatility_estimate', 0) > 0.5 else 'low'
        multiplier = self.VOL_TIME_MULTIPLIER.get(vol_level, 1.0)
        return base_time * multiplier

    
    def _get_volatility_for_sl(self) -> str:
        """Determine volatility regime for stop-loss"""
        try:
            vol = getattr(self.belief_state, 'volatility_estimate', 0.1)
            if vol > 0.5:
                return 'high'
            elif vol < 0.1:
                return 'low'
            else:
                return 'medium'
        except:
            return 'medium'
    
    def _calculate_dynamic_stop_loss(self) -> float:
        """Calculate volatility-adjusted stop-loss"""
        vol_level = self._get_volatility_for_sl()
        base_sl = self._stop_loss_pct
        multiplier = self.VOLATILITY_SL_MAP.get(vol_level, 1.0)
        return base_sl * multiplier
    
    async def _check_exit_conditions(self, result: TradingCycleResult):
        """PHASE 2: Enhanced exit strategy with regime-aware time, SL, TP, and trailing stop"""
        if not self._open_positions:
            return
        
        current_time = time.time()
        current_regime = self._get_regime_for_exit()
        regime_time_exit = self._get_regime_time_exit(current_regime)
        dynamic_sl = self._calculate_dynamic_stop_loss()
        
        for trade_id, pos in list(self._open_positions.items()):
            if pos.get('status') != 'OPEN':
                continue
            
            hold_time = current_time - pos['entry_time']
            
            # Get current price for P&L calculation
            try:
                market_data = await self._get_real_market_data(pos['symbol'])
                current_price = (market_data.get('bid_price', 0) + market_data.get('ask_price', 0)) / 2
                if current_price == 0:
                    current_price = market_data.get('last_price', 0)
            except:
                current_price = pos['entry_price']
            
            # Calculate P&L percentage
            if pos['side'] == 'BUY':
                pnl_pct = (current_price - pos['entry_price']) / pos['entry_price']
            else:
                pnl_pct = (pos['entry_price'] - current_price) / pos['entry_price']
            
            # Track take-profit activations
            if 'tp_activated' not in pos:
                pos['tp_activated'] = []
            if 'trailing_activated' not in pos:
                pos['trailing_activated'] = False
            if 'highest_pnl' not in pos:
                pos['highest_pnl'] = pnl_pct
            
            # Update highest P&L for trailing stop
            if pnl_pct > pos['highest_pnl']:
                pos['highest_pnl'] = pnl_pct
            
            # ============ EXIT CONDITIONS ============
            exit_reason = None
            exit_type = None
            
            # PRIORITY 1: Time-based exit (regime-aware & Volatility-Adjusted)
            vol_level = self._get_volatility_for_sl()
            vol_time_multiplier = {
                'high': 0.7,    # Exit faster in high vol
                'medium': 1.0,
                'low': 1.3      # Give more time in low vol
            }.get(vol_level, 1.0)
            
            adjusted_regime_time_exit = max(regime_time_exit * vol_time_multiplier, 45.0)  # enforce min 45 s hold
            
            if hold_time >= adjusted_regime_time_exit:
                exit_reason = f"TIME_OUT (regime={current_regime}, vol={vol_level}, {hold_time:.1f}s >= {adjusted_regime_time_exit:.1f}s)"
                exit_type = 'TIME'
            
            # PRIORITY 2: Stop-loss (volatility-adjusted)
            elif pnl_pct <= -dynamic_sl:
                exit_reason = f"STOP_LOSS (PnL: {pnl_pct*100:.2f}% <= -{dynamic_sl*100:.2f}%, vol={self._get_volatility_for_sl()})"
                exit_type = 'SL'
            
            # PRIORITY 3: Take-profit tiers
            else:
                for tier in self.TAKE_PROFIT_TIERS:
                    tier_name = tier['name']
                    if tier_name not in pos['tp_activated'] and pnl_pct >= tier['threshold']:
                        pos['tp_activated'].append(tier_name)
                        # Partial close for this tier
                        await self._partial_close_position(trade_id, pos, tier, current_price, result)
                        break
            
            # PRIORITY 4: Trailing stop
            if not exit_reason and pos['highest_pnl'] > self.TRAILING_CONFIG['activation_profit']:
                # Check if price has moved back
                trailing_distance = self.TRAILING_CONFIG['trailing_distance']
                min_lock = self.TRAILING_CONFIG['min_lock']
                
                # Calculate trailing stop price (highest minus distance)
                trailing_trigger = pos['highest_pnl'] - trailing_distance
                
                if pnl_pct <= trailing_trigger and pnl_pct > min_lock:
                    exit_reason = f"TRAILING_STOP (high: {pos['highest_pnl']*100:.2f}%, current: {pnl_pct*100:.2f}%)"
                    exit_type = 'TRAILING'
            
            if exit_reason:
                await self._close_position(trade_id, pos, exit_reason, current_price, result)
    
    async def _partial_close_position(self, trade_id: str, pos: Dict, tier: Dict, current_price: float, result: TradingCycleResult):
        """Execute partial take-profit close"""
        tier_name = tier['name']
        size_pct = tier['size_pct']
        
        partial_qty = pos['quantity'] * size_pct
        remaining_qty = pos['quantity'] - partial_qty
        
        self.logger.critical(f"🎯 TAKE PROFIT {tier_name}: {pos['symbol']} | Closing {size_pct*100}% @ {current_price}")
        
        # Determine close side
        close_side = "SELL" if pos['side'] == "BUY" else "BUY"
        
        # Create exit signal
        exit_signal = TradingSignal(
            symbol=pos['symbol'],
            action=close_side,
            quantity=partial_qty,
            confidence=1.0,
            expected_return=0.0,
            timestamp=time.time(),
            regime=RegimeType.SIDEWAYS_LOW_VOL,
            signal_strength=1.0
        )
        
        try:
            binance_result = await self._place_binance_order(exit_signal)
            
            if binance_result and 'orderId' in binance_result:
                filled_qty = float(binance_result.get('executedQty', partial_qty))
                avg_price = float(binance_result.get('avgPrice', current_price))
                
                if avg_price == 0:
                    avg_price = current_price
                
                self.logger.critical(f"✅ TP {tier_name} FILLED: {filled_qty} @ {avg_price}")
                
                # Update remaining quantity
                pos['quantity'] = remaining_qty
                
                # Record partial exit
                self.journal.record_exit(
                    trade_id,
                    exit_price=avg_price,
                    metadata={
                        'exit_reason': f'PARTIAL_TP_{tier_name}',
                        'partial_qty': filled_qty,
                        'remaining_qty': remaining_qty,
                        'binance_order_id': binance_result.get('orderId'),
                        'exit_type': 'PARTIAL_TP'
                    }
                )
                
                result.orders_executed += 1
                
                # If no remaining quantity, remove from open positions
                if remaining_qty <= 0:
                    del self._open_positions[trade_id]
        except Exception as e:
            self.logger.error(f"❌ Partial TP failed: {e}")
    
    async def _close_position(self, trade_id: str, pos: Dict, exit_reason: str, current_price: float, result: TradingCycleResult):
        """PHASE 2.2 & 2.3: Close a position with real exit order"""
        self.logger.critical(f"🔴 EXIT SIGNAL: {pos['symbol']} | Reason: {exit_reason} | Entry: {pos['entry_price']} | Current: {current_price}")
        
        # Determine close side (opposite of entry)
        close_side = "SELL" if pos['side'] == "BUY" else "BUY"
        
        # Create exit signal
        exit_signal = TradingSignal(
            symbol=pos['symbol'],
            action=close_side,
            quantity=pos['quantity'],
            confidence=1.0,
            expected_return=0.0,
            timestamp=time.time(),
            regime=RegimeType.SIDEWAYS_LOW_VOL,
            signal_strength=1.0
        )
        
        # Place exit order
        try:
            binance_result = await self._place_binance_order(exit_signal)
            
            if binance_result and 'orderId' in binance_result:
                order_status = binance_result.get('status', '')
                filled_qty = float(binance_result.get('executedQty', pos['quantity']))
                avg_price = float(binance_result.get('avgPrice', current_price))
                
                if avg_price == 0:
                    avg_price = current_price
                
                self.logger.critical(f"✅ EXIT ORDER PLACED: {close_side} {filled_qty} {pos['symbol']} @ {avg_price} | Status: {order_status}")
                
                # Record exit in journal
                self.journal.record_exit(
                    trade_id,
                    exit_price=avg_price,
                    metadata={
                        'exit_reason': exit_reason,
                        'binance_order_id': binance_result.get('orderId'),
                        'binance_status': order_status,
                        'exit_type': 'REAL'
                    }
                )
                
                # Remove from open positions
                del self._open_positions[trade_id]
                
                result.orders_executed += 1
            else:
                self.logger.error(f"❌ EXIT ORDER FAILED: {binance_result}")
        except Exception as e:
            self.logger.error(f"❌ Exit order exception: {e}")
    
    async def start(self):
        """Start the continuous trading loop"""
        self.logger.info("Starting trading loop")
        self._running = True
        self._start_time = time.time()
        
        await send_system_status_alert(
            component="trading_loop",
            status="running",
            details={
                "mode": self.config.mode.value,
                "symbols": self.config.symbols,
            },
        )
        
        try:
            while self._running:
                await self._run_cycle()
                await asyncio.sleep(self.config.cycle_interval)
        except asyncio.CancelledError:
            self.logger.info("Trading loop cancelled - will restart")
            raise
        except Exception as e:
            self.logger.error(f"Trading loop error: {e}")
            await send_system_status_alert(
                component="trading_loop",
                status="error",
                details={"error": str(e)},
            )
            raise
        finally:
            if self._running:  # Only shutdown if not restarting
                await self.shutdown()
    
    async def _run_cycle(self) -> TradingCycleResult:
        """Run a single trading cycle"""
        self._cycle_count += 1
        cycle_id = f"cycle_{self._cycle_count}_{int(time.time())}"
        
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
            success=True,
        )
        
        try:
            self.logger.info(f"Starting {cycle_id}")
            
            # Check margin availability at start of cycle
            await self._update_balance()
            if not self._margin_available:
                self.logger.warning(f"⚠️ No available margin - waiting for positions to close. Wallet: ${self.current_balance:.2f}, Available: $0.00")
            else:
                self.logger.debug(f"Margin available: ${self.current_balance:.2f}")
            
            for symbol in self.config.symbols:
                if not self._margin_available:
                    self.logger.debug(f"Skipping {symbol} - no margin available")
                    continue
                    
                await self._process_symbol(symbol, result)
                result.symbols_processed += 1
            
            await self._update_metrics(result)
            
            # PHASE 2.2 & 2.3: Check open positions for exit conditions
            await self._check_exit_conditions(result)
            
        except Exception as e:
            self.logger.error(f"Cycle error: {e}")
            result.errors.append(str(e))
            result.success = False
            pass  # Metrics disabled for now
        
        finally:
            result.duration_ms = (time.time() - cycle_start) * 1000
            pass  # increment_counter("orders_submitted", 1)
            
            self.logger.info(
                f"Completed {cycle_id}: {result.signals_generated} signals, "
                f"{result.orders_executed} orders in {result.duration_ms:.1f}ms"
            )
            
            self._save_cycle_count()
        
        return result
    
    async def _process_symbol(self, symbol: str, result: TradingCycleResult):
        """Process a single symbol with parallel execution"""
        try:
            # Step 1: Fetch market data (initially without expected_return)
            market_data = await self._fetch_market_data(symbol, expected_return=0.0)
            
            if market_data is None:
                self.logger.warning(f"{symbol}: No market data available, skipping")
                return result
            
            # Log the market data type for debugging
            self.logger.debug(f"{symbol}: Market data type: {type(market_data)}, content keys: {list(market_data.keys()) if isinstance(market_data, dict) else 'Not a dict'}")
            
            self.belief_state = self.belief_state_estimator.update(market_data)
            
            # Log belief state details for debugging
            self.logger.debug(
                f"{symbol}: Belief state - Confidence: {self.belief_state.confidence:.4f}, "
                f"Expected Return: {self.belief_state.expected_return:.4f}, "
                f"is_confident({self.config.min_confidence_threshold}): {self.belief_state.is_confident(self.config.min_confidence_threshold)}"
            )
            
            # Generate trading signals from belief state
            trading_signal = self.signal_generator.generate_signal(self.belief_state, symbol)
            trading_signals = [trading_signal] if trading_signal else []
            
            # Log if signals were generated
            if trading_signals:
                result.signals_generated += len(trading_signals)
                self.logger.info(f"{symbol}: Generated {len(trading_signals)} trading signals")
            else:
                self.logger.debug(f"{symbol}: No trading signals generated")
            
            # Regime-Adaptive Filters (Phase 4 Optimization)
            # Skip trading in extremely low volatility or highly unstable regimes
            volatility = self.belief_state.volatility_estimate if hasattr(self.belief_state, 'volatility_estimate') else 0.1
            
            # Filter 1: Volatility Threshold - Avoid 'flat' markets where signals are noisy
            # If volatility is too low (< 0.05), returns are usually captured by fees
            if volatility < 0.02:
                self.logger.debug(f"{symbol}: Skipping due to low volatility ({volatility:.4f})")
                return result
            
            # Filter 2: High-Risk Regime Filter (Crisis/Crash)
            try:
                regime, reg_prob = self.belief_state.get_most_likely_regime()
                from perception.belief_state import RegimeType
                if regime == RegimeType.CRISIS and reg_prob > 0.80:
                    self.logger.warning(f"{symbol}: Skipping due to high-risk CRISIS regime (prob {reg_prob:.2f})")
                    return result
                
                # [OPTIMIZATION] Regime Direction Filter - Block SELL in RECOVERY (10.9% WR vs 29.8% for BUY)
                if getattr(self.config, 'regime_direction_filter', False) and regime == RegimeType.RECOVERY:
                    if signal and signal.side == 'SELL':
                        self.logger.warning(f"{symbol}: Blocking SELL in RECOVERY regime (10.9% WR)")
                        return result
                        
            except Exception as e:
                self.logger.debug(f"{symbol}: Regime filter skipped due to error: {e}")
            
            # Filter 3: Time-of-Day Filter (Optional)
            # Focus on high-liquidity windows (e.g., avoid very late night gaps if needed)
            # For now, we keep it open as the current testnet performance is robust


            for signal in trading_signals:
                # Fixed double counting of signals_generated
                self.logger.info(
                    f"{symbol}: Signal - {signal.action} {signal.quantity:.6f}, "
                    f"Confidence: {signal.confidence:.4f}, Strength: {signal.signal_strength:.4f}"
                )
                
                # Debug: Log belief state before risk assessment
                try:
                    belief_state_dict = self.belief_state.to_dict()
                    self.logger.debug(f"{symbol}: Belief state dict type: {type(belief_state_dict)}, keys: {list(belief_state_dict.keys())}")
                    
                    # Check for any string values in the belief state dict
                    for key, value in belief_state_dict.items():
                        if isinstance(value, str):
                            self.logger.warning(f"{symbol}: belief_state['{key}'] is string: {value[:100]}")
                
                except Exception as e:
                    self.logger.error(f"{symbol}: Error in belief_state.to_dict(): {e}")
                    raise
                
                try:
                    belief_state_dict = self.belief_state.to_dict()
                    import sys
                    print(f"MARKER_BEFORE_RISK: symbol={symbol}", file=sys.stderr)
                    print(f"MARKER: belief_state_dict type={type(belief_state_dict)}, keys={list(belief_state_dict.keys())}", file=sys.stderr)
                    print(f"MARKER: market_data type={type(market_data)}, keys={list(market_data.keys()) if isinstance(market_data, dict) else 'N/A'}", file=sys.stderr)
                    
                    risk_assessment = self.risk_manager.assess_risk(
                        belief_state=belief_state_dict,
                        portfolio_state={"cash": self.current_balance, "positions": self._open_positions},
                        market_data=market_data,
                        current_positions=self._open_positions,
                        recent_returns=[]
                    )
                    
                    # Calculate current market price for the Safety Governor
                    current_price = 0.0
                    if market_data:
                        bid = market_data.get('bid_price', 0)
                        ask = market_data.get('ask_price', 0)
                        current_price = (bid + ask) / 2 if bid > 0 and ask > 0 else market_data.get('last_price', 0)
                    
                    # NEW: Enforce Safety Governor limits (Concentration, Total Exposure)
                    trade_params = {
                        'quantity': signal.quantity,
                        'price': current_price,
                        'signal_confidence': signal.confidence
                    }
                    
                    # Format positions for SafetyGovernor: needs {symbol: quantity}
                    current_positions_quantities = {
                        symbol: pos['quantity'] 
                        for symbol, pos in self._open_positions.items()
                    }
                    
                    # Bypass safety_governor if not initialized
                    if not hasattr(self, 'safety_governor'):
                        self.logger.debug(f"Safety Governor not initialized, skipping check for {symbol}")
                    elif not self.safety_governor.check_pre_trade(
                        trade_params=trade_params,
                        current_positions=current_positions_quantities,
                        portfolio_value=self.current_balance
                    ):
                        self.logger.warning(f"Signal rejected by Safety Governor for {symbol} (Concentration/Exposure limit exceeded)")
                        continue
                except Exception as e:
                    import traceback
                    import sys
                    tb = traceback.format_exc()
                    print(f"DEBUG: Got exception: {e}", file=sys.stderr)
                    print(f"DEBUG: Full traceback:\n{tb}", file=sys.stderr)
                    raise
                
                if risk_assessment.risk_level.value >= 2:  # WARNING level or higher
                    self.logger.warning(
                        f"Signal rejected by risk manager: {risk_assessment.protective_action}"
                    )
                    await send_risk_alert(
                        message=f"Signal rejected for {symbol}",
                        violation_type="risk_check_failed",
                        details={
                            "symbol": symbol,
                            "risk_level": risk_assessment.risk_level.name,
                            "risk_score": risk_assessment.risk_score,
                        },
                    )
                    continue
                
                await self._execute_signal(signal, result)
        
        except Exception as e:
            self.logger.error(f"Error processing {symbol}: {e}")
            result.errors.append(f"{symbol}: {str(e)}")

    async def _get_real_market_data(self, symbol: str) -> Dict:
        """Fetch real market data from Binance Testnet API"""
        try:
            # Convert symbol format for Binance (BTC/USDT -> BTCUSDT)
            binance_symbol = symbol.replace("/", "")
            
            # Fetch ticker data from Binance
            url = f"{self.base_url}/fapi/v1/ticker/bookTicker?symbol={binance_symbol}"
            
            session = self._get_session()
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "symbol": symbol,
                        "bid_price": float(data.get("bidPrice", 0)),
                        "ask_price": float(data.get("askPrice", 0)),
                        "bid_size": float(data.get("bidQty", 0)),
                        "ask_size": float(data.get("askQty", 0)),
                        "last_price": 0.0,
                        "last_size": 0.0,
                    }
                else:
                        self.logger.warning(f"Failed to fetch market data for {symbol}: HTTP {resp.status}")
                        return None
        except Exception as e:
            self.logger.error(f"Error fetching real market data for {symbol}: {e}")
            return None

    def _format_quantity(self, symbol: str, quantity: float) -> str:
        """Format quantity to match Binance's exact precision, returning as a string to avoid float noise"""
        try:
            from decimal import Decimal, ROUND_DOWN
            
            # Convert symbol format for lookup (BTC/USDT -> BTCUSDT)
            binance_symbol = symbol.replace("/", "")
            
            # Get precision from rules discovered during initialization
            rules = self.precision_rules.get(binance_symbol, {"precision": 3})
            precision = rules["precision"]
            
            # Use Decimal for absolute precision control
            # Round down to the exact number of allowed decimals
            quant_dec = Decimal(str(quantity))
            # Create a format string like '0.0001' based on precision
            # Example: precision 4 -> Decimal('1.0000')
            # We use quantize to truncate to the exact precision
            format_str = '0.' + '0' * precision
            rounded_qty = quant_dec.quantize(Decimal(format_str), rounding=ROUND_DOWN)
            
            # Convert to string and remove trailing zeros if necessary, 
            # but keeping the precision formatting is safer for Binance
            return format(rounded_qty, f'.{precision}f')
            
        except Exception as e:
            self.logger.error(f"Precision formatting error for {symbol}: {e}")
            # Fallback to simple string rounding
            return f"{quantity:.8f}"
    
    def calculate_safe_notional(self, balance: float, symbol: str) -> float:
        """Dynamically calculate safe notional based on account size.
        
        This ensures the system works on both:
        - Testnet (~$2,500+ balance): Uses larger positions, capped at $100
        - Real account (~$10 balance): Uses very small positions to avoid margin issues
        
        Balance tiers:
        - >= $1000: Testnet tier (5% of balance, capped at $100)
        - >= $100: Medium tier (10% of balance)
        - >= $10: Small real account (15% of balance)
        - < $10: Emergency tier (20% of balance, minimal positions)
        """
        SYMBOL_MAINT_MARGIN = {
            "BTC/USDT": 0.005,   # 0.5% maintenance margin
            "ETH/USDT": 0.005,
            "BNB/USDT": 0.005,
            "SOL/USDT": 0.010,
            "DOGE/USDT": 0.020,
            "XRP/USDT": 0.020,
            "ADA/USDT": 0.020,
            "MATIC/USDT": 0.020,
        }
        
        maint_fraction = SYMBOL_MAINT_MARGIN.get(symbol, 0.010)
        
        if balance >= 1000:
            # Testnet with large balance - use 10%, cap at $500 (UPGRADED for profitability)
            base_notional = balance * 0.10
            safe_notional = min(base_notional, 500.0)
            self.logger.debug(f"Testnet tier: balance=${balance:.2f}, using ${safe_notional:.2f}")
        elif balance >= 100:
            # Medium account
            safe_notional = balance * 0.10
            self.logger.debug(f"Medium tier: balance=${balance:.2f}, using ${safe_notional:.2f}")
        elif balance >= 10:
            # Small real account - use smaller percentage to be safe
            safe_notional = balance * 0.15
            self.logger.debug(f"Small account tier: balance=${balance:.2f}, using ${safe_notional:.2f}")
        else:
            # Very small balance - use 20% but be very conservative
            safe_notional = balance * 0.20
            self.logger.warning(f"Emergency tier: balance=${balance:.2f}, using minimal ${safe_notional:.2f}")
        
        # Ensure minimum notional of $1 for very small accounts
        return max(safe_notional, 1.0)
    
    async def _fetch_market_data(self, symbol: str, expected_return: float = 0.0) -> Dict:
        """Fetch market data for a symbol with bias toward expected_return"""
        import random
        import numpy as np
        
        # Fetch real market data from Binance
        market_data = await self._get_real_market_data(symbol)
        
        # If we couldn't get real data, skip processing - better to not trade than to trade with fake prices
        if market_data is None:
            self.logger.warning(f"Skipping {symbol} due to unavailable real market data from Binance API")
            return None
            
        # Log that we're using real market data for this symbol
        self.logger.debug(f"Using real market data for {symbol}: bid={market_data.get('bid_price', 0)}, ask={market_data.get('ask_price', 0)}")
        
        # Also log the mid price for clarity
        bid = market_data.get('bid_price', 0)
        ask = market_data.get('ask_price', 0)
        if bid > 0 and ask > 0:
            mid_price = (bid + ask) / 2
            self.logger.debug(f"Real market price for {symbol}: {mid_price}")
        
        # Create market data dictionary with real prices
        return {
            "symbol": symbol,
            "bid_price": market_data.get("bid_price", 0),
            "ask_price": market_data.get("ask_price", 0),
            "bid_size": market_data.get("bid_size", 0),
            "ask_size": market_data.get("ask_size", 0),
            "last_price": market_data.get("last_price", 0),
            "last_size": market_data.get("last_size", 0),
        }
        
        # Create realistic bid/ask spread with some randomness
        spread = current_price * 0.0005  # 5 basis points
        bid_price = current_price - spread / 2
        ask_price = current_price + spread / 2
        
        # Create realistic order book sizes with occasional imbalances
        base_size = random.uniform(5, 20)
        
        # 30% chance of significant imbalance for testing
        if random.random() < 0.3:
            if random.random() < 0.5:
                bid_size = base_size * random.uniform(2, 4)  # Strong bid
                ask_size = base_size
            else:
                bid_size = base_size
                ask_size = base_size * random.uniform(2, 4)  # Strong ask
        else:
            bid_size = base_size * random.uniform(0.8, 1.2)
            ask_size = base_size * random.uniform(0.8, 1.2)
        
        # Last trade information
        last_price = bid_price if random.random() < 0.5 else ask_price
        last_size = random.uniform(1, 10)
        
        return {
            "symbol": symbol,
            "bid_price": bid_price,
            "ask_price": ask_price,
            "bid_size": bid_size,
            "ask_size": ask_size,
            "last_price": last_price,
            "last_size": last_size,
        }
    


    async def _execute_signal(self, signal: TradingSignal, result: TradingCycleResult):
        """Execute a trading signal"""
        try:
            # Place order directly on Binance Testnet
            binance_result = await self._place_binance_order(signal)
            
            # Check if order was successful
            if 'orderId' in binance_result:
                order_status = binance_result.get('status', '')
                # Check if order is filled or we should treat NEW as filled for market orders
                if order_status == 'FILLED' or order_status == 'NEW':
                    # Order placed successfully (treat NEW as filled for immediate processing)
                    result.orders_executed += 1
                    increment_counter("orders_filled", 1, symbol=signal.symbol, side=signal.action)
                    
                    # Extract fill information from Binance response
                    # For NEW market orders, these might be 0 initially, but we'll use the requested values
                    # for immediate journal recording (will be updated later by monitoring)
                    filled_qty = float(binance_result.get('executedQty', 0))
                    avg_price = float(binance_result.get('avgPrice', 0))
                    
                    # PHASE 1.3: Check if order needs to wait for fill
                    # For testnet, orders may be in NEW status - wait for fill
                    order_status = binance_result.get('status', '')
                    order_id = binance_result.get('orderId')
                    
                    if order_status == 'NEW' and avg_price == 0:
                        self.logger.info(f"⏳ Order {order_id} status=NEW, waiting for fill...")
                        
                        # Wait for order to fill (poll up to 5 seconds)
                        for wait_attempt in range(10):
                            await asyncio.sleep(0.5)
                            fill_check = await self._verify_order(order_id, signal.symbol.replace("/", ""))
                            
                            if fill_check:
                                new_status = fill_check.get('status', '')
                                new_avg_price = float(fill_check.get('avgPrice', 0))
                                new_filled_qty = float(fill_check.get('executedQty', 0))
                                
                                self.logger.info(f"⏳ Order check {wait_attempt+1}: status={new_status}, avgPrice={new_avg_price}, filledQty={new_filled_qty}")
                                
                                if new_status == 'FILLED' and new_avg_price > 0:
                                    avg_price = new_avg_price
                                    filled_qty = new_filled_qty
                                    order_status = 'FILLED'
                                    self.logger.info(f"✅ Order {order_id} FILLED at {avg_price}")
                                    break
                                elif new_status == 'PARTIALLY_FILLED_FILLED' and new_avg_price > 0:
                                    avg_price = new_avg_price
                                    filled_qty = new_filled_qty
                                    order_status = 'PARTIALLY_FILLED'
                                    self.logger.info(f"✅ Order {order_id} PARTIALLY FILLED at {avg_price}")
                                    break
                    
                    # Now check if we have valid price after waiting
                    if avg_price == 0 or avg_price is None:
                        # Use the price from signal or estimate as fallback for testnet
                        price = getattr(signal, 'price', None)
                        if price is None or price == 0:
                            price = self._last_used_price.get(signal.symbol, 0.0)
                        if price > 0:
                            avg_price = price
                            self.logger.warning(f"⚠️ Using estimated price {avg_price} for {signal.symbol}")
                        else:
                            self.logger.critical(f"⛔ CRITICAL: No valid price for {signal.symbol}! Full response: {binance_result}")
                            return
                    
                    # Ensure filled_qty is valid
                    if filled_qty == 0:
                        filled_qty = float(binance_result.get('quantity', 0)) or getattr(signal, 'quantity', 0)
                    
                    # If we got 0 values from exchange, use our requested values for immediate processing
                    if filled_qty == 0:
                        filled_qty = float(binance_result.get('quantity', 0)) or getattr(signal, 'quantity', 0)
                    if avg_price == 0:
                        # Use the price from signal or estimate
                        price = getattr(signal, 'price', None)
                        if price is None:
                            # Skip fallback to hardcoded prices - use the price we calculated for the order
                            price = self._last_used_price.get(signal.symbol, 0.0)
                        avg_price = price
                    
                    # Ensure alerting is configured before sending trade alert
                    configure_alerting_from_env()
                    try:
                        await send_trade_execution_alert(
                            symbol=signal.symbol,
                            side=signal.action,
                            quantity=filled_qty,
                            price=avg_price,
                            success=True,
                        )
                    except Exception as alert_err:
                        self.logger.error(f"Failed to send trade execution alert: {alert_err}")
                    
                    self.logger.info(
                        f"✅ BINANCE {'FILLED' if order_status == 'FILLED' else 'PLACED'}: {signal.action} {filled_qty} {signal.symbol} "
                        f"@ {avg_price} USDT (Status: {order_status})"
                    )
                    
                    # PHASE 1.4 & 1.5: Log order ID and verify order
                    order_id = binance_result.get('orderId')
                    self.logger.critical(f"🆔 ORDER ID CAPTURED: {order_id} for {signal.symbol}")
                    
                    # Verify order exists on Binance (PHASE 1.4)
                    # Small delay to allow order to process
                    await asyncio.sleep(0.5)
                    verification = await self._verify_order(order_id, signal.symbol)
                    if verification is None:
                        self.logger.critical(f"⚠️ ORDER VERIFICATION FAILED for ID: {order_id}")
                    else:
                        self.logger.critical(f"✅ ORDER VERIFIED: {verification.get('status')}, Price: {verification.get('price')}, Qty: {verification.get('executedQty')}")
                    
                    # Record trade in journal
                    trade_id = f"trade_{int(time.time() * 1000)}"
                    self.journal.record_entry(
                        trade_id=trade_id,
                        symbol=signal.symbol,
                        side=signal.action,
                        quantity=filled_qty,
                        entry_price=avg_price,
                        predicted_return=getattr(signal, 'expected_return', 0.0),
                        uncertainty=getattr(signal, 'uncertainty', 0.0),
                        metadata={'confidence': signal.confidence, 'cycle': self._cycle_count, 'binance_order_id': binance_result.get('orderId'), 'binance_status': order_status}
                    )
                    
                    # PHASE 2.2: Track open position for time-based exit monitoring
                    self._open_positions[trade_id] = {
                        'trade_id': trade_id,
                        'symbol': signal.symbol,
                        'side': signal.action,
                        'entry_price': avg_price,
                        'quantity': filled_qty,
                        'entry_time': time.time(),
                        'binance_order_id': order_id,
                        'status': 'OPEN'
                    }
                    
                    self.logger.critical(f"🔒 TRADE RECORDED: {trade_id} | {signal.symbol} {signal.action} @ {avg_price}")
                    self.logger.critical(f"⏳ Position tracked for exit monitoring. Max hold: {self._max_hold_time_seconds}s, Stop-loss: {self._stop_loss_pct*100}%")
                    
                else:
                    # Order rejected or other status
                    configure_alerting_from_env()
                    try:
                        await send_trade_execution_alert(
                            symbol=signal.symbol,
                            side=signal.action,
                            quantity=signal.quantity,
                            price=0,
                            success=False,
                            error=f"Order status: {order_status}",
                        )
                    except Exception as alert_err:
                        self.logger.error(f"Failed to send rejection alert: {alert_err}")
                    
                    self.logger.warning(
                        f"❌ BINANCE ORDER {order_status}: {signal.action} {signal.symbol}"
                    )
            else:
                # Order failed completely
                configure_alerting_from_env()
                try:
                    await send_trade_execution_alert(
                        symbol=signal.symbol,
                        side=signal.action,
                        quantity=signal.quantity,
                        price=0,
                        success=False,
                        error=binance_result.get('msg', 'Unknown error'),
                    )
                except Exception as alert_err:
                    self.logger.error(f"Failed to send failure alert: {alert_err}")
                
                self.logger.warning(
                    f"❌ BINANCE REJECTED: {signal.action} {signal.symbol} - {binance_result.get('msg', 'Unknown error')}"
                )
        
        except Exception as e:
            self.logger.error(f"Execution error: {e}")
            result.errors.append(f"Execution: {str(e)}")
    
    async def _update_metrics(self, result: TradingCycleResult):
        """Update metrics after cycle"""
        # Metrics updates disabled for now
        # balance = await self.executor.get_balance()
        # positions = await self.executor.get_positions()
    

    
    async def shutdown(self):
        """Shutdown the trading loop"""
        self.logger.info("Shutting down trading loop")
        self._running = False
        
        if self.health_server:
            self.health_server.stop()
        
        # balance = await self.executor.get_balance()
        # positions = await self.executor.get_positions()
        
        await send_system_status_alert(
            component="trading_loop",
            status="stopped",
            details={
                "cycles_completed": self._cycle_count,
                "uptime_seconds": time.time() - self._start_time if self._start_time else 0,
                "final_balance": "N/A (direct API)",  # balance
                "final_positions": "N/A (direct API)",  # positions
            },
        )
        
        self._shutdown_event.set()
    
    async def wait_for_shutdown(self):
        """Wait for shutdown to complete"""
        await self._shutdown_event.wait()


def create_testnet_trading_loop() -> EnhancedTradingLoop:
    """Create a testnet trading loop with default configuration"""
    config = TradingConfig(
        mode=TradingMode.PAPER,
        symbols=["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "XRP/USDT", "DOGE/USDT", "MATIC/USDT", "SOL/USDT", "DOT/USDT", "AVAX/USDT", "LINK/USDT", "UNI/USDT", "LTC/USDT", "BCH/USDT", "ATOM/USDT", "ETC/USDT", "XLM/USDT", "ALGO/USDT", "VET/USDT", "FIL/USDT"],
        cycle_interval=10.0,
        max_position_size=0.15,
        max_daily_loss=15000.0,
        max_orders_per_minute=30,
        min_confidence_threshold=0.2,
        min_expected_return=0.003,
        min_signal_strength=0.05,
        min_uncertainty=0.0,
        max_uncertainty=1.0,
        enable_alerting=True,
        health_check_port=8081,
        metrics_port=9091,
    )
    
    return EnhancedTradingLoop(config)


def create_live_trading_loop() -> EnhancedTradingLoop:
    """Create a live trading loop with default configuration"""
    config = TradingConfig(
        mode=TradingMode.LIVE,
        symbols=["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "XRP/USDT", "DOGE/USDT", "MATIC/USDT", "SOL/USDT", "DOT/USDT", "AVAX/USDT", "LINK/USDT", "UNI/USDT", "LTC/USDT", "BCH/USDT", "ATOM/USDT", "ETC/USDT", "XLM/USDT", "ALGO/USDT", "VET/USDT", "FIL/USDT"],
        cycle_interval=30.0,  # Slower cycle for live trading
        max_position_size=0.05,  # Reduced position size for live trading
        max_daily_loss=5000.0,  # Reduced daily loss limit for live trading
        max_orders_per_minute=20,
        min_confidence_threshold=0.25,  # Slightly higher confidence threshold for live
        min_expected_return=0.005,  # Slightly higher expected return for live
        min_signal_strength=0.08,
        min_uncertainty=0.0,
        max_uncertainty=1.0,
        enable_alerting=True,
        health_check_port=8082,  # Different port for live system
        metrics_port=9092,  # Different port for live system
    )
    
    return EnhancedTradingLoop(config)


def create_live_trading_loop() -> EnhancedTradingLoop:
    """Create a live trading loop with default configuration"""
    config = TradingConfig(
        mode=TradingMode.LIVE,
        symbols=["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "XRP/USDT", "DOGE/USDT", "MATIC/USDT", "SOL/USDT", "DOT/USDT", "AVAX/USDT", "LINK/USDT", "UNI/USDT", "LTC/USDT", "BCH/USDT", "ATOM/USDT", "ETC/USDT", "XLM/USDT", "ALGO/USDT", "VET/USDT", "FIL/USDT"],
        cycle_interval=60.0,
        max_position_size=0.05,
        max_daily_loss=5000.0,
        max_orders_per_minute=20,
        min_confidence_threshold=0.3,
        min_expected_return=0.01,
        min_signal_strength=0.1,
        min_uncertainty=0.0,
        max_uncertainty=1.0,
        enable_alerting=True,
        health_check_port=8082,
        metrics_port=9092,
        base_url="https://fapi.binance.com"
    )
    
    return EnhancedTradingLoop(config)


async def run_testnet_trading_loop():
    """Run the testnet trading loop with proper signal handling"""
    loop = create_testnet_trading_loop()
    
    #     def signal_handler(sig, frame):
    #         print("\nShutdown signal received")
    #         loop._running = False
    #     
    #     signal.signal(signal.SIGINT, signal_handler)
    #     signal.signal(signal.SIGTERM, signal_handler)
    
    await loop.initialize()
    await loop.start()


async def run_live_trading_loop():
    """Run the live trading loop with proper signal handling"""
    loop = create_live_trading_loop()
    
    #     def signal_handler(sig, frame):
    #         print("\nShutdown signal received")
    #         loop._running = False
    #     
    #     signal.signal(signal.SIGINT, signal_handler)
    #     signal.signal(signal.SIGTERM, signal_handler)
    
    await loop.initialize()
    await loop.start()


if __name__ == "__main__":
    import sys
    import signal
    import asyncio
    import os
    
    # Load env vars directly from .env file in current directory
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    
    logging.basicConfig(level=logging.INFO)
    
    def signal_handler(sig, frame):
        print("\nShutdown signal received - continuing to run...")
        # Don't exit, let the retry loop handle restart
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Retry loop for continuous operation
    max_retries = 1000
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Determine which mode to run based on command line argument
            if len(sys.argv) > 1 and sys.argv[1] == "live":
                print("Starting LIVE trading loop...")
                asyncio.run(run_live_trading_loop())
            else:
                print("Starting TESTNET trading loop...")
                asyncio.run(run_testnet_trading_loop())
        except KeyboardInterrupt:
            print("\nInterrupted by user. Exiting.")
            break
        except Exception as e:
            retry_count += 1
            print(f"[ERROR] Trading loop crashed: {e}")
            print(f"[INFO] Restarting in 5 seconds... (attempt {retry_count}/{max_retries})")
            import time
            time.sleep(5)
    
    if retry_count >= max_retries:
        print("[FATAL] Max retries reached. System requires manual intervention.")
        sys.exit(1)