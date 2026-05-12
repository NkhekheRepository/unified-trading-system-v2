"""
Configuration Management System for Unified Trading System
Provides validated configuration management with schema validation and environment variable support
"""


import yaml
import os
import json
from typing import Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime
import copy


class ConfigValidationError(Exception):
    """Exception raised when configuration validation fails"""
    pass


class ConfigManager:
    """
    Unified configuration manager that:
    1. Loads configuration from YAML files
    2. Supports environment variable overrides
    3. Provides schema validation
    4. Supports configuration versioning
    5. Provides default values
    """
    
    def __init__(self, config_dir: Union[str, Path] = None):
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "config"
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Configuration cache
        self._config_cache: Dict[str, Any] = {}
        self._schema_cache: Dict[str, Dict] = {}
        
        # Load default schema
        self._load_default_schemas()
    
    def _load_default_schemas(self):
        """Load default configuration schemas"""
        # Main configuration schema
        self._schema_cache["unified"] = {
            "type": "object",
            "properties": {
                "system": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "string"},
                        "environment": {"type": "string", "enum": ["development", "staging", "production"]},
                        "debug": {"type": "boolean"},
                        "log_level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]}
                    },
                    "required": ["name", "version", "environment"]
                },
                "perception": {
                    "type": "object",
                    "properties": {
                        "belief_state": {
                            "type": "object",
                            "properties": {
                                "tau_drift": {"type": "number", "minimum": 0.01, "maximum": 1.0},
                                "warning_threshold": {"type": "number", "minimum": 0.0, "maximum": 0.5},
                                "window_size": {"type": "integer", "minimum": 10, "maximum": 1000},
                                "min_samples": {"type": "integer", "minimum": 5, "maximum": 100}
                            }
                        },
                        "feature_engineering": {
                            "type": "object",
                            "properties": {
                                "enable_ofI": {"type": "boolean"},
                                "enable_I_star": {"type": "boolean"},
                                "enable_L_star": {"type": "boolean"},
                                "enable_S_star": {"type": "boolean"},
                                "enable_depth_imbalance": {"type": "boolean"}
                            }
                        }
                    }
                },
                "decision": {
                    "type": "object",
                    "properties": {
                        "aggression_controller": {
                            "type": "object",
                            "properties": {
                                "kappa": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                                "lambda_": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                                "beta_max": {"type": "number", "minimum": 0.0, "maximum": 2.0},
                                "eta": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                                "alpha_target": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                            }
                        }
                    }
                },
                "execution": {
                    "type": "object",
                    "properties": {
                        "smart_order_router": {
                            "type": "object",
                            "properties": {
                                "execution_eta": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                                "market_impact_factor": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                                "latency_base": {"type": "integer", "minimum": 1, "maximum": 100},
                                "slippage_factor": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                            }
                        }
                    }
                },
                "feedback": {
                    "type": "object",
                    "properties": {
                        "pnl_engine": {
                            "type": "object",
                            "properties": {
                                "history_limit": {"type": "integer", "minimum": 100, "maximum": 10000}
                            }
                        },
                        "alert_thresholds": {
                            "type": "object",
                            "properties": {
                                "pnl_drawdown": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                                "sre_latency_p95": {"type": "number", "minimum": 0.0, "maximum": 1000.0},
                                "sre_error_rate": {"type": "number", "minimum": 0.0, "maximum": 100.0},
                                "learning_insight_stagnation": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                            }
                        }
                    }
                },
                "adaptation": {
                    "type": "object",
                    "properties": {
                        "drift_detector": {
                            "type": "object",
                            "properties": {
                                "tau_drift": {"type": "number", "minimum": 0.01, "maximum": 1.0},
                                "warning_threshold": {"type": "number", "minimum": 0.0, "maximum": 0.5},
                                "window_size": {"type": "integer", "minimum": 10, "maximum": 1000},
                                "min_samples": {"type": "integer", "minimum": 5, "maximum": 100}
                            }
                        }
                    }
                },
                "risk_management": {
                    "type": "object",
                    "properties": {
                        "risk_manifold": {
                            "type": "object",
                            "properties": {
                                "risk_sensitivity": {"type": "number", "minimum": 0.0, "maximum": 5.0},
                                "nonlinearity_factor": {"type": "number", "minimum": 0.0, "maximum": 2.0},
                                "drawdown_warning": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                                "drawdown_danger": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                                "drawdown_critical": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                                "daily_loss_warning": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                                "daily_loss_danger": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                                "daily_loss_critical": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                                 "leverage_warning": {"type": "number", "minimum": 0.0, "maximum": 50.0},
                                 "leverage_danger": {"type": "number", "minimum": 0.0, "maximum": 50.0},
                                 "leverage_critical": {"type": "number", "minimum": 0.0, "maximum": 50.0}
                            }
                        }
                    }
                }
            },
            "required": ["system"]
        }
    
    def load_config(self, config_name: str = "unified", environment: str = None) -> Dict[str, Any]:
        """
        Load configuration from file with environment variable overrides
        
        Args:
            config_name: Name of configuration file (without .yaml extension)
            environment: Environment name (optional, uses SYSTEM_ENV or defaults to development)
            
        Returns:
            Merged configuration dictionary
        """
        # Determine environment
        if environment is None:
            environment = os.environ.get("SYSTEM_ENV", "development")
        
        # Check cache
        cache_key = f"{config_name}_{environment}"
        if cache_key in self._config_cache:
            return copy.deepcopy(self._config_cache[cache_key])
        
        # Load base configuration
        config_file = self.config_dir / f"{config_name}.yaml"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}
        
        # Load environment-specific overrides
        env_file = self.config_dir / "environments" / f"{environment}.yaml"
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_config = yaml.safe_load(f) or {}
            config = self._deep_merge(config, env_config)
        
        # Apply environment variable overrides
        config = self._apply_env_overrides(config)
        
        # Apply defaults
        config = self._apply_defaults(config)
        
        # Validate configuration
        self._validate_config(config, config_name)
        
        # Cache result
        self._config_cache[cache_key] = copy.deepcopy(config)
        
        return config
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = copy.deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result
    
    def _apply_env_overrides(self, config: Dict) -> Dict:
        """Apply environment variable overrides to configuration"""
        # Format: SYSTEM_SECTION_SUBSECTION_PARAMETER=value
        env_prefix = "SYSTEM_"
        
        for key, value in os.environ.items():
            if key.startswith(env_prefix):
                # Convert SYSTEM_PERCEPTION_BELIEF_STATE_TAU_DRIFT -> perception.belief_state.tau_drift
                config_key = key[len(env_prefix):].lower()
                key_parts = config_key.split("_")
                
                # Navigate to the correct location in config
                current = config
                try:
                    for part in key_parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    
                    # Set the value (try to convert type)
                    final_key = key_parts[-1]
                    current[final_key] = self._convert_env_value(value)
                except Exception as e:
                    # If we can't navigate the structure, skip this override
                    pass
        
        return config
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type"""
        # Try boolean
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        
        # Try integer
        try:
            if "." not in value:
                return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Try JSON (for lists, dicts)
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Return as string
        return value
    
    def _apply_defaults(self, config: Dict) -> Dict:
        """Apply default values where missing"""
        # Get the schema for this config type
        schema = self._schema_cache.get("unified", {})
        return self._apply_schema_defaults(config, schema.get("properties", {}))
    
    def _apply_schema_defaults(self, config: Dict, properties: Dict) -> Dict:
        """Apply defaults based on schema properties"""
        result = copy.deepcopy(config)
        
        for prop_name, prop_schema in properties.items():
            if prop_name not in result:
                # If property has a default value, use it
                if "default" in prop_schema:
                    result[prop_name] = copy.deepcopy(prop_schema["default"])
                elif prop_schema.get("type") == "object":
                    # Recursively apply defaults to nested objects
                    result[prop_name] = self._apply_schema_defaults({}, prop_schema.get("properties", {}))
                elif prop_schema.get("type") == "array":
                    # Default empty array
                    result[prop_name] = []
                # For other types, leave as missing (will be handled by validation)
            else:
                # Recursively apply defaults to nested objects
                if (prop_schema.get("type") == "object" and 
                    isinstance(result[prop_name], dict) and 
                    "properties" in prop_schema):
                    result[prop_name] = self._apply_schema_defaults(
                        result[prop_name], 
                        prop_schema["properties"]
                    )
                elif (prop_schema.get("type") == "array" and 
                      isinstance(result[prop_name], list) and 
                      "items" in prop_schema and 
                      prop_schema["items"].get("type") == "object"):
                    # Apply defaults to array of objects
                    result[prop_name] = [
                        self._apply_schema_defaults(item, prop_schema["items"].get("properties", {}))
                        for item in result[prop_name]
                    ]
        
        return result
    
    def _validate_config(self, config: Dict, config_name: str):
        """Validate configuration against schema"""
        schema = self._schema_cache.get(config_name, self._schema_cache.get("unified", {}))
        self._validate_against_schema(config, schema, config_name)
    
    def _validate_against_schema(self, config: Dict, schema: Dict, path: str = ""):
        """Recursively validate configuration against schema"""
        # Handle full schema structure: check if this is a full schema with properties
        if "properties" in schema:
            # This is a full schema object, extract the properties
            properties_schema = schema.get("properties", {})
            required_fields = schema.get("required", [])
            
            # Check required fields at this level
            for field_name in required_fields:
                full_path = f"{path}.{field_name}" if path else field_name
                if field_name not in config:
                    raise ConfigValidationError(f"Required field '{full_path}' is missing")
            
            # Check each property that is present in the config
            for prop_name, prop_value in config.items():
                full_path = f"{path}.{prop_name}" if path else prop_name
                
                # Skip if not in schema (additional properties are allowed by default)
                if prop_name not in properties_schema:
                    continue
                    
                prop_schema = properties_schema[prop_name]
                
                # Validate type and constraints
                self._validate_value(prop_value, prop_schema, full_path)
                
                # Recursively validate nested objects
                prop_type = prop_schema.get("type")
                if prop_type == "object" and isinstance(prop_value, dict):
                    self._validate_against_schema(prop_value, prop_schema, full_path)
                elif prop_type == "array" and isinstance(prop_value, list):
                    item_schema = prop_schema.get("items", {})
                    if item_schema.get("type") == "object":
                        for i, item in enumerate(prop_value):
                            if isinstance(item, dict):
                                self._validate_against_schema(
                                    item, 
                                    item_schema, 
                                    f"{full_path}[{i}]"
                                )
        else:
            # This appears to be already a properties schema (legacy support)
            # Check each property that is present in the config
            for prop_name, prop_value in config.items():
                full_path = f"{path}.{prop_name}" if path else prop_name
                
                # Skip if not in schema (additional properties are allowed by default)
                if prop_name not in schema:
                    continue
                    
                prop_schema = schema[prop_name]
                
                # Validate type and constraints
                self._validate_value(prop_value, prop_schema, full_path)
                
                # Recursively validate nested objects
                prop_type = prop_schema.get("type")
                if prop_type == "object" and isinstance(prop_value, dict):
                    nested_schema = prop_schema.get("properties", {})
                    self._validate_against_schema(prop_value, nested_schema, full_path)
                elif prop_type == "array" and isinstance(prop_value, list):
                    item_schema = prop_schema.get("items", {})
                    if item_schema.get("type") == "object":
                        for i, item in enumerate(prop_value):
                            if isinstance(item, dict):
                                self._validate_against_schema(
                                    item, 
                                    item_schema.get("properties", {}), 
                                    f"{full_path}[{i}]"
                                )
    
    def _validate_value(self, value: Any, schema: Dict, path: str):
        """Validate a single value against its schema"""
        # Type validation
        expected_type = schema.get("type")
        if expected_type:
            type_ok = False
            if expected_type == "string":
                type_ok = isinstance(value, str)
            elif expected_type == "integer":
                type_ok = isinstance(value, int) and not isinstance(value, bool)
            elif expected_type == "number":
                type_ok = isinstance(value, (int, float)) and not isinstance(value, bool)
            elif expected_type == "boolean":
                type_ok = isinstance(value, bool)
            elif expected_type == "array":
                type_ok = isinstance(value, list)
            elif expected_type == "object":
                type_ok = isinstance(value, dict)
            
            if not type_ok:
                raise ConfigValidationError(f"Field '{path}' must be of type {expected_type}, got {type(value).__name__}")
        
        # Range validation for numbers
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                raise ConfigValidationError(f"Field '{path}' must be >= {schema['minimum']}, got {value}")
            if "maximum" in schema and value > schema["maximum"]:
                raise ConfigValidationError(f"Field '{path}' must be <= {schema['maximum']}, got {value}")
        
        # Length validation for strings and arrays
        if isinstance(value, (str, list)):
            if "min_length" in schema and len(value) < schema["min_length"]:
                raise ConfigValidationError(f"Field '{path}' must have length >= {schema['min_length']}, got {len(value)}")
            if "max_length" in schema and len(value) > schema["max_length"]:
                raise ConfigValidationError(f"Field '{path}' must have length <= {schema['max_length']}, got {len(value)}")
        
        # Enum validation
        if "enum" in schema:
            if value not in schema["enum"]:
                raise ConfigValidationError(f"Field '{path}' must be one of {schema['enum']}, got {value}")
        
        # Pattern validation for strings
        if "pattern" in schema and isinstance(value, str):
            import re
            if not re.match(schema["pattern"], value):
                raise ConfigValidationError(f"Field '{path}' must match pattern {schema['pattern']}, got {value}")
    
    def save_config(self, config: Dict, config_name: str = "unified", environment: str = None):
        """Save configuration to file"""
        # Determine environment
        if environment is None:
            environment = os.environ.get("SYSTEM_ENV", "development")
        
        # Save base configuration
        config_file = self.config_dir / f"{config_name}.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        
        # Save environment-specific configuration (only non-default values)
        env_dir = self.config_dir / "environments"
        env_dir.mkdir(exist_ok=True)
        env_file = env_dir / f"{environment}.yaml"
        
        # For simplicity, we'll save the full config as environment-specific
        # In practice, we'd compute the diff from base config
        with open(env_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        
        # Clear cache
        cache_key = f"{config_name}_{environment}"
        if cache_key in self._config_cache:
            del self._config_cache[cache_key]
    
    def get_config_value(self, config: Dict, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation
        
        Args:
            config: Configuration dictionary
            key_path: Dot-separated path (e.g., "system.name")
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split(".")
        current = config
        
        try:
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return default
            return current
        except Exception:
            return default
    
    def set_config_value(self, config: Dict, key_path: str, value: Any) -> Dict:
        """
        Set a configuration value using dot notation
        
        Args:
            config: Configuration dictionary
            key_path: Dot-separated path (e.g., "system.name")
            value: Value to set
            
        Returns:
            Updated configuration dictionary
        """
        keys = key_path.split(".")
        current = config
        
        # Navigate to parent of target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Set the value
        if isinstance(current, dict):
            current[keys[-1]] = value
        
        return config

    def validate_and_load(self, config_name: str = "unified", environment: str = None) -> Dict[str, Any]:
        """
        Convenience method to load and validate configuration
        
        Returns:
            Validated configuration dictionary
        """
        return self.load_config(config_name, environment)

    @classmethod
    def create_default_config(cls, config_dir: Union[str, Path] = None):
        """Create default configuration files"""
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "config"
        config_dir = Path(config_dir)
        config_dir.mkdir(exist_ok=True)
        
        # Create main config file
        main_config_file = config_dir / "unified.yaml"
        if not main_config_file.exists():
            with open(main_config_file, 'w') as f:
                f.write(DEFAULT_CONFIG_TEMPLATE)
        
        # Create environments directory
        env_dir = config_dir / "environments"
        env_dir.mkdir(exist_ok=True)
        
        # Create default environment configs
        environments = ["development", "staging", "production"]
        for env in environments:
            env_file = env_dir / f"{env}.yaml"
            if not env_file.exists():
                # Environment-specific overrides would go here
                # For now, create empty files or minimal overrides
                env_content = f"# {env.title()} Environment Configuration\n# Overrides for {env} environment\n"
                with open(env_file, 'w') as f:
                    f.write(env_content)


# Default configuration template
DEFAULT_CONFIG_TEMPLATE = """
# Unified Trading System Configuration
system:
  name: "Unified Trading System"
  version: "1.0.0"
  environment: "development"
  debug: false
  log_level: "INFO"

perception:
  belief_state:
    tau_drift: 0.1
    warning_threshold: 0.05
    window_size: 100
    min_samples: 30
  feature_engineering:
    enable_ofI: true
    enable_I_star: true
    enable_L_star: true
    enable_S_star: true
    enable_depth_imbalance: true

decision:
  aggression_controller:
    kappa: 0.1
    lambda_: 0.05
    beta_max: 0.5
    eta: 0.01
    alpha_target: 0.5

execution:
  smart_order_router:
    execution_eta: 0.01
    market_impact_factor: 0.1
    latency_base: 5
    slippage_factor: 0.05

feedback:
  pnl_engine:
    history_limit: 1000
  alert_thresholds:
    pnl_drawdown: 0.05
    sre_latency_p95: 100.0
    sre_error_rate: 10.0
    learning_insight_stagnation: 0.1

adaptation:
  drift_detector:
    tau_drift: 0.1
    warning_threshold: 0.05
    window_size: 100
    min_samples: 30

risk_management:
  risk_manifold:
    risk_sensitivity: 1.0
    nonlinearity_factor: 0.5
    drawdown_warning: 0.05
    drawdown_danger: 0.10
    drawdown_critical: 0.15
    daily_loss_warning: 0.03
    daily_loss_danger: 0.05
    daily_loss_critical: 0.08
    leverage_warning: 0.5
    leverage_danger: 0.7
    leverage_critical: 0.9
"""


@classmethod
def create_default_config(cls, config_dir: Union[str, Path] = None):
    """Create default configuration files"""
    if config_dir is None:
        config_dir = Path(__file__).parent.parent / "config"
    config_dir = Path(config_dir)
    config_dir.mkdir(exist_ok=True)
    
    # Create main config file
    main_config_file = config_dir / "unified.yaml"
    if not main_config_file.exists():
        with open(main_config_file, 'w') as f:
            f.write(DEFAULT_CONFIG_TEMPLATE)
    
    # Create environments directory
    env_dir = config_dir / "environments"
    env_dir.mkdir(exist_ok=True)
    
    # Create default environment configs
    environments = ["development", "staging", "production"]
    for env in environments:
        env_file = env_dir / f"{env}.yaml"
        if not env_file.exists():
            # Environment-specific overrides would go here
            # For now, create empty files or minimal overrides
            env_content = f"# {env.title()} Environment Configuration\n# Overrides for {env} environment\n"
            with open(env_file, 'w') as f:
                f.write(env_content)


# Example usage and testing
if __name__ == "__main__":
    import tempfile
    import shutil
    
    # Create temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    print(f"Using temporary directory: {temp_dir}")
    
    try:
        # Create config manager
        config_manager = ConfigManager(temp_dir)
        
        # Create default configuration
        ConfigManager.create_default_config(temp_dir)
        
        # Load default configuration
        print("\nLoading default configuration:")
        config = config_manager.load_config()
        print(f"System name: {config.get('system', {}).get('name')}")
        print(f"System version: {config.get('system', {}).get('version')}")
        print(f"Environment: {config.get('system', {}).get('environment')}")
        print(f"Debug mode: {config.get('system', {}).get('debug')}")
        print(f"Log level: {config.get('system', {}).get('log_level')}")
        
        # Test getting specific values
        kappa = config_manager.get_config_value(config, "decision.aggression_controller.kappa")
        print(f"\nAggression controller kappa: {kappa}")
        
        # Test setting values
        config = config_manager.set_config_value(config, "decision.aggression_controller.kappa", 0.15)
        new_kappa = config_manager.get_config_value(config, "decision.aggression_controller.kappa")
        print(f"Updated kappa: {new_kappa}")
        
        # Test environment variable overrides
        print("\nTesting environment variable overrides:")
        os.environ["SYSTEM_SYSTEM_NAME"] = "Test Trading System"
        os.environ["SYSTEM_DECISION_AGGRESSION_CONTROLLER_KAPPA"] = "0.2"
        os.environ["SYSTEM_FEEDBACK_ALERT_THRESHOLDS_PNLDRAWDOWN"] = "0.08"
        
        # Reload config to see overrides
        config_with_overrides = config_manager.load_config()
        print(f"System name with override: {config_with_overrides.get('system', {}).get('name')}")
        print(f"Kappa with override: {config_with_overrides.get('decision', {}).get('aggression_controller', {}).get('kappa')}")
        print(f"Drawdown threshold with override: {config_with_overrides.get('feedback', {}).get('alert_thresholds', {}).get('pnl_drawdown')}")
        
        # Test validation with invalid config
        print("\nTesting validation:")
        invalid_config = {
            "system": {
                "name": "Test System"
                # Missing required version and environment fields
            },
            "decision": {
                "aggression_controller": {
                    "kappa": 1.5  # Above maximum of 1.0
                }
            }
        }
        
        try:
            config_manager._validate_config(invalid_config, "unified")
            print("ERROR: Validation should have failed!")
        except ConfigValidationError as e:
            print(f"Validation correctly failed: {e}")
        
        # Test saving configuration
        print("\nTesting configuration save:")
        test_config = {
            "system": {
                "name": "Save Test System",
                "version": "2.0.0",
                "environment": "testing"
            }
        }
        
        config_manager.save_config(test_config, "test_config", "testing")
        print("Configuration saved successfully")
        
        # Load saved configuration
        loaded_test_config = config_manager.load_config("test_config", "testing")
        print(f"Loaded test config name: {loaded_test_config.get('system', {}).get('name')}")
        print(f"Loaded test config version: {loaded_test_config.get('system', {}).get('version')}")
        
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)
        print(f"\nCleaned up temporary directory: {temp_dir}")