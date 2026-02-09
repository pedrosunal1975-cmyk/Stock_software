# Path: core/config_loader.py
"""
Map Pro Core Configuration Loader

Centralized configuration management for the main application.
Loads PostgreSQL data path settings from .env file.

Architecture:
- Single source for core application configuration
- Focused on essential startup paths (PostgreSQL data directory)
- Each module has its own config_loader for module-specific settings
- This loader is for root-level application initialization only

Note:
    Module-specific configurations are handled by their respective
    config_loader.py files (database/core/, searcher/core/, etc.)
"""

import os
from pathlib import Path
from typing import Optional, Any
from dotenv import load_dotenv


# Environment variable keys for core configuration
ENV_DB_POSTGRESQL_DATA_DIR = 'DB_POSTGRESQL_DATA_DIR'
ENV_DB_LOG_DIR = 'DB_LOG_DIR'
ENV_DB_ROOT_DIR = 'DB_ROOT_DIR'


class CoreConfigLoader:
    """
    Configuration loader for Map Pro core application.

    Loads only essential startup configuration:
    - PostgreSQL data directory path
    - Core log directory

    Module-specific configurations are delegated to their own loaders.

    Example:
        config = CoreConfigLoader()
        pg_data_dir = config.get('postgresql_data_dir')
    """

    def __init__(self, env_file: Optional[Path] = None):
        """
        Initialize core configuration loader.

        Args:
            env_file: Optional path to .env file. If None, searches default locations.
        """
        self._config = {}
        self._env_loaded = False
        self._load_env(env_file)
        self._load_config()

    def _load_env(self, env_file: Optional[Path] = None) -> None:
        """
        Load environment variables from .env file.

        Args:
            env_file: Optional explicit path to .env file
        """
        if env_file and env_file.exists():
            load_dotenv(dotenv_path=env_file)
            self._env_loaded = True
            return

        # Search for .env in standard locations
        current_file = Path(__file__).resolve()
        root_dir = current_file.parent.parent  # core/ -> map_pro/

        search_paths = [
            root_dir / '.env',                    # map_pro/.env
            root_dir.parent / '.env',             # project_root/.env
            Path.cwd() / '.env',                  # current directory
        ]

        for env_path in search_paths:
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)
                self._env_loaded = True
                return

        # No .env found - will use defaults or environment variables
        self._env_loaded = False

    def _load_config(self) -> None:
        """Load core configuration values."""
        # PostgreSQL data directory (critical for startup)
        self._config['postgresql_data_dir'] = self._get_path(
            ENV_DB_POSTGRESQL_DATA_DIR,
            default=Path('/mnt/map_pro/database/postgres/data')
        )

        # Core log directory
        self._config['log_dir'] = self._get_path(
            ENV_DB_LOG_DIR,
            default=Path('/mnt/map_pro/database/logs')
        )

        # Database root directory
        self._config['db_root_dir'] = self._get_path(
            ENV_DB_ROOT_DIR,
            default=Path('/mnt/map_pro/database')
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

    def get_postgresql_data_dir(self) -> Path:
        """
        Get PostgreSQL data directory path.

        Returns:
            Path to PostgreSQL data directory
        """
        return self._config.get('postgresql_data_dir')

    def is_env_loaded(self) -> bool:
        """
        Check if .env file was successfully loaded.

        Returns:
            True if .env was loaded, False otherwise
        """
        return self._env_loaded

    def _get_env(
        self,
        key: str,
        required: bool = False,
        default: Optional[str] = None
    ) -> Optional[str]:
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

    def _get_path(
        self,
        key: str,
        required: bool = False,
        default: Optional[Path] = None
    ) -> Optional[Path]:
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


# Global config instance for convenience
_core_config: Optional[CoreConfigLoader] = None


def get_core_config() -> CoreConfigLoader:
    """
    Get global core configuration instance.

    Returns:
        CoreConfigLoader instance
    """
    global _core_config
    if _core_config is None:
        _core_config = CoreConfigLoader()
    return _core_config


__all__ = ['CoreConfigLoader', 'get_core_config']
