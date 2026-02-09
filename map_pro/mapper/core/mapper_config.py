# Path: core/mapper_config.py
"""
Mapper-Specific Configuration - Water Paradigm

Runtime configuration, constants, and defaults for statement extraction.
This complements ConfigLoader by providing mapper-specific settings and constants.

Water paradigm: Extract company's declared structure, no transformation.
"""

from dataclasses import dataclass
from enum import Enum


class ValidationLevel(Enum):
    """Validation strictness levels."""
    NONE = "none"        # No validation
    BASIC = "basic"      # Basic schema validation
    FULL = "full"        # Complete validation


@dataclass
class MapperRuntimeConfig:
    """
    Runtime configuration for mapper operations.
    
    This provides defaults and runtime settings that can be overridden
    per mapping operation.
    
    Attributes:
        validation_level: Validation strictness
        enable_caching: Enable result caching
        timeout_seconds: Timeout per filing (0 = no timeout)
    """
    
    validation_level: ValidationLevel = ValidationLevel.FULL
    enable_caching: bool = True
    timeout_seconds: int = 60
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary."""
        return {
            'validation_level': self.validation_level.value,
            'enable_caching': self.enable_caching,
            'timeout_seconds': self.timeout_seconds,
        }


# =============================================================================
# MAPPER CONSTANTS
# =============================================================================

# Coverage thresholds
COVERAGE_COMPLETE = 100.0    # All facts organized (100%)
COVERAGE_EXCELLENT = 98.0    # Excellent coverage (98%+)
COVERAGE_GOOD = 95.0         # Good coverage (95%+)
COVERAGE_ACCEPTABLE = 90.0   # Acceptable coverage (90%+)
COVERAGE_MINIMUM = 85.0      # Minimum acceptable (85%+)

# Quality score thresholds
QUALITY_EXCELLENT = 90.0     # Excellent quality (90%+)
QUALITY_GOOD = 80.0          # Good quality (80%+)
QUALITY_ACCEPTABLE = 70.0    # Acceptable quality (70%+)
QUALITY_POOR = 60.0          # Poor quality (60%+)
QUALITY_MINIMUM = 50.0       # Minimum acceptable (50%+)

# Timeout settings (seconds)
TIMEOUT_QUICK = 30           # Quick extraction (30s)
TIMEOUT_STANDARD = 60        # Standard extraction (60s)
TIMEOUT_EXTENDED = 120       # Extended extraction (2min)
TIMEOUT_UNLIMITED = 0        # No timeout

# Batch processing
BATCH_SIZE_SMALL = 10        # Small batch
BATCH_SIZE_MEDIUM = 50       # Medium batch
BATCH_SIZE_LARGE = 100       # Large batch
BATCH_SIZE_XLARGE = 500      # Extra large batch

# Cache TTL (hours)
CACHE_TTL_SHORT = 6          # Short-term cache (6h)
CACHE_TTL_MEDIUM = 24        # Medium-term cache (24h)
CACHE_TTL_LONG = 168         # Long-term cache (1 week)
CACHE_TTL_PERMANENT = 0      # Permanent cache (no expiry)


# =============================================================================
# DEFAULT CONFIGURATIONS
# =============================================================================

DEFAULT_OUTPUT_CONFIG = {
    'include_metadata': True,
    'include_provenance': True,
    'json_pretty_print': True,
    'json_indent': 2,
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_coverage_level(percent: float) -> str:
    """
    Get coverage level description from percentage.
    
    Args:
        percent: Coverage percentage (0.0-100.0)
        
    Returns:
        Coverage level description
        
    Example:
        >>> get_coverage_level(99.5)
        'EXCELLENT'
    """
    if percent >= COVERAGE_COMPLETE:
        return "COMPLETE"
    elif percent >= COVERAGE_EXCELLENT:
        return "EXCELLENT"
    elif percent >= COVERAGE_GOOD:
        return "GOOD"
    elif percent >= COVERAGE_ACCEPTABLE:
        return "ACCEPTABLE"
    elif percent >= COVERAGE_MINIMUM:
        return "MINIMUM"
    else:
        return "POOR"


def get_quality_level(score: float) -> str:
    """
    Get quality level description from score.
    
    Args:
        score: Quality score (0.0-100.0)
        
    Returns:
        Quality level description
        
    Example:
        >>> get_quality_level(92.5)
        'EXCELLENT'
    """
    if score >= QUALITY_EXCELLENT:
        return "EXCELLENT"
    elif score >= QUALITY_GOOD:
        return "GOOD"
    elif score >= QUALITY_ACCEPTABLE:
        return "ACCEPTABLE"
    elif score >= QUALITY_POOR:
        return "POOR"
    elif score >= QUALITY_MINIMUM:
        return "MINIMUM"
    else:
        return "UNACCEPTABLE"


__all__ = [
    'ValidationLevel',
    'MapperRuntimeConfig',
    'get_coverage_level',
    'get_quality_level',
]