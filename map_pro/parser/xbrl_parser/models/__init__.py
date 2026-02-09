# Path: xbrl_parser/models/__init__.py
"""
XBRL Parser Data Models

Complete set of data models for XBRL parsing:
- Error handling and validation
- Core XBRL structures (Fact, Context, Unit, Concept)
- Relationship networks
- Parsed filing result

All models use dataclasses for type safety and immutability.
"""

# ==============================================================================
# CONFIGURATION (Phase 1.1)
# ==============================================================================

from ..models.config import (
    # Enums
    ValidationLevel,
    ParsingMode,
    LogFormat,
    ConfigProfile,
    MarketProfile,
    # Classes
    ParserConfig,
    # Helper functions
    create_config,
)

# ==============================================================================
# ERROR HANDLING & VALIDATION (Phase 1.4)
# ==============================================================================

from ..models.error import (
    # Enums
    ErrorSeverity,
    ReliabilityLevel,
    ErrorCategory,
    RecoveryStrategy,
    # Classes
    ParsingError,
    ErrorCollection,
    # Helper functions
    create_error,
    create_critical_error,
    create_standard_error,
    create_warning,
    create_info,
)

from ..models.validation import (
    # Enums
    ValidationStatus,
    # Classes
    ValidationResult,
    ValidationSummary,
    CompletenessAudit,
    CalculationValidation,
    # Helper functions
    create_validation_result,
    create_passed_validation,
    create_failed_validation,
    create_skipped_validation,
)

# ==============================================================================
# FACT DATA MODEL (Phase 1.2.3)
# ==============================================================================

from ..models.fact import (
    # Enums
    FactReliability,
    FactType,
    # Classes
    Fact,
    # Helper functions
    create_fact,
    create_numeric_fact,
    create_text_fact,
    create_nil_fact,
)

# ==============================================================================
# CONTEXT DATA MODEL (Phase 1.2.3)
# ==============================================================================

from ..models.context import (
    # Enums
    PeriodType,
    # Classes
    EntityIdentifier,
    Period,
    ExplicitDimension,
    TypedDimension,
    Segment,
    Scenario,
    Context,
    # Helper functions
    create_context,
    create_instant_context,
    create_duration_context,
)

# ==============================================================================
# UNIT DATA MODEL (Phase 1.2.3)
# ==============================================================================

from ..models.unit import (
    # Enums
    UnitType,
    # Classes
    Unit,
    # Helper functions
    create_unit,
    create_simple_unit,
    create_complex_unit,
    create_currency_unit,
    create_shares_unit,
    create_pure_unit,
)

# ==============================================================================
# CONCEPT DATA MODEL (Phase 1.2.3)
# ==============================================================================

from ..models.concept import (
    # Enums
    ConceptType,
    ConceptPeriodType,
    BalanceType,
    # Classes
    Concept,
    # Helper functions
    create_concept,
    create_monetary_concept,
    create_shares_concept,
    create_abstract_concept,
)

# ==============================================================================
# RELATIONSHIP DATA MODEL (Phase 1.2.3)
# ==============================================================================

from ..models.relationship import (
    # Enums
    RelationshipType,
    # Classes
    Relationship,
    PresentationRelationship,
    CalculationRelationship,
    DefinitionRelationship,
    Label,
    Reference,
    # Helper functions
    create_presentation_relationship,
    create_calculation_relationship,
    create_definition_relationship,
)

# ==============================================================================
# PARSED FILING (TOP-LEVEL) (Phase 1.2.3)
# ==============================================================================

from ..models.parsed_filing import (
    # Classes
    FilingMetadata,
    TaxonomyData,
    InstanceData,
    ParsingStatistics,
    Provenance,
    ParsedFiling,
    # Helper functions
    create_parsed_filing,
)

# ==============================================================================
# EXPORTS
# ==============================================================================

__all__ = [
    # Configuration
    'ValidationLevel',
    'ParsingMode',
    'LogFormat',
    'ConfigProfile',
    'MarketProfile',
    'ParserConfig',
    'create_config',
    
    # Error handling
    'ErrorSeverity',
    'ReliabilityLevel',
    'ErrorCategory',
    'RecoveryStrategy',
    'ParsingError',
    'ErrorCollection',
    'create_error',
    'create_critical_error',
    'create_standard_error',
    'create_warning',
    'create_info',
    
    # Validation
    'ValidationStatus',
    'ValidationResult',
    'ValidationSummary',
    'CompletenessAudit',
    'CalculationValidation',
    'create_validation_result',
    'create_passed_validation',
    'create_failed_validation',
    'create_skipped_validation',
    
    # Fact
    'FactReliability',
    'FactType',
    'Fact',
    'create_fact',
    'create_numeric_fact',
    'create_text_fact',
    'create_nil_fact',
    
    # Context
    'PeriodType',
    'EntityIdentifier',
    'Period',
    'ExplicitDimension',
    'TypedDimension',
    'Segment',
    'Scenario',
    'Context',
    'create_context',
    'create_instant_context',
    'create_duration_context',
    
    # Unit
    'UnitType',
    'Unit',
    'create_unit',
    'create_simple_unit',
    'create_complex_unit',
    'create_currency_unit',
    'create_shares_unit',
    'create_pure_unit',
    
    # Concept
    'ConceptType',
    'ConceptPeriodType',
    'BalanceType',
    'Concept',
    'create_concept',
    'create_monetary_concept',
    'create_shares_concept',
    'create_abstract_concept',
    
    # Relationship
    'RelationshipType',
    'Relationship',
    'PresentationRelationship',
    'CalculationRelationship',
    'DefinitionRelationship',
    'Label',
    'Reference',
    'create_presentation_relationship',
    'create_calculation_relationship',
    'create_definition_relationship',
    
    # Parsed Filing
    'FilingMetadata',
    'TaxonomyData',
    'InstanceData',
    'ParsingStatistics',
    'Provenance',
    'ParsedFiling',
    'create_parsed_filing',
]
