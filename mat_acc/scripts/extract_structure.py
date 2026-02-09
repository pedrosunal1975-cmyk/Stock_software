# Path: mat_acc/scripts/extract_structure.py
"""
Extract Structure from XBRL Filings

Extracts structural information from XBRL filings and updates hierarchy nodes:
- statement_type: Type of financial statement (balance_sheet, income_statement, etc.)
- balance: Debit or credit balance (from taxonomy)
- is_calculated_total: Whether node is a total in calculation linkbase
- calculation_parent: Parent mat_acc_id in calculation hierarchy
- calculation_weight: Weight in calculation (+1.0 or -1.0)

Usage:
    python scripts/extract_structure.py              # All filings
    python scripts/extract_structure.py --filing-id <uuid>  # Specific filing
    python scripts/extract_structure.py --summary    # Show extractor summary
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from process.structure import StructureExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Extract structure from XBRL filings'
    )
    parser.add_argument(
        '--filing-id',
        type=str,
        help='Extract structure for specific filing UUID'
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
        help='Show extractor summary (loaded taxonomies, balance attributes)'
    )

    args = parser.parse_args()

    print('=' * 70)
    print('mat_acc Structure Extractor')
    print('=' * 70)
    print()

    # Initialize extractor
    extractor = StructureExtractor()

    if args.summary:
        # Show summary of loaded taxonomies
        summary = extractor.get_summary()
        print('Extractor Summary')
        print('-' * 40)
        print(f"  Taxonomies loaded: {summary['taxonomies_loaded']}")
        print(f"  Total elements: {summary['total_elements']}")
        print(f"  Elements with balance: {summary['elements_with_balance']}")
        print()
        print('Available taxonomies:')
        for name in summary['taxonomy_names']:
            print(f"  - {name}")
        return 0

    if args.filing_id:
        # Extract structure for specific filing
        print(f'Extracting structure for filing: {args.filing_id}')
        print()
        try:
            result = extractor.extract_filing(args.filing_id, args.batch_size)
            print_result(result)
        except Exception as e:
            print(f'Error: {e}')
            logger.exception("Error during extraction")
            return 1
    else:
        # Extract structure for all filings
        print('Extracting structure for all filings in database...')
        print()
        results = extractor.extract_all_filings(args.batch_size)

        print(f'Processed {len(results)} filings')
        print()

        total_nodes = 0
        total_extracted = 0
        total_no_match = 0
        error_count = 0

        for result in results:
            print_result(result)
            total_nodes += result.total_nodes
            total_extracted += result.extracted_count
            total_no_match += result.no_match_count
            if result.errors:
                error_count += 1

        print()
        print('=' * 70)
        print('Summary')
        print('=' * 70)
        print(f'  Filings processed: {len(results)}')
        print(f'  Total nodes: {total_nodes}')
        print(f'  Extracted: {total_extracted}')
        print(f'  No match: {total_no_match}')
        print(f'  Filings with errors: {error_count}')
        if total_nodes > 0:
            rate = (total_extracted / total_nodes) * 100
            print(f'  Success rate: {rate:.1f}%')

    return 0


def print_result(result):
    """Print a single extraction result."""
    status = '[OK]' if not result.errors else '[WARN]'
    print(f'{status} Filing: {result.filing_id}')
    print(f'      Nodes: {result.total_nodes}, '
          f'Extracted: {result.extracted_count}, '
          f'Already done: {result.already_extracted}, '
          f'No match: {result.no_match_count}')
    if result.errors:
        for error in result.errors[:3]:  # Show first 3 errors
            print(f'      Error: {error}')


if __name__ == '__main__':
    sys.exit(main())
