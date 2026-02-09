# Path: searcher/markets/esef/searcher.py
"""
ESEF Searcher

Main searcher implementation for ESEF/UKSEF filings via filings.xbrl.org.
Implements BaseSearcher interface with async operations.
"""

import re
from typing import Optional

from searcher.engine.base_searcher import BaseSearcher
from searcher.core.logger import get_logger
from searcher.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT
from searcher.markets.esef.constants import (
    MARKET_ID,
    FORM_TYPE_ALIASES,
    REPORT_TYPE_AFR,
    LEI_PATTERN,
    COUNTRY_UK,
    MSG_NO_FILINGS_FOUND,
)
from searcher.markets.esef.api_client import ESEFAPIClient
from searcher.markets.esef.url_builder import ESEFURLBuilder
from searcher.markets.esef.response_parser import ESEFResponseParser

logger = get_logger(__name__, 'markets')


class ESEFSearcher(BaseSearcher):
    """
    ESEF/UKSEF searcher implementation using filings.xbrl.org API.

    Workflow:
    1. Parse identifier (LEI or company name)
    2. Build API query with filters
    3. Fetch filings from API
    4. Parse response and extract download URLs
    5. Build result dictionaries
    """

    def __init__(self):
        """Initialize ESEF searcher with all components."""
        self.api_client = ESEFAPIClient()
        self.url_builder = ESEFURLBuilder()
        self.response_parser = ESEFResponseParser()

    async def search_by_identifier(
        self,
        identifier: str,
        form_type: str,
        max_results: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        country: Optional[str] = None
    ) -> list[dict]:
        """
        Search ESEF filings by company identifier.

        Args:
            identifier: LEI or company name
            form_type: Report type (AFR, SFR, etc.)
            max_results: Maximum results to return
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            country: Optional country filter (e.g., 'GB')

        Returns:
            List of filing dictionaries
        """
        logger.info(
            f"{LOG_INPUT} ESEF search: {identifier} / {form_type} / max={max_results}"
        )

        # Normalize form type
        report_type = self._normalize_form_type(form_type)

        # Determine if identifier is LEI or name
        lei = None

        if self._is_lei(identifier):
            lei = identifier.upper()
            logger.info(f"{LOG_PROCESS} Using LEI directly: {lei}")
        else:
            # Search entities first to get LEI from name
            logger.info(f"{LOG_PROCESS} Searching entities by name: {identifier}")
            entity_info = await self._get_entity_by_name(identifier, country)

            if not entity_info:
                logger.warning(f"{LOG_OUTPUT} No entity found for name: {identifier}")
                return []

            lei = entity_info.get('lei')
            logger.info(f"{LOG_PROCESS} Found entity LEI: {lei}")

        if not lei:
            logger.warning(f"{LOG_OUTPUT} Could not determine LEI for: {identifier}")
            return []

        # Build API URL for filings (filter by entity.identifier = LEI)
        # Note: filings.xbrl.org API does NOT have report_type field
        # All filings are returned regardless of form_type requested

        url = self.url_builder.get_filings_url(
            country=country,
            entity_identifier=lei,
            period_end_from=start_date,
            period_end_to=end_date,
            page_size=max_results,
            include_entity=True
        )

        # Fetch filings
        logger.info(f"{LOG_PROCESS} Fetching filings from: {url}")
        response = await self.api_client.get_json(url)

        if not response:
            logger.warning(f"{LOG_OUTPUT} {MSG_NO_FILINGS_FOUND}")
            return []

        # Parse response
        filings = self.response_parser.parse_filings_response(response)
        logger.info(f"{LOG_PROCESS} API returned {len(filings)} filings")

        if not filings:
            logger.warning(f"{LOG_OUTPUT} {MSG_NO_FILINGS_FOUND}")
            return []

        # Build result dictionaries
        results = []
        for filing in filings[:max_results]:
            result = self._build_filing_result(filing, report_type)
            if result:
                results.append(result)

        logger.info(f"{LOG_OUTPUT} ESEF search complete: {len(results)} results")
        return results

    async def _get_entity_api_id_by_lei(self, lei: str) -> Optional[str]:
        """
        Get entity API ID by fetching entity directly via LEI.

        Args:
            lei: Legal Entity Identifier

        Returns:
            Entity API ID string if found, None otherwise
        """
        # Fetch entity directly by LEI
        url = self.url_builder.get_entity_by_lei_url(lei)
        logger.info(f"{LOG_PROCESS} Fetching entity by LEI: {url}")

        response = await self.api_client.get_json(url)

        if not response:
            return None

        # Extract entity API ID from JSON:API response
        # Response format: {"data": {"type": "entity", "id": "...", "attributes": {...}}}
        data = response.get('data', {})
        if isinstance(data, dict):
            return data.get('id')

        return None

    async def _get_entity_by_name(
        self,
        name: str,
        country: Optional[str] = None
    ) -> Optional[dict]:
        """
        Search entities endpoint to get entity info by company name.

        Args:
            name: Company name to search
            country: Optional country filter

        Returns:
            dict with 'lei' and 'api_id' if found, None otherwise
        """
        # Build entities search URL
        url = self.url_builder.get_entities_url(
            country=country,
            name=name,
            page_size=5  # Get top 5 matches
        )

        logger.info(f"{LOG_PROCESS} Searching entities: {url}")
        response = await self.api_client.get_json(url)

        if not response:
            return None

        # Parse entities response
        entities = self.response_parser.parse_entities_response(response)

        if not entities:
            return None

        # Return first matching entity's info
        first_entity = entities[0]
        return {
            'lei': first_entity.get('lei'),
            'api_id': first_entity.get('api_id')
        }

    async def search_by_company_name(
        self,
        company_name: str,
        form_type: str,
        max_results: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        country: Optional[str] = None
    ) -> list[dict]:
        """
        Search ESEF filings by company name.

        Delegates to search_by_identifier.

        Args:
            company_name: Company name
            form_type: Report type
            max_results: Maximum results
            start_date: Optional start date
            end_date: Optional end date
            country: Optional country filter

        Returns:
            List of filing dictionaries
        """
        return await self.search_by_identifier(
            identifier=company_name,
            form_type=form_type,
            max_results=max_results,
            start_date=start_date,
            end_date=end_date,
            country=country
        )

    async def search_uk_filings(
        self,
        identifier: str,
        form_type: str = REPORT_TYPE_AFR,
        max_results: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> list[dict]:
        """
        Search UK ESEF/UKSEF filings specifically.

        Convenience method for UK-specific searches.

        Args:
            identifier: LEI or company name
            form_type: Report type
            max_results: Maximum results
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            List of filing dictionaries
        """
        return await self.search_by_identifier(
            identifier=identifier,
            form_type=form_type,
            max_results=max_results,
            start_date=start_date,
            end_date=end_date,
            country=COUNTRY_UK
        )

    def _normalize_form_type(self, form_type: str) -> str:
        """
        Normalize form type to ESEF report type.

        Args:
            form_type: User input (e.g., 'annual', '10-K', 'AFR')

        Returns:
            Normalized report type (e.g., 'AFR')
        """
        form_type_clean = form_type.strip().lower().replace(' ', '').replace('-', '')

        # Check aliases
        if form_type_clean in FORM_TYPE_ALIASES:
            normalized = FORM_TYPE_ALIASES[form_type_clean]
            logger.debug(f"Normalized form type: {form_type} -> {normalized}")
            return normalized

        # Return uppercase if no alias (might be already normalized)
        return form_type.strip().upper()

    def _is_lei(self, identifier: str) -> bool:
        """
        Check if identifier is a valid LEI format.

        Args:
            identifier: Identifier string

        Returns:
            bool: True if matches LEI pattern
        """
        return bool(re.match(LEI_PATTERN, identifier.upper()))

    def _build_filing_result(self, filing: dict, form_type: str) -> Optional[dict]:
        """
        Build standardized result dictionary from parsed filing.

        Args:
            filing: Parsed filing from response
            form_type: Requested form type (used as fallback since API has no report_type)

        Returns:
            dict: Standardized result or None
        """
        # Get download URL
        download_url = self.response_parser.get_filing_download_url(filing)
        if not download_url:
            logger.warning(f"No download URL for filing {filing.get('filing_id')}")
            return None

        # Extract entity info from included entity data
        # The API returns entity data via relationship/included, not as direct fields
        entity = filing.get('entity', {})
        entity_name = entity.get('name', '')
        lei = entity.get('lei', '') or entity.get('identifier', '')

        # Build result using BaseSearcher helper
        # Note: API has no report_type field, use the requested form_type
        return self._build_result_dict(
            filing_url=download_url,
            form_type=form_type,
            filing_date=filing.get('period_end', ''),
            company_name=entity_name,
            entity_id=lei,
            accession_number=filing.get('fxo_id') or filing.get('filing_id', ''),
            market_id=MARKET_ID
        )

    async def close(self) -> None:
        """Close API client session."""
        await self.api_client.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


__all__ = ['ESEFSearcher']
