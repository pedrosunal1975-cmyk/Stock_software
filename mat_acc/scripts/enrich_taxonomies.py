# Path: mat_acc/scripts/enrich_taxonomies.py
"""
Enrich Taxonomy Labels

Enriches hierarchy nodes with standard taxonomy labels from loaded
taxonomy libraries (US-GAAP, IFRS, UK-GAAP, etc.).

Preserves company-specific labels in 'label' column while adding
standard taxonomy labels to 'standard_label' column.

Usage:
    python scripts/enrich_taxonomies.py              # All filings
    python scripts/enrich_taxonomies.py --filing-id <uuid>  # Specific filing
    python scripts/enrich_taxonomies.py --summary    # Show enricher summary
    python scripts/enrich_taxonomies.py --skip-taxonomy  # Skip library check
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from process.enricher import TaxonomyEnricher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_library_py() -> Optional[Path]:
    """Find the map_pro library.py script from config."""
    from config_loader import ConfigLoader
    config = ConfigLoader()

    # Get library path from config
    library_path = config.get('library_script_path')
    if library_path and library_path.exists():
        logger.info(f"Found library.py at: {library_path}")
        return library_path

    # Fallback: relative to this file's location
    relative_path = Path(__file__).parent.parent.parent / 'library/library.py'
    if relative_path.exists():
        logger.info(f"Found library.py at: {relative_path}")
        return relative_path

    logger.warning("library.py not found. Check MAT_ACC_LIBRARY_SCRIPT_PATH in .env")
    return None


def get_library_env() -> dict:
    """
    Build environment dict for library.py subprocess.

    Loads mat_acc's .env file and converts MAP_PRO_* variables
    to the format expected by the library module.

    Returns:
        Environment dictionary for subprocess
    """
    # Load mat_acc's .env file
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)

    # Start with current environment
    env = os.environ.copy()

    # Map MAT_ACC/MAP_PRO prefixed variables to library module format
    mappings = {
        # Database configuration
        'MAP_PRO_DB_HOST': 'DB_HOST',
        'MAP_PRO_DB_PORT': 'DB_PORT',
        'MAP_PRO_DB_NAME': 'DB_NAME',
        'MAP_PRO_DB_USER': 'DB_USER',
        'MAP_PRO_DB_PASSWORD': 'DB_PASSWORD',
        'MAP_PRO_DB_ROOT_DIR': 'DB_ROOT_DIR',
        'MAP_PRO_DB_LOG_DIR': 'DB_LOG_DIR',
        'MAP_PRO_DB_POSTGRESQL_DATA_DIR': 'DB_POSTGRESQL_DATA_DIR',
        'MAP_PRO_DB_LOG_LEVEL': 'DB_LOG_LEVEL',
        'MAP_PRO_DB_LOG_CONSOLE': 'DB_LOG_CONSOLE',
        'MAP_PRO_DB_POOL_SIZE': 'DB_POOL_SIZE',
        'MAP_PRO_DB_POOL_MAX_OVERFLOW': 'DB_POOL_MAX_OVERFLOW',
        'MAP_PRO_DB_POOL_TIMEOUT': 'DB_POOL_TIMEOUT',
        'MAP_PRO_DB_POOL_RECYCLE': 'DB_POOL_RECYCLE',
        # Shared data paths
        'MAP_PRO_DATA_ENTITIES_DIR': 'DATA_ENTITIES_DIR',
        'MAP_PRO_DATA_TAXONOMIES_DIR': 'DATA_TAXONOMIES_DIR',
        # Library module
        'MAP_PRO_LIBRARY_TAXONOMIES_ROOT': 'LIBRARY_TAXONOMIES_ROOT',
        'MAP_PRO_LIBRARY_TAXONOMIES_LIBRARIES': 'LIBRARY_TAXONOMIES_LIBRARIES',
        'MAP_PRO_LIBRARY_MANUAL_DOWNLOADS': 'LIBRARY_MANUAL_DOWNLOADS',
        'MAP_PRO_LIBRARY_PARSED_FILES_DIR': 'LIBRARY_PARSED_FILES_DIR',
        'MAP_PRO_LIBRARY_CACHE_DIR': 'LIBRARY_CACHE_DIR',
        'MAP_PRO_LIBRARY_TEMP_DIR': 'LIBRARY_TEMP_DIR',
        'MAP_PRO_LIBRARY_LOG_DIR': 'LIBRARY_LOG_DIR',
        'MAP_PRO_LIBRARY_MONITOR_INTERVAL': 'LIBRARY_MONITOR_INTERVAL',
        'MAP_PRO_LIBRARY_AUTO_CREATE': 'LIBRARY_AUTO_CREATE',
        'MAP_PRO_LIBRARY_MIN_FILES_THRESHOLD': 'LIBRARY_MIN_FILES_THRESHOLD',
        'MAP_PRO_LIBRARY_CACHE_TTL': 'LIBRARY_CACHE_TTL',
        'MAP_PRO_LIBRARY_MAX_RETRIES': 'LIBRARY_MAX_RETRIES',
        # Downloader module
        'MAP_PRO_DOWNLOADER_ROOT_DIR': 'DOWNLOADER_ROOT_DIR',
        'MAP_PRO_DOWNLOADER_ENTITIES_DIR': 'DOWNLOADER_ENTITIES_DIR',
        'MAP_PRO_DOWNLOADER_TEMP_DIR': 'DOWNLOADER_TEMP_DIR',
        'MAP_PRO_DOWNLOADER_LOG_DIR': 'DOWNLOADER_LOG_DIR',
        'MAP_PRO_DOWNLOADER_CACHE_DIR': 'DOWNLOADER_CACHE_DIR',
    }

    for src_key, dst_key in mappings.items():
        value = os.getenv(src_key)
        if value:
            env[dst_key] = value

    return env


def ensure_taxonomies_available() -> bool:
    """
    Trigger library.py to ensure taxonomy libraries are available.

    Runs:
    1. library.py --scan (scan parsed filings for taxonomy requirements)
    2. library.py --process-manual (process any manually downloaded ZIPs)
    3. library.py --download (download any missing taxonomies)

    Returns:
        True if successful, False otherwise
    """
    library_py = find_library_py()

    if not library_py:
        print("[WARN] library.py not found - taxonomies may not be available")
        return False

    # Get environment with library module configuration from mat_acc .env
    library_env = get_library_env()

    try:
        print("\n[INFO] Scanning for taxonomy requirements...")
        logger.info("Running library.py --scan")

        result_scan = subprocess.run(
            [sys.executable, str(library_py), '--scan'],
            env=library_env,
            timeout=120
        )

        if result_scan.returncode != 0:
            logger.warning(f"library.py --scan returned {result_scan.returncode}")
        else:
            logger.info("library.py --scan completed successfully")

        print("[INFO] Processing manual taxonomy downloads...")
        logger.info("Running library.py --process-manual")

        result_manual = subprocess.run(
            [sys.executable, str(library_py), '--process-manual'],
            env=library_env,
            timeout=300
        )

        if result_manual.returncode != 0:
            logger.warning(f"library.py --process-manual returned {result_manual.returncode}")
        else:
            logger.info("library.py --process-manual completed successfully")

        print("[INFO] Downloading required taxonomies...")
        logger.info("Running library.py --download")

        result_download = subprocess.run(
            [sys.executable, str(library_py), '--download'],
            env=library_env,
            timeout=300
        )

        if result_download.returncode != 0:
            logger.warning(f"library.py --download returned {result_download.returncode}")
            return False
        else:
            logger.info("library.py --download completed successfully")
            print("[OK] Taxonomy libraries ready\n")
            return True

    except subprocess.TimeoutExpired:
        logger.error("library.py timed out")
        print("[FAIL] Taxonomy operations timed out")
        return False
    except Exception as e:
        logger.error(f"Failed to run library.py: {e}")
        print(f"[FAIL] Could not run library.py: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Enrich hierarchy nodes with standard taxonomy labels'
    )
    parser.add_argument(
        '--filing-id',
        type=str,
        help='Enrich specific filing UUID'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Batch size for processing (default: 100)'
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show enricher summary (loaded taxonomies)'
    )
    parser.add_argument(
        '--skip-taxonomy',
        action='store_true',
        help='Skip taxonomy library availability check'
    )

    args = parser.parse_args()

    print('=' * 70)
    print('mat_acc Taxonomy Enricher')
    print('=' * 70)

    # Ensure taxonomy libraries are available (unless skipped)
    if not args.skip_taxonomy:
        print()
        print('Checking Taxonomy Libraries')
        print('-' * 70)
        ensure_taxonomies_available()

    print()

    # Initialize enricher
    enricher = TaxonomyEnricher()

    if args.summary:
        # Show summary of loaded taxonomies
        summary = enricher.get_summary()
        print('Enricher Summary')
        print('-' * 40)
        print(f"  Taxonomies loaded: {summary['taxonomies_loaded']}")
        print(f"  Total elements: {summary['total_elements']}")
        print(f"  Total labels: {summary['total_labels']}")
        print()
        print('Available taxonomies:')
        for name in summary['taxonomy_names']:
            print(f"  - {name}")
        return 0

    if args.filing_id:
        # Enrich specific filing
        print(f'Enriching filing: {args.filing_id}')
        print()
        try:
            result = enricher.enrich_filing(args.filing_id, args.batch_size)
            print_result(result)
        except Exception as e:
            print(f'Error: {e}')
            return 1
    else:
        # Enrich all filings
        print('Enriching all filings in database...')
        print()
        results = enricher.enrich_all_filings(args.batch_size)

        print(f'Processed {len(results)} filings')
        print()

        total_nodes = 0
        total_enriched = 0
        total_no_match = 0
        error_count = 0

        for result in results:
            print_result(result)
            total_nodes += result.total_nodes
            total_enriched += result.enriched_count
            total_no_match += result.no_match_count
            if result.errors:
                error_count += 1

        print()
        print('=' * 70)
        print('Summary')
        print('=' * 70)
        print(f'  Filings processed: {len(results)}')
        print(f'  Total nodes: {total_nodes}')
        print(f'  Enriched: {total_enriched}')
        print(f'  No match: {total_no_match}')
        print(f'  Filings with errors: {error_count}')
        if total_nodes > 0:
            rate = (total_enriched / total_nodes) * 100
            print(f'  Success rate: {rate:.1f}%')

    return 0


def print_result(result):
    """Print a single enrichment result."""
    status = '[OK]' if not result.errors else '[WARN]'
    print(f'{status} Filing: {result.filing_id}')
    print(f'      Nodes: {result.total_nodes}, '
          f'Enriched: {result.enriched_count}, '
          f'Already done: {result.already_enriched}, '
          f'No match: {result.no_match_count}')
    if result.errors:
        for error in result.errors[:3]:  # Show first 3 errors
            print(f'      Error: {error}')


if __name__ == '__main__':
    sys.exit(main())
