# Path: xbrl_parser/parser_modes.py
"""
Parser Mode Configurations

Different parsing modes optimized for specific use cases.
"""

from enum import Enum
from dataclasses import dataclass


class ParsingMode(Enum):
    """Parsing mode selection."""
    FULL = "full"
    FACTS_ONLY = "facts_only"
    VALIDATION_ONLY = "validation_only"
    METADATA_ONLY = "metadata_only"
    STREAMING = "streaming"
    QUICK_SCAN = "quick_scan"


@dataclass
class ModeConfiguration:
    """Configuration for parsing mode."""
    mode: ParsingMode
    extract_facts: bool = True
    extract_contexts: bool = True
    extract_units: bool = True
    load_taxonomy: bool = True
    validate_structure: bool = True
    validate_calculations: bool = True
    validate_dimensions: bool = True
    market_validation: bool = True
    serialize_output: bool = True
    create_indexes: bool = False
    enable_checkpoints: bool = True
    enable_profiling: bool = False
    enable_metrics: bool = True
    streaming_mode: bool = False
    description: str = ""


MODE_CONFIGURATIONS = {
    ParsingMode.FULL: ModeConfiguration(
        mode=ParsingMode.FULL,
        extract_facts=True,
        extract_contexts=True,
        extract_units=True,
        load_taxonomy=True,
        validate_structure=True,
        validate_calculations=True,
        validate_dimensions=True,
        market_validation=True,
        serialize_output=True,
        create_indexes=False,
        enable_checkpoints=True,
        enable_profiling=False,
        enable_metrics=True,
        streaming_mode=False,
        description="Full parsing with all validation and output"
    ),
    
    ParsingMode.FACTS_ONLY: ModeConfiguration(
        mode=ParsingMode.FACTS_ONLY,
        extract_facts=True,
        extract_contexts=True,
        extract_units=True,
        load_taxonomy=False,
        validate_structure=False,
        validate_calculations=False,
        validate_dimensions=False,
        market_validation=False,
        serialize_output=True,
        create_indexes=False,
        enable_checkpoints=False,
        enable_profiling=False,
        enable_metrics=True,
        streaming_mode=False,
        description="Extract facts only, no validation"
    ),
    
    ParsingMode.VALIDATION_ONLY: ModeConfiguration(
        mode=ParsingMode.VALIDATION_ONLY,
        extract_facts=True,
        extract_contexts=True,
        extract_units=True,
        load_taxonomy=True,
        validate_structure=True,
        validate_calculations=True,
        validate_dimensions=True,
        market_validation=True,
        serialize_output=False,
        create_indexes=False,
        enable_checkpoints=False,
        enable_profiling=False,
        enable_metrics=True,
        streaming_mode=False,
        description="Validate only, no output serialization"
    ),
    
    ParsingMode.METADATA_ONLY: ModeConfiguration(
        mode=ParsingMode.METADATA_ONLY,
        extract_facts=False,
        extract_contexts=False,
        extract_units=False,
        load_taxonomy=False,
        validate_structure=False,
        validate_calculations=False,
        validate_dimensions=False,
        market_validation=False,
        serialize_output=True,
        create_indexes=False,
        enable_checkpoints=False,
        enable_profiling=False,
        enable_metrics=False,
        streaming_mode=False,
        description="Extract metadata only, skip facts"
    ),
    
    ParsingMode.STREAMING: ModeConfiguration(
        mode=ParsingMode.STREAMING,
        extract_facts=True,
        extract_contexts=True,
        extract_units=True,
        load_taxonomy=True,
        validate_structure=True,
        validate_calculations=False,
        validate_dimensions=False,
        market_validation=False,
        serialize_output=True,
        create_indexes=False,
        enable_checkpoints=True,
        enable_profiling=False,
        enable_metrics=True,
        streaming_mode=True,
        description="Memory-efficient streaming for large files"
    ),
    
    ParsingMode.QUICK_SCAN: ModeConfiguration(
        mode=ParsingMode.QUICK_SCAN,
        extract_facts=True,
        extract_contexts=False,
        extract_units=False,
        load_taxonomy=False,
        validate_structure=False,
        validate_calculations=False,
        validate_dimensions=False,
        market_validation=False,
        serialize_output=False,
        create_indexes=False,
        enable_checkpoints=False,
        enable_profiling=False,
        enable_metrics=False,
        streaming_mode=False,
        description="Ultra-fast fact counting, minimal extraction"
    ),
}


def get_mode_config(mode: ParsingMode) -> ModeConfiguration:
    """Get configuration for mode."""
    return MODE_CONFIGURATIONS[mode]


def list_modes() -> list:
    """list available modes with descriptions."""
    return [
        f"{mode.value}: {config.description}"
        for mode, config in MODE_CONFIGURATIONS.items()
    ]


__all__ = [
    'ParsingMode',
    'ModeConfiguration',
    'get_mode_config',
    'list_modes',
]