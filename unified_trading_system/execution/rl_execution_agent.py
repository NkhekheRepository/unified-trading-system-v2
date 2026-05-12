import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import deque
import random
import logging
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class OrderBookState:
    """Represents L2 order book state for RL agent"""
    bid_ask_spread: float
    depth_imbalance: float  # (bid_vol - ask_vol) / (bid_vol + ask_vol)
    order_flow_imbalance: float
    volatility: float
    time_of_day: float  # Normalized 0-1
    recent_trades_count: int
    urgency: float  # how urgent is the execution (0-1)
    
    def to_vector(self) -> np.ndarray:
        return np.array([
            self.bid_ask_spread,
            self.depth_imbalance,
            self.order_flow_imbalance,
            self.volatility,
            self.time_of_day,
            self.recent_trades_count / 100.0,  # Normalize
            self.urgency
        ], dtype=np.float32)

class ExecutionAction:
    """Possible execution actions"""
    MARKET = "MARKET"
    LIMIT_AGGRESSIVE = "LIMIT_AGGRESSIVE"  # Place limit order inside spread
    LIMIT_PASSIVE = "LIMIT_PASSIVE"  # Place limit order at bid/ask
    ICEBERG = "ICEBERG"  # Split into smaller orders
    
    @staticmethod
    def all_actions():
        return [ExecutionAction.MARKET, ExecutionAction.LIMIT_AGGRESSIVE, 
                ExecutionAction.LIMIT_PASSIVE, ExecutionAction.ICEBERG]

@dataclass
class ExecutionResult:
    """Result of an execution for learning"""
    action: str
    expected_price: float
    executed_price: float
    slippage_bps: float  # Basis points of slippage
    fill_time_seconds: float
    order_size: float
    timestamp: str

class QLearningExecutionAgent:
    """RL agent using Q-Learning to optimize execution and minimize slippage"""
    
    def __init__(self, learning_rate: float = 0.01, discount_factor: float = 0.95, 
                 epsilon: float = 0.1, epsilon_decay: float = 0.995):
        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = 0.01
        
        # State discretization for Q-table
        self.state_buckets = {
            'spread': 5,      # Low, Medium, High, Very High, Extreme
            'imbalance': 5,    # Strong Bid, Weak Bid, Neutral, Weak Ask, Strong Ask
            'volatility': 3,   # Low, Medium, High
            'urgency': 3       # Low, Medium, High
        }
        
        # Initialize Q-table as dictionary (state_tuple -> action -> q_value)
        self.q_table = {}
        
        # Experience replay buffer
        self.replay_buffer = deque(maxlen=10000)
        
        # Performance tracking
        self.total_slippage_saved = 0.0
        self.execution_count = 0
        self.model_path = "/home/nkhekhe/unified_trading_system/execution/rl_agent_model.json"
        
        self.load_model()
        
    def _discretize_state(self, state: OrderBookState) -> Tuple[int, int, int, int]:
        """Convert continuous state to discrete buckets"""
        # Spread: 0=Low (<0.01%), 1=Med (0.01-0.05%), 2=High (0.05-0.1%), 3=VH (>0.1%)
        spread_bucket = min(int(state.bid_ask_spread * 10000 / 5), self.state_buckets['spread'] - 1)
        
        # Imbalance: -1 to 1 -> 0 to 4
        imbalance_bucket = int((state.depth_imbalance + 1) / 2 * (self.state_buckets['imbalance'] - 1))
        
        # Volatility: 0=Low, 1=Med, 2=High
        volatility_bucket = min(int(state.volatility * 10), self.state_buckets['volatility'] - 1)
        
        # Urgency: 0=Low, 1=Med, 2=High
        urgency_bucket = min(int(state.urgency * 3), self.state_buckets['urgency'] - 1)
        
        return (spread_bucket, imbalance_bucket, volatility_bucket, urgency_bucket)
    
    def _get_q_values(self, state_tuple: Tuple) -> Dict[str, float]:
        """Get Q-values for all actions in a state"""
        if state_tuple not in self.q_table:
            self.q_table[state_tuple] = {a: 0.0 for a in ExecutionAction.all_actions()}
        return self.q_table[state_tuple]
    
    def select_action(self, state: OrderBookState, training: bool = True) -> str:
        """Select execution action using epsilon-greedy policy"""
        state_tuple = self._discretize_state(state)
        q_values = self._get_q_values(state_tuple)
        
        if training and random.random() < self.epsilon:
            # Explore: random action
            return random.choice(ExecutionAction.all_actions())
        else:
            # Exploit: best action
            return max(q_values.items(), key=lambda x: x[1])[0]
    
    def calculate_reward(self, result: ExecutionResult) -> float:
        """Calculate reward based on execution quality
        
        Reward components:
        - Negative slippage (lower is better)
        - Fill time penalty (slower is worse)
        - Fee consideration (limit orders get rebates)
        """
        # Base reward: negative slippage in bps (we want to minimize slippage)
        reward = -result.slippage_bps
        
        # Penalty for slow fills (market orders should be fast)
        if result.action == ExecutionAction.MARKET:
            reward -= result.fill_time_seconds * 0.1
        elif result.action in [ExecutionAction.LIMIT_AGGRESSIVE, ExecutionAction.LIMIT_PASSIVE]:
            # Limit orders get maker rebate (positive reward)
            reward += 2.0  # Assume 2 bps rebate
            # But penalty if it doesn't fill
            if result.fill_time_seconds > 60:  # Didn't fill in 1 minute
                reward -= 10.0
        
        # Normalize reward
        return reward / 10.0
    
    def update(self, state: OrderBookState, action: str, reward: float, 
               next_state: Optional[OrderBookState]):
        """Update Q-values using Q-learning update rule"""
        state_tuple = self._discretize_state(state)
        q_values = self._get_q_values(state_tuple)
        
        # Calculate target Q-value
        if next_state:
            next_state_tuple = self._discretize_state(next_state)
            next_q_values = self._get_q_values(next_state_tuple)
            max_next_q = max(next_q_values.values())
            target = reward + self.gamma * max_next_q
        else:
            target = reward  # Terminal state
        
        # Q-learning update
        current_q = q_values[action]
        q_values[action] = current_q + self.lr * (target - current_q)
        
        # Decay epsilon
        self.epsilon = max(self.epsilon * self.epsilon_decay, self.epsilon_min)
        
        self.execution_count += 1
        
    def record_execution(self, result: ExecutionResult):
        """Record execution result and update agent"""
        self.replay_buffer.append(result)
        self.total_slippage_saved += -result.slippage_bps
        
        # Periodic model save
        if self.execution_count % 100 == 0:
            self.save_model()
            
        logger.info(f"Execution #{self.execution_count}: {result.action}, "
                   f"Slippage={result.slippage_bps:.2f}bps, "
                   f"Saved={self.total_slippage_saved:.2f}bps")
    
    def save_model(self):
        """Save Q-table and parameters to disk"""
        try:
            model_data = {
                "q_table": {str(k): v for k, v in self.q_table.items()},
                "epsilon": self.epsilon,
                "execution_count": self.execution_count,
                "total_slippage_saved": self.total_slippage_saved
            }
            with open(self.model_path, 'w') as f:
                json.dump(model_data, f, indent=2)
            logger.info(f"Model saved to {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
    
    def load_model(self):
        """Load Q-table and parameters from disk"""
        try:
            with open(self.model_path, 'r') as f:
                model_data = json.load(f)
            
            # Convert string keys back to tuples
            self.q_table = {}
            for k_str, v in model_data["q_table"].items():
                # Parse tuple from string like "(1, 2, 0, 1)"
                k_tuple = tuple(int(x.strip()) for x in k_str.strip("()").split(","))
                self.q_table[k_tuple] = v
            
            self.epsilon = model_data.get("epsilon", self.epsilon)
            self.execution_count = model_data.get("execution_count", 0)
            self.total_slippage_saved = model_data.get("total_slippage_saved", 0.0)
            
            logger.info(f"Model loaded from {self.model_path}, "
                       f"executions={self.execution_count}, "
                       f"slippage_saved={self.total_slippage_saved:.2f}bps")
        except FileNotFoundError:
            logger.info("No existing model found, starting fresh")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")

if __name__ == "__main__":
    # Test the agent
    agent = QLearningExecutionAgent()
    
    # Simulate an execution decision
    state = OrderBookState(
        bid_ask_spread=0.0003,  # 3 bps spread
        depth_imbalance=0.2,     # Slightly more bids
        order_flow_imbalance=0.1,
        volatility=0.05,
        time_of_day=0.5,
        recent_trades_count=50,
        urgency=0.8
    )
    
    action = agent.select_action(state, training=True)
    print(f"Selected action: {action}")
    
    # Simulate result
    result = ExecutionResult(
        action=action,
        expected_price=50000.0,
        executed_price=50001.5,  # Slipped 1.5
        slippage_bps=3.0,
        fill_time_seconds=0.5,
        order_size=0.1,
        timestamp=datetime.now().isoformat()
    )
    
    reward = agent.calculate_reward(result)
    print(f"Reward: {reward:.4f}")
    agent.record_execution(result)
