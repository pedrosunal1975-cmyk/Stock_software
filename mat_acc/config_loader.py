# Path: mat_acc/config_loader.py
"""
Configuration Loader for mat_acc (Mathematical Accountancy)

Loads configuration from .env file for the financial analysis system.
Singleton pattern ensures consistent configuration across all components.

NO hardcoded paths, NO magic numbers.
All configuration comes from environment variables.
"""

import os
from typing import Optional, Any
from pathlib import Path
from dotenv import load_dotenv


# ==============================================================================
# DEFAULT CONFIGURATION VALUES
# ==============================================================================

# Logging Defaults
DEFAULT_LOG_LEVEL: str = 'INFO'
DEFAULT_LOG_FORMAT: str = 'json'
DEFAULT_LOG_ROTATION: str = 'daily'
DEFAULT_LOG_RETENTION_DAYS: int = 30
DEFAULT_LOG_MAX_SIZE_MB: int = 10
DEFAULT_LOG_BACKUP_COUNT: int = 5

# Verification Thresholds
DEFAULT_MIN_VERIFICATION_SCORE: float = 95.0
DEFAULT_EXCELLENT_THRESHOLD: int = 90
DEFAULT_GOOD_THRESHOLD: int = 75
DEFAULT_FAIR_THRESHOLD: int = 50
DEFAULT_POOR_THRESHOLD: int = 25

# Calculation Defaults
DEFAULT_CALCULATION_TOLERANCE: float = 0.01
DEFAULT_HIGH_CONFIDENCE_THRESHOLD: float = 90.0
DEFAULT_MEDIUM_CONFIDENCE_THRESHOLD: float = 70.0

# Performance Defaults
DEFAULT_MAX_CONCURRENT_JOBS: int = 3
DEFAULT_BATCH_SIZE: int = 10
DEFAULT_CACHE_TTL_HOURS: int = 24


class ConfigLoader:
    """
    Thread-safe singleton configuration loader for mat_acc.

    Loads configuration from environment variables with validation,
    type conversion, and sensible defaults.

    Example:
        config = ConfigLoader()
        output_dir = config.get('output_dir')  # Returns Path object
        score = config.get('min_verification_score')  # Returns float
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
        # mat_acc/config_loader.py -> .env is in same directory
        current_file = Path(__file__).resolve()
        project_root = current_file.parent
        env_path = project_root / '.env'

        if env_path.exists():
            load_dotenv(dotenv_path=env_path, interpolate=True)

        self._config = self._load_configuration()
        ConfigLoader._initialized = True

    def _load_configuration(self) -> dict[str, Any]:
        """
        Load and validate all configuration from environment.

        Returns:
            Dictionary of validated configuration values with proper types

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        config = {
            # ================================================================
            # BASE PATHS
            # ================================================================
            'program_dir': self._get_path('MAT_ACC_PROGRAM_DIR', required=True),
            'data_root': self._get_path('MAT_ACC_DATA_ROOT', required=True),

            # ================================================================
            # ENVIRONMENT & DEBUG
            # ================================================================
            'environment': self._get_env('MAT_ACC_ENVIRONMENT', 'development'),
            'debug': self._get_bool('MAT_ACC_DEBUG', False),
            'enable_profiling': self._get_bool('MAT_ACC_ENABLE_PROFILING', False),

            # ================================================================
            # INPUT PATHS (READ-ONLY - from map_pro modules)
            # ================================================================
            'verification_reports_dir': self._get_path(
                'MAT_ACC_VERIFICATION_REPORTS_DIR', required=True
            ),
            'mapper_output_dir': self._get_path(
                'MAT_ACC_MAPPER_OUTPUT_DIR', required=True
            ),
            'parser_output_dir': self._get_path(
                'MAT_ACC_PARSER_OUTPUT_DIR', required=True
            ),
            'xbrl_filings_dir': self._get_path(
                'MAT_ACC_XBRL_FILINGS_DIR', required=True
            ),
            'taxonomy_dir': self._get_path(
                'MAT_ACC_TAXONOMY_DIR', required=True
            ),
            'library_script_path': self._get_path(
                'MAT_ACC_LIBRARY_SCRIPT_PATH', required=False
            ),

            # ================================================================
            # OUTPUT PATHS (WRITE)
            # ================================================================
            'output_dir': self._get_path('MAT_ACC_OUTPUT_DIR', required=True),
            'reports_dir': self._get_path('MAT_ACC_REPORTS_DIR', required=True),
            'ratios_dir': self._get_path('MAT_ACC_RATIOS_DIR', required=True),
            'normalized_dir': self._get_path('MAT_ACC_NORMALIZED_DIR', required=True),
            'graphs_dir': self._get_path('MAT_ACC_GRAPHS_DIR', required=True),
            'audit_dir': self._get_path('MAT_ACC_AUDIT_DIR', required=True),

            # ================================================================
            # LOGGING CONFIGURATION
            # ================================================================
            'log_dir': self._get_path('MAT_ACC_LOG_DIR', required=True),
            'log_level': self._get_env('MAT_ACC_LOG_LEVEL', DEFAULT_LOG_LEVEL),
            'log_format': self._get_env('MAT_ACC_LOG_FORMAT', DEFAULT_LOG_FORMAT),
            'log_rotation': self._get_env('MAT_ACC_LOG_ROTATION', DEFAULT_LOG_ROTATION),
            'log_retention_days': self._get_int(
                'MAT_ACC_LOG_RETENTION_DAYS', DEFAULT_LOG_RETENTION_DAYS
            ),
            'log_max_size_mb': self._get_int(
                'MAT_ACC_LOG_MAX_SIZE_MB', DEFAULT_LOG_MAX_SIZE_MB
            ),
            'log_backup_count': self._get_int(
                'MAT_ACC_LOG_BACKUP_COUNT', DEFAULT_LOG_BACKUP_COUNT
            ),
            'log_console': self._get_bool('MAT_ACC_LOG_CONSOLE', True),
            'structured_logging': self._get_bool('MAT_ACC_STRUCTURED_LOGGING', True),

            # ================================================================
            # CACHE CONFIGURATION
            # ================================================================
            'cache_dir': self._get_path('MAT_ACC_CACHE_DIR'),
            'enable_caching': self._get_bool('MAT_ACC_ENABLE_CACHING', True),
            'cache_ttl_hours': self._get_int(
                'MAT_ACC_CACHE_TTL_HOURS', DEFAULT_CACHE_TTL_HOURS
            ),

            # ================================================================
            # VERIFICATION THRESHOLDS
            # ================================================================
            'min_verification_score': self._get_float(
                'MAT_ACC_MIN_VERIFICATION_SCORE', DEFAULT_MIN_VERIFICATION_SCORE
            ),
            'excellent_threshold': self._get_int(
                'MAT_ACC_EXCELLENT_THRESHOLD', DEFAULT_EXCELLENT_THRESHOLD
            ),
            'good_threshold': self._get_int(
                'MAT_ACC_GOOD_THRESHOLD', DEFAULT_GOOD_THRESHOLD
            ),
            'fair_threshold': self._get_int(
                'MAT_ACC_FAIR_THRESHOLD', DEFAULT_FAIR_THRESHOLD
            ),
            'poor_threshold': self._get_int(
                'MAT_ACC_POOR_THRESHOLD', DEFAULT_POOR_THRESHOLD
            ),

            # ================================================================
            # CALCULATION CONFIGURATION
            # ================================================================
            'enable_level_1': self._get_bool('MAT_ACC_ENABLE_LEVEL_1', True),
            'enable_level_2': self._get_bool('MAT_ACC_ENABLE_LEVEL_2', True),
            'enable_level_3': self._get_bool('MAT_ACC_ENABLE_LEVEL_3', True),
            'enable_level_4': self._get_bool('MAT_ACC_ENABLE_LEVEL_4', False),
            'calculation_tolerance': self._get_float(
                'MAT_ACC_CALCULATION_TOLERANCE', DEFAULT_CALCULATION_TOLERANCE
            ),
            'high_confidence_threshold': self._get_float(
                'MAT_ACC_HIGH_CONFIDENCE_THRESHOLD', DEFAULT_HIGH_CONFIDENCE_THRESHOLD
            ),
            'medium_confidence_threshold': self._get_float(
                'MAT_ACC_MEDIUM_CONFIDENCE_THRESHOLD', DEFAULT_MEDIUM_CONFIDENCE_THRESHOLD
            ),

            # ================================================================
            # PERFORMANCE CONFIGURATION
            # ================================================================
            'max_concurrent_jobs': self._get_int(
                'MAT_ACC_MAX_CONCURRENT_JOBS', DEFAULT_MAX_CONCURRENT_JOBS
            ),
            'batch_size': self._get_int('MAT_ACC_BATCH_SIZE', DEFAULT_BATCH_SIZE),
            'enable_multithreading': self._get_bool(
                'MAT_ACC_ENABLE_MULTITHREADING', True
            ),

            # ================================================================
            # OUTPUT CONFIGURATION
            # ================================================================
            'output_json': self._get_bool('MAT_ACC_OUTPUT_JSON', True),
            'output_csv': self._get_bool('MAT_ACC_OUTPUT_CSV', True),
            'output_excel': self._get_bool('MAT_ACC_OUTPUT_EXCEL', True),
            'output_html': self._get_bool('MAT_ACC_OUTPUT_HTML', True),
            'output_pdf': self._get_bool('MAT_ACC_OUTPUT_PDF', False),
            'json_pretty_print': self._get_bool('MAT_ACC_JSON_PRETTY_PRINT', True),
            'json_indent': self._get_int('MAT_ACC_JSON_INDENT', 2),
            'include_audit_trail': self._get_bool('MAT_ACC_INCLUDE_AUDIT_TRAIL', True),
            'include_confidence_scores': self._get_bool(
                'MAT_ACC_INCLUDE_CONFIDENCE_SCORES', True
            ),
            'include_lineage': self._get_bool('MAT_ACC_INCLUDE_LINEAGE', True),

            # ================================================================
            # DATABASE CONFIGURATION
            # ================================================================
            # SQLite database directory and path (primary for mat_acc)
            'database_dir': self._get_path('MAT_ACC_DATABASE_DIR', required=True),
            'database_path': self._get_path('MAT_ACC_DATABASE_PATH', required=True),

            # PostgreSQL configuration (for future scalability)
            'db_host': self._get_env('MAT_ACC_DB_HOST', 'localhost'),
            'db_port': self._get_int('MAT_ACC_DB_PORT', 5432),
            'db_name': self._get_env('MAT_ACC_DB_NAME', 'mat_acc_db'),
            'db_user': self._get_env('MAT_ACC_DB_USER', ''),
            'db_password': self._get_env('MAT_ACC_DB_PASSWORD', ''),
            'db_pool_size': self._get_int('MAT_ACC_DB_POOL_SIZE', 5),
            'db_pool_max_overflow': self._get_int('MAT_ACC_DB_POOL_MAX_OVERFLOW', 10),
            'db_pool_timeout': self._get_int('MAT_ACC_DB_POOL_TIMEOUT', 30),
            'db_pool_recycle': self._get_int('MAT_ACC_DB_POOL_RECYCLE', 3600),
        }

        return config

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

    def _get_path(self, key: str, required: bool = False) -> Optional[Path]:
        """
        Get path from environment variable.

        Args:
            key: Environment variable name
            required: If True, raise error when missing

        Returns:
            Path object or None

        Raises:
            ValueError: If required and missing
        """
        value = os.getenv(key)

        if value is None:
            if required:
                raise ValueError(f"Required path not configured: {key}")
            return None

        # Handle variable interpolation
        if '${' in value:
            value = os.path.expandvars(value)

        return Path(value)

    def _get_env(self, key: str, default: str = '') -> str:
        """Get string environment variable."""
        return os.getenv(key, default)

    def _get_int(self, key: str, default: int) -> int:
        """Get integer environment variable."""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def _get_float(self, key: str, default: float) -> float:
        """Get float environment variable."""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    def _get_bool(self, key: str, default: bool) -> bool:
        """Get boolean environment variable."""
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')

    def get_db_connection_string(self) -> str:
        """
        Build database connection string.

        Returns:
            PostgreSQL connection string
        """
        return (
            f"postgresql://{self._config['db_user']}:"
            f"{self._config['db_password']}@"
            f"{self._config['db_host']}:"
            f"{self._config['db_port']}/"
            f"{self._config['db_name']}"
        )

    def __repr__(self) -> str:
        """String representation showing key paths."""
        return (
            f"ConfigLoader("
            f"data_root={self._config.get('data_root')}, "
            f"environment={self._config.get('environment')})"
        )


__all__ = ['ConfigLoader']
