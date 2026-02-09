# Path: mat_acc/scripts/migrate_add_enricher_columns.py
"""
Migration: Add Enricher Columns

Adds standard_label and taxonomy_namespace columns to hierarchy_nodes table
for the TaxonomyEnricher feature.

Usage:
    python scripts/migrate_add_enricher_columns.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from database.models.base import initialize_engine, get_engine


def main():
    """Run migration to add enricher columns."""
    print('=' * 70)
    print('Migration: Add Enricher Columns')
    print('=' * 70)
    print()

    # Initialize engine
    initialize_engine()
    engine = get_engine()

    # SQL to add columns if they don't exist
    migrations = [
        {
            'name': 'standard_label',
            'sql': """
                ALTER TABLE hierarchy_nodes
                ADD COLUMN IF NOT EXISTS standard_label TEXT;
            """,
            'comment': """
                COMMENT ON COLUMN hierarchy_nodes.standard_label IS
                'Standard taxonomy label (from US-GAAP, IFRS, etc.)';
            """
        },
        {
            'name': 'taxonomy_namespace',
            'sql': """
                ALTER TABLE hierarchy_nodes
                ADD COLUMN IF NOT EXISTS taxonomy_namespace VARCHAR(255);
            """,
            'comment': """
                COMMENT ON COLUMN hierarchy_nodes.taxonomy_namespace IS
                'Taxonomy namespace that provided the standard label';
            """
        }
    ]

    with engine.connect() as conn:
        for migration in migrations:
            print(f"Adding column: {migration['name']}...")
            try:
                conn.execute(text(migration['sql']))
                conn.execute(text(migration['comment']))
                conn.commit()
                print(f"  [OK] Column {migration['name']} added")
            except Exception as e:
                if 'already exists' in str(e).lower():
                    print(f"  [SKIP] Column {migration['name']} already exists")
                else:
                    print(f"  [ERROR] {e}")

    print()
    print('Migration complete.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
