# Path: searcher/markets/esef/url_builder.py
"""
ESEF URL Builder

Constructs URLs for filings.xbrl.org API endpoints.
All URL templates loaded from configuration (no hardcoding).
"""

from typing import Optional
from urllib.parse import urlencode

from searcher.core.config_loader import ConfigLoader
from searcher.core.logger import get_logger
from searcher.markets.esef.constants import (
    DEFAULT_BASE_URL,
    ENDPOINT_FILINGS,
    ENDPOINT_ENTITIES,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
)

logger = get_logger(__name__, 'markets')


class ESEFURLBuilder:
    """
    Builds URLs for filings.xbrl.org API.

    All URL templates come from configuration.
    Supports JSON-API query parameters for filtering and pagination.
    """

    def __init__(self, config: ConfigLoader = None):
        """
        Initialize URL builder.

        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()

        # Load base URL from config (fallback to default)
        self.base_url = self.config.get('esef_base_url', DEFAULT_BASE_URL)

    def get_filings_url(
        self,
        country: Optional[str] = None,
        entity_identifier: Optional[str] = None,
        period_end_from: Optional[str] = None,
        period_end_to: Optional[str] = None,
        page_number: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        include_entity: bool = True,
        sort_by: str = "-processed"
    ) -> str:
        """
        Build URL for filings endpoint with filters.

        Note: filings.xbrl.org API does NOT support filtering by report_type.
        Filter by report type client-side after fetching results.

        Args:
            country: Country code filter (e.g., 'GB', 'DE')
            entity_identifier: Entity identifier (LEI) to filter by
            period_end_from: Period end date start (YYYY-MM-DD)
            period_end_to: Period end date end (YYYY-MM-DD)
            page_number: Page number (1-indexed)
            page_size: Results per page
            include_entity: Include entity relationship data
            sort_by: Sort field (prefix with - for descending)

        Returns:
            str: Complete API URL with query parameters
        """
        url = f"{self.base_url}{ENDPOINT_FILINGS}"

        # Build query parameters
        params = {}

        # Filters (JSON-API filter syntax)
        if country:
            params['filter[country]'] = country.upper()

        if entity_identifier:
            params['filter[entity.identifier]'] = entity_identifier.upper()

        # Note: report_type filter is NOT supported by filings.xbrl.org API
        # Filtering by report type must be done client-side after fetching results

        if period_end_from:
            params['filter[period_end][gte]'] = period_end_from

        if period_end_to:
            params['filter[period_end][lte]'] = period_end_to

        # Pagination
        params['page[number]'] = page_number
        params['page[size]'] = min(page_size, MAX_PAGE_SIZE)

        # Include related entities
        if include_entity:
            params['include'] = 'entity'

        # Sorting
        if sort_by:
            params['sort'] = sort_by

        # Build URL with query string
        if params:
            url += '?' + urlencode(params)

        return url

    def get_filing_by_id_url(self, filing_id: str) -> str:
        """
        Build URL for specific filing by ID.

        Args:
            filing_id: Filing ID

        Returns:
            str: API URL for specific filing
        """
        return f"{self.base_url}{ENDPOINT_FILINGS}/{filing_id}"

    def get_entities_url(
        self,
        country: Optional[str] = None,
        name: Optional[str] = None,
        lei: Optional[str] = None,
        page_number: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE
    ) -> str:
        """
        Build URL for entities endpoint.

        Args:
            country: Country code filter
            name: Entity name filter (partial match)
            lei: LEI filter (exact match)
            page_number: Page number
            page_size: Results per page

        Returns:
            str: API URL for entities
        """
        url = f"{self.base_url}{ENDPOINT_ENTITIES}"

        params = {}

        if country:
            params['filter[country]'] = country.upper()

        if name:
            params['filter[name]'] = name

        if lei:
            params['filter[lei]'] = lei.upper()

        params['page[number]'] = page_number
        params['page[size]'] = min(page_size, MAX_PAGE_SIZE)

        if params:
            url += '?' + urlencode(params)

        return url

    def get_entity_by_lei_url(self, lei: str) -> str:
        """
        Build URL for entity by LEI.

        Args:
            lei: Legal Entity Identifier

        Returns:
            str: API URL for entity
        """
        return f"{self.base_url}{ENDPOINT_ENTITIES}/{lei.upper()}"


__all__ = ['ESEFURLBuilder']
