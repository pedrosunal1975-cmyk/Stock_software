# Path: library/engine/url_resolver.py
"""
URL Resolver - CORRECTED ARCHITECTURE

Resolves namespace URIs to taxonomy library download URLs.
CRITICAL PRINCIPLE: Trust company declarations FIRST, use patterns as FALLBACK.

Architecture (CORRECT):
1. PRIMARY: Extract and construct URL directly from declared namespace URI
2. FALLBACK: Use searcher.TaxonomyRecognizer only if direct construction fails

NO HARDCODED VALUES - all configuration imported from constants.py
"""

from typing import Dict, Any, List, Set, Optional
from urllib.parse import urlparse

from library.core.logger import get_logger
from library.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT
from library.engine.constants import (
    STANDARD_AUTHORITIES,
    COMPILED_COMPANY_PATTERNS,
    RESERVED_TAXONOMY_NAMES,
    URL_PATTERN_PRIMARY,
    URL_CONSTRUCTION_PATTERNS,
    SPECIAL_NAMESPACE_PARSING,
    SPECIAL_DOWNLOAD_PATTERNS,
    VERSION_DATE_PATTERN,
    MANUAL_DOWNLOAD_REQUIRED,
    is_valid_version,
    is_company_extension,
    is_included_taxonomy,
    get_authority_transform,
    is_manual_download_required,
)

logger = get_logger(__name__, 'engine')


class URLResolver:
    """
    Resolves namespace URIs to download URLs.
    
    ARCHITECTURE: Declared URLs first, pattern matching as fallback.
    
    Key principles:
    - Trust company's declared namespaces (primary source)
    - Extract taxonomy info directly from namespace structure
    - Use TaxonomyRecognizer only as fallback
    - Skip company-specific extensions
    
    Example:
        resolver = URLResolver()
        
        # Resolve with primary + fallback
        result = resolver.resolve_namespace(
            'http://xbrl.sec.gov/dei/2024',
            use_fallback=True
        )
    """
    
    def __init__(self):
        """Initialize URL resolver."""
        logger.debug(f"{LOG_PROCESS} Initializing URL resolver")
        
        # Lazy load TaxonomyRecognizer (only if needed for fallback)
        self._recognizer = None
        
        logger.info(f"{LOG_OUTPUT} URL resolver initialized (fallback mode available)")
    
    def resolve_namespace(
        self,
        namespace: str,
        use_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Resolve namespace to taxonomy metadata with download URL.
        
        PRIMARY: Direct URL construction from namespace
        FALLBACK: TaxonomyRecognizer pattern matching (if use_fallback=True)
        
        Args:
            namespace: Taxonomy namespace URI
            use_fallback: Whether to use TaxonomyRecognizer if direct fails
            
        Returns:
            Dictionary with taxonomy metadata
        """
        logger.debug(f"{LOG_INPUT} Resolving namespace: {namespace}")
        
        # Check if company-specific extension
        if self._is_company_extension(namespace):
            logger.info(f"{LOG_OUTPUT} Skipping company extension: {namespace}")
            return self._create_company_extension_result(namespace)
        
        # PRIMARY: Try direct URL construction
        direct_result = self._construct_url_directly(namespace)
        
        # Check if this is an included taxonomy (like country, currency, etc.)
        if direct_result['recognized']:
            taxonomy_name = direct_result['taxonomy_name']
            if is_included_taxonomy(taxonomy_name):
                logger.info(
                    f"{LOG_OUTPUT} Taxonomy '{taxonomy_name}' is included in parent taxonomies "
                    f"(us-gaap/dei) - marking as included"
                )
                return self._create_included_taxonomy_result(namespace, direct_result)
        
        if direct_result['recognized']:
            logger.info(
                f"{LOG_OUTPUT} Resolved directly: {namespace} → "
                f"{direct_result['taxonomy_name']} v{direct_result['version']}"
            )
            return direct_result
        
        # FALLBACK: Use TaxonomyRecognizer if enabled
        if use_fallback:
            logger.info(f"{LOG_PROCESS} Direct construction failed, using fallback")
            fallback_result = self._resolve_with_recognizer(namespace)

            if fallback_result['recognized']:
                # Check if this is an included taxonomy (same check as for direct_result)
                taxonomy_name = fallback_result['taxonomy_name']
                if is_included_taxonomy(taxonomy_name):
                    logger.info(
                        f"{LOG_OUTPUT} Taxonomy '{taxonomy_name}' is included/built-in "
                        f"(not downloadable) - marking as included"
                    )
                    return self._create_included_taxonomy_result(namespace, fallback_result)

                logger.info(
                    f"{LOG_OUTPUT} Resolved via fallback: {namespace} → "
                    f"{fallback_result['taxonomy_name']} v{fallback_result['version']}"
                )
                return fallback_result
        
        # Could not resolve
        logger.warning(f"{LOG_OUTPUT} Could not resolve namespace: {namespace}")
        return self._create_unknown_result(namespace)
    
    def batch_resolve(
        self,
        namespaces: Set[str],
        use_fallback: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Resolve multiple namespaces.
        
        Args:
            namespaces: Set of namespace URIs
            use_fallback: Whether to use fallback for each namespace
            
        Returns:
            List of resolved metadata dictionaries
        """
        logger.info(f"{LOG_INPUT} Batch resolving {len(namespaces)} namespaces")
        
        results = []
        for namespace in namespaces:
            result = self.resolve_namespace(namespace, use_fallback=use_fallback)
            results.append(result)
        
        recognized_count = sum(1 for r in results if r['recognized'])
        logger.info(
            f"{LOG_OUTPUT} Batch resolved: {recognized_count}/{len(namespaces)} recognized"
        )
        
        return results
    
    def _is_company_extension(self, namespace: str) -> bool:
        """
        Check if namespace is a company-specific extension.
        
        Uses patterns from constants.py
        
        Args:
            namespace: Namespace URI
            
        Returns:
            True if company extension
        """
        # Parse namespace to get authority
        parsed = urlparse(namespace)
        authority = parsed.netloc
        
        # Use constants function
        return is_company_extension(namespace, authority)
    
    def _construct_url_directly(self, namespace: str) -> Dict[str, Any]:
        """
        Construct download URL directly from namespace structure.

        PRIMARY METHOD: Extract and construct URL from declared namespace.
        Uses smart authority transformation from constants.py
        Handles special namespace structures (IFRS, etc.) via SPECIAL_NAMESPACE_PARSING

        Args:
            namespace: Namespace URI

        Returns:
            Metadata dictionary with constructed URL
        """
        # Parse namespace URI
        parsed = urlparse(namespace)
        authority = parsed.netloc
        path_parts = [p for p in parsed.path.strip('/').split('/') if p]

        # Check if this authority uses special namespace parsing
        if authority in SPECIAL_NAMESPACE_PARSING:
            return self._parse_special_namespace(namespace, parsed, path_parts)

        # Standard parsing: taxonomy at position 0, version at position 1
        if len(path_parts) < 1:
            return self._create_unknown_result(namespace)

        taxonomy_name = path_parts[0] if len(path_parts) >= 1 else None
        version = path_parts[1] if len(path_parts) >= 2 else 'unknown'

        # Validate version using constants function
        if not is_valid_version(version):
            version = 'unknown'

        if not taxonomy_name or version == 'unknown':
            return self._create_unknown_result(namespace)

        # Check if taxonomy name is reserved
        if taxonomy_name.lower() in RESERVED_TAXONOMY_NAMES:
            return self._create_unknown_result(namespace)

        # Apply smart authority transformation from constants
        download_authority = get_authority_transform(authority)

        # Construct URL using pattern from constants
        download_url = URL_PATTERN_PRIMARY.format(
            authority=download_authority,
            taxonomy=taxonomy_name,
            version=version
        )

        return {
            'taxonomy_name': taxonomy_name,
            'version': version,
            'namespace': namespace,
            'download_url': download_url,
            'authority': authority,
            'source': 'direct',
            'is_company_extension': False,
            'recognized': True,
            'needs_verification': True
        }

    def _parse_special_namespace(
        self,
        namespace: str,
        parsed,
        path_parts: List[str]
    ) -> Dict[str, Any]:
        """
        Parse namespace using special rules for non-standard authorities.

        Handles authorities like IFRS that use different namespace structures.
        Configuration comes from SPECIAL_NAMESPACE_PARSING in constants.py

        Args:
            namespace: Original namespace URI
            parsed: Parsed URL object
            path_parts: List of path components

        Returns:
            Metadata dictionary with constructed URL(s)
        """
        authority = parsed.netloc
        config = SPECIAL_NAMESPACE_PARSING.get(authority, {})

        if not path_parts:
            return self._create_unknown_result(namespace)

        # Extract taxonomy name based on position
        taxonomy_position = config.get('taxonomy_position', 0)
        try:
            taxonomy_name = path_parts[taxonomy_position]
        except IndexError:
            return self._create_unknown_result(namespace)

        # Normalize taxonomy name if configured (e.g., ifrs-full -> ifrs)
        if config.get('normalize_name') and '-' in taxonomy_name:
            # Keep full name for now, but could extract base: ifrs-full -> ifrs
            pass

        # Extract version based on extraction method
        version = None
        version_extraction = config.get('version_extraction', 'standard')

        if version_extraction == 'date_year':
            # Look for date-like component and extract year
            for part in path_parts:
                match = VERSION_DATE_PATTERN.match(part)
                if match:
                    version = match.group(1)  # Extract year (e.g., 2022)
                    break
        else:
            # Standard: version at position 1
            version = path_parts[1] if len(path_parts) > 1 else None

        # Validate version
        if not version or not is_valid_version(version):
            # Try to find any 4-digit year in path parts
            for part in path_parts:
                if is_valid_version(part):
                    version = part
                    break

        if not version:
            logger.warning(
                f"{LOG_PROCESS} Could not extract version from special namespace: {namespace}"
            )
            return self._create_unknown_result(namespace)

        # Check if taxonomy name is reserved
        if taxonomy_name.lower() in RESERVED_TAXONOMY_NAMES:
            return self._create_unknown_result(namespace)

        # Get download URLs from special patterns
        download_urls = self._get_special_download_urls(authority, taxonomy_name, version)

        if not download_urls:
            # Fall back to standard pattern construction
            download_authority = get_authority_transform(authority)
            download_urls = [
                URL_PATTERN_PRIMARY.format(
                    authority=download_authority,
                    taxonomy=taxonomy_name,
                    version=version
                )
            ]

        # Check if this authority requires manual download
        manual_required = is_manual_download_required(authority)

        if manual_required:
            manual_config = MANUAL_DOWNLOAD_REQUIRED.get(authority, {})
            logger.warning(
                f"{LOG_PROCESS} {taxonomy_name} v{version} likely requires manual download: "
                f"{manual_config.get('reason', 'CDN protection')}"
            )

        logger.info(
            f"{LOG_PROCESS} Parsed special namespace: {namespace} -> "
            f"{taxonomy_name} v{version} ({len(download_urls)} candidate URLs)"
            f"{' [MANUAL DOWNLOAD LIKELY REQUIRED]' if manual_required else ''}"
        )

        return {
            'taxonomy_name': taxonomy_name,
            'version': version,
            'namespace': namespace,
            'download_url': download_urls[0],  # Primary URL
            'alternative_urls': download_urls[1:] if len(download_urls) > 1 else [],
            'authority': authority,
            'source': 'special',
            'is_company_extension': False,
            'recognized': True,
            'needs_verification': True,
            'manual_download_required': manual_required,
            'manual_download_page': MANUAL_DOWNLOAD_REQUIRED.get(authority, {}).get('download_page', ''),
        }

    def _get_special_download_urls(
        self,
        authority: str,
        taxonomy_name: str,
        version: str
    ) -> List[str]:
        """
        Get download URLs for special authorities.

        Uses SPECIAL_DOWNLOAD_PATTERNS from constants.py

        Args:
            authority: Namespace authority domain
            taxonomy_name: Extracted taxonomy name
            version: Extracted version

        Returns:
            List of candidate download URLs to try
        """
        patterns = SPECIAL_DOWNLOAD_PATTERNS.get(authority, [])

        urls = []
        for pattern in patterns:
            try:
                url = pattern.format(
                    taxonomy=taxonomy_name,
                    version=version
                )
                urls.append(url)
            except KeyError:
                # Pattern requires fields we don't have
                continue

        return urls
    
    def _resolve_with_recognizer(self, namespace: str) -> Dict[str, Any]:
        """
        Resolve namespace using TaxonomyRecognizer (fallback).
        
        Args:
            namespace: Namespace URI
            
        Returns:
            Metadata dictionary from TaxonomyRecognizer
        """
        # Lazy load recognizer
        if self._recognizer is None:
            try:
                from searcher.engine import TaxonomyRecognizer
                self._recognizer = TaxonomyRecognizer()
                logger.info(f"{LOG_PROCESS} Loaded TaxonomyRecognizer for fallback")
            except ImportError as e:
                logger.error(f"Cannot import TaxonomyRecognizer: {e}")
                return self._create_unknown_result(namespace)
        
        # Use recognizer to match namespace
        try:
            result = self._recognizer.match_namespace(namespace)
            
            if result and result.get('recognized'):
                # Add source flag
                result['source'] = 'fallback'
                result['is_company_extension'] = False
                return result
            else:
                return self._create_unknown_result(namespace)
                
        except Exception as e:
            logger.error(f"Error in TaxonomyRecognizer: {e}")
            return self._create_unknown_result(namespace)
    
    def _create_company_extension_result(self, namespace: str) -> Dict[str, Any]:
        """Create result for company-specific extension (skip)."""
        return {
            'taxonomy_name': 'company-extension',
            'version': 'unknown',
            'namespace': namespace,
            'download_url': '',
            'authority': '',
            'source': 'skipped',
            'is_company_extension': True,
            'recognized': False
        }
    
    def _create_included_taxonomy_result(self, namespace: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create result for included taxonomy (bundled in parent taxonomies).
        
        These taxonomies don't need separate downloads - they're already
        included in us-gaap or dei.
        """
        return {
            'taxonomy_name': metadata['taxonomy_name'],
            'version': metadata['version'],
            'namespace': namespace,
            'download_url': '',  # No separate download needed
            'authority': metadata['authority'],
            'source': 'included',
            'is_company_extension': False,
            'is_included_taxonomy': True,
            'recognized': True,  # We recognize it, but don't download separately
            'included_in': ['us-gaap', 'dei'],  # Parent taxonomies
        }
    
    def _create_unknown_result(self, namespace: str) -> Dict[str, Any]:
        """Create result for unrecognized namespace."""
        return {
            'taxonomy_name': 'unknown',
            'version': 'unknown',
            'namespace': namespace,
            'download_url': '',
            'authority': '',
            'source': 'unknown',
            'is_company_extension': False,
            'recognized': False
        }
    
    def get_required_libraries(
        self,
        namespaces: Set[str],
        use_fallback: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get list of required taxonomy libraries from namespaces.
        
        Filters out:
        - Company extensions
        - Unrecognized namespaces
        - Duplicates
        
        Args:
            namespaces: Set of namespace URIs from parsed.json
            use_fallback: Whether to use fallback resolution
            
        Returns:
            List of unique taxonomy library metadata
        """
        logger.info(f"{LOG_INPUT} Getting required libraries from {len(namespaces)} namespaces")
        
        # Resolve all namespaces
        all_results = self.batch_resolve(namespaces, use_fallback=use_fallback)
        
        # Filter out company extensions, unknowns, and included taxonomies
        libraries = [
            r for r in all_results
            if r['recognized'] 
            and not r['is_company_extension']
            and not r.get('is_included_taxonomy', False)  # Skip included taxonomies
        ]
        
        # Deduplicate by (taxonomy_name, version)
        unique_libs = {}
        for lib in libraries:
            key = (lib['taxonomy_name'], lib['version'])
            if key not in unique_libs:
                unique_libs[key] = lib
        
        result_list = list(unique_libs.values())
        
        logger.info(f"{LOG_OUTPUT} Required libraries: {len(result_list)}")
        
        return result_list


__all__ = ['URLResolver']