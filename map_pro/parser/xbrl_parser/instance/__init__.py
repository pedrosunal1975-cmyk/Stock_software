# Path: xbrl_parser/instance/__init__.py
"""
Instance Document Parsing Module

This module provides components for parsing XBRL instance documents.

Main Components:
    - InstanceParser: Main orchestrator for instance parsing
    - ContextParser: Extracts context elements
    - UnitParser: Extracts unit elements
    - FactExtractor: Extracts fact elements
    - FootnoteExtractor: Extracts footnotes
    - constants: Namespace URIs and constants
    
Example:
    from ..instance import InstanceParser
    
    parser = InstanceParser()
    result = parser.parse_instance(Path("filing.xml"))
    
    print(f"Facts: {result.fact_count}")
    print(f"Contexts: {result.context_count}")
    print(f"Units: {result.unit_count}")
"""

from ..instance.instance_parser import (
    InstanceParser,
    InstanceParseResult
)
from ..instance.context_parser import ContextParser
from ..instance.unit_parser import UnitParser
from ..instance.fact_extractor import FactExtractor
from ..instance.footnote_extractor import (
    FootnoteExtractor,
    Footnote,
    FootnoteLink
)
from ..instance import constants


__all__ = [
    'InstanceParser',
    'InstanceParseResult',
    'ContextParser',
    'UnitParser',
    'FactExtractor',
    'FootnoteExtractor',
    'Footnote',
    'FootnoteLink',
    'constants'
]
