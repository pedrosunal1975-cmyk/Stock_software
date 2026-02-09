# Path: xbrl_parser/ixbrl/ixbrl_parser.py
"""
Inline XBRL (iXBRL) Parser

Main parser for iXBRL documents embedded in HTML/XHTML.

This module handles:
- iXBRL document detection
- HTML parsing
- ix namespace element extraction
- Transformation to standard XBRL
- Hidden fact discovery
- Continuation processing

Example:
    from ..ixbrl import IXBRLParser
    
    parser = IXBRLParser()
    result = parser.parse_ixbrl(Path("filing.html"))
    
    print(f"Extracted {result.fact_count} facts from iXBRL")
"""

import logging
from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field
import time

from ...core.config_loader import ConfigLoader
from ..models.error import ParsingError, ErrorCategory, ErrorSeverity
from ..ixbrl.constants import (
    IX_NS_2013,
    IX_NS_2011,
    XBRLI_NS
)


@dataclass
class IXBRLParseResult:
    """
    Result of iXBRL document parsing.
    
    Contains extracted XBRL data and statistics.
    """
    # Extracted data (transformed to standard XBRL)
    xbrl_document: Optional[str] = None  # Transformed XML string
    
    # Statistics
    ixbrl_path: Optional[str] = None
    fact_count: int = 0
    hidden_fact_count: int = 0
    continuation_count: int = 0
    parse_time_seconds: float = 0.0
    
    # Metadata
    document_type: str = "HTML"  # HTML or XHTML
    ix_version: Optional[str] = None  # iXBRL specification version
    
    # Errors
    errors: list[ParsingError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class IXBRLParser:
    """
    Parses Inline XBRL (iXBRL) documents.
    
    Extracts XBRL data from HTML/XHTML documents and transforms to standard XBRL.
    
    Example:
        config = ConfigLoader()
        parser = IXBRLParser(config)
        
        # Parse iXBRL document
        result = parser.parse_ixbrl(Path("filing.html"))
        
        # Get transformed XBRL
        xbrl_xml = result.xbrl_document
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize iXBRL parser.
        
        Args:
            config: Configuration loader
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger(__name__)
        
        # Check if iXBRL is enabled
        self.enabled = self.config.get('enable_ixbrl', True)
        
        # Will import components lazily
        self._html_extractor = None
        self._transformer = None
        
        self.logger.info(f"IXBRLParser initialized (enabled={self.enabled})")
    
    def parse_ixbrl(self, ixbrl_path: Path) -> IXBRLParseResult:
        """
        Parse complete iXBRL document.
        
        Extracts real contexts, units, and schema references from HTML,
        then transforms ix: elements to standard XBRL format.
        
        Args:
            ixbrl_path: Path to iXBRL HTML/XHTML file
            
        Returns:
            IXBRLParseResult with transformed XBRL and statistics
            
        Example:
            result = parser.parse_ixbrl(Path("filing.html"))
            print(f"Extracted {result.fact_count} facts")
        """
        self.logger.info(f"Parsing iXBRL document: {ixbrl_path}")
        
        start_time = time.time()
        result = IXBRLParseResult()
        result.ixbrl_path = str(ixbrl_path)
        
        if not self.enabled:
            self.logger.warning("iXBRL parsing is disabled")
            result.warnings.append("iXBRL parsing is disabled in configuration")
            return result
        
        try:
            # Check file exists
            if not ixbrl_path.exists():
                raise FileNotFoundError(f"iXBRL file not found: {ixbrl_path}")
            
            # Detect document type
            result.document_type = self._detect_document_type(ixbrl_path)
            
            # Extract all iXBRL data from HTML
            extraction_data = self._extract_all_ixbrl_data(ixbrl_path, result)
            
            ix_elements = extraction_data['ix_elements']
            contexts = extraction_data['contexts']
            units = extraction_data['units']
            schema_refs = extraction_data['schema_refs']
            footnotes = extraction_data['footnotes']
            nsmap = extraction_data['nsmap']
            
            self.logger.info(
                f"Extracted from iXBRL: {len(ix_elements)} facts, "
                f"{len(contexts)} contexts, {len(units)} units, "
                f"{len(schema_refs)} schema refs, {len(footnotes)} footnotes"
            )
            
            # Transform to standard XBRL using real extracted data
            result.xbrl_document = self._transform_to_xbrl(
                ix_elements,
                contexts,
                units,
                footnotes,
                nsmap,
                result
            )
            
            # Update statistics
            result.fact_count = len([e for e in ix_elements if self._is_fact_element(e)])
            result.hidden_fact_count = len([e for e in ix_elements if self._is_hidden(e)])
            
            self.logger.info(
                f"iXBRL parsed successfully: {result.fact_count} facts "
                f"({result.hidden_fact_count} hidden)"
            )
            
        except Exception as e:
            self.logger.error(f"iXBRL parsing failed: {e}", exc_info=True)
            result.errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                message=f"Failed to parse iXBRL: {e}",
                severity=ErrorSeverity.ERROR,
                source_file=str(ixbrl_path)
            ))
        
        result.parse_time_seconds = time.time() - start_time
        return result
    
    def _detect_document_type(self, file_path: Path) -> str:
        """
        Detect if document is HTML or XHTML.
        
        Args:
            file_path: Path to file
            
        Returns:
            'HTML' or 'XHTML'
        """
        # Read first few lines
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            header = f.read(1024).lower()
        
        # Check for XHTML doctype
        if 'xhtml' in header:
            return 'XHTML'
        
        return 'HTML'
    
    def _extract_all_ixbrl_data(self, file_path: Path, result: IXBRLParseResult) -> dict:
        """
        Extract ALL iXBRL data from HTML document.
        
        Extracts:
        - ix: fact elements
        - xbrli:context elements (from ix:resources/ix:header)
        - xbrli:unit elements (from ix:resources/ix:header)
        - link:schemaRef elements
        - ix:footnote elements
        - Namespace map from root element
        
        Args:
            file_path: Path to iXBRL file
            result: Parse result for error tracking
            
        Returns:
            Dictionary with keys: ix_elements, contexts, units, schema_refs, footnotes, nsmap
        """
        from ..ixbrl.html_extractor import HTMLExtractor
        
        if self._html_extractor is None:
            self._html_extractor = HTMLExtractor(self.config)
        
        # Parse HTML once
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Try XHTML parser first
        try:
            from lxml import etree
            tree = etree.fromstring(content)
        except etree.XMLSyntaxError:
            # Fall back to HTML parser
            from lxml import html as lxml_html
            tree = lxml_html.fromstring(content)
        
        # Extract namespace map from root element
        nsmap = self._html_extractor.extract_namespace_map(tree)
        
        # Extract ix: fact elements
        ix_elements = self._html_extractor.extract_ix_elements(file_path, result)
        
        # Extract real contexts from HTML
        contexts = self._html_extractor.extract_contexts(tree)
        
        # Extract real units from HTML
        units = self._html_extractor.extract_units(tree)
        
        # Extract schema references
        schema_refs = self._html_extractor.extract_schema_refs(tree)
        
        # Extract footnotes (for future use)
        footnotes = self._html_extractor.extract_footnotes(tree)
        
        return {
            'ix_elements': ix_elements,
            'contexts': contexts,
            'units': units,
            'schema_refs': schema_refs,
            'footnotes': footnotes,
            'nsmap': nsmap
        }
    
    def _extract_ix_elements(self, file_path: Path, result: IXBRLParseResult) -> list:
        """
        Extract iXBRL elements from HTML document.
        
        DEPRECATED: Use _extract_all_ixbrl_data() instead.
        
        Args:
            file_path: Path to iXBRL file
            result: Parse result for error tracking
            
        Returns:
            list of ix: namespace elements
        """
        from ..ixbrl.html_extractor import HTMLExtractor
        
        if self._html_extractor is None:
            self._html_extractor = HTMLExtractor(self.config)
        
        return self._html_extractor.extract_ix_elements(file_path, result)
    
    def _transform_to_xbrl(
        self,
        ix_elements: list,
        contexts: list,
        units: list,
        footnotes: list,
        nsmap: dict[str, str],
        result: IXBRLParseResult
    ) -> str:
        """
        Transform iXBRL elements to standard XBRL XML.
        
        Uses real extracted contexts, units, footnotes, and namespace map.
        
        Args:
            ix_elements: list of ix: namespace elements
            contexts: list of real xbrli:context elements
            units: list of real xbrli:unit elements
            footnotes: list of ix:footnote elements
            nsmap: Namespace map from HTML root
            result: Parse result for error tracking
            
        Returns:
            Standard XBRL XML string
        """
        from ..ixbrl.ix_transformer import IXTransformer
        
        if self._transformer is None:
            self._transformer = IXTransformer(self.config)
        
        return self._transformer.transform_to_xbrl(
            ix_elements,
            contexts,
            units,
            footnotes,
            nsmap,
            result
        )
    
    def _is_fact_element(self, element) -> bool:
        """Check if element is an iXBRL fact."""
        if not hasattr(element, 'tag'):
            return False
        
        tag = element.tag
        fact_tags = ['nonFraction', 'nonNumeric', 'fraction']
        
        return any(ft in tag for ft in fact_tags)
    
    def _is_hidden(self, element) -> bool:
        """Check if element is hidden."""
        if not hasattr(element, 'tag'):
            return False
        
        return 'hidden' in element.tag.lower()
    
    def is_ixbrl_document(self, file_path: Path) -> bool:
        """
        Check if file is an iXBRL document.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file contains iXBRL markers
            
        Example:
            if parser.is_ixbrl_document(Path("filing.html")):
                result = parser.parse_ixbrl(Path("filing.html"))
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(8192)  # Read first 8KB
            
            # Check for iXBRL namespace declarations
            ixbrl_markers = [
                'xmlns:ix=',
                IX_NS_2013,
                IX_NS_2011,
                'ix:header',
                'ix:hidden',
                'ix:nonFraction',
                'ix:nonNumeric'
            ]
            
            return any(marker in content for marker in ixbrl_markers)
            
        except Exception as e:
            self.logger.error(f"Failed to check if file is iXBRL: {e}")
            return False


__all__ = ['IXBRLParser', 'IXBRLParseResult']
