# Path: searcher/core/metadata_extractor.py
"""
Base Metadata Extractor

Universal metadata extraction for all markets.
Provides foundation for market-specific extractors.

Architecture:
- Market-agnostic core fields
- Structured output compatible with database JSONB columns
- Extensible for any XBRL-compliant market
"""

from datetime import datetime
from urllib.parse import urlparse
import re


class BaseMetadataExtractor:
    """
    Base metadata extractor for all markets.
    
    Provides universal metadata extraction that works across
    all regulatory markets (SEC, FRC, ESMA, etc.).
    
    Market-specific extractors inherit from this and add
    their specific metadata in structured JSONB format.
    """
    
    @staticmethod
    def extract_core_metadata(
        url: str,
        form_type: str,
        filing_date: str,
        company_name: str,
        market_type: str,
        market_entity_id: str
    ) -> dict[str, any]:
        """
        Extract core metadata common to ALL markets.
        
        This is the universal structure that works for every market.
        Market-specific data goes in separate structured sections.
        
        Args:
            url: Full filing URL
            form_type: Market's form type (10-K, AA, Annual Report, etc.)
            filing_date: Filing date (YYYY-MM-DD)
            company_name: Company name (exact from search)
            market_type: Market identifier (sec, frc, esma, etc.)
            market_entity_id: Market-specific entity ID (CIK, company_number, LEI, etc.)
            
        Returns:
            Core metadata dictionary compatible with database
        """
        # Parse URL components
        url_components = BaseMetadataExtractor.extract_url_components(url)
        
        # Extract filing year
        filing_year = filing_date.split('-')[0] if filing_date else ''
        
        # Core metadata (universal fields)
        core_metadata = {
            # Market identification
            'market_type': market_type,
            'market_entity_id': market_entity_id,
            
            # Company information
            'company_name': company_name,
            
            # Filing information
            'form_type': form_type,
            'filing_date': filing_date,
            'filing_year': filing_year,
            
            # URL information (universal)
            'url': url,
            'url_domain': url_components['domain'],
            'url_protocol': url_components['protocol'],
            'url_path': url_components['path'],
            
            # File information (universal)
            'filename': url_components['filename'],
            'file_extension': url_components['file_extension'],
            
            # Timestamps
            'metadata_created_at': datetime.now().isoformat(),
            
            # Status flags (for database workflow)
            'downloaded': False,
            'validated': False,
        }
        
        return core_metadata
    
    @staticmethod
    def extract_url_components(url: str) -> dict[str, str]:
        """
        Extract universal URL components.
        
        Works for any URL structure from any market.
        
        Args:
            url: Full URL
            
        Returns:
            Dictionary with URL components
        """
        parsed = urlparse(url)
        
        # Extract filename from path
        path_parts = parsed.path.strip('/').split('/')
        filename = path_parts[-1] if path_parts else ''
        
        # Extract file extension
        file_extension = ''
        if '.' in filename:
            file_extension = '.' + filename.rsplit('.', 1)[1]
        
        return {
            'protocol': parsed.scheme,
            'domain': parsed.netloc,
            'path': parsed.path,
            'filename': filename,
            'file_extension': file_extension,
            'full_url': url,
        }
    
    @staticmethod
    def _is_xbrl_file(filename_lower: str) -> bool:
        """Check if filename indicates XBRL content."""
        return any(pattern in filename_lower for pattern in ['xbrl', '-ins.xml', '_htm.zip'])

    @staticmethod
    def _get_file_category_by_extension(filename_lower: str) -> str:
        """Determine file category based on extension."""
        if filename_lower.endswith(('.htm', '.html')):
            return 'html'
        elif filename_lower.endswith('.xml'):
            return 'xml'
        elif filename_lower.endswith('.txt'):
            return 'text'
        elif filename_lower.endswith('.pdf'):
            return 'pdf'
        return 'unknown'

    @staticmethod
    def classify_file_type(filename: str) -> dict[str, any]:
        """
        Classify file type from filename.

        Universal classification that works for all markets.

        Args:
            filename: Filename to classify

        Returns:
            File classification dictionary
        """
        filename_lower = filename.lower()

        # Determine file characteristics
        is_xbrl = BaseMetadataExtractor._is_xbrl_file(filename_lower)
        is_archive = filename_lower.endswith('.zip')

        # Determine primary category
        if is_xbrl:
            file_category = 'xbrl'
        elif is_archive:
            file_category = 'archive'
        else:
            file_category = BaseMetadataExtractor._get_file_category_by_extension(filename_lower)

        return {
            'is_xbrl': is_xbrl,
            'is_archive': is_archive,
            'is_html': file_category == 'html',
            'is_xml': file_category == 'xml',
            'file_category': file_category,
        }
    
    @staticmethod
    def build_storage_structure(
        market_type: str,
        company_name: str,
        market_entity_id: str,
        filing_year: str,
        form_type: str,
        filename: str
    ) -> dict[str, str]:
        """
        Generate universal storage directory structure.
        
        Creates hierarchical structure for organized file storage
        that works for any market.
        
        Args:
            market_type: Market identifier (sec, frc, esma)
            company_name: Company name
            market_entity_id: Market-specific entity ID
            filing_year: Filing year
            form_type: Form type
            filename: File name
            
        Returns:
            Storage structure dictionary
        """
        # Sanitize company name for directory
        company_safe = re.sub(r'[^\w\s-]', '', company_name).strip()
        company_safe = re.sub(r'[-\s]+', '_', company_safe)
        
        structure = {
            'root': market_type,
            'company_dir': f"{company_safe}_{market_entity_id}",
            'year_dir': filing_year,
            'form_dir': form_type,
            'filename': filename,
            'full_path': f"{market_type}/{company_safe}_{market_entity_id}/{filing_year}/{form_type}",
        }
        
        return structure
    
    @staticmethod
    def build_database_compatible_metadata(
        core_metadata: dict[str, any],
        market_specific_metadata: dict[str, any],
        identifiers: dict[str, any],
        file_classification: dict[str, any],
        storage_structure: dict[str, str]
    ) -> dict[str, any]:
        """
        Build database-compatible metadata structure.
        
        Combines all metadata into structure that maps directly
        to database columns and JSONB fields.
        
        Args:
            core_metadata: Core universal metadata
            market_specific_metadata: Market-specific data (for JSONB)
            identifiers: Market-specific identifiers (for JSONB)
            file_classification: File classification
            storage_structure: Storage directory structure
            
        Returns:
            Complete database-compatible metadata
        """
        # Build search_metadata JSONB structure
        search_metadata = {
            'market_specific': market_specific_metadata,
            'file_classification': file_classification,
            'storage_structure': storage_structure,
            'url_components': {
                'domain': core_metadata['url_domain'],
                'protocol': core_metadata['url_protocol'],
                'path': core_metadata['url_path'],
            }
        }
        
        # Build complete record
        database_record = {
            # Core fields (map to database columns)
            'market_type': core_metadata['market_type'],
            'market_entity_id': core_metadata['market_entity_id'],
            'company_name': core_metadata['company_name'],
            'form_type': core_metadata['form_type'],
            'filing_date': core_metadata['filing_date'],
            'filing_url': core_metadata['url'],
            'filename': core_metadata['filename'],
            
            # JSONB fields
            'search_metadata': search_metadata,
            'identifiers': identifiers,
            
            # Status fields
            'downloaded': core_metadata['downloaded'],
            'validated': core_metadata['validated'],
            
            # Timestamps
            'created_at': core_metadata['metadata_created_at'],
        }
        
        return database_record


__all__ = ['BaseMetadataExtractor']