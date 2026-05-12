"""
Testnet Execution Adapter for Unified Trading System
Wraps execution model with paper trading and full order lifecycle management.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from execution.smart_order_router import (
    ExecutionModel,
    ExecutionIntent,
    ExecutionPlan,
    ExecutionResult,
    OrderStatus,
    OrderType,
)


class TestnetOrderState(Enum):
    """Order lifecycle states"""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class TestnetOrder:
    """Extended order for testnet execution"""
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: Optional[float]
    order_type: OrderType
    state: TestnetOrderState = TestnetOrderState.PENDING
    filled_quantity: float = 0.0
    average_fill_price: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    execution_plan: Optional[ExecutionPlan] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class TestnetFill:
    """Trade fill record"""
    fill_id: str
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    fee: float = 0.0
    timestamp: float = field(default_factory=time.time)


class TestnetExecutor:
    """
    Testnet execution adapter with paper trading
    Manages order lifecycle and simulates real exchange behavior
    """
    
    def __init__(
        self,
        execution_model: Optional[ExecutionModel] = None,
        paper_balance: Optional[Dict[str, float]] = None,
        default_slippage: float = 0.001,
    ):
        self.execution_model = execution_model or ExecutionModel()
        self.paper_balance = paper_balance or {
            "BTC": 1.0,
            "ETH": 10.0,
            "USDT": 100000.0,
            "SOL": 100.0,
        }
        self.default_slippage = default_slippage
        
        # Phase 3.1 (10/10 Upgrade): Slippage modeling
        # Order book depth simulation (simplified)
        self.market_depth: Dict[str, Dict[str, float]] = {
            "BTC/USDT": {"bid_depth": 100.0, "ask_depth": 100.0},
            "ETH/USDT": {"bid_depth": 500.0, "ask_depth": 500.0},
            "SOL/USDT": {"bid_depth": 1000.0, "ask_depth": 1000.0},
            "BNB/USDT": {"bid_depth": 200.0, "ask_depth": 200.0},
        }
        self.slippage_factor = 0.0001  # Slippage per unit of quantity/depth
        
        self.orders: Dict[str, TestnetOrder] = {}
        self.fills: List[TestnetFill] = []
        self.order_counter = 0
        
        self._logger = logging.getLogger("testnet.executor")
        self._order_tasks: Dict[str, asyncio.Task] = {}
    
    def _calculate_slippage(self, symbol: str, quantity: float, side: str) -> float:
        """
        Calculate realistic slippage based on order size vs market depth.
        
        Args:
            symbol: Trading pair
            quantity: Order quantity
            side: BUY or SELL
            
        Returns:
            Slippage as a decimal (e.g., 0.001 = 0.1%)
        """
        depth_info = self.market_depth.get(symbol, {"bid_depth": 100.0, "ask_depth": 100.0})
        depth = depth_info["bid_depth"] if side == "BUY" else depth_info["ask_depth"]
        
        # Slippage increases with order size relative to depth
        if depth <= 0:
            return self.default_slippage * 2  # Low liquidity penalty
        
        size_ratio = quantity / depth
        slippage = self.slippage_factor * size_ratio * 100  # Scale up based on impact
        
        # Apply minimum and maximum slippage bounds
        slippage = max(self.default_slippage * 0.5, min(slippage, 0.01))  # Cap at 1%
        
        self._logger.debug(f"Slippage for {symbol}: {slippage*100:.3f}% (qty={quantity}, depth={depth})")
        return slippage
    
    def _generate_order_id(self) -> str:
        """Generate unique order ID"""
        self.order_counter += 1
        return f"TESTNET_{self.order_counter}_{int(time.time() * 1000)}"
    
    async def execute_intent(self, intent: ExecutionIntent) -> ExecutionResult:
        """
        Execute a trading intent using the execution model and paper trading
        
        Args:
            intent: Execution intent from decision layer
            
        Returns:
            Execution result
        """
        self._logger.info(
            f"Executing intent: {intent.side} {intent.quantity} {intent.symbol}"
        )
        
        # Get market data first
        market_data = await self._get_market_data(intent.symbol)
        
        # Create execution plan using market data
        plan = self.execution_model.plan_execution(intent, market_data)
        
        result = await self._execute_plan(plan, market_data)
        
        if result.status == OrderStatus.FILLED:
            self._update_paper_balance(intent, result)
        
        return result
    
    async def submit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: OrderType = OrderType.LIMIT,
        price: Optional[float] = None,
        time_in_force: str = "GTC",
    ) -> TestnetOrder:
        """
        Submit an order directly
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Order quantity
            order_type: Order type
            price: Limit price (None for market orders)
            time_in_force: Time in force
            
        Returns:
            TestnetOrder
        """
        order_id = self._generate_order_id()
        
        intent = ExecutionIntent(
            symbol=symbol,
            side=side,
            quantity=quantity,
            urgency=0.5,
            max_slippage=self.default_slippage,
            min_time_limit=10,
            max_time_limit=60,
            aggression_level=0.5,
            timestamp=int(time.time() * 1000),
        )
        
        # Get market data for execution plan
        market_data = await self._get_market_data(symbol)
        plan = self.execution_model.plan_execution(intent, market_data)
        
        order = TestnetOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price or plan.price,
            order_type=order_type,
            execution_plan=plan,
        )
        
        self.orders[order_id] = order
        
        if order_type == OrderType.MARKET:
            await self._fill_order(order)
        else:
            order.state = TestnetOrderState.SUBMITTED
        
        return order
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        
        if order.state in (TestnetOrderState.FILLED, TestnetOrderState.CANCELLED):
            return False
        
        order.state = TestnetOrderState.CANCELLED
        order.updated_at = time.time()
        
        self._logger.info(f"Cancelled order: {order_id}")
        return True
    
    async def get_order_status(self, order_id: str) -> Optional[TestnetOrder]:
        """Get order status"""
        return self.orders.get(order_id)
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[TestnetOrder]:
        """Get all open orders"""
        open_states = (TestnetOrderState.PENDING, TestnetOrderState.SUBMITTED, 
                      TestnetOrderState.PARTIALLY_FILLED)
        
        orders = [o for o in self.orders.values() if o.state in open_states]
        
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        
        return orders
    
    async def get_fills(self, symbol: Optional[str] = None) -> List[TestnetFill]:
        """Get all fills"""
        fills = self.fills
        
        if symbol:
            fills = [f for f in fills if f.symbol == symbol]
        
        return fills
    
    async def get_balance(self) -> Dict[str, float]:
        """Get current paper balance"""
        return self.paper_balance.copy()
    
    async def get_positions(self) -> List[Dict]:
        """Get current positions with PnL"""
        positions = []
        
        for asset, quantity in self.paper_balance.items():
            if asset == "USDT":
                continue
            
            if quantity > 0:
                positions.append({
                    "asset": asset,
                    "quantity": quantity,
                    "value": quantity * self._get_estimated_price(asset),
                })
        
        return positions
    
    async def reset_balance(self, balance: Dict[str, float]):
        """Reset paper balance"""
        self.paper_balance = balance.copy()
        self.orders.clear()
        self.fills.clear()
        self._logger.info("Paper balance reset")
    
    async def _get_market_data(self, symbol: str) -> Dict:
        """Get simulated market data"""
        base_price = {
            "BTC/USDT": 50000.0,
            "ETH/USDT": 3000.0,
            "SOL/USDT": 100.0,
            "BNB/USDT": 400.0,
        }.get(symbol, 100.0)
        
        import random
        price = base_price * (1 + random.gauss(0, 0.001))
        
        return {
            "symbol": symbol,
            "mid_price": price,
            "bid_price": price * 0.9995,
            "ask_price": price * 1.0005,
            "volume": random.uniform(1000000, 10000000),
            "liquidity_estimate": 0.5,
        }
    
    def _get_estimated_price(self, asset: str) -> float:
        """Get estimated price for asset"""
        prices = {
            "BTC": 50000.0,
            "ETH": 3000.0,
            "SOL": 100.0,
            "BNB": 400.0,
        }
        return prices.get(asset, 0.0)
    
    async def _execute_plan(self, plan: ExecutionPlan, market_data: Dict) -> ExecutionResult:
        """Execute an execution plan"""
        return self.execution_model.simulate_execution(plan, market_data)
    
    async def _fill_order(self, order: TestnetOrder):
        """Fill a market order with realistic slippage modeling (Phase 3.1)"""
        market_data = await self._get_market_data(order.symbol)
        
        # Phase 3.1: Calculate slippage based on order size vs market depth
        slippage = self._calculate_slippage(order.symbol, order.quantity, order.side)
        
        # Adjust fill price based on slippage
        base_price = market_data.get("mid_price", 100.0)
        if order.side == "BUY":
            fill_price = base_price * (1 + slippage)  # Pay more for market buys
        else:  # SELL
            fill_price = base_price * (1 - slippage)  # Receive less for market sells
        
        # Apply commission (0.1% round-trip typical for Binance futures)
        commission_rate = 0.001  # 0.1% taker fee
        commission = fill_price * order.quantity * commission_rate
        
        order.filled_quantity = order.quantity
        order.average_fill_price = fill_price
        
        # Store execution metadata including slippage and fees
        if not hasattr(order, 'metadata'):
            order.metadata = {}
        order.metadata['slippage_pct'] = slippage
        order.metadata['commission'] = commission
        order.metadata['fill_price_before_slippage'] = base_price
        
        order.state = TestnetOrderState.FILLED
        self._update_paper_balance_from_order(order, commission)
        
        order.updated_at = time.time()
        self._logger.info(f"Order {order.order_id} filled: price={fill_price:.4f}, slippage={slippage*100:.3f}%, commission={commission:.4f}")
    
    def _update_paper_balance(self, intent: ExecutionIntent, result: ExecutionResult):
        """Update paper balance after execution"""
        base, quote = intent.symbol.split("/")
        
        if intent.side == "BUY":
            self.paper_balance[quote] = self.paper_balance.get(quote, 0.0) - intent.quantity * result.average_price
            self.paper_balance[base] = self.paper_balance.get(base, 0.0) + result.filled_quantity
        else:
            self.paper_balance[base] = self.paper_balance.get(base, 0.0) - result.filled_quantity
            self.paper_balance[quote] = self.paper_balance.get(quote, 0.0) + result.filled_quantity * result.average_price
    
    def _update_paper_balance_from_order(self, order: TestnetOrder, commission: float = 0.0):
        """Update paper balance from a TestnetOrder including commission"""
        base, quote = order.symbol.split("/")
        
        if order.side == "BUY":
            total_cost = order.filled_quantity * order.average_fill_price + commission
            self.paper_balance[quote] = self.paper_balance.get(quote, 0.0) - total_cost
            self.paper_balance[base] = self.paper_balance.get(base, 0.0) + order.filled_quantity
        else:
            self.paper_balance[base] = self.paper_balance.get(base, 0.0) - order.filled_quantity
            revenue = order.filled_quantity * order.average_fill_price - commission
            self.paper_balance[quote] = self.paper_balance.get(quote, 0.0) + revenue


class TestnetExecutionWithGovernance(TestnetExecutor):
    """
    Testnet executor with governance and risk controls
    """
    
    def __init__(
        self,
        execution_model: Optional[ExecutionModel] = None,
        paper_balance: Optional[Dict[str, float]] = None,
        max_position_size: float = 1.0,
        max_daily_loss: float = 10000.0,
        max_orders_per_minute: int = 10,
    ):
        super().__init__(execution_model, paper_balance)
        
        self.max_position_size = max_position_size
        self.max_daily_loss = max_daily_loss
        self.max_orders_per_minute = max_orders_per_minute
        
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.order_times: List[float] = []
        
        self._logger = logging.getLogger("testnet.governance")
    
    async def submit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: OrderType = OrderType.LIMIT,
        price: Optional[float] = None,
        time_in_force: str = "GTC",
    ) -> Optional[TestnetOrder]:
        """Submit order with governance checks"""
        
        if not self._check_rate_limit():
            self._logger.warning("Rate limit exceeded")
            return None
        
        if not self._check_position_limits(symbol, side, quantity):
            self._logger.warning(f"Position limit exceeded for {symbol}")
            return None
        
        if not self._check_daily_loss_limit():
            self._logger.warning("Daily loss limit exceeded")
            return None
        
        return await super().submit_order(symbol, side, quantity, order_type, price, time_in_force)
    
    def _check_rate_limit(self) -> bool:
        """Check if order rate limit is exceeded"""
        now = time.time()
        self.order_times = [t for t in self.order_times if now - t < 60]
        
        return len(self.order_times) < self.max_orders_per_minute
    
    def _check_position_limits(self, symbol: str, side: str, quantity: float) -> bool:
        """Check if order would exceed position limits"""
        base = symbol.split("/")[0]
        
        current_position = self.paper_balance.get(base, 0)
        
        if side == "BUY":
            new_position = current_position + quantity
        else:
            new_position = current_position - quantity
        
        return abs(new_position) <= self.max_position_size
    
    def _check_daily_loss_limit(self) -> bool:
        """Check if daily loss limit is exceeded"""
        return self.daily_pnl >= -self.max_daily_loss
    
    def record_trade_pnl(self, pnl: float):
        """Record PnL from a trade"""
        self.daily_pnl += pnl
        self.daily_trades += 1
    
    def reset_daily_metrics(self):
        """Reset daily trading metrics"""
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self._logger.info("Daily metrics reset")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    async def test_executor():
        executor = TestnetExecutionWithGovernance()
        
        print(f"Initial balance: {await executor.get_balance()}")
        
        order = await executor.submit_order(
            "BTC/USDT", "BUY", 0.1, OrderType.MARKET
        )
        print(f"Order: {order}")
        
        print(f"Balance after trade: {await executor.get_balance()}")
        
        positions = await executor.get_positions()
        print(f"Positions: {positions}")
    
    asyncio.run(test_executor())
