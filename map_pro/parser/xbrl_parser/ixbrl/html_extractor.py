# Path: xbrl_parser/ixbrl/html_extractor.py
"""
HTML Extractor for iXBRL

Extracts iXBRL elements from HTML/XHTML documents.

This module handles:
- HTML/XHTML parsing
- ix: namespace element extraction
- XBRL contexts and units extraction from ix:resources/ix:header
- Schema reference extraction
- Hidden section discovery
- Continuation resolution
- Reference linking
- Footnote extraction

Example:
    from ..ixbrl import HTMLExtractor
    
    extractor = HTMLExtractor()
    ix_elements = extractor.extract_ix_elements(Path("filing.html"), result)
    contexts = extractor.extract_contexts(tree)
    units = extractor.extract_units(tree)
"""

import logging
from typing import Optional
from pathlib import Path
from lxml import etree, html

from ...core.config_loader import ConfigLoader
from ..models.error import ParsingError, ErrorCategory, ErrorSeverity
from ..ixbrl.constants import (
    IX_NS_2013,
    IX_NS_2011,
    XBRLI_NS,
    LINK_NS,
    XLINK_NS,
    IX_RESOURCES,
    IX_HEADER,
    IX_REFERENCES,
    XBRL_CONTEXT,
    XBRL_UNIT,
    XBRL_SCHEMA_REF,
    IX_FOOTNOTE
)


class HTMLExtractor:
    """
    Extracts iXBRL elements from HTML documents.
    
    Parses HTML/XHTML and extracts all ix: namespace elements.
    
    Example:
        extractor = HTMLExtractor()
        ix_elements = extractor.extract_ix_elements(Path("filing.html"), result)
        
        print(f"Found {len(ix_elements)} iXBRL elements")
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize HTML extractor.
        
        Args:
            config: Configuration loader
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger(__name__)
        self.logger.debug("HTMLExtractor initialized")
    
    def extract_ix_elements(self, file_path: Path, result) -> list[etree._Element]:
        """
        Extract all iXBRL elements from HTML document.
        
        Args:
            file_path: Path to HTML/XHTML file
            result: Parse result for error tracking
            
        Returns:
            list of ix: namespace elements
            
        Example:
            ix_elements = extractor.extract_ix_elements(Path("filing.html"), result)
        """
        self.logger.info(f"Extracting iXBRL elements from: {file_path}")
        
        try:
            # Parse HTML document
            tree = self._parse_html(file_path)
            
            # Extract ix: elements
            ix_elements = self._find_ix_elements(tree)
            
            # Process continuations
            ix_elements = self._resolve_continuations(ix_elements)
            
            # Process hidden sections
            ix_elements.extend(self._extract_hidden_elements(tree))
            
            self.logger.info(f"Extracted {len(ix_elements)} iXBRL elements")
            return ix_elements
            
        except Exception as e:
            self.logger.error(f"Failed to extract iXBRL elements: {e}", exc_info=True)
            result.errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                message=f"Failed to extract iXBRL elements: {e}",
                severity=ErrorSeverity.ERROR,
                source_file=str(file_path)
            ))
            return []
    
    def _parse_html(self, file_path: Path) -> etree._Element:
        """
        Parse HTML/XHTML file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Parsed HTML tree
        """
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Try XHTML parser first (stricter, preserves namespaces)
        try:
            tree = etree.fromstring(content)
            self.logger.debug("Parsed as XHTML")
            return tree
        except etree.XMLSyntaxError:
            pass
        
        # Fall back to HTML parser
        tree = html.fromstring(content)
        self.logger.debug("Parsed as HTML")
        return tree
    
    def extract_namespace_map(self, tree: etree._Element) -> dict[str, str]:
        """
        Extract namespace map from HTML root element.
        
        In iXBRL files, namespaces are declared at the root with xmlns attributes.
        Since HTML parser may not preserve these in nsmap, we extract them manually.
        
        Args:
            tree: Parsed HTML tree
            
        Returns:
            Dictionary mapping prefix to namespace URI
        """
        nsmap = {}
        
        # First, try to get from element's nsmap if available
        if hasattr(tree, 'nsmap') and tree.nsmap:
            nsmap.update(tree.nsmap)
        
        # Also extract from xmlns attributes (for HTML-parsed documents)
        for key, value in tree.attrib.items():
            if key == 'xmlns':
                # Default namespace
                nsmap[None] = value
            elif key.startswith('xmlns:'):
                # Prefixed namespace
                prefix = key[6:]  # Remove 'xmlns:' prefix
                nsmap[prefix] = value
        
        self.logger.debug(f"Extracted namespace map with {len(nsmap)} prefixes")
        return nsmap
    
    def _find_ix_elements(self, tree: etree._Element) -> list[etree._Element]:
        """
        Find all ix: namespace elements in tree.
        
        Args:
            tree: Parsed HTML tree
            
        Returns:
            list of ix: elements
        """
        ix_elements = []
        
        # Search for both 2013 and 2011 namespaces
        for ns in [IX_NS_2013, IX_NS_2011]:
            # Find all elements in this namespace
            for elem in tree.iter():
                if isinstance(elem.tag, str) and elem.tag.startswith('{' + ns):
                    ix_elements.append(elem)
        
        # Also search by prefix if namespaces not found
        if not ix_elements:
            for elem in tree.iter():
                if isinstance(elem.tag, str) and elem.tag.startswith('ix:'):
                    ix_elements.append(elem)
        
        return ix_elements
    
    def _resolve_continuations(self, elements: list[etree._Element]) -> list[etree._Element]:
        """
        Resolve continuation references in iXBRL.
        
        Some iXBRL elements reference content elsewhere via continuedAt.
        
        Args:
            elements: list of ix: elements
            
        Returns:
            Elements with continuations resolved
        """
        # Build continuation map
        continuation_map = {}
        
        for elem in elements:
            # Check for ix:continuation
            if 'continuation' in elem.tag.lower():
                cont_id = elem.get('id')
                if cont_id:
                    continuation_map[cont_id] = elem
        
        # Resolve continuedAt references
        resolved = []
        for elem in elements:
            continued_at = elem.get('continuedAt')
            
            if continued_at and continued_at in continuation_map:
                # Merge with continuation content
                cont_elem = continuation_map[continued_at]
                merged = self._merge_elements(elem, cont_elem)
                resolved.append(merged)
            else:
                resolved.append(elem)
        
        return resolved
    
    def _merge_elements(
        self,
        primary: etree._Element,
        continuation: etree._Element
    ) -> etree._Element:
        """
        Merge primary element with its continuation.
        
        Args:
            primary: Primary element
            continuation: Continuation element
            
        Returns:
            Merged element
        """
        # Create copy of primary
        merged = etree.Element(primary.tag, attrib=primary.attrib)
        
        # Combine text content
        text_parts = []
        
        if primary.text:
            text_parts.append(primary.text)
        
        if continuation.text:
            text_parts.append(continuation.text)
        
        merged.text = ' '.join(text_parts)
        
        # Copy children from both
        for child in list(primary) + list(continuation):
            merged.append(child)
        
        return merged
    
    def _extract_hidden_elements(self, tree: etree._Element) -> list[etree._Element]:
        """
        Extract elements from ix:hidden sections.
        
        Args:
            tree: Parsed HTML tree
            
        Returns:
            list of hidden ix: elements
        """
        hidden_elements = []
        
        # Find ix:hidden sections
        for ns in [IX_NS_2013, IX_NS_2011]:
            hidden_sections = tree.findall(f".//{{{ns}}}hidden")
            
            for section in hidden_sections:
                # Extract all ix: elements from hidden section
                for elem in section.iter():
                    if elem.tag.startswith('{' + ns):
                        hidden_elements.append(elem)
        
        return hidden_elements
    
    def get_element_text(self, element: etree._Element) -> str:
        """
        Get complete text content from element.
        
        Includes text from element and all descendants.
        
        Args:
            element: HTML element
            
        Returns:
            Complete text content
        """
        return element.text_content() if hasattr(element, 'text_content') else (element.text or '')
    
    def extract_contexts(self, tree: etree._Element) -> list[etree._Element]:
        """
        Extract XBRL context elements from iXBRL HTML.
        
        In iXBRL files, contexts are embedded in:
        - <ix:resources> sections (most common)
        - <ix:header> sections
        - Sometimes directly in <head> or <body>
        
        Args:
            tree: Parsed HTML tree
            
        Returns:
            list of xbrli:context XML elements
            
        Example:
            contexts = extractor.extract_contexts(tree)
            print(f"Found {len(contexts)} contexts")
        """
        contexts = []
        
        # Search in ix:resources sections
        for ns in [IX_NS_2013, IX_NS_2011]:
            resources_sections = tree.findall(f".//{{{ns}}}{IX_RESOURCES}")
            for section in resources_sections:
                # Find all xbrli:context elements
                ctx_elements = section.findall(f".//{{{XBRLI_NS}}}{XBRL_CONTEXT}")
                contexts.extend(ctx_elements)
        
        # Search in ix:header sections
        for ns in [IX_NS_2013, IX_NS_2011]:
            header_sections = tree.findall(f".//{{{ns}}}{IX_HEADER}")
            for section in header_sections:
                ctx_elements = section.findall(f".//{{{XBRLI_NS}}}{XBRL_CONTEXT}")
                contexts.extend(ctx_elements)
        
        # Fallback: search entire document for xbrli:context
        if not contexts:
            contexts = tree.findall(f".//{{{XBRLI_NS}}}{XBRL_CONTEXT}")
        
        self.logger.debug(f"Extracted {len(contexts)} contexts from iXBRL HTML")
        return contexts
    
    def extract_units(self, tree: etree._Element) -> list[etree._Element]:
        """
        Extract XBRL unit elements from iXBRL HTML.
        
        In iXBRL files, units are embedded in:
        - <ix:resources> sections (most common)
        - <ix:header> sections
        - Sometimes directly in <head> or <body>
        
        Args:
            tree: Parsed HTML tree
            
        Returns:
            list of xbrli:unit XML elements
            
        Example:
            units = extractor.extract_units(tree)
            print(f"Found {len(units)} units")
        """
        units = []
        
        # Search in ix:resources sections
        for ns in [IX_NS_2013, IX_NS_2011]:
            resources_sections = tree.findall(f".//{{{ns}}}{IX_RESOURCES}")
            for section in resources_sections:
                unit_elements = section.findall(f".//{{{XBRLI_NS}}}{XBRL_UNIT}")
                units.extend(unit_elements)
        
        # Search in ix:header sections
        for ns in [IX_NS_2013, IX_NS_2011]:
            header_sections = tree.findall(f".//{{{ns}}}{IX_HEADER}")
            for section in header_sections:
                unit_elements = section.findall(f".//{{{XBRLI_NS}}}{XBRL_UNIT}")
                units.extend(unit_elements)
        
        # Fallback: search entire document
        if not units:
            units = tree.findall(f".//{{{XBRLI_NS}}}{XBRL_UNIT}")
        
        self.logger.debug(f"Extracted {len(units)} units from iXBRL HTML")
        return units
    
    def extract_schema_refs(self, tree: etree._Element) -> list[str]:
        """
        Extract schema references from iXBRL HTML.
        
        Schema references are typically in:
        - <ix:references> sections
        - <link:schemaRef> elements in <head>
        
        Args:
            tree: Parsed HTML tree
            
        Returns:
            list of schema reference URIs
            
        Example:
            schema_refs = extractor.extract_schema_refs(tree)
            for ref in schema_refs:
                print(f"Schema: {ref}")
        """
        schema_refs = []
        
        # Search in ix:references sections
        for ns in [IX_NS_2013, IX_NS_2011]:
            references_sections = tree.findall(f".//{{{ns}}}{IX_REFERENCES}")
            for section in references_sections:
                schema_elements = section.findall(f".//{{{LINK_NS}}}{XBRL_SCHEMA_REF}")
                for elem in schema_elements:
                    href = elem.get(f'{{{XLINK_NS}}}href')
                    if href:
                        schema_refs.append(href)
        
        # Fallback: search for link:schemaRef anywhere
        if not schema_refs:
            schema_elements = tree.findall(f".//{{{LINK_NS}}}{XBRL_SCHEMA_REF}")
            for elem in schema_elements:
                href = elem.get(f'{{{XLINK_NS}}}href')
                if href:
                    schema_refs.append(href)
        
        self.logger.debug(f"Extracted {len(schema_refs)} schema references from iXBRL HTML")
        return schema_refs
    
    def extract_footnotes(self, tree: etree._Element) -> list[etree._Element]:
        """
        Extract ix:footnote elements from iXBRL HTML.
        
        iXBRL footnotes use <ix:footnote> elements with:
        - id attribute for linking
        - footnoteID attribute
        - Content as inner HTML/text
        
        Args:
            tree: Parsed HTML tree
            
        Returns:
            list of ix:footnote elements
            
        Example:
            footnotes = extractor.extract_footnotes(tree)
            for fn in footnotes:
                fn_id = fn.get('id')
                print(f"Footnote {fn_id}: {fn.text}")
        """
        footnotes = []
        
        # Search for ix:footnote elements by namespace
        for ns in [IX_NS_2013, IX_NS_2011]:
            fn_elements = tree.findall(f".//{{{ns}}}footnote")
            footnotes.extend(fn_elements)
        
        # If HTML parser was used, namespaces may be lost
        # Search by tag name pattern instead
        if not footnotes:
            # Count all elements with 'footnote' in tag name for diagnostics
            all_footnote_tags = []
            for elem in tree.iter():
                if isinstance(elem.tag, str):
                    if 'footnote' in elem.tag.lower():
                        all_footnote_tags.append(elem.tag)
                        # Check if tag ends with 'footnote' (handles both 'ix:footnote' and '{ns}footnote')
                        if elem.tag.endswith('footnote') or ':footnote' in elem.tag:
                            footnotes.append(elem)
            
            if all_footnote_tags:
                self.logger.debug(f"Found {len(all_footnote_tags)} elements with 'footnote' in tag: {set(all_footnote_tags)}")
        
        # Also check for footnoteRefs on facts to see if footnotes are referenced but not extracted
        fact_footnote_refs = []
        for elem in tree.iter():
            if isinstance(elem.tag, str):
                footnote_refs = elem.get('footnoteRefs') or elem.get('footnotRefs')
                if footnote_refs:
                    fact_footnote_refs.append(footnote_refs)
        
        if fact_footnote_refs:
            self.logger.info(f"Found {len(fact_footnote_refs)} facts with footnoteRefs, but extracted {len(footnotes)} footnote elements")
            self.logger.debug(f"Sample footnoteRefs: {fact_footnote_refs[:5]}")
        
        self.logger.debug(f"Extracted {len(footnotes)} footnotes from iXBRL HTML")
        return footnotes


__all__ = ['HTMLExtractor']
