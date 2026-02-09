# Path: database/core/config_loader.py
"""
Database Configuration Loader

Centralized configuration management for the database module.
Loads settings from .env file and provides validated access.

Architecture:
- Single source for all configuration values
- Validation of required settings
- Type conversion and defaults
- No hardcoded paths
"""

import os
from pathlib import Path
from typing import Optional, Any
from dotenv import load_dotenv

from database.constants import (
    ENV_DB_HOST,
    ENV_DB_PORT,
    ENV_DB_NAME,
    ENV_DB_USER,
    ENV_DB_PASSWORD,
    ENV_DB_ROOT_DIR,
    ENV_DB_LOG_DIR,
    ENV_DB_LOG_LEVEL,
    ENV_DB_LOG_CONSOLE,
    ENV_DB_POSTGRESQL_DATA_DIR,
    ENV_DATA_ENTITIES_DIR,
    ENV_DATA_TAXONOMIES_DIR,
    ENV_DB_POOL_SIZE,
    ENV_DB_POOL_MAX_OVERFLOW,
    ENV_DB_POOL_TIMEOUT,
    ENV_DB_POOL_RECYCLE,
    DEFAULT_POOL_SIZE,
    DEFAULT_POOL_MAX_OVERFLOW,
    DEFAULT_POOL_TIMEOUT,
    DEFAULT_POOL_RECYCLE,
)


class ConfigLoader:
    """
    Configuration loader for database module.
    
    Loads and validates all configuration from environment variables.
    Provides type-safe access to configuration values.
    
    Example:
        config = ConfigLoader()
        db_host = config.get('db_host')
        log_dir = config.get('log_dir')
    """
    
    def __init__(self, env_file: Optional[Path] = None):
        """
        Initialize configuration loader.
        
        Args:
            env_file: Optional path to .env file. If None, searches current directory.
        """
        self._config = {}
        self._load_env(env_file)
        self._load_config()
    
    def _load_env(self, env_file: Optional[Path] = None) -> None:
        if env_file:
            load_dotenv(dotenv_path=env_file)
        else:
            # Default to root .env
            current_file = Path(__file__).resolve()
            root_dir = current_file.parent.parent.parent  # core/ -> database/ -> map_pro/
            default_env = root_dir / '.env'
            load_dotenv(dotenv_path=default_env)
    
    def _load_config(self) -> None:
        """Load and validate all configuration values."""
        # Database connection
        self._config['db_host'] = self._get_env(ENV_DB_HOST, required=True)
        self._config['db_port'] = self._get_int(ENV_DB_PORT, default=5432)
        self._config['db_name'] = self._get_env(ENV_DB_NAME, required=True)
        self._config['db_user'] = self._get_env(ENV_DB_USER, required=True)
        self._config['db_password'] = self._get_env(ENV_DB_PASSWORD, required=True)
        
        # Directory paths
        self._config['db_root_dir'] = self._get_path(ENV_DB_ROOT_DIR, required=True)
        self._config['db_log_dir'] = self._get_path(ENV_DB_LOG_DIR, required=True)
        self._config['db_postgresql_data_dir'] = self._get_path(
            ENV_DB_POSTGRESQL_DATA_DIR,
            required=True
        )
        
        # Shared data directories
        self._config['data_entities_dir'] = self._get_path(
            ENV_DATA_ENTITIES_DIR,
            required=True
        )
        self._config['data_taxonomies_dir'] = self._get_path(
            ENV_DATA_TAXONOMIES_DIR,
            required=True
        )
        
        # Logging configuration
        self._config['log_level'] = self._get_env(ENV_DB_LOG_LEVEL, default='INFO')
        self._config['log_console'] = self._get_bool(ENV_DB_LOG_CONSOLE, default=True)
        
        # Connection pool configuration
        self._config['pool_size'] = self._get_int(
            ENV_DB_POOL_SIZE,
            default=DEFAULT_POOL_SIZE
        )
        self._config['pool_max_overflow'] = self._get_int(
            ENV_DB_POOL_MAX_OVERFLOW,
            default=DEFAULT_POOL_MAX_OVERFLOW
        )
        self._config['pool_timeout'] = self._get_int(
            ENV_DB_POOL_TIMEOUT,
            default=DEFAULT_POOL_TIMEOUT
        )
        self._config['pool_recycle'] = self._get_int(
            ENV_DB_POOL_RECYCLE,
            default=DEFAULT_POOL_RECYCLE
        )
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)
    
    def get_database_url(self) -> str:
        """
        Get PostgreSQL connection URL.
        
        Returns:
            SQLAlchemy database URL string
        """
        return (
            f"postgresql://{self._config['db_user']}:{self._config['db_password']}"
            f"@{self._config['db_host']}:{self._config['db_port']}"
            f"/{self._config['db_name']}"
        )
    
    def _get_env(self, key: str, required: bool = False, default: Optional[str] = None) -> Optional[str]:
        """
        Get environment variable value.
        
        Args:
            key: Environment variable name
            required: Whether variable is required
            default: Default value if not found
            
        Returns:
            Environment variable value or default
            
        Raises:
            ValueError: If required variable not found
        """
        value = os.getenv(key, default)
        
        if required and value is None:
            raise ValueError(f"Required environment variable not set: {key}")
        
        return value
    
    def _get_int(self, key: str, required: bool = False, default: Optional[int] = None) -> Optional[int]:
        """
        Get environment variable as integer.
        
        Args:
            key: Environment variable name
            required: Whether variable is required
            default: Default value if not found
            
        Returns:
            Integer value or default
        """
        value = self._get_env(key, required=required)
        
        if value is None:
            return default
        
        try:
            return int(value)
        except ValueError:
            if default is not None:
                return default
            raise ValueError(f"Environment variable {key} must be an integer: {value}")
    
    def _get_bool(self, key: str, required: bool = False, default: Optional[bool] = None) -> Optional[bool]:
        """
        Get environment variable as boolean.
        
        Args:
            key: Environment variable name
            required: Whether variable is required
            default: Default value if not found
            
        Returns:
            Boolean value or default
        """
        value = self._get_env(key, required=required)
        
        if value is None:
            return default
        
        return value.lower() in ('true', '1', 'yes', 'on')
    
    def _get_path(self, key: str, required: bool = False, default: Optional[Path] = None) -> Optional[Path]:
        """
        Get environment variable as Path object.
        
        Args:
            key: Environment variable name
            required: Whether variable is required
            default: Default value if not found
            
        Returns:
            Path object or default
        """
        value = self._get_env(key, required=required)
        
        if value is None:
            return default
        
        return Path(value)


__all__ = ['ConfigLoader']