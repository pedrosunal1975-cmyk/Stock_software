# Path: xbrl_parser/instance/fact_extractor.py
"""
Fact Extractor

Extracts facts from XBRL instance documents.

This module handles:
- Fact element identification
- Numeric fact extraction
- Text fact extraction
- Nil fact handling
- Context and unit reference resolution
- Dimension extraction
- Footnote reference handling

Example:
    from ..instance import FactExtractor
    
    extractor = FactExtractor()
    facts = extractor.extract_facts(root, result)
    
    for fact in facts:
        print(f"{fact.concept}: {fact.value} ({fact.fact_type})")
"""

import logging
from typing import Optional
from decimal import Decimal, InvalidOperation
from lxml import etree

from ...core.config_loader import ConfigLoader
from ..models.fact import Fact, FactType, FactReliability
from ..models.error import ParsingError, ErrorCategory
from ..instance.constants import (
    XBRLI_NS,
    XBRLDI_NS,
    XSI_NS,
    LINK_NS,
    XSD_NS,
    SKIP_NAMESPACES,
    XML_NS
)


class FactExtractor:
    """
    Extracts facts from XBRL instance documents.
    
    Identifies and parses fact elements, resolving contexts and units.
    
    Example:
        extractor = FactExtractor()
        facts = extractor.extract_facts(root, result)
        
        # Filter facts
        monetary_facts = [f for f in facts if f.fact_type == FactType.NUMERIC]
        print(f"Found {len(monetary_facts)} numeric facts")
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize fact extractor.
        
        Args:
            config: Configuration loader
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger(__name__)
        self.logger.debug("FactExtractor initialized")
    
    def extract_facts(self, root: etree._Element, result) -> list[Fact]:
        """
        Extract all facts from instance document.
        
        Args:
            root: Instance document root element
            result: InstanceParseResult with contexts and units
            
        Returns:
            list of extracted Fact objects
            
        Example:
            facts = extractor.extract_facts(root, result)
            print(f"Extracted {len(facts)} facts")
        """
        facts = []
        fact_count = 0
        
        # Get all child elements of root (potential facts)
        for elem in root:
            # Skip non-element items (comments, processing instructions)
            if not isinstance(elem.tag, str):
                continue
            
            # Skip known XBRL structure elements
            if self._is_structure_element(elem):
                continue
            
            try:
                fact = self._extract_fact(elem, result)
                if fact:
                    facts.append(fact)
                    fact_count += 1
                    
            except Exception as e:
                self.logger.error(f"Failed to extract fact from element {elem.tag}: {e}")
                result.errors.append(ParsingError(
                    category=ErrorCategory.INVALID_FACT,
                    message=f"Failed to extract fact: {e}",
                    severity="WARNING"
                ))
        
        self.logger.info(f"Extracted {fact_count} facts from instance")
        return facts
    
    def _is_structure_element(self, elem: etree._Element) -> bool:
        """
        Check if element is XBRL structure (not a fact).
        
        Args:
            elem: XML element
            
        Returns:
            True if element is structure, False if potential fact
        """
        # Safely get tag
        tag = getattr(elem, 'tag', None)
        if not tag or not isinstance(tag, str):
            return True
        
        # Get namespace
        if tag.startswith('{'):
            ns = tag[1:tag.index('}')]
        else:
            return True
        
        # Check for XBRL structure namespaces
        structure_namespaces = [
            XBRLI_NS,
            LINK_NS,
            XSD_NS
        ]
        
        return ns in structure_namespaces
    
    def _extract_fact(self, elem: etree._Element, result) -> Optional[Fact]:
        """
        Extract a single fact from element.
        
        Args:
            elem: Fact XML element
            result: InstanceParseResult with contexts and units
            
        Returns:
            Extracted Fact object or None if not a valid fact
        """
        # Get concept (element tag name)
        concept = self._get_qname(elem)
        
        # Get context reference
        context_ref = elem.get('contextRef')
        if not context_ref:
            self.logger.warning(f"Fact {concept} missing contextRef")
            return None
        
        # Verify context exists
        if context_ref not in result.contexts:
            self.logger.warning(f"Fact {concept} references unknown context {context_ref}")
            return None
        
        # Get unit reference (optional)
        unit_ref = elem.get('unitRef')
        
        # Verify unit exists if specified
        if unit_ref and unit_ref not in result.units:
            self.logger.warning(f"Fact {concept} references unknown unit {unit_ref}")
        
        # Check for nil value
        nil_attr = elem.get(f'{{{XSI_NS}}}nil')
        is_nil = nil_attr == 'true'
        
        # Get decimals/precision
        decimals = elem.get('decimals')
        precision = elem.get('precision')
        
        # Get fact ID
        fact_id = elem.get('id')
        
        # Get language (xml:lang attribute)
        language = elem.get(f'{{{XML_NS}}}lang')
        
        # Determine fact type and extract value
        fact_type, value = self._extract_value(elem, is_nil)
        
        # Extract footnote references
        footnote_refs = self._extract_footnote_refs(elem)
        
        # Get source location
        source_file = result.instance_path if hasattr(result, 'instance_path') else None
        source_line = elem.sourceline if hasattr(elem, 'sourceline') else None
        
        # Create fact with ALL attributes
        fact = Fact(
            concept=concept,
            value=value,
            fact_type=fact_type,
            context_ref=context_ref,
            unit_ref=unit_ref,
            decimals=decimals,
            precision=precision,
            is_nil=is_nil,
            id=fact_id,
            language=language,
            footnote_refs=footnote_refs,
            source_file=source_file,
            source_line=source_line,
            source_element=elem.tag,
            reliability=FactReliability.HIGH
        )
        
        return fact
    
    def _extract_footnote_refs(self, elem: etree._Element) -> list[str]:
        """
        Extract footnote references from fact element.
        
        Note: In XBRL, footnotes are linked through xlink:label attributes
        in the footnoteLink section, not directly on facts. This method
        prepares for linking by checking if the fact has an ID.
        
        The actual linking happens in instance_parser._link_footnotes_to_facts().
        
        Args:
            elem: Fact element
            
        Returns:
            Empty list (footnotes are linked separately)
        """
        # Footnotes are linked through separate footnoteLink elements
        # This will be populated later during the linking phase
        return []
    
    def _get_qname(self, elem: etree._Element) -> str:
        """
        Get qualified name from element tag.
        
        Args:
            elem: XML element
            
        Returns:
            Qualified name (prefix:localname)
        """
        tag = elem.tag
        
        # Handle namespaced tags
        if tag.startswith('{'):
            ns_end = tag.index('}')
            namespace = tag[1:ns_end]
            local_name = tag[ns_end+1:]
            
            # Try to find prefix for namespace
            nsmap = elem.nsmap
            prefix = None
            for p, ns in nsmap.items():
                if ns == namespace:
                    prefix = p
                    break
            
            if prefix:
                return f"{prefix}:{local_name}"
            else:
                return local_name
        
        return tag
    
    def _extract_value(self, elem: etree._Element, is_nil: bool) -> tuple:
        """
        Extract value and determine fact type.
        
        Args:
            elem: Fact element
            is_nil: Whether fact is nil
            
        Returns:
            tuple of (fact_type, value)
        """
        if is_nil:
            return FactType.TEXT, None
        
        # Get text content
        text_content = elem.text
        
        if text_content is None:
            # Check for child elements (text blocks or tuples)
            if len(elem) > 0:
                # Has children - could be text block or tuple
                inner_xml = etree.tostring(elem, encoding='unicode', method='html')
                return FactType.TEXT_BLOCK, inner_xml
            else:
                return FactType.TEXT, ""
        
        # Try to parse as numeric
        value_str = text_content.strip()
        
        if self._is_numeric(value_str):
            try:
                numeric_value = Decimal(value_str)
                return FactType.NUMERIC, str(numeric_value)
            except (InvalidOperation, ValueError):
                pass
        
        # Check for boolean
        if value_str.lower() in ('true', 'false', '1', '0'):
            return FactType.BOOLEAN, value_str.lower() in ('true', '1')
        
        # Check for date patterns
        if self._looks_like_date(value_str):
            return FactType.DATE, value_str
        
        # Default to text
        return FactType.TEXT, value_str
    
    def _is_numeric(self, value: str) -> bool:
        """
        Check if value string is numeric.
        
        Args:
            value: String value
            
        Returns:
            True if numeric, False otherwise
        """
        # Remove common numeric formatting
        cleaned = value.replace(',', '').replace('_', '')
        
        # Check for numeric patterns
        try:
            float(cleaned)
            return True
        except ValueError:
            return False
    
    def _looks_like_date(self, value: str) -> bool:
        """
        Check if value looks like a date.
        
        Args:
            value: String value
            
        Returns:
            True if looks like date, False otherwise
        """
        # Simple heuristic: contains dashes and digits
        if '-' in value and any(c.isdigit() for c in value):
            # Check for YYYY-MM-DD pattern
            parts = value.split('-')
            if len(parts) == 3:
                return all(p.isdigit() for p in parts)
        
        return False


__all__ = ['FactExtractor']
