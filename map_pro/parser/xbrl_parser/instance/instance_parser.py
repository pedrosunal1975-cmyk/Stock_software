# Path: xbrl_parser/instance/instance_parser.py
"""
Instance Document Parser

Main orchestrator for parsing XBRL instance documents.

This module coordinates:
- Context parsing
- Unit parsing
- Fact extraction
- Footnote extraction
- Fact-to-footnote linking

Example:
    from ..instance import InstanceParser
    
    parser = InstanceParser()
    result = parser.parse_instance(Path("filing.xml"))
    
    print(f"Extracted {len(result.facts)} facts")
    print(f"Contexts: {len(result.contexts)}")
    print(f"Units: {len(result.units)}")
"""

import logging
from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field
import time

from ...core.config_loader import ConfigLoader
from ..foundation.xml_parser import XMLParser
from ..models.fact import Fact
from ..models.context import Context
from ..models.unit import Unit
from ..models.error import ParsingError, ErrorCategory
from ..instance.constants import (
    LINK_NS,
    XLINK_NS
)


@dataclass
class InstanceParseResult:
    """
    Result of instance document parsing.
    
    Contains all extracted data and statistics.
    """
    # Extracted data
    facts: list[Fact] = field(default_factory=list)
    contexts: dict[str, Context] = field(default_factory=dict)
    units: dict[str, Unit] = field(default_factory=dict)
    footnotes: dict[str, 'Footnote'] = field(default_factory=dict)
    namespaces: dict[str, str] = field(default_factory=dict)
    
    # Metadata
    instance_path: Optional[str] = None
    schema_refs: list[str] = field(default_factory=list)
    
    # Statistics
    parse_time_seconds: float = 0.0
    fact_count: int = 0
    context_count: int = 0
    unit_count: int = 0
    footnote_count: int = 0
    
    # Errors
    errors: list[ParsingError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class InstanceParser:
    """
    Parses XBRL instance documents.
    
    Coordinates context, unit, and fact extraction from instance XML.
    Links footnotes to facts after extraction.
    
    Example:
        config = ConfigLoader()
        parser = InstanceParser(config)
        
        # Parse instance
        result = parser.parse_instance(Path("filing.xml"))
        
        # Access results with full fact attributes
        for fact in result.facts:
            print(f"{fact.concept}: {fact.value}")
            if fact.footnote_refs:
                print(f"  Has {len(fact.footnote_refs)} footnotes")
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize instance parser.
        
        Args:
            config: Configuration loader (creates default if None)
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger(__name__)
        self.xml_parser = XMLParser(self.config)
        
        # Will import parsers lazily to avoid circular imports
        self._context_parser = None
        self._unit_parser = None
        self._fact_extractor = None
        self._footnote_extractor = None
        
        self.logger.info("InstanceParser initialized")
    
    def parse_instance(self, instance_path: Path) -> InstanceParseResult:
        """
        Parse complete XBRL instance document.
        
        This method:
        1. Parses contexts and units
        2. Extracts facts with ALL attributes (id, language, etc.)
        3. Extracts footnotes
        4. Links footnotes to facts bi-directionally
        
        Args:
            instance_path: Path to instance XML file
            
        Returns:
            InstanceParseResult with extracted data and statistics
            
        Example:
            result = parser.parse_instance(Path("filing.xml"))
            print(f"Extracted {result.fact_count} facts")
            
            # Facts now have all attributes including footnotes
            for fact in result.facts:
                if fact.footnote_refs:
                    print(f"{fact.concept} has footnotes: {fact.footnote_refs}")
        """
        self.logger.info(f"Parsing instance document: {instance_path}")
        
        start_time = time.time()
        result = InstanceParseResult()
        result.instance_path = str(instance_path)
        
        try:
            # Check file exists
            if not instance_path.exists():
                raise FileNotFoundError(f"Instance file not found: {instance_path}")
            
            # Parse XML
            xml_result = self.xml_parser.parse_file(instance_path)
            if not xml_result.well_formed:
                result.errors.extend(xml_result.errors)
                return result
            
            root = xml_result.root
            
            # Extract schema references
            result.schema_refs = self._extract_schema_refs(root)
            
            # Extract namespace map from root element
            if hasattr(root, 'nsmap') and root.nsmap:
                result.namespaces = {k if k is not None else 'default': v for k, v in root.nsmap.items()}

            # Parse contexts
            result.contexts = self._parse_contexts(root, result)
            result.context_count = len(result.contexts)
            
            # Parse units
            result.units = self._parse_units(root, result)
            result.unit_count = len(result.units)
            
            # Extract facts (with ALL attributes)
            result.facts = self._extract_facts(root, result)
            result.fact_count = len(result.facts)
            
            # Extract footnotes
            result.footnotes = self._extract_footnotes(root, result)
            result.footnote_count = len(result.footnotes)
            
            # Link footnotes to facts (bi-directional linking)
            # This populates fact.footnote_refs based on footnote.fact_refs
            self._link_footnotes_to_facts(result.facts, result.footnotes)
            
            self.logger.info(
                f"Instance parsed successfully: {result.fact_count} facts, "
                f"{result.context_count} contexts, {result.unit_count} units, "
                f"{result.footnote_count} footnotes"
            )
            
        except Exception as e:
            self.logger.error(f"Instance parsing failed: {e}", exc_info=True)
            result.errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                message=f"Failed to parse instance: {e}",
                severity="ERROR",
                source_file=str(instance_path)
            ))
        
        result.parse_time_seconds = time.time() - start_time
        return result
    
    def _extract_schema_refs(self, root) -> list[str]:
        """
        Extract schema references from instance.
        
        Args:
            root: Instance root element
            
        Returns:
            list of schema reference URIs
        """
        schema_refs = []
        
        # Find schemaRef elements
        schema_ref_elements = root.findall(f".//{{{LINK_NS}}}schemaRef")
        
        for schema_ref in schema_ref_elements:
            # Get xlink:href attribute
            href = schema_ref.get(f"{{{XLINK_NS}}}href")
            if href:
                schema_refs.append(href)
        
        self.logger.debug(f"Found {len(schema_refs)} schema references")
        return schema_refs
    
    def _parse_contexts(self, root, result: InstanceParseResult) -> dict[str, Context]:
        """
        Parse all contexts from instance.
        
        Args:
            root: Instance root element
            result: Parse result for error tracking
            
        Returns:
            Dictionary of context_id -> Context
        """
        from ..instance.context_parser import ContextParser
        
        if self._context_parser is None:
            self._context_parser = ContextParser(self.config)
        
        return self._context_parser.parse_contexts(root, result)
    
    def _parse_units(self, root, result: InstanceParseResult) -> dict[str, Unit]:
        """
        Parse all units from instance.
        
        Args:
            root: Instance root element
            result: Parse result for error tracking
            
        Returns:
            Dictionary of unit_id -> Unit
        """
        from ..instance.unit_parser import UnitParser
        
        if self._unit_parser is None:
            self._unit_parser = UnitParser(self.config)
        
        return self._unit_parser.parse_units(root, result)
    
    def _extract_facts(self, root, result: InstanceParseResult) -> list[Fact]:
        """
        Extract all facts from instance.
        
        Facts are extracted with ALL attributes including:
        - Core: concept, value, context_ref, unit_ref
        - Precision: decimals, precision
        - Metadata: id, language, is_nil
        - Provenance: source_file, source_line, source_element
        
        Args:
            root: Instance root element
            result: Parse result with contexts and units
            
        Returns:
            list of extracted facts with ALL attributes
        """
        from ..instance.fact_extractor import FactExtractor
        
        if self._fact_extractor is None:
            self._fact_extractor = FactExtractor(self.config)
        
        return self._fact_extractor.extract_facts(root, result)
    
    def _extract_footnotes(self, root, result: InstanceParseResult) -> dict:
        """
        Extract footnotes from instance.
        
        FootnoteExtractor extracts footnotes and creates footnote â†’ fact links
        by populating footnote.fact_refs.
        
        Args:
            root: Instance root element
            result: Parse result with facts
            
        Returns:
            Dictionary of footnote_id -> Footnote
        """
        from ..instance.footnote_extractor import FootnoteExtractor
        
        if self._footnote_extractor is None:
            self._footnote_extractor = FootnoteExtractor(self.config)
        
        return self._footnote_extractor.extract_footnotes(root, result)
    
    def _link_footnotes_to_facts(self, facts: list[Fact], footnotes: dict) -> None:
        """
        Link footnotes to facts (bi-directional linking).
        
        FootnoteExtractor already populates footnote.fact_refs (footnote â†’ fact IDs).
        This method creates the reverse link: fact.footnote_refs (fact â†’ footnote IDs).
        
        This is CRITICAL for complete fact extraction - without this, facts have
        empty footnote_refs even when footnotes exist!
        
        Args:
            facts: list of extracted facts
            footnotes: Dictionary of footnote_id -> Footnote objects
        """
        if not footnotes:
            self.logger.info("No footnotes to link")
            return
        
        self.logger.info(f"Linking {len(footnotes)} footnotes to facts")
        
        # Create fact ID to fact mapping for quick lookup
        fact_map = {}
        for fact in facts:
            if fact.id:
                fact_map[fact.id] = fact
        
        self.logger.info(f"Created fact map with {len(fact_map)} facts (facts with IDs)")
        
        # For each footnote, add its ID to all referenced facts
        total_links = 0
        for footnote_id, footnote in footnotes.items():
            self.logger.info(f"Footnote '{footnote_id}' has {len(footnote.fact_refs)} fact references")
            for fact_id in footnote.fact_refs:
                if fact_id in fact_map:
                    fact = fact_map[fact_id]
                    if footnote_id not in fact.footnote_refs:
                        fact.footnote_refs.append(footnote_id)
                        total_links += 1
                else:
                    self.logger.warning(f"Fact ID '{fact_id}' referenced by footnote but not found in fact map")
        
        # Log statistics
        facts_with_footnotes = sum(1 for f in facts if f.footnote_refs)
        self.logger.info(
            f"Linking complete: {total_links} links created, {facts_with_footnotes} facts have footnote references"
        )


__all__ = ['InstanceParser', 'InstanceParseResult']
