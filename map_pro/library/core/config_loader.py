# Path: library/core/config_loader.py
"""
Library Configuration Loader

Loads and manages configuration from .env file.
Singleton pattern ensures consistent configuration across module.

Usage:
    from library.core.config_loader import LibraryConfig
    
    config = LibraryConfig()
    taxonomies_dir = config.get('library_taxonomies_libraries')
"""

import os
from pathlib import Path
from typing import Any, Optional
from dotenv import load_dotenv

from library.constants import (
    ENV_LIBRARY_TAXONOMIES_ROOT,
    ENV_LIBRARY_TAXONOMIES_LIBRARIES,
    ENV_LIBRARY_PARSED_FILES_DIR,
    ENV_LIBRARY_MANUAL_DOWNLOADS,
    ENV_LIBRARY_CACHE_DIR,
    ENV_LIBRARY_TEMP_DIR,
    ENV_LIBRARY_LOG_DIR,
    ENV_LIBRARY_MONITOR_INTERVAL,
    ENV_LIBRARY_AUTO_CREATE,
    ENV_LIBRARY_MIN_FILES_THRESHOLD,
    ENV_LIBRARY_CACHE_TTL,
    ENV_LIBRARY_MAX_RETRIES,
    ENV_DB_HOST,
    ENV_DB_PORT,
    ENV_DB_NAME,
    ENV_DB_USER,
    ENV_DB_PASSWORD,
    DEFAULT_MONITOR_INTERVAL,
    MIN_FILES_THRESHOLD,
    CACHE_TTL_SECONDS,
    MAX_RETRY_ATTEMPTS,
)


class LibraryConfig:
    """
    Library configuration manager (Singleton).
    
    Loads configuration from .env file and provides
    type-safe access to configuration values.
    """
    
    _instance = None
    _config = None
    
    def __new__(cls):
        """Singleton pattern - only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_configuration()
        return cls._instance
    
    def _load_configuration(self) -> None:
        """Load configuration from .env file or environment variables."""
        # Find .env file - optional, environment variables take precedence
        env_path = Path(__file__).parent.parent.parent / '.env'

        if env_path.exists():
            # Load from .env file (won't override existing env vars)
            load_dotenv(env_path)
        else:
            # Check if required environment variables are already set
            # (e.g., passed via subprocess from mat_acc)
            required_vars = [
                ENV_LIBRARY_TAXONOMIES_ROOT,
                ENV_LIBRARY_TAXONOMIES_LIBRARIES,
                ENV_DB_HOST,
                ENV_DB_NAME,
            ]
            missing = [v for v in required_vars if not os.getenv(v)]
            if missing:
                raise FileNotFoundError(
                    f".env file not found at {env_path} and required "
                    f"environment variables not set: {missing}"
                )
        
        # Build configuration dictionary
        self._config = {
            # Taxonomy paths
            'library_taxonomies_root': self._get_path(ENV_LIBRARY_TAXONOMIES_ROOT, required=True),
            'library_taxonomies_libraries': self._get_path(ENV_LIBRARY_TAXONOMIES_LIBRARIES, required=True),
            'library_parsed_files_dir': self._get_path(ENV_LIBRARY_PARSED_FILES_DIR, required=True),
            'library_manual_downloads': self._get_path(ENV_LIBRARY_MANUAL_DOWNLOADS, required=True),
            'library_cache_dir': self._get_path(ENV_LIBRARY_CACHE_DIR, required=True),
            'library_temp_dir': self._get_path(ENV_LIBRARY_TEMP_DIR, required=True),
            'library_log_dir': self._get_path(ENV_LIBRARY_LOG_DIR, required=True),
            
            # Behavior settings
            'library_monitor_interval': self._get_int(ENV_LIBRARY_MONITOR_INTERVAL, default=DEFAULT_MONITOR_INTERVAL),
            'library_auto_create': self._get_bool(ENV_LIBRARY_AUTO_CREATE, default=True),
            'library_min_files_threshold': self._get_int(ENV_LIBRARY_MIN_FILES_THRESHOLD, default=MIN_FILES_THRESHOLD),
            'library_cache_ttl': self._get_int(ENV_LIBRARY_CACHE_TTL, default=CACHE_TTL_SECONDS),
            'library_max_retries': self._get_int(ENV_LIBRARY_MAX_RETRIES, default=MAX_RETRY_ATTEMPTS),
            
            # Database settings
            'db_host': os.getenv(ENV_DB_HOST, 'localhost'),
            'db_port': self._get_int(ENV_DB_PORT, default=5432),
            'db_name': os.getenv(ENV_DB_NAME, 'xbrl_coordination'),
            'db_user': os.getenv(ENV_DB_USER, 'xbrl_user'),
            'db_password': os.getenv(ENV_DB_PASSWORD, ''),
        }
    
    def get(self, key: str, required: bool = True) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key
            required: Whether key is required (raises error if missing)
            
        Returns:
            Configuration value
            
        Raises:
            KeyError: If required key is missing
        """
        if key not in self._config:
            if required:
                raise KeyError(f"Configuration key '{key}' not found")
            return None
        
        return self._config[key]
    
    def _get_path(self, env_var: str, required: bool = True) -> Optional[Path]:
        """
        Get path from environment variable.
        
        Args:
            env_var: Environment variable name
            required: Whether path is required
            
        Returns:
            Path object or None
        """
        value = os.getenv(env_var)
        
        if value is None:
            if required:
                raise ValueError(f"Required environment variable {env_var} not set")
            return None
        
        return Path(value)
    
    def _get_int(self, env_var: str, default: int = 0) -> int:
        """
        Get integer from environment variable.
        
        Args:
            env_var: Environment variable name
            default: Default value if not set
            
        Returns:
            Integer value
        """
        value = os.getenv(env_var)
        
        if value is None:
            return default
        
        try:
            return int(value)
        except ValueError:
            return default
    
    def _get_bool(self, env_var: str, default: bool = False) -> bool:
        """
        Get boolean from environment variable.
        
        Args:
            env_var: Environment variable name
            default: Default value if not set
            
        Returns:
            Boolean value
        """
        value = os.getenv(env_var)
        
        if value is None:
            return default
        
        return value.lower() in ('true', '1', 'yes', 'on')
    
    def validate_configuration(self) -> bool:
        """
        Validate that all required configuration is present.
        
        Returns:
            True if valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        required_paths = [
            'library_taxonomies_root',
            'library_taxonomies_libraries',
            'library_log_dir',
        ]
        
        for key in required_paths:
            path = self.get(key)
            if path is None:
                raise ValueError(f"Required path '{key}' not configured")
        
        return True


__all__ = ['LibraryConfig']