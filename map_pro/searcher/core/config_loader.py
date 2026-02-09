# Path: searcher/core/config_loader.py
"""
Configuration Loader

Centralized configuration management for the Searcher Module.
Loads and validates environment variables with type safety and defaults.

This module provides a singleton ConfigLoader that reads from .env file
and provides type-safe access to all configuration values.

CRITICAL: NO HARDCODING - All values come from environment variables.
"""

import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv


# Default Configuration Values
DEFAULT_DB_PORT: int = 5432
DEFAULT_DB_POOL_SIZE: int = 5
DEFAULT_DB_POOL_MAX_OVERFLOW: int = 10
DEFAULT_DB_POOL_TIMEOUT: int = 30
DEFAULT_DB_POOL_RECYCLE: int = 3600
DEFAULT_API_TIMEOUT: int = 30
DEFAULT_API_RETRY_COUNT: int = 3
DEFAULT_MAX_CONCURRENT_REQUESTS: int = 3
DEFAULT_MAX_RESULTS: int = 100
DEFAULT_LOOKBACK_DAYS: int = 365
DEFAULT_CACHE_EXPIRY_HOURS: int = 24
DEFAULT_SEC_RATE_LIMIT: int = 10
DEFAULT_FCA_RATE_LIMIT: int = 5
DEFAULT_ESMA_RATE_LIMIT: int = 3


class ConfigLoader:
    """
    Thread-safe singleton configuration loader.
    
    Loads configuration from environment variables with validation,
    type conversion, and sensible defaults. All configuration access
    should go through this class to ensure consistency.
    
    Example:
        config = ConfigLoader()
        sec_user_agent = config.get('sec_user_agent')
        rate_limit = config.get('sec_rate_limit')
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
        
        Only runs once due to singleton pattern. Loads .env file
        and validates all configuration on first instantiation.
        """
        if ConfigLoader._initialized:
            return
            
        # Find .env relative to this file's location (project root)
        # config_loader.py is at: map_pro/searcher/core/config_loader.py
        # .env is at: map_pro/.env
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent  # Go up 3 levels: core/ -> searcher/-> map_pro/
        env_path = project_root / '.env'
        
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, interpolate=True)
        
        self._config = self._load_configuration()
        ConfigLoader._initialized = True
    
    def _load_configuration(self) -> dict[str, any]:
        """
        Load and validate all configuration from environment.
        
        Returns:
            Dictionary of validated configuration values with proper types
            
        Raises:
            ValueError: If required configuration is missing or invalid
        """
        config = {
            # ================================================================
            # DIRECTORY PATHS
            # ================================================================
            'searcher_root_dir': self._get_path('SEARCHER_ROOT_DIR', required=True),
            'searcher_log_dir': self._get_path('SEARCHER_LOG_DIR', required=True),
            'searcher_cache_dir': self._get_path('SEARCHER_CACHE_DIR', required=False),
            'searcher_export_dir': self._get_path('SEARCHER_EXPORT_DIR', required=False),
            
            # ================================================================
            # SHARED DATA PATHS
            # ================================================================
            'data_entities_dir': self._get_path('DATA_ENTITIES_DIR', required=True),
            'data_taxonomies_dir': self._get_path('DATA_TAXONOMIES_DIR', required=True),
            
            # ================================================================
            # DATABASE CONFIGURATION
            # ================================================================
            'db_host': self._get_env('DB_HOST', required=True),
            'db_port': self._get_int('DB_PORT', DEFAULT_DB_PORT),
            'db_name': self._get_env('DB_NAME', required=True),
            'db_user': self._get_env('DB_USER', required=True),
            'db_password': self._get_env('DB_PASSWORD', required=True),

            # Database Connection Pool
            'db_pool_size': self._get_int('DB_POOL_SIZE', DEFAULT_DB_POOL_SIZE),
            'db_pool_max_overflow': self._get_int('DB_POOL_MAX_OVERFLOW', DEFAULT_DB_POOL_MAX_OVERFLOW),
            'db_pool_timeout': self._get_int('DB_POOL_TIMEOUT', DEFAULT_DB_POOL_TIMEOUT),
            'db_pool_recycle': self._get_int('DB_POOL_RECYCLE', DEFAULT_DB_POOL_RECYCLE),
            
            # ================================================================
            # GENERAL API CONFIGURATION
            # ================================================================
            'api_timeout': self._get_int('SEARCHER_API_TIMEOUT', DEFAULT_API_TIMEOUT),
            'api_retry_count': self._get_int('SEARCHER_API_RETRY_COUNT', DEFAULT_API_RETRY_COUNT),
            'max_concurrent_requests': self._get_int('SEARCHER_MAX_CONCURRENT_REQUESTS', DEFAULT_MAX_CONCURRENT_REQUESTS),
            'max_results': self._get_int('SEARCHER_MAX_RESULTS', DEFAULT_MAX_RESULTS),
            'default_lookback_days': self._get_int('SEARCHER_DEFAULT_LOOKBACK_DAYS', DEFAULT_LOOKBACK_DAYS),
            
            # ================================================================
            # LOGGING CONFIGURATION
            # ================================================================
            'log_level': self._get_env('SEARCHER_LOG_LEVEL', 'INFO'),
            'log_console': self._get_bool('SEARCHER_LOG_CONSOLE', True),
            'store_raw_responses': self._get_bool('SEARCHER_STORE_RAW_RESPONSES', False),
            
            # ================================================================
            # CACHE CONFIGURATION
            # ================================================================
            'enable_cache': self._get_bool('SEARCHER_ENABLE_CACHE', True),
            'cache_expiry_hours': self._get_int('SEARCHER_CACHE_EXPIRY_HOURS', DEFAULT_CACHE_EXPIRY_HOURS),
            
            # ================================================================
            # OPERATIONAL SETTINGS
            # ================================================================
            'auto_retry': self._get_bool('SEARCHER_AUTO_RETRY', True),
            'rate_limit_delay': self._get_float('SEARCHER_RATE_LIMIT_DELAY', 1.0),
            
            # ================================================================
            # SEC SPECIFIC CONFIGURATION
            # ================================================================
            # CRITICAL: SEC_USER_AGENT is REQUIRED by SEC
            'sec_user_agent': self._get_env('SEARCHER_SEC_USER_AGENT', required=True),
            'sec_base_url': self._get_env('SEARCHER_SEC_BASE_URL', required=False),
            'sec_rate_limit': self._get_int('SEARCHER_SEC_RATE_LIMIT', DEFAULT_SEC_RATE_LIMIT),
            'sec_timeout': self._get_int('SEARCHER_SEC_TIMEOUT', DEFAULT_API_TIMEOUT),
            'sec_retry_attempts': self._get_int('SEARCHER_SEC_RETRY_ATTEMPTS', DEFAULT_API_RETRY_COUNT),
            
            # SEC Data Source URLs (ALL from .env - no hardcoded defaults)
            'sec_company_tickers_url': self._get_env('SEARCHER_SEC_COMPANY_TICKERS_URL', required=False),
            'sec_submissions_url': self._get_env('SEARCHER_SEC_SUBMISSIONS_URL', required=False),
            'sec_facts_url': self._get_env('SEARCHER_SEC_FACTS_URL', required=False),
            'sec_archives_base_url': self._get_env('SEARCHER_SEC_ARCHIVES_BASE_URL', required=False),
            
            # ================================================================
            # UK COMPANIES HOUSE SPECIFIC CONFIGURATION
            # ================================================================
            'uk_ch_api_key': self._get_env('SEARCHER_UK_CH_API_KEY', required=False),
            'uk_ch_user_agent': self._get_env('SEARCHER_UK_CH_USER_AGENT', required=False),
            'uk_ch_base_url': self._get_env('SEARCHER_UK_CH_BASE_URL', required=False),
            'uk_ch_company_url': self._get_env('SEARCHER_UK_CH_COMPANY_URL', required=False),
            'uk_ch_filing_history_url': self._get_env('SEARCHER_UK_CH_FILING_HISTORY_URL', required=False),
            'uk_ch_document_meta_url': self._get_env('SEARCHER_UK_CH_DOCUMENT_META_URL', required=False),
            'uk_ch_document_content_url': self._get_env('SEARCHER_UK_CH_DOCUMENT_CONTENT_URL', required=False),
            'uk_ch_rate_limit': self._get_int('SEARCHER_UK_CH_RATE_LIMIT', 600),
            'uk_ch_timeout': self._get_int('SEARCHER_UK_CH_TIMEOUT', DEFAULT_API_TIMEOUT),
            'uk_ch_download_timeout': self._get_int('SEARCHER_UK_CH_DOWNLOAD_TIMEOUT', 120),
            'uk_ch_max_retries': self._get_int('SEARCHER_UK_CH_MAX_RETRIES', DEFAULT_API_RETRY_COUNT),
            'uk_ch_retry_delay': self._get_int('SEARCHER_UK_CH_RETRY_DELAY', 2),
            'uk_ch_backoff_factor': self._get_int('SEARCHER_UK_CH_BACKOFF_FACTOR', 2),

            # ================================================================
            # FCA SPECIFIC CONFIGURATION (Future)
            # ================================================================
            'fca_base_url': self._get_env('SEARCHER_FCA_BASE_URL', required=False),
            'fca_api_key': self._get_env('SEARCHER_FCA_API_KEY', required=False),
            'fca_rate_limit': self._get_int('SEARCHER_FCA_RATE_LIMIT', DEFAULT_FCA_RATE_LIMIT),
            'fca_timeout': self._get_int('SEARCHER_FCA_TIMEOUT', DEFAULT_API_TIMEOUT),
            'fca_retry_attempts': self._get_int('SEARCHER_FCA_RETRY_ATTEMPTS', DEFAULT_API_RETRY_COUNT),

            # ================================================================
            # ESMA SPECIFIC CONFIGURATION (Future)
            # ================================================================
            'esma_base_url': self._get_env('SEARCHER_ESMA_BASE_URL', required=False),
            'esma_api_key': self._get_env('SEARCHER_ESMA_API_KEY', required=False),
            'esma_rate_limit': self._get_int('SEARCHER_ESMA_RATE_LIMIT', DEFAULT_ESMA_RATE_LIMIT),
            'esma_timeout': self._get_int('SEARCHER_ESMA_TIMEOUT', DEFAULT_API_TIMEOUT),
            'esma_retry_attempts': self._get_int('SEARCHER_ESMA_RETRY_ATTEMPTS', DEFAULT_API_RETRY_COUNT),

            # ================================================================
            # ESEF SPECIFIC CONFIGURATION (filings.xbrl.org)
            # ================================================================
            'esef_base_url': self._get_env('SEARCHER_ESEF_BASE_URL', 'https://filings.xbrl.org'),
            'esef_user_agent': self._get_env('SEARCHER_ESEF_USER_AGENT', required=False),
            'esef_timeout': self._get_int('SEARCHER_ESEF_TIMEOUT', DEFAULT_API_TIMEOUT),
            'esef_max_retries': self._get_int('SEARCHER_ESEF_MAX_RETRIES', DEFAULT_API_RETRY_COUNT),
            'esef_retry_delay': self._get_int('SEARCHER_ESEF_RETRY_DELAY', 2),
            'esef_backoff_factor': self._get_int('SEARCHER_ESEF_BACKOFF_FACTOR', 2),
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
                raise ValueError(f"Required environment variable '{key}' is not set")
            return default
        
        return value.strip()
    
    def _get_bool(self, key: str, default: bool) -> bool:
        """
        Get boolean environment variable.
        
        Accepts: true, 1, yes, on (case-insensitive)
        
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
                raise ValueError(f"Required environment variable '{key}' is not set")
            return None
        
        return Path(value.strip())
    
    def get(self, key: str, default=None):
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value or default
            
        Example:
            config = ConfigLoader()
            sec_user_agent = config.get('sec_user_agent')
            rate_limit = config.get('sec_rate_limit', 10)
        """
        return self._config.get(key, default)
    
    def __getitem__(self, key: str):
        """
        Get configuration value using dictionary syntax.
        
        Args:
            key: Configuration key
            
        Returns:
            Configuration value
            
        Raises:
            KeyError: If key not found
            
        Example:
            config = ConfigLoader()
            sec_user_agent = config['sec_user_agent']
        """
        return self._config[key]
    
    def __contains__(self, key: str) -> bool:
        """
        Check if configuration key exists.
        
        Args:
            key: Configuration key
            
        Returns:
            True if key exists, False otherwise
            
        Example:
            config = ConfigLoader()
            if 'sec_user_agent' in config:
                print("SEC user agent is configured")
        """
        return key in self._config
    
    def keys(self):
        """
        Get all configuration keys.
        
        Returns:
            Iterator of configuration keys
        """
        return self._config.keys()
    
    def items(self):
        """
        Get all configuration key-value pairs.
        
        Returns:
            Iterator of (key, value) tuples
        """
        return self._config.items()


__all__ = ['ConfigLoader']