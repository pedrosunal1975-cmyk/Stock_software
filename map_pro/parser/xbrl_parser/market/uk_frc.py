# Path: xbrl_parser/market/uk_frc.py
"""
UK FRC Validator

FRC-specific validation rules for UK filings.

This module validates:
- Companies House number format and presence
- Accounting standard validity
- Required FRC elements
- Authorization date rules
- Audit information requirements

Example:
    from ..market import FRCValidator
    
    validator = FRCValidator()
    errors = validator.validate(parsed_filing)
"""

import logging
import re
from datetime import datetime

from ..models.parsed_filing import ParsedFiling
from ..models.error import ParsingError, ErrorSeverity, ErrorCategory
from ..market.constants import (
    UK_FRC,
    MARKET_UK_FRC
)


class FRCValidator:
    """
    UK FRC-specific validator.
    
    Validates UK FRC filing requirements including Companies House number,
    accounting standards, and required elements.
    
    Example:
        validator = FRCValidator()
        errors = validator.validate(filing)
        
        for error in errors:
            print(f"{error.severity}: {error.message}")
    """
    
    def __init__(self):
        """Initialize FRC validator."""
        self.logger = logging.getLogger(__name__)
        self.logger.debug("FRCValidator initialized")
    
    def get_market_id(self) -> str:
        """Get market identifier."""
        return MARKET_UK_FRC
    
    def validate(self, filing: ParsedFiling) -> list[ParsingError]:
        """
        Validate filing against FRC rules.
        
        Args:
            filing: Parsed filing to validate
            
        Returns:
            list of validation errors
        """
        errors: list[ParsingError] = []
        
        self.logger.info("Running FRC validation")
        
        # Validate Companies House number
        errors.extend(self._validate_ch_number(filing))
        
        # Validate accounting standard
        errors.extend(self._validate_accounting_standard(filing))
        
        # Validate required elements
        errors.extend(self._validate_required_elements(filing))
        
        # Validate authorization date
        errors.extend(self._validate_authorization_date(filing))
        
        # Check audit information
        errors.extend(self._check_audit_information(filing))
        
        # Validate inline XBRL
        errors.extend(self._validate_inline_xbrl(filing))
        
        self.logger.info(f"FRC validation completed: {len(errors)} issues found")
        return errors
    
    def _validate_ch_number(self, filing: ParsedFiling) -> list[ParsingError]:
        """Validate Companies House number format and presence."""
        errors: list[ParsingError] = []
        
        if not UK_FRC.REQUIRE_COMPANIES_HOUSE_NUMBER:
            return errors
        
        if not filing.metadata or not filing.metadata.entity_identifier:
            errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                severity=ErrorSeverity.ERROR,
                message=UK_FRC.MSG_MISSING_CH,
                details={'code': UK_FRC.ERR_MISSING_CH_NUMBER},
                source_file=str(filing.metadata.entry_point) if filing.metadata and filing.metadata.entry_point else None
            ))
            return errors
        
        ch_number = filing.metadata.entity_identifier
        
        # Validate CH number format (6-8 alphanumeric characters)
        if not re.match(UK_FRC.CH_NUMBER_PATTERN, ch_number):
            errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                severity=ErrorSeverity.ERROR,
                message=UK_FRC.MSG_INVALID_CH,
                details={
                    'code': UK_FRC.ERR_INVALID_CH_NUMBER,
                    'ch_number': ch_number,
                    'expected_format': '6-8 alphanumeric characters'
                },
                source_file=str(filing.metadata.entry_point) if filing.metadata.entry_point else None
            ))
        
        return errors
    
    def _validate_accounting_standard(self, filing: ParsedFiling) -> list[ParsingError]:
        """Validate accounting standard."""
        errors: list[ParsingError] = []
        
        # Try to find accounting standard from facts
        if not filing.instance or not filing.instance.facts:
            return errors
        
        # Look for accounting standard in facts
        accounting_standard = None
        for fact in filing.instance.facts:
            if 'AccountingStandard' in fact.concept or 'Framework' in fact.concept:
                accounting_standard = fact.value
                break
        
        # If found, validate it
        if accounting_standard:
            # Normalize for comparison
            standard_upper = accounting_standard.upper()
            
            # Check if it matches any valid standard
            valid = any(
                valid_std.upper() in standard_upper
                for valid_std in UK_FRC.VALID_ACCOUNTING_STANDARDS
            )
            
            if not valid:
                errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    severity=ErrorSeverity.WARNING,
                    message=UK_FRC.MSG_INVALID_STANDARD,
                    details={
                        'code': UK_FRC.ERR_INVALID_STANDARD,
                        'accounting_standard': accounting_standard,
                        'valid_standards': UK_FRC.VALID_ACCOUNTING_STANDARDS
                    },
                    source_file=str(filing.metadata.entry_point) if filing.metadata and filing.metadata.entry_point else None
                ))
        
        return errors
    
    def _validate_required_elements(self, filing: ParsedFiling) -> list[ParsingError]:
        """Validate required FRC elements."""
        errors: list[ParsingError] = []
        
        if not filing.instance or not filing.instance.facts:
            return errors
        
        # Get all concepts
        concepts = {fact.concept for fact in filing.instance.facts}
        
        # Check for required elements
        for required in UK_FRC.REQUIRED_ELEMENTS:
            found = any(required in concept for concept in concepts)
            
            if not found:
                errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    severity=ErrorSeverity.WARNING,
                    message=UK_FRC.MSG_MISSING_ELEMENT,
                    details={
                        'code': UK_FRC.ERR_MISSING_REQUIRED_ELEMENT,
                        'required_element': required
                    },
                    source_file=str(filing.metadata.entry_point) if filing.metadata and filing.metadata.entry_point else None
                ))
        
        return errors
    
    def _validate_authorization_date(self, filing: ParsedFiling) -> list[ParsingError]:
        """Validate authorization date."""
        errors: list[ParsingError] = []
        
        # Look for authorization date in facts
        auth_date = None
        
        if filing.instance and filing.instance.facts:
            for fact in filing.instance.facts:
                if 'AuthorisationFinancialStatements' in fact.concept or 'DateAuthorisation' in fact.concept:
                    auth_date = fact.value
                    break
        
        if not auth_date:
            errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                severity=ErrorSeverity.WARNING,
                message=UK_FRC.MSG_MISSING_AUTH,
                details={'code': UK_FRC.ERR_MISSING_AUTH_DATE},
                source_file=str(filing.metadata.entry_point) if filing.metadata and filing.metadata.entry_point else None
            ))
            return errors
        
        # Check if authorization date is in the future
        if not UK_FRC.ALLOW_FUTURE_DATES:
            try:
                # Try to parse date
                if isinstance(auth_date, str):
                    # Handle common date formats
                    from dateutil import parser
                    auth_datetime = parser.parse(auth_date)
                    
                    if auth_datetime > datetime.now():
                        errors.append(ParsingError(
                            category=ErrorCategory.XBRL_INVALID,
                            severity=ErrorSeverity.ERROR,
                            message=UK_FRC.MSG_FUTURE_AUTH,
                            details={
                                'code': UK_FRC.ERR_FUTURE_AUTH_DATE,
                                'authorization_date': auth_date
                            },
                            source_file=str(filing.metadata.entry_point) if filing.metadata and filing.metadata.entry_point else None
                        ))
            except:
                # If parsing fails, skip date validation
                pass
        
        return errors
    
    def _check_audit_information(self, filing: ParsedFiling) -> list[ParsingError]:
        """Check for audit information."""
        errors: list[ParsingError] = []
        
        if not UK_FRC.REQUIRE_AUDIT_INFORMATION:
            return errors
        
        if not filing.instance or not filing.instance.facts:
            return errors
        
        # Look for audit-related concepts
        has_audit_info = False
        audit_opinion = None
        
        for fact in filing.instance.facts:
            concept_lower = fact.concept.lower()
            if 'audit' in concept_lower:
                has_audit_info = True
                if 'opinion' in concept_lower:
                    audit_opinion = fact.value
                break
        
        if not has_audit_info:
            errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                severity=ErrorSeverity.WARNING,
                message=UK_FRC.MSG_MISSING_AUDIT,
                details={'code': UK_FRC.ERR_MISSING_AUDIT_INFO},
                source_file=str(filing.metadata.entry_point) if filing.metadata and filing.metadata.entry_point else None
            ))
        
        # Validate audit opinion if found
        if audit_opinion:
            # Normalize opinion
            opinion_normalized = audit_opinion.strip().title()
            
            if opinion_normalized not in UK_FRC.VALID_AUDIT_OPINIONS:
                errors.append(ParsingError(
                    category=ErrorCategory.XBRL_INVALID,
                    severity=ErrorSeverity.WARNING,
                    message=UK_FRC.MSG_INVALID_OPINION,
                    details={
                        'code': UK_FRC.ERR_INVALID_AUDIT_OPINION,
                        'audit_opinion': audit_opinion,
                        'valid_opinions': UK_FRC.VALID_AUDIT_OPINIONS
                    },
                    source_file=str(filing.metadata.entry_point) if filing.metadata and filing.metadata.entry_point else None
                ))
        
        return errors
    
    def _validate_inline_xbrl(self, filing: ParsedFiling) -> list[ParsingError]:
        """Validate inline XBRL requirement."""
        errors: list[ParsingError] = []
        
        if not UK_FRC.REQUIRE_INLINE_XBRL:
            return errors
        
        # Check if filing is inline XBRL
        is_inline = False
        
        if filing.metadata and filing.metadata.source_files:
            for source_file in filing.metadata.source_files:
                source_str = str(source_file).lower()
                if '.xhtml' in source_str or 'inline' in source_str:
                    is_inline = True
                    break
        
        if not is_inline:
            errors.append(ParsingError(
                category=ErrorCategory.XBRL_INVALID,
                severity=ErrorSeverity.WARNING,
                message="FRC filings should use Inline XBRL format",
                details={'code': 'FRC_INLINE_XBRL'},
                source_file=str(filing.metadata.entry_point) if filing.metadata and filing.metadata.entry_point else None
            ))
        
        return errors


__all__ = ['FRCValidator']
