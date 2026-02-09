# Path: searcher/engine/taxonomy_recognizer.py
"""
Taxonomy Recognizer - 100% AGNOSTIC

Pattern-based taxonomy namespace recognition.
NO hardcoded taxonomy names, URLs, or market-specific logic.

Architecture:
- Uses configurable regex patterns from constants
- Extracts taxonomy info from namespace structure
- Generates download URLs from templates
- Creates alternative URLs from patterns
- Works for ANY taxonomy from ANY authority
"""

from typing import Optional
import re

from searcher.core.logger import get_logger
from searcher.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT
from searcher.engine.constants import (
    compile_patterns,
    ALTERNATIVE_URL_TEMPLATES,
    get_authority_variants,
    infer_market_type,
)

logger = get_logger(__name__, 'engine')


class TaxonomyRecognizer:
    """
    100% AGNOSTIC taxonomy recognizer.
    
    Uses pattern matching to recognize ANY taxonomy namespace.
    NO hardcoded taxonomy knowledge.
    
    Example:
        recognizer = TaxonomyRecognizer()
        
        # Works for ANY taxonomy
        result = recognizer.match_namespace('http://fasb.org/us-gaap/2024')
        result = recognizer.match_namespace('http://ifrs.org/taxonomy/2023')
        result = recognizer.match_namespace('http://custom.org/my-taxonomy/2025')
        
        # All return same structure:
        {
            'taxonomy_name': str,    # Extracted from namespace
            'version': str,           # Extracted from namespace
            'authority': str,         # Extracted from namespace
            'namespace': str,         # Original namespace
            'download_url': str,      # Generated from template
            'market_type': str,       # Inferred from authority
            'recognized': True
        }
    """
    
    def __init__(self):
        """Initialize taxonomy recognizer with compiled patterns."""
        self.patterns = compile_patterns()
        logger.info(f"{LOG_INPUT} TaxonomyRecognizer initialized with {len(self.patterns)} patterns")
    
    def match_namespace(self, namespace_uri: str) -> Optional[dict[str, any]]:
        """
        Match namespace URI to taxonomy metadata.
        
        100% AGNOSTIC - works for ANY taxonomy.
        Extracts info from namespace structure using patterns.
        
        Args:
            namespace_uri: Namespace URI (e.g., 'http://fasb.org/us-gaap/2024')
            
        Returns:
            Dictionary with taxonomy metadata or None if no pattern matches
        """
        logger.debug(f"{LOG_INPUT} Matching namespace: {namespace_uri}")
        
        # Try each pattern
        for pattern_config in self.patterns:
            match = pattern_config['compiled'].search(namespace_uri)
            
            if match:
                # Extract components from pattern groups
                authority = match.group(pattern_config['authority_group'])
                taxonomy_name = match.group(pattern_config['taxonomy_group'])
                version = match.group(pattern_config['version_group'])
                
                # Clean taxonomy name (remove path separators if any)
                taxonomy_name = taxonomy_name.strip('/').lower()
                
                # Generate download URL from template
                download_url = self._generate_download_url(
                    pattern_config['url_template'],
                    authority,
                    taxonomy_name,
                    version
                )
                
                # Infer market type
                market_type = infer_market_type(authority)
                
                result = {
                    'taxonomy_name': taxonomy_name,
                    'version': version,
                    'namespace': namespace_uri,
                    'download_url': download_url,
                    'market_type': market_type,
                    'authority': authority,
                    'recognized': True,
                }
                
                logger.info(
                    f"{LOG_OUTPUT} Matched: {namespace_uri} -> "
                    f"{taxonomy_name} v{version} ({market_type})"
                )
                
                return result
        
        # No pattern matched
        logger.warning(f"{LOG_OUTPUT} No pattern matched for namespace: {namespace_uri}")
        
        return {
            'taxonomy_name': 'unknown',
            'version': 'unknown',
            'namespace': namespace_uri,
            'download_url': '',
            'market_type': 'unknown',
            'authority': '',
            'recognized': False,
            'error': 'No matching pattern found'
        }
    
    def get_alternative_urls(
        self,
        taxonomy_name: str,
        version: str,
        namespace: str
    ) -> list[str]:
        """
        Generate alternative download URLs for ANY taxonomy.
        
        100% AGNOSTIC - uses templates, not hardcoded URLs.
        
        Args:
            taxonomy_name: Taxonomy name (extracted from namespace)
            version: Version (extracted from namespace)
            namespace: Original namespace URI
            
        Returns:
            List of alternative URLs to try
        """
        logger.debug(
            f"{LOG_INPUT} Generating alternative URLs for {taxonomy_name} v{version}"
        )
        
        # Extract authority from namespace
        authority = self._extract_authority_from_namespace(namespace)
        
        if not authority:
            logger.warning(f"Could not extract authority from: {namespace}")
            return []
        
        # Get authority variants
        authority_variants = get_authority_variants(authority)
        
        # Generate alternative URLs using templates
        alternative_urls = []
        
        for template in ALTERNATIVE_URL_TEMPLATES:
            for auth_variant in authority_variants:
                url = self._generate_download_url(
                    template,
                    auth_variant,
                    taxonomy_name,
                    version
                )
                
                # Don't add duplicates
                if url and url not in alternative_urls:
                    alternative_urls.append(url)
        
        # Remove original namespace if it's in the list
        alternative_urls = [url for url in alternative_urls if url != namespace]
        
        logger.info(
            f"{LOG_OUTPUT} Generated {len(alternative_urls)} alternative URLs for "
            f"{taxonomy_name} v{version}"
        )
        
        return alternative_urls
    
    def _generate_download_url(
        self,
        template: str,
        authority: str,
        taxonomy_name: str,
        version: str
    ) -> str:
        """
        Generate download URL from template.
        
        Replaces placeholders: {authority}, {taxonomy}, {version}
        
        Args:
            template: URL template with placeholders
            authority: Authority domain
            taxonomy_name: Taxonomy name
            version: Version
            
        Returns:
            Generated URL
        """
        try:
            url = template.format(
                authority=authority,
                taxonomy=taxonomy_name,
                version=version
            )
            return url
        except Exception as e:
            logger.warning(f"Error generating URL from template '{template}': {e}")
            return ''
    
    def _extract_authority_from_namespace(self, namespace: str) -> str:
        """
        Extract authority domain from namespace URI.
        
        Args:
            namespace: Namespace URI
            
        Returns:
            Authority domain
        """
        # Match common URL patterns
        pattern = r'https?://(?:www\.|xbrl\.)?([^/]+)'
        match = re.search(pattern, namespace, re.IGNORECASE)
        
        if match:
            return match.group(1)
        
        return ''
    
    def batch_match(self, namespace_uris: list[str]) -> list[dict[str, any]]:
        """
        Match multiple namespaces at once.
        
        Args:
            namespace_uris: List of namespace URIs
            
        Returns:
            List of match results
        """
        logger.debug(f"{LOG_INPUT} Batch matching {len(namespace_uris)} namespaces")
        
        results = []
        for namespace in namespace_uris:
            result = self.match_namespace(namespace)
            if result:
                results.append(result)
        
        recognized_count = sum(1 for r in results if r.get('recognized', False))
        
        logger.info(
            f"{LOG_OUTPUT} Batch match complete: "
            f"{recognized_count}/{len(results)} recognized"
        )
        
        return results
    
    def get_unrecognized(self, namespace_uris: list[str]) -> list[str]:
        """
        Get list of unrecognized namespaces.
        
        Useful for identifying company extensions or unknown taxonomies.
        
        Args:
            namespace_uris: List of namespace URIs
            
        Returns:
            List of unrecognized namespace URIs
        """
        results = self.batch_match(namespace_uris)
        
        unrecognized = [
            r['namespace'] for r in results
            if not r.get('recognized', False)
        ]
        
        logger.info(f"{LOG_OUTPUT} Found {len(unrecognized)} unrecognized namespaces")
        
        return unrecognized


__all__ = ['TaxonomyRecognizer']