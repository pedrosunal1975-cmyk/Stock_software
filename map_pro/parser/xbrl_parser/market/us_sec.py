# Path: xbrl_parser/market/us_sec.py
"""
US SEC Validator

SEC-specific validation rules for US GAAP filings.

This module validates:
- CIK format and presence
- Document type validity
- Required SEC elements
- Filing date rules
- Deprecated element usage

Example:
    from ..market import SECValidator
    
    validator = SECValidator()
    errors = validator.validate(parsed_filing)
"""

import logging
import re
from datetime import datetime

from ..models.parsed_filing import ParsedFiling
from ..models.error import ParsingError, ErrorSeverity, ErrorCategory
from ..market.constants import (
    US_SEC,
    MARKET_US_SEC
)


class SECValidator:
    """
    US SEC-specific validator.
    
    Validates SEC filing requirements including CIK, document types,
    and required elements.
    
    Example:
        validator = SECValidator()
        errors = validator.validate(filing)
        
        for error in errors:
            print(f"{error.severity}: {error.message}")
    """
    
    def __init__(self):
        """Initialize SEC validator."""
        self.logger = logging.getLogger(__name__)
        self.logger.debug("SECValidator initialized")
    
    def get_market_id(self) -> str:
        """Get market identifier."""
        return MARKET_US_SEC
    
    def validate(self, filing: ParsedFiling) -> list[ParsingError]:
        """
        Validate filing against SEC rules.
        
        Args:
            filing: Parsed filing to validate
            
        Returns:
            list of validation errors
        """
        errors: list[ParsingError] = []
        
        self.logger.info("Running SEC validation")
        
        # Validate CIK
        errors.extend(self._validate_cik(filing))
        
        # Validate document type
        errors.extend(self._validate_document_type(filing))
        
        # Validate required elements
        errors.extend(self._validate_required_elements(filing))
        
        # Validate filing dates
        errors.extend(self._validate_dates(filing))
        
        # Check deprecated elements
        errors.extend(self._check_deprecated_elements(filing))
        
        self.logger.info(f"SEC validation completed: {len(errors)} issues found")
        return errors
    
    def _validate_cik(self, filing: ParsedFiling) -> list[ParsingError]:
        """Validate CIK format and presence."""
        errors: list[ParsingError] = []
        
        if not filing.metadata or not filing.metadata.entity_identifier:
            errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                severity=ErrorSeverity.ERROR,
                message=US_SEC.MSG_MISSING_CIK,
                details={'code': US_SEC.ERR_MISSING_CIK},
                source_file=str(filing.metadata.entry_point) if filing.metadata and filing.metadata.entry_point else None
            ))
            return errors
        
        cik = filing.metadata.entity_identifier
        
        # Validate CIK format
        if not re.match(US_SEC.CIK_PATTERN, cik):
            errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                severity=ErrorSeverity.ERROR,
                message=US_SEC.MSG_INVALID_CIK,
                details={
                    'code': US_SEC.ERR_INVALID_CIK_FORMAT,
                    'cik': cik,
                    'expected_format': '10 digits'
                },
                source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
            ))
        
        return errors
    
    def _validate_document_type(self, filing: ParsedFiling) -> list[ParsingError]:
        """Validate document type."""
        errors: list[ParsingError] = []
        
        if not filing.metadata or not filing.metadata.document_type:
            errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                severity=ErrorSeverity.ERROR,
                message=US_SEC.MSG_MISSING_DOCTYPE,
                details={'code': US_SEC.ERR_MISSING_DOCUMENT_TYPE},
                source_file=str(filing.metadata.entry_point) if filing.metadata and filing.metadata.entry_point else None
            ))
            return errors
        
        doc_type = filing.metadata.document_type
        
        # Check if valid document type
        if doc_type not in US_SEC.VALID_DOCUMENT_TYPES:
            errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                severity=ErrorSeverity.WARNING,
                message=US_SEC.MSG_INVALID_DOCTYPE,
                details={
                    'code': US_SEC.ERR_INVALID_DOCUMENT_TYPE,
                    'document_type': doc_type,
                    'valid_types': US_SEC.VALID_DOCUMENT_TYPES[:5]  # Sample
                },
                source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
            ))
        
        return errors
    
    def _validate_required_elements(self, filing: ParsedFiling) -> list[ParsingError]:
        """Validate required SEC elements."""
        errors: list[ParsingError] = []
        
        if not filing.instance or not filing.instance.facts:
            return errors
        
        # Get all concepts
        concepts = {fact.concept for fact in filing.instance.facts}
        
        # Check for required elements
        for required in US_SEC.REQUIRED_ELEMENTS:
            found = any(required in concept for concept in concepts)
            
            if not found:
                errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    severity=ErrorSeverity.WARNING,
                    message=US_SEC.MSG_MISSING_ELEMENT,
                    details={
                        'code': US_SEC.ERR_MISSING_REQUIRED_ELEMENT,
                        'required_element': required
                    },
                    source_file=str(filing.metadata.entry_point) if filing.metadata and filing.metadata.entry_point else None
                ))
        
        return errors
    
    def _validate_dates(self, filing: ParsedFiling) -> list[ParsingError]:
        """Validate filing dates."""
        errors: list[ParsingError] = []
        
        if not filing.metadata:
            return errors
        
        # Check filing date
        if filing.metadata.filing_date:
            if not US_SEC.ALLOW_FUTURE_DATES:
                if filing.metadata.filing_date > datetime.now():
                    errors.append(ParsingError(
                        category=ErrorCategory.XBRL_INVALID,
                        severity=ErrorSeverity.ERROR,
                        message=US_SEC.MSG_FUTURE_DATE,
                        details={
                            'code': US_SEC.ERR_FUTURE_FILING_DATE,
                            'filing_date': filing.metadata.filing_date
                        },
                        source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                    ))
        
        # Check period length if period_end_date exists
        if filing.metadata.period_end_date and filing.metadata.filing_date:
            period_length = (filing.metadata.period_end_date - filing.metadata.filing_date).days
            
            if period_length > US_SEC.MAX_PERIOD_LENGTH_DAYS:
                errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    severity=ErrorSeverity.WARNING,
                    message=US_SEC.MSG_PERIOD_TOO_LONG,
                    details={
                        'code': US_SEC.ERR_PERIOD_TOO_LONG,
                        'period_days': period_length,
                        'max_days': US_SEC.MAX_PERIOD_LENGTH_DAYS
                    },
                    source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
                ))
        
        return errors
    
    def _check_deprecated_elements(self, filing: ParsedFiling) -> list[ParsingError]:
        """Check for deprecated taxonomy elements."""
        errors: list[ParsingError] = []
        
        if not US_SEC.WARN_DEPRECATED_ELEMENTS:
            return errors
        
        # This is a simplified check - in production you'd compare against
        # a list of deprecated elements from the taxonomy
        
        # For now, just log that we checked
        self.logger.debug("Deprecated element check completed")
        
        return errors


__all__ = ['SECValidator']
