# Path: xbrl_parser/foundation/namespace_info.py
"""
Namespace Information Data Structures

Core data models for namespace tracking and management.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class TaxonomyType(str, Enum):
    """Known taxonomy types."""
    US_GAAP = "US-GAAP"
    IFRS = "IFRS"
    UK_GAAP = "UK-GAAP"
    ESEF = "ESEF"
    DEI = "DEI"
    CUSTOM = "CUSTOM"


@dataclass
class NamespaceInfo:
    """
    Information about a registered namespace.
    
    Attributes:
        uri: Namespace URI
        prefixes: list of prefixes mapping to this URI
        preferred_prefix: Primary prefix to use
        declared_in: Files where namespace is declared
        is_standard: Whether this is a standard taxonomy
        is_extension: Whether this is an extension taxonomy
        taxonomy_type: Type of taxonomy (US-GAAP, IFRS, etc.)
        region: Geographic region (US, UK, EU, etc.)
        first_seen: First file where namespace was seen
        usage_count: Number of times namespace is used
    """
    uri: str
    prefixes: list[str] = field(default_factory=list)
    preferred_prefix: str = ""
    declared_in: list[str] = field(default_factory=list)
    is_standard: bool = False
    is_extension: bool = False
    taxonomy_type: Optional[str] = None
    region: Optional[str] = None
    first_seen: Optional[str] = None
    usage_count: int = 0
    
    def add_prefix(self, prefix: str):
        """Add prefix if not already present."""
        if prefix not in self.prefixes:
            self.prefixes.append(prefix)
            if not self.preferred_prefix:
                self.preferred_prefix = prefix
    
    def add_declaration(self, location: str):
        """Add declaration location if not already present."""
        if location not in self.declared_in:
            self.declared_in.append(location)
            if not self.first_seen:
                self.first_seen = location
    
    def increment_usage(self):
        """Increment usage counter."""
        self.usage_count += 1
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'uri': self.uri,
            'prefixes': self.prefixes,
            'preferred_prefix': self.preferred_prefix,
            'is_standard': self.is_standard,
            'is_extension': self.is_extension,
            'taxonomy_type': self.taxonomy_type,
            'region': self.region,
            'declared_in': self.declared_in,
            'usage_count': self.usage_count
        }


@dataclass
class TaxonomyDetectionResult:
    """
    Result of taxonomy detection.
    
    Attributes:
        primary_taxonomy: Main taxonomy type
        detected_taxonomies: All detected taxonomy types
        namespaces_by_taxonomy: Namespace URIs grouped by taxonomy
        confidence: Detection confidence (0-1)
    """
    primary_taxonomy: TaxonomyType
    detected_taxonomies: set[TaxonomyType]
    namespaces_by_taxonomy: dict
    confidence: float
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'primary_taxonomy': self.primary_taxonomy.value,
            'detected_taxonomies': [t.value for t in self.detected_taxonomies],
            'namespaces_by_taxonomy': {
                k.value: v for k, v in self.namespaces_by_taxonomy.items()
            },
            'confidence': self.confidence
        }


@dataclass
class MarketMetadata:
    """
    Market and region information.
    
    Attributes:
        primary_market: Main market
        regulatory_authority: Regulatory body 
        reporting_framework: Accounting framework 
        detected_markets: All detected markets
        confidence: Detection confidence (0-1)
    """
    primary_market: str
    regulatory_authority: str
    reporting_framework: str
    detected_markets: set[str]
    confidence: float
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'primary_market': self.primary_market,
            'regulatory_authority': self.regulatory_authority,
            'reporting_framework': self.reporting_framework,
            'detected_markets': list(self.detected_markets),
            'confidence': self.confidence
        }


__all__ = [
    'TaxonomyType',
    'NamespaceInfo',
    'TaxonomyDetectionResult',
    'MarketMetadata'
]