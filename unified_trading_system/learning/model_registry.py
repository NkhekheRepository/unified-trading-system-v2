"""
Model Registry Module for Trading System
Manages model versions, deployment, and A/B testing
"""

import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json
import os
import shutil
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class ModelVersion:
    """Model version information"""
    version_id: str
    model_type: str
    created_at: float
    performance_metrics: Dict[str, float]
    config: Dict[str, Any]
    file_path: str
    is_active: bool = False
    is_production: bool = False

class ModelRegistry:
    """
    Registry for managing multiple model versions and deployments
    """
    
    def __init__(self, base_path: str = "./models"):
        self.base_path = base_path
        self.models: Dict[str, List[ModelVersion]] = {}
        self.active_models: Dict[str, str] = {}  # model_name -> version_id
        self.production_models: Dict[str, str] = {}
        
        # Ensure directory exists
        os.makedirs(base_path, exist_ok=True)
        
        # Load existing models
        self._load_registry()
    
    def _load_registry(self):
        """
        Load registry from disk
        """
        registry_file = os.path.join(self.base_path, 'registry.json')
        
        if os.path.exists(registry_file):
            with open(registry_file, 'r') as f:
                data = json.load(f)
            
            # Restore models
            for model_name, versions in data.get('models', {}).items():
                self.models[model_name] = []
                for v in versions:
                    self.models[model_name].append(ModelVersion(**v))
            
            # Restore active/production
            self.active_models = data.get('active_models', {})
            self.production_models = data.get('production_models', {})
            
            logger.info(f"Loaded registry with {len(self.models)} models")
        else:
            logger.info("No existing registry found, starting fresh")
    
    def _save_registry(self):
        """
        Save registry to disk
        """
        registry_file = os.path.join(self.base_path, 'registry.json')
        
        data = {
            'models': {
                name: [vars(v) for v in versions] 
                for name, versions in self.models.items()
            },
            'active_models': self.active_models,
            'production_models': self.production_models
        }
        
        with open(registry_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info("Registry saved")
    
    def register_model(self,
                     model_name: str,
                     model_type: str,
                     performance_metrics: Dict[str, float],
                     config: Dict[str, Any],
                     file_path: str) -> str:
        """
        Register a new model version
        """
        # Generate version ID
        timestamp = datetime.now().timestamp()
        version_id = f"{model_name}_{timestamp:.0f}"
        
        # Create model version
        version = ModelVersion(
            version_id=version_id,
            model_type=model_type,
            created_at=timestamp,
            performance_metrics=performance_metrics,
            config=config,
            file_path=file_path,
            is_active=False,
            is_production=False
        )
        
        # Add to registry
        if model_name not in self.models:
            self.models[model_name] = []
        
        self.models[model_name].append(version)
        
        # Save registry
        self._save_registry()
        
        logger.info(f"Registered model version: {version_id}")
        
        return version_id
    
    def activate_model(self, model_name: str, version_id: str) -> bool:
        """
        Activate a model version for inference
        """
        if model_name not in self.models:
            logger.warning(f"Model {model_name} not found in registry")
            return False
        
        # Find version
        version = None
        for v in self.models[model_name]:
            if v.version_id == version_id:
                version = v
                break
        
        if version is None:
            logger.warning(f"Version {version_id} not found for model {model_name}")
            return False
        
        # Deactivate previous active
        if model_name in self.active_models:
            prev_version_id = self.active_models[model_name]
            for v in self.models[model_name]:
                if v.version_id == prev_version_id:
                    v.is_active = False
                    break
        
        # Activate new version
        version.is_active = True
        self.active_models[model_name] = version_id
        
        # Save
        self._save_registry()
        
        logger.info(f"Activated model {model_name} version {version_id}")
        
        return True
    
    def promote_to_production(self, model_name: str, version_id: str) -> bool:
        """
        Promote a model version to production
        """
        if model_name not in self.models:
            logger.warning(f"Model {model_name} not found in registry")
            return False
        
        # Find version
        version = None
        for v in self.models[model_name]:
            if v.version_id == version_id:
                version = v
                break
        
        if version is None:
            logger.warning(f"Version {version_id} not found for model {model_name}")
            return False
        
        # Check performance
        if version.performance_metrics.get('sharpe_ratio', 0) < 1.0:
            logger.warning(f"Model Sharpe ratio {version.performance_metrics.get('sharpe_ratio')} below threshold")
            # Still allow but warn
        
        # Demote previous production
        if model_name in self.production_models:
            prev_version_id = self.production_models[model_name]
            for v in self.models[model_name]:
                if v.version_id == prev_version_id:
                    v.is_production = False
                    break
        
        # Promote new version
        version.is_production = True
        self.production_models[model_name] = version_id
        
        # Save
        self._save_registry()
        
        logger.info(f"Promoted model {model_name} version {version_id} to production")
        
        return True
    
    def rollback(self, model_name: str) -> bool:
        """
        Rollback to previous production model version
        """
        if model_name not in self.models or not self.models[model_name]:
            return False
        
        # Find previous production version
        for v in self.models[model_name]:
            if v.is_production:
                logger.info(f"Model {model_name} already at production version {v.version_id}")
                return True
        
        # Otherwise, activate the last version
        versions = self.models[model_name]
        if versions:
            last_version = versions[-1]
            self.promote_to_production(model_name, last_version.version_id)
            return True
        
        return False
    
    def get_active_version(self, model_name: str) -> Optional[ModelVersion]:
        """
        Get currently active model version
        """
        if model_name not in self.active_models:
            return None
        
        version_id = self.active_models[model_name]
        
        for v in self.models.get(model_name, []):
            if v.version_id == version_id:
                return v
        
        return None
    
    def get_production_version(self, model_name: str) -> Optional[ModelVersion]:
        """
        Get production model version
        """
        if model_name not in self.production_models:
            return None
        
        version_id = self.production_models[model_name]
        
        for v in self.models.get(model_name, []):
            if v.version_id == version_id:
                return v
        
        return None
    
    def get_model_versions(self, model_name: str) -> List[ModelVersion]:
        """
        Get all versions of a model
        """
        return self.models.get(model_name, [])
    
    def compare_versions(self, model_name: str) -> Dict[str, Any]:
        """
        Compare different versions of a model
        """
        versions = self.get_model_versions(model_name)
        
        if not versions:
            return {'error': 'No versions found'}
        
        comparisons = []
        for v in versions:
            comparisons.append({
                'version_id': v.version_id,
                'created_at': v.created_at,
                'performance': v.performance_metrics,
                'is_active': v.is_active,
                'is_production': v.is_production
            })
        
        return {
            'model_name': model_name,
            'total_versions': len(versions),
            'versions': comparisons,
            'production_version': self.production_models.get(model_name),
            'active_version': self.active_models.get(model_name)
        }
    
    def cleanup_old_versions(self, model_name: str, keep_n: int = 5):
        """
        Remove old model versions, keeping only the N best
        """
        if model_name not in self.models:
            return
        
        versions = self.models[model_name]
        
        if len(versions) <= keep_n:
            return
        
        # Sort by performance (best first)
        sorted_versions = sorted(
            versions, 
            key=lambda v: v.performance_metrics.get('sharpe_ratio', 0),
            reverse=True
        )
        
        # Keep top N
        versions_to_keep = sorted_versions[:keep_n]
        
        # Remove old versions
        for v in versions:
            if v not in versions_to_keep:
                # Remove file if exists
                if os.path.exists(v.file_path):
                    try:
                        os.remove(v.file_path)
                    except:
                        pass
        
        # Update registry
        self.models[model_name] = versions_to_keep
        self._save_registry()
        
        logger.info(f"Cleaned up {model_name}, kept {keep_n} versions")

class ABTestManager:
    """
    Manager for A/B testing of models
    """
    
    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self.tests: Dict[str, Dict] = {}
    
    def create_test(self,
                 test_name: str,
                 model_a: str,
                 model_b: str,
                 traffic_split: float = 0.5,
                 duration_days: int = 7) -> str:
        """
        Create A/B test
        """
        test_id = f"test_{len(self.tests)}_{datetime.now().timestamp()}"
        
        self.tests[test_id] = {
            'test_id': test_id,
            'test_name': test_name,
            'model_a': model_a,
            'model_b': model_b,
            'traffic_split': traffic_split,
            'duration_days': duration_days,
            'start_time': datetime.now().timestamp(),
            'status': 'RUNNING',
            'results': {
                'model_a': {'predictions': 0, 'correct': 0},
                'model_b': {'predictions': 0, 'correct': 0}
            }
        }
        
        logger.info(f"Created A/B test: {test_name}")
        
        return test_id
    
    def record_prediction(self, test_id: str, model_name: str, correct: bool):
        """
        Record prediction result
        """
        if test_id not in self.tests:
            logger.warning(f"Test {test_id} not found")
            return
        
        self.tests[test_id]['results'][model_name]['predictions'] += 1
        if correct:
            self.tests[test_id]['results'][model_name]['correct'] += 1
    
    def get_test_results(self, test_id: str) -> Dict[str, Any]:
        """
        Get A/B test results
        """
        if test_id not in self.tests:
            return {'error': 'Test not found'}
        
        test = self.tests[test_id]
        results = test['results']
        
        # Calculate accuracies
        accuracy_a = results['model_a']['correct'] / results['model_a']['predictions'] if results['model_a']['predictions'] > 0 else 0
        accuracy_b = results['model_b']['correct'] / results['model_b']['predictions'] if results['model_b']['predictions'] > 0 else 0
        
        return {
            'test_name': test['test_name'],
            'status': test['status'],
            'model_a': {
                'name': test['model_a'],
                'predictions': results['model_a']['predictions'],
                'accuracy': accuracy_a
            },
            'model_b': {
                'name': test['model_b'],
                'predictions': results['model_b']['predictions'],
                'accuracy': accuracy_b
            },
            'winner': 'model_a' if accuracy_a > accuracy_b else 'model_b',
            'improvement': abs(accuracy_a - accuracy_b) / max(accuracy_a, accuracy_b) if max(accuracy_a, accuracy_b) > 0 else 0
        }
    
    def complete_test(self, test_id: str) -> Optional[str]:
        """
        Complete A/B test and return winner
        """
        if test_id not in self.tests:
            return None
        
        results = self.get_test_results(test_id)
        winner = results.get('winner')
        
        self.tests[test_id]['status'] = 'COMPLETED'
        self.tests[test_id]['winner'] = winner
        
        logger.info(f"A/B test {test_id} completed. Winner: {winner}")
        
        return winner

def create_model_registry(base_path: str = "./models") -> ModelRegistry:
    """
    Factory function to create model registry
    """
    return ModelRegistry(base_path)

def create_ab_test_manager(registry: ModelRegistry) -> ABTestManager:
    """
    Factory function to create A/B test manager
    """
    return ABTestManager(registry)