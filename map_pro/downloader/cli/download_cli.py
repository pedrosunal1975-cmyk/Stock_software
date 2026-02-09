# Path: downloader/cli/download_cli.py
"""
Download CLI Interface

Interactive command-line interface for downloading XBRL filings.
Lists pending AND failed downloads from database and executes download workflow.

Architecture:
- Query database for downloadable filings (pending OR failed)
- Display clean list with status indicator
- User selects by number
- Trigger DownloadCoordinator
- IPO logging throughout

Usage:
    python download.py
"""

import asyncio
from typing import Optional, List
from datetime import datetime

from downloader.core.logger import get_logger
from downloader.engine.coordinator import DownloadCoordinator
from downloader.engine.db_operations import DatabaseRepository
from downloader.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT

logger = get_logger(__name__, 'cli')


class DownloadCLI:
    """
    Interactive CLI for downloading XBRL filings.
    
    Workflow:
    1. Query database for downloadable filings (pending OR failed)
    2. Display list to user (company, form, date, status)
    3. User selects filing(s) by number
    4. Execute download via coordinator
    5. Display results
    
    Example:
        cli = DownloadCLI()
        await cli.run()
    """
    
    def __init__(self):
        """Initialize download CLI."""
        self.db_repo = DatabaseRepository()
        self.coordinator = DownloadCoordinator()
    
    async def run(self):
        """
        Run interactive CLI session.
        
        Main entry point for CLI interface.
        """
        logger.info(f"{LOG_INPUT} Starting Download CLI")
        
        try:
            # Get downloadable filings (pending + failed)
            downloadable = self._get_downloadable_filings()
            
            if not downloadable:
                print("\nNo downloadable filings found in database.")
                print("Run the searcher module first to populate filings.")
                return
            
            # Display options
            self._display_downloadable_filings(downloadable)
            
            # Get user selection
            selection = self._get_user_selection(len(downloadable))
            
            if selection is None:
                print("\nDownload cancelled.")
                return
            
            # Download selected filing(s)
            await self._download_filings(downloadable, selection)
        
        except KeyboardInterrupt:
            print("\n\nDownload interrupted by user.")
            logger.info(f"{LOG_OUTPUT} User interrupted download")
        
        except Exception as e:
            print(f"\nError: {e}")
            logger.error(f"CLI error: {e}", exc_info=True)
        
        finally:
            await self.coordinator.close()
    
    def _get_downloadable_filings(self, limit: int = 100) -> List:
        """
        Get downloadable filings from database (pending OR failed).
        
        Args:
            limit: Maximum number to retrieve
            
        Returns:
            List of FilingSearch records with 'pending' or 'failed' status
        """
        logger.info(f"{LOG_PROCESS} Querying downloadable filings...")
        
        downloadable = self.db_repo.get_pending_downloads(limit=limit)
        
        logger.info(f"{LOG_OUTPUT} Found {len(downloadable)} downloadable filings")
        
        return downloadable
    
    def _display_downloadable_filings(self, filings: List):
        """
        Display downloadable filings to user.
        
        Shows: company name, form type, filing date, status (PENDING/FAILED).
        Uses pre-loaded entity data from db_repo.
        
        Args:
            filings: List of FilingSearch records with pre-loaded entity data
        """
        print("\n" + "=" * 90)
        print("DOWNLOADABLE FILINGS (Pending & Failed)")
        print("=" * 90)
        print(f"\n{'#':<5} {'Company':<40} {'Form':<10} {'Date':<12} {'Status':<10}")
        print("-" * 90)
        
        for i, filing in enumerate(filings, 1):
            # Use pre-loaded company name (from db_operations session handling)
            company_name = getattr(filing, '_company_name', 'UNKNOWN')
            
            # Truncate company name if too long
            if len(company_name) > 38:
                company_name = company_name[:35] + "..."
            
            # Format date
            date_str = filing.filing_date.strftime('%Y-%m-%d') if filing.filing_date else 'N/A'
            
            # Format status
            status = filing.download_status.upper() if filing.download_status else 'UNKNOWN'
            
            print(f"{i:<5} {company_name:<40} {filing.form_type:<10} {date_str:<12} {status:<10}")
        
        print("=" * 90)
    
    def _get_user_selection(self, max_options: int) -> Optional[List[int]]:
        """
        Get user selection from displayed options.
        
        Args:
            max_options: Maximum valid option number
            
        Returns:
            List of selected indices (0-based) or None if cancelled
        """
        print(f"\nEnter selection:")
        print(f"  - Single number (1-{max_options})")
        print(f"  - Range (e.g., 1-5)")
        print(f"  - Multiple (e.g., 1,3,5)")
        print(f"  - 'all' for all filings")
        print(f"  - 'q' to quit")
        
        while True:
            try:
                choice = input("\nSelection: ").strip().lower()
                
                # Quit
                if choice in ('q', 'quit', 'exit'):
                    return None
                
                # All
                if choice == 'all':
                    return list(range(max_options))
                
                # Parse selection
                selected = []
                
                # Handle ranges (e.g., "1-5")
                if '-' in choice and ',' not in choice:
                    parts = choice.split('-')
                    if len(parts) == 2:
                        start = int(parts[0])
                        end = int(parts[1])
                        if 1 <= start <= end <= max_options:
                            selected = list(range(start - 1, end))
                        else:
                            print(f"Invalid range. Must be between 1 and {max_options}")
                            continue
                
                # Handle multiple (e.g., "1,3,5")
                elif ',' in choice:
                    numbers = [int(n.strip()) for n in choice.split(',')]
                    if all(1 <= n <= max_options for n in numbers):
                        selected = [n - 1 for n in numbers]
                    else:
                        print(f"Invalid selection. All numbers must be between 1 and {max_options}")
                        continue
                
                # Handle single number
                else:
                    num = int(choice)
                    if 1 <= num <= max_options:
                        selected = [num - 1]
                    else:
                        print(f"Invalid selection. Must be between 1 and {max_options}")
                        continue
                
                return selected
            
            except ValueError:
                print("Invalid input. Please enter a number, range, or 'q' to quit.")
                continue
            except KeyboardInterrupt:
                return None
    
    async def _download_filings(self, filings: List, selection: List[int]):
        """
        Download selected filings.
        
        Args:
            filings: All downloadable filings
            selection: List of selected indices (0-based)
        """
        selected_filings = [filings[i] for i in selection]
        
        print(f"\nDownloading {len(selected_filings)} filing(s)...\n")
        logger.info(f"{LOG_INPUT} Starting download of {len(selected_filings)} filing(s)")
        
        # Download each filing
        success_count = 0
        failed_count = 0
        retry_count = 0
        
        for i, filing in enumerate(selected_filings, 1):
            # Use pre-loaded company name
            company_name = getattr(filing, '_company_name', 'UNKNOWN')
            
            # Check if this is a retry (was failed before)
            is_retry = filing.download_status == 'failed'
            retry_marker = "[RETRY] " if is_retry else ""
            if is_retry:
                retry_count += 1
            
            print(f"[{i}/{len(selected_filings)}] {retry_marker}{company_name} - {filing.form_type}")
            
            try:
                # Process filing
                result = await self.coordinator.process_single_filing(filing)
                
                if result.success:
                    success_count += 1
                    print(f"  Success ({result.total_duration:.1f}s)")
                else:
                    failed_count += 1
                    error_stage = result.error_stage or 'unknown'
                    print(f"  Failed at {error_stage}")
            
            except Exception as e:
                failed_count += 1
                print(f"  Error: {e}")
                logger.error(f"Download failed: {e}")
        
        # Summary
        print("\n" + "=" * 90)
        print("DOWNLOAD SUMMARY")
        print("=" * 90)
        print(f"Total:     {len(selected_filings)}")
        print(f"Retries:   {retry_count}")
        print(f"Success:   {success_count}")
        print(f"Failed:    {failed_count}")
        print("=" * 90)
        
        logger.info(
            f"{LOG_OUTPUT} Download complete: {success_count} succeeded, "
            f"{failed_count} failed ({retry_count} were retries)"
        )


async def main():
    """Main CLI entry point."""
    cli = DownloadCLI()
    await cli.run()


if __name__ == '__main__':
    asyncio.run(main())


__all__ = ['DownloadCLI', 'main']