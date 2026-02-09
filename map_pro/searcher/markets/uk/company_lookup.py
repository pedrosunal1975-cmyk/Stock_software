# Path: searcher/markets/uk/company_lookup.py
"""
UK Company Number Lookup

Validates and normalizes UK company numbers.
Supports lookup by company number or name.
"""

import re
from typing import Optional

from searcher.core.logger import get_logger
from searcher.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT
from searcher.markets.uk.constants import (
    COMPANY_NUMBER_MIN_LENGTH,
    COMPANY_NUMBER_MAX_LENGTH,
    COMPANY_NUMBER_PATTERN,
    PREFIX_SCOTLAND,
    PREFIX_NORTHERN_IRELAND,
    PREFIX_EUROPEAN_SE,
    PREFIX_OVERSEAS,
    MSG_INVALID_COMPANY_NUMBER,
    ERR_INVALID_COMPANY_NUMBER,
)
from searcher.markets.uk.api_client import UKAPIClient
from searcher.markets.uk.url_builder import UKURLBuilder

logger = get_logger(__name__, 'markets')


class UKCompanyLookup:
    """
    Validates and resolves UK company numbers.

    Handles:
    - Company number format validation
    - Number normalization (uppercase, padding)
    - Prefix validation (SC, NI, SE, FC)
    - Company existence verification via API
    """

    def __init__(self, api_client: UKAPIClient, url_builder: UKURLBuilder):
        """
        Initialize company lookup.

        Args:
            api_client: UK API client
            url_builder: UK URL builder
        """
        self.api_client = api_client
        self.url_builder = url_builder

        # Compile regex pattern
        self._pattern = re.compile(COMPANY_NUMBER_PATTERN)

    def validate_format(self, company_number: str) -> bool:
        """
        Validate company number format.

        Args:
            company_number: Company number to validate

        Returns:
            bool: True if valid format
        """
        if not company_number:
            return False

        # Normalize
        normalized = company_number.strip().upper()

        # Check length
        if len(normalized) < COMPANY_NUMBER_MIN_LENGTH:
            return False
        if len(normalized) > COMPANY_NUMBER_MAX_LENGTH:
            return False

        # Check pattern
        return bool(self._pattern.match(normalized))

    def normalize(self, company_number: str) -> str:
        """
        Normalize company number to standard format.

        Normalization:
        - Convert to uppercase
        - Strip whitespace
        - Validate format

        Args:
            company_number: Company number to normalize

        Returns:
            str: Normalized company number

        Raises:
            ValueError: Invalid company number format
        """
        if not company_number:
            raise ValueError(f"{MSG_INVALID_COMPANY_NUMBER}: empty")

        # Normalize
        normalized = company_number.strip().upper()

        # Remove common separators (if any)
        normalized = normalized.replace(' ', '').replace('-', '')

        # Validate
        if not self.validate_format(normalized):
            raise ValueError(
                f"{MSG_INVALID_COMPANY_NUMBER}: '{company_number}' "
                f"(must be {COMPANY_NUMBER_MIN_LENGTH}-{COMPANY_NUMBER_MAX_LENGTH} alphanumeric characters)"
            )

        logger.debug(
            f"Normalized company number: {company_number} -> {normalized}",
            extra={LOG_PROCESS: 'normalize_company_number'}
        )

        return normalized

    def get_jurisdiction(self, company_number: str) -> str:
        """
        Get jurisdiction from company number prefix.

        Args:
            company_number: Normalized company number

        Returns:
            str: Jurisdiction code
        """
        if company_number.startswith(PREFIX_SCOTLAND):
            return 'scotland'
        elif company_number.startswith(PREFIX_NORTHERN_IRELAND):
            return 'northern-ireland'
        elif company_number.startswith(PREFIX_EUROPEAN_SE):
            return 'european-public-limited-liability-company-se'
        elif company_number.startswith(PREFIX_OVERSEAS):
            return 'overseas-entity'
        else:
            return 'england-wales'

    async def verify_exists(self, company_number: str) -> tuple[bool, Optional[dict]]:
        """
        Verify company exists in Companies House.

        Args:
            company_number: Normalized company number

        Returns:
            tuple: (exists: bool, company_data: dict or None)
        """
        try:
            # Get company profile
            url = self.url_builder.get_company_profile_url(company_number)
            company_data = await self.api_client.get_json(url)

            if company_data:
                logger.debug(
                    f"Company found: {company_data.get('company_name', 'Unknown')}",
                    extra={LOG_OUTPUT: 'company_lookup', 'company_number': company_number}
                )
                return True, company_data
            else:
                logger.warning(
                    f"Company not found: {company_number}",
                    extra={LOG_OUTPUT: 'company_lookup_failed', 'company_number': company_number}
                )
                return False, None

        except Exception as e:
            logger.error(
                f"Error verifying company {company_number}: {e}",
                extra={LOG_OUTPUT: 'error', 'company_number': company_number}
            )
            return False, None

    async def resolve(self, identifier: str) -> tuple[str, Optional[dict]]:
        """
        Resolve identifier to company number and data.

        Args:
            identifier: Company number or name

        Returns:
            tuple: (company_number: str, company_data: dict or None)

        Raises:
            ValueError: Invalid identifier or company not found
        """
        logger.debug(
            f"Resolving identifier: {identifier}",
            extra={LOG_INPUT: 'resolve_identifier'}
        )

        # Try as direct company number
        try:
            company_number = self.normalize(identifier)

            # Verify exists
            exists, company_data = await self.verify_exists(company_number)

            if exists:
                return company_number, company_data
            else:
                raise ValueError(f"Company not found: {company_number}")

        except ValueError as e:
            # If format validation failed, could be a company name
            # For now, we only support direct company numbers
            # Future: implement company name search
            logger.error(
                f"Failed to resolve identifier: {identifier} - {e}",
                extra={LOG_OUTPUT: 'error'}
            )
            raise ValueError(f"Invalid company number or company not found: {identifier}")
