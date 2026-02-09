# Path: core/config_loader.py
"""
Configuration Loader - Water Paradigm

Loads configuration for XBRL statement extractor.
NO hardcoded schemas, NO transformation rules.

This module provides a singleton ConfigLoader that reads from .env file
and provides type-safe access to configuration values.
"""

import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# ============================================================================
# DEFAULT CONFIGURATION VALUES
# ============================================================================

# Logging Defaults
DEFAULT_LOG_RETENTION_DAYS: int = 30
DEFAULT_LOG_MAX_SIZE_MB: int = 10
DEFAULT_LOG_BACKUP_COUNT: int = 5

# Mapper Configuration Defaults
DEFAULT_MAX_MEMORY_MB: int = 4096
DEFAULT_MAX_CONCURRENT_JOBS: int = 3
DEFAULT_BATCH_SIZE: int = 100

# Validation Configuration Defaults
DEFAULT_MIN_COVERAGE_PERCENT: float = 95.0
DEFAULT_MIN_QUALITY_SCORE: float = 80.0

# Component Configuration Defaults
DEFAULT_UNIT_CONVERSION_PRECISION: int = 2
DEFAULT_FUZZY_MATCHING_THRESHOLD: float = 0.85

# Output Configuration Defaults
DEFAULT_JSON_INDENT: int = 2

# Performance & Optimization Defaults
DEFAULT_MEMORY_CLEANUP_THRESHOLD_MB: int = 3072

# Observability & Monitoring Defaults
DEFAULT_HEALTH_CHECK_INTERVAL: int = 60


class ConfigLoader:
    """
    Thread-safe singleton configuration loader.
    
    Loads configuration from environment variables with validation,
    type conversion, and sensible defaults.
    
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
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent  # Go up 3 levels
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
            'program_dir': self._get_path('MAPPER_PROGRAM_DIR', required=False),  # Optional - not used
            'data_root': self._get_path('MAPPER_DATA_ROOT', required=True),
            'loaders_root': self._get_path('MAPPER_LOADERS_ROOT', required=True),
            
            # ================================================================
            # ENVIRONMENT & DEBUG
            # ================================================================
            'environment': self._get_env('MAPPER_ENVIRONMENT', 'development'),
            'debug': self._get_bool('MAPPER_DEBUG', False),
            'enable_profiling': self._get_bool('MAPPER_ENABLE_PROFILING', False),
            
            # ================================================================
            # INPUT PATHS (READ-ONLY - shared with parser)
            # ================================================================
            'xbrl_filings_path': self._get_path('MAPPER_XBRL_FILINGS_PATH', required=True),
            'taxonomy_path': self._get_path('MAPPER_TAXONOMY_PATH', required=True),
            'parser_output_dir': self._get_path('MAPPER_PARSER_OUTPUT_DIR', required=True),
            'taxonomy_cache_dir': self._get_path('MAPPER_TAXONOMY_CACHE_DIR', required=True),
            
            # ================================================================
            # OUTPUT PATHS (WRITE - Mapped Statements)
            # ================================================================
            'output_mapped_dir': self._get_path('MAPPER_OUTPUT_MAPPED_DIR', required=True),
            
            # ================================================================
            # LOGGING CONFIGURATION
            # ================================================================
            'log_dir': self._get_path('MAPPER_LOG_DIR', required=True),
            'log_format': self._get_env('MAPPER_LOG_FORMAT', 'json'),
            'log_rotation': self._get_env('MAPPER_LOG_ROTATION', 'daily'),
            'log_retention_days': self._get_int('MAPPER_LOG_RETENTION_DAYS', DEFAULT_LOG_RETENTION_DAYS),
            'log_max_size_mb': self._get_int('MAPPER_LOG_MAX_SIZE_MB', DEFAULT_LOG_MAX_SIZE_MB),
            'log_backup_count': self._get_int('MAPPER_LOG_BACKUP_COUNT', DEFAULT_LOG_BACKUP_COUNT),
            'log_level': self._get_env('MAPPER_LOG_LEVEL', 'INFO'),
            'main_log': self._get_env('MAPPER_MAIN_LOG', 'mapper.log'),
            'structured_logging': self._get_bool('MAPPER_STRUCTURED_LOGGING', True),
            'log_compress_archived': self._get_bool('MAPPER_LOG_COMPRESS_ARCHIVED', True),
            
            # ================================================================
            # MAPPER CONFIGURATION
            # ================================================================
            'max_memory_mb': self._get_int('MAPPER_MAX_MEMORY_MB', DEFAULT_MAX_MEMORY_MB),
            'max_concurrent_jobs': self._get_int('MAPPER_MAX_CONCURRENT_JOBS', DEFAULT_MAX_CONCURRENT_JOBS),
            'batch_size': self._get_int('MAPPER_BATCH_SIZE', DEFAULT_BATCH_SIZE),
            'enable_batch_processing': self._get_bool('MAPPER_ENABLE_BATCH_PROCESSING', True),
            'continue_on_error': self._get_bool('MAPPER_CONTINUE_ON_ERROR', True),
            'max_errors': self._get_int('MAPPER_MAX_ERRORS', 0),
            
            # ================================================================
            # VALIDATION CONFIGURATION
            # ================================================================
            'validation_level': self._get_env('MAPPER_VALIDATION_LEVEL', 'full'),
            'strict_mode': self._get_bool('MAPPER_STRICT_MODE', False),
            'enable_output_validation': self._get_bool('MAPPER_ENABLE_OUTPUT_VALIDATION', True),
            'enable_completeness_check': self._get_bool('MAPPER_ENABLE_COMPLETENESS_CHECK', True),
            'min_coverage_percent': self._get_float('MAPPER_MIN_COVERAGE_PERCENT', DEFAULT_MIN_COVERAGE_PERCENT),
            'min_quality_score': self._get_float('MAPPER_MIN_QUALITY_SCORE', DEFAULT_MIN_QUALITY_SCORE),
            
            # ================================================================
            # COMPONENT CONFIGURATION
            # ================================================================
            'unit_conversion_precision': self._get_int('MAPPER_UNIT_CONVERSION_PRECISION', DEFAULT_UNIT_CONVERSION_PRECISION),
            'enable_fuzzy_matching': self._get_bool('MAPPER_ENABLE_FUZZY_MATCHING', False),
            'fuzzy_matching_threshold': self._get_float('MAPPER_FUZZY_MATCHING_THRESHOLD', DEFAULT_FUZZY_MATCHING_THRESHOLD),
            'enable_dimension_handling': self._get_bool('MAPPER_ENABLE_DIMENSION_HANDLING', True),
            'enable_period_normalization': self._get_bool('MAPPER_ENABLE_PERIOD_NORMALIZATION', True),
            
            # ================================================================
            # OUTPUT CONFIGURATION
            # ================================================================
            'include_metadata': self._get_bool('MAPPER_INCLUDE_METADATA', True),
            'include_confidence_scores': self._get_bool('MAPPER_INCLUDE_CONFIDENCE_SCORES', False),
            'include_provenance': self._get_bool('MAPPER_INCLUDE_PROVENANCE', True),
            'include_comparison_results': self._get_bool('MAPPER_INCLUDE_COMPARISON_RESULTS', False),
            'json_pretty_print': self._get_bool('MAPPER_JSON_PRETTY_PRINT', True),
            'json_indent': self._get_int('MAPPER_JSON_INDENT', DEFAULT_JSON_INDENT),
            
            # ================================================================
            # PERFORMANCE & OPTIMIZATION
            # ================================================================
            'enable_multithreading': self._get_bool('MAPPER_ENABLE_MULTITHREADING', True),
            'worker_threads': self._get_int('MAPPER_WORKER_THREADS', 0),
            'memory_cleanup_threshold_mb': self._get_int('MAPPER_MEMORY_CLEANUP_THRESHOLD_MB', DEFAULT_MEMORY_CLEANUP_THRESHOLD_MB),
            
            # ================================================================
            # OBSERVABILITY & MONITORING
            # ================================================================
            'enable_health_checks': self._get_bool('MAPPER_ENABLE_HEALTH_CHECKS', True),
            'health_check_interval': self._get_int('MAPPER_HEALTH_CHECK_INTERVAL', DEFAULT_HEALTH_CHECK_INTERVAL),
            'enable_metrics': self._get_bool('MAPPER_ENABLE_METRICS', False),
            'metrics_format': self._get_env('MAPPER_METRICS_FORMAT', 'json'),
            
            # ================================================================
            # ADVANCED
            # ================================================================
            'enable_experimental_features': self._get_bool('MAPPER_ENABLE_EXPERIMENTAL_FEATURES', False),
            'enable_debug_artifacts': self._get_bool('MAPPER_ENABLE_DEBUG_ARTIFACTS', False),
            'debug_artifacts_dir': self._get_path('MAPPER_DEBUG_ARTIFACTS_DIR'),
        }
        
        return config
    
    def _get_env(self, key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
        """Get string environment variable."""
        value = os.getenv(key)
        
        if value is None:
            if required:
                raise ValueError(f"Required environment variable '{key}' is not set")
            return default
        
        return value.strip()
    
    def _get_bool(self, key: str, default: bool) -> bool:
        """Get boolean environment variable."""
        value = os.getenv(key)
        if value is None:
            return default
        
        return value.strip().lower() in ('true', '1', 'yes', 'on')
    
    def _get_int(self, key: str, default: int) -> int:
        """Get integer environment variable."""
        value = os.getenv(key)
        if value is None:
            return default
        
        try:
            return int(value.strip())
        except ValueError:
            return default
    
    def _get_float(self, key: str, default: float) -> float:
        """Get float environment variable."""
        value = os.getenv(key)
        if value is None:
            return default
        
        try:
            return float(value.strip())
        except ValueError:
            return default
    
    def _get_path(self, key: str, required: bool = False) -> Optional[Path]:
        """Get path environment variable."""
        value = os.getenv(key)
        
        if value is None:
            if required:
                raise ValueError(f"Required environment variable '{key}' is not set")
            return None
        
        return Path(value.strip())
    
    def get(self, key: str, default: any = None) -> any:
        """Get configuration value."""
        return self._config.get(key, default)
    
    def __getitem__(self, key: str) -> any:
        """Get configuration value using dictionary syntax."""
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