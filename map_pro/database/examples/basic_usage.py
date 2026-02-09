# Path: database/examples/basic_usage.py
"""
Database Module Basic Usage Examples

Demonstrates common patterns for using the database module.
"""

from datetime import datetime, date
from database import (
    initialize_database,
    session_scope,
    Market,
    Entity,
    FilingSearch,
    DownloadedFiling,
    TaxonomyLibrary,
    get_logger,
)

logger = get_logger(__name__, 'core')


def example_initialization():
    """Example: Initialize database module."""
    print("\n" + "=" * 70)
    print("Example 1: Database Initialization")
    print("=" * 70)
    
    # Initialize database (call once at startup)
    initialize_database()
    print("✓ Database initialized")


def example_market_registration():
    """Example: Register a new market."""
    print("\n" + "=" * 70)
    print("Example 2: Market Registration")
    print("=" * 70)
    
    with session_scope() as session:
        # Check if market already exists
        sec = session.query(Market).filter_by(market_id='sec').first()
        
        if not sec:
            # Register SEC market
            sec = Market(
                market_id='sec',
                market_name='U.S. Securities and Exchange Commission',
                market_country='USA',
                api_base_url='https://www.sec.gov/cgi-bin/browse-edgar',
                is_active=True,
                rate_limit_per_minute=10,
                user_agent_required=True
            )
            session.add(sec)
            session.commit()
            print(f"✓ Registered market: {sec.market_name}")
        else:
            print(f"✓ Market already exists: {sec.market_name}")


def example_entity_creation():
    """Example: Create and verify entity."""
    print("\n" + "=" * 70)
    print("Example 3: Entity Creation with File Verification")
    print("=" * 70)
    
    with session_scope() as session:
        # Create entity
        entity = Entity(
            market_type='sec',
            market_entity_id='0001234567',
            company_name='BOEING CO',  # EXACT from search
            data_directory_path='/mnt/map_pro/data/entities/sec/BOEING_CO',
            entity_status='active',
            identifiers={
                'cik': '0001234567',
                'ticker': 'BA',
                'lei': 'XYZ123...'
            }
        )
        session.add(entity)
        session.commit()
        
        print(f"✓ Created entity: {entity.company_name}")
        print(f"  Entity ID: {entity.entity_id}")
        print(f"  Market: {entity.market_type}")
        
        # CRITICAL: Verify directory exists
        if entity.directory_exists:
            print(f"  ✓ Directory exists: {entity.data_directory_path}")
        else:
            print(f"  ⚠ Directory missing: {entity.data_directory_path}")
            print("    Create directory before using entity")


def example_search_to_download_pipeline():
    """Example: Complete search → download pipeline."""
    print("\n" + "=" * 70)
    print("Example 4: Search → Download Pipeline")
    print("=" * 70)
    
    # STEP 1: SEARCHER - Store search results
    print("\nSTEP 1: Searcher stores filing URLs")
    with session_scope() as session:
        entity = session.query(Entity).first()
        
        if not entity:
            print("⚠ No entities found - run example_entity_creation first")
            return
        
        search = FilingSearch(
            entity_id=entity.entity_id,
            market_type=entity.market_type,
            form_type='10-K',
            filing_date=date(2024, 12, 31),
            filing_url='https://www.sec.gov/Archives/edgar/data/1234567/...',
            accession_number='0001234567-24-000123',
            search_metadata={
                'search_timestamp': datetime.now().isoformat(),
                'search_query': {'cik': '0001234567', 'type': '10-K'}
            },
            download_status='pending'
        )
        session.add(search)
        session.commit()
        
        print(f"✓ Stored search result: {search.form_type}")
        print(f"  Filing URL: {search.filing_url}")
        print(f"  Status: {search.download_status}")
    
    # STEP 2: DOWNLOADER - Process pending downloads
    print("\nSTEP 2: Downloader processes pending filings")
    with session_scope() as session:
        pending = session.query(FilingSearch).filter_by(
            download_status='pending'
        ).all()
        
        print(f"Found {len(pending)} pending downloads")
        
        for filing_search in pending:
            # Simulate download
            download_path = f"/mnt/map_pro/data/entities/sec/BOEING_CO/filings/10-K/{filing_search.accession_number}"
            
            # Create download record
            downloaded = DownloadedFiling(
                search_id=filing_search.search_id,
                entity_id=filing_search.entity_id,
                download_directory=download_path,
                download_completed_at=datetime.now()
            )
            session.add(downloaded)
            
            # Update search status
            filing_search.download_status = 'completed'
            session.commit()
            
            print(f"✓ Downloaded filing to: {download_path}")
            
            # CRITICAL: Verify files exist
            if downloaded.files_actually_exist:
                print("  ✓ Files verified on disk")
            else:
                print("  ⚠ Files missing - download may have failed")


def example_taxonomy_workflow():
    """Example: Parser → Taxonomy downloader workflow."""
    print("\n" + "=" * 70)
    print("Example 5: Taxonomy Declaration and Download")
    print("=" * 70)
    
    # STEP 1: PARSER - Declare taxonomy from parsed.json
    print("\nSTEP 1: Parser declares taxonomy from parsed.json")
    with session_scope() as session:
        namespace = 'http://fasb.org/us-gaap/2024'  # From parsed.json
        
        library = session.query(TaxonomyLibrary).filter_by(
            taxonomy_namespace=namespace
        ).first()
        
        if not library:
            library = TaxonomyLibrary(
                taxonomy_name='us-gaap',
                taxonomy_version='2024',
                taxonomy_namespace=namespace,
                download_status='pending'
            )
            session.add(library)
            session.commit()
            print(f"✓ Declared new taxonomy: {library.taxonomy_name}/{library.taxonomy_version}")
        else:
            print(f"✓ Taxonomy already exists: {library.taxonomy_name}/{library.taxonomy_version}")
    
    # STEP 2: TAXONOMY DOWNLOADER - Process pending
    print("\nSTEP 2: Taxonomy downloader processes pending libraries")
    with session_scope() as session:
        pending = session.query(TaxonomyLibrary).filter_by(
            download_status='pending'
        ).all()
        
        print(f"Found {len(pending)} pending taxonomy downloads")
        
        for library in pending:
            # Simulate download
            library_path = f"/mnt/map_pro/data/taxonomies/{library.taxonomy_name}/{library.taxonomy_version}"
            
            library.library_directory = library_path
            library.source_url = f"https://xbrl.fasb.org/us-gaap/{library.taxonomy_version}/"
            library.download_status = 'completed'
            library.total_files = 150  # Simulated count
            library.download_completed_at = datetime.now()
            
            session.commit()
            
            print(f"✓ Downloaded taxonomy: {library.taxonomy_name}/{library.taxonomy_version}")
            print(f"  Path: {library_path}")
            
            # CRITICAL: Sync with reality
            sync_result = library.sync_with_reality()
            if sync_result['actual_files'] == 0:
                print(f"  ⚠ No files found - download may have failed")
                library.download_status = 'failed'
                session.commit()
            else:
                print(f"  ✓ Verified {sync_result['actual_files']} files on disk")


def example_file_verification():
    """Example: File verification patterns."""
    print("\n" + "=" * 70)
    print("Example 6: File Verification Patterns")
    print("=" * 70)
    
    with session_scope() as session:
        filing = session.query(DownloadedFiling).first()
        
        if not filing:
            print("⚠ No downloaded filings found")
            return
        
        print(f"\nVerifying filing {filing.filing_id}:")
        
        # Check download directory
        if filing.download_directory_exists:
            print("✓ Download directory exists")
        else:
            print("✗ Download directory missing")
        
        # Check files
        if filing.files_actually_exist:
            print("✓ Files exist on disk")
        else:
            print("✗ Files missing despite database status")
        
        # Check instance file
        if filing.instance_file_path:
            if filing.instance_file_exists:
                print(f"✓ Instance file exists: {filing.instance_file_path}")
            else:
                print(f"✗ Instance file missing: {filing.instance_file_path}")
        else:
            print("⚠ Instance file path not set")
        
        # Overall readiness
        if filing.ready_for_parsing:
            print("✓ READY FOR PARSING")
        else:
            print("✗ NOT READY - missing requirements")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("DATABASE MODULE USAGE EXAMPLES")
    print("=" * 70)
    
    try:
        example_initialization()
        example_market_registration()
        example_entity_creation()
        example_search_to_download_pipeline()
        example_taxonomy_workflow()
        example_file_verification()
        
        print("\n" + "=" * 70)
        print("ALL EXAMPLES COMPLETED")
        print("=" * 70)
        
    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
        print(f"\n✗ Error: {e}")


if __name__ == "__main__":
    main()