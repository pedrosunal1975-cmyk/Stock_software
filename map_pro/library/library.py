# Path: library/library.py
"""
Library Module - Main CLI Entry Point
Taxonomy library management for MAP PRO system.
Discovers parsed filings, identifies taxonomy requirements, ensures availability.
100% AGNOSTIC - no hardcoded taxonomy knowledge.
All pattern matching delegated to searcher.TaxonomyRecognizer.
Usage:
    python library.py --scan          # Scan once and identify requirements
    python library.py --monitor       # Continuous monitoring
    python library.py --list          # List all libraries
    python library.py --list-pending  # Show pending downloads
    python library.py --stats         # Show statistics
"""
import sys
import argparse
import time
from pathlib import Path

# Add parent directory to path so we can import library module
sys.path.insert(0, str(Path(__file__).parent.parent))

# CRITICAL: Initialize database engine FIRST, before any library imports
from database import initialize_engine
initialize_engine()

# NOW safe to import library components
from library.core.config_loader import LibraryConfig
from library.core.data_paths import LibraryPaths
from library.core.logger import get_logger

logger = get_logger(__name__, 'cli')


def main():
    """Main entry point for library module."""
    parser = argparse.ArgumentParser(
        description='Library Module - Taxonomy Management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python library.py --scan            Scan once for new files
  python library.py --monitor         Start background monitoring
  python library.py --list            Show all libraries
  python library.py --list-pending    Show pending downloads
  python library.py --download        Download all pending taxonomies
  python library.py --manual          Show manual download instructions
  python library.py --stats           Show statistics
        """
    )
    
    parser.add_argument(
        '--monitor',
        action='store_true',
        help='Start continuous monitoring for new parsed files'
    )
    
    parser.add_argument(
        '--scan',
        action='store_true',
        help='Scan once for pending files and exit'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all taxonomy libraries'
    )
    
    parser.add_argument(
        '--list-pending',
        action='store_true',
        help='List pending taxonomy downloads'
    )
    
    parser.add_argument(
        '--manual',
        action='store_true',
        help='Show manual download instructions'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show library statistics'
    )
    
    parser.add_argument(
        '--setup',
        action='store_true',
        help='Create all required directories'
    )
    
    parser.add_argument(
        '--download',
        action='store_true',
        help='Download all pending taxonomy libraries'
    )

    parser.add_argument(
        '--process-manual',
        action='store_true',
        help='Process all ZIP files in manual_downloads directory automatically'
    )

    args = parser.parse_args()
    
    # If no arguments, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return 0
    
    logger.info("[INPUT] Initializing library module")
    
    try:
        # Execute requested command
        if args.setup:
            return cmd_setup()
        elif args.scan:
            return cmd_scan()
        elif args.monitor:
            return cmd_monitor()
        elif args.list:
            return cmd_list()
        elif args.list_pending:
            return cmd_list_pending()
        elif args.manual:
            return cmd_manual()
        elif args.stats:
            return cmd_stats()
        elif args.download:
            return cmd_download()
        elif args.process_manual:
            return cmd_process_manual()
        else:
            parser.print_help()
            return 0
            
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        logger.info("[OUTPUT] Interrupted by user")
        return 0
    except Exception as e:
        print(f"\nError: {e}")
        logger.error(f"Error in library module: {e}")
        return 1


def cmd_setup():
    """Create all required directories."""
    logger.info("[INPUT] Setting up library directories")
    
    config = LibraryConfig()
    paths = LibraryPaths(config)
    
    # This automatically creates all directories
    count = paths.ensure_all_directories()
    
    print("\nDirectory setup complete!")
    print(f"Created directories:")
    print(f"  Taxonomies Root: {paths.taxonomies_root}")
    print(f"  Libraries:       {paths.taxonomies_libraries}")
    print(f"  Manual Downloads: {paths.manual_downloads}")
    print(f"  Cache:           {paths.cache_dir}")
    print(f"  Temp:            {paths.temp_dir}")
    print(f"  Logs:            {paths.log_dir}")
    
    logger.info("[OUTPUT] Setup complete")
    return 0


def cmd_scan():
    """Scan once for new parsed files and process."""
    logger.info("[INPUT] Running one-time scan")
    
    print("\n" + "=" * 80)
    print("LIBRARY SCAN - ONE-TIME")
    print("=" * 80)
    
    try:
        from library.engine.coordinator import LibraryCoordinator
        
        # Initialize coordinator
        coordinator = LibraryCoordinator()
        
        print("\nScanning for new parsed filings...")
        
        # Process all new filings
        results = coordinator.process_new_filings()
        
        if not results:
            print("No new filings found to process.")
            logger.info("[OUTPUT] No new filings found")
            return 0
        
        # Display results
        print(f"\nProcessed {len(results)} filings:\n")
        
        success_count = 0
        for result in results:
            if result['success']:
                success_count += 1
                filing_id = result['filing_id']
                ns_count = len(result.get('namespaces_detected', []))
                libs_ready = result.get('libraries_ready', False)
                
                status = "âœ“ Ready" if libs_ready else "âš  Missing libraries"
                print(f"  {status} | {filing_id}")
                print(f"    Namespaces: {ns_count}")
                print(f"    Libraries: {', '.join(result.get('libraries_required', []))}")
                
                if not libs_ready:
                    missing = result.get('libraries_missing', 0)
                    print(f"    Missing: {missing} libraries")
                print()
            else:
                print(f"  âœ— Error | {result['filing_id']}: {result.get('error', 'Unknown error')}\n")
        
        # Summary
        print("=" * 80)
        print(f"Summary: {success_count}/{len(results)} filings processed successfully")
        print("=" * 80)
        
        logger.info(f"[OUTPUT] Scan complete: {success_count}/{len(results)} successful")
        
        return 0
        
    except ImportError as e:
        print(f"\nError: Cannot import required modules")
        print(f"Details: {e}")
        print("\nEnsure searcher and database modules are available.")
        logger.error(f"Import error: {e}")
        return 1
    except Exception as e:
        print(f"\nError during scan: {e}")
        logger.error(f"Scan error: {e}")
        return 1


def cmd_monitor():
    """Start continuous monitoring for new parsed files."""
    logger.info("[INPUT] Starting continuous monitoring")
    
    print("\n" + "=" * 80)
    print("LIBRARY MONITOR - CONTINUOUS MODE")
    print("=" * 80)
    print("\nPress Ctrl+C to stop monitoring\n")
    
    try:
        from library.engine.coordinator import LibraryCoordinator
        
        config = LibraryConfig()
        interval = config.get('library_monitor_interval')
        
        # Initialize coordinator
        coordinator = LibraryCoordinator()
        
        print(f"Monitoring every {interval} seconds...\n")
        
        cycle = 0
        while True:
            cycle += 1
            print(f"[Cycle {cycle}] Scanning for new filings...")
            
            # Process new filings
            results = coordinator.process_new_filings()
            
            if results:
                print(f"  Found {len(results)} new filings")
                
                for result in results:
                    if result['success']:
                        filing_id = result['filing_id']
                        libs_ready = result.get('libraries_ready', False)
                        status = "âœ“" if libs_ready else "âš "
                        print(f"  {status} {filing_id}")
            else:
                print(f"  No new filings")
            
            # Get statistics
            stats = coordinator.get_statistics()
            print(f"  Total processed: {stats['processed_filings_count']}")
            
            # Wait for next cycle
            print(f"  Waiting {interval}s...\n")
            time.sleep(interval)
            
    except ImportError as e:
        print(f"\nError: Cannot import required modules")
        print(f"Details: {e}")
        print("\nEnsure searcher and database modules are available.")
        logger.error(f"Import error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
        logger.info("[OUTPUT] Monitoring stopped")
        return 0
    except Exception as e:
        print(f"\nError during monitoring: {e}")
        logger.error(f"Monitor error: {e}")
        return 1


def cmd_list():
    """List all taxonomy libraries."""
    logger.info("[INPUT] Listing taxonomy libraries")
    
    try:
        from library.cli.library_cli import LibraryCLI
        
        cli = LibraryCLI()
        cli.list_libraries()
        
        logger.info("[OUTPUT] List complete")
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        logger.error(f"List error: {e}")
        return 1


def cmd_list_pending():
    """List pending taxonomy downloads."""
    logger.info("[INPUT] Listing pending downloads")
    
    try:
        from library.cli.library_cli import LibraryCLI
        
        cli = LibraryCLI()
        cli.list_pending()
        
        logger.info("[OUTPUT] List pending complete")
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        logger.error(f"List pending error: {e}")
        return 1


def cmd_manual():
    """Show manual download instructions."""
    logger.info("[INPUT] Showing manual instructions")
    
    try:
        from library.engine.manual_processor import ManualProcessor
        
        processor = ManualProcessor()
        instructions = processor.get_manual_instructions()
        
        print(instructions)
        
        logger.info("[OUTPUT] Manual instructions displayed")
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        logger.error(f"Manual instructions error: {e}")
        return 1


def cmd_stats():
    """Show library statistics."""
    logger.info("[INPUT] Showing statistics")
    
    try:
        from library.cli.library_cli import LibraryCLI
        
        cli = LibraryCLI()
        cli.show_statistics()
        
        logger.info("[OUTPUT] Statistics displayed")
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        logger.error(f"Statistics error: {e}")
        return 1


def cmd_download():
    """Download all pending taxonomy libraries."""
    logger.info("[INPUT] Starting download of pending taxonomies")

    print("\n" + "=" * 80)
    print("LIBRARY DOWNLOAD - PENDING TAXONOMIES")
    print("=" * 80)

    try:
        # First, ensure all directories exist (including manual_downloads)
        from library.core.config_loader import LibraryConfig
        from library.core.data_paths import LibraryPaths
        from library.engine.manual_processor import ManualProcessor

        config = LibraryConfig()
        paths = LibraryPaths(config)
        paths.ensure_all_directories()

        # Check for manual downloads first
        print("\nChecking for manual downloads...")
        manual_processor = ManualProcessor(config, paths)
        manual_files = manual_processor.scan_manual_directory()

        if manual_files:
            print(f"\nFound {len(manual_files)} file(s) in manual_downloads/:")
            for f in manual_files:
                detected = "[OK]" if f.get('auto_detected') else "[??]"
                name = f.get('detected_name', '?')
                version = f.get('detected_version', '?')
                print(f"  {detected} {f['filename']} -> {name} v{version}")
            print("\nTo process all files automatically, run:")
            print("  python library.py --process-manual")
            print()
        else:
            print(f"  No files in {paths.manual_downloads}")
            print("  (Place manually downloaded ZIP files here)")

        # Import downloader coordinator
        import sys
        from pathlib import Path

        # Add downloader module to path (sibling module)
        downloader_path = Path(__file__).parent.parent / 'downloader'
        if str(downloader_path) not in sys.path:
            sys.path.insert(0, str(downloader_path))

        from downloader.engine.coordinator import DownloadCoordinator
        import asyncio

        print("\nInitializing download coordinator...")

        # Create coordinator
        coordinator = DownloadCoordinator()

        print("Querying pending taxonomy downloads...")

        # Download pending taxonomies
        # Note: coordinator.process_pending_downloads() handles BOTH filings AND taxonomies
        async def run_downloads():
            stats = await coordinator.process_pending_downloads(limit=100)
            return stats

        # Run async download
        stats = asyncio.run(run_downloads())

        # Display results
        print("\n" + "=" * 80)
        print("DOWNLOAD RESULTS")
        print("=" * 80)
        print(f"Total processed: {stats['total']}")
        print(f"Succeeded: {stats['succeeded']}")
        print(f"Failed: {stats['failed']}")
        print(f"Duration: {stats['duration']:.1f}s")

        # If there were failures, remind about manual downloads
        if stats['failed'] > 0:
            print("\n" + "-" * 80)
            print("MANUAL DOWNLOAD MAY BE REQUIRED")
            print("-" * 80)
            print(f"Some taxonomies failed to download automatically.")
            print(f"Manual downloads directory: {paths.manual_downloads}")
            print("\nFor IFRS taxonomies:")
            print("  1. Visit: https://www.ifrs.org/issued-standards/ifrs-taxonomy/")
            print("  2. Download the required year's taxonomy ZIP")
            print("  3. Place in manual_downloads/ directory")
            print("  4. Run: python library.py --process-manual")

        print("=" * 80)

        logger.info(
            f"[OUTPUT] Download complete: {stats['succeeded']}/{stats['total']} successful"
        )

        return 0

    except ImportError as e:
        print(f"\nError: Cannot import downloader module")
        print(f"Details: {e}")
        print("\nEnsure downloader module is available in parent directory.")
        logger.error(f"Import error: {e}")
        return 1
    except Exception as e:
        print(f"\nError during download: {e}")
        logger.error(f"Download error: {e}")
        return 1


def cmd_process_manual():
    """Process all ZIP files in manual_downloads directory automatically."""
    logger.info("[INPUT] Processing manual downloads")

    print("\n" + "=" * 80)
    print("PROCESS MANUAL DOWNLOADS")
    print("=" * 80)

    try:
        from library.engine.manual_processor import ManualProcessor

        config = LibraryConfig()
        paths = LibraryPaths(config)

        # Ensure directories exist
        paths.ensure_all_directories()

        processor = ManualProcessor(config, paths)

        # First, show what files are available
        print(f"\nScanning: {paths.manual_downloads}")

        files = processor.scan_manual_directory()

        if not files:
            print("\nNo files found in manual_downloads directory.")
            print(f"\nTo use manual downloads:")
            print(f"  1. Download taxonomy ZIP files")
            print(f"  2. Place them in: {paths.manual_downloads}")
            print(f"  3. Run: python library.py --process-manual")
            return 0

        # Show detected files
        print(f"\nFound {len(files)} file(s):\n")
        for f in files:
            detected = "[OK]" if f.get('auto_detected') else "[??]"
            name = f.get('detected_name', '?')
            version = f.get('detected_version', '?')
            print(f"  {detected} {f['filename']}")
            print(f"      -> {name} v{version} ({f['size_mb']:.1f} MB)")

        # Process all files
        print("\n" + "-" * 80)
        print("Processing files...")
        print("-" * 80)

        result = processor.process_all_manual_files()

        # Show results
        print()
        for r in result.get('results', []):
            if r['success']:
                print(f"  [OK] {r['filename']}")
                print(f"       -> Extracted to: {r.get('extract_path', 'N/A')}")
                print(f"       -> Files: {r.get('file_count', 0)}")
            else:
                print(f"  [FAIL] {r['filename']}")
                print(f"         Error: {r.get('error', 'Unknown')}")

        # Summary
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)
        print(f"Total files: {result['total']}")
        print(f"Processed:   {result['processed']}")
        print(f"Failed:      {result['failed']}")

        if result['processed'] > 0:
            print(f"\nTaxonomies extracted to: {paths.taxonomies_libraries}")
            print(f"ZIP files remain in:     {paths.manual_downloads}")

        print("=" * 80)

        logger.info(
            f"[OUTPUT] Manual processing complete: "
            f"{result['processed']}/{result['total']} successful"
        )

        return 0 if result['success'] else 1

    except Exception as e:
        print(f"\nError during processing: {e}")
        logger.error(f"Process manual error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())