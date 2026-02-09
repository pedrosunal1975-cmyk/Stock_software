#!/usr/bin/env python3
"""
Comprehensive Database Schema Checker
Compare TaxonomyLibrary model definition vs actual database schema
Generate COMPLETE migration SQL to fix all discrepancies at once
"""

import psycopg2
from typing import Dict, List, Set

# Database connection parameters
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'xbrl_coordination',
    'user': 'a',
    'password': 'malafat74'
}

# All columns defined in TaxonomyLibrary model (from taxonomy_libraries.py)
MODEL_COLUMNS = {
    # Primary identification
    'library_id': 'UUID PRIMARY KEY',
    'taxonomy_name': 'VARCHAR(255)',
    'taxonomy_version': 'VARCHAR(50)',
    'taxonomy_namespace': 'TEXT UNIQUE',
    
    # Download URLs
    'source_url': 'TEXT',
    'primary_url': 'TEXT',
    'current_url': 'TEXT',
    'alternative_urls_tried': 'JSONB DEFAULT \'[]\'::jsonb',
    
    # File system paths
    'library_directory': 'TEXT',
    'downloaded_file_path': 'TEXT',
    'downloaded_file_size': 'INTEGER',
    'expected_file_size': 'INTEGER',
    'extraction_path': 'TEXT',
    
    # File verification
    'file_size': 'INTEGER',
    'file_hash': 'VARCHAR(128)',
    'total_files': 'INTEGER DEFAULT 0',
    'file_count': 'INTEGER DEFAULT 0',
    
    # Status tracking
    'download_status': 'VARCHAR(50) DEFAULT \'pending\'',
    'status': 'VARCHAR(50) DEFAULT \'pending\'',
    'validation_status': 'VARCHAR(50) DEFAULT \'pending\'',
    
    # Attempt tracking
    'download_attempts': 'INTEGER DEFAULT 0',
    'extraction_attempts': 'INTEGER DEFAULT 0',
    'total_attempts': 'INTEGER DEFAULT 0',
    
    # Failure tracking
    'download_error': 'TEXT',
    'failure_stage': 'VARCHAR(50)',
    'failure_reason': 'VARCHAR(50)',
    'failure_details': 'TEXT',
    
    # Dependency tracking
    'required_by_filings': 'JSONB DEFAULT \'[]\'::jsonb',
    'taxonomy_metadata': 'JSONB',
    
    # Timestamps
    'last_attempt_date': 'TIMESTAMP WITH TIME ZONE',
    'last_success_date': 'TIMESTAMP WITH TIME ZONE',
    'download_completed_at': 'TIMESTAMP WITH TIME ZONE',
    'last_verified_at': 'TIMESTAMP WITH TIME ZONE',
    'created_at': 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()',
    'updated_at': 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()',
}


def get_existing_columns() -> Set[str]:
    """Query database to get existing column names."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns
            WHERE table_name = 'taxonomy_libraries'
        """)
        
        columns = {row[0] for row in cursor.fetchall()}
        
        cursor.close()
        conn.close()
        
        return columns
        
    except Exception as e:
        print(f"ERROR connecting to database: {e}")
        return set()


def generate_migration_sql(missing_columns: List[str]) -> str:
    """Generate SQL migration for missing columns."""
    
    sql_parts = [
        "-- ============================================================================",
        "-- COMPLETE DATABASE MIGRATION - Add ALL Missing Columns",
        "-- ============================================================================",
        "-- Generated automatically by comparing model vs database",
        "-- ============================================================================\n",
        "DO $$",
        "DECLARE",
        "    column_count INTEGER := 0;",
        "BEGIN",
        "    RAISE NOTICE 'Adding ALL missing columns to taxonomy_libraries...';\n"
    ]
    
    for col_name in sorted(missing_columns):
        col_type = MODEL_COLUMNS[col_name]
        
        sql_parts.extend([
            f"    -- {col_name}",
            f"    IF NOT EXISTS (",
            f"        SELECT 1 FROM information_schema.columns",
            f"        WHERE table_name = 'taxonomy_libraries' AND column_name = '{col_name}'",
            f"    ) THEN",
            f"        ALTER TABLE taxonomy_libraries ADD COLUMN {col_name} {col_type};",
            f"        column_count := column_count + 1;",
            f"        RAISE NOTICE '  [+] Added {col_name}';",
            f"    ELSE",
            f"        RAISE NOTICE '  [✓] {col_name} already exists';",
            f"    END IF;\n"
        ])
    
    sql_parts.extend([
        "    RAISE NOTICE '';",
        "    RAISE NOTICE '============================================================================';",
        "    RAISE NOTICE 'Migration complete: Added % columns', column_count;",
        "    RAISE NOTICE '============================================================================';",
        "END $$;\n",
        "-- Verify all columns exist",
        "SELECT COUNT(*) as total_columns",
        "FROM information_schema.columns",
        "WHERE table_name = 'taxonomy_libraries';"
    ])
    
    return "\n".join(sql_parts)


def main():
    print("=" * 80)
    print("DATABASE SCHEMA COMPARISON")
    print("=" * 80)
    print()
    
    # Get existing columns from database
    print("Querying database for existing columns...")
    existing_columns = get_existing_columns()
    
    if not existing_columns:
        print("ERROR: Could not retrieve database columns!")
        return
    
    print(f"Found {len(existing_columns)} existing columns in database\n")
    
    # Compare with model
    model_columns = set(MODEL_COLUMNS.keys())
    missing_columns = model_columns - existing_columns
    extra_columns = existing_columns - model_columns
    
    print("=" * 80)
    print("ANALYSIS RESULTS")
    print("=" * 80)
    print()
    
    print(f"Total columns in MODEL: {len(model_columns)}")
    print(f"Total columns in DATABASE: {len(existing_columns)}")
    print(f"Missing from DATABASE: {len(missing_columns)}")
    print(f"Extra in DATABASE (not in model): {len(extra_columns)}")
    print()
    
    if missing_columns:
        print("MISSING COLUMNS (need to be added):")
        for col in sorted(missing_columns):
            print(f"  - {col}: {MODEL_COLUMNS[col]}")
        print()
        
        # Generate migration SQL
        migration_sql = generate_migration_sql(list(missing_columns))
        
        output_file = "FINAL_COMPLETE_MIGRATION.sql"
        with open(output_file, 'w') as f:
            f.write(migration_sql)
        
        print(f"✓ Generated complete migration: {output_file}")
        print()
        print("To apply:")
        print(f"  PGPASSWORD=malafat74 psql -h localhost -p 5432 -U a -d xbrl_coordination -f {output_file}")
    else:
        print("✓ All model columns exist in database!")
    
    if extra_columns:
        print()
        print("EXTRA COLUMNS in database (not defined in model):")
        for col in sorted(extra_columns):
            print(f"  - {col}")
        print()
        print("Note: These are harmless but could be removed if not needed")
    
    print()
    print("=" * 80)


if __name__ == '__main__':
    main()