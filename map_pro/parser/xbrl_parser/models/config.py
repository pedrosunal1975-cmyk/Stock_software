# Path: xbrl_parser/models/config.py
"""
Parser Configuration Schema

Type-safe, validated configuration for XBRL Parser using Pydantic.
Provides ParserConfig model and configuration profiles.

Design:
- Pydantic v2 for validation and serialization
- Immutable configuration (frozen)
- Sensible defaults for all settings
- Profile-based configuration (Quick, Standard, Strict, Research, Production)
- Market-specific profiles (US SEC, EU ESEF, UK FRC)
"""

from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class ValidationLevel(str, Enum):
    """Validation thoroughness levels."""
    NONE = "none"
    BASIC = "basic"
    FULL = "full"


class ParsingMode(str, Enum):
    """Parsing operation modes."""
    FULL = "full"
    FACTS_ONLY = "facts_only"
    VALIDATION_ONLY = "validation_only"
    STREAMING = "streaming"


class LogFormat(str, Enum):
    """Log output formats."""
    JSON = "json"
    TEXT = "text"
    STRUCTURED = "structured"


class ConfigProfile(str, Enum):
    """Named configuration profiles."""
    QUICK = "quick"
    STANDARD = "standard"
    STRICT = "strict"
    RESEARCH = "research"
    PRODUCTION = "production"


class MarketProfile(str, Enum):
    """Market-specific configuration profiles."""
    US_SEC = "us_sec"
    EU_ESEF = "eu_esef"
    UK_FRC = "uk_frc"
    IFRS = "ifrs"
    GENERIC = "generic"


class ParserConfig(BaseModel):
    """
    Type-safe parser configuration with validation.
    
    This is the main configuration object for the XBRL Parser.
    All settings are validated and type-checked using Pydantic.
    
    Example:
        # Create with defaults
        config = ParserConfig()
        
        # Create from profile
        config = ParserConfig.from_profile(ConfigProfile.STRICT)
        
        # Create custom
        config = ParserConfig(
            strict_mode=True,
            validation_level=ValidationLevel.FULL,
            max_memory_mb=8192
        )
    """
    
    # ========================================================================
    # CORE SETTINGS
    # ========================================================================
    
    strict_mode: bool = Field(
        default=False,
        description="If True, fail on first error instead of continuing"
    )
    
    validation_level: ValidationLevel = Field(
        default=ValidationLevel.FULL,
        description="Validation thoroughness: none, basic, or full"
    )
    
    parsing_mode: ParsingMode = Field(
        default=ParsingMode.FULL,
        description="Parsing mode: full, facts_only, validation_only, or streaming"
    )
    
    # ========================================================================
    # MEMORY & PERFORMANCE
    # ========================================================================
    
    max_memory_mb: int = Field(
        default=4096,
        ge=512,
        le=65536,
        description="Maximum memory usage in MB (512-65536)"
    )
    
    enable_streaming: bool = Field(
        default=True,
        description="Enable streaming mode for large files"
    )
    
    streaming_threshold_mb: int = Field(
        default=50,
        ge=10,
        le=500,
        description="File size threshold for streaming mode (MB)"
    )
    
    streaming_batch_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Number of facts per streaming batch"
    )
    
    timeout_seconds: int = Field(
        default=0,
        ge=0,
        description="Parser timeout in seconds (0 = no timeout)"
    )
    
    max_concurrent_jobs: int = Field(
        default=3,
        ge=1,
        le=32,
        description="Maximum concurrent parsing jobs"
    )
    
    # ========================================================================
    # CACHING
    # ========================================================================
    
    enable_taxonomy_caching: bool = Field(
        default=True,
        description="Enable taxonomy caching"
    )
    
    taxonomy_cache_ttl_hours: int = Field(
        default=168,
        ge=1,
        le=8760,
        description="Taxonomy cache TTL in hours (1-8760)"
    )
    
    enable_result_caching: bool = Field(
        default=True,
        description="Enable result caching"
    )
    
    result_cache_ttl_hours: int = Field(
        default=24,
        ge=1,
        le=720,
        description="Result cache TTL in hours (1-720)"
    )
    
    # ========================================================================
    # VALIDATION SETTINGS
    # ========================================================================
    
    enable_calculation_validation: bool = Field(
        default=True,
        description="Enable calculation validation"
    )
    
    calculation_tolerance: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="Calculation tolerance (0.0-1.0)"
    )
    
    enable_dimensional_validation: bool = Field(
        default=True,
        description="Enable dimensional validation"
    )
    
    enable_completeness_audit: bool = Field(
        default=True,
        description="Enable completeness audit"
    )
    
    min_quality_score: float = Field(
        default=70.0,
        ge=0.0,
        le=100.0,
        description="Minimum quality score threshold (0-100)"
    )
    
    # ========================================================================
    # ERROR HANDLING
    # ========================================================================
    
    continue_on_error: bool = Field(
        default=True,
        description="Continue parsing on errors vs fail fast"
    )
    
    max_errors: int = Field(
        default=0,
        ge=0,
        description="Maximum errors before stopping (0 = unlimited)"
    )
    
    enable_error_recovery: bool = Field(
        default=True,
        description="Enable error recovery strategies"
    )
    
    enable_checkpoints: bool = Field(
        default=True,
        description="Enable checkpoint/resume for large files"
    )
    
    checkpoint_interval: int = Field(
        default=5000,
        ge=100,
        le=50000,
        description="Facts per checkpoint (100-50000)"
    )
    
    # ========================================================================
    # FEATURE FLAGS
    # ========================================================================
    
    enable_footnotes: bool = Field(
        default=True,
        description="Enable footnote extraction"
    )
    
    enable_ixbrl: bool = Field(
        default=True,
        description="Enable inline XBRL support"
    )
    
    enable_tuples: bool = Field(
        default=True,
        description="Enable tuple support (deprecated but in old filings)"
    )
    
    enable_relationship_networks: bool = Field(
        default=True,
        description="Enable relationship network building"
    )
    
    enable_label_extraction: bool = Field(
        default=True,
        description="Enable label extraction (multi-language)"
    )
    
    enable_reference_extraction: bool = Field(
        default=True,
        description="Enable reference extraction"
    )
    
    # ========================================================================
    # OUTPUT SETTINGS
    # ========================================================================
    
    include_provenance: bool = Field(
        default=True,
        description="Include provenance in output"
    )
    
    include_statistics: bool = Field(
        default=True,
        description="Include statistics in output"
    )
    
    include_validation_results: bool = Field(
        default=True,
        description="Include validation results in output"
    )
    
    json_pretty_print: bool = Field(
        default=True,
        description="Pretty-print JSON output"
    )
    
    json_indent: int = Field(
        default=2,
        ge=0,
        le=8,
        description="JSON indentation level (0-8)"
    )
    
    # ========================================================================
    # LOGGING & DEBUG
    # ========================================================================
    
    log_format: LogFormat = Field(
        default=LogFormat.JSON,
        description="Log format: json, text, or structured"
    )
    
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Log level"
    )
    
    verbose_errors: bool = Field(
        default=True,
        description="Include verbose error messages"
    )
    
    include_stack_traces: bool = Field(
        default=True,
        description="Include stack traces in errors"
    )
    
    # ========================================================================
    # INDEXING
    # ========================================================================
    
    enable_indexing: bool = Field(
        default=True,
        description="Enable SQLite indexing for fast queries"
    )
    
    index_batch_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Index batch size (100-10000)"
    )
    
    # ========================================================================
    # MARKET-SPECIFIC
    # ========================================================================
    
    enable_market_auto_detection: bool = Field(
        default=True,
        description="Auto-detect market from namespaces"
    )
    
    enable_sec_validation: bool = Field(
        default=True,
        description="Enable SEC-specific validation"
    )
    
    enable_frc_validation: bool = Field(
        default=True,
        description="Enable FRC-specific validation"
    )
    
    enable_esma_validation: bool = Field(
        default=True,
        description="Enable ESMA-specific validation"
    )
    
    enable_ifrs_validation: bool = Field(
        default=True,
        description="Enable IFRS-specific validation"
    )
    
    # ========================================================================
    # ADVANCED
    # ========================================================================
    
    lazy_load_taxonomies: bool = Field(
        default=True,
        description="Lazy load taxonomies on demand"
    )
    
    enable_multithreading: bool = Field(
        default=True,
        description="Enable multi-threading"
    )
    
    worker_threads: int = Field(
        default=0,
        ge=0,
        le=64,
        description="Worker threads (0 = auto-detect CPU count)"
    )
    
    # Pydantic v2 configuration
    model_config = {
        'frozen': True,  # Make configuration immutable
        'use_enum_values': True,
        'validate_assignment': True,
    }
    
    @field_validator('max_errors')
    @classmethod
    def validate_max_errors(cls, v: int, info) -> int:
        """Validate max_errors is 0 in strict mode."""
        if info.data.get('strict_mode') and v != 0:
            raise ValueError("strict_mode requires max_errors=0")
        return v
    
    @model_validator(mode='after')
    def validate_streaming_settings(self) -> 'ParserConfig':
        """Validate streaming-related settings are consistent."""
        if self.parsing_mode == ParsingMode.STREAMING:
            if not self.enable_streaming:
                raise ValueError(
                    "parsing_mode='streaming' requires enable_streaming=True"
                )
        return self
    
    @model_validator(mode='after')
    def validate_memory_settings(self) -> 'ParserConfig':
        """Validate memory settings are reasonable."""
        if self.enable_streaming and self.streaming_threshold_mb > self.max_memory_mb:
            raise ValueError(
                f"streaming_threshold_mb ({self.streaming_threshold_mb}) "
                f"cannot exceed max_memory_mb ({self.max_memory_mb})"
            )
        return self
    
    # ========================================================================
    # FACTORY METHODS - NAMED PROFILES
    # ========================================================================
    
    @classmethod
    def from_profile(cls, profile: ConfigProfile) -> 'ParserConfig':
        """
        Create configuration from named profile.
        
        Args:
            profile: Configuration profile to use
            
        Returns:
            ParserConfig instance
            
        Example:
            config = ParserConfig.from_profile(ConfigProfile.STRICT)
        """
        profiles = {
            ConfigProfile.QUICK: cls._quick_profile,
            ConfigProfile.STANDARD: cls._standard_profile,
            ConfigProfile.STRICT: cls._strict_profile,
            ConfigProfile.RESEARCH: cls._research_profile,
            ConfigProfile.PRODUCTION: cls._production_profile,
        }
        return profiles[profile]()
    
    @classmethod
    def _quick_profile(cls) -> 'ParserConfig':
        """Quick profile: Fast parsing, minimal validation."""
        return cls(
            strict_mode=False,
            validation_level=ValidationLevel.BASIC,
            enable_calculation_validation=False,
            enable_dimensional_validation=False,
            enable_completeness_audit=False,
            enable_relationship_networks=False,
            enable_label_extraction=False,
            enable_reference_extraction=False,
            enable_indexing=False,
            include_statistics=False,
            include_validation_results=False,
        )
    
    @classmethod
    def _standard_profile(cls) -> 'ParserConfig':
        """Standard profile: Balanced approach (default)."""
        return cls()  # Uses defaults
    
    @classmethod
    def _strict_profile(cls) -> 'ParserConfig':
        """Strict profile: Maximum validation, fail on errors."""
        return cls(
            strict_mode=True,
            validation_level=ValidationLevel.FULL,
            continue_on_error=False,
            max_errors=0,
            enable_calculation_validation=True,
            enable_dimensional_validation=True,
            enable_completeness_audit=True,
            min_quality_score=95.0,
            verbose_errors=True,
            include_stack_traces=True,
        )
    
    @classmethod
    def _research_profile(cls) -> 'ParserConfig':
        """Research profile: Full data extraction, all features."""
        return cls(
            strict_mode=False,
            validation_level=ValidationLevel.FULL,
            enable_relationship_networks=True,
            enable_label_extraction=True,
            enable_reference_extraction=True,
            enable_footnotes=True,
            enable_indexing=True,
            include_provenance=True,
            include_statistics=True,
            include_validation_results=True,
            json_pretty_print=True,
        )
    
    @classmethod
    def _production_profile(cls) -> 'ParserConfig':
        """Production profile: Optimized for reliability and performance."""
        return cls(
            strict_mode=False,
            validation_level=ValidationLevel.FULL,
            max_memory_mb=8192,
            enable_streaming=True,
            enable_taxonomy_caching=True,
            enable_result_caching=True,
            continue_on_error=True,
            enable_error_recovery=True,
            enable_checkpoints=True,
            enable_multithreading=True,
            min_quality_score=85.0,
            log_format=LogFormat.JSON,
        )
    
    # ========================================================================
    # FACTORY METHODS - MARKET PROFILES
    # ========================================================================
    
    @classmethod
    def from_market_profile(cls, market: MarketProfile) -> 'ParserConfig':
        """
        Create configuration from market profile.
        
        Args:
            market: Market profile to use
            
        Returns:
            ParserConfig instance
            
        Example:
            config = ParserConfig.from_market_profile(MarketProfile.US_SEC)
        """
        profiles = {
            MarketProfile.US_SEC: cls._us_sec_profile,
            MarketProfile.EU_ESEF: cls._eu_esef_profile,
            MarketProfile.UK_FRC: cls._uk_frc_profile,
            MarketProfile.IFRS: cls._ifrs_profile,
            MarketProfile.GENERIC: cls._standard_profile,
        }
        return profiles[market]()
    
    @classmethod
    def _us_sec_profile(cls) -> 'ParserConfig':
        """US SEC profile: DEI required, SEC-specific validations."""
        return cls(
            validation_level=ValidationLevel.FULL,
            enable_sec_validation=True,
            enable_frc_validation=False,
            enable_esma_validation=False,
            enable_calculation_validation=True,
            enable_dimensional_validation=True,
            enable_ixbrl=True,  # SEC allows both formats
            min_quality_score=80.0,
        )
    
    @classmethod
    def _eu_esef_profile(cls) -> 'ParserConfig':
        """EU ESEF profile: Inline XBRL mandatory, anchoring rules."""
        return cls(
            validation_level=ValidationLevel.FULL,
            enable_sec_validation=False,
            enable_frc_validation=False,
            enable_esma_validation=True,
            enable_ixbrl=True,  # Mandatory for ESEF
            enable_dimensional_validation=True,
            min_quality_score=85.0,
        )
    
    @classmethod
    def _uk_frc_profile(cls) -> 'ParserConfig':
        """UK FRC profile: Companies House identifiers, UK-GAAP."""
        return cls(
            validation_level=ValidationLevel.FULL,
            enable_sec_validation=False,
            enable_frc_validation=True,
            enable_esma_validation=False,
            enable_ixbrl=True,  # Common in UK
            min_quality_score=80.0,
        )
    
    @classmethod
    def _ifrs_profile(cls) -> 'ParserConfig':
        """IFRS profile: International standards."""
        return cls(
            validation_level=ValidationLevel.FULL,
            enable_ifrs_validation=True,
            enable_sec_validation=False,
            enable_frc_validation=False,
            enable_esma_validation=False,
            min_quality_score=80.0,
        )
    
    def to_dict(self) -> dict:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary representation
        """
        return self.model_dump()
    
    def to_json(self) -> str:
        """
        Convert configuration to JSON string.
        
        Returns:
            JSON string representation
        """
        return self.model_dump_json(indent=2)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_config(
    profile: Optional[ConfigProfile] = None,
    market: Optional[MarketProfile] = None,
    **overrides
) -> ParserConfig:
    """
    Create parser configuration with optional profile and overrides.
    
    Args:
        profile: Optional named profile (Quick, Standard, Strict, etc.)
        market: Optional market profile (US_SEC, EU_ESEF, UK_FRC)
        **overrides: Additional settings to override
        
    Returns:
        ParserConfig instance
        
    Example:
        # Standard config
        config = create_config()
        
        # Quick profile
        config = create_config(profile=ConfigProfile.QUICK)
        
        # US SEC market
        config = create_config(market=MarketProfile.US_SEC)
        
        # Strict with overrides
        config = create_config(
            profile=ConfigProfile.STRICT,
            max_memory_mb=8192
        )
    """
    if profile and market:
        raise ValueError("Cannot specify both profile and market")
    
    if profile:
        config = ParserConfig.from_profile(profile)
    elif market:
        config = ParserConfig.from_market_profile(market)
    else:
        config = ParserConfig()
    
    # Apply overrides if provided
    if overrides:
        config = config.model_copy(update=overrides)
    
    return config


__all__ = [
    'ParserConfig',
    'ValidationLevel',
    'ParsingMode',
    'LogFormat',
    'ConfigProfile',
    'MarketProfile',
    'create_config',
]
