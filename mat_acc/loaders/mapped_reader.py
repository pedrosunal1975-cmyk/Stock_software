# Path: mat_acc/loaders/mapped_reader.py
"""
Mapped Statement Reader for mat_acc

Reads and interprets mapped statement files.
Works with paths provided by MappedDataLoader.

RESPONSIBILITY: Load and parse mapped statement JSON files
into structured data for financial analysis.

Adapted from map_pro/verification/loaders/mapped_reader.py
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any

from .mapped_data import MappedFilingEntry
from .constants import MAPPED_STATEMENT_MARKERS, MAPPED_STATEMENT_FOLDERS

# Size threshold for identifying main statements (50KB)
MAIN_STATEMENT_SIZE_THRESHOLD = 50 * 1024


@dataclass
class StatementFact:
    """
    A single fact from a mapped statement.

    Attributes:
        concept: Concept name (e.g., 'us-gaap:Assets')
        value: Fact value (numeric or string)
        unit: Unit of measurement (e.g., 'USD')
        decimals: Decimal precision
        period_start: Period start date (for duration facts)
        period_end: Period end date
        context_id: Context identifier
        dimensions: Dimensional qualifiers
        label: Human-readable label
        order: Display order in statement
        depth: Nesting depth in hierarchy
        is_total: Whether this is a total line
        is_abstract: Whether this is an abstract concept
    """
    concept: str
    value: Any
    unit: Optional[str] = None
    decimals: Optional[int] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    context_id: Optional[str] = None
    dimensions: dict = field(default_factory=dict)
    label: Optional[str] = None
    order: Optional[float] = None
    depth: int = 0
    is_total: bool = False
    is_abstract: bool = False


@dataclass
class Statement:
    """
    A financial statement with its facts.

    Attributes:
        name: Statement name (e.g., 'ConsolidatedBalanceSheet')
        role: Statement role URI
        facts: List of facts in this statement
        metadata: Additional statement metadata
        source_file: Path to the source file
        file_size_bytes: Size of source file in bytes
        is_main_statement: Whether this is a main statement
    """
    name: str
    role: Optional[str] = None
    facts: list[StatementFact] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    source_file: Optional[str] = None
    file_size_bytes: int = 0
    is_main_statement: bool = False


@dataclass
class MappedStatements:
    """
    Complete set of mapped statements for a filing.

    Attributes:
        statements: List of statements
        filing_info: Filing metadata
        namespaces: Namespace declarations
        periods: Available reporting periods
        market: Market identifier
        main_statements: List of main statement names
        total_statement_files: Total number of statement files found
    """
    statements: list[Statement] = field(default_factory=list)
    filing_info: dict = field(default_factory=dict)
    namespaces: dict = field(default_factory=dict)
    periods: list[dict] = field(default_factory=list)
    market: str = ''
    main_statements: list[str] = field(default_factory=list)
    total_statement_files: int = 0


class MappedReader:
    """
    Reads and interprets mapped statement JSON files.

    Uses paths from MappedDataLoader to load actual content.
    Converts JSON structure into typed dataclasses for analysis.

    Example:
        loader = MappedDataLoader(config)
        reader = MappedReader()

        filings = loader.discover_all_mapped_filings()
        for filing in filings:
            statements = reader.read_statements(filing)
            for stmt in statements.statements:
                print(f"{stmt.name}: {len(stmt.facts)} facts")
    """

    def __init__(self):
        """Initialize mapped reader."""
        self.logger = logging.getLogger('input.mapped_reader')

    def read_statements(self, filing: MappedFilingEntry) -> Optional[MappedStatements]:
        """
        Read all statements from a mapped filing.

        Strategy:
        1. Look for ALL statement files (core_statements + details + other)
        2. Fall back to combined file if no individual files exist

        Args:
            filing: MappedFilingEntry from MappedDataLoader

        Returns:
            MappedStatements object or None if reading fails
        """
        self.logger.info(f"Reading statements for {filing.company}/{filing.form}/{filing.date}")

        result = MappedStatements(market=filing.market)
        json_files = filing.available_files.get('json', [])
        result.total_statement_files = len(json_files)

        if not json_files:
            self.logger.warning(f"No JSON files found for {filing.filing_folder}")
            return None

        # Strategy 1: Load ALL statement files
        all_statement_files = self._find_all_statement_files(filing)

        if all_statement_files:
            self.logger.info(f"Found {len(all_statement_files)} total statement files")
            self._read_individual_files(all_statement_files, result)

            if result.statements:
                self._identify_main_statements(result)
                return result

        # Strategy 2: Fall back to combined file
        self.logger.info("No statement folders found, trying combined file")
        main_file = self._find_main_statements_file(filing)

        if main_file and main_file.exists():
            self._read_combined_file(main_file, result)
            if result.statements:
                self._identify_main_statements(result)
                return result

        # Strategy 3: Try all JSON files
        self._read_individual_files(json_files, result)
        self._identify_main_statements(result)

        return result

    def _find_all_statement_files(self, filing: MappedFilingEntry) -> list[Path]:
        """Find ALL statement files across all folders."""
        all_files = []
        found_paths = set()

        # Check json folder structure
        if filing.json_folder and filing.json_folder.exists():
            for folder_name in MAPPED_STATEMENT_FOLDERS:
                folder_path = filing.json_folder / folder_name
                if folder_path.exists() and folder_path.is_dir():
                    files = list(folder_path.glob('*.json'))
                    for f in files:
                        if f not in found_paths:
                            found_paths.add(f)
                            all_files.append(f)

        # Check direct folder structure
        if filing.filing_folder:
            for folder_name in MAPPED_STATEMENT_FOLDERS:
                folder_path = filing.filing_folder / folder_name
                if folder_path.exists() and folder_path.is_dir():
                    files = list(folder_path.glob('*.json'))
                    for f in files:
                        if f not in found_paths:
                            found_paths.add(f)
                            all_files.append(f)

            # Check json/JSON subfolder
            for subdir in ['json', 'JSON']:
                json_root = filing.filing_folder / subdir
                if json_root.exists():
                    for folder_name in MAPPED_STATEMENT_FOLDERS:
                        folder_path = json_root / folder_name
                        if folder_path.exists() and folder_path.is_dir():
                            files = list(folder_path.glob('*.json'))
                            for f in files:
                                if f not in found_paths:
                                    found_paths.add(f)
                                    all_files.append(f)

        return all_files

    def _read_combined_file(self, file_path: Path, result: MappedStatements) -> None:
        """Read statements from a combined file."""
        try:
            file_size = file_path.stat().st_size

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            result.filing_info = data.get('filing_info', data.get('metadata', {}))
            result.namespaces = data.get('namespaces', {})
            result.periods = data.get('periods', [])

            statements_data = data.get('statements', [])
            if isinstance(statements_data, dict):
                for name, stmt_data in statements_data.items():
                    stmt = self._parse_single_statement(
                        stmt_data, name,
                        source_file=str(file_path),
                        file_size=file_size // max(len(statements_data), 1)
                    )
                    if stmt:
                        result.statements.append(stmt)
            elif isinstance(statements_data, list):
                for stmt_data in statements_data:
                    name = stmt_data.get('name', stmt_data.get('statement_name', file_path.stem))
                    stmt = self._parse_single_statement(
                        stmt_data, name,
                        source_file=str(file_path),
                        file_size=file_size // max(len(statements_data), 1)
                    )
                    if stmt:
                        result.statements.append(stmt)

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error in {file_path}: {e}")
        except Exception as e:
            self.logger.error(f"Error reading {file_path}: {e}")

    def _read_individual_files(self, json_files: list[Path], result: MappedStatements) -> None:
        """Read statements from individual files."""
        sorted_files = sorted(json_files, key=lambda f: f.stat().st_size, reverse=True)

        for file_path in sorted_files:
            try:
                file_size = file_path.stat().st_size

                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                name = self._extract_statement_name(file_path)

                if not result.namespaces and 'namespaces' in data:
                    result.namespaces = data['namespaces']

                if not result.filing_info:
                    if 'filing_info' in data:
                        result.filing_info = data['filing_info']
                    elif 'metadata' in data:
                        result.filing_info = data['metadata']

                stmt = self._parse_single_statement(
                    data, name,
                    source_file=str(file_path),
                    file_size=file_size
                )
                if stmt:
                    result.statements.append(stmt)

            except json.JSONDecodeError as e:
                self.logger.warning(f"JSON decode error in {file_path}: {e}")
            except Exception as e:
                self.logger.warning(f"Error reading {file_path}: {e}")

    def _extract_statement_name(self, file_path: Path) -> str:
        """Extract a clean statement name from file path."""
        name = file_path.stem
        name = name.replace('_', ' ').replace('-', ' ')

        if name.islower() or name.isupper():
            name = name.title().replace(' ', '')

        for marker in ['Json', 'Data', 'Export']:
            name = name.replace(marker, '')

        return name.strip() or file_path.stem

    def _identify_main_statements(self, result: MappedStatements) -> None:
        """Identify main statements based on file size and content."""
        main_statement_indicators = [
            'balance', 'income', 'operations', 'cashflow',
            'cash_flow', 'cash flow', 'equity', 'stockholders',
            'comprehensive', 'financial position',
        ]

        for stmt in result.statements:
            name_lower = stmt.name.lower()

            is_main_by_name = any(
                indicator in name_lower
                for indicator in main_statement_indicators
            )
            is_main_by_size = stmt.file_size_bytes >= MAIN_STATEMENT_SIZE_THRESHOLD
            is_main_by_facts = len(stmt.facts) >= 20

            stmt.is_main_statement = (
                is_main_by_size or
                (is_main_by_name and is_main_by_facts)
            )

            if stmt.is_main_statement:
                result.main_statements.append(stmt.name)

    def _find_main_statements_file(self, filing: MappedFilingEntry) -> Optional[Path]:
        """Find the main statements JSON file."""
        if filing.json_folder and filing.json_folder.exists():
            for file_path in filing.json_folder.iterdir():
                if file_path.name in MAPPED_STATEMENT_MARKERS:
                    return file_path

        for file_path in filing.filing_folder.iterdir():
            if file_path.is_file() and file_path.name in MAPPED_STATEMENT_MARKERS:
                return file_path

        json_files = filing.available_files.get('json', [])
        return json_files[0] if json_files else None

    def _parse_single_statement(
        self,
        data: dict,
        name: str,
        source_file: Optional[str] = None,
        file_size: int = 0
    ) -> Optional[Statement]:
        """Parse a single statement from JSON data."""
        try:
            stmt = Statement(
                name=name,
                role=data.get('role', data.get('roleUri')),
                metadata={
                    k: v for k, v in data.items()
                    if k not in ['facts', 'items', 'role', 'roleUri', 'name']
                },
                source_file=source_file,
                file_size_bytes=file_size,
            )

            facts_data = data.get('facts', data.get('items', []))
            for fact_data in facts_data:
                fact = self._parse_fact(fact_data)
                if fact:
                    stmt.facts.append(fact)

            return stmt

        except Exception as e:
            self.logger.error(f"Error parsing statement {name}: {e}")
            return None

    def _parse_fact(self, data: dict) -> Optional[StatementFact]:
        """Parse a single fact from JSON data."""
        try:
            concept = (
                data.get('concept') or
                data.get('name') or
                data.get('qname') or
                ''
            )
            value = data.get('value', data.get('fact_value'))

            return StatementFact(
                concept=concept,
                value=value,
                unit=data.get('unit', data.get('unit_ref')),
                decimals=data.get('decimals'),
                period_start=data.get('period_start', data.get('startDate')),
                period_end=data.get('period_end', data.get('endDate', data.get('instant'))),
                context_id=data.get('context_id', data.get('context_ref', data.get('contextRef'))),
                dimensions=data.get('dimensions', {}),
                label=data.get('label', data.get('preferredLabel')),
                order=data.get('order'),
                depth=data.get('depth', data.get('level', 0)),
                is_total=data.get('is_total', data.get('isTotal', False)),
                is_abstract=data.get('is_abstract', data.get('isAbstract', False)),
            )

        except Exception as e:
            self.logger.error(f"Error parsing fact: {e}")
            return None

    def get_all_facts(self, statements: MappedStatements) -> list[StatementFact]:
        """Get all facts from all statements."""
        all_facts = []
        for stmt in statements.statements:
            all_facts.extend(stmt.facts)
        return all_facts

    def get_facts_by_concept(
        self,
        statements: MappedStatements,
        concept_pattern: str
    ) -> list[StatementFact]:
        """Find facts matching a concept pattern."""
        matching = []
        pattern_lower = concept_pattern.lower()

        for stmt in statements.statements:
            for fact in stmt.facts:
                if pattern_lower in fact.concept.lower():
                    matching.append(fact)

        return matching

    def get_main_statements(self, statements: MappedStatements) -> list[Statement]:
        """Get only the main statements."""
        return [stmt for stmt in statements.statements if stmt.is_main_statement]


__all__ = ['MappedReader', 'MappedStatements', 'Statement', 'StatementFact']
