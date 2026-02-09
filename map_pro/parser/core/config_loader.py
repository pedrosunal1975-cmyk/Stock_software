# Path: core/config_loader.py
"""
Configuration Loader

Centralized configuration management for the XBRL Parser.
Loads and validates environment variables with type safety and defaults.

This module provides a singleton ConfigLoader that reads from .env file
and provides type-safe access to all configuration values.
"""

import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv


class ConfigLoader:
    """
    Thread-safe singleton configuration loader.
    
    Loads configuration from environment variables with validation,
    type conversion, and sensible defaults. All configuration access
    should go through this class to ensure consistency.
    
    Example:
        config = ConfigLoader()
        data_root = config.get('data_root')  # Returns Path object
        debug_mode = config.get('debug')     # Returns bool
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
        # config_loader.py is at: map_pro/parser/core/config_loader.py
        # .env is at: map_pro/.env
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent  # Go up 3 levels: core/ -> parser/ -> map_pro/
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
            # BASE PATHS - Critical for all operations
            # ================================================================
            'program_dir': self._get_path('PARSER_PROGRAM_DIR', required=False),  # Optional - not used
            'data_root': self._get_path('PARSER_DATA_ROOT', required=True),
            'loaders_root': self._get_path('PARSER_LOADERS_ROOT', required=True),
            
            # ================================================================
            # ENVIRONMENT & DEBUG
            # ================================================================
            'environment': self._get_env('PARSER_ENVIRONMENT', 'development'),
            'debug': self._get_bool('PARSER_DEBUG', False),
            'enable_profiling': self._get_bool('PARSER_ENABLE_PROFILING', False),
            
            # ================================================================
            # INPUT PATHS (READ-ONLY)
            # ================================================================
            'xbrl_filings_path': self._get_path('PARSER_XBRL_FILINGS_PATH', required=True),
            'taxonomy_path': self._get_path('PARSER_TAXONOMY_PATH', required=True),
            
            # ================================================================
            # OUTPUT PATHS (WRITE)
            # ================================================================
            'output_dir': self._get_path('PARSER_OUTPUT_DIR', required=True),
            'output_parsed_dir': self._get_path('PARSER_OUTPUT_PARSED_DIR', required=True),
            # Note: output_extracted_dir removed - CSV now saved in parsed_reports folders
            # Note: output_exports_dir removed - never used
            
            # ================================================================
            # CACHE & TEMPORARY PATHS
            # ================================================================
            'taxonomy_cache_dir': self._get_path('PARSER_TAXONOMY_CACHE_DIR', required=True),
            'taxonomy_cache_db': self._get_path('PARSER_TAXONOMY_CACHE_DB', required=True),
            'enable_taxonomy_caching': self._get_bool('PARSER_ENABLE_TAXONOMY_CACHING', True),
            'taxonomy_cache_size_mb': self._get_int('PARSER_TAXONOMY_CACHE_SIZE_MB', 1024),
            'taxonomy_cache_ttl_hours': self._get_int('PARSER_TAXONOMY_CACHE_TTL_HOURS', 168),
            # Note: temp directories removed - checkpoint system never used
            
            # ================================================================
            # INDEXING & QUERY SYSTEM
            # ================================================================
            'enable_indexing': self._get_bool('PARSER_ENABLE_INDEXING', True),
            # Note: indexes_dir, indexes_query_cache_dir removed - query caching never used
            'index_batch_size': self._get_int('PARSER_INDEX_BATCH_SIZE', 1000),
            'index_compression': self._get_bool('PARSER_INDEX_COMPRESSION', True),
            
            # ================================================================
            # LOGGING CONFIGURATION
            # ================================================================
            'log_dir': self._get_path('PARSER_LOG_DIR', required=True),
            'log_format': self._get_env('PARSER_LOG_FORMAT', 'json'),
            'log_rotation': self._get_env('PARSER_LOG_ROTATION', 'daily'),
            'log_retention_days': self._get_int('PARSER_LOG_RETENTION_DAYS', 30),
            'log_max_size_mb': self._get_int('PARSER_LOG_MAX_SIZE_MB', 10),
            'log_backup_count': self._get_int('PARSER_LOG_BACKUP_COUNT', 5),
            'log_level': self._get_env('PARSER_LOG_LEVEL', 'INFO'),
            
            # Process-specific log files
            'error_log': self._get_env('PARSER_ERROR_LOG', 'parser_error.log'),
            'warning_log': self._get_env('PARSER_WARNING_LOG', 'parser_warning.log'),
            'debug_log': self._get_env('PARSER_DEBUG_LOG', 'parser_debug.log'),
            'main_log': self._get_env('PARSER_MAIN_LOG', 'parser.log'),
            'system_log': self._get_env('PARSER_SYSTEM_LOG', 'system.log'),
            'input_log': self._get_env('PARSER_INPUT_LOG', 'input.log'),
            
            'structured_logging': self._get_bool('PARSER_STRUCTURED_LOGGING', True),
            'log_compress_archived': self._get_bool('PARSER_LOG_COMPRESS_ARCHIVED', True),
            
            # ================================================================
            # PARSER CONFIGURATION
            # ================================================================
            'max_memory_mb': self._get_int('PARSER_MAX_MEMORY_MB', 4096),
            'enable_streaming': self._get_bool('PARSER_ENABLE_STREAMING', True),
            'streaming_threshold_mb': self._get_int('PARSER_STREAMING_THRESHOLD_MB', 50),
            'streaming_batch_size': self._get_int('PARSER_STREAMING_BATCH_SIZE', 1000),
            'timeout_seconds': self._get_int('PARSER_TIMEOUT_SECONDS', 0),
            'max_concurrent_jobs': self._get_int('PARSER_MAX_CONCURRENT_JOBS', 3),
            
            # ================================================================
            # VALIDATION CONFIGURATION
            # ================================================================
            'validation_level': self._get_env('PARSER_VALIDATION_LEVEL', 'full'),
            'strict_mode': self._get_bool('PARSER_STRICT_MODE', False),
            'enable_calculation_validation': self._get_bool('PARSER_ENABLE_CALCULATION_VALIDATION', True),
            'calculation_tolerance': self._get_float('PARSER_CALCULATION_TOLERANCE', 0.01),
            'enable_dimensional_validation': self._get_bool('PARSER_ENABLE_DIMENSIONAL_VALIDATION', True),
            'enable_completeness_audit': self._get_bool('PARSER_ENABLE_COMPLETENESS_AUDIT', True),
            'min_quality_score': self._get_float('PARSER_MIN_QUALITY_SCORE', 70.0),
            
            # ================================================================
            # MARKET-SPECIFIC CONFIGURATION
            # ================================================================
            'default_market': self._get_env('PARSER_DEFAULT_MARKET', 'sec'),
            'enable_market_auto_detection': self._get_bool('PARSER_ENABLE_MARKET_AUTO_DETECTION', True),
            'enable_sec_validation': self._get_bool('PARSER_ENABLE_SEC_VALIDATION', True),
            'enable_frc_validation': self._get_bool('PARSER_ENABLE_FRC_VALIDATION', True),
            'enable_esma_validation': self._get_bool('PARSER_ENABLE_ESMA_VALIDATION', True),
            'enable_ifrs_validation': self._get_bool('PARSER_ENABLE_IFRS_VALIDATION', True),
            
            # ================================================================
            # TAXONOMY SOURCES (Configurable URLs - ALL from .env)
            # ================================================================
            # NOTE: Variable names are configuration keys only
            # Market-specific logic lives in xbrl_parser/market/ module
            # All URLs must be defined in .env - no hardcoded defaults
            'taxonomy_source_1_url': self._get_env('PARSER_US_GAAP_URL', required=False),
            'taxonomy_source_2_url': self._get_env('PARSER_IFRS_URL', required=False),
            'taxonomy_source_3_url': self._get_env('PARSER_UK_GAAP_URL', required=False),
            'taxonomy_source_4_url': self._get_env('PARSER_ESEF_URL', required=False),
            'taxonomy_download_timeout': self._get_int('PARSER_TAXONOMY_DOWNLOAD_TIMEOUT', 30),
            'taxonomy_download_retries': self._get_int('PARSER_TAXONOMY_DOWNLOAD_RETRIES', 3),
            
            # ================================================================
            # PERFORMANCE & OPTIMIZATION
            # ================================================================
            'enable_multithreading': self._get_bool('PARSER_ENABLE_MULTITHREADING', True),
            'worker_threads': self._get_int('PARSER_WORKER_THREADS', 0),
            'enable_result_caching': self._get_bool('PARSER_ENABLE_RESULT_CACHING', True),
            'result_cache_ttl_hours': self._get_int('PARSER_RESULT_CACHE_TTL_HOURS', 24),
            'lazy_load_taxonomies': self._get_bool('PARSER_LAZY_LOAD_TAXONOMIES', True),
            'memory_cleanup_threshold_mb': self._get_int('PARSER_MEMORY_CLEANUP_THRESHOLD_MB', 3072),
            
            # ================================================================
            # ERROR HANDLING & RECOVERY
            # ================================================================
            'continue_on_error': self._get_bool('PARSER_CONTINUE_ON_ERROR', True),
            'max_errors': self._get_int('PARSER_MAX_ERRORS', 0),
            'enable_error_recovery': self._get_bool('PARSER_ENABLE_ERROR_RECOVERY', True),
            'enable_checkpoints': self._get_bool('PARSER_ENABLE_CHECKPOINTS', True),
            'checkpoint_interval': self._get_int('PARSER_CHECKPOINT_INTERVAL', 5000),
            
            # ================================================================
            # OUTPUT CONFIGURATION
            # ================================================================
            'output_schema_version': self._get_env('PARSER_OUTPUT_SCHEMA_VERSION', '1.0'),
            'include_provenance': self._get_bool('PARSER_INCLUDE_PROVENANCE', True),
            'include_statistics': self._get_bool('PARSER_INCLUDE_STATISTICS', True),
            'include_validation_results': self._get_bool('PARSER_INCLUDE_VALIDATION_RESULTS', True),
            'json_pretty_print': self._get_bool('PARSER_JSON_PRETTY_PRINT', True),
            'json_indent': self._get_int('PARSER_JSON_INDENT', 2),
            'enable_output_compression': self._get_bool('PARSER_ENABLE_OUTPUT_COMPRESSION', False),
            
            # ================================================================
            # FEATURE FLAGS
            # ================================================================
            'enable_footnotes': self._get_bool('PARSER_ENABLE_FOOTNOTES', True),
            'enable_ixbrl': self._get_bool('PARSER_ENABLE_IXBRL', True),
            'enable_tuples': self._get_bool('PARSER_ENABLE_TUPLES', True),
            'enable_custom_linkbases': self._get_bool('PARSER_ENABLE_CUSTOM_LINKBASES', True),
            'enable_relationship_networks': self._get_bool('PARSER_ENABLE_RELATIONSHIP_NETWORKS', True),
            'enable_label_extraction': self._get_bool('PARSER_ENABLE_LABEL_EXTRACTION', True),
            'enable_reference_extraction': self._get_bool('PARSER_ENABLE_REFERENCE_EXTRACTION', True),
            
            # ================================================================
            # DEVELOPMENT & TESTING
            # ================================================================
            'dev_cache_enabled': self._get_bool('PARSER_DEV_CACHE_ENABLED', False),
            'dev_cache_dir': self._get_path('PARSER_DEV_CACHE_DIR', required=False),
            'test_mode': self._get_bool('PARSER_TEST_MODE', False),
            'test_fixtures_dir': self._get_path('PARSER_TEST_FIXTURES_DIR', required=False),
            'verbose_errors': self._get_bool('PARSER_VERBOSE_ERRORS', True),
            'include_stack_traces': self._get_bool('PARSER_INCLUDE_STACK_TRACES', True),
            
            # ================================================================
            # SECURITY
            # ================================================================
            'disable_external_entities': self._get_bool('PARSER_DISABLE_EXTERNAL_ENTITIES', True),
            'max_file_size_mb': self._get_int('PARSER_MAX_FILE_SIZE_MB', 500),
            'max_xml_depth': self._get_int('PARSER_MAX_XML_DEPTH', 100),
            'validate_file_signatures': self._get_bool('PARSER_VALIDATE_FILE_SIGNATURES', True),
            
            # ================================================================
            # OBSERVABILITY & MONITORING
            # ================================================================
            'enable_health_checks': self._get_bool('PARSER_ENABLE_HEALTH_CHECKS', True),
            'health_check_interval': self._get_int('PARSER_HEALTH_CHECK_INTERVAL', 60),
            'enable_metrics': self._get_bool('PARSER_ENABLE_METRICS', True),
            'metrics_format': self._get_env('PARSER_METRICS_FORMAT', 'json'),
            # Note: metrics_dir, profile_output_dir removed - metrics/profiling never write to disk
            
            # ================================================================
            # CUSTOM VALIDATORS
            # ================================================================
            'enable_custom_validators': self._get_bool('PARSER_ENABLE_CUSTOM_VALIDATORS', True),
            'custom_validators_dir': self._get_path('PARSER_CUSTOM_VALIDATORS_DIR', required=False),
            
            # ================================================================
            # PARSING MODES
            # ================================================================
            'default_mode': self._get_env('PARSER_DEFAULT_MODE', 'full'),
            
            # ================================================================
            # DATE & TIME CONFIGURATION
            # ================================================================
            'default_timezone': self._get_env('PARSER_DEFAULT_TIMEZONE', 'UTC'),
            'date_format': self._get_env('PARSER_DATE_FORMAT', 'iso'),
            'fuzzy_date_parsing': self._get_bool('PARSER_FUZZY_DATE_PARSING', True),
            
            # ================================================================
            # ENCODING CONFIGURATION
            # ================================================================
            'default_encoding': self._get_env('PARSER_DEFAULT_ENCODING', 'utf-8'),
            'encoding_fallbacks': self._get_env('PARSER_ENCODING_FALLBACKS', 'utf-8,latin-1,cp1252'),
            'auto_detect_encoding': self._get_bool('PARSER_AUTO_DETECT_ENCODING', True),
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
    
    def get(self, key: str, default: any = None) -> any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value or default
            
        Example:
            config = ConfigLoader()
            data_root = config.get('data_root')
            debug = config.get('debug', False)
        """
        return self._config.get(key, default)
    
    def __getitem__(self, key: str) -> any:
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
            data_root = config['data_root']
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
            if 'data_root' in config:
                print("Data root is configured")
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