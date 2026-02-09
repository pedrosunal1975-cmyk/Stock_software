# CLAUDE.md - AI Assistant Guide for MAP PRO

**Last Updated:** 2026-01-24
**Repository:** MAP PRO (Multi-market XBRL Analysis Platform)
**Purpose:** Comprehensive guide for AI assistants working on this codebase

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Repository Structure](#repository-structure)
3. [Critical Coding Standards](#critical-coding-standards)
4. [Development Workflow](#development-workflow)
5. [Module Descriptions](#module-descriptions)
6. [Configuration Management](#configuration-management)
7. [Testing Conventions](#testing-conventions)
8. [Common Operations](#common-operations)
9. [File Organization Rules](#file-organization-rules)
10. [Tech Stack & Dependencies](#tech-stack--dependencies)

---

## Project Overview

**MAP PRO** is a production-grade, enterprise-level XBRL (eXtensible Business Reporting Language) financial filing processing system designed to search, download, parse, and extract financial data from regulatory filings across multiple markets (SEC, FCA, ESMA, etc.).

### Core Philosophy

The system is built on **strict architectural principles**:

1. **Market Agnostic** - Supports any regulatory market (SEC, ESMA, FCA, etc.)
2. **Taxonomy Agnostic** - Handles any XBRL taxonomy (US-GAAP, IFRS, UK-GAAP, custom)
3. **Database Reflects Reality** - Filesystem is the source of truth, database is metadata
4. **No Hardcoding** - All configurations externalized to `.env` and config files
5. **Modular Architecture** - Six independent, reusable modules
6. **Output Separation** - Program files vs. data files strictly separated

### Project Goals

- Process XBRL filings from multiple regulatory markets
- Extract financial statements EXACTLY as declared by companies (no transformation)
- Support extensibility for new markets and taxonomies
- Maintain production-grade quality with comprehensive error handling
- Enable reusability of components across different projects

---

## Repository Structure

```
/home/user/map_pro/
├── database/           # Metadata coordination layer (PostgreSQL + SQLAlchemy)
│   ├── core/           # Database configuration and utilities
│   ├── models/         # SQLAlchemy models (markets, entities, filings, taxonomies)
│   ├── operations/     # Database operations and queries
│   └── setup.py
│
├── searcher/           # Filing search across regulatory markets
│   ├── core/           # Searcher configuration
│   ├── engine/         # Search orchestration
│   └── markets/        # Market-specific implementations (SEC, ESMA, FCA)
│
├── downloader/         # Downloads XBRL filings and taxonomy libraries
│   ├── core/           # Downloader configuration
│   ├── engine/         # Download coordinator, archive processor, retry manager
│   └── download.py     # CLI entry point
│
├── library/            # Taxonomy library management
│   ├── core/           # Library configuration
│   ├── engine/         # Library coordinator, taxonomy reader
│   └── library.py      # CLI entry point
│
├── parser/             # Parse XBRL instance documents to JSON
│   ├── xbrl_parser/    # Main parsing package
│   │   ├── foundation/ # XML parsing, namespace handling
│   │   ├── instance/   # Instance document parsing
│   │   ├── taxonomy/   # Taxonomy loading and management
│   │   ├── ixbrl/      # Inline XBRL support
│   │   ├── validation/ # Validation framework
│   │   └── market/     # Market-specific logic (ONLY place for market code)
│   ├── core/           # Configuration management
│   └── parser.py       # CLI entry point
│
├── mapper/             # Extract financial statements from parsed filings
│   ├── mapping/        # Statement extraction logic
│   │   ├── orchestrator.py      # Main workflow coordinator
│   │   ├── statement_builder.py # Builds statements from linkbases
│   │   └── dimension_handler.py # Handles XBRL dimensions
│   ├── core/           # Mapper configuration
│   └── mapper.py       # CLI entry point
│
├── env                 # MASTER configuration file (all modules)
├── standards.py        # Complete coding standards and validation functions
├── standards_checker.py # Automated standards compliance checker
└── README.md

/mnt/map_pro/          # DATA PARTITION (all outputs go here)
├── downloader/
│   ├── entities/      # Downloaded filings by market/company
│   ├── temp/          # Temporary downloads
│   └── logs/          # Download logs
│
├── taxonomies/
│   ├── libraries/     # Standard taxonomies (us-gaap, ifrs, etc.)
│   ├── manual_downloads/  # Manual taxonomy staging
│   └── cache/         # Taxonomy cache
│
├── parser/
│   ├── parsed_reports/  # Parser outputs (parsed.json, facts.csv, summary.txt)
│   ├── cache/taxonomies/  # Taxonomy cache
│   └── logs/          # Parser logs
│
├── mapper/
│   ├── mapped_statements/  # Extracted financial statements
│   └── logs/          # Mapper logs
│
└── database/
    ├── postgresql_data/  # PostgreSQL data files
    └── logs/          # Database logs
```

---

## Critical Coding Standards

**READ `standards.py` BEFORE ANY CODING WORK**

The project has **strict, non-negotiable coding standards** defined in `standards.py`. All code must comply with these principles:

### 1. **NO HARDCODE - Nowhere and on no subject**

```python
# FORBIDDEN
url = "https://data.sec.gov/submissions/CIK0000320193.json"
path = "/home/user/data/filings"

# CORRECT
from core.config_loader import ConfigLoader
config = ConfigLoader()
url = config.sec_submissions_url.format(cik=cik)
path = config.entities_dir
```

**Rules:**
- NO URLs/URIs in code
- NO file paths in code
- NO IP addresses, hostnames
- Use `.env` + `core/config_loader.py` for ALL configuration
- Exceptions: Comments, docstrings, test fixtures (clearly marked)

### 2. **MARKET AGNOSTIC - Only in `/market/` directory**

```python
# FORBIDDEN (outside market/)
if "us-gaap" in namespace:
    # Market-specific logic

# CORRECT (use registry pattern)
from xbrl_parser.market import MarketRegistry
validator = MarketRegistry.get_validator(market_code)
validator.validate(filing)
```

**Rules:**
- Market-specific code ONLY in `xbrl_parser/market/` directory
- Rest of system must work for ANY market
- Use market detector + registry pattern
- Keywords to avoid outside `/market/`: us-gaap, sec, edgar, ifrs, esef, esma, uk-gaap, frc

### 3. **TAXONOMY AGNOSTIC - Support any taxonomy**

```python
# FORBIDDEN
if concept == "us-gaap:Assets":
    process_assets()

# CORRECT (generic namespace handling)
namespace = get_namespace(concept)
taxonomy = load_taxonomy(namespace)
element = taxonomy.get_element(concept)
```

**Rules:**
- No hardcoded taxonomy namespaces
- No hardcoded concept names
- Generic taxonomy loading for any taxonomy
- Extensible taxonomy support

### 4. **OUTPUT LOCATION - NEVER write to program files**

```python
# FORBIDDEN
output_path = "xbrl_parser/output/parsed.json"  # In program directory!

# CORRECT
from core.config_loader import ConfigLoader
config = ConfigLoader()
output_path = config.output_parsed_dir / market / company / form / date / "parsed.json"
# Writes to: /mnt/map_pro/parser/parsed_reports/sec/apple/10-K/2024-09-30/parsed.json
```

**Rules:**
- **NEVER EVER** write reports/data under project files
- Program files: `.py`, `.env`, `config`, `__init__.py`, source code
- Data files: `.json`, `.xml`, `.htm`, `.txt`, `.csv`, any generated output
- Always write to DATA PARTITION (`/mnt/map_pro/`)
- If unsure, ask user for correct data partition location

### 5. **PATH REGIME CHECK - Before adding ANY path**

**CRITICAL WORKFLOW:**

```python
# Before adding a new path, you MUST:
# 1. Read /home/user/map_pro/env completely
# 2. Read core/data_paths.py to understand path construction
# 3. Read core/config_loader.py to see how paths are loaded
# 4. Check if required path already exists
# 5. If exists: USE IT (stop creating duplicates!)
# 6. If not exists: Add following existing patterns
```

**Example:**
```bash
# BAD: Adding PARSER_LOGS_DIR when PARSER_LOG_DIR already exists
# GOOD: Use existing PARSER_LOG_DIR

# BAD: Creating PARSER_CACHE_PATH separately
# GOOD: Use ${PARSER_DATA_ROOT}/cache pattern in .env
```

### 6. **FILE HEADER PATH - Every Python file**

```python
# Path: xbrl_parser/foundation/xml_parser.py
"""
XML Parser for XBRL documents.

This module provides XML parsing capabilities with namespace handling.
"""

import os
from pathlib import Path
```

**Rules:**
- FIRST line of EVERY Python file
- Format: `# Path: relative/path/from/project/root.py`
- Start from project root (e.g., `parser/`, `database/`, `mapper/`)
- Use forward slashes, no leading slash
- Include `.py` extension
- Add to ANY file missing this header

### 7. **TEST LOCATION - Organized structure**

```
parser/tests/
├── unit/
│   ├── test_foundation/
│   ├── test_instance/
│   └── test_taxonomy/
├── integration/
├── regression/
└── fixtures/
```

**Rules:**
- Tests under `{module}/tests/` directory
- Structure: `tests/unit/test_<component>/`
- Naming: `test_<functionality>.py`
- NEVER create tests in root or random locations

### 8. **ASCII ONLY - No emojis anywhere**

```python
# FORBIDDEN
print("✓ Success")
log.info("⚠️ Warning")

# CORRECT
print("[OK] Success")
log.info("[WARN] Warning")
```

**Rules:**
- ASCII characters only (0x00 to 0x7F)
- No emoji characters (U+1F300 to U+1F9FF)
- No Unicode symbols beyond ASCII
- Use: `[OK]` `[FAIL]` `[WARN]` `->` `*` instead of emojis

### 9. **FOLDER TREE - Always verify first**

**Before writing ANY new files:**
1. Ask user for current folder tree (Claude sees files flat)
2. Create virtual copy of folder structure
3. Verify file locations
4. DO NOT forget `__init__.py` files in folder tree

---

## Development Workflow

### Setting Up the Environment

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd map_pro
   ```

2. **Install dependencies for each module:**
   ```bash
   # Database module
   cd database && pip install -r requirements.txt

   # Parser module
   cd parser && pip install -r requirements.txt

   # Mapper module
   cd mapper && pip install -r requirements.txt
   ```

3. **Configure environment:**
   - Master config: `/home/user/map_pro/env`
   - Edit database credentials, paths, API settings
   - Verify all paths point to `/mnt/map_pro/` (data partition)

4. **Initialize database:**
   ```bash
   cd database
   python -m database.operations.initialize
   ```

5. **Create data directories:**
   ```bash
   # Data partition structure created automatically by modules
   # Or manually create:
   mkdir -p /mnt/map_pro/{downloader,taxonomies,parser,mapper,database}/{logs,cache}
   ```

### Development Guidelines

1. **Before starting work:**
   - Read `standards.py` completely
   - Review module's `README.md` if exists
   - Check current branch (`claude/claude-md-mkrwjitjf5zlmlpw-pd3ZR`)
   - Verify folder structure

2. **While coding:**
   - Run `python standards_checker.py` regularly
   - Add `# Path:` header to all new files
   - Use type hints on all functions
   - Write docstrings (Google or NumPy style)
   - No hardcoded values - use config loader

3. **Before committing:**
   - Run standards checker: `python standards_checker.py`
   - Run tests: `pytest tests/`
   - Run type checker: `mypy module_name/`
   - Run linter: `flake8 module_name/`
   - Format code: `black module_name/` and `isort module_name/`

4. **Commit conventions:**
   - Concise messages focusing on "why" not "what"
   - Use git HEREDOC for multi-line messages
   - Follow existing commit style (check `git log`)
   - Commit message draft should analyze ALL changes

### Code Quality Standards

```python
# Complexity thresholds
MAX_CYCLOMATIC_COMPLEXITY = 10
MAX_FUNCTION_LENGTH = 50  # lines
MAX_CLASS_LENGTH = 300    # lines
MAX_LINE_LENGTH = 100     # characters

# Coverage targets
MIN_UNIT_TEST_COVERAGE = 80%
MIN_INTEGRATION_TEST_COVERAGE = 70%
TARGET_OVERALL_COVERAGE = 95%
```

---

## Module Descriptions

### 1. Database Module (`/database/`)

**Purpose:** Metadata coordination layer for entire processing pipeline

**Key Models:**
- `markets` - Registry of regulatory markets (SEC, FRC, ESMA)
- `entities` - Company registry across all markets
- `filing_searches` - Search results from market APIs
- `downloaded_filings` - Downloaded filing tracking with filesystem verification
- `taxonomy_libraries` - Standard taxonomy registry with integrity checks

**Philosophy:**
- Database is metadata exchange hub, NOT source of truth
- Always verify filesystem before trusting database
- Properties: `files_actually_exist`, `ready_for_parsing`, `is_truly_available`

**Usage:**
```python
from database.models import DownloadedFiling, TaxonomyLibrary
from database.operations import FilingQueries

# Query filings ready for parsing
filings = FilingQueries.get_ready_for_parsing(market='sec', limit=10)

# Verify filesystem reality
for filing in filings:
    if filing.files_actually_exist:
        process_filing(filing.directory_path)
```

### 2. Searcher Module (`/searcher/`)

**Purpose:** Interactive filing search across multiple regulatory markets

**Supported Markets:**
- SEC (primary implementation)
- ESMA (extensible)
- FCA (extensible)

**Features:**
- Market-specific search implementations
- Registry pattern for extensibility
- Database integration for storing search results
- Interactive CLI and programmatic API

**Usage:**
```python
from searcher.engine import SearchCoordinator

coordinator = SearchCoordinator()
results = coordinator.search(
    market='sec',
    company='Apple Inc',
    form_type='10-K',
    date_from='2023-01-01'
)
# Results stored in database.models.filing_searches
```

### 3. Downloader Module (`/downloader/`)

**Purpose:** Downloads XBRL filings and taxonomy libraries with streaming and retry logic

**Key Components:**
- `DownloadCoordinator` - Main workflow orchestrator
- `ArchiveDownloader` - Handles file downloads with resume capability
- `DistributionProcessor` - Distribution-agnostic extraction (ZIP, tar.gz, single files)
- `RetryManager` - Intelligent retry with exponential backoff
- `PathResolver` - Routes downloads to correct destinations

**Features:**
- Streaming downloads for large files
- Archive auto-detection and extraction
- Database synchronization post-download
- Handles both filings and taxonomies

**Output Locations:**
- Filings: `/mnt/map_pro/downloader/entities/{market}/{company}/filings/{form}/{accession}/`
- Taxonomies: `/mnt/map_pro/taxonomies/libraries/`

**Usage:**
```python
from downloader import DownloadCoordinator

coordinator = DownloadCoordinator()
await coordinator.process_pending_downloads(limit=5)
```

**CLI Entry Point:**
```bash
cd downloader
python download.py
```

### 4. Library Module (`/library/`)

**Purpose:** Taxonomy library management - monitors parsed filings and ensures required taxonomies are available

**Workflow:**
1. Monitors parsed filing outputs
2. Detects taxonomy requirements from `parsed.json`
3. Registers missing taxonomies in database
4. Triggers downloads via downloader
5. Verifies availability before mapper runs

**Key Components:**
- `LibraryCoordinator` - Monitoring and orchestration
- `TaxonomyReader` - Reads taxonomy metadata
- `ManualProcessor` - Handles manual taxonomy downloads

**Usage:**
```python
from library.engine.coordinator import LibraryCoordinator

coordinator = LibraryCoordinator()
results = coordinator.process_new_filings()
```

**CLI Entry Point:**
```bash
cd library
python library.py
```

### 5. Parser Module (`/parser/`)

**Purpose:** Parse XBRL instance documents into structured JSON format

**Architecture:** `/parser/xbrl_parser/` - main parsing package

**Key Components:**
- `XBRLParser` - Main orchestrator and entry point
- `EntryPointDetector` - Universal entry point detection (any market)
- `InstanceParser` - Parses XBRL instance documents
- `TaxonomyService` - Loads and manages taxonomy schemas
- `ValidationRegistry` - Market-specific validation

**Parsing Modes:**
- `FULL` - Complete parsing with all data
- `FACTS_ONLY` - Only fact extraction
- `METADATA_ONLY` - Only metadata extraction

**Output Structure:**
```
/mnt/map_pro/parser/parsed_reports/{market}/{company}/{form}/{date}/
├── parsed.json      # Complete structured data
├── facts.csv        # Fact table export
├── summary.txt      # Human-readable report
└── workbook.xlsx    # Optional Excel export
```

**Usage:**
```python
from xbrl_parser import XBRLParser

parser = XBRLParser()
filing = parser.parse('/mnt/map_pro/downloader/entities/sec/apple/filings/10-K/...')
```

**CLI Entry Point:**
```bash
cd parser
python parser.py /path/to/filing.xml
```

### 6. Mapper Module (`/mapper/`)

**Purpose:** Extract financial statements EXACTLY as declared by companies (no transformation)

**Design Principle:** "WATER" - takes the shape of container (company's presentation linkbase)

**Key Components:**
- `MappingOrchestrator` - Coordinates extraction workflow
- `StatementBuilder` - Builds statements from presentation linkbase
- `FilingCharacteristicsExtractor` - Extracts filing metadata
- `LinkbaseLocator` - Finds presentation/calculation linkbases
- `DimensionHandler` - Handles XBRL dimensions
- `PeriodNormalizer` - Normalizes reporting periods

**Workflow:**
1. Reads `parsed.json` from parser output
2. Locates presentation linkbase
3. Extracts company's declared structure
4. Exports statements (JSON, CSV, Excel)

**Output Location:**
```
/mnt/map_pro/mapper/mapped_statements/{market}/{company}/{form}/{date}/
```

**Usage:**
```python
from mapping.orchestrator import MappingOrchestrator

orchestrator = MappingOrchestrator()
result = orchestrator.extract_and_export(parsed_json_path)
```

**CLI Entry Point:**
```bash
cd mapper
python mapper.py /path/to/parsed.json
```

---

## Configuration Management

### Master Configuration File

**Location:** `/home/user/map_pro/env`

All modules read from this centralized configuration file. It contains:

1. **Shared Database Configuration** (all modules)
   - PostgreSQL connection settings
   - Connection pool configuration

2. **Shared Data Paths** (all modules)
   - `DATA_ENTITIES_DIR=/mnt/map_pro/downloader/entities`
   - `DATA_TAXONOMIES_DIR=/mnt/map_pro/taxonomies/libraries`

3. **Module-Specific Sections:**
   - `SEARCHER_*` - Searcher configuration
   - `DOWNLOADER_*` - Downloader configuration
   - `DB_*` - Database configuration
   - `LIBRARY_*` - Library configuration
   - `PARSER_*` - Parser configuration
   - `MAPPER_*` - Mapper configuration

### Configuration Loading Pattern

Each module has:
- `core/config_loader.py` - Loads configuration from `.env`
- `core/data_paths.py` - Path construction and auto-creation logic

**Example:**
```python
# Path: parser/core/config_loader.py
from pathlib import Path
import os
from dotenv import load_dotenv

class ConfigLoader:
    def __init__(self):
        # Load from master .env
        load_dotenv('/home/user/map_pro/env')

        self.data_root = Path(os.getenv('PARSER_DATA_ROOT'))
        self.output_dir = Path(os.getenv('PARSER_OUTPUT_PARSED_DIR'))
        self.taxonomy_cache = Path(os.getenv('PARSER_TAXONOMY_CACHE_DIR'))

    def _get_path(self, env_var: str) -> Path:
        """Get path from environment with interpolation support."""
        value = os.getenv(env_var)
        if value and '${' in value:
            # Handle interpolation: ${PARSER_DATA_ROOT}/cache
            value = os.path.expandvars(value)
        return Path(value) if value else None
```

### Environment Variable Interpolation

```bash
# In .env file
PARSER_DATA_ROOT=/mnt/map_pro/parser
PARSER_OUTPUT_DIR=${PARSER_DATA_ROOT}/parsed_reports
PARSER_CACHE_DIR=${PARSER_DATA_ROOT}/cache/taxonomies
PARSER_LOG_DIR=${PARSER_DATA_ROOT}/logs
```

---

## Testing Conventions

### Test Structure

```
{module}/tests/
├── unit/                    # Unit tests
│   ├── test_foundation/
│   ├── test_instance/
│   └── test_taxonomy/
├── integration/             # Integration tests
├── regression/              # Regression tests
└── fixtures/                # Test data and fixtures
```

### Testing Tools

```bash
# Main testing framework
pytest>=7.4.0
pytest-cov>=4.1.0          # Coverage
pytest-asyncio>=0.21.0     # Async tests

# Testing utilities
hypothesis>=6.82.0         # Property-based testing
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=xbrl_parser --cov-report=html

# Run specific test file
pytest tests/unit/test_foundation/test_xml_parser.py

# Run with verbose output
pytest tests/ -v

# Run only integration tests
pytest tests/integration/
```

### Writing Tests

```python
# Path: parser/tests/unit/test_foundation/test_xml_parser.py
"""
Unit tests for XML parser component.
"""

import pytest
from xbrl_parser.foundation import XMLParser

class TestXMLParser:
    """Test cases for XMLParser class."""

    def test_parse_valid_xml(self):
        """Test parsing valid XML document."""
        parser = XMLParser()
        doc = parser.parse('<root><child>value</child></root>')
        assert doc is not None
        assert doc.tag == 'root'

    def test_parse_invalid_xml_raises_error(self):
        """Test that invalid XML raises appropriate error."""
        parser = XMLParser()
        with pytest.raises(ValueError):
            parser.parse('<invalid')
```

### Coverage Targets

- **Minimum Unit Test Coverage:** 80%
- **Minimum Integration Test Coverage:** 70%
- **Target Overall Coverage:** 95%

---

## Common Operations

### Processing Pipeline (End-to-End)

```bash
# 1. Search for filings
cd searcher
python searcher.py --market sec --company "Apple Inc" --form "10-K"

# 2. Download filings
cd ../downloader
python download.py  # Interactive CLI

# 3. Parse filings
cd ../parser
python parser.py /mnt/map_pro/downloader/entities/sec/apple/filings/10-K/.../instance.xml

# 4. Library checks taxonomies (automatic monitoring)
cd ../library
python library.py  # Runs in background monitoring mode

# 5. Extract financial statements
cd ../mapper
python mapper.py /mnt/map_pro/parser/parsed_reports/sec/apple/10-K/2024-09-30/parsed.json
```

### Programmatic Usage

```python
# Complete pipeline
from searcher.engine import SearchCoordinator
from downloader import DownloadCoordinator
from xbrl_parser import XBRLParser
from mapping.orchestrator import MappingOrchestrator

# 1. Search
searcher = SearchCoordinator()
results = searcher.search(market='sec', company='Apple Inc', form_type='10-K')

# 2. Download
downloader = DownloadCoordinator()
await downloader.process_pending_downloads()

# 3. Parse
parser = XBRLParser()
filing = parser.parse('/path/to/filing.xml')

# 4. Map (extract statements)
mapper = MappingOrchestrator()
statements = mapper.extract_and_export('/path/to/parsed.json')
```

### Standards Compliance Check

```bash
# Run automated standards checker
python standards_checker.py

# Check specific module
python standards_checker.py parser/

# Check with detailed output
python standards_checker.py --verbose
```

### Database Operations

```python
from database.operations import FilingQueries, EntityQueries

# Get filings ready for parsing
filings = FilingQueries.get_ready_for_parsing(market='sec', limit=10)

# Find entity by name
entity = EntityQueries.find_by_name('Apple Inc')

# Get filings for entity
filings = FilingQueries.get_by_entity(entity.id, form_type='10-K')
```

### Logging

Each module uses **IPO Logging Pattern:**

```python
# Input/Process/Output segregated logs
{module}/logs/
├── input.log      # Input data and requests
├── process.log    # Processing operations
├── output.log     # Generated outputs
└── full.log       # Complete log (all events)
```

**Configuration (in .env):**
```bash
PARSER_LOG_DIR=/mnt/map_pro/parser/logs
PARSER_LOG_FORMAT=json              # or 'text'
PARSER_LOG_ROTATION=daily
PARSER_LOG_RETENTION_DAYS=30
PARSER_LOG_MAX_SIZE_MB=10
PARSER_LOG_LEVEL=INFO
```

---

## File Organization Rules

### Python File Structure

```python
# Path: xbrl_parser/foundation/xml_parser.py
"""
XML Parser for XBRL documents.

This module provides XML parsing capabilities with proper namespace
handling and error recovery.

Classes:
    XMLParser: Main XML parsing class
    NamespaceHandler: Namespace management utility

Usage:
    parser = XMLParser()
    doc = parser.parse('filing.xml')
"""

from pathlib import Path
from typing import Optional, Dict, Any
import logging

# Constants (from config, not hardcoded!)
from core.config_loader import ConfigLoader

logger = logging.getLogger(__name__)
config = ConfigLoader()


class XMLParser:
    """
    Parse XML documents with namespace handling.

    Args:
        encoding: Character encoding for XML files
        remove_blank_text: Whether to remove blank text nodes

    Attributes:
        encoding: Character encoding
        parser: Underlying XML parser instance
    """

    def __init__(self, encoding: str = 'utf-8', remove_blank_text: bool = True):
        self.encoding = encoding
        self.parser = self._create_parser(remove_blank_text)

    def parse(self, source: str | Path) -> Any:
        """
        Parse XML from file or string.

        Args:
            source: File path or XML string

        Returns:
            Parsed XML document

        Raises:
            ValueError: If XML is invalid
            FileNotFoundError: If file does not exist
        """
        # Implementation
        pass
```

### Directory Naming Conventions

- **Modules:** lowercase with underscores (`xbrl_parser`, `config_loader`)
- **Packages:** lowercase, short, descriptive (`foundation`, `instance`, `taxonomy`)
- **Classes:** PascalCase (`XMLParser`, `DownloadCoordinator`)
- **Functions:** snake_case (`parse_filing`, `get_taxonomy`)
- **Constants:** UPPER_CASE (`MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Private:** prefix with underscore (`_internal_method`, `_helper_function`)

### Import Organization

```python
# 1. Standard library imports
import os
import sys
from pathlib import Path
from typing import Optional, Dict, List

# 2. Third-party imports
import lxml.etree as ET
from sqlalchemy import select

# 3. Local application imports
from core.config_loader import ConfigLoader
from xbrl_parser.foundation import XMLParser
from database.models import DownloadedFiling
```

**Use `isort` to maintain import order:**
```bash
isort module_name/
```

---

## Tech Stack & Dependencies

### Core Technologies

- **Language:** Python 3.12+
- **Database:** PostgreSQL with SQLAlchemy ORM
- **Async:** asyncio for downloader operations
- **XML Processing:** lxml, ElementTree
- **HTTP:** aiohttp for async downloads

### Key Dependencies

#### XBRL Processing
```
arelle-release>=2.3.0      # XBRL processing library
lxml>=4.9.0                # XML parsing
```

#### Data & Validation
```
pydantic>=2.0.0            # Data validation
requests>=2.31.0           # HTTP requests
tenacity>=8.2.0            # Retry logic
openpyxl>=3.1.0            # Excel export
```

#### Database
```
sqlalchemy>=2.0.0          # ORM
postgresql                 # Database
psycopg2-binary            # PostgreSQL adapter
```

#### Testing
```
pytest>=7.4.0              # Testing framework
pytest-cov>=4.1.0          # Coverage
pytest-asyncio>=0.21.0     # Async tests
hypothesis>=6.82.0         # Property-based testing
```

#### Code Quality
```
mypy>=1.5.0                # Type checking
black>=23.7.0              # Code formatting
isort>=5.12.0              # Import sorting
flake8>=6.1.0              # Linting
flake8-docstrings>=1.7.0   # Docstring linting
pylint>=2.17.0             # Advanced linting
bandit>=1.7.5              # Security linting
safety>=2.3.5              # Dependency security checks
```

#### Profiling & Monitoring
```
memory-profiler>=0.61.0    # Memory profiling
line-profiler>=4.1.0       # Line-by-line profiling
```

#### Documentation
```
sphinx>=7.1.0              # Documentation generation
sphinx-rtd-theme>=1.3.0    # Read the Docs theme
```

#### Utilities
```
python-dateutil>=2.8.2     # Date utilities
python-dotenv>=1.0.0       # Environment variables
tqdm>=4.66.0               # Progress bars
rich>=13.5.0               # Rich terminal output
```

### Development Tools

```bash
# Code formatting
black parser/ --line-length 100
isort parser/

# Type checking
mypy parser/

# Linting
flake8 parser/
pylint parser/

# Security checks
bandit -r parser/
safety check

# Testing
pytest tests/ --cov=parser --cov-report=html

# Documentation
cd docs && sphinx-build -b html source/ build/
```

---

## Data Flow Pipeline

```
┌─────────────┐
│   SEARCHER  │  User searches for company filings
└──────┬──────┘
       │ Results stored with URLs
       ▼
┌─────────────┐
│  DATABASE   │  filing_searches table (status: pending)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ DOWNLOADER  │  Downloads filings to /mnt/map_pro/downloader/entities/
└──────┬──────┘
       │ Updates database (downloaded_filings)
       ▼
┌─────────────┐
│   PARSER    │  Reads downloaded filings
└──────┬──────┘  Generates parsed.json with taxonomy references
       │ Saves to /mnt/map_pro/parser/parsed_reports/
       ▼
┌─────────────┐
│   LIBRARY   │  Monitors parsed outputs
└──────┬──────┘  Detects taxonomy namespaces from parsed.json
       │ Registers missing taxonomies in database
       ▼
┌─────────────┐
│ DOWNLOADER  │  Downloads taxonomies to /mnt/map_pro/taxonomies/libraries/
└──────┬──────┘  Updates database (taxonomy_libraries)
       │
       ▼
┌─────────────┐
│   MAPPER    │  Reads parsed.json
└─────────────┘  Extracts financial statements
                 Saves to /mnt/map_pro/mapper/mapped_statements/
```

---

## Important Reminders for AI Assistants

### Before Starting ANY Work:

1. ✓ Read `/home/user/map_pro/standards.py` completely
2. ✓ Review this CLAUDE.md file
3. ✓ Check current git branch: `claude/claude-md-mkrwjitjf5zlmlpw-pd3ZR`
4. ✓ Verify you understand the module you're working on
5. ✓ Ask user for current folder tree if writing new files

### During Development:

1. ✓ Add `# Path:` header to ALL new Python files (first line!)
2. ✓ Use type hints on all functions and classes
3. ✓ Write docstrings (Google or NumPy style)
4. ✓ NO hardcoded values - use config loader
5. ✓ Check path regime before adding new paths (read .env, config_loader.py, data_paths.py)
6. ✓ Market-specific code ONLY in `/market/` directories
7. ✓ ALL outputs to data partition (`/mnt/map_pro/`), NEVER to program files
8. ✓ Use ASCII only - no emojis anywhere
9. ✓ Run `python standards_checker.py` frequently

### Before Committing:

1. ✓ Run standards checker
2. ✓ Run tests with pytest
3. ✓ Run type checker with mypy
4. ✓ Format code with black and isort
5. ✓ Review all changes for compliance
6. ✓ Write concise commit message (focus on "why" not "what")

### When in Doubt:

- **Read the standards.py file** - it has validation functions and detailed rules
- **Check existing code** - follow patterns already established
- **Ask the user** - especially for data partition locations
- **Verify filesystem** - don't trust database blindly

---

## Quick Reference Commands

```bash
# Standards compliance check
python standards_checker.py

# Run all tests
pytest tests/ --cov

# Type checking
mypy module_name/

# Code formatting
black module_name/ --line-length 100 && isort module_name/

# Linting
flake8 module_name/
pylint module_name/

# Security checks
bandit -r module_name/
safety check

# View project structure
tree -L 3 -I '__pycache__|*.pyc|.git'

# Check git status
git status

# View recent commits
git log --oneline -10

# View configuration
cat env

# Check database connection
psql -h localhost -U a -d xbrl_coordination
```

---

## Support Files

- **`standards.py`** - Complete coding standards, project principles, validation functions (1226 lines)
- **`standards_checker.py`** - Automated standards compliance checker
- **`env`** - Master configuration file for all modules
- **`README.md`** - Basic project information

---

## Additional Resources

### Project Principles Reference

From `standards.py`:

```python
PROJECT_PRINCIPLES = {
    'no_hardcode',           # NO hardcoded URLs, paths, constants
    'market_agnostic',       # Market-specific code only in /market/
    'taxonomy_agnostic',     # Support any taxonomy
    'output_location',       # NEVER write to program files
    'folder_tree',           # Always verify folder structure
    'path_regime_check',     # Check .env before adding paths
    'test_location',         # Tests under tests/ directory
    'file_header_path',      # # Path: comment on every file
    'phase_instructions',    # Follow implementation phases
    'ascii_only',            # No emojis anywhere
}
```

### Design Principles

```python
DESIGN_PRINCIPLES = {
    'modular',              # Independent, importable packages
    'reusable',             # Components usable in other projects
    'testable',             # Clear boundaries for unit testing (95%+ coverage)
    'typed',                # Type hints on all public APIs
    'documented',           # Comprehensive docstrings
    'standards_compliant',  # PEP 8, proper packaging
}
```

---

**End of CLAUDE.md**

This guide should be your primary reference when working on the MAP PRO codebase. Always prioritize code quality, standards compliance, and the project's core architectural principles.

For questions or clarifications, refer to:
- `standards.py` for detailed rules and validation logic
- Module-specific `README.md` files (if they exist)
- The user who owns this project

Remember: **"Database reflects reality, filesystem is truth"** - always verify!
