# Path: xbrl_parser/instance/context_parser.py
"""
Context Parser

Extracts and parses context elements from XBRL instance documents.

This module handles:
- Context element extraction
- Entity identifier parsing
- Period parsing (instant, duration, forever)
- Explicit dimension parsing
- Typed dimension parsing
- Scenario and segment parsing

Example:
    from ..instance import ContextParser
    
    parser = ContextParser()
    contexts = parser.parse_contexts(root, result)
    
    for context_id, context in contexts.items():
        print(f"{context_id}: {context.entity.value} @ {context.period}")
"""

import logging
from typing import Optional
from datetime import datetime, date
from lxml import etree

from ...core.config_loader import ConfigLoader
from ..models.context import (
    Context,
    EntityIdentifier,
    Period,
    PeriodType,
    ExplicitDimension,
    TypedDimension
)
from ..models.error import ParsingError, ErrorCategory
from ..instance.constants import (
    XBRLI_NS,
    XBRLDI_NS
)


class ContextParser:
    """
    Parses context elements from XBRL instances.
    
    Extracts entity, period, and dimensional information from contexts.
    
    Example:
        parser = ContextParser()
        contexts = parser.parse_contexts(root, result)
        
        # Access specific context
        ctx = contexts['c20231231']
        print(f"Entity: {ctx.entity.value}")
        print(f"Period: {ctx.period.instant}")
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize context parser.
        
        Args:
            config: Configuration loader
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger(__name__)
        self.logger.debug("ContextParser initialized")
    
    def parse_contexts(self, root: etree._Element, result) -> dict[str, Context]:
        """
        Parse all context elements from instance.
        
        Args:
            root: Instance document root element
            result: InstanceParseResult for error tracking
            
        Returns:
            Dictionary mapping context IDs to Context objects
            
        Example:
            contexts = parser.parse_contexts(root, result)
            print(f"Found {len(contexts)} contexts")
        """
        contexts = {}
        
        # Find all context elements
        context_elements = root.findall(f".//{{{XBRLI_NS}}}context")
        
        self.logger.info(f"Found {len(context_elements)} context elements")
        
        for ctx_elem in context_elements:
            try:
                context_id = ctx_elem.get('id')
                if not context_id:
                    self.logger.warning("Context element missing 'id' attribute")
                    continue
                
                # Parse context
                context = self._parse_context_element(ctx_elem, result)
                if context:
                    contexts[context_id] = context
                    
            except Exception as e:
                self.logger.error(f"Failed to parse context: {e}", exc_info=True)
                result.errors.append(ParsingError(
                    category=ErrorCategory.MISSING_CONTEXT,
                    message=f"Failed to parse context: {e}",
                    severity="ERROR"
                ))
        
        self.logger.info(f"Successfully parsed {len(contexts)} contexts")
        return contexts
    
    def _parse_context_element(self, ctx_elem: etree._Element, result) -> Optional[Context]:
        """
        Parse a single context element.
        
        Args:
            ctx_elem: Context XML element
            result: InstanceParseResult for error tracking
            
        Returns:
            Parsed Context object or None if parsing failed
        """
        context_id = ctx_elem.get('id')
        
        # Parse entity
        entity = self._parse_entity(ctx_elem, result)
        if not entity:
            return None
        
        # Parse period
        period = self._parse_period(ctx_elem, result)
        if not period:
            return None
        
        # Parse dimensions (segment and scenario)
        segment, scenario = self._parse_dimensions(ctx_elem, result)
        
        # Create context
        context = Context(
            id=context_id,
            entity=entity,
            period=period,
            segment=segment,
            scenario=scenario
        )
        
        return context
    
    def _parse_entity(self, ctx_elem: etree._Element, result) -> Optional[EntityIdentifier]:
        """
        Parse entity element from context.
        
        Args:
            ctx_elem: Context XML element
            result: InstanceParseResult for error tracking
            
        Returns:
            EntityIdentifier object or None if parsing failed
        """
        # Find entity element
        entity_elem = ctx_elem.find(f".//{{{XBRLI_NS}}}entity")
        if entity_elem is None:
            self.logger.error("Context missing entity element")
            return None
        
        # Find identifier
        identifier_elem = entity_elem.find(f"{{{XBRLI_NS}}}identifier")
        if identifier_elem is None:
            self.logger.error("Entity missing identifier element")
            return None
        
        # Get scheme and value
        scheme = identifier_elem.get('scheme')
        value = identifier_elem.text
        
        if not scheme or not value:
            self.logger.error(f"Invalid entity identifier: scheme={scheme}, value={value}")
            return None
        
        return EntityIdentifier(scheme=scheme, value=value.strip())
    
    def _parse_period(self, ctx_elem: etree._Element, result) -> Optional[Period]:
        """
        Parse period element from context.
        
        Args:
            ctx_elem: Context XML element
            result: InstanceParseResult for error tracking
            
        Returns:
            Period object or None if parsing failed
        """
        # Find period element
        period_elem = ctx_elem.find(f".//{{{XBRLI_NS}}}period")
        if period_elem is None:
            self.logger.error("Context missing period element")
            return None
        
        # Check for instant period
        instant_elem = period_elem.find(f"{{{XBRLI_NS}}}instant")
        if instant_elem is not None:
            instant_date = self._parse_date(instant_elem.text)
            if instant_date:
                return Period(
                    period_type=PeriodType.INSTANT,
                    instant=instant_date
                )
        
        # Check for duration period
        start_elem = period_elem.find(f"{{{XBRLI_NS}}}startDate")
        end_elem = period_elem.find(f"{{{XBRLI_NS}}}endDate")
        
        if start_elem is not None and end_elem is not None:
            start_date = self._parse_date(start_elem.text)
            end_date = self._parse_date(end_elem.text)
            
            if start_date and end_date:
                return Period(
                    period_type=PeriodType.DURATION,
                    start_date=start_date,
                    end_date=end_date
                )
        
        # Check for forever period
        forever_elem = period_elem.find(f"{{{XBRLI_NS}}}forever")
        if forever_elem is not None:
            return Period(period_type=PeriodType.FOREVER)
        
        self.logger.error("Could not determine period type")
        return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """
        Parse date string to date object.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            date object or None if parsing failed
        """
        if not date_str:
            return None
        
        try:
            # Handle datetime strings (strip time component)
            if 'T' in date_str:
                date_str = date_str.split('T')[0]
            
            # Parse date
            return datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
            
        except ValueError as e:
            self.logger.warning(f"Failed to parse date '{date_str}': {e}")
            return None
    
    def _parse_dimensions(self, ctx_elem: etree._Element, result) -> tuple:
        """
        Parse dimensional information from segment and scenario.
        
        Args:
            ctx_elem: Context XML element
            result: InstanceParseResult for error tracking
            
        Returns:
            tuple of (Segment object or None, Scenario object or None)
        """
        from ..models.context import Segment, Scenario
        
        segment = None
        scenario = None
        
        # Parse segment dimensions
        entity_elem = ctx_elem.find(f".//{{{XBRLI_NS}}}entity")
        if entity_elem is not None:
            segment_elem = entity_elem.find(f"{{{XBRLI_NS}}}segment")
            if segment_elem is not None:
                exp, typ = self._parse_dimension_container(segment_elem)
                if exp or typ:
                    segment = Segment(
                        explicit_dimensions=list(exp.values()),
                        typed_dimensions=list(typ.values())
                    )
        
        # Parse scenario dimensions
        scenario_elem = ctx_elem.find(f".//{{{XBRLI_NS}}}scenario")
        if scenario_elem is not None:
            exp, typ = self._parse_dimension_container(scenario_elem)
            if exp or typ:
                scenario = Scenario(
                    explicit_dimensions=list(exp.values()),
                    typed_dimensions=list(typ.values())
                )
        
        return segment, scenario
    
    def _parse_dimension_container(self, container: etree._Element) -> tuple:
        """
        Parse dimensions from segment or scenario container.
        
        Args:
            container: Segment or scenario element
            
        Returns:
            tuple of (explicit_dimensions dict, typed_dimensions dict)
        """
        explicit_dims = {}
        typed_dims = {}
        
        # Parse explicit dimensions
        explicit_members = container.findall(f".//{{{XBRLDI_NS}}}explicitMember")
        for member in explicit_members:
            dimension = member.get('dimension')
            member_value = member.text
            
            if dimension and member_value:
                explicit_dims[dimension] = ExplicitDimension(
                    dimension=dimension,
                    member=member_value.strip()
                )
        
        # Parse typed dimensions
        typed_members = container.findall(f".//{{{XBRLDI_NS}}}typedMember")
        for member in typed_members:
            dimension = member.get('dimension')
            
            if dimension:
                # Extract typed value (serialize inner XML)
                if len(member) > 0:
                    from lxml import etree
                    value_xml = ''.join(
                        etree.tostring(child, encoding='unicode') 
                        for child in member
                    )
                    typed_dims[dimension] = TypedDimension(
                        dimension=dimension,
                        value_xml=value_xml
                    )
        
        return explicit_dims, typed_dims


__all__ = ['ContextParser']
