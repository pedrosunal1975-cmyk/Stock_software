# Path: mat_acc/scripts/migrate_add_structure_columns.py
"""
Migration: Add Structure Extraction Columns

Adds columns to hierarchy_nodes table for structure extraction:
- statement_type: Type of financial statement
- balance: Debit or credit balance from taxonomy
- is_calculated_total: Whether node is a total in calculation linkbase
- calculation_parent: Parent mat_acc_id in calculation hierarchy
- calculation_weight: Weight in calculation (+1 or -1)

Usage:
    python scripts/migrate_add_structure_columns.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from database.models.base import initialize_engine, get_engine


def main():
    """Run migration to add structure extraction columns."""
    print('=' * 70)
    print('Migration: Add Structure Extraction Columns')
    print('=' * 70)
    print()

    # Initialize engine
    initialize_engine()
    engine = get_engine()

    migrations = [
        {
            'name': 'statement_type',
            'sql': """
                ALTER TABLE hierarchy_nodes
                ADD COLUMN IF NOT EXISTS statement_type VARCHAR(50);
            """,
            'comment': """
                COMMENT ON COLUMN hierarchy_nodes.statement_type IS
                'Statement type: balance_sheet, income_statement, cash_flow, equity, comprehensive_income';
            """,
            'index': """
                CREATE INDEX IF NOT EXISTS idx_node_statement_type
                ON hierarchy_nodes(statement_type);
            """
        },
        {
            'name': 'balance',
            'sql': """
                ALTER TABLE hierarchy_nodes
                ADD COLUMN IF NOT EXISTS balance VARCHAR(10);
            """,
            'comment': """
                COMMENT ON COLUMN hierarchy_nodes.balance IS
                'Balance type from taxonomy: debit or credit';
            """
        },
        {
            'name': 'is_calculated_total',
            'sql': """
                ALTER TABLE hierarchy_nodes
                ADD COLUMN IF NOT EXISTS is_calculated_total BOOLEAN DEFAULT FALSE;
            """,
            'comment': """
                COMMENT ON COLUMN hierarchy_nodes.is_calculated_total IS
                'Whether this node is a total in calculation linkbase';
            """
        },
        {
            'name': 'calculation_parent',
            'sql': """
                ALTER TABLE hierarchy_nodes
                ADD COLUMN IF NOT EXISTS calculation_parent VARCHAR(50);
            """,
            'comment': """
                COMMENT ON COLUMN hierarchy_nodes.calculation_parent IS
                'mat_acc_id of parent in calculation hierarchy';
            """,
            'index': """
                CREATE INDEX IF NOT EXISTS idx_node_calculation_parent
                ON hierarchy_nodes(calculation_parent);
            """
        },
        {
            'name': 'calculation_weight',
            'sql': """
                ALTER TABLE hierarchy_nodes
                ADD COLUMN IF NOT EXISTS calculation_weight FLOAT;
            """,
            'comment': """
                COMMENT ON COLUMN hierarchy_nodes.calculation_weight IS
                'Weight in calculation: 1.0 (add) or -1.0 (subtract)';
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
