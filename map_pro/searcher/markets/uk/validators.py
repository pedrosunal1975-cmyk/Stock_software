# Path: searcher/markets/uk/validators.py
"""
UK Search Input Validators

Validates user input for UK company searches.
"""

import re
from datetime import datetime
from typing import Optional

from searcher.markets.uk.constants import (
    COMPANY_NUMBER_PATTERN,
    FILING_TYPE_FULL_ACCOUNTS,
    FILING_TYPE_ABRIDGED_ACCOUNTS,
    FILING_TYPE_DORMANT_ACCOUNTS,
    FILING_TYPE_GROUP_ACCOUNTS,
    MSG_INVALID_COMPANY_NUMBER,
    ERR_INVALID_COMPANY_NUMBER,
    ERR_INVALID_FILING_TYPE,
)


class UKValidators:
    """
    Validates UK search input parameters.

    Handles:
    - Company number validation
    - Filing type validation
    - Date range validation
    - Limit validation
    """

    # Valid filing types
    VALID_FILING_TYPES = [
        FILING_TYPE_FULL_ACCOUNTS,
        FILING_TYPE_ABRIDGED_ACCOUNTS,
        FILING_TYPE_DORMANT_ACCOUNTS,
        FILING_TYPE_GROUP_ACCOUNTS,
    ]

    @staticmethod
    def validate_company_number(company_number: str) -> tuple[bool, Optional[str]]:
        """
        Validate company number format.

        Args:
            company_number: Company number to validate

        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        if not company_number:
            return False, "Company number is required"

        # Normalize
        normalized = company_number.strip().upper()

        # Check pattern
        if not re.match(COMPANY_NUMBER_PATTERN, normalized):
            return False, f"{MSG_INVALID_COMPANY_NUMBER}: '{company_number}'"

        return True, None

    @staticmethod
    def validate_filing_types(filing_types: list[str]) -> tuple[bool, Optional[str]]:
        """
        Validate filing type codes.

        Args:
            filing_types: List of filing type codes

        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        if not filing_types:
            return True, None  # Optional parameter

        if not isinstance(filing_types, list):
            return False, "Filing types must be a list"

        # Check each type
        invalid = [ft for ft in filing_types if ft not in UKValidators.VALID_FILING_TYPES]

        if invalid:
            return False, f"Invalid filing types: {invalid}. Valid types: {UKValidators.VALID_FILING_TYPES}"

        return True, None

    @staticmethod
    def validate_date(date_str: str) -> tuple[bool, Optional[str]]:
        """
        Validate date string format (YYYY-MM-DD).

        Args:
            date_str: Date string

        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        if not date_str:
            return True, None  # Optional

        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True, None
        except ValueError:
            return False, f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD"

    @staticmethod
    def validate_date_range(
        start_date: str,
        end_date: str
    ) -> tuple[bool, Optional[str]]:
        """
        Validate date range.

        Args:
            start_date: Start date string
            end_date: End date string

        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        # Validate individual dates
        valid_start, err_start = UKValidators.validate_date(start_date)
        if not valid_start:
            return False, err_start

        valid_end, err_end = UKValidators.validate_date(end_date)
        if not valid_end:
            return False, err_end

        # Check range order
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')

                if start > end:
                    return False, f"Start date ({start_date}) must be before end date ({end_date})"
            except Exception as e:
                return False, f"Date range validation error: {e}"

        return True, None

    @staticmethod
    def validate_limit(limit: int) -> tuple[bool, Optional[str]]:
        """
        Validate result limit.

        Args:
            limit: Maximum results

        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        if not isinstance(limit, int):
            return False, "Limit must be an integer"

        if limit < 1:
            return False, "Limit must be at least 1"

        if limit > 1000:
            return False, "Limit cannot exceed 1000"

        return True, None

    @staticmethod
    def validate_search_params(
        identifier: str,
        filing_types: list[str] = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = 10
    ) -> tuple[bool, Optional[str]]:
        """
        Validate all search parameters.

        Args:
            identifier: Company number
            filing_types: Filing type codes
            start_date: Start date
            end_date: End date
            limit: Result limit

        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        # Validate company number
        valid, error = UKValidators.validate_company_number(identifier)
        if not valid:
            return False, error

        # Validate filing types
        valid, error = UKValidators.validate_filing_types(filing_types)
        if not valid:
            return False, error

        # Validate date range
        valid, error = UKValidators.validate_date_range(start_date, end_date)
        if not valid:
            return False, error

        # Validate limit
        valid, error = UKValidators.validate_limit(limit)
        if not valid:
            return False, error

        return True, None
