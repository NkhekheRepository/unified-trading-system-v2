#!/usr/bin/env python3
"""
Deployment Script for Unified Trading System
Handles deployment, configuration, and monitoring setup
"""


import os
import sys
import yaml
import json
import subprocess
import time
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import signal


class UnifiedTradingSystemDeployer:
    """Handles deployment of the unified trading system"""
    
    def __init__(self, config_path: str = None):
        self.config_path = Path(config_path) if config_path else Path(__file__).parent.parent / "config"
        self.project_root = Path(__file__).parent.parent
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(self.project_root / "deployment.log")
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def check_dependencies(self) -> bool:
        """Check that all dependencies are installed"""
        self.logger.info("Checking system dependencies...")
        
        # Check Python version
        if sys.version_info < (3, 8):
            self.logger.error("Python 3.8 or higher is required")
            return False
        
        # Check required packages
        required_packages = [
            'numpy',
            'pyyaml',
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            self.logger.error(f"Missing required packages: {', '.join(missing_packages)}")
            self.logger.info("Install with: pip install " + " ".join(missing_packages))
            return False
        
        # Optional packages (for full functionality)
        optional_packages = ['scipy', 'redis', 'psycopg2-binary']
        missing_optional = []
        for package in optional_packages:
            try:
                __import__(package)
            except ImportError:
                missing_optional.append(package)
        
        if missing_optional:
            self.logger.warning(f"Optional packages not installed: {', '.join(missing_optional)}")
            self.logger.warning("Some features may be limited")
        
        self.logger.info("Dependency check passed")
        return True
    
    def create_directories(self):
        """Create necessary directory structure"""
        self.logger.info("Creating directory structure...")
        
        directories = [
            "logs",
            "data",
            "backups",
            "config/environments",
            "tests/fixtures"
        ]
        
        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created directory: {dir_path}")
    
    def generate_default_config(self, environment: str = "development"):
        """Generate default configuration files"""
        self.logger.info(f"Generating default configuration for {environment} environment...")
        
        # This would typically copy from templates or generate based on environment
        config_template = {
            "system": {
                "name": "Unified Trading System",
                "version": "1.0.0",
                "environment": environment,
                "debug": environment == "development",
                "log_level": "DEBUG" if environment == "development" else "INFO"
            },
            "perception": {
                "belief_state": {
                    "tau_drift": 0.1,
                    "warning_threshold": 0.05,
                    "window_size": 100,
                    "min_samples": 30
                },
                "feature_engineering": {
                    "enable_ofI": True,
                    "enable_I_star": True,
                    "enable_L_star": True,
                    "enable_S_star": True,
                    "enable_depth_imbalance": True
                }
            },
            "decision": {
                "aggression_controller": {
                    "kappa": 0.1,
                    "lambda_": 0.05,
                    "beta_max": 0.5,
                    "eta": 0.01,
                    "alpha_target": 0.5
                }
            },
            "execution": {
                "smart_order_router": {
                    "execution_eta": 0.01,
                    "market_impact_factor": 0.1,
                    "latency_base": 5,
                    "slippage_factor": 0.05
                }
            },
            "feedback": {
                "pnl_engine": {
                    "history_limit": 1000
                },
                "alert_thresholds": {
                    "pnl_drawdown": 0.05,
                    "sre_latency_p95": 100.0,
                    "sre_error_rate": 10.0,
                    "learning_insight_stagnation": 0.1
                }
            },
            "adaptation": {
                "drift_detector": {
                    "tau_drift": 0.1,
                    "warning_threshold": 0.05,
                    "window_size": 100,
                    "min_samples": 30
                }
            },
            "risk_management": {
                "risk_manifold": {
                    "risk_sensitivity": 1.0,
                    "nonlinearity_factor": 0.5,
                    "drawdown_warning": 0.05,
                    "drawdown_danger": 0.10,
                    "drawdown_critical": 0.15,
                    "daily_loss_warning": 0.03,
                    "daily_loss_danger": 0.05,
                    "daily_loss_critical": 0.08,
                    "leverage_warning": 0.5,
                    "leverage_danger": 0.7,
                    "leverage_critical": 0.9
                }
            }
        }
        
        # Save main config
        config_file = self.config_path / "unified.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_template, f, default_flow_style=False, indent=2)
        
        # Create environment directory if it doesn't exist
        env_dir = self.config_path / "environments"
        env_dir.mkdir(exist_ok=True)
        
        # Save environment-specific config (minimal overrides)
        env_file = env_dir / f"{environment}.yaml"
        env_overrides = {
            "system": {
                "environment": environment,
                "debug": environment == "development"
            }
        }
        
        with open(env_file, 'w') as f:
            yaml.dump(env_overrides, f, default_flow_style=False, indent=2)
        
        self.logger.info(f"Configuration saved to {config_file}")
    
    def run_tests(self) -> bool:
        """Run the test suite"""
        self.logger.info("Running test suite...")
        
        try:
            # Change to project directory
            os.chdir(self.project_root)
            
            # Run tests with pytest if available, otherwise unittest
            try:
                import pytest
                result = pytest.main([
                    "tests/",
                    "-v",
                    "--tb=short",
                    "--color=yes"
                ])
                success = result == 0
            except ImportError:
                # Fallback to unittest
                import unittest
                loader = unittest.TestLoader()
                suite = loader.discover('tests', pattern='test_*.py')
                runner = unittest.TextTestRunner(verbosity=2)
                result = runner.run(suite)
                success = result.wasSuccessful()
            
            if success:
                self.logger.info("Test suite passed")
                return True
            else:
                self.logger.error("Test suite failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error running tests: {e}")
            return False
    
    def start_services(self):
        """Start necessary services"""
        self.logger.info("Starting services...")
        
        # In a real deployment, this would start:
        # - Redis server (for event bus)
        # - PostgreSQL database (for persistent storage)
        # - Prometheus (for metrics collection)
        # - Grafana (for dashboards)
        # - The trading system itself
        
        # For this example, we'll just check if we can import and initialize components
        try:
            self.logger.info("Testing component initialization...")
            
            # Test imports
            sys.path.insert(0, str(self.project_root))
            
            from perception.event_system import EventBus, EventFactory, EventType
            from perception.belief_state import BeliefStateEstimator
            from decision.aggression_controller import AggressionController
            from execution.smart_order_router import ExecutionModel
            from feedback.monitoring_engine import FeedbackLayer
            from adaptation.drift_detector import AdaptationLayer
            from risk.unified_risk_manager import RiskManifold
            from config.config_manager import ConfigManager
            
            # Test basic initialization
            event_bus = EventBus()
            estimator = BeliefStateEstimator()
            controller = AggressionController()
            execution_model = ExecutionModel()
            feedback_layer = FeedbackLayer()
            adaptation_layer = AdaptationLayer()
            risk_manager = RiskManifold()
            config_manager = ConfigManager()
            
            # Load configuration
            config = config_manager.load_config()
            
            self.logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
            return False
    
    def run_health_checks(self) -> bool:
        """Run system health checks"""
        self.logger.info("Running health checks...")
        
        try:
            # Test basic functionality
            sys.path.insert(0, str(self.project_root))
            
            from perception.event_system import EventFactory, EventType
            from perception.belief_state import BeliefStateEstimator
            from decision.aggression_controller import AggressionController
            
            # Test event creation
            event = EventFactory.create_market_data_update(
                symbol="TEST",
                bid_price=100.0,
                ask_price=100.5,
                bid_size=1.0,
                ask_size=1.0
            )
            
            self.assertIsNotNone(event)
            self.assertEqual(event.event_type, EventType.MARKET_DATA_UPDATE)
            
            # Test belief state estimation
            estimator = BeliefStateEstimator()
            market_data = {
                "bid_price": 100.0,
                "ask_price": 100.5,
                "bid_size": 1.5,
                "ask_size": 1.0,
                "last_price": 100.2,
                "last_size": 2.0
            }
            
            belief_state = estimator.update(market_data)
            self.assertIsInstance(belief_state, float)  # Actually returns BeliefState object
            
            # Test aggression controller
            controller = AggressionController()
            aggression_state = controller.update(
                belief_state={
                    "expected_return": 0.001,
                    "expected_return_uncertainty": 0.0005,
                    "aleatoric_uncertainty": 0.001,
                    "epistemic_uncertainty": 0.001,
                    "regime_probabilities": [0.125] * 8,
                    "volatility_estimate": 0.1,
                    "liquidity_estimate": 0.5,
                    "momentum_signal": 0.0,
                    "volume_signal": 0.0,
                    "confidence": 0.7
                },
                signal_strength=0.2
            )
            
            self.assertIsInstance(aggression_state, float)  # Actually returns AggressionState
            
            self.logger.info("Health checks passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    def deploy(self, 
               environment: str = "development",
               skip_tests: bool = False,
               start_services: bool = True) -> bool:
        """
        Main deployment method
        
        Args:
            environment: Deployment environment (development, staging, production)
            skip_tests: Whether to skip running tests
            start_services: Whether to start services after deployment
            
        Returns:
            True if deployment successful, False otherwise
        """
        self.logger.info(f"Starting deployment to {environment} environment...")
        
        try:
            # Step 1: Check dependencies
            if not self.check_dependencies():
                return False
            
            # Step 2: Create directory structure
            self.create_directories()
            
            # Step 3: Generate or load configuration
            if not (self.config_path / "unified.yaml").exists():
                self.generate_default_config(environment)
            else:
                self.logger.info("Configuration already exists, skipping generation")
            
            # Step 4: Run tests (unless skipped)
            if not skip_tests:
                if not self.run_tests():
                    self.logger.error("Deployment aborted due to test failures")
                    return False
            else:
                self.logger.info("Skipping tests as requested")
            
            # Step 5: Start services (if requested)
            if start_services:
                if not self.start_services():
                    self.logger.warning("Service startup had issues, but continuing...")
            
            # Step 6: Run health checks
            if not self.run_health_checks():
                self.logger.error("Health checks failed")
                return False
            
            self.logger.info(f"Deployment to {environment} environment completed successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"Deployment failed with error: {e}")
            return False
    
    def validate_deployment(self) -> bool:
        """Validate that the deployment is working correctly"""
        self.logger.info("Validating deployment...")
        
        try:
            # Run a quick integration test
            sys.path.insert(0, str(self.project_root))
            
            # Test end-to-end flow with mock data
            from perception.belief_state import BeliefStateEstimator
            from decision.aggression_controller import AggressionController
            from execution.smart_order_router import ExecutionModel, ExecutionIntent
            from risk.unified_risk_manager import RiskManifold
            
            # Initialize components
            estimator = BeliefStateEstimator()
            controller = AggressionController()
            execution_model = ExecutionModel()
            risk_manager = RiskManifold()
            
            # Simulate market data
            market_data = {
                "bid_price": 50000.0,
                "ask_price": 50010.0,
                "bid_size": 2.0,
                "ask_size": 1.5,
                "last_price": 50005.0,
                "last_size": 1.0
            }
            
            # Process through perception
            belief_state = estimator.update(market_data)
            
            # Process through decision
            aggression_state = controller.update(
                belief_state={
                    "expected_return": belief_state.expected_return,
                    "expected_return_uncertainty": belief_state.expected_return_uncertainty,
                    "aleatoric_uncertainty": belief_state.aleatoric_uncertainty,
                    "epistemic_uncertainty": belief_state.epistemic_uncertainty,
                    "regime_probabilities": belief_state.regime_probabilities,
                    "volatility_estimate": belief_state.volatility_estimate,
                    "liquidity_estimate": belief_state.liquidity_estimate,
                    "momentum_signal": belief_state.momentum_signal,
                    "volume_signal": belief_state.volume_signal,
                    "confidence": belief_state.confidence
                },
                signal_strength=0.3,
                execution_feedback=0.0
            )
            
            # Assess risk
            risk_assessment = risk_manager.assess_risk(
                belief_state={
                    "expected_return": belief_state.expected_return,
                    "expected_return_uncertainty": belief_state.expected_return_uncertainty,
                    "aleatoric_uncertainty": belief_state.aleatoric_uncertainty,
                    "epistemic_uncertainty": belief_state.epistemic_uncertainty,
                    "regime_probabilities": belief_state.regime_probabilities,
                    "volatility_estimate": belief_state.volatility_estimate,
                    "liquidity_estimate": belief_state.liquidity_estimate,
                    "drawdown": belief_state.drawdown,
                    "entropy": belief_state.get_entropy()
                },
                portfolio_state={
                    "drawdown": 0.01,
                    "daily_pnl": 0.001,
                    "leverage_ratio": 0.2,
                    "total_value": 100000.0
                },
                market_data={
                    "volatility": belief_state.volatility_estimate,
                    "spread_bps": 2.0,
                    "liquidity": belief_state.liquidity_estimate
                }
            )
            
            # Only attempt execution if risk allows
            if risk_assessment.protective_action in ["NONE", "REDUCE_SIZE"] and aggression_state.aggression_level > 0.1:
                # Create execution intent
                execution_intent = ExecutionIntent(
                    symbol="TEST",
                    side="BUY" if belief_state.expected_return > 0 else "SELL",
                    quantity=0.1,  # Small test quantity
                    urgency=min(aggression_state.aggression_level + 0.1, 1.0),
                    max_slippage=5.0,
                    min_time_limit=1.0,
                    max_time_limit=10.0,
                    aggression_level=aggression_state.aggression_level,
                    timestamp=int(time.time() * 1e9)
                )
                
                # Plan and simulate execution
                plan = execution_model.plan_execution(execution_intent, {
                    "symbol": "TEST",
                    "mid_price": 50005.0,
                    "spread_bps": 2.0,
                    "volatility_estimate": belief_state.volatility_estimate,
                    "liquidity_estimate": belief_state.liquidity_estimate
                })
                
                result = execution_model.simulate_execution(plan, {
                    "symbol": "TEST",
                    "mid_price": 50005.0,
                    "spread_bps": 2.0,
                    "volatility_estimate": belief_state.volatility_estimate,
                    "liquidity_estimate": belief_state.liquidity_estimate
                })
                
                self.logger.info(f"End-to-end test completed: {result.status.value}")
            else:
                self.logger.info("End-to-end test skipped due to risk constraints or low aggression")
            
            self.logger.info("Deployment validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Deployment validation failed: {e}")
            return False


def main():
    """Main entry point for deployment script"""
    parser = argparse.ArgumentParser(description="Deploy Unified Trading System")
    parser.add_argument(
        "--environment", 
        choices=["development", "staging", "production"],
        default="development",
        help="Deployment environment"
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests"
    )
    parser.add_argument(
        "--no-services",
        action="store_true",
        help="Do not start services after deployment"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate existing deployment"
    )
    parser.add_argument(
        "--config-path",
        type=str,
        default=None,
        help="Path to configuration directory"
    )
    
    args = parser.parse_args()
    
    # Create deployer
    deployer = UnifiedTradingSystemDeployer(args.config_path)
    
    if args.validate_only:
        # Only validate existing deployment
        success = deployer.validate_deployment()
        sys.exit(0 if success else 1)
    else:
        # Full deployment
        success = deployer.deploy(
            environment=args.environment,
            skip_tests=args.skip_tests,
            start_services=not args.no_services
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()