"""
Walk-Forward Backtesting Framework for Trading System
Implements time-series cross-validation and parameter optimization
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import os
from collections import deque

logger = logging.getLogger(__name__)

@dataclass
class WalkForwardResult:
    """Results from a walk-forward test"""
    train_period_start: float
    train_period_end: float
    test_period_start: float
    test_period_end: float
    train_metrics: Dict[str, float]
    test_metrics: Dict[str, float]
    parameter_values: Dict[str, Any]
    is_profitable: bool

class WalkForwardBacktester:
    """
    Walk-forward backtesting with time-series cross-validation
    """
    
    def __init__(self, 
                 train_period_days: int = 90,
                 test_period_days: int = 30,
                 step_days: int = 15,
                 min_train_period_days: int = 30):
        self.train_period_days = train_period_days
        self.test_period_days = test_period_days
        self.step_days = step_days
        self.min_train_period_days = min_train_period_days
        
        self.results = []
        self.best_parameters = None
        self.parameter_history = []
        
        logger.info(f"Initialized WalkForwardBacktester: train={train_period_days}d, test={test_period_days}d, step={step_days}d")
    
    def validate_parameter_stability(self,
                                  parameter_name: str,
                                  parameter_values: List[float],
                                  performance_by_param: Dict[float, List[float]]) -> Dict[str, Any]:
        """
        Validate that a parameter produces consistent results across different periods
        """
        if not performance_by_param:
            return {'stable': False, 'reason': 'No performance data'}
        
        # Calculate consistency score
        avg_performances = []
        for param_val, perfs in performance_by_param.items():
            if perfs:
                avg_performances.append(np.mean(perfs))
        
        if not avg_performances:
            return {'stable': False, 'reason': 'Insufficient data'}
        
        avg_perf = np.mean(avg_performances)
        std_perf = np.std(avg_performances)
        
        # Coefficient of variation (lower = more stable)
        cv = std_perf / (abs(avg_perf) + 1e-8)
        
        # Check stability
        is_stable = cv < 0.5  # Less than 50% variation is considered stable
        
        return {
            'stable': is_stable,
            'coefficient_of_variation': cv,
            'avg_performance': avg_perf,
            'std_performance': std_perf,
            'recommendation': 'USE' if is_stable else 'REVIEW'
        }
    
    def optimize_parameters_grid(self,
                                   param_ranges: Dict[str, List[Any]],
                                   data: pd.DataFrame,
                                   evaluate_fn: Callable) -> Dict[str, Any]:
        """
        Perform grid search over parameter combinations
        """
        best_params = None
        best_performance = float('-inf')
        all_results = []
        
        # Generate parameter combinations
        param_names = list(param_ranges.keys())
        param_values = list(param_ranges.values())
        
        from itertools import product
        combinations = list(product(*param_values))
        
        logger.info(f"Testing {len(combinations)} parameter combinations")
        
        for combo in combinations:
            params = dict(zip(param_names, combo))
            
            # Walk-forward test with these parameters
            wf_results = self.run_walk_forward(
                params,
                data,
                evaluate_fn
            )
            
            # Calculate average test performance
            test_performances = [r.test_metrics.get('total_pnl', 0) for r in wf_results]
            avg_perf = np.mean(test_performances)
            
            all_results.append({
                'params': params,
                'avg_performance': avg_perf,
                'test_results': wf_results
            })
            
            if avg_perf > best_performance:
                best_performance = avg_perf
                best_params = params
        
        # Store best parameters
        self.best_parameters = best_params
        
        logger.info(f"Best parameters: {best_params} with performance: {best_performance:.2f}")
        
        return {
            'best_parameters': best_params,
            'best_performance': best_performance,
            'all_results': all_results
        }
    
    def run_walk_forward(self,
                          parameters: Dict[str, Any],
                          data: pd.DataFrame,
                          evaluate_fn: Callable) -> List[WalkForwardResult]:
        """
        Run walk-forward test with given parameters
        """
        results = []
        
        # Calculate dates
        total_days = self.train_period_days + self.test_period_days
        timestamps = data['timestamp'].values
        
        if len(timestamps) == 0:
            logger.warning("No data provided")
            return results
        
        # Convert timestamps to days if needed
        if timestamps[0] > 1e9:  # Unix timestamp in seconds
            start_date = datetime.fromtimestamp(timestamps[0])
            end_date = datetime.fromtimestamp(timestamps[-1])
        else:  # Already in days or other format
            start_date = datetime(2000, 1, 1)
            end_date = start_date + timedelta(days=len(timestamps))
        
        # Generate walk-forward windows
        current_train_start = start_date
        total_span = end_date - start_date
        
        while True:
            train_start = current_train_start
            train_end = train_start + timedelta(days=self.train_period_days)
            test_start = train_end
            test_end = test_start + timedelta(days=self.test_period_days)
            
            # Check if we've gone past the data
            if test_end > end_date:
                break
            
            # Extract train and test periods
            train_mask = (data['timestamp'] >= train_start.timestamp()) & \
                       (data['timestamp'] < train_end.timestamp())
            test_mask = (data['timestamp'] >= test_start.timestamp()) & \
                      (data['timestamp'] < test_end.timestamp())
            
            train_data = data[train_mask]
            test_data = data[test_mask]
            
            if len(train_data) < self.min_train_period_days:
                break
            
            # Evaluate on train period
            train_metrics = evaluate_fn(train_data, parameters)
            
            # Evaluate on test period
            test_metrics = evaluate_fn(test_data, parameters)
            
            # Store result
            result = WalkForwardResult(
                train_period_start=train_start.timestamp(),
                train_period_end=train_end.timestamp(),
                test_period_start=test_start.timestamp(),
                test_period_end=test_end.timestamp(),
                train_metrics=train_metrics,
                test_metrics=test_metrics,
                parameter_values=parameters,
                is_profitable=test_metrics.get('total_pnl', 0) > 0
            )
            
            results.append(result)
            
            # Move to next window
            current_train_start = train_start + timedelta(days=self.step_days)
        
        # Store results
        self.results.extend(results)
        
        logger.info(f"Completed walk-forward test with {len(results)} windows")
        
        return results
    
    def analyze_parameter_stability(self) -> Dict[str, Any]:
        """
        Analyze stability of parameters across different test periods
        """
        if not self.results:
            return {'error': 'No results available'}
        
        # Group results by parameters
        parameter_performances = {}
        for result in self.results:
            param_key = json.dumps(result.parameter_values, sort_keys=True)
            if param_key not in parameter_performances:
                parameter_performances[param_key] = []
            parameter_performances[param_key].append(
                result.test_metrics.get('total_pnl', 0)
            )
        
        # Analyze stability
        stability_analysis = {}
        for param_key, perfs in parameter_performances.items():
            params = json.loads(param_key)
            avg_perf = np.mean(perfs)
            std_perf = np.std(perfs)
            cv = std_perf / (abs(avg_perf) + 1e-8)
            
            stability_analysis[param_key] = {
                'parameters': params,
                'avg_performance': avg_perf,
                'std_performance': std_perf,
                'coefficient_of_variation': cv,
                'stable': cv < 0.5,
                'profitable_windows': sum(1 for p in perfs if p > 0),
                'total_windows': len(perfs)
            }
        
        # Find most stable profitable parameters
        stable_params = [v for v in stability_analysis.values() if v['stable'] and v['avg_performance'] > 0]
        
        if stable_params:
            # Sort by profitability
            stable_params.sort(key=lambda x: x['avg_performance'], reverse=True)
            best_stable = stable_params[0]
        else:
            best_stable = None
        
        return {
            'total_windows': len(self.results),
            'profitable_windows': sum(1 for r in self.results if r.is_profitable),
            'stability_analysis': stability_analysis,
            'best_stable_parameters': best_stable
        }
    
    def save_results(self, filepath: str):
        """
        Save walk-forward results to file
        """
        results_data = []
        for result in self.results:
            results_data.append({
                'train_period_start': result.train_period_start,
                'train_period_end': result.train_period_end,
                'test_period_start': result.test_period_start,
                'test_period_end': result.test_period_end,
                'train_metrics': result.train_metrics,
                'test_metrics': result.test_metrics,
                'parameter_values': result.parameter_values,
                'is_profitable': result.is_profitable
            })
        
        with open(filepath, 'w') as f:
            json.dump({
                'results': results_data,
                'best_parameters': self.best_parameters,
                'parameter_history': self.parameter_history
            }, f, indent=2, default=str)
        
        logger.info(f"Saved {len(results_data)} results to {filepath}")
    
    def load_results(self, filepath: str):
        """
        Load walk-forward results from file
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Restore results
        self.results = []
        for r in data.get('results', []):
            result = WalkForwardResult(
                train_period_start=r['train_period_start'],
                train_period_end=r['train_period_end'],
                test_period_start=r['test_period_start'],
                test_period_end=r['test_period_end'],
                train_metrics=r['train_metrics'],
                test_metrics=r['test_metrics'],
                parameter_values=r['parameter_values'],
                is_profitable=r['is_profitable']
            )
            self.results.append(result)
        
        self.best_parameters = data.get('best_parameters')
        self.parameter_history = data.get('parameter_history', [])
        
        logger.info(f"Loaded {len(self.results)} results from {filepath}")

class ParameterOptimizer:
    """
    Parameter optimizer with safety constraints to prevent overfitting
    """
    
    def __init__(self, 
                 max_iterations: int = 100,
                 exploration_rate: float = 0.3,
                 exploitation_rate: float = 0.7):
        self.max_iterations = max_iterations
        self.exploration_rate = exploration_rate
        self.exploitation_rate = exploitation_rate
        
        self.current_parameters = {}
        self.performance_history = []
        self.best_parameters = None
        self.best_performance = float('-inf')
        
    def optimize(self,
                  initial_params: Dict[str, Any],
                  param_bounds: Dict[str, Tuple[float, float]],
                  evaluate_fn: Callable) -> Dict[str, Any]:
        """
        Perform optimization with exploration-exploitation balancing
        """
        self.current_parameters = initial_params.copy()
        
        for iteration in range(self.max_iterations):
            # Decide whether to explore or exploit
            exploration = np.random.random() < self.exploration_rate
            
            # Generate new parameters
            if exploration:
                # Random exploration within bounds
                new_params = {}
                for param_name, bounds in param_bounds.items():
                    new_params[param_name] = np.random.uniform(bounds[0], bounds[1])
            else:
                # Small random modification of current best
                new_params = self.current_parameters.copy()
                param_name = np.random.choice(list(param_bounds.keys()))
                bounds = param_bounds[param_name]
                
                # Small step from current value
                current_val = new_params.get(param_name, bounds[0])
                step_size = (bounds[1] - bounds[0]) * 0.1
                new_val = current_val + np.random.uniform(-step_size, step_size)
                new_params[param_name] = np.clip(new_val, bounds[0], bounds[1])
            
            # Evaluate new parameters
            performance = evaluate_fn(new_params)
            
            # Update history
            self.performance_history.append({
                'iteration': iteration,
                'parameters': new_params.copy(),
                'performance': performance,
                'exploration': exploration
            })
            
            # Update current parameters if better
            if performance > self.best_performance:
                self.best_performance = performance
                self.best_parameters = new_params.copy()
                self.current_parameters = new_params.copy()
        
        logger.info(f"Optimization complete: best_performance={self.best_performance:.4f}")
        
        return self.best_parameters
    
    def get_parameter_trajectory(self) -> List[Dict]:
        """
        Get the trajectory of parameter optimization
        """
        return self.performance_history
    
    def save_optimizer_state(self, filepath: str):
        """
        Save optimizer state
        """
        state = {
            'current_parameters': self.current_parameters,
            'best_parameters': self.best_parameters,
            'best_performance': self.best_performance,
            'performance_history': self.performance_history
        }
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"Optimizer state saved to {filepath}")
    
    def load_optimizer_state(self, filepath: str):
        """
        Load optimizer state
        """
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        self.current_parameters = state['current_parameters']
        self.best_parameters = state['best_parameters']
        self.best_performance = state['best_performance']
        self.performance_history = state['performance_history']
        
        logger.info(f"Optimizer state loaded from {filepath}")

def create_walk_forward_backtester(**kwargs) -> WalkForwardBacktester:
    """
    Factory function to create walk-forward backtester
    """
    return WalkForwardBacktester(**kwargs)