# Path: xbrl_parser/models/parsed_filing.py
"""
Parsed Filing Data Model

Top-level result object containing complete parsed XBRL filing.

This module defines:
- ParsedFiling (main result)
- FilingMetadata
- TaxonomyData
- InstanceData
- ParsingStatistics
- Provenance
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from pathlib import Path

from ..models.error import ErrorCollection, ReliabilityLevel
from ..models.validation import ValidationSummary
from ..models.fact import Fact
from ..models.context import Context
from ..models.unit import Unit
from ..models.concept import Concept
from ..models.relationship import (
    PresentationRelationship,
    CalculationRelationship,
    DefinitionRelationship,
    Label,
    Reference
)


# ==============================================================================
# FILING METADATA
# ==============================================================================

@dataclass
class FilingMetadata:
    """
    Filing identification and metadata.
    
    Attributes:
        filing_id: Unique filing identifier
        document_type: Document type (10-K, 10-Q, Annual Report, etc.)
        filing_date: Filing date
        period_end_date: Reporting period end date
        
        company_name: Company name
        entity_identifier: Primary entity identifier (CIK, LEI, etc.)
        
        market: Market/region (SEC, FRC, ESMA, IFRS)
        regulatory_authority: Regulatory body
        
        source_files: list of source file paths
        entry_point: Main entry point file
    """
    filing_id: Optional[str] = None
    document_type: Optional[str] = None
    filing_date: Optional[datetime] = None
    period_end_date: Optional[datetime] = None
    
    company_name: Optional[str] = None
    entity_identifier: Optional[str] = None
    
    market: Optional[str] = None
    regulatory_authority: Optional[str] = None
    
    source_files: list[Path] = field(default_factory=list)
    entry_point: Optional[Path] = None
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary."""
        return {
            'filing_id': self.filing_id,
            'document_type': self.document_type,
            'filing_date': self.filing_date.isoformat() if self.filing_date else None,
            'period_end_date': self.period_end_date.isoformat() if self.period_end_date else None,
            'company_name': self.company_name,
            'entity_identifier': self.entity_identifier,
            'market': self.market,
            'regulatory_authority': self.regulatory_authority,
            'source_file_count': len(self.source_files),
            'source_files': [str(f) for f in self.source_files],
            'entry_point': str(self.entry_point) if self.entry_point else None,
        }


# ==============================================================================
# TAXONOMY DATA
# ==============================================================================

@dataclass
class TaxonomyData:
    """
    Taxonomy information and structure.
    
    Attributes:
        namespaces: Namespace URI to prefix mapping
        schemas: Schema file paths
        linkbases: Linkbase file paths
        
        concepts: All concept definitions
        presentation_networks: Presentation relationships by role
        calculation_networks: Calculation relationships by role
        definition_networks: Definition relationships by role
        labels: Concept labels by concept and language
        references: Concept references
        
        primary_taxonomy: Primary taxonomy name (US-GAAP, IFRS, etc.)
        taxonomy_version: Taxonomy version/date
        extension_schemas: Extension taxonomy schemas
        
        fingerprint: Taxonomy fingerprint for caching
    """
    namespaces: dict[str, str] = field(default_factory=dict)
    schemas: list[Path] = field(default_factory=list)
    linkbases: list[Path] = field(default_factory=list)
    
    concepts: dict[str, Concept] = field(default_factory=dict)
    presentation_networks: dict[str, list[PresentationRelationship]] = field(default_factory=dict)
    calculation_networks: dict[str, list[CalculationRelationship]] = field(default_factory=dict)
    definition_networks: dict[str, list[DefinitionRelationship]] = field(default_factory=dict)
    labels: dict[str, list[Label]] = field(default_factory=dict)
    references: dict[str, list[Reference]] = field(default_factory=dict)
    
    primary_taxonomy: Optional[str] = None
    taxonomy_version: Optional[str] = None
    extension_schemas: list[Path] = field(default_factory=list)
    
    fingerprint: Optional[str] = None
    
    def get_concept(self, qname: str) -> Optional[Concept]:
        """Get concept by QName."""
        return self.concepts.get(qname)
    
    def get_labels(self, qname: str, language: str = "en") -> list[Label]:
        """Get labels for concept in specific language."""
        concept_labels = self.labels.get(qname, [])
        return [l for l in concept_labels if l.language == language]
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary."""
        return {
            'namespace_count': len(self.namespaces),
            'namespaces': self.namespaces,
            'schema_count': len(self.schemas),
            'linkbase_count': len(self.linkbases),
            'concept_count': len(self.concepts),
            'presentation_network_count': len(self.presentation_networks),
            'calculation_network_count': len(self.calculation_networks),
            'definition_network_count': len(self.definition_networks),
            'label_count': sum(len(labels) for labels in self.labels.values()),
            'reference_count': sum(len(refs) for refs in self.references.values()),
            'primary_taxonomy': self.primary_taxonomy,
            'taxonomy_version': self.taxonomy_version,
            'extension_schema_count': len(self.extension_schemas),
            'fingerprint': self.fingerprint,
        }


# ==============================================================================
# INSTANCE DATA
# ==============================================================================

@dataclass
class InstanceData:
    """
    Instance document data (facts, contexts, units).
    
    Attributes:
        facts: All facts
        contexts: All contexts by ID
        units: All units by ID
        
        footnotes: Footnotes by ID
        
        fact_count_by_concept: Fact counts by concept
        fact_count_by_type: Fact counts by type
    """
    facts: list[Fact] = field(default_factory=list)
    contexts: dict[str, Context] = field(default_factory=dict)
    units: dict[str, Unit] = field(default_factory=dict)
    namespaces: dict[str, str] = field(default_factory=dict)
    footnotes: dict[str, str] = field(default_factory=dict)
    
    fact_count_by_concept: dict[str, int] = field(default_factory=dict)
    fact_count_by_type: dict[str, int] = field(default_factory=dict)
    
    def get_context(self, context_id: str) -> Optional[Context]:
        """Get context by ID."""
        return self.contexts.get(context_id)
    
    def get_unit(self, unit_id: str) -> Optional[Unit]:
        """Get unit by ID."""
        return self.units.get(unit_id)
    
    def get_facts_by_concept(self, concept: str) -> list[Fact]:
        """Get all facts for specific concept."""
        return [f for f in self.facts if f.concept == concept]
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary."""
        return {
            'fact_count': len(self.facts),
            'context_count': len(self.contexts),
            'unit_count': len(self.units),
            'footnote_count': len(self.footnotes),
            'fact_count_by_concept': self.fact_count_by_concept,
            'fact_count_by_type': self.fact_count_by_type,
        }


# ==============================================================================
# PARSING STATISTICS
# ==============================================================================

@dataclass
class ParsingStatistics:
    """
    Parsing performance and count statistics.
    
    Attributes:
        total_duration_ms: Total parsing time in milliseconds
        
        phase_timings: Time spent in each phase (ms)
        component_timings: Time spent in each component (ms)
        
        memory_peak_mb: Peak memory usage in MB
        memory_by_component: Memory usage by component (MB)
        
        io_stats: IO statistics (files, bytes, cache hits)
        
        bottlenecks: Identified performance bottlenecks
    """
    total_duration_ms: float = 0.0
    
    phase_timings: dict[str, float] = field(default_factory=dict)
    component_timings: dict[str, float] = field(default_factory=dict)
    
    memory_peak_mb: float = 0.0
    memory_by_component: dict[str, float] = field(default_factory=dict)
    
    io_stats: dict[str, any] = field(default_factory=dict)
    
    bottlenecks: list[str] = field(default_factory=list)
    
    def add_phase_timing(self, phase: str, duration_ms: float) -> None:
        """Add timing for a phase."""
        self.phase_timings[phase] = duration_ms
    
    def add_component_timing(self, component: str, duration_ms: float) -> None:
        """Add timing for a component."""
        self.component_timings[component] = duration_ms
    
    def get_slowest_phase(self) -> Optional[str]:
        """Get slowest parsing phase."""
        if not self.phase_timings:
            return None
        return max(self.phase_timings.items(), key=lambda x: x[1])[0]
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary."""
        return {
            'total_duration_ms': self.total_duration_ms,
            'total_duration_sec': self.total_duration_ms / 1000.0,
            'phase_timings': self.phase_timings,
            'component_timings': self.component_timings,
            'memory_peak_mb': self.memory_peak_mb,
            'memory_by_component': self.memory_by_component,
            'io_stats': self.io_stats,
            'bottlenecks': self.bottlenecks,
            'slowest_phase': self.get_slowest_phase(),
        }


# ==============================================================================
# PROVENANCE
# ==============================================================================

@dataclass
class Provenance:
    """
    Parsing provenance and audit trail.
    
    Attributes:
        parser_version: Parser version string
        parsing_timestamp: When parsing occurred
        
        source_file_hashes: SHA-256 hashes of source files
        configuration: Configuration used
        
        parser_mode: Parsing mode used (full, facts_only, etc.)
        features_enabled: list of enabled features
        
        schema_version: Output schema version
    """
    parser_version: Optional[str] = None
    parsing_timestamp: Optional[datetime] = None
    
    source_file_hashes: dict[str, str] = field(default_factory=dict)
    configuration: dict[str, any] = field(default_factory=dict)
    
    parser_mode: Optional[str] = None
    features_enabled: list[str] = field(default_factory=list)
    
    schema_version: str = "1.0"
    
    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary."""
        return {
            'parser_version': self.parser_version,
            'parsing_timestamp': self.parsing_timestamp.isoformat() if self.parsing_timestamp else None,
            'source_file_count': len(self.source_file_hashes),
            'source_file_hashes': self.source_file_hashes,
            'configuration': self.configuration,
            'parser_mode': self.parser_mode,
            'features_enabled': self.features_enabled,
            'schema_version': self.schema_version,
        }


# ==============================================================================
# PARSED FILING (TOP-LEVEL)
# ==============================================================================

@dataclass
class ParsedFiling:
    """
    Complete parsed XBRL filing result.
    
    This is the top-level object returned by the parser containing:
    - Filing metadata
    - Taxonomy data
    - Instance data (facts, contexts, units)
    - Validation results
    - Parsing statistics
    - Provenance information
    - Error collection
    
    Attributes:
        metadata: Filing identification and metadata
        taxonomy: Taxonomy structure and definitions
        instance: Instance data (facts, contexts, units)
        validation: Validation results and quality assessment
        statistics: Parsing performance metrics
        provenance: Audit trail and configuration
        errors: All errors encountered during parsing
        
        reliability: Overall parsing reliability level
        quality_score: Overall quality score (0-100)
    """
    metadata: FilingMetadata = field(default_factory=FilingMetadata)
    taxonomy: TaxonomyData = field(default_factory=TaxonomyData)
    instance: InstanceData = field(default_factory=InstanceData)
    validation: ValidationSummary = field(default_factory=ValidationSummary)
    statistics: ParsingStatistics = field(default_factory=ParsingStatistics)
    provenance: Provenance = field(default_factory=Provenance)
    errors: ErrorCollection = field(default_factory=ErrorCollection)
    
    reliability: ReliabilityLevel = ReliabilityLevel.COMPLETE
    quality_score: float = 100.0
    
    def is_complete(self) -> bool:
        """Check if parsing completed successfully."""
        return self.reliability == ReliabilityLevel.COMPLETE
    
    def is_failed(self) -> bool:
        """Check if parsing failed."""
        return self.reliability == ReliabilityLevel.FAILED
    
    def has_errors(self) -> bool:
        """Check if filing has errors."""
        return self.errors.has_errors()
    
    def has_critical_errors(self) -> bool:
        """Check if filing has critical errors."""
        return self.errors.has_critical()
    
    def update_reliability(self) -> None:
        """
        Update overall reliability based on errors and validation.
        
        Uses both error collection and validation summary to determine
        the final reliability level.
        """
        # Get reliability from errors
        error_reliability = self.errors.determine_reliability()
        
        # Get reliability from validation
        validation_reliability = self.validation.reliability
        
        # Take the worse of the two
        if error_reliability.value < validation_reliability.value:
            self.reliability = error_reliability
        else:
            self.reliability = validation_reliability
        
        # Update quality score
        self.quality_score = self.validation.quality_score
    
    def to_dict(self, include_data: bool = True) -> dict[str, any]:
        """
        Convert to dictionary for serialization.
        
        Args:
            include_data: If True, include all facts/contexts/units.
                         If False, only include counts and metadata.
        
        Returns:
            Dictionary representation
        """
        result = {
            'metadata': self.metadata.to_dict(),
            'taxonomy': self.taxonomy.to_dict(),
            'instance': self.instance.to_dict(),
            'validation': self.validation.to_dict(),
            'statistics': self.statistics.to_dict(),
            'provenance': self.provenance.to_dict(),
            'errors': {
                'total_count': len(self.errors),
                'has_critical': self.errors.has_critical(),
                'has_errors': self.errors.has_errors(),
                'by_severity': {k.value: v for k, v in self.errors.count_by_severity().items()},
                'by_category': {k.value: v for k, v in self.errors.count_by_category().items()},
            },
            'reliability': self.reliability.value,
            'quality_score': self.quality_score,
            'is_complete': self.is_complete(),
        }
        
        # Optionally include full data
        if include_data:
            result['facts'] = [f.to_dict() for f in self.instance.facts]
            result['contexts'] = {k: v.to_dict() for k, v in self.instance.contexts.items()}
            result['units'] = {k: v.to_dict() for k, v in self.instance.units.items()}
            result['concepts'] = {k: v.to_dict() for k, v in self.taxonomy.concepts.items()}
            result['error_details'] = self.errors.to_dict_list()
        
        return result


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def create_parsed_filing(
    filing_id: Optional[str] = None,
    company_name: Optional[str] = None,
    **kwargs
) -> ParsedFiling:
    """
    Create a ParsedFiling with basic metadata.
    
    Args:
        filing_id: Filing identifier
        company_name: Company name
        **kwargs: Additional metadata fields
        
    Returns:
        ParsedFiling instance
    """
    metadata = FilingMetadata(
        filing_id=filing_id,
        company_name=company_name,
        **kwargs
    )
    
    return ParsedFiling(metadata=metadata)


__all__ = [
    'FilingMetadata',
    'TaxonomyData',
    'InstanceData',
    'ParsingStatistics',
    'Provenance',
    'ParsedFiling',
    'create_parsed_filing',
]
