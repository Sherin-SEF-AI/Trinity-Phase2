"""
Trinity Phase 2 - Configuration Management
Handles loading and validating configuration files
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


DEFAULT_CONFIG_PATH = "config/config.yaml"
TEMPLATE_CONFIG_PATH = "config/config.template.yaml"


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file

    Args:
        config_path: Path to config file. If None, uses default path.

    Returns:
        Dictionary containing configuration
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    config_file = Path(config_path)

    # If config doesn't exist, try to copy from template
    if not config_file.exists():
        template_file = Path(TEMPLATE_CONFIG_PATH)
        if template_file.exists():
            logger.warning(f"Config file not found at {config_path}, using template")
            config_path = str(template_file)
        else:
            raise FileNotFoundError(
                f"Configuration file not found: {config_path} "
                f"and template not found: {TEMPLATE_CONFIG_PATH}"
            )

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        logger.info(f"Configuration loaded from: {config_path}")
        return config

    except yaml.YAMLError as e:
        logger.error(f"Error parsing configuration file: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise


def save_config(config: Dict[str, Any], config_path: str = DEFAULT_CONFIG_PATH):
    """
    Save configuration to YAML file

    Args:
        config: Configuration dictionary
        config_path: Path to save config file
    """
    config_file = Path(config_path)
    config_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Configuration saved to: {config_path}")

    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        raise


def get_config_value(config: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Get configuration value using dot notation

    Args:
        config: Configuration dictionary
        key_path: Dot-separated path to config value (e.g., 'cameras.camera_1.resolution')
        default: Default value if key not found

    Returns:
        Configuration value or default
    """
    keys = key_path.split('.')
    value = config

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default

    return value


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate configuration structure and required fields

    Args:
        config: Configuration dictionary

    Returns:
        True if valid, raises ValueError otherwise
    """
    required_sections = ['application', 'cameras', 'detection', 'tracking', 'database']

    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required configuration section: {section}")

    # Validate camera configuration
    cameras_config = config.get('cameras', {})
    num_cameras = cameras_config.get('count', 0)

    if num_cameras < 1:
        raise ValueError("At least 1 camera must be configured")

    for i in range(1, num_cameras + 1):
        cam_key = f'camera_{i}'
        if cam_key not in cameras_config:
            raise ValueError(f"Missing configuration for {cam_key}")

        cam_cfg = cameras_config[cam_key]
        required_cam_fields = ['device_id', 'resolution', 'position', 'orientation']

        for field in required_cam_fields:
            if field not in cam_cfg:
                raise ValueError(f"Missing required field '{field}' in {cam_key}")

    # Validate database configuration
    db_config = config.get('database', {})
    db_type = db_config.get('type')

    if db_type not in ['sqlite', 'postgresql']:
        raise ValueError(f"Invalid database type: {db_type}. Must be 'sqlite' or 'postgresql'")

    logger.success("Configuration validation passed")
    return True


class Config:
    """Configuration singleton for global access"""
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance

    def load(self, config_path: Optional[str] = None):
        """Load configuration"""
        self._config = load_config(config_path)
        validate_config(self._config)

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value"""
        if self._config is None:
            self.load()
        return get_config_value(self._config, key_path, default)

    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration"""
        if self._config is None:
            self.load()
        return self._config

    def reload(self):
        """Reload configuration from file"""
        self.load()


# Global config instance
config = Config()
