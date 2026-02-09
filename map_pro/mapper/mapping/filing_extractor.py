# Path: mapping/filing_extractor.py
"""
Filing Characteristics Extractor

Extracts metadata from parsed filings for output organization.
Uses constants.py for market-agnostic key variations.
"""

import logging
from typing import Optional

from ..mapping.constants import (
    PERIOD_END_METADATA_KEYS,
    PERIOD_END_XBRL_CONCEPTS,
    FILING_DATE_METADATA_KEYS,
    FILING_DATE_XBRL_CONCEPTS,
    ENTITY_IDENTIFIER_METADATA_KEYS,
    ENTITY_IDENTIFIER_XBRL_CONCEPTS,
    ENTITY_NAME_METADATA_KEYS,
    ENTITY_NAME_XBRL_CONCEPTS,
    MAX_FACTS_TO_SEARCH,
    DEFAULT_ENTITY_NAME,
)


class FilingCharacteristicsExtractor:
    """
    Extracts filing metadata from ParsedFiling.
    
    Handles:
    - Entity name/identifier
    - Period end date
    - Filing date
    - Filing type
    """
    
    def __init__(self):
        """Initialize extractor."""
        self.logger = logging.getLogger('mapping.filing_extractor')
    
    def extract(self, parsed_filing) -> dict[str, any]:
        """
        Extract all filing characteristics.
        
        Args:
            parsed_filing: ParsedFiling object
            
        Returns:
            Dictionary of filing characteristics
        """
        return {
            'entity_identifier': self._get_entity_identifier(parsed_filing),
            'entity_name': self._get_entity_name(parsed_filing),
            'market': parsed_filing.characteristics.market,
            'filing_type': parsed_filing.characteristics.filing_type,
            'primary_taxonomy': parsed_filing.characteristics.primary_taxonomy,
            'period_end': self._get_period_end(parsed_filing),
            'filing_date': self._get_filing_date(parsed_filing),
        }
    
    def _get_entity_identifier(self, parsed_filing) -> Optional[str]:
        """
        Extract entity identifier (CIK, company number, etc.) - market agnostic.
        
        Searches for various naming conventions defined in constants.py.
        """
        try:
            instance = parsed_filing.raw_data.get('instance', {})
            entity = instance.get('entity', {})
            
            if isinstance(entity, dict):
                for key in ENTITY_IDENTIFIER_METADATA_KEYS:
                    value = entity.get(key)
                    if value:
                        return str(value)
            
            # Try from facts
            for fact in parsed_filing.facts[:MAX_FACTS_TO_SEARCH]:
                fact_name = fact.name if hasattr(fact, 'name') else fact.get('name', '')
                fact_value = fact.value if hasattr(fact, 'value') else fact.get('value')
                
                for concept in ENTITY_IDENTIFIER_XBRL_CONCEPTS:
                    if concept in fact_name:
                        if fact_value:
                            return str(fact_value)
            
            return None
        except Exception as e:
            self.logger.warning(f"Could not extract entity identifier: {e}")
            return None
    
    def _get_entity_name(self, parsed_filing) -> Optional[str]:
        """
        Extract entity name - market agnostic.
        
        Searches for various naming conventions defined in constants.py.
        """
        try:
            instance = parsed_filing.raw_data.get('instance', {})
            entity = instance.get('entity', {})
            
            if isinstance(entity, dict):
                for key in ENTITY_NAME_METADATA_KEYS:
                    value = entity.get(key)
                    if value:
                        return str(value)
            
            # Try from facts
            for fact in parsed_filing.facts[:MAX_FACTS_TO_SEARCH]:
                fact_name = fact.name if hasattr(fact, 'name') else fact.get('name', '')
                fact_value = fact.value if hasattr(fact, 'value') else fact.get('value')
                
                for concept in ENTITY_NAME_XBRL_CONCEPTS:
                    if concept in fact_name:
                        if fact_value:
                            return str(fact_value)
            
            return DEFAULT_ENTITY_NAME
        except Exception as e:
            self.logger.warning(f"Could not extract entity name: {e}")
            return DEFAULT_ENTITY_NAME
    
    def _get_period_end(self, parsed_filing) -> Optional[str]:
        """
        Extract period end date - market agnostic.
        
        Searches for various naming conventions defined in constants.py.
        Returns the full date string as-is from source.
        """
        try:
            # Try from metadata - search multiple keys
            metadata = parsed_filing.raw_data.get('metadata', {})
            
            for key in PERIOD_END_METADATA_KEYS:
                value = metadata.get(key)
                if value:
                    self.logger.info(f"Found period end in metadata['{key}']: {value}")
                    return str(value)
            
            # Try from facts - search for XBRL concepts
            for fact in parsed_filing.facts[:MAX_FACTS_TO_SEARCH]:
                fact_name = fact.name if hasattr(fact, 'name') else fact.get('name', '')
                fact_value = fact.value if hasattr(fact, 'value') else fact.get('value')
                
                for concept in PERIOD_END_XBRL_CONCEPTS:
                    if concept in fact_name:
                        if fact_value:
                            self.logger.info(f"Found period end in facts ('{fact_name}'): {fact_value}")
                            return str(fact_value)
            
            self.logger.warning("Could not find period_end in metadata or facts")
            self.logger.warning(f"Metadata keys available: {list(metadata.keys())}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting period end: {e}")
            return None
    
    def _get_filing_date(self, parsed_filing) -> Optional[str]:
        """
        Extract filing date - market agnostic.
        
        Searches for various naming conventions defined in constants.py.
        """
        try:
            # Try from metadata
            metadata = parsed_filing.raw_data.get('metadata', {})
            
            for key in FILING_DATE_METADATA_KEYS:
                value = metadata.get(key)
                if value:
                    self.logger.info(f"Found filing date in metadata['{key}']: {value}")
                    return str(value)
            
            # Try from facts
            for fact in parsed_filing.facts[:MAX_FACTS_TO_SEARCH]:
                fact_name = fact.name if hasattr(fact, 'name') else fact.get('name', '')
                fact_value = fact.value if hasattr(fact, 'value') else fact.get('value')
                
                for concept in FILING_DATE_XBRL_CONCEPTS:
                    if concept in fact_name:
                        if fact_value:
                            self.logger.info(f"Found filing date in facts ('{fact_name}'): {fact_value}")
                            return str(fact_value)
            
            self.logger.warning("Could not find filing_date in metadata or facts")
            return None
        except Exception as e:
            self.logger.error(f"Error extracting filing date: {e}")
            return None


__all__ = ['FilingCharacteristicsExtractor']