# Path: searcher/markets/sec/sec_validators.py
"""
SEC Validators

Validation functions for SEC-specific data formats.
Validates CIKs, tickers, accession numbers, and filing types.
"""

import re
from typing import Optional
from datetime import date

from searcher.core.logger import get_logger
from searcher.markets.sec.constants import (
    CIK_LENGTH,
    MAJOR_FILING_TYPES,
    SEC_FOUNDING_YEAR,
)

logger = get_logger(__name__, 'markets')


class SECValidator:
    """Validator for SEC-specific formats and identifiers."""
    
    @staticmethod
    def validate_cik(cik: str) -> bool:
        """
        Validate CIK format.
        
        CIK must be numeric and can be 1-10 digits.
        Leading zeros are optional in input but required in API calls.
        
        Args:
            cik: CIK string to validate
            
        Returns:
            True if valid CIK format
        """
        if not cik or not isinstance(cik, str):
            return False
        
        # Remove any whitespace
        cik = cik.strip()
        
        # Must be numeric
        if not cik.isdigit():
            return False
        
        # Must be between 1 and 10 digits
        if len(cik) < 1 or len(cik) > CIK_LENGTH:
            return False
        
        return True
    
    @staticmethod
    def normalize_cik(cik: str) -> str:
        """
        Normalize CIK to 10-digit format with leading zeros.
        
        Args:
            cik: CIK string (can be 1-10 digits)
            
        Returns:
            10-digit CIK with leading zeros
            
        Raises:
            ValueError: If CIK is invalid
        """
        if not SECValidator.validate_cik(cik):
            raise ValueError(f"Invalid CIK format: {cik}")
        
        # Pad with leading zeros to 10 digits
        return cik.strip().zfill(CIK_LENGTH)
    
    @staticmethod
    def validate_ticker(ticker: str) -> bool:
        """
        Validate ticker symbol format.
        
        Tickers are typically 1-5 uppercase letters.
        Some special cases exist (e.g., BRK.A, BRK.B).
        
        Args:
            ticker: Ticker symbol to validate
            
        Returns:
            True if valid ticker format
        """
        if not ticker or not isinstance(ticker, str):
            return False
        
        ticker = ticker.strip().upper()
        
        # Basic pattern: 1-5 letters, optionally followed by .A, .B, etc.
        pattern = r'^[A-Z]{1,5}(\.[A-Z])?$'
        
        return bool(re.match(pattern, ticker))
    
    @staticmethod
    def normalize_ticker(ticker: str) -> str:
        """
        Normalize ticker symbol to uppercase.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            Uppercase ticker symbol
        """
        return ticker.strip().upper()
    
    @staticmethod
    def validate_accession_number(accession_number: str) -> bool:
        """
        Validate SEC accession number format.
        
        Format: NNNNNNNNNN-NN-NNNNNN (10-2-6 digits with hyphens)
        Example: 0001193125-21-123456
        
        Args:
            accession_number: Accession number to validate
            
        Returns:
            True if valid accession number format
        """
        if not accession_number or not isinstance(accession_number, str):
            return False
        
        # Pattern: 10 digits, hyphen, 2 digits, hyphen, 6 digits
        pattern = r'^\d{10}-\d{2}-\d{6}$'
        
        return bool(re.match(pattern, accession_number.strip()))
    
    @staticmethod
    def validate_filing_type(filing_type: str) -> bool:
        """
        Validate filing type.
        
        Args:
            filing_type: Filing type to validate
            
        Returns:
            True if recognized filing type
        """
        if not filing_type or not isinstance(filing_type, str):
            return False
        
        filing_type = filing_type.strip().upper()
        
        # Check against known major filing types
        return filing_type in MAJOR_FILING_TYPES
    
    @staticmethod
    def validate_date(date_value: date) -> bool:
        """
        Validate filing date.
        
        Date must be reasonable (not in future, not before SEC founding in 1934).
        
        Args:
            date_value: Date to validate
            
        Returns:
            True if valid date
        """
        if not isinstance(date_value, date):
            return False

        # SEC was founded in 1934
        if date_value.year < SEC_FOUNDING_YEAR:
            return False
        
        # Date cannot be in the future
        if date_value > date.today():
            return False
        
        return True
    
    @staticmethod
    def validate_date_range(date_from: Optional[date], date_to: Optional[date]) -> bool:
        """
        Validate date range.
        
        Args:
            date_from: Start date
            date_to: End date
            
        Returns:
            True if valid date range
        """
        if date_from is None and date_to is None:
            return True  # No range specified is valid
        
        if date_from is not None:
            if not SECValidator.validate_date(date_from):
                return False
        
        if date_to is not None:
            if not SECValidator.validate_date(date_to):
                return False
        
        # If both specified, from must be before to
        if date_from is not None and date_to is not None:
            if date_from > date_to:
                return False
        
        return True
    
    @staticmethod
    def identify_identifier_type(identifier: str) -> Optional[str]:
        """
        Identify what type of identifier this is.
        
        Args:
            identifier: Company identifier
            
        Returns:
            'cik', 'ticker', or None if cannot determine
        """
        if not identifier:
            return None
        
        identifier = identifier.strip()
        
        # Check if it's a CIK (all digits)
        if identifier.isdigit():
            if SECValidator.validate_cik(identifier):
                return 'cik'
        
        # Check if it's a ticker (letters, possibly with dot)
        if SECValidator.validate_ticker(identifier):
            return 'ticker'
        
        return None
    
    @staticmethod
    def validate_url(url: str, allowed_domains: list) -> bool:
        """
        Validate URL is from allowed SEC domains.
        
        Args:
            url: URL to validate
            allowed_domains: List of allowed domain names
            
        Returns:
            True if URL is from allowed domain
        """
        if not url or not isinstance(url, str):
            return False
        
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(url)
            return parsed.netloc in allowed_domains
        except Exception:
            return False


# Convenience functions for backward compatibility
def validate_cik(cik: str) -> bool:
    """Validate CIK format."""
    return SECValidator.validate_cik(cik)


def normalize_cik(cik: str) -> str:
    """Normalize CIK to 10-digit format."""
    return SECValidator.normalize_cik(cik)


def validate_ticker(ticker: str) -> bool:
    """Validate ticker symbol format."""
    return SECValidator.validate_ticker(ticker)


def normalize_ticker(ticker: str) -> str:
    """Normalize ticker to uppercase."""
    return SECValidator.normalize_ticker(ticker)


def identify_identifier_type(identifier: str) -> Optional[str]:
    """Identify identifier type (cik or ticker)."""
    return SECValidator.identify_identifier_type(identifier)


__all__ = [
    'SECValidator',
    'validate_cik',
    'normalize_cik',
    'validate_ticker',
    'normalize_ticker',
    'identify_identifier_type',
]