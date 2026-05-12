"""
Smart Order Router for Unified Trading System
Combines LVR's smart order routing with Autonomous System's execution model
"""


import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import time


class OrderType(Enum):
    """Order types"""
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP_LIMIT = "STOP_LIMIT"
    ICEBERG = "ICEBERG"
    TWAP = "TWAP"
    VWAP = "VWAP"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass
class ExecutionIntent:
    """Intent to execute a trade (from decision layer)"""
    symbol: str
    side: str  # "BUY" or "SELL"
    quantity: float  # Desired quantity
    urgency: float  # How urgently to execute [0, 1]
    max_slippage: float  # Maximum acceptable slippage
    min_time_limit: float  # Minimum time to execute (seconds)
    max_time_limit: float  # Maximum time to execute (seconds)
    aggression_level: float  # Current aggression level [0, 1]
    timestamp: int  # Nanoseconds since epoch


@dataclass
class ExecutionPlan:
    """Planned execution strategy"""
    symbol: str
    order_type: OrderType
    quantity: float
    price: Optional[float]  # None for market orders
    time_in_force: str
    max_slippage: float
    expected_slippage: float
    expected_latency: int  # milliseconds
    expected_cost: float  # Total expected cost in basis points
    urgency_score: float  # Computed urgency based on market conditions
    side: str  # "BUY" or "SELL"
    timestamp: int  # Nanoseconds since epoch


@dataclass
class ExecutionResult:
    """Result of execution attempt"""
    status: OrderStatus
    filled_quantity: float
    average_price: float
    slippage: float  # Basis points
    latency: int  # Milliseconds
    market_impact: float  # Estimated market impact in basis points
    timestamp: int  # Nanoseconds since epoch
    order_id: Optional[str] = None
    error_message: Optional[str] = None


class ExecutionModel:
    """
    Unified execution model combining:
    1. LVR's smart order routing and execution planning
    2. Autonomous System's execution feedback loop
    3. Market impact modeling and slippage prediction
    """
    
    def __init__(
        self,
        execution_eta: float = 0.01,      # Execution feedback gain
        market_impact_factor: float = 0.1, # Market impact scaling
        latency_base: int = 5,            # Base latency in ms
        slippage_factor: float = 0.05     # Base slippage factor
    ):
        self.execution_eta = execution_eta
        self.market_impact_factor = market_impact_factor
        self.latency_base = latency_base
        self.slippage_factor = slippage_factor
        
        # Execution history for learning
        self.execution_history = []
        
        # Venue characteristics (would be learned/calibrated in practice)
        self.venue_characteristics = {
            "primary": {
                "latency": 2,           # ms
                "fill_rate": 0.95,      # probability of fill
                "slippage_factor": 0.03,
                "market_impact": 0.02
            },
            "secondary": {
                "latency": 5,
                "fill_rate": 0.85,
                "slippage_factor": 0.05,
                "market_impact": 0.04
            },
            "dark_pool": {
                "latency": 10,
                "fill_rate": 0.60,
                "slippage_factor": 0.01,
                "market_impact": 0.005
            }
        }
    
    def plan_execution(
        self,
        execution_intent: ExecutionIntent,
        market_data: Dict,
        orderbook_data: Dict = None
    ) -> ExecutionPlan:
        """
        Plan execution strategy based on intent and market conditions
        
        Args:
            execution_intent: What we want to execute
            market_data: Current market data (prices, volumes, etc.)
            orderbook_data: Order book data (optional)
            
        Returns:
            Execution plan
        """
        # Extract market conditions
        volatility = market_data.get("volatility_estimate", 0.1)
        liquidity = market_data.get("liquidity_estimate", 0.5)
        spread = market_data.get("spread_bps", 1.0)  # basis points
        
        # Compute urgency based on intent and market conditions
        urgency_score = self._compute_urgency(
            execution_intent.urgency,
            execution_intent.aggression_level,
            volatility,
            liquidity
        )
        
        # Select order type based on urgency and market conditions
        order_type = self._select_order_type(
            urgency_score,
            volatility,
            liquidity,
            spread,
            execution_intent.quantity
        )
        
        # Determine price and timing
        mid_price = market_data.get("mid_price", 0.0)
        if order_type == OrderType.MARKET:
            price = None  # Market order
        else:
            # Limit order price based on side and urgency
            if execution_intent.side == "BUY":
                # For buy orders, more urgent = higher price (more aggressive)
                price_offset = urgency_score * spread * 0.5  # Half spread * urgency
                price = mid_price + (price_offset / 10000)  # Convert bps to price
            else:  # SELL
                # For sell orders, more urgent = lower price (more aggressive)
                price_offset = urgency_score * spread * 0.5
                price = mid_price - (price_offset / 10000)
        
        # Determine time in force
        time_in_force = self._select_time_in_force(
            execution_intent.min_time_limit,
            execution_intent.max_time_limit,
            urgency_score
        )
        
        # Estimate execution costs
        expected_slippage = self._estimate_slippage(
            order_type,
            execution_intent.quantity,
            volatility,
            liquidity,
            urgency_score
        )
        
        expected_latency = self._estimate_latency(
            order_type,
            urgency_score
        )
        
        expected_cost = self._estimate_total_cost(
            expected_slippage,
            expected_latency,
            spread
        )
        
        # Create execution plan
        plan = ExecutionPlan(
            symbol=execution_intent.symbol,
            order_type=order_type,
            quantity=execution_intent.quantity,
            price=price,
            time_in_force=time_in_force,
            max_slippage=execution_intent.max_slippage,
            expected_slippage=expected_slippage,
            expected_latency=expected_latency,
            expected_cost=expected_cost,
            urgency_score=urgency_score,
            side=execution_intent.side,
            timestamp=int(time.time() * 1e9)
        )
        
        return plan
    
    def simulate_execution(
        self,
        execution_plan: ExecutionPlan,
        market_data: Dict
    ) -> ExecutionResult:
        """
        Simulate execution based on plan and current market conditions
        
        Args:
            execution_plan: Planned execution strategy
            market_data: Current market data
            
        Returns:
            Execution result
        """
        # Determine if execution succeeds based on venue characteristics
        # In practice, this would involve actual order routing
        
        # Select venue based on order characteristics
        venue = self._select_venue(execution_plan)
        venue_chars = self.venue_characteristics[venue]
        
        # Simulate fill (probabilistic based on venue fill rate)
        fill_success = np.random.random() < venue_chars["fill_rate"]
        
        if fill_success:
            status = OrderStatus.FILLED
            filled_quantity = execution_plan.quantity
        else:
            status = OrderStatus.REJECTED
            filled_quantity = 0.0
        
        # Simulate price and slippage
        mid_price = market_data.get("mid_price", 0.0)
        if execution_plan.price is not None:
            # Limit order - use specified price
            execution_price = execution_plan.price
        else:
            # Market order - subject to slippage
            base_price = mid_price
            slippage_bps = np.random.normal(
                execution_plan.expected_slippage,
                execution_plan.expected_slippage * 0.3  # 30% variation
            )
            # Apply slippage based on side
            if execution_plan.side == "BUY":
                execution_price = base_price * (1 + slippage_bps / 10000)
            else:  # SELL
                execution_price = base_price * (1 - slippage_bps / 10000)
        
        # Ensure we have a price
        if execution_price == 0.0 and mid_price > 0:
            execution_price = mid_price
        elif execution_price == 0.0:
            execution_price = 100.0  # Default fallback price
        
        # Calculate actual slippage
        if execution_plan.price is not None:
            # For limit orders, slippage is difference from mid price
            slippage_bps = abs(execution_price - mid_price) / mid_price * 10000
        else:
            # For market orders, we already calculated slippage above
            slippage_bps = abs(execution_price - mid_price) / mid_price * 10000 if mid_price > 0 else 0.0
        
        # Simulate latency
        base_latency = venue_chars["latency"]
        latency_variation = np.random.exponential(base_latency * 0.2)  # Exponential tail
        latency = int(base_latency + latency_variation)
        
        # Estimate market impact
        market_impact = self._estimate_market_impact(
            execution_plan.quantity,
            market_data.get("liquidity_estimate", 0.5),
            venue_chars["market_impact"]
        )
        
        # Calculate average price (for partial fills, would be weighted average)
        average_price = execution_price
        
        # Create execution result
        result = ExecutionResult(
            status=status,
            filled_quantity=filled_quantity,
            average_price=average_price,
            slippage=slippage_bps,
            latency=latency,
            market_impact=market_impact,
            timestamp=int(time.time() * 1e9)
        )
        
        # Record in execution history for learning
        self._record_execution(execution_plan, result, market_data)
        
        return result
    
    def apply_execution_feedback(
        self,
        aggression_level: float,
        execution_result: ExecutionResult
    ) -> float:
        """
        Apply execution feedback to adjust aggression level
        Based on Autonomous System's execution feedback:
        α_{t+1} = α_t − η · ExecutionStress_t
        
        Args:
            aggression_level: Current aggression level
            execution_result: Result of execution attempt
            
        Returns:
            Updated aggression level
        """
        # Compute execution stress from result
        execution_stress = self._compute_execution_stress(execution_result)
        
        # Apply feedback: reduce aggression for poor execution
        updated_aggression = aggression_level - self.execution_eta * execution_stress
        
        # Ensure bounds
        updated_aggression = np.clip(updated_aggression, 0.0, 1.0)
        
        return updated_aggression

    def _compute_execution_stress(self, execution_result: ExecutionResult) -> float:
        """
        Compute execution stress from execution result
        Based on Autonomous System's execution stress formulation
        
        Args:
            execution_result: Result of execution attempt
            
        Returns:
            Execution stress value [0, 1]
        """
        # Components of execution stress
        slippage_stress = min(execution_result.slippage / 50.0, 1.0)  # Normalize to 50bps max
        latency_stress = min(execution_result.latency / 100.0, 1.0)    # Normalize to 100ms max
        impact_stress = min(execution_result.market_impact / 50.0, 1.0)   # Normalize to 50bps max
        # For fill_ratio, we'll use a simplified approach since it's not directly stored
        # In a full implementation, this would be filled_quantity / requested_quantity
        fill_ratio_stress = 0.1  # Assume 90% fill ratio as default for testing
        
        # Weighted combination
        execution_stress = (
            0.3 * slippage_stress +
            0.2 * latency_stress +
            0.3 * impact_stress +
            0.2 * fill_ratio_stress
        )
        
        return np.clip(execution_stress, 0.0, 1.0)

    # Helper methods
    
    def _compute_urgency(
        self,
        base_urgency: float,
        aggression_level: float,
        volatility: float,
        liquidity: float
    ) -> float:
        """Compute execution urgency based on multiple factors"""
        # Base urgency from intent
        urgency = base_urgency
        
        # Increase urgency with aggression (more aggressive = more urgent execution)
        urgency += 0.3 * aggression_level
        
        # Increase urgency with volatility (need to act fast in volatile markets)
        urgency += 0.2 * min(volatility * 2, 0.5)  # Cap volatility contribution
        
        # Decrease urgency with poor liquidity (harder to execute quickly)
        urgency -= 0.2 * (1.0 - liquidity)
        
        # Ensure bounds
        return np.clip(urgency, 0.0, 1.0)
    
    def _select_order_type(
        self,
        urgency: float,
        volatility: float,
        liquidity: float,
        spread: float,
        quantity: float
    ) -> OrderType:
        """Select appropriate order type based on conditions"""
        # Very high urgency -> market order
        if urgency > 0.8:
            return OrderType.MARKET
        
        # High volatility and low liquidity -> limit orders to control slippage
        if volatility > 0.3 and liquidity < 0.4:
            return OrderType.LIMIT
        
        # Low urgency and good liquidity -> can use passive orders
        if urgency < 0.3 and liquidity > 0.7:
            return OrderType.LIMIT
        
        # Medium conditions -> default to limit
        return OrderType.LIMIT
    
    def _select_time_in_force(
        self,
        min_time: float,
        max_time: float,
        urgency: float
    ) -> str:
        """Select time in force based on timing constraints and urgency"""
        # Convert seconds to approximate time in force
        if max_time <= 1:  # Very short term -> IOC or FOK
            return "IOC" if urgency > 0.5 else "FOK"
        elif max_time <= 5:  # Short term
            return "IOC"
        elif max_time <= 60:  # Medium term -> DAY
            return "DAY"
        else:  # Long term -> GTC
            return "GTC"
    
    def _select_venue(self, execution_plan: ExecutionPlan) -> str:
        """Select execution venue based on order characteristics"""
        # Simple heuristic: urgent orders go to primary venue
        # Large orders might benefit from dark pools
        # Otherwise use primary venue
        
        if execution_plan.urgency_score > 0.7:
            return "primary"
        elif execution_plan.quantity > 1000:  # Large order threshold
            return "dark_pool" if np.random.random() < 0.3 else "primary"
        else:
            return "primary"
    
    def _estimate_slippage(
        self,
        order_type: OrderType,
        quantity: float,
        volatility: float,
        liquidity: float,
        urgency: float
    ) -> float:
        """Expected slippage in basis points"""
        # Base slippage
        base_slippage = self.slippage_factor * 100  # Convert to bps
        
        # Adjust for order type
        if order_type == OrderType.MARKET:
            slippage_multiplier = 2.0  # Market orders have higher slippage
        elif order_type == OrderType.LIMIT:
            slippage_multiplier = 0.5  # Limit orders can have negative slippage (improvement)
        else:
            slippage_multiplier = 1.0
        
        # Adjust for quantity (larger orders = more slippage)
        quantity_factor = 1.0 + np.log10(max(quantity, 1)) * 0.2
        
        # Adjust for volatility and liquidity
        volatility_factor = 1.0 + volatility * 2
        liquidity_factor = 2.0 - liquidity  # Lower liquidity = higher factor
        
        # Adjust for urgency (more urgent = higher slippage tolerance)
        urgency_factor = 1.0 + urgency * 0.5
        
        expected_slippage = (
            base_slippage * 
            slippage_multiplier * 
            quantity_factor * 
            volatility_factor * 
            liquidity_factor * 
            urgency_factor
        )
        
        return max(expected_slippage, 0.1)  # Minimum 0.1 bps
    
    def _estimate_latency(
        self,
        order_type: OrderType,
        urgency: float
    ) -> int:
        """Expected latency in milliseconds"""
        # Base latency
        base_latency = self.latency_base
        
        # Adjust for order type
        if order_type == OrderType.MARKET:
            latency_multiplier = 1.0  # Market orders are fastest
        elif order_type == OrderType.LIMIT:
            latency_multiplier = 1.5  # Limit orders may rest longer
        else:
            latency_multiplier = 1.2
        
        # Adjust for urgency (more urgent = lower latency preference)
        urgency_factor = 2.0 - urgency  # Urgent orders want lower latency
        
        expected_latency = int(base_latency * latency_multiplier * urgency_factor)
        
        return max(expected_latency, 1)  # Minimum 1ms
    
    def _estimate_total_cost(
        self,
        expected_slippage: float,
        expected_latency: int,
        spread: float
    ) -> float:
        """Expected total execution cost in basis points"""
        # Slippage cost
        slippage_cost = expected_slippage
        
        # Latency cost (opportunity cost from delay)
        # Assume 1bp per 10ms of latency (simplified)
        latency_cost = expected_latency / 10.0
        
        # Spread cost (half spread for passive execution)
        spread_cost = spread * 0.5
        
        total_cost = slippage_cost + latency_cost + spread_cost
        
        return total_cost
    
    def _estimate_market_impact(
        self,
        quantity: float,
        liquidity: float,
        venue_market_impact: float
    ) -> float:
        """Estimate market impact in basis points"""
        # Simplified square-root law for market impact
        # Impact ∝ quantity / sqrt(liquidity)
        base_impact = self.market_impact_factor * 100  # Convert to bps
        
        # Normalize quantity (assume 100 is typical unit size)
        normalized_quantity = quantity / 100.0
        
        # Liquidity adjustment (lower liquidity = higher impact)
        liquidity_adjustment = 1.0 / max(liquidity, 0.1)
        
        # Venue adjustment
        venue_adjustment = venue_market_impact / 0.02  # Normalize to base 0.02
        
        market_impact = base_impact * normalized_quantity * np.sqrt(liquidity_adjustment) * venue_adjustment
        
        return market_impact
    
    def _record_execution(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
        market_data: Dict
    ):
        """Record execution for learning and analysis"""
        record = {
            "timestamp": result.timestamp,
            "plan": {
                "order_type": plan.order_type.value,
                "quantity": plan.quantity,
                "urgency_score": plan.urgency_score,
                "expected_slippage": plan.expected_slippage,
                "expected_latency": plan.expected_latency,
                "expected_cost": plan.expected_cost
            },
            "result": {
                "status": result.status.value,
                "filled_quantity": result.filled_quantity,
                "slippage": result.slippage,
                "latency": result.latency,
                "market_impact": result.market_impact
            },
            "market_conditions": {
                "volatility": market_data.get("volatility_estimate", 0.0),
                "liquidity": market_data.get("liquidity_estimate", 0.0),
                "spread": market_data.get("spread_bps", 0.0)
            }
        }
        
        self.execution_history.append(record)
        
        # Keep history bounded
        if len(self.execution_history) > 10000:
            self.execution_history = self.execution_history[-5000:]


# Example usage and testing
if __name__ == "__main__":
    import time
    
    # Create execution model
    execution_model = ExecutionModel(
        execution_eta=0.01,
        market_impact_factor=0.1,
        latency_base=5,
        slippage_factor=0.05
    )
    
    # Create execution intent (would come from decision layer)
    execution_intent = ExecutionIntent(
        symbol="BTCUSDT",
        side="BUY",
        quantity=10.0,
        urgency=0.6,
        max_slippage=5.0,  # 5 basis points
        min_time_limit=1.0,  # 1 second
        max_time_limit=10.0,  # 10 seconds
        aggression_level=0.7,
        timestamp=int(time.time() * 1e9)
    )
    
    # Simulate market data (would come from perception layer)
    market_data = {
        "symbol": "BTCUSDT",
        "bid_price": 50000.0,
        "ask_price": 50010.0,
        "bid_size": 5.0,
        "ask_size": 3.0,
        "last_price": 50005.0,
        "last_size": 2.0,
        "mid_price": 50005.0,
        "spread_bps": 2.0,  # 2 basis points
        "volatility_estimate": 0.15,
        "liquidity_estimate": 0.6,
        "volume_imbalance": 0.1
    }
    
    print("Smart Order Router Execution Planning:")
    print("=" * 50)
    
    # Plan execution
    plan = execution_model.plan_execution(execution_intent, market_data)
    
    print(f"Order Type: {plan.order_type.value}")
    print(f"Quantity: {plan.quantity}")
    print(f"Price: {plan.price}")
    print(f"Time in Force: {plan.time_in_force}")
    print(f"Urgency Score: {plan.urgency_score:.3f}")
    print(f"Expected Slippage: {plan.expected_slippage:.2f} bps")
    print(f"Expected Latency: {plan.expected_latency} ms")
    print(f"Expected Cost: {plan.expected_cost:.2f} bps")
    print()
    
    # Simulate execution
    print("Execution Simulation:")
    print("-" * 30)
    
    for i in range(5):
        result = execution_model.simulate_execution(plan, market_data)
        
        print(f"Simulation {i+1}:")
        print(f"  Status: {result.status.value}")
        print(f"  Filled Quantity: {result.filled_quantity}")
        print(f"  Average Price: {result.average_price:.2f}")
        print(f"  Slippage: {result.slippage:.2f} bps")
        print(f"  Latency: {result.latency} ms")
        print(f"  Market Impact: {result.market_impact:.2f} bps")
        print()
        
        # Apply execution feedback to aggression level
        updated_aggression = execution_model.apply_execution_feedback(
            execution_intent.aggression_level,
            result
        )
        
        print(f"  Updated Aggression Level: {updated_aggression:.3f}")
        print(f"  Aggression Change: {updated_aggression - execution_intent.aggression_level:.3f}")
        print()
        
        # Small delay between simulations
        time.sleep(0.01)
    
