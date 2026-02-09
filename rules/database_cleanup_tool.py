#!/usr/bin/env python3
"""
Map Pro Database Cleanup Tool
==============================

Standalone tool for comprehensive database cleanup and health check.
Works with the xbrl_coordination database schema (5 tables):
- markets, entities, filing_searches, downloaded_filings, taxonomy_libraries

Can be run independently without starting the full Map Pro system.

Usage:
    python database_cleanup_tool.py --check          # Audit only (no changes)
    python database_cleanup_tool.py --clean          # Clean duplicates/orphans
    python database_cleanup_tool.py --verify-files   # Verify filesystem paths
    python database_cleanup_tool.py --constraints    # Add missing constraints
    python database_cleanup_tool.py --full           # Full cleanup + constraints

Requirements:
    - PostgreSQL connection details in .env or as arguments
    - psycopg2 package installed
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("ERROR: psycopg2 not installed. Install with: pip install psycopg2-binary")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False


class DatabaseCleanupTool:
    """
    Comprehensive database cleanup and health check tool for xbrl_coordination.

    Handles:
    - Duplicate detection and removal
    - Orphan record cleanup
    - File system verification (database vs reality)
    - UNIQUE constraint management
    - Database health auditing
    - Detailed reporting
    """

    # Table definitions with their key columns
    TABLES = {
        'markets': {
            'primary_key': 'market_id',
            'unique_columns': ['market_id'],
            'description': 'Regulatory market registry'
        },
        'entities': {
            'primary_key': 'entity_id',
            'unique_columns': [('market_type', 'market_entity_id')],
            'foreign_keys': {'market_type': 'markets.market_id'},
            'path_columns': ['data_directory_path'],
            'description': 'Company/entity registry'
        },
        'filing_searches': {
            'primary_key': 'search_id',
            'unique_columns': [],
            'foreign_keys': {'entity_id': 'entities.entity_id'},
            'description': 'Filing search results'
        },
        'downloaded_filings': {
            'primary_key': 'filing_id',
            'unique_columns': ['search_id'],
            'foreign_keys': {
                'search_id': 'filing_searches.search_id',
                'entity_id': 'entities.entity_id'
            },
            'path_columns': ['download_directory', 'extraction_directory', 'instance_file_path'],
            'description': 'Downloaded filings tracker'
        },
        'taxonomy_libraries': {
            'primary_key': 'library_id',
            'unique_columns': [('taxonomy_name', 'taxonomy_version'), 'taxonomy_namespace'],
            'path_columns': ['library_directory', 'downloaded_file_path', 'extraction_path'],
            'description': 'Taxonomy library registry'
        }
    }

    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config
        self.conn = None
        self.results = {}

    def connect(self) -> psycopg2.extensions.connection:
        """Create database connection."""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
        return self.conn

    def close(self):
        """Close database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()
            self.conn = None

    def _print_header(self, title: str):
        """Print section header."""
        print("\n" + "=" * 70)
        print(title)
        print("=" * 70)

    def _print_subheader(self, title: str):
        """Print subsection header."""
        print(f"\n{title}")
        print("-" * 50)

    # =========================================================================
    # AUDIT FUNCTIONS
    # =========================================================================

    def audit_table_counts(self) -> Dict:
        """Get row counts for all tables."""
        self._print_header("TABLE STATISTICS")

        results = {}
        conn = self.connect()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        for table_name, table_info in self.TABLES.items():
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                count = cursor.fetchone()['count']
                results[table_name] = count
                print(f"  {table_name}: {count} rows - {table_info['description']}")
            except Exception as e:
                results[table_name] = f"ERROR: {e}"
                print(f"  {table_name}: ERROR - {e}")

        cursor.close()
        return results

    def audit_duplicates(self) -> Dict:
        """Check all tables for duplicate records."""
        self._print_header("DUPLICATE DETECTION")

        results = {}
        conn = self.connect()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check entities duplicates (market_type + market_entity_id)
        self._print_subheader("1. Checking entities for duplicates...")
        cursor.execute("""
            SELECT market_type, market_entity_id, COUNT(*) as dup_count
            FROM entities
            GROUP BY market_type, market_entity_id
            HAVING COUNT(*) > 1
        """)
        entity_dups = cursor.fetchall()
        results['entities'] = len(entity_dups)
        if entity_dups:
            print(f"   WARNING: {len(entity_dups)} duplicate entity combinations found:")
            for dup in entity_dups[:5]:
                print(f"      - {dup['market_type']}/{dup['market_entity_id']}: {dup['dup_count']} occurrences")
        else:
            print("   OK: No duplicate entities")

        # Check downloaded_filings duplicates (search_id should be unique)
        self._print_subheader("2. Checking downloaded_filings for duplicates...")
        cursor.execute("""
            SELECT search_id, COUNT(*) as dup_count
            FROM downloaded_filings
            GROUP BY search_id
            HAVING COUNT(*) > 1
        """)
        filing_dups = cursor.fetchall()
        results['downloaded_filings'] = len(filing_dups)
        if filing_dups:
            print(f"   WARNING: {len(filing_dups)} duplicate search_id values found")
            for dup in filing_dups[:5]:
                print(f"      - search_id {dup['search_id']}: {dup['dup_count']} occurrences")
        else:
            print("   OK: No duplicate downloaded_filings")

        # Check taxonomy_libraries duplicates (name+version, namespace)
        self._print_subheader("3. Checking taxonomy_libraries for duplicates...")
        cursor.execute("""
            SELECT taxonomy_name, taxonomy_version, COUNT(*) as dup_count
            FROM taxonomy_libraries
            GROUP BY taxonomy_name, taxonomy_version
            HAVING COUNT(*) > 1
        """)
        tax_name_dups = cursor.fetchall()

        cursor.execute("""
            SELECT taxonomy_namespace, COUNT(*) as dup_count
            FROM taxonomy_libraries
            WHERE taxonomy_namespace IS NOT NULL
            GROUP BY taxonomy_namespace
            HAVING COUNT(*) > 1
        """)
        tax_ns_dups = cursor.fetchall()

        results['taxonomy_libraries_name_version'] = len(tax_name_dups)
        results['taxonomy_libraries_namespace'] = len(tax_ns_dups)

        if tax_name_dups:
            print(f"   WARNING: {len(tax_name_dups)} duplicate name/version combinations")
        if tax_ns_dups:
            print(f"   WARNING: {len(tax_ns_dups)} duplicate namespaces")
        if not tax_name_dups and not tax_ns_dups:
            print("   OK: No duplicate taxonomy_libraries")

        # Check filing_searches for potential duplicates
        self._print_subheader("4. Checking filing_searches for potential duplicates...")
        cursor.execute("""
            SELECT entity_id, form_type, filing_date, accession_number, COUNT(*) as dup_count
            FROM filing_searches
            WHERE accession_number IS NOT NULL
            GROUP BY entity_id, form_type, filing_date, accession_number
            HAVING COUNT(*) > 1
        """)
        search_dups = cursor.fetchall()
        results['filing_searches'] = len(search_dups)
        if search_dups:
            print(f"   WARNING: {len(search_dups)} potential duplicate filing searches")
            for dup in search_dups[:5]:
                print(f"      - {dup['form_type']} on {dup['filing_date']}: {dup['dup_count']} occurrences")
        else:
            print("   OK: No duplicate filing_searches")

        cursor.close()
        return results

    def audit_orphans(self) -> Dict:
        """Check for orphan records (broken foreign key relationships)."""
        self._print_header("ORPHAN RECORD DETECTION")

        results = {}
        conn = self.connect()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Entities without valid market
        self._print_subheader("1. Checking entities without valid market...")
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM entities e
            LEFT JOIN markets m ON e.market_type = m.market_id
            WHERE m.market_id IS NULL
        """)
        orphan_entities = cursor.fetchone()['count']
        results['entities_no_market'] = orphan_entities
        print(f"   Entities without valid market: {orphan_entities}")

        # Filing searches without valid entity
        self._print_subheader("2. Checking filing_searches without valid entity...")
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM filing_searches fs
            LEFT JOIN entities e ON fs.entity_id = e.entity_id
            WHERE e.entity_id IS NULL
        """)
        orphan_searches = cursor.fetchone()['count']
        results['filing_searches_no_entity'] = orphan_searches
        print(f"   Filing searches without valid entity: {orphan_searches}")

        # Downloaded filings without valid search
        self._print_subheader("3. Checking downloaded_filings without valid search...")
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM downloaded_filings df
            LEFT JOIN filing_searches fs ON df.search_id = fs.search_id
            WHERE fs.search_id IS NULL
        """)
        orphan_downloads_search = cursor.fetchone()['count']
        results['downloaded_filings_no_search'] = orphan_downloads_search
        print(f"   Downloaded filings without valid search: {orphan_downloads_search}")

        # Downloaded filings without valid entity
        self._print_subheader("4. Checking downloaded_filings without valid entity...")
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM downloaded_filings df
            LEFT JOIN entities e ON df.entity_id = e.entity_id
            WHERE e.entity_id IS NULL
        """)
        orphan_downloads_entity = cursor.fetchone()['count']
        results['downloaded_filings_no_entity'] = orphan_downloads_entity
        print(f"   Downloaded filings without valid entity: {orphan_downloads_entity}")

        cursor.close()

        total_orphans = sum(v for v in results.values() if isinstance(v, int))
        if total_orphans == 0:
            print("\n   OK: No orphan records found")
        else:
            print(f"\n   WARNING: {total_orphans} total orphan records found")

        return results

    def audit_status_consistency(self) -> Dict:
        """Check for status inconsistencies."""
        self._print_header("STATUS CONSISTENCY CHECK")

        results = {}
        conn = self.connect()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Filing searches status distribution
        self._print_subheader("1. Filing searches status distribution...")
        cursor.execute("""
            SELECT
                download_status,
                extraction_status,
                COUNT(*) as count
            FROM filing_searches
            GROUP BY download_status, extraction_status
            ORDER BY download_status, extraction_status
        """)
        search_status = cursor.fetchall()
        results['filing_searches_status'] = search_status
        for status in search_status:
            print(f"   download={status['download_status']}, extraction={status['extraction_status']}: {status['count']}")

        # Downloaded filings with completed search but missing files
        self._print_subheader("2. Downloaded filings parse status distribution...")
        cursor.execute("""
            SELECT parse_status, COUNT(*) as count
            FROM downloaded_filings
            GROUP BY parse_status
            ORDER BY parse_status
        """)
        parse_status = cursor.fetchall()
        results['downloaded_filings_parse_status'] = parse_status
        for status in parse_status:
            print(f"   parse_status={status['parse_status']}: {status['count']}")

        # Taxonomy libraries status
        self._print_subheader("3. Taxonomy libraries status distribution...")
        cursor.execute("""
            SELECT
                download_status,
                status,
                validation_status,
                COUNT(*) as count
            FROM taxonomy_libraries
            GROUP BY download_status, status, validation_status
            ORDER BY download_status, status
        """)
        tax_status = cursor.fetchall()
        results['taxonomy_libraries_status'] = tax_status
        for status in tax_status:
            print(f"   download={status['download_status']}, status={status['status']}, validation={status['validation_status']}: {status['count']}")

        # Check for inconsistent statuses
        self._print_subheader("4. Checking for status inconsistencies...")

        # Searches marked completed but no downloaded_filing record
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM filing_searches fs
            LEFT JOIN downloaded_filings df ON fs.search_id = df.search_id
            WHERE fs.download_status = 'completed' AND df.filing_id IS NULL
        """)
        missing_downloads = cursor.fetchone()['count']
        results['completed_without_download'] = missing_downloads
        if missing_downloads > 0:
            print(f"   WARNING: {missing_downloads} searches marked 'completed' but no downloaded_filing record")
        else:
            print("   OK: All completed searches have download records")

        cursor.close()
        return results

    def audit_constraints(self) -> Dict:
        """Check for existence of important constraints."""
        self._print_header("CONSTRAINT CHECK")

        results = {}
        conn = self.connect()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get all constraints
        cursor.execute("""
            SELECT
                tc.table_name,
                tc.constraint_name,
                tc.constraint_type
            FROM information_schema.table_constraints tc
            WHERE tc.table_schema = 'public'
            AND tc.table_name IN ('markets', 'entities', 'filing_searches',
                                   'downloaded_filings', 'taxonomy_libraries')
            ORDER BY tc.table_name, tc.constraint_type
        """)
        constraints = cursor.fetchall()

        # Group by table
        by_table = {}
        for c in constraints:
            table = c['table_name']
            if table not in by_table:
                by_table[table] = []
            by_table[table].append({
                'name': c['constraint_name'],
                'type': c['constraint_type']
            })

        results['constraints'] = by_table

        for table_name in self.TABLES.keys():
            self._print_subheader(f"{table_name} constraints:")
            if table_name in by_table:
                for c in by_table[table_name]:
                    print(f"   {c['type']}: {c['name']}")
            else:
                print("   No constraints found")

        # Check for expected constraints
        expected_constraints = {
            'entities': 'entities_market_entity_unique',
            'taxonomy_libraries': 'taxonomy_name_version_unique',
        }

        self._print_subheader("Expected constraints check:")
        for table, constraint_name in expected_constraints.items():
            exists = any(
                c['name'] == constraint_name
                for c in by_table.get(table, [])
            )
            status = "EXISTS" if exists else "MISSING"
            results[f'{table}_{constraint_name}'] = exists
            print(f"   {table}.{constraint_name}: {status}")

        cursor.close()
        return results

    def verify_file_paths(self) -> Dict:
        """Verify that file paths in database actually exist on filesystem."""
        self._print_header("FILE SYSTEM VERIFICATION")

        results = {}
        conn = self.connect()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check entity data directories
        self._print_subheader("1. Checking entity data directories...")
        cursor.execute("""
            SELECT entity_id, company_name, data_directory_path
            FROM entities
            WHERE data_directory_path IS NOT NULL
        """)
        entities = cursor.fetchall()

        entity_missing = []
        entity_exists = 0
        for entity in entities:
            path = entity['data_directory_path']
            if path and Path(path).exists():
                entity_exists += 1
            else:
                entity_missing.append({
                    'id': str(entity['entity_id']),
                    'name': entity['company_name'],
                    'path': path
                })

        results['entities_path_exists'] = entity_exists
        results['entities_path_missing'] = len(entity_missing)
        print(f"   Paths exist: {entity_exists}")
        print(f"   Paths missing: {len(entity_missing)}")
        if entity_missing:
            for m in entity_missing[:3]:
                print(f"      - {m['name']}: {m['path']}")

        # Check downloaded_filings directories
        self._print_subheader("2. Checking downloaded_filings directories...")
        cursor.execute("""
            SELECT filing_id, download_directory, extraction_directory, instance_file_path
            FROM downloaded_filings
        """)
        filings = cursor.fetchall()

        download_exists = 0
        download_missing = 0
        extraction_exists = 0
        extraction_missing = 0
        instance_exists = 0
        instance_missing = 0

        for filing in filings:
            # Download directory
            if filing['download_directory']:
                if Path(filing['download_directory']).exists():
                    download_exists += 1
                else:
                    download_missing += 1

            # Extraction directory
            if filing['extraction_directory']:
                if Path(filing['extraction_directory']).exists():
                    extraction_exists += 1
                else:
                    extraction_missing += 1

            # Instance file
            if filing['instance_file_path']:
                if Path(filing['instance_file_path']).exists():
                    instance_exists += 1
                else:
                    instance_missing += 1

        results['download_dir_exists'] = download_exists
        results['download_dir_missing'] = download_missing
        results['extraction_dir_exists'] = extraction_exists
        results['extraction_dir_missing'] = extraction_missing
        results['instance_file_exists'] = instance_exists
        results['instance_file_missing'] = instance_missing

        print(f"   Download directories: {download_exists} exist, {download_missing} missing")
        print(f"   Extraction directories: {extraction_exists} exist, {extraction_missing} missing")
        print(f"   Instance files: {instance_exists} exist, {instance_missing} missing")

        # Check taxonomy_libraries directories
        self._print_subheader("3. Checking taxonomy_libraries directories...")
        cursor.execute("""
            SELECT library_id, taxonomy_name, taxonomy_version, library_directory
            FROM taxonomy_libraries
            WHERE library_directory IS NOT NULL
        """)
        taxonomies = cursor.fetchall()

        tax_exists = 0
        tax_missing = []
        for tax in taxonomies:
            path = tax['library_directory']
            if path and Path(path).exists():
                tax_exists += 1
            else:
                tax_missing.append({
                    'name': tax['taxonomy_name'],
                    'version': tax['taxonomy_version'],
                    'path': path
                })

        results['taxonomy_path_exists'] = tax_exists
        results['taxonomy_path_missing'] = len(tax_missing)
        print(f"   Paths exist: {tax_exists}")
        print(f"   Paths missing: {len(tax_missing)}")
        if tax_missing:
            for m in tax_missing[:3]:
                print(f"      - {m['name']}/{m['version']}: {m['path']}")

        cursor.close()
        return results

    # =========================================================================
    # CLEANUP FUNCTIONS
    # =========================================================================

    def clean_duplicate_entities(self) -> int:
        """Remove duplicate entities, keeping the oldest."""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM entities e1
            USING entities e2
            WHERE e1.market_type = e2.market_type
            AND e1.market_entity_id = e2.market_entity_id
            AND e1.created_at > e2.created_at
        """)
        deleted = cursor.rowcount
        conn.commit()
        cursor.close()

        return deleted

    def clean_duplicate_downloaded_filings(self) -> int:
        """Remove duplicate downloaded_filings by search_id, keeping oldest."""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM downloaded_filings df1
            USING downloaded_filings df2
            WHERE df1.search_id = df2.search_id
            AND df1.created_at > df2.created_at
        """)
        deleted = cursor.rowcount
        conn.commit()
        cursor.close()

        return deleted

    def clean_orphan_filing_searches(self) -> int:
        """Remove filing_searches without valid entity."""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM filing_searches fs
            WHERE NOT EXISTS (
                SELECT 1 FROM entities e WHERE e.entity_id = fs.entity_id
            )
        """)
        deleted = cursor.rowcount
        conn.commit()
        cursor.close()

        return deleted

    def clean_orphan_downloaded_filings(self) -> int:
        """Remove downloaded_filings without valid search or entity."""
        conn = self.connect()
        cursor = conn.cursor()

        # Delete those without valid search
        cursor.execute("""
            DELETE FROM downloaded_filings df
            WHERE NOT EXISTS (
                SELECT 1 FROM filing_searches fs WHERE fs.search_id = df.search_id
            )
        """)
        deleted_no_search = cursor.rowcount

        # Delete those without valid entity
        cursor.execute("""
            DELETE FROM downloaded_filings df
            WHERE NOT EXISTS (
                SELECT 1 FROM entities e WHERE e.entity_id = df.entity_id
            )
        """)
        deleted_no_entity = cursor.rowcount

        conn.commit()
        cursor.close()

        return deleted_no_search + deleted_no_entity

    def run_cleanup(self) -> Dict:
        """Run all cleanup operations."""
        self._print_header("RUNNING CLEANUP")

        results = {}

        print("\n1. Cleaning duplicate entities...")
        results['duplicate_entities_removed'] = self.clean_duplicate_entities()
        print(f"   Removed: {results['duplicate_entities_removed']}")

        print("\n2. Cleaning duplicate downloaded_filings...")
        results['duplicate_downloads_removed'] = self.clean_duplicate_downloaded_filings()
        print(f"   Removed: {results['duplicate_downloads_removed']}")

        print("\n3. Cleaning orphan filing_searches...")
        results['orphan_searches_removed'] = self.clean_orphan_filing_searches()
        print(f"   Removed: {results['orphan_searches_removed']}")

        print("\n4. Cleaning orphan downloaded_filings...")
        results['orphan_downloads_removed'] = self.clean_orphan_downloaded_filings()
        print(f"   Removed: {results['orphan_downloads_removed']}")

        total = sum(results.values())
        print(f"\nTotal records removed: {total}")

        return results

    # =========================================================================
    # CONSTRAINT FUNCTIONS
    # =========================================================================

    def add_constraints(self) -> Dict:
        """Add missing UNIQUE constraints."""
        self._print_header("ADDING CONSTRAINTS")

        results = {}
        conn = self.connect()
        cursor = conn.cursor()

        constraints_to_add = [
            {
                'table': 'entities',
                'name': 'entities_market_entity_unique',
                'columns': 'market_type, market_entity_id',
            },
            {
                'table': 'taxonomy_libraries',
                'name': 'taxonomy_name_version_unique',
                'columns': 'taxonomy_name, taxonomy_version',
            },
            {
                'table': 'downloaded_filings',
                'name': 'downloaded_filings_search_unique',
                'columns': 'search_id',
            },
        ]

        for constraint in constraints_to_add:
            print(f"\n1. Adding {constraint['name']}...")
            try:
                cursor.execute(f"""
                    ALTER TABLE {constraint['table']}
                    ADD CONSTRAINT {constraint['name']}
                    UNIQUE ({constraint['columns']})
                """)
                conn.commit()
                print(f"   Added: {constraint['name']}")
                results[constraint['name']] = 'added'
            except psycopg2.errors.DuplicateTable:
                conn.rollback()
                print(f"   Skipped: {constraint['name']} (already exists)")
                results[constraint['name']] = 'exists'
            except psycopg2.errors.UniqueViolation as e:
                conn.rollback()
                print(f"   FAILED: {constraint['name']} - duplicates exist!")
                print(f"           Clean duplicates first with --clean")
                results[constraint['name']] = 'failed_duplicates'
            except Exception as e:
                conn.rollback()
                print(f"   ERROR: {e}")
                results[constraint['name']] = f'error: {e}'

        # Add useful indexes
        indexes_to_add = [
            {
                'table': 'filing_searches',
                'name': 'idx_filing_searches_entity_status',
                'columns': 'entity_id, download_status',
            },
            {
                'table': 'downloaded_filings',
                'name': 'idx_downloaded_filings_parse_status',
                'columns': 'parse_status',
            },
            {
                'table': 'taxonomy_libraries',
                'name': 'idx_taxonomy_download_status',
                'columns': 'download_status',
            },
        ]

        print("\nAdding indexes...")
        for index in indexes_to_add:
            try:
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS {index['name']}
                    ON {index['table']} ({index['columns']})
                """)
                conn.commit()
                print(f"   Added: {index['name']}")
                results[index['name']] = 'added'
            except Exception as e:
                conn.rollback()
                print(f"   ERROR adding {index['name']}: {e}")
                results[index['name']] = f'error: {e}'

        cursor.close()
        return results

    # =========================================================================
    # MAIN FUNCTIONS
    # =========================================================================

    def run_full_audit(self) -> Dict:
        """Run complete audit without making changes."""
        print("\n" + "=" * 70)
        print("COMPREHENSIVE DATABASE AUDIT")
        print(f"Database: {self.db_config.get('database', 'unknown')}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        results = {}

        results['table_counts'] = self.audit_table_counts()
        results['duplicates'] = self.audit_duplicates()
        results['orphans'] = self.audit_orphans()
        results['status'] = self.audit_status_consistency()
        results['constraints'] = self.audit_constraints()

        # Summary
        self._print_header("AUDIT SUMMARY")

        total_issues = 0

        # Count duplicate issues
        dup_count = sum(v for k, v in results['duplicates'].items() if isinstance(v, int))
        if dup_count > 0:
            print(f"  Duplicates found: {dup_count}")
            total_issues += dup_count

        # Count orphan issues
        orphan_count = sum(v for k, v in results['orphans'].items() if isinstance(v, int))
        if orphan_count > 0:
            print(f"  Orphan records: {orphan_count}")
            total_issues += orphan_count

        if total_issues == 0:
            print("  No issues found - database is healthy!")
        else:
            print(f"\n  Total issues: {total_issues}")
            print("  Run with --clean to fix these issues")

        print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return results

    def run_full_cleanup(self) -> Dict:
        """Run complete cleanup: audit, clean, verify, add constraints."""
        print("\n" + "=" * 70)
        print("COMPREHENSIVE DATABASE CLEANUP")
        print(f"Database: {self.db_config.get('database', 'unknown')}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        results = {}

        # Initial audit
        print("\n>>> PHASE 1: Initial Audit")
        results['initial_audit'] = self.run_full_audit()

        # Cleanup
        print("\n>>> PHASE 2: Cleanup")
        results['cleanup'] = self.run_cleanup()

        # Add constraints
        print("\n>>> PHASE 3: Add Constraints")
        results['constraints'] = self.add_constraints()

        # File verification
        print("\n>>> PHASE 4: File System Verification")
        results['file_verification'] = self.verify_file_paths()

        # Final verification
        print("\n>>> PHASE 5: Final Verification")
        results['final_audit'] = self.audit_table_counts()
        results['final_duplicates'] = self.audit_duplicates()

        self._print_header("CLEANUP COMPLETE")
        print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return results


def load_config_from_env() -> Dict[str, str]:
    """Load database configuration from .env file."""
    if HAS_DOTENV:
        # Try to find .env file
        env_paths = [
            Path('.env'),
            Path(__file__).parent / '.env',
            Path(__file__).parent.parent / '.env',
        ]

        for env_path in env_paths:
            if env_path.exists():
                load_dotenv(env_path)
                break

    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'xbrl_coordination'),
        'user': os.getenv('DB_USER', 'a'),
        'password': os.getenv('DB_PASSWORD', ''),
    }


def main():
    """Main entry point for the cleanup tool."""
    parser = argparse.ArgumentParser(
        description='Map Pro Database Cleanup Tool (xbrl_coordination)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python database_cleanup_tool.py --check              # Audit only
  python database_cleanup_tool.py --verify-files       # Check file paths
  python database_cleanup_tool.py --clean              # Remove duplicates/orphans
  python database_cleanup_tool.py --constraints        # Add UNIQUE constraints
  python database_cleanup_tool.py --full               # Complete cleanup

  # With custom connection:
  python database_cleanup_tool.py --host localhost --user a --database xbrl_coordination --check
        """
    )

    # Actions
    parser.add_argument('--check', action='store_true',
                       help='Audit databases (no changes)')
    parser.add_argument('--clean', action='store_true',
                       help='Clean duplicates and orphans')
    parser.add_argument('--verify-files', action='store_true',
                       help='Verify file paths exist on filesystem')
    parser.add_argument('--constraints', action='store_true',
                       help='Add UNIQUE constraints')
    parser.add_argument('--full', action='store_true',
                       help='Full cleanup (audit + clean + constraints)')

    # Connection options
    parser.add_argument('--host', default=None,
                       help='Database host (default: from .env or localhost)')
    parser.add_argument('--port', type=int, default=None,
                       help='Database port (default: from .env or 5432)')
    parser.add_argument('--database', default=None,
                       help='Database name (default: from .env or xbrl_coordination)')
    parser.add_argument('--user', default=None,
                       help='Database user (default: from .env)')
    parser.add_argument('--password', default=None,
                       help='Database password (default: from .env)')

    args = parser.parse_args()

    # Require at least one action
    if not any([args.check, args.clean, args.verify_files, args.constraints, args.full]):
        parser.print_help()
        sys.exit(1)

    # Load config from .env, then override with command line args
    db_config = load_config_from_env()

    if args.host:
        db_config['host'] = args.host
    if args.port:
        db_config['port'] = args.port
    if args.database:
        db_config['database'] = args.database
    if args.user:
        db_config['user'] = args.user
    if args.password:
        db_config['password'] = args.password

    # Create cleanup tool
    tool = DatabaseCleanupTool(db_config)

    try:
        if args.full:
            tool.run_full_cleanup()
        else:
            if args.check:
                tool.run_full_audit()

            if args.verify_files:
                tool.verify_file_paths()

            if args.clean:
                tool.run_cleanup()

            if args.constraints:
                tool.add_constraints()

        print("\n[SUCCESS] Database operations completed")

    except psycopg2.OperationalError as e:
        print(f"\n[ERROR] Database connection failed: {e}")
        print("\nCheck your connection settings:")
        print(f"  Host: {db_config['host']}")
        print(f"  Port: {db_config['port']}")
        print(f"  Database: {db_config['database']}")
        print(f"  User: {db_config['user']}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Cleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Cleanup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        tool.close()


if __name__ == '__main__':
    main()
