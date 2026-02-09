# XBRL Coordination Database

Metadata coordination layer for XBRL filing processing pipeline.

## Purpose

The database module serves as a **metadata exchange** between processing modules:
- **Searcher**: Stores filing URLs found from market APIs
- **Downloader**: Reads URLs, updates download status
- **Extractor**: Processes downloaded files, updates extraction status
- **Taxonomy**: Manages standard taxonomy library declarations and downloads

## Critical Design Principles

### 1. Database is Metadata - Filesystem is Truth

```python
# ✓ CORRECT - Always verify reality
if filing.files_actually_exist:
    parser.parse(filing.instance_file_path)
else:
    logger.error("Files missing despite database status")

# ✗ WRONG - Trust database blindly
if filing.download_status == 'completed':
    parser.parse(filing.instance_file_path)  # Files might not exist!
```

### 2. File Existence Verification

Every model with file paths has verification properties:

```python
entity.directory_exists          # Check if directory exists
filing.files_actually_exist      # Check if files exist
filing.ready_for_parsing         # Check if ready to parse
library.is_truly_available       # Check if library usable
```

### 3. Market Agnostic

```python
# Works for ANY market
entity = Entity(
    market_type='sec',                    # 'sec', 'frc', 'esma', etc.
    market_entity_id='0001234567',        # CIK, company number, etc.
    identifiers={'cik': '0001234567'}     # Flexible JSON storage
)
```

### 4. Name Preservation

```python
# EXACT from source - never normalized
entity.company_name = 'BOEING CO'  # From API exactly
filing.form_type = '10-K'          # From API exactly
library.taxonomy_namespace = 'http://fasb.org/us-gaap/2024'  # From parsed.json exactly
```

## Database Schema

Five tables only (simplified for metadata coordination):

### 1. markets
Reference data for all supported regulatory markets.
```sql
market_id (PK)           -- 'sec', 'frc', 'esma'
market_name              -- Full market name
market_country           -- ISO country code
api_base_url             -- Market API endpoint
```

### 2. entities
Company registry across all markets.
```sql
entity_id (PK, UUID)
market_type (FK → markets)
market_entity_id         -- CIK, company number, etc.
company_name             -- EXACT from search
data_directory_path      -- Where files stored
identifiers (JSONB)      -- Flexible ID storage
```

### 3. filing_searches
Search results from market APIs.
```sql
search_id (PK, UUID)
entity_id (FK → entities)
form_type                -- EXACT from API
filing_date
filing_url               -- EXACT URL from API
download_status          -- pending, completed, failed
extraction_status        -- pending, completed, failed, not_needed
```

### 4. downloaded_filings
Downloaded and extracted filing tracking.
```sql
filing_id (PK, UUID)
search_id (FK → filing_searches)
download_directory       -- Where downloaded
extraction_directory     -- Where extracted (if needed)
instance_file_path       -- Main XBRL document
```

### 5. taxonomy_libraries
Standard taxonomy library registry.
```sql
library_id (PK, UUID)
taxonomy_name            -- 'us-gaap', 'ifrs-full'
taxonomy_version         -- '2024'
taxonomy_namespace       -- Full URI (unique)
library_directory        -- Where files stored
download_status          -- pending, completed, failed
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `env.py` to `.env` and configure:

```bash
cp env.py .env
nano .env
```

Key settings:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=xbrl_coordination
DB_USER=your_username
DB_PASSWORD=your_password

DB_ROOT_DIR=/mnt/map_pro/database
DB_LOG_DIR=/mnt/map_pro/database/logs
DB_POSTGRESQL_DATA_DIR=/mnt/map_pro/database/postgresql_data

DATA_ENTITIES_DIR=/mnt/map_pro/data/entities
DATA_TAXONOMIES_DIR=/mnt/map_pro/data/taxonomies
```

### 3. Initialize Database

```bash
python -m database.setup
```

## Usage Examples

### Initialization

```python
from database import initialize_database

# Initialize once at application startup
initialize_database()
```

### Working with Entities

```python
from database import session_scope, Entity

# Create entity from search result
with session_scope() as session:
    entity = Entity(
        market_type='sec',
        market_entity_id='0001234567',
        company_name='BOEING CO',  # EXACT from API
        data_directory_path='/mnt/map_pro/data/entities/sec/BOEING_CO',
        identifiers={'cik': '0001234567', 'ticker': 'BA'}
    )
    session.add(entity)
    session.commit()

# Verify before use
with session_scope() as session:
    entity = session.query(Entity).first()
    
    if entity.directory_exists:
        print(f"Processing {entity.company_name}")
        process_entity(entity)
    else:
        print(f"Directory missing for {entity.company_name}")
```

### Searcher → Downloader Pipeline

```python
from database import session_scope, FilingSearch, DownloadedFiling
from datetime import datetime

# SEARCHER: Store search results
with session_scope() as session:
    search = FilingSearch(
        entity_id=entity_id,
        market_type='sec',
        form_type='10-K',
        filing_date=datetime(2024, 12, 31).date(),
        filing_url='https://www.sec.gov/...',  # EXACT URL
        download_status='pending'
    )
    session.add(search)

# DOWNLOADER: Process pending downloads
with session_scope() as session:
    pending = session.query(FilingSearch).filter_by(
        download_status='pending'
    ).all()
    
    for filing_search in pending:
        # Download file
        download_path = downloader.download(filing_search.filing_url)
        
        # Create tracking record
        downloaded = DownloadedFiling(
            search_id=filing_search.search_id,
            entity_id=filing_search.entity_id,
            download_directory=download_path,
            download_completed_at=datetime.now()
        )
        session.add(downloaded)
        
        # Update status
        filing_search.download_status = 'completed'
        session.commit()
```

### Parser → Taxonomy Downloader

```python
from database import session_scope, TaxonomyLibrary

# PARSER: Declare taxonomy from parsed.json
with session_scope() as session:
    namespace = 'http://fasb.org/us-gaap/2024'  # From parsed.json
    
    library = session.query(TaxonomyLibrary).filter_by(
        taxonomy_namespace=namespace
    ).first()
    
    if not library:
        # New taxonomy declaration
        library = TaxonomyLibrary(
            taxonomy_name='us-gaap',
            taxonomy_version='2024',
            taxonomy_namespace=namespace,
            download_status='pending'
        )
        session.add(library)
        session.commit()

# TAXONOMY DOWNLOADER: Process pending libraries
with session_scope() as session:
    pending = session.query(TaxonomyLibrary).filter_by(
        download_status='pending'
    ).all()
    
    for library in pending:
        # Download taxonomy
        download_path = taxonomy_downloader.download(library.taxonomy_namespace)
        
        library.library_directory = download_path
        library.download_status = 'completed'
        
        # CRITICAL: Verify files exist
        sync_result = library.sync_with_reality()
        if sync_result['actual_files'] == 0:
            logger.error(f"Download failed - no files for {library.taxonomy_name}")
            library.download_status = 'failed'
        
        session.commit()
```

### File Verification Pattern

```python
# Always verify before use
with session_scope() as session:
    filing = session.query(DownloadedFiling).first()
    
    # Multiple verification levels
    if filing.files_actually_exist:
        print("✓ Files exist on disk")
        
        if filing.instance_file_exists:
            print("✓ Instance file found")
            
            if filing.ready_for_parsing:
                print("✓ Ready for parser")
                parser.parse(filing.instance_file_path)
            else:
                print("✗ Not ready - missing requirements")
        else:
            print("✗ Instance file not found")
    else:
        print("✗ Files missing despite database status")
```

## Module Integration

Other modules import database as needed:

```python
# In searcher module
from database import session_scope, Entity, FilingSearch

# In downloader module
from database import session_scope, FilingSearch, DownloadedFiling

# In extractor module
from database import session_scope, DownloadedFiling

# In taxonomy module
from database import session_scope, TaxonomyLibrary
```

## Logging

Database module uses centralized logging:

```python
from database.core.logger import get_logger

logger = get_logger(__name__, 'models')
logger.info("Entity created successfully")
```

Logs written to: `/mnt/map_pro/database/logs/database_activity.log`

## Directory Structure

```
/mnt/map_pro/database/
├── logs/                           # Database activity logs
├── postgresql_data/                # PostgreSQL data files
└── .env                           # Configuration (not in repo)

database/                           # Module source
├── __init__.py                    # Main module exports
├── setup.py                       # Setup script
├── env.py                         # Environment template
├── requirements.txt               # Dependencies
├── constants.py                   # Constants (no hardcoding)
├── core/
│   ├── __init__.py
│   ├── config_loader.py          # Configuration management
│   ├── data_paths.py             # Directory management
│   └── logger.py                 # Centralized logging
└── models/
    ├── __init__.py
    ├── base.py                   # SQLAlchemy base
    ├── markets.py                # Market registry
    ├── entities.py               # Entity tracking
    ├── filing_searches.py        # Search results
    ├── downloaded_filings.py     # Download tracking
    └── taxonomy_libraries.py     # Taxonomy registry
```

## Future Integration

Database module designed for future central logging integration:

```python
# Future: System-wide logger
from core.system_logger import get_logger  # Central system logger

# Current: Module-specific logger
from database.core.logger import get_logger  # Database logger
```

Logger interfaces identical - seamless migration when ready.