# Path: xbrl_parser/ixbrl/__init__.py
"""
Inline XBRL (iXBRL) Module

This module provides components for parsing Inline XBRL documents.

iXBRL embeds XBRL data within HTML/XHTML documents for human readability
while maintaining machine-readable XBRL data.

Main Components:
    - IXBRLParser: Main parser for iXBRL documents
    - HTMLExtractor: Extracts iXBRL elements from HTML
    - IXTransformer: Transforms iXBRL to standard XBRL
    - constants: iXBRL namespace URIs and configuration constants
    
Example:
    from ..ixbrl import IXBRLParser
    
    parser = IXBRLParser()
    result = parser.parse_ixbrl(Path("filing.html"))
    
    print(f"Extracted {result.fact_count} facts from iXBRL")
    
    # Use transformed XBRL
    xbrl_xml = result.xbrl_document
"""

from ..ixbrl.ixbrl_parser import (
    IXBRLParser,
    IXBRLParseResult
)
from ..ixbrl.html_extractor import HTMLExtractor
from ..ixbrl.ix_transformer import IXTransformer
from ..ixbrl import constants


__all__ = [
    'IXBRLParser',
    'IXBRLParseResult',
    'HTMLExtractor',
    'IXTransformer',
    'constants'
]
