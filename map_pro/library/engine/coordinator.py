# Path: library/engine/coordinator.py
"""
Library Coordinator

Main orchestration for library module.
100% AGNOSTIC - coordinates other components without hardcoded logic.

Architecture:
- Discovers filings (FilingScanner)
- Extracts namespaces (NamespaceExtractor)
- Resolves to libraries (URLResolver → searcher)
- Checks availability (AvailabilityChecker)
- Saves missing libraries (DatabaseConnector → searcher)
- Caches results (ResultCache)

NO hardcoded taxonomy knowledge - pure orchestration.

Usage:
    from library.engine.coordinator import LibraryCoordinator
    
    coordinator = LibraryCoordinator()
    
    # Process single filing
    result = coordinator.process_filing('sec/Apple_Inc/10-K/0001234567')
    
    # Process all new filings
    results = coordinator.process_new_filings()
"""

from typing import List, Dict, Any, Optional, Set
from pathlib import Path

from library.core.config_loader import LibraryConfig
from library.core.data_paths import LibraryPaths
from library.core.logger import get_logger
from library.engine.metadata_extractor import MetadataExtractor
from library.loaders.parsed_reader import ParsedReader
from library.loaders.taxonomy_reader import TaxonomyReader
from library.engine.url_resolver import URLResolver
from library.engine.availability_checker import AvailabilityChecker
from library.engine.db_connector import DatabaseConnector
from library.engine.result_cache import ResultCache
from library.models.filing_entry import FilingEntry
from library.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT

logger = get_logger(__name__, 'engine')


class LibraryCoordinator:
    """
    Main library workflow orchestrator.
    
    100% AGNOSTIC - delegates all taxonomy-specific operations.
    
    Responsibilities:
    - Coordinate workflow across components
    - Handle errors gracefully
    - Cache results
    - Track processed filings
    
    Example:
        coordinator = LibraryCoordinator()
        
        # Process all new filings
        results = coordinator.process_new_filings()
        
        # Process specific filing
        result = coordinator.process_filing_by_id('filing_id')
    """
    
    def __init__(
        self,
        config: Optional[LibraryConfig] = None,
        paths: Optional[LibraryPaths] = None
    ):
        """
        Initialize library coordinator.
        
        Args:
            config: Optional LibraryConfig instance
            paths: Optional LibraryPaths instance
        """
        logger.info(f"{LOG_PROCESS} Initializing library coordinator")
        
        self.config = config if config else LibraryConfig()
        self.paths = paths if paths else LibraryPaths(self.config)
        
        # Initialize components
        self.metadata_extractor = MetadataExtractor(self.config)
        self.parsed_reader = ParsedReader(self.config)
        self.taxonomy_reader = TaxonomyReader(self.config)
        self.resolver = URLResolver()
        self.checker = AvailabilityChecker(self.config, self.paths)
        self.db = DatabaseConnector(self.config)
        self.cache = ResultCache(self.config)
        
        # Track processed filings
        self._processed_filings: Set[str] = set()
        
        logger.info(f"{LOG_OUTPUT} Library coordinator initialized")
    
    def process_filing(self, filing: FilingEntry) -> Dict[str, Any]:
        """
        Process single filing for taxonomy requirements.
        
        Workflow:
        1. Check cache
        2. Extract namespaces
        3. Resolve to libraries (delegates to searcher)
        4. Check availability (dual verification)
        5. Save missing libraries (delegates to searcher)
        6. Cache result
        
        Args:
            filing: FilingEntry object
            
        Returns:
            Dictionary with processing result
        """
        filing_id = filing.filing_id
        
        logger.info(f"{LOG_INPUT} Processing filing: {filing_id}")
        
        # Check cache first
        cached = self.cache.get_cached_result(filing_id)
        if cached:
            logger.info(f"{LOG_OUTPUT} Using cached result for {filing_id}")
            return cached
        
        try:
            # Step 1: Extract namespaces
            logger.debug(f"{LOG_PROCESS} Extracting namespaces from {filing_id}")
            filing_info = self.parsed_reader.read_file(filing.parsed_json_path)
            
            if not filing_info.success:
                result = {
                    'success': False,
                    'filing_id': filing_id,
                    'error': filing_info.error,
                }
                return result
            
            namespaces = filing_info.namespaces
            
            if not namespaces:
                result = {
                    'success': True,
                    'filing_id': filing_id,
                    'namespaces_detected': [],
                    'libraries_required': [],
                    'libraries_ready': True,
                    'message': 'No taxonomy namespaces detected',
                }
                self.cache.cache_result(filing_id, result)
                return result
            
            logger.info(f"{LOG_OUTPUT} Detected {len(namespaces)} namespaces")
            
            # Step 2: Resolve to libraries (delegates to searcher)
            logger.debug(f"{LOG_PROCESS} Resolving namespaces to libraries")
            required_libraries = self.resolver.get_required_libraries(namespaces)
            
            logger.info(f"{LOG_OUTPUT} Requires {len(required_libraries)} libraries")
            
            # Step 3: DUAL VERIFICATION - Check database AND physical files
            logger.debug(f"{LOG_PROCESS} Running dual verification (DB + Physical)")
            availability = self._dual_verification(required_libraries)
            
            logger.info(
                f"{LOG_OUTPUT} Dual verification: "
                f"{availability['available_count']} available, "
                f"{availability['missing_count']} missing"
            )
            
            if availability['reconciliation_updates'] > 0:
                logger.info(
                    f"{LOG_OUTPUT} Reconciled {availability['reconciliation_updates']} "
                    f"database/physical mismatches"
                )
            
            # Step 4: Save missing libraries (delegates to searcher)
            saved_count = 0
            if availability['missing_libraries']:
                logger.debug(f"{LOG_PROCESS} Saving missing libraries to database")
                
                for library in availability['missing_libraries']:
                    save_result = self.db.save_taxonomy(library)
                    if save_result['success']:
                        saved_count += 1
                
                logger.info(f"{LOG_OUTPUT} Saved {saved_count} missing libraries")
            
            # Build result
            result = {
                'success': True,
                'filing_id': filing_id,
                'namespaces_detected': list(namespaces),
                'libraries_required': [
                    f"{lib['taxonomy_name']} v{lib['version']}"
                    for lib in required_libraries
                ],
                'libraries_ready': availability['missing_count'] == 0,
                'libraries_available': availability['available_count'],
                'libraries_missing': availability['missing_count'],
                'libraries_saved': saved_count,
                'reconciliation_updates': availability.get('reconciliation_updates', 0),
                'db_only_count': availability.get('db_only_count', 0),
                'physical_only_count': availability.get('physical_only_count', 0),
            }
            
            # Cache successful result
            self.cache.cache_result(filing_id, result)
            
            logger.info(f"{LOG_OUTPUT} Successfully processed {filing_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing filing {filing_id}: {e}")
            
            result = {
                'success': False,
                'filing_id': filing_id,
                'error': str(e),
            }
            
            return result
    
    def process_new_filings(self) -> List[Dict[str, Any]]:
        """
        Process all filings not yet processed.
        
        Returns:
            List of processing results
        """
        logger.info(f"{LOG_INPUT} Processing new filings")
        
        # Discover all filings
        all_filings = self.metadata_extractor.extract_all()
        
        # Filter to new filings
        new_filings = [
            filing for filing in all_filings
            if filing.filing_id not in self._processed_filings
        ]
        
        logger.info(f"{LOG_OUTPUT} Found {len(new_filings)} new filings to process")
        
        # Process each filing
        results = []
        for filing in new_filings:
            result = self.process_filing(filing)
            results.append(result)
            
            # Track as processed
            if result['success']:
                self._processed_filings.add(filing.filing_id)
        
        logger.info(f"{LOG_OUTPUT} Processed {len(results)} new filings")
        
        return results
    
    def process_filing_by_id(self, filing_id: str) -> Optional[Dict[str, Any]]:
        """
        Process specific filing by ID.
        
        Args:
            filing_id: Filing identifier (market/company/form/accession)
            
        Returns:
            Processing result or None if not found
        """
        logger.info(f"{LOG_INPUT} Processing filing by ID: {filing_id}")
        
        # Find filing
        all_filings = self.metadata_extractor.extract_all()
        filing = next((f for f in all_filings if f.filing_id == filing_id), None)
        
        if not filing:
            logger.warning(f"{LOG_OUTPUT} Filing not found: {filing_id}")
            return None
        
        # Process it
        return self.process_filing(filing)
    
    def _dual_verification(
        self,
        required_libraries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        DUAL VERIFICATION: Check both database AND physical files.
        
        Critical for integrity:
        - Database might say library exists but files are deleted
        - Files might exist but database doesn't know
        - Files might be incomplete (below threshold)
        
        Args:
            required_libraries: List of library metadata from url_resolver
            
        Returns:
            Dictionary with verification results and reconciliation
        """
        logger.debug(f"{LOG_PROCESS} Running dual verification (DB + Physical)")
        
        # Step 1: Check database
        db_availability = self.checker.check_library_availability(required_libraries)
        
        # Step 2: Check physical files
        physical_verifications = self.taxonomy_reader.verify_libraries()
        
        # Build lookup of physically available libraries
        physical_complete = {
            v.directory_name: v
            for v in physical_verifications
            if v.is_complete
        }
        
        logger.debug(
            f"{LOG_OUTPUT} DB reports {db_availability['available_count']} available, "
            f"Physical has {len(physical_complete)} complete"
        )
        
        # Step 3: Reconcile - find mismatches
        truly_available = []
        missing_libraries = []
        needs_db_update = []
        
        for library in required_libraries:
            lib_name = library.get('taxonomy_name', '')
            lib_version = library.get('version', '')
            lib_key = f"{lib_name}-{lib_version}"
            
            # Check if in database
            in_db = any(
                lib.get('taxonomy_name') == lib_name and lib.get('version') == lib_version
                for lib in db_availability.get('available_libraries', [])
            )
            
            # Check if physically complete
            # Try multiple naming patterns
            physical_exists = False
            for potential_name in [lib_key, lib_name, f"{lib_name}-{lib_version}"]:
                if potential_name in physical_complete:
                    physical_exists = True
                    break
            
            # Reconciliation logic
            if in_db and physical_exists:
                # Perfect - both agree
                truly_available.append(library)
            elif in_db and not physical_exists:
                # Database says yes, but files missing - CRITICAL MISMATCH
                logger.warning(
                    f"Database claims {lib_key} is available but files are missing/incomplete"
                )
                missing_libraries.append(library)
                needs_db_update.append({
                    'library': library,
                    'action': 'mark_as_missing',
                    'reason': 'files_not_found'
                })
            elif not in_db and physical_exists:
                # Files exist but database doesn't know - update database
                logger.info(f"Found {lib_key} on disk but not in database - will register")
                truly_available.append(library)
                needs_db_update.append({
                    'library': library,
                    'action': 'register_found',
                    'reason': 'files_exist_not_in_db'
                })
            else:
                # Neither - truly missing
                missing_libraries.append(library)
        
        # Step 4: Apply reconciliation updates
        for update in needs_db_update:
            library = update['library']
            action = update['action']
            
            if action == 'register_found':
                # Register in database
                self.db.save_taxonomy(library)
                logger.info(
                    f"{LOG_OUTPUT} Registered {library['taxonomy_name']} "
                    f"v{library['version']} (found on disk)"
                )
            elif action == 'mark_as_missing':
                # Could mark as inactive in database
                # For now just log - db_connector can add this method later
                logger.warning(
                    f"{LOG_OUTPUT} Mismatch: {library['taxonomy_name']} "
                    f"v{library['version']} in DB but files missing"
                )
        
        result = {
            'available_libraries': truly_available,
            'missing_libraries': missing_libraries,
            'available_count': len(truly_available),
            'missing_count': len(missing_libraries),
            'reconciliation_updates': len(needs_db_update),
            'db_only_count': sum(1 for u in needs_db_update if u['action'] == 'mark_as_missing'),
            'physical_only_count': sum(1 for u in needs_db_update if u['action'] == 'register_found'),
        }
        
        logger.info(
            f"{LOG_OUTPUT} Dual verification complete: "
            f"{result['available_count']} truly available, "
            f"{result['missing_count']} missing, "
            f"{result['reconciliation_updates']} reconciled"
        )
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get coordinator statistics.
        
        Returns:
            Dictionary with statistics
        """
        cache_stats = self.cache.get_statistics()
        
        return {
            'processed_filings_count': len(self._processed_filings),
            'cache_stats': cache_stats,
        }
    
    def reset_processed_cache(self) -> None:
        """Reset the processed filings tracker."""
        count = len(self._processed_filings)
        self._processed_filings.clear()
        logger.info(f"{LOG_OUTPUT} Reset processed filings cache ({count} entries)")


__all__ = ['LibraryCoordinator']