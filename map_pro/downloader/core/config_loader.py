# Path: downloader/core/config_loader.py
"""
Downloader Configuration Loader

Centralized configuration management for the Downloader Module.
Loads and validates environment variables with type safety and defaults.

CRITICAL: NO HARDCODING - All values come from environment variables.

Architecture:
- Singleton pattern for global configuration
- Type-safe access with validation
- Sensible defaults
- Integration with database module configuration
"""

import os
from typing import Any, Optional
from pathlib import Path
from dotenv import load_dotenv

from downloader.constants import (
    ENV_DOWNLOADER_ROOT,
    ENV_DOWNLOADER_ENTITIES,
    ENV_DOWNLOADER_TEMP,
    ENV_DOWNLOADER_LOG,
    ENV_DOWNLOADER_CACHE,
    ENV_LIBRARY_TAXONOMIES,
    ENV_REQUEST_TIMEOUT,
    ENV_CONNECT_TIMEOUT,
    ENV_READ_TIMEOUT,
    ENV_RETRY_ATTEMPTS,
    ENV_RETRY_DELAY,
    ENV_MAX_RETRY_DELAY,
    ENV_MAX_CONCURRENT,
    ENV_CHUNK_SIZE,
    ENV_ENABLE_RESUME,
    ENV_MAX_ARCHIVE_SIZE,
    ENV_VERIFY_EXTRACTION,
    ENV_PRESERVE_ZIP,
    ENV_MAX_EXTRACTION_DEPTH,
    ENV_MIN_FILE_SIZE,
    ENV_VERIFY_CHECKSUMS,
    ENV_VERIFY_URL_BEFORE,
    ENV_LOG_LEVEL,
    ENV_LOG_CONSOLE,
    ENV_STORE_RAW_RESPONSES,
    ENV_LOG_PROGRESS_INTERVAL,
    ENV_CLEANUP_TEMP_ON_START,
    ENV_CLEANUP_FAILED,
    ENV_TEMP_RETENTION_HOURS,
    ENV_AUTO_RETRY,
    ENV_VERIFY_FILES_EXIST,
    ENV_MAX_SEARCH_DEPTH,
    ENV_SEC_USER_AGENT,
    ENV_UK_CH_API_KEY,
    ENV_UK_CH_USER_AGENT,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_TIMEOUT,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_DELAY,
    DEFAULT_MAX_RETRY_DELAY,
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_DB_PORT,
    DEFAULT_DB_POOL_SIZE,
    DEFAULT_DB_POOL_MAX_OVERFLOW,
    DEFAULT_DB_POOL_TIMEOUT,
    DEFAULT_DB_POOL_RECYCLE,
    DEFAULT_LOG_PROGRESS_INTERVAL,
    MIN_FILE_SIZE,
    MAX_ARCHIVE_SIZE,
    MAX_EXTRACTION_DEPTH,
    TEMP_RETENTION_HOURS,
    MAX_SEARCH_DEPTH,
)


class ConfigLoader:
    """
    Thread-safe singleton configuration loader.
    
    Loads configuration from environment variables with validation,
    type conversion, and sensible defaults.
    
    Example:
        config = ConfigLoader()
        temp_dir = config.get('downloader_temp_dir')
        chunk_size = config.get('chunk_size')
    """
    
    _instance: Optional['ConfigLoader'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'ConfigLoader':
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        Initialize configuration loader.
        
        Only runs once due to singleton pattern.
        """
        if ConfigLoader._initialized:
            return
        
        # Find .env relative to this file
        # config_loader.py is at: map_pro/downloader/core/config_loader.py
        # .env is at: map_pro/.env
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent  # Go up: core/ -> downloader/ -> map_pro/
        env_path = project_root / '.env'
        
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, interpolate=True)
        
        self._config = self._load_configuration()
        ConfigLoader._initialized = True
    
    def _load_configuration(self) -> dict[str, Any]:
        """
        Load and validate all configuration from environment.
        
        Returns:
            Dictionary of validated configuration values
            
        Raises:
            ValueError: If required configuration is missing or invalid
        """
        config = {
            # ================================================================
            # DIRECTORY PATHS
            # ================================================================
            'downloader_root_dir': self._get_path(ENV_DOWNLOADER_ROOT, required=True),
            'downloader_entities_dir': self._get_path(ENV_DOWNLOADER_ENTITIES, required=True),
            'downloader_temp_dir': self._get_path(ENV_DOWNLOADER_TEMP, required=True),
            'downloader_log_dir': self._get_path(ENV_DOWNLOADER_LOG, required=True),
            'downloader_cache_dir': self._get_path(ENV_DOWNLOADER_CACHE, required=False),
            
            # ================================================================
            # TAXONOMIES PATHS (Across All Modules)
            # ================================================================
            # CRITICAL: Must point to /mnt/map_pro/taxonomies/libraries
            # We provide TWO keys for backwards compatibility:
            #   - 'library_taxonomies_dir' (legacy)
            #   - 'library_taxonomies_libraries' (correct, used by coordinator)
            # Both point to the same path from ENV_LIBRARY_TAXONOMIES
            'library_taxonomies_dir': self._get_path(ENV_LIBRARY_TAXONOMIES, required=True),
            'library_taxonomies_libraries': self._get_path(ENV_LIBRARY_TAXONOMIES, required=True),  # Alias
            
            # ================================================================
            # DATABASE CONFIGURATION (shared with database module)
            # ================================================================
            'db_host': self._get_env('DB_HOST', required=True),
            'db_port': self._get_int('DB_PORT', DEFAULT_DB_PORT),
            'db_name': self._get_env('DB_NAME', required=True),
            'db_user': self._get_env('DB_USER', required=True),
            'db_password': self._get_env('DB_PASSWORD', required=True),
            'db_pool_size': self._get_int('DB_POOL_SIZE', DEFAULT_DB_POOL_SIZE),
            'db_pool_max_overflow': self._get_int('DB_POOL_MAX_OVERFLOW', DEFAULT_DB_POOL_MAX_OVERFLOW),
            'db_pool_timeout': self._get_int('DB_POOL_TIMEOUT', DEFAULT_DB_POOL_TIMEOUT),
            'db_pool_recycle': self._get_int('DB_POOL_RECYCLE', DEFAULT_DB_POOL_RECYCLE),
            
            # ================================================================
            # DOWNLOAD CONFIGURATION
            # ================================================================
            'request_timeout': self._get_int(ENV_REQUEST_TIMEOUT, DEFAULT_TIMEOUT),
            'connect_timeout': self._get_int(ENV_CONNECT_TIMEOUT, DEFAULT_CONNECT_TIMEOUT),
            'read_timeout': self._get_int(ENV_READ_TIMEOUT, DEFAULT_TIMEOUT),
            'retry_attempts': self._get_int(ENV_RETRY_ATTEMPTS, DEFAULT_RETRY_ATTEMPTS),
            'retry_delay': self._get_int(ENV_RETRY_DELAY, DEFAULT_RETRY_DELAY),
            'max_retry_delay': self._get_int(ENV_MAX_RETRY_DELAY, DEFAULT_MAX_RETRY_DELAY),
            'max_concurrent': self._get_int(ENV_MAX_CONCURRENT, DEFAULT_MAX_CONCURRENT),
            'chunk_size': self._get_int(ENV_CHUNK_SIZE, DEFAULT_CHUNK_SIZE),
            'enable_resume': self._get_bool(ENV_ENABLE_RESUME, True),
            
            # ================================================================
            # EXTRACTION CONFIGURATION
            # ================================================================
            'max_archive_size': self._get_int(ENV_MAX_ARCHIVE_SIZE, MAX_ARCHIVE_SIZE),
            'verify_extraction': self._get_bool(ENV_VERIFY_EXTRACTION, True),
            'preserve_zip': self._get_bool(ENV_PRESERVE_ZIP, False),
            'max_extraction_depth': self._get_int(ENV_MAX_EXTRACTION_DEPTH, MAX_EXTRACTION_DEPTH),
            
            # ================================================================
            # VALIDATION CONFIGURATION
            # ================================================================
            'min_file_size': self._get_int(ENV_MIN_FILE_SIZE, MIN_FILE_SIZE),
            'verify_checksums': self._get_bool(ENV_VERIFY_CHECKSUMS, True),
            'verify_url_before_download': self._get_bool(ENV_VERIFY_URL_BEFORE, True),
            
            # ================================================================
            # LOGGING CONFIGURATION
            # ================================================================
            'log_level': self._get_env(ENV_LOG_LEVEL, 'INFO'),
            'log_console': self._get_bool(ENV_LOG_CONSOLE, True),
            'store_raw_responses': self._get_bool(ENV_STORE_RAW_RESPONSES, False),
            'log_progress_interval': self._get_int(ENV_LOG_PROGRESS_INTERVAL, DEFAULT_LOG_PROGRESS_INTERVAL),
            
            # ================================================================
            # CLEANUP CONFIGURATION
            # ================================================================
            'cleanup_temp_on_start': self._get_bool(ENV_CLEANUP_TEMP_ON_START, True),
            'cleanup_failed_downloads': self._get_bool(ENV_CLEANUP_FAILED, True),
            'temp_retention_hours': self._get_int(ENV_TEMP_RETENTION_HOURS, TEMP_RETENTION_HOURS),
            
            # ================================================================
            # OPERATIONAL SETTINGS
            # ================================================================
            'auto_retry': self._get_bool(ENV_AUTO_RETRY, True),
            'verify_files_exist': self._get_bool(ENV_VERIFY_FILES_EXIST, True),
            'max_search_depth': self._get_int(ENV_MAX_SEARCH_DEPTH, MAX_SEARCH_DEPTH),
            
            # ================================================================
            # MARKET-SPECIFIC SETTINGS
            # ================================================================
            'sec_user_agent': self._get_env(ENV_SEC_USER_AGENT, required=False),
            'uk_ch_api_key': self._get_env(ENV_UK_CH_API_KEY, required=False),
            'uk_ch_user_agent': self._get_env(ENV_UK_CH_USER_AGENT, required=False),
        }
        
        return config
    
    def _get_env(self, key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
        """
        Get string environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            required: If True, raises ValueError when missing
            
        Returns:
            Environment variable value or default
            
        Raises:
            ValueError: If required and not found
        """
        value = os.getenv(key)
        
        if value is None:
            if required:
                raise ValueError(f"Required environment variable not set: {key}")
            return default
        
        return value.strip()
    
    def _get_bool(self, key: str, default: bool) -> bool:
        """
        Get boolean environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Boolean value
        """
        value = os.getenv(key)
        if value is None:
            return default
        
        return value.strip().lower() in ('true', '1', 'yes', 'on')
    
    def _get_int(self, key: str, default: int) -> int:
        """
        Get integer environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not found or invalid
            
        Returns:
            Integer value
        """
        value = os.getenv(key)
        if value is None:
            return default
        
        try:
            return int(value.strip())
        except ValueError:
            return default
    
    def _get_float(self, key: str, default: float) -> float:
        """
        Get float environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not found or invalid
            
        Returns:
            Float value
        """
        value = os.getenv(key)
        if value is None:
            return default
        
        try:
            return float(value.strip())
        except ValueError:
            return default
    
    def _get_path(self, key: str, required: bool = False) -> Optional[Path]:
        """
        Get path environment variable.
        
        Args:
            key: Environment variable name
            required: If True, raises ValueError when missing
            
        Returns:
            Path object or None
            
        Raises:
            ValueError: If required and not found
        """
        value = os.getenv(key)
        
        if value is None:
            if required:
                raise ValueError(f"Required environment variable not set: {key}")
            return None
        
        return Path(value.strip())
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value or default
            
        Example:
            config = ConfigLoader()
            temp_dir = config.get('downloader_temp_dir')
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
    
    def __getitem__(self, key: str) -> Any:
        """Dictionary-style access to configuration."""
        return self._config[key]
    
    def __contains__(self, key: str) -> bool:
        """Check if configuration key exists."""
        return key in self._config
    
    def keys(self):
        """Get all configuration keys."""
        return self._config.keys()
    
    def items(self):
        """Get all configuration key-value pairs."""
        return self._config.items()


__all__ = ['ConfigLoader']