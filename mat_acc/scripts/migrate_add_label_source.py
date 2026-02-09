# Path: mat_acc/scripts/migrate_add_label_source.py
"""
Migration: Add label_source Column

Adds label_source column to hierarchy_nodes table to track the provenance
of standard_label values (taxonomy name or 'generated').

Usage:
    python scripts/migrate_add_label_source.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from database.models.base import initialize_engine, get_engine


def main():
    """Run migration to add label_source column."""
    print('=' * 70)
    print('Migration: Add label_source Column')
    print('=' * 70)
    print()

    # Initialize engine
    initialize_engine()
    engine = get_engine()

    migrations = [
        {
            'name': 'label_source',
            'sql': """
                ALTER TABLE hierarchy_nodes
                ADD COLUMN IF NOT EXISTS label_source VARCHAR(50);
            """,
            'comment': """
                COMMENT ON COLUMN hierarchy_nodes.label_source IS
                'Source of standard_label: taxonomy name (us-gaap, ifrs-full) or generated';
            """,
            'index': """
                CREATE INDEX IF NOT EXISTS idx_node_label_source
                ON hierarchy_nodes(label_source);
            """
        }
    ]

    with engine.connect() as conn:
        for migration in migrations:
            print(f"Adding column: {migration['name']}...")
            try:
                conn.execute(text(migration['sql']))
                print(f"  [OK] Column {migration['name']} added")

                conn.execute(text(migration['comment']))
                print(f"  [OK] Comment added")

                if 'index' in migration:
                    conn.execute(text(migration['index']))
                    print(f"  [OK] Index created")

                conn.commit()

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
