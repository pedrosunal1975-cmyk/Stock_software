# Path: library/cli/library_cli.py
"""
Library CLI

Enhanced command-line interface for library management.
Provides user-friendly commands for monitoring and inspection.

Commands:
- list - List downloaded libraries
- list-pending - Show pending downloads
- stats - Show statistics
- scan - Scan specific filing
- check - Check library availability

Usage:
    from library.cli.library_cli import LibraryCLI
    
    cli = LibraryCLI()
    cli.run(args)
"""

from typing import List, Dict, Any, Optional

from library.core.logger import get_logger
from library.constants import LOG_INPUT, LOG_OUTPUT
from library.cli.constants import (
    SEPARATOR_LINE,
    INDENT_LEVEL_1,
    INDENT_LEVEL_2,
    SYMBOL_BULLET,
    HEADER_LIBRARIES,
    HEADER_PENDING,
    HEADER_STATISTICS,
    HEADER_MANUAL_INSTRUCTIONS,
    HEADER_SCANNING_FILING,
    HEADER_CHECKING_LIBRARY,
    MSG_NO_PENDING,
    MSG_LIBRARIES_BY_STATUS,
    MSG_FOUND_PENDING,
    MSG_COORDINATOR_NOT_IMPLEMENTED,
    MSG_WILL_SCAN_FILING,
    STATS_DIRECTORY_TITLE,
    STATS_DATABASE_TITLE,
    STATS_LIBRARIES_COUNT,
    STATS_MANUAL_DOWNLOADS,
    STATS_PROCESSED_FILES,
    STATS_CACHE_FILES,
    STATS_TEMP_FILES,
    LIBRARY_DISPLAY_NAME,
    LIBRARY_DISPLAY_URL,
    LIBRARY_DISPLAY_MARKETS,
    STATUS_LABEL_IN_DB,
    STATUS_LABEL_ON_DISK,
    STATUS_LABEL_FILE_COUNT,
    STATUS_LABEL_IS_READY,
    ACTION_DOWNLOAD_REQUIRED,
    ACTION_REINDEX_REQUIRED,
    ACTION_READY_TO_USE,
    MANUAL_INSTRUCTIONS_TEMPLATE,
    TAXONOMY_SOURCE_SEC,
    TAXONOMY_SOURCE_FASB,
    TAXONOMY_SOURCE_IFRS,
    TAXONOMY_SOURCE_ESMA,
    ERROR_LISTING_LIBRARIES,
    ERROR_LISTING_PENDING,
    ERROR_SHOWING_STATISTICS,
    ERROR_CHECKING_LIBRARY,
    ERROR_IMPORT_FAILED,
    ERROR_DB_INIT_FAILED,
    format_header,
    format_field,
    format_error,
)

logger = get_logger(__name__, 'cli')


class LibraryCLI:
    """
    Command-line interface for library management.
    
    Provides user-friendly commands for:
    - Listing libraries (downloaded, pending, failed)
    - Showing statistics
    - Scanning specific filings
    - Checking library availability
    
    Example:
        cli = LibraryCLI()
        
        # List all libraries
        cli.list_libraries()
        
        # Show pending downloads
        cli.list_pending()
        
        # Show statistics
        cli.show_statistics()
    """
    
    def __init__(self):
        """Initialize library CLI."""
        logger.debug(f"{LOG_INPUT} Library CLI initialized")
        
        try:
            # CRITICAL: Initialize database engine FIRST
            from database import initialize_engine
            
            logger.info(f"{LOG_INPUT} Initializing database engine")
            initialize_engine()
            logger.info(f"{LOG_OUTPUT} Database engine initialized")
            
            # Now import and create connectors
            from library.engine.db_connector import DatabaseConnector
            from library.core.data_paths import LibraryPaths
            
            self.db = DatabaseConnector()
            self.paths = LibraryPaths()
            
        except ImportError as e:
            logger.error(ERROR_IMPORT_FAILED.format(error=e))
            raise
        except Exception as e:
            logger.error(ERROR_DB_INIT_FAILED.format(error=e))
            raise
    
    def list_libraries(self, status_filter: Optional[str] = None) -> None:
        """
        List taxonomy libraries.
        
        Args:
            status_filter: Optional filter by status (active, pending, failed)
        """
        print(format_header(HEADER_LIBRARIES))
        
        try:
            counts = self.db.count_libraries_by_status()
            
            print(f"\n{MSG_LIBRARIES_BY_STATUS}")
            for status, count in counts.items():
                print(format_field(status, str(count)))
            
            print(f"\n{SEPARATOR_LINE}")
            
        except Exception as e:
            logger.error(ERROR_LISTING_LIBRARIES.format(error=e))
            print(format_error(e))
    
    def list_pending(self) -> None:
        """List pending taxonomy downloads."""
        print(format_header(HEADER_PENDING))
        
        try:
            pending = self.db.get_pending_taxonomies()
            
            if not pending:
                print(f"\n{MSG_NO_PENDING}")
            else:
                print(f"\n{MSG_FOUND_PENDING.format(count=len(pending))}\n")
                
                for lib in pending:
                    print(LIBRARY_DISPLAY_NAME.format(
                        indent=INDENT_LEVEL_1,
                        symbol=SYMBOL_BULLET,
                        name=lib['taxonomy_name'],
                        version=lib['version']
                    ))
                    print(LIBRARY_DISPLAY_URL.format(
                        indent=INDENT_LEVEL_2,
                        url=lib['download_url']
                    ))
                    print(LIBRARY_DISPLAY_MARKETS.format(
                        indent=INDENT_LEVEL_2,
                        markets=lib.get('market_types', [])
                    ))
                    print()
            
            print(SEPARATOR_LINE)
            
        except Exception as e:
            logger.error(ERROR_LISTING_PENDING.format(error=e))
            print(format_error(e))
    
    def show_statistics(self) -> None:
        """Show library statistics."""
        print(format_header(HEADER_STATISTICS))
        
        try:
            # Get directory stats
            dir_stats = self.paths.get_directory_stats()
            
            print(f"\n{STATS_DIRECTORY_TITLE}")
            print(format_field(
                STATS_LIBRARIES_COUNT,
                str(dir_stats['libraries_count'])
            ))
            print(format_field(
                STATS_MANUAL_DOWNLOADS,
                str(dir_stats['manual_downloads_count'])
            ))
            print(format_field(
                STATS_CACHE_FILES,
                str(dir_stats['cache_files_count'])
            ))
            print(format_field(
                STATS_TEMP_FILES,
                str(dir_stats['temp_files_count'])
            ))
            
            # Get database stats
            counts = self.db.count_libraries_by_status()
            
            print(f"\n{STATS_DATABASE_TITLE}")
            for status, count in counts.items():
                print(format_field(status, str(count)))
            
            print(f"\n{SEPARATOR_LINE}")
            
        except Exception as e:
            logger.error(ERROR_SHOWING_STATISTICS.format(error=e))
            print(format_error(e))
    
    def scan_filing(self, filing_id: str) -> None:
        """
        Scan specific filing for taxonomy requirements.
        
        Args:
            filing_id: Filing identifier
        """
        print(format_header(f"{HEADER_SCANNING_FILING}: {filing_id}"))
        
        # TODO: Implement when coordinator is available
        print(f"\n{MSG_COORDINATOR_NOT_IMPLEMENTED}")
        print(MSG_WILL_SCAN_FILING)
        
        print(f"\n{SEPARATOR_LINE}")
    
    def check_library(
        self,
        taxonomy_name: str,
        version: str
    ) -> None:
        """
        Check if library is available.
        
        Args:
            taxonomy_name: Taxonomy name
            version: Taxonomy version
        """
        print(format_header(f"{HEADER_CHECKING_LIBRARY}: {taxonomy_name} v{version}"))
        
        try:
            from library.engine.availability_checker import AvailabilityChecker
            
            checker = AvailabilityChecker()
            status = checker.get_library_status(taxonomy_name, version)
            
            print("\nStatus:")
            print(format_field(
                STATUS_LABEL_IN_DB,
                str(status['available_in_db'])
            ))
            print(format_field(
                STATUS_LABEL_ON_DISK,
                str(status['available_on_disk'])
            ))
            print(format_field(
                STATUS_LABEL_FILE_COUNT,
                str(status['file_count'])
            ))
            print(format_field(
                STATUS_LABEL_IS_READY,
                str(status['is_ready'])
            ))
            
            if status['requires_download']:
                print(f"\n{INDENT_LEVEL_1}{ACTION_DOWNLOAD_REQUIRED}")
            elif status['requires_reindex']:
                print(f"\n{INDENT_LEVEL_1}{ACTION_REINDEX_REQUIRED}")
            else:
                print(f"\n{INDENT_LEVEL_1}{ACTION_READY_TO_USE}")
            
            print(f"\n{SEPARATOR_LINE}")
            
        except Exception as e:
            logger.error(ERROR_CHECKING_LIBRARY.format(error=e))
            print(format_error(e))
    
    def show_manual_instructions(self) -> None:
        """Show manual download instructions."""
        print(format_header(HEADER_MANUAL_INSTRUCTIONS))
        
        print(MANUAL_INSTRUCTIONS_TEMPLATE.format(
            manual_downloads_dir=self.paths.manual_downloads,
            symbol=SYMBOL_BULLET,
            sec_url=TAXONOMY_SOURCE_SEC,
            fasb_url=TAXONOMY_SOURCE_FASB,
            ifrs_url=TAXONOMY_SOURCE_IFRS,
            esma_url=TAXONOMY_SOURCE_ESMA
        ))
        
        print(SEPARATOR_LINE)


__all__ = ['LibraryCLI']