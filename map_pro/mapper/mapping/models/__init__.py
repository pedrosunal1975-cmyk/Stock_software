# Path: mapping/models/__init__.py
"""
Data Models Module

Core data models for the mapper.

REUSED FROM PARSER:
- Fact: XBRL fact representation
- Context: XBRL context (period, entity, dimensions)
- Unit: XBRL unit (currency, measures)
- Concept: XBRL concept definition
- Relationship: XBRL relationship (presentation, calculation)

NEW FOR MAPPER:
- ParsedFiling: Parsed filing with intelligence

Example:
    from ...mapping.models import (
        Fact, Context, Unit,
        MappedFact, MappingResult, ComparisonResult
    )
    
    # Use models
    fact = Fact(name='us-gaap:Revenue', value=1000000, ...)
    mapped = MappedFact(source_fact=fact, target_field='revenue.total', ...)
"""

# Reused from parser
from .fact import Fact
from .context import Context
from .unit import Unit
from .concept import Concept
from .relationship import Relationship

# New for mapper
from .parsed_filing import ParsedFiling

__all__ = [
    # Reused from parser
    'Fact',
    'Context',
    'Unit',
    'Concept',
    'Relationship',
    # New for mapper
    'ParsedFiling',
]
