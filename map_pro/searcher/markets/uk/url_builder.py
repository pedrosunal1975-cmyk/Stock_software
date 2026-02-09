# Path: searcher/markets/uk/url_builder.py
"""
UK Companies House URL Builder

Constructs URLs for Companies House API endpoints.
All URL templates loaded from configuration (no hardcoding).
"""

from searcher.core.config_loader import ConfigLoader
from searcher.core.logger import get_logger

logger = get_logger(__name__, 'markets')


class UKURLBuilder:
    """
    Builds URLs for Companies House API.

    All URL templates come from configuration.
    Supports parameter substitution and validation.
    """

    def __init__(self, config: ConfigLoader = None):
        """
        Initialize URL builder.

        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()

        # Load URL templates from config
        self.base_url = self.config.get('uk_ch_base_url')
        self.company_url = self.config.get('uk_ch_company_url')
        self.filing_history_url = self.config.get('uk_ch_filing_history_url')
        self.document_meta_url = self.config.get('uk_ch_document_meta_url')
        self.document_content_url = self.config.get('uk_ch_document_content_url')

    def get_company_profile_url(self, company_number: str) -> str:
        """
        Get URL for company profile.

        Args:
            company_number: Company number (e.g., "00000006")

        Returns:
            str: Company profile API URL
        """
        return self.company_url.format(company_number=company_number)

    def get_filing_history_url(
        self,
        company_number: str,
        category: str = None,
        items_per_page: int = 100,
        start_index: int = 0
    ) -> str:
        """
        Get URL for filing history.

        Args:
            company_number: Company number
            category: Optional filing category filter (e.g., "accounts")
            items_per_page: Number of items per page (max 100)
            start_index: Starting index for pagination

        Returns:
            str: Filing history API URL
        """
        url = self.filing_history_url.format(company_number=company_number)

        # Add query parameters
        params = []
        if category:
            params.append(f"category={category}")
        if items_per_page != 100:
            params.append(f"items_per_page={items_per_page}")
        if start_index > 0:
            params.append(f"start_index={start_index}")

        if params:
            url += "?" + "&".join(params)

        return url

    def get_document_metadata_url(self, document_id: str) -> str:
        """
        Get URL for document metadata.

        Args:
            document_id: Document ID from filing history

        Returns:
            str: Document metadata API URL
        """
        return self.document_meta_url.format(document_id=document_id)

    def get_document_content_url(self, document_id: str) -> str:
        """
        Get URL for document content (download).

        Args:
            document_id: Document ID from filing history

        Returns:
            str: Document content API URL
        """
        return self.document_content_url.format(document_id=document_id)

    def get_search_url(self, query: str, items_per_page: int = 20) -> str:
        """
        Get URL for company search by name.

        Args:
            query: Search query (company name)
            items_per_page: Number of results per page

        Returns:
            str: Search API URL
        """
        # Search endpoint (if needed in future)
        url = f"{self.base_url}/search/companies"
        url += f"?q={query}&items_per_page={items_per_page}"
        return url
