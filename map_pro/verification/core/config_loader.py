# Path: verification/core/config_loader.py
"""
Configuration Loader for Verification Module

Loads configuration from .env file for the verification system.
Singleton pattern ensures consistent configuration across all components.

NO hardcoded paths, NO magic numbers.
All configuration comes from environment variables.
"""

import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv


# ==============================================================================
# DEFAULT CONFIGURATION VALUES
# ==============================================================================

# Logging Defaults
DEFAULT_LOG_RETENTION_DAYS: int = 30
DEFAULT_LOG_MAX_SIZE_MB: int = 10
DEFAULT_LOG_BACKUP_COUNT: int = 5

# Verification Configuration Defaults
DEFAULT_CALCULATION_TOLERANCE: float = 0.01
DEFAULT_ROUNDING_TOLERANCE: float = 1.0

# Scoring Thresholds
DEFAULT_EXCELLENT_THRESHOLD: int = 90
DEFAULT_GOOD_THRESHOLD: int = 75
DEFAULT_FAIR_THRESHOLD: int = 50
DEFAULT_POOR_THRESHOLD: int = 25

# Score Weights
DEFAULT_HORIZONTAL_WEIGHT: float = 0.40
DEFAULT_VERTICAL_WEIGHT: float = 0.40
DEFAULT_LIBRARY_WEIGHT: float = 0.20

# Performance Defaults
DEFAULT_MAX_CONCURRENT_JOBS: int = 3
DEFAULT_BATCH_SIZE: int = 10


class ConfigLoader:
    """
    Thread-safe singleton configuration loader for verification module.

    Loads configuration from environment variables with validation,
    type conversion, and sensible defaults.

    Example:
        config = ConfigLoader()
        output_dir = config.get('output_dir')  # Returns Path object
        tolerance = config.get('calculation_tolerance')  # Returns float
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
        # verification/core/config_loader.py -> go up 3 levels to map_pro/.env
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
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
            # BASE PATHS
            # ================================================================
            'data_root': self._get_path('VERIFICATION_DATA_ROOT', required=True),
            'loaders_root': self._get_path('VERIFICATION_LOADERS_ROOT', required=True),

            # ================================================================
            # ENVIRONMENT & DEBUG
            # ================================================================
            'environment': self._get_env('VERIFICATION_ENVIRONMENT', 'development'),
            'debug': self._get_bool('VERIFICATION_DEBUG', False),

            # ================================================================
            # INPUT PATHS (READ-ONLY - from other modules)
            # ================================================================
            'mapper_output_dir': self._get_path('VERIFICATION_MAPPER_OUTPUT_DIR', required=True),
            'parser_output_dir': self._get_path('VERIFICATION_PARSER_OUTPUT_DIR', required=True),
            'xbrl_filings_path': self._get_path('VERIFICATION_XBRL_FILINGS_PATH', required=True),
            'taxonomy_path': self._get_path('VERIFICATION_TAXONOMY_PATH', required=True),

            # ================================================================
            # OUTPUT PATHS (WRITE)
            # ================================================================
            'output_dir': self._get_path('VERIFICATION_OUTPUT_DIR', required=True),
            # Note: simplified_dir removed - StatementSimplifier not integrated into 3-stage pipeline

            # ================================================================
            # LOGGING CONFIGURATION
            # ================================================================
            'log_dir': self._get_path('VERIFICATION_LOG_DIR', required=True),
            'log_format': self._get_env('VERIFICATION_LOG_FORMAT', 'json'),
            'log_rotation': self._get_env('VERIFICATION_LOG_ROTATION', 'daily'),
            'log_retention_days': self._get_int(
                'VERIFICATION_LOG_RETENTION_DAYS', DEFAULT_LOG_RETENTION_DAYS
            ),
            'log_level': self._get_env('VERIFICATION_LOG_LEVEL', 'INFO'),
            'structured_logging': self._get_bool('VERIFICATION_STRUCTURED_LOGGING', True),

            # ================================================================
            # VERIFICATION CONFIGURATION
            # ================================================================
            'calculation_tolerance': self._get_float(
                'VERIFICATION_CALCULATION_TOLERANCE', DEFAULT_CALCULATION_TOLERANCE
            ),
            'rounding_tolerance': self._get_float(
                'VERIFICATION_ROUNDING_TOLERANCE', DEFAULT_ROUNDING_TOLERANCE
            ),
            'enable_library_checks': self._get_bool('VERIFICATION_ENABLE_LIBRARY_CHECKS', True),
            'strict_mode': self._get_bool('VERIFICATION_STRICT_MODE', False),
            'continue_on_error': self._get_bool('VERIFICATION_CONTINUE_ON_ERROR', True),

            # ================================================================
            # SCORING THRESHOLDS
            # ================================================================
            'excellent_threshold': self._get_int(
                'VERIFICATION_EXCELLENT_THRESHOLD', DEFAULT_EXCELLENT_THRESHOLD
            ),
            'good_threshold': self._get_int(
                'VERIFICATION_GOOD_THRESHOLD', DEFAULT_GOOD_THRESHOLD
            ),
            'fair_threshold': self._get_int(
                'VERIFICATION_FAIR_THRESHOLD', DEFAULT_FAIR_THRESHOLD
            ),
            'poor_threshold': self._get_int(
                'VERIFICATION_POOR_THRESHOLD', DEFAULT_POOR_THRESHOLD
            ),

            # ================================================================
            # SCORE WEIGHTS
            # ================================================================
            'horizontal_weight': self._get_float(
                'VERIFICATION_HORIZONTAL_WEIGHT', DEFAULT_HORIZONTAL_WEIGHT
            ),
            'vertical_weight': self._get_float(
                'VERIFICATION_VERTICAL_WEIGHT', DEFAULT_VERTICAL_WEIGHT
            ),
            'library_weight': self._get_float(
                'VERIFICATION_LIBRARY_WEIGHT', DEFAULT_LIBRARY_WEIGHT
            ),

            # ================================================================
            # PERFORMANCE
            # ================================================================
            'max_concurrent_jobs': self._get_int(
                'VERIFICATION_MAX_CONCURRENT_JOBS', DEFAULT_MAX_CONCURRENT_JOBS
            ),
            'batch_size': self._get_int('VERIFICATION_BATCH_SIZE', DEFAULT_BATCH_SIZE),
        }

        return config

    def _get_env(
        self,
        key: str,
        default: Optional[str] = None,
        required: bool = False
    ) -> Optional[str]:
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

    @classmethod
    def reset(cls):
        """Reset singleton for testing purposes."""
        cls._instance = None
        cls._initialized = False


__all__ = ['ConfigLoader']
