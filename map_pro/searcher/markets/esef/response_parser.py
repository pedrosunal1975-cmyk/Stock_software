# Path: searcher/markets/esef/response_parser.py
"""
ESEF Response Parser

Parses JSON-API responses from filings.xbrl.org.
Extracts filing and entity data into standardized format.
"""

from typing import Optional

from searcher.core.logger import get_logger
from searcher.constants import LOG_PROCESS
from searcher.markets.esef.constants import (
    KEY_DATA,
    KEY_INCLUDED,
    KEY_META,
    ATTR_ATTRIBUTES,
    ATTR_RELATIONSHIPS,
    FIELD_ENTITY,
    FIELD_ENTITY_DATA,
    DEFAULT_BASE_URL,
)

logger = get_logger(__name__, 'markets')


class ESEFResponseParser:
    """
    Parses filings.xbrl.org JSON-API responses.

    Handles:
    - Filing list responses
    - Single filing responses
    - Entity relationship resolution
    - Pagination metadata extraction
    """

    def parse_filings_response(self, response: dict) -> list[dict]:
        """
        Parse filings list response.

        Args:
            response: JSON-API response dict

        Returns:
            list[dict]: Parsed filing records
        """
        if not response:
            return []

        # Extract data array
        data = response.get(KEY_DATA, [])
        if not data:
            return []

        # Build entity lookup from included resources
        entity_lookup = self._build_entity_lookup(response.get(KEY_INCLUDED, []))

        # Parse each filing
        filings = []
        for item in data:
            filing = self._parse_filing_item(item, entity_lookup)
            if filing:
                filings.append(filing)

        logger.debug(f"{LOG_PROCESS} Parsed {len(filings)} filings")
        return filings

    def _parse_filing_item(
        self,
        item: dict,
        entity_lookup: dict
    ) -> Optional[dict]:
        """
        Parse single filing item from response.

        Args:
            item: Filing item from data array
            entity_lookup: Entity ID -> entity data lookup

        Returns:
            dict: Parsed filing or None
        """
        if not item:
            return None

        # Get filing ID and type
        filing_id = item.get('id')
        filing_type = item.get('type')

        # Get attributes
        attrs = item.get(ATTR_ATTRIBUTES, {})

        # Extract core fields
        # Note: filings.xbrl.org API does NOT have: report_type, lei, entity_name
        # Those fields don't exist in the actual API response
        filing = {
            'filing_id': filing_id,
            'filing_type': filing_type,
            'fxo_id': attrs.get('fxo_id'),  # Filing index
            'country': attrs.get('country'),
            'date_added': attrs.get('date_added'),
            'period_end': attrs.get('period_end'),
            'report_url': attrs.get('report_url'),
            'viewer_url': attrs.get('viewer_url'),
            'json_url': attrs.get('json_url'),
            'package_url': attrs.get('package_url'),
            'sha256': attrs.get('sha256'),
            'processed': attrs.get('processed'),
            'error_count': attrs.get('error_count'),
            'warning_count': attrs.get('warning_count'),
        }

        # Resolve entity relationship if available
        relationships = item.get(ATTR_RELATIONSHIPS, {})
        entity_rel = relationships.get(FIELD_ENTITY, {})
        entity_data = entity_rel.get(FIELD_ENTITY_DATA, {})

        if entity_data:
            entity_id = entity_data.get('id')
            entity_type = entity_data.get('type')

            # Look up full entity data from included
            if entity_id and entity_id in entity_lookup:
                entity = entity_lookup[entity_id]
                filing['entity'] = entity
            else:
                filing['entity'] = {
                    'id': entity_id,
                    'type': entity_type
                }

        return filing

    def _build_entity_lookup(self, included: list) -> dict:
        """
        Build entity lookup from included resources.

        Args:
            included: Included resources array from response

        Returns:
            dict: Entity ID -> entity data mapping
        """
        lookup = {}

        for item in included:
            item_type = item.get('type')
            item_id = item.get('id')

            if item_type == 'entity' and item_id:
                attrs = item.get(ATTR_ATTRIBUTES, {})
                lookup[item_id] = {
                    'id': item_id,
                    'name': attrs.get('name'),
                    'lei': attrs.get('lei'),
                    'country': attrs.get('country'),
                    'identifier': attrs.get('identifier'),
                }

        return lookup

    def parse_entities_response(self, response: dict) -> list[dict]:
        """
        Parse entities list response.

        Args:
            response: JSON-API response dict

        Returns:
            list[dict]: Parsed entity records
        """
        if not response:
            return []

        # Extract data array
        data = response.get(KEY_DATA, [])
        if not data:
            return []

        # Parse each entity
        entities = []
        for item in data:
            entity = self._parse_entity_item(item)
            if entity:
                entities.append(entity)

        logger.debug(f"{LOG_PROCESS} Parsed {len(entities)} entities")
        return entities

    def _parse_entity_item(self, item: dict) -> Optional[dict]:
        """
        Parse single entity item from response.

        Args:
            item: Entity item from data array

        Returns:
            dict: Parsed entity or None
        """
        if not item:
            return None

        # Get entity API ID (from JSON:API 'id' field)
        entity_api_id = item.get('id')

        # Get attributes
        attrs = item.get(ATTR_ATTRIBUTES, {})

        return {
            'api_id': entity_api_id,  # JSON:API ID for filtering filings
            'id': entity_api_id,  # Keep for backwards compatibility
            'name': attrs.get('name'),
            'lei': attrs.get('lei') or entity_api_id,  # ID is typically the LEI
            'country': attrs.get('country'),
            'identifier': attrs.get('identifier'),
        }

    def parse_pagination(self, response: dict) -> dict:
        """
        Parse pagination metadata from response.

        Args:
            response: JSON-API response dict

        Returns:
            dict: Pagination info with total_pages, total_count, etc.
        """
        meta = response.get(KEY_META, {})

        return {
            'total_count': meta.get('total_count', 0),
            'total_pages': meta.get('total_pages', 0),
            'current_page': meta.get('current_page', 1),
            'page_size': meta.get('page_size', 25),
        }

    def get_filing_download_url(self, filing: dict) -> Optional[str]:
        """
        Get the best download URL for a filing.

        Priority (changed to prefer package for complete filing data):
        1. package_url - ZIP package with all files (xhtml + xsd + linkbases)
        2. report_url - Direct iXBRL file only (no extension taxonomy)

        Args:
            filing: Parsed filing dict

        Returns:
            str: Full download URL or None
        """
        # Prefer package URL (ZIP) - contains complete filing with:
        # - iXBRL document (xhtml)
        # - Extension taxonomy (xsd)
        # - Linkbase files (pre, cal, def, lab)
        package_url = filing.get('package_url')
        if package_url:
            return self._ensure_full_url(package_url)

        # Fallback to direct report URL (iXBRL file only)
        report_url = filing.get('report_url')
        if report_url:
            return self._ensure_full_url(report_url)

        return None

    def _ensure_full_url(self, url: str) -> str:
        """
        Ensure URL is a full URL with base domain.

        The filings.xbrl.org API returns relative paths like:
        /2138002P5RNKC5W2JZ46/2025-02-22/ESEF/GB/0/...

        This method prepends the base URL if needed.

        Args:
            url: URL or relative path

        Returns:
            str: Full URL with https://filings.xbrl.org prefix
        """
        if not url:
            return url

        # Already a full URL
        if url.startswith('http://') or url.startswith('https://'):
            return url

        # Relative path - prepend base URL
        if url.startswith('/'):
            return f"{DEFAULT_BASE_URL}{url}"

        # No leading slash - add one
        return f"{DEFAULT_BASE_URL}/{url}"


__all__ = ['ESEFResponseParser']
