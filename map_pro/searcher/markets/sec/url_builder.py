# Path: searcher/markets/sec/url_builder.py
"""
SEC URL Builder

Constructs SEC API URLs with proper formatting.
All base URLs come from configuration.
"""

from searcher.core.config_loader import ConfigLoader


class SECURLBuilder:
    """
    Builds SEC API URLs.
    
    Handles CIK and accession number formatting.
    All base URLs loaded from configuration.
    """
    
    def __init__(self, config: ConfigLoader = None):
        """
        Initialize URL builder.
        
        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
    
    def build_submissions_url(self, cik: str) -> str:
        """
        Build submissions.json URL for a CIK.
        
        Args:
            cik: CIK number (will be padded to 10 digits)
            
        Returns:
            Full submissions.json URL
        """
        template = self.config.get('sec_submissions_url')
        formatted_cik = self._format_cik_for_url(cik)
        return template.format(cik=formatted_cik)
    
    def build_filing_index_url(self, cik: str, accession: str) -> str:
        """
        Build index.json URL for a filing.
        
        Args:
            cik: CIK number
            accession: Accession number
            
        Returns:
            Full index.json URL
        """
        formatted_cik = self._strip_cik_padding(cik)
        formatted_accession = self._format_accession_for_url(accession)
        
        archives_base = self.config.get('sec_archives_base_url')
        return f"{archives_base}{formatted_cik}/{formatted_accession}/index.json"
    
    def build_file_download_url(self, cik: str, accession: str, filename: str) -> str:
        """
        Build file download URL.
        
        Args:
            cik: CIK number
            accession: Accession number
            filename: File name
            
        Returns:
            Full file download URL
        """
        formatted_cik = self._strip_cik_padding(cik)
        formatted_accession = self._format_accession_for_url(accession)
        
        archives_base = self.config.get('sec_archives_base_url')
        return f"{archives_base}{formatted_cik}/{formatted_accession}/{filename}"
    
    def build_company_tickers_url(self) -> str:
        """
        Build company_tickers.json URL.
        
        Returns:
            Company tickers URL
        """
        return self.config.get('sec_company_tickers_url')
    
    def _format_cik_for_url(self, cik: str) -> str:
        """
        Format CIK for URL (padded to 10 digits).
        
        Args:
            cik: CIK number
            
        Returns:
            Padded CIK (e.g., '0000320193')
        """
        from searcher.markets.sec.constants import CIK_LENGTH, CIK_PADDING_CHAR
        
        # Remove any existing padding
        cik_clean = str(cik).strip().lstrip(CIK_PADDING_CHAR)
        
        # Pad to required length
        return cik_clean.zfill(CIK_LENGTH)
    
    def _strip_cik_padding(self, cik: str) -> str:
        """
        Strip leading zeros from CIK.
        
        Args:
            cik: CIK number
            
        Returns:
            CIK without leading zeros (e.g., '320193')
        """
        from searcher.markets.sec.constants import CIK_PADDING_CHAR
        
        return str(cik).strip().lstrip(CIK_PADDING_CHAR)
    
    def _format_accession_for_url(self, accession: str) -> str:
        """
        Format accession number for URL (remove dashes).
        
        Args:
            accession: Accession number (e.g., '0000320193-24-000123')
            
        Returns:
            Formatted accession (e.g., '000032019324000123')
        """
        return accession.replace('-', '')


__all__ = ['SECURLBuilder']