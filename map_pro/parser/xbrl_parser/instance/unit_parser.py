# Path: xbrl_parser/instance/unit_parser.py
"""
Unit Parser

Extracts and parses unit elements from XBRL instance documents.

This module handles:
- Unit element extraction
- Measure parsing
- Divide operations (numerator/denominator)
- ISO 4217 currency code handling
- Custom unit definitions

Example:
    from ..instance import UnitParser
    
    parser = UnitParser()
    units = parser.parse_units(root, result)
    
    for unit_id, unit in units.items():
        print(f"{unit_id}: {unit.measures}")
"""

import logging
from typing import Optional
from lxml import etree

from ...core.config_loader import ConfigLoader
from ..models.unit import Unit, UnitType
from ..models.error import ParsingError, ErrorCategory
from ..instance.constants import (
    XBRLI_NS,
    ISO4217_NS
)


class UnitParser:
    """
    Parses unit elements from XBRL instances.
    
    Extracts measure and divide information from unit definitions.
    
    Example:
        parser = UnitParser()
        units = parser.parse_units(root, result)
        
        # Access specific unit
        usd_unit = units['usd']
        print(f"Measures: {usd_unit.measures}")
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize unit parser.
        
        Args:
            config: Configuration loader
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger(__name__)
        self.logger.debug("UnitParser initialized")
    
    def parse_units(self, root: etree._Element, result) -> dict[str, Unit]:
        """
        Parse all unit elements from instance.
        
        Args:
            root: Instance document root element
            result: InstanceParseResult for error tracking
            
        Returns:
            Dictionary mapping unit IDs to Unit objects
            
        Example:
            units = parser.parse_units(root, result)
            print(f"Found {len(units)} units")
        """
        units = {}
        
        # Find all unit elements
        unit_elements = root.findall(f".//{{{XBRLI_NS}}}unit")
        
        self.logger.info(f"Found {len(unit_elements)} unit elements")
        
        for unit_elem in unit_elements:
            try:
                unit_id = unit_elem.get('id')
                if not unit_id:
                    self.logger.warning("Unit element missing 'id' attribute")
                    continue
                
                # Parse unit
                unit = self._parse_unit_element(unit_elem, result)
                if unit:
                    units[unit_id] = unit
                    
            except Exception as e:
                self.logger.error(f"Failed to parse unit: {e}", exc_info=True)
                result.errors.append(ParsingError(
                    category=ErrorCategory.MISSING_UNIT,
                    message=f"Failed to parse unit: {e}",
                    severity="ERROR"
                ))
        
        self.logger.info(f"Successfully parsed {len(units)} units")
        return units
    
    def _parse_unit_element(self, unit_elem: etree._Element, result) -> Optional[Unit]:
        """
        Parse a single unit element.
        
        Args:
            unit_elem: Unit XML element
            result: InstanceParseResult for error tracking
            
        Returns:
            Parsed Unit object or None if parsing failed
        """
        unit_id = unit_elem.get('id')
        
        # Check for divide element (ratio units)
        divide_elem = unit_elem.find(f"{{{XBRLI_NS}}}divide")
        if divide_elem is not None:
            return self._parse_divide_unit(unit_id, divide_elem, result)
        
        # Parse simple measure unit
        measure_elems = unit_elem.findall(f"{{{XBRLI_NS}}}measure")
        if not measure_elems:
            self.logger.warning(f"Unit {unit_id} has no measures")
            return None
        
        # Extract measures
        measures = []
        for measure_elem in measure_elems:
            if measure_elem.text:
                measures.append(measure_elem.text.strip())
        
        if not measures:
            self.logger.warning(f"Unit {unit_id} has empty measures")
            return None
        
        return Unit(
            id=unit_id,
            unit_type=UnitType.SIMPLE,
            measures=measures
        )
    
    def _parse_divide_unit(
        self,
        unit_id: str,
        divide_elem: etree._Element,
        result
    ) -> Optional[Unit]:
        """
        Parse a divide (ratio) unit.
        
        Args:
            unit_id: Unit identifier
            divide_elem: Divide XML element
            result: InstanceParseResult for error tracking
            
        Returns:
            Parsed Unit object or None if parsing failed
        """
        # Parse numerator
        numerator_elem = divide_elem.find(f"{{{XBRLI_NS}}}unitNumerator")
        if numerator_elem is None:
            self.logger.error(f"Divide unit {unit_id} missing numerator")
            return None
        
        numerator_measures = []
        for measure in numerator_elem.findall(f"{{{XBRLI_NS}}}measure"):
            if measure.text:
                numerator_measures.append(measure.text.strip())
        
        # Parse denominator
        denominator_elem = divide_elem.find(f"{{{XBRLI_NS}}}unitDenominator")
        if denominator_elem is None:
            self.logger.error(f"Divide unit {unit_id} missing denominator")
            return None
        
        denominator_measures = []
        for measure in denominator_elem.findall(f"{{{XBRLI_NS}}}measure"):
            if measure.text:
                denominator_measures.append(measure.text.strip())
        
        if not numerator_measures or not denominator_measures:
            self.logger.error(f"Divide unit {unit_id} has empty numerator or denominator")
            return None
        
        return Unit(
            id=unit_id,
            unit_type=UnitType.COMPLEX,
            numerator=numerator_measures,
            denominator=denominator_measures
        )
    

__all__ = ['UnitParser']
