# Path: xbrl_parser/market/eu_esef.py
"""
EU ESEF Validator

ESEF-specific validation rules for European filings.

This module validates:
- LEI format and presence
- Inline XBRL requirements
- Extension taxonomy requirements
- Language validity
- Anchoring requirements
- XHTML document requirements

Example:
    from ..market import ESEFValidator
    
    validator = ESEFValidator()
    errors = validator.validate(parsed_filing)
"""

import logging
import re

from ..models.parsed_filing import ParsedFiling
from ..models.error import ParsingError, ErrorSeverity, ErrorCategory
from ..market.constants import (
    EU_ESEF,
    MARKET_EU_ESEF
)


class ESEFValidator:
    """
    EU ESEF-specific validator.
    
    Validates ESEF filing requirements including LEI, inline XBRL,
    extension taxonomy, and anchoring.
    
    Example:
        validator = ESEFValidator()
        errors = validator.validate(filing)
        
        for error in errors:
            print(f"{error.severity}: {error.message}")
    """
    
    def __init__(self):
        """Initialize ESEF validator."""
        self.logger = logging.getLogger(__name__)
        self.logger.debug("ESEFValidator initialized")
    
    def get_market_id(self) -> str:
        """Get market identifier."""
        return MARKET_EU_ESEF
    
    def validate(self, filing: ParsedFiling) -> list[ParsingError]:
        """
        Validate filing against ESEF rules.
        
        Args:
            filing: Parsed filing to validate
            
        Returns:
            list of validation errors
        """
        errors: list[ParsingError] = []
        
        self.logger.info("Running ESEF validation")
        
        # Validate LEI
        errors.extend(self._validate_lei(filing))
        
        # Validate inline XBRL
        errors.extend(self._validate_inline_xbrl(filing))
        
        # Validate extension taxonomy
        errors.extend(self._validate_extension_taxonomy(filing))
        
        # Validate required elements
        errors.extend(self._validate_required_elements(filing))
        
        # Validate language
        errors.extend(self._validate_language(filing))
        
        # Check anchoring
        errors.extend(self._check_anchoring(filing))
        
        # Validate XHTML
        errors.extend(self._validate_xhtml(filing))
        
        self.logger.info(f"ESEF validation completed: {len(errors)} issues found")
        return errors
    
    def _validate_lei(self, filing: ParsedFiling) -> list[ParsingError]:
        """Validate LEI format and presence."""
        errors: list[ParsingError] = []
        
        if not filing.metadata or not filing.metadata.entity_identifier:
            errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                severity=ErrorSeverity.ERROR,
                message=EU_ESEF.MSG_MISSING_LEI,
                details={'code': EU_ESEF.ERR_MISSING_LEI},
                source_file=str(filing.metadata.entry_point) if filing.metadata and filing.metadata.entry_point else None
            ))
            return errors
        
        lei = filing.metadata.entity_identifier
        
        # Validate LEI format (20 characters: 18 alphanumeric + 2 digits)
        if not re.match(EU_ESEF.LEI_PATTERN, lei):
            errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                severity=ErrorSeverity.ERROR,
                message=EU_ESEF.MSG_INVALID_LEI,
                details={
                    'code': EU_ESEF.ERR_INVALID_LEI_FORMAT,
                    'lei': lei,
                    'expected_format': '20 characters (18 alphanumeric + 2 digits)'
                },
                source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
            ))
        
        return errors
    
    def _validate_inline_xbrl(self, filing: ParsedFiling) -> list[ParsingError]:
        """Validate inline XBRL requirement."""
        errors: list[ParsingError] = []
        
        if not EU_ESEF.REQUIRE_INLINE_XBRL:
            return errors
        
        # Check if filing is inline XBRL
        is_inline = False
        
        if filing.metadata and filing.metadata.source_files:
            # Check for .xhtml or inline XBRL indicators
            for source_file in filing.metadata.source_files:
                source_str = str(source_file).lower()
                if '.xhtml' in source_str or 'inline' in source_str:
                    is_inline = True
                    break
        
        if not is_inline:
            errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                severity=ErrorSeverity.ERROR,
                message=EU_ESEF.MSG_NO_IXBRL,
                details={'code': EU_ESEF.ERR_MISSING_INLINE_XBRL},
                source_file=str(filing.metadata.entry_point) if filing.metadata and filing.metadata.entry_point else None
            ))
        
        return errors
    
    def _validate_extension_taxonomy(self, filing: ParsedFiling) -> list[ParsingError]:
        """Validate extension taxonomy requirement."""
        errors: list[ParsingError] = []
        
        if not EU_ESEF.REQUIRE_EXTENSION_TAXONOMY:
            return errors
        
        # Check for extension taxonomy
        has_extension = False
        
        if filing.taxonomy and hasattr(filing.taxonomy, 'namespaces'):
            namespaces = filing.taxonomy.namespaces
            
            # Look for extension namespace (typically company-specific)
            for ns_prefix, ns_uri in namespaces.items():
                # Extension namespaces usually don't contain standard taxonomy URIs
                if not any(standard in ns_uri for standard in EU_ESEF.NAMESPACES):
                    has_extension = True
                    break
        
        if not has_extension:
            errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                severity=ErrorSeverity.WARNING,
                message=EU_ESEF.MSG_NO_EXTENSION,
                details={'code': EU_ESEF.ERR_NO_EXTENSION_TAXONOMY},
                source_file=str(filing.metadata.entry_point) if filing.metadata and filing.metadata.entry_point else None
            ))
        
        return errors
    
    def _validate_required_elements(self, filing: ParsedFiling) -> list[ParsingError]:
        """Validate required ESEF elements."""
        errors: list[ParsingError] = []
        
        if not filing.instance or not filing.instance.facts:
            return errors
        
        # Get all concepts
        concepts = {fact.concept for fact in filing.instance.facts}
        
        # Check for required elements
        for required in EU_ESEF.REQUIRED_ELEMENTS:
            found = any(required in concept for concept in concepts)
            
            if not found:
                errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    severity=ErrorSeverity.WARNING,
                    message=EU_ESEF.MSG_MISSING_ELEMENT,
                    details={
                        'code': EU_ESEF.ERR_MISSING_REQUIRED_ELEMENT,
                        'required_element': required
                    },
                    source_file=str(filing.metadata.entry_point) if filing.metadata and filing.metadata.entry_point else None
                ))
        
        return errors
    
    def _validate_language(self, filing: ParsedFiling) -> list[ParsingError]:
        """Validate language against ESEF supported languages."""
        errors: list[ParsingError] = []
        
        # Check if language attribute exists and has value
        if not filing.metadata or not hasattr(filing.metadata, 'language') or not filing.metadata.language:
            return errors
        
        language = filing.metadata.language.lower()
        
        # Check if language is in supported list
        if language not in EU_ESEF.VALID_LANGUAGES:
            errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                severity=ErrorSeverity.WARNING,
                message=EU_ESEF.MSG_INVALID_LANG,
                details={
                    'code': EU_ESEF.ERR_INVALID_LANGUAGE,
                    'language': language,
                    'supported_languages': EU_ESEF.VALID_LANGUAGES[:10]  # Sample
                },
                source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
            ))
        
        return errors
    
    def _check_anchoring(self, filing: ParsedFiling) -> list[ParsingError]:
        """Check anchoring to IFRS taxonomy."""
        errors: list[ParsingError] = []
        
        if not EU_ESEF.REQUIRE_ANCHORING:
            return errors
        
        if not filing.instance or not filing.instance.facts:
            return errors
        
        # Calculate anchoring percentage
        total_facts = len(filing.instance.facts)
        anchored_facts = 0
        
        # Check how many facts use IFRS taxonomy concepts
        for fact in filing.instance.facts:
            concept = fact.concept
            # IFRS concepts typically contain 'ifrs' in the concept name
            if 'ifrs' in concept.lower():
                anchored_facts += 1
        
        if total_facts > 0:
            anchoring_percent = (anchored_facts / total_facts) * 100
            
            if anchoring_percent < EU_ESEF.MIN_ANCHORED_ELEMENTS_PERCENT:
                errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    severity=ErrorSeverity.WARNING,
                    message=EU_ESEF.MSG_LOW_ANCHORING,
                    details={
                        'code': EU_ESEF.ERR_INSUFFICIENT_ANCHORING,
                        'anchoring_percent': round(anchoring_percent, 1),
                        'minimum_required': EU_ESEF.MIN_ANCHORED_ELEMENTS_PERCENT
                    },
                    source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                ))
        
        return errors
    
    def _validate_xhtml(self, filing: ParsedFiling) -> list[ParsingError]:
        """Validate XHTML document requirement."""
        errors: list[ParsingError] = []
        
        if not EU_ESEF.REQUIRE_XHTML_DOCUMENT:
            return errors
        
        # Check for XHTML document
        has_xhtml = False
        
        if filing.metadata and filing.metadata.source_files:
            for source_file in filing.metadata.source_files:
                if str(source_file).lower().endswith('.xhtml'):
                    has_xhtml = True
                    break
        
        if not has_xhtml:
            errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                severity=ErrorSeverity.ERROR,
                message=EU_ESEF.MSG_NO_XHTML,
                details={'code': EU_ESEF.ERR_MISSING_XHTML},
                source_file=str(filing.metadata.entry_point) if filing.metadata and filing.metadata.entry_point else None
            ))
        
        return errors


__all__ = ['ESEFValidator']
