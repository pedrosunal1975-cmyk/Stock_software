# Path: xbrl_parser/ixbrl/ix_transformer.py
"""
iXBRL to XBRL Transformer

Transforms iXBRL elements to standard XBRL format.

This module handles:
- ix:nonFraction to XBRL fact conversion
- ix:nonNumeric to XBRL fact conversion
- Context generation from ix: attributes
- Unit generation
- XBRL document assembly

Example:
    from ..ixbrl import IXTransformer
    
    transformer = IXTransformer()
    xbrl_xml = transformer.transform_to_xbrl(ix_elements, result)
"""

import logging
from typing import Optional
from lxml import etree
from datetime import datetime

from ...core.config_loader import ConfigLoader
from ..models.error import ParsingError, ErrorCategory, ErrorSeverity
from ..ixbrl.constants import (
    IX_NS,
    XBRLI_NS,
    ISO4217_NS,
    XML_NS,
    LINK_NS,
    XLINK_NS,
    XBRL_DATE_FORMAT
)

# For convenience in fact transformation
IX_TRANSFORMER_XML_NS = XML_NS


class IXTransformer:
    """
    Transforms iXBRL elements to standard XBRL.
    
    Converts ix: namespace elements to standard XBRL XML format.
    Uses real extracted contexts and units from iXBRL HTML.
    
    Example:
        transformer = IXTransformer()
        xbrl_xml = transformer.transform_to_xbrl(
            ix_elements, 
            contexts, 
            units,
            result
        )
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize IX transformer.
        
        Args:
            config: Configuration loader
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger(__name__)
        self.logger.debug("IXTransformer initialized")
        
        # Track contexts and units
        self.contexts_seen: set[str] = set()
        self.units_seen: set[str] = set()
        
        # Namespace map from HTML root
        self.nsmap: dict[str, str] = {}
    
    def transform_to_xbrl(
        self,
        ix_elements: list[etree._Element],
        contexts: list[etree._Element],
        units: list[etree._Element],
        footnotes: list[etree._Element],
        nsmap: dict[str, str],
        result
    ) -> str:
        """
        Transform iXBRL elements to standard XBRL XML.
        
        Uses real extracted contexts, units, footnotes, and namespace map from HTML root.
        NO FAKE DATA - all contexts and units must be real.
        
        Args:
            ix_elements: list of ix: namespace elements
            contexts: list of real xbrli:context elements extracted from HTML
            units: list of real xbrli:unit elements extracted from HTML
            footnotes: list of ix:footnote elements extracted from HTML
            nsmap: Namespace map from HTML root element
            result: Parse result for error tracking
            
        Returns:
            Standard XBRL XML string
            
        Example:
            xbrl_xml = transformer.transform_to_xbrl(
                ix_elements, 
                contexts,
                units,
                footnotes,
                nsmap,
                result
            )
        """
        self.logger.info(f"Transforming {len(ix_elements)} iXBRL elements to XBRL")
        self.logger.info(f"Using {len(contexts)} real contexts and {len(units)} real units")
        
        # Store namespace map for use in transformation
        self.nsmap = nsmap
        
        try:
            # Create XBRL root element
            root = self._create_xbrl_root()
            
            # Add real contexts to XBRL
            for context in contexts:
                root.append(context)
                # Track context IDs
                ctx_id = context.get('id')
                if ctx_id:
                    self.contexts_seen.add(ctx_id)
            
            # Add real units to XBRL
            for unit in units:
                root.append(unit)
                # Track unit IDs
                unit_id = unit.get('id')
                if unit_id:
                    self.units_seen.add(unit_id)
            
            # Transform facts and collect footnote references
            fact_footnote_refs = {}  # fact_id -> [footnote_ids]
            
            for ix_elem in ix_elements:
                fact = self._transform_fact(ix_elem)
                if fact is not None:
                    root.append(fact)
                    
                    # Track footnote references
                    footnote_refs = ix_elem.get('footnoteRefs')
                    if footnote_refs:
                        fact_id = fact.get('id')
                        if fact_id:
                            # footnoteRefs can be space-separated list
                            fact_footnote_refs[fact_id] = footnote_refs.split()
            
            # Transform footnotes to standard XBRL footnoteLink format
            if footnotes:
                footnote_link = self._create_footnote_link(footnotes, fact_footnote_refs)
                if footnote_link is not None:
                    root.append(footnote_link)
                    self.logger.info(f"Added {len(footnotes)} footnotes to XBRL")
            
            # Serialize to XML string
            xbrl_xml = etree.tostring(
                root,
                encoding='unicode',
                pretty_print=True
            )
            
            # Add XML declaration manually
            xbrl_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + xbrl_xml
            
            self.logger.info("Transformation to XBRL complete")
            return xbrl_xml
            
        except Exception as e:
            self.logger.error(f"Failed to transform to XBRL: {e}", exc_info=True)
            result.errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                message=f"Failed to transform to XBRL: {e}",
                severity=ErrorSeverity.ERROR
            ))
            return ""
    
    def _create_xbrl_root(self) -> etree._Element:
            """
            Create XBRL root element with namespaces.
            Returns:
                XBRL root element
            """
            # Use the complete namespace map from HTML
            nsmap = dict(self.nsmap)
            
            # Ensure XBRL instance namespace is present
            if None not in nsmap:
                nsmap[None] = XBRLI_NS
            if 'xbrli' not in nsmap:
                nsmap['xbrli'] = XBRLI_NS
            
            root = etree.Element(
                f'{{{XBRLI_NS}}}xbrl',
                nsmap=nsmap
            )
            
            return root
    
    def _transform_fact(self, ix_elem: etree._Element) -> Optional[etree._Element]:
        """
        Transform ix: fact element to XBRL fact.
        
        Preserves all attributes including ID.
        
        Args:
            ix_elem: ix: fact element
            
        Returns:
            XBRL fact element or None
        """
        tag = ix_elem.tag
        
        # Check if this is a fact element
        if not self._is_fact_element(tag):
            return None
        
        # Get fact name
        name = ix_elem.get('name')
        if not name:
            return None
        
        # Create fact element with proper namespace
        # Extract namespace and local name
        if ':' in name:
            prefix, local_name = name.split(':', 1)
            
            # Use stored namespace map from HTML root
            ns = self.nsmap.get(prefix)
            
            if ns:
                # Create element with proper namespace
                fact = etree.Element(f'{{{ns}}}{local_name}')
            else:
                # Namespace prefix not in map - log warning and use fallback
                self.logger.warning(f"Namespace prefix '{prefix}' not in namespace map, using fallback")
                # Use a generic namespace URI based on the prefix
                ns = f'http://xbrl.org/entity/{prefix}'
                fact = etree.Element(f'{{{ns}}}{local_name}')
        else:
            # No prefix - just create element with local name
            fact = etree.Element(name)
        
        # IMPORTANT: Preserve fact ID attribute
        fact_id = ix_elem.get('id')
        if fact_id:
            fact.set('id', fact_id)
        
        # Add context reference
        context_ref = ix_elem.get('contextRef')
        if context_ref:
            fact.set('contextRef', context_ref)
        
        # Add unit reference (for numeric facts)
        unit_ref = ix_elem.get('unitRef')
        if unit_ref:
            fact.set('unitRef', unit_ref)
        
        # Add decimals/precision
        decimals = ix_elem.get('decimals')
        if decimals:
            fact.set('decimals', decimals)
        
        precision = ix_elem.get('precision')
        if precision:
            fact.set('precision', precision)
        
        # Preserve language attribute
        lang = ix_elem.get(f'{{{IX_TRANSFORMER_XML_NS}}}lang')
        if lang:
            fact.set(f'{{{IX_TRANSFORMER_XML_NS}}}lang', lang)
        
        # set fact value
        fact.text = self._get_fact_value(ix_elem)
        
        return fact
    
    def _is_fact_element(self, tag: str) -> bool:
        """
        Check if element is an iXBRL fact.
        
        Args:
            tag: Element tag
            
        Returns:
            True if fact element
        """
        fact_tags = ['nonFraction', 'nonNumeric', 'fraction']
        return any(ft in tag for ft in fact_tags)
    
    def _get_fact_value(self, ix_elem: etree._Element) -> str:
        """
        Extract fact value from ix: element.
        
        Args:
            ix_elem: ix: element
            
        Returns:
            Fact value string
        """
        # For nonFraction, use format attribute or text
        if 'nonFraction' in ix_elem.tag:
            # Check for format attribute (some iXBRL formats values)
            format_attr = ix_elem.get('format')
            if format_attr:
                # Value might need unformatting
                text = ix_elem.text or ""
                # Remove common formatting
                return text.replace(',', '').replace('$', '').strip()
            
            return ix_elem.text or ""
        
        # For nonNumeric, return text content
        if 'nonNumeric' in ix_elem.tag:
            if hasattr(ix_elem, 'text_content'):
                return ix_elem.text_content()
            return ix_elem.text or ""
        
        return ix_elem.text or ""
    
    def _create_footnote_link(
        self,
        footnotes: list[etree._Element],
        fact_footnote_refs: dict[str, list[str]]
    ) -> Optional[etree._Element]:
        """
        Create standard XBRL footnoteLink from ix:footnote elements.
        
        Transforms iXBRL footnotes to standard XBRL format:
        - ix:footnote → link:footnote
        - Creates link:footnoteArc to link facts to footnotes
        
        Args:
            footnotes: list of ix:footnote elements
            fact_footnote_refs: Mapping of fact IDs to footnote IDs
            
        Returns:
            link:footnoteLink element or None
        """
        if not footnotes:
            return None
        
        try:
            # Create footnoteLink element
            footnote_link = etree.Element(
                f'{{{LINK_NS}}}footnoteLink',
                attrib={
                    f'{{{XLINK_NS}}}type': 'extended',
                    f'{{{XLINK_NS}}}role': 'http://www.xbrl.org/2003/role/link'
                }
            )
            
            # Add footnote elements
            for ix_fn in footnotes:
                # Get footnote ID
                fn_id = ix_fn.get('id')
                if not fn_id:
                    fn_id = ix_fn.get('footnoteID')
                
                if not fn_id:
                    continue
                
                # Create link:footnote element
                footnote = etree.SubElement(
                    footnote_link,
                    f'{{{LINK_NS}}}footnote',
                    attrib={
                        f'{{{XLINK_NS}}}type': 'resource',
                        f'{{{XLINK_NS}}}label': fn_id,
                        f'{{{XLINK_NS}}}role': 'http://www.xbrl.org/2003/role/footnote'
                    }
                )
                
                # Copy footnote text content (including nested elements)
                footnote.text = ''.join(ix_fn.itertext())  # Gets all text including from child elements
                
                # Preserve language if present
                lang = ix_fn.get(f'{{{XML_NS}}}lang')
                if lang:
                    footnote.set(f'{{{XML_NS}}}lang', lang)
            
            # Create locator and footnoteArc elements to link facts to footnotes
            for fact_id, fn_ids in fact_footnote_refs.items():
                # Create locator for the fact (required for proper XBRL structure)
                loc_label = f"loc_{fact_id}"
                loc = etree.SubElement(
                    footnote_link,
                    f'{{{LINK_NS}}}loc',
                    attrib={
                        f'{{{XLINK_NS}}}type': 'locator',
                        f'{{{XLINK_NS}}}href': f"#{fact_id}",
                        f'{{{XLINK_NS}}}label': loc_label
                    }
                )
                
                # Create arc from locator to each footnote
                for fn_id in fn_ids:
                    arc = etree.SubElement(
                        footnote_link,
                        f'{{{LINK_NS}}}footnoteArc',
                        attrib={
                            f'{{{XLINK_NS}}}type': 'arc',
                            f'{{{XLINK_NS}}}arcrole': 'http://www.xbrl.org/2003/arcrole/fact-footnote',
                            f'{{{XLINK_NS}}}from': loc_label,  # Now references locator label
                            f'{{{XLINK_NS}}}to': fn_id          # References footnote label
                        }
                    )
            
            return footnote_link
            
        except Exception as e:
            self.logger.error(f"Failed to create footnoteLink: {e}", exc_info=True)
            return None


__all__ = ['IXTransformer']
