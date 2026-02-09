# Path: xbrl_parser/instance/footnote_extractor.py
"""
Footnote Extractor

Extracts and resolves footnotes from XBRL instance documents.

This module handles:
- Footnote link parsing
- Footnote content extraction
- Footnote-to-fact reference resolution
- Multiple language footnotes
- HTML content in footnotes
- Footnote role and arc processing

Example:
    from ..instance import FootnoteExtractor
    
    extractor = FootnoteExtractor()
    footnotes = extractor.extract_footnotes(root, result)
    
    # Get footnotes for a specific fact
    fact_footnotes = extractor.get_fact_footnotes(fact, footnotes)
    for fn in fact_footnotes:
        print(f"Footnote: {fn.content}")
"""

import logging
from typing import Optional
from dataclasses import dataclass, field
from lxml import etree

from ...core.config_loader import ConfigLoader
from ..models.error import ParsingError, ErrorCategory
from ..instance.constants import (
    XBRLI_NS,
    LINK_NS,
    XLINK_NS,
    XML_NS
)


@dataclass
class Footnote:
    """
    XBRL footnote representation.
    
    Attributes:
        footnote_id: Unique footnote identifier
        content: Footnote text content (may include HTML)
        language: Language code (e.g., 'en-US')
        role: Footnote role URI
        is_html: Whether content contains HTML
        fact_refs: set of fact IDs this footnote references
    """
    footnote_id: str
    content: str
    language: Optional[str] = None
    role: Optional[str] = None
    is_html: bool = False
    fact_refs: set[str] = field(default_factory=set)
    
    def get_plain_text(self) -> str:
        """
        Extract plain text from footnote content.
        
        Returns:
            Plain text with HTML tags removed
        """
        if not self.is_html:
            return self.content
        
        # Simple HTML tag removal
        try:
            from lxml.html import fromstring, tostring
            doc = fromstring(self.content)
            return doc.text_content().strip()
        except Exception:
            # Fallback: simple tag stripping
            import re
            return re.sub(r'<[^>]+>', '', self.content).strip()


@dataclass
class FootnoteLink:
    """
    Footnote link connecting facts to footnotes.
    
    Attributes:
        from_label: Source locator label (fact reference)
        to_label: Target locator label (footnote reference)
        role: Link role
        arcrole: Arc role
        order: Display order
    """
    from_label: str
    to_label: str
    role: str
    arcrole: Optional[str] = None
    order: float = 1.0


class FootnoteExtractor:
    """
    Extracts footnotes from XBRL instance documents.
    
    Parses footnoteLink elements and resolves fact-to-footnote relationships.
    
    Example:
        config = ConfigLoader()
        extractor = FootnoteExtractor(config)
        
        # Extract all footnotes
        footnotes = extractor.extract_footnotes(root, result)
        
        # Find footnotes for specific fact
        fact_footnotes = extractor.get_fact_footnotes(fact, footnotes)
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize footnote extractor.
        
        Args:
            config: Configuration loader
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger(__name__)
        
        # Check if footnote extraction is enabled
        self.enabled = self.config.get('enable_footnotes', True)
        
        self.logger.debug(f"FootnoteExtractor initialized (enabled={self.enabled})")
    
    def extract_footnotes(self, root: etree._Element, result) -> dict[str, Footnote]:
        """
        Extract all footnotes from instance document.
        
        Args:
            root: Instance document root element
            result: InstanceParseResult for error tracking
            
        Returns:
            Dictionary mapping footnote IDs to Footnote objects
            
        Example:
            footnotes = extractor.extract_footnotes(root, result)
            print(f"Found {len(footnotes)} footnotes")
        """
        if not self.enabled:
            self.logger.debug("Footnote extraction disabled")
            return {}
        
        footnotes = {}
        
        # Find all footnoteLink elements
        footnote_links = root.findall(f".//{{{LINK_NS}}}footnoteLink")
        
        self.logger.info(f"Found {len(footnote_links)} footnoteLink elements")
        
        for link in footnote_links:
            try:
                # Extract footnotes from this link
                link_footnotes = self._extract_from_link(link, result)
                footnotes.update(link_footnotes)
                
                # Extract and resolve relationships
                self._resolve_footnote_links(link, footnotes, result)
                
            except Exception as e:
                self.logger.error(f"Failed to extract footnotes from link: {e}", exc_info=True)
                result.errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    message=f"Failed to extract footnotes: {e}",
                    severity="WARNING"
                ))
        
        self.logger.info(f"Extracted {len(footnotes)} footnotes")
        return footnotes
    
    def _extract_from_link(
        self,
        link: etree._Element,
        result
    ) -> dict[str, Footnote]:
        """
        Extract footnotes from a footnoteLink element.
        
        Args:
            link: footnoteLink element
            result: InstanceParseResult for error tracking
            
        Returns:
            Dictionary of footnote ID to Footnote
        """
        footnotes = {}
        
        # Find all footnote elements
        footnote_elements = link.findall(f"{{{LINK_NS}}}footnote")
        
        for fn_elem in footnote_elements:
            try:
                footnote = self._parse_footnote_element(fn_elem)
                if footnote:
                    footnotes[footnote.footnote_id] = footnote
                    
            except Exception as e:
                self.logger.error(f"Failed to parse footnote element: {e}")
                result.errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    message=f"Failed to parse footnote: {e}",
                    severity="WARNING"
                ))
        
        return footnotes
    
    def _parse_footnote_element(self, fn_elem: etree._Element) -> Optional[Footnote]:
        """
        Parse a single footnote element.
        
        Args:
            fn_elem: Footnote XML element
            
        Returns:
            Parsed Footnote object or None
        """
        # Get xlink:label (footnote ID)
        footnote_id = fn_elem.get(f'{{{XLINK_NS}}}label')
        if not footnote_id:
            self.logger.warning("Footnote element missing xlink:label")
            return None
        
        # Get xlink:role
        role = fn_elem.get(f'{{{XLINK_NS}}}role')
        
        # Get xml:lang
        language = fn_elem.get(f'{{{XML_NS}}}lang')
        
        # Get content
        content = self._extract_footnote_content(fn_elem)
        
        # Check if content contains HTML
        is_html = self._is_html_content(content)
        
        return Footnote(
            footnote_id=footnote_id,
            content=content,
            language=language,
            role=role,
            is_html=is_html
        )
    
    def _extract_footnote_content(self, fn_elem: etree._Element) -> str:
        """
        Extract content from footnote element.
        
        Args:
            fn_elem: Footnote element
            
        Returns:
            Footnote content (may include HTML)
        """
        # If element has children, serialize inner XML
        if len(fn_elem) > 0:
            content_parts = []
            
            # Add text before first child
            if fn_elem.text:
                content_parts.append(fn_elem.text)
            
            # Add children
            for child in fn_elem:
                child_str = etree.tostring(child, encoding='unicode', method='html')
                content_parts.append(child_str)
                
                # Add tail text
                if child.tail:
                    content_parts.append(child.tail)
            
            return ''.join(content_parts)
        
        # Simple text content
        return fn_elem.text or ""
    
    def _is_html_content(self, content: str) -> bool:
        """
        Check if content contains HTML tags.
        
        Args:
            content: Content string
            
        Returns:
            True if content contains HTML
        """
        return '<' in content and '>' in content
    
    def _resolve_footnote_links(
        self,
        link: etree._Element,
        footnotes: dict[str, Footnote],
        result
    ) -> None:
        """
        Resolve fact-to-footnote relationships from link arcs.
        
        Args:
            link: footnoteLink element
            footnotes: Dictionary of footnotes to update
            result: InstanceParseResult for error tracking
        """
        # Build locator map (label -> fact ID)
        locators = self._extract_locators(link)
        self.logger.info(f"Extracted {len(locators)} locators for footnote linking")
        
        # Find all footnoteArc elements
        arcs = link.findall(f"{{{LINK_NS}}}footnoteArc")
        self.logger.info(f"Found {len(arcs)} footnoteArc elements")
        
        linked_count = 0
        for arc in arcs:
            try:
                # Get arc attributes
                from_label = arc.get(f'{{{XLINK_NS}}}from')
                to_label = arc.get(f'{{{XLINK_NS}}}to')
                
                if not from_label or not to_label:
                    continue
                
                # Resolve fact ID from locator
                fact_id = locators.get(from_label)
                if fact_id:
                    # Add fact reference to footnote
                    if to_label in footnotes:
                        footnotes[to_label].fact_refs.add(fact_id)
                        linked_count += 1
                    else:
                        self.logger.warning(f"Footnote label '{to_label}' not found in extracted footnotes")
                else:
                    self.logger.warning(f"Locator '{from_label}' not found for footnote arc")
                        
            except Exception as e:
                self.logger.error(f"Failed to resolve footnote arc: {e}")
        
        self.logger.info(f"Linked {linked_count} fact-to-footnote relationships")
    
    def _extract_locators(self, link: etree._Element) -> dict[str, str]:
        """
        Extract locators mapping labels to fact IDs.
        
        Args:
            link: footnoteLink element
            
        Returns:
            Dictionary mapping labels to fact IDs
        """
        locators = {}
        
        # Find all loc elements
        loc_elements = link.findall(f"{{{LINK_NS}}}loc")
        
        for loc in loc_elements:
            label = loc.get(f'{{{XLINK_NS}}}label')
            href = loc.get(f'{{{XLINK_NS}}}href')
            
            if label and href:
                # Extract fact ID from href (usually #factID)
                if '#' in href:
                    fact_id = href.split('#')[1]
                    locators[label] = fact_id
        
        return locators
    
    def get_fact_footnotes(
        self,
        fact,
        footnotes: dict[str, Footnote]
    ) -> list[Footnote]:
        """
        Get all footnotes associated with a fact.
        
        Args:
            fact: Fact object with id attribute
            footnotes: Dictionary of all footnotes
            
        Returns:
            list of Footnote objects for this fact
            
        Example:
            fact_footnotes = extractor.get_fact_footnotes(fact, footnotes)
            for fn in fact_footnotes:
                print(fn.content)
        """
        fact_id = getattr(fact, 'id', None) or getattr(fact, 'fact_id', None)
        
        if not fact_id:
            return []
        
        # Find footnotes that reference this fact
        result = []
        for footnote in footnotes.values():
            if fact_id in footnote.fact_refs:
                result.append(footnote)
        
        return result
    
    def get_footnotes_by_language(
        self,
        footnotes: dict[str, Footnote],
        language: str = 'en'
    ) -> dict[str, Footnote]:
        """
        Filter footnotes by language.
        
        Args:
            footnotes: All footnotes
            language: Language code prefix (e.g., 'en' matches 'en-US')
            
        Returns:
            Filtered footnotes dictionary
            
        Example:
            en_footnotes = extractor.get_footnotes_by_language(footnotes, 'en')
        """
        return {
            fn_id: fn
            for fn_id, fn in footnotes.items()
            if fn.language and fn.language.startswith(language)
        }


__all__ = ['FootnoteExtractor', 'Footnote', 'FootnoteLink']
