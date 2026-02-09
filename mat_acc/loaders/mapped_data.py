# Path: mat_acc/loaders/mapped_data.py
"""
Mapped Data Loader for mat_acc

BLIND doorkeeper for mapped statements directory.
Discovers and provides paths to mapped statement files.
Does NOT load or interpret contents - that's for mapped_reader.py.

DESIGN PRINCIPLES:
- NO hardcoded directory structure assumptions
- Recursive file discovery (up to 25 levels deep)
- Detects mapped filings by marker files (MAIN_FINANCIAL_STATEMENTS.json, etc.)
- Market-agnostic, naming-convention-agnostic
- Searches EVERYTHING, lets caller decide what to use

Adapted from map_pro/verification/loaders/mapped_data.py
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .constants import (
    MAPPED_STATEMENT_MARKERS,
    MAPPED_OUTPUT_SUBDIRS,
    MAPPED_STATEMENT_FOLDERS,
    normalize_form_name,
    get_form_variations,
    normalize_name,
    MAX_DIRECTORY_DEPTH,
)


@dataclass
class MappedFilingEntry:
    """
    Entry for a mapped filing folder.

    Contains only paths and folder-derived metadata.
    Does NOT contain file contents - that's for mapped_reader.

    Attributes:
        market: Market name (e.g., 'sec', 'esef') - extracted from path
        company: Company name (from folder name)
        form: Document type/form (from folder name)
        date: Filing date (from folder name)
        filing_folder: Path to mapped filing folder
        json_folder: Path to json/ subdirectory (if exists)
        csv_folder: Path to csv/ subdirectory (if exists)
        excel_folder: Path to excel/ subdirectory (if exists)
        available_files: Dict of file types to paths
    """
    market: str
    company: str
    form: str
    date: str
    filing_folder: Path
    json_folder: Optional[Path]
    csv_folder: Optional[Path]
    excel_folder: Optional[Path]
    available_files: dict[str, list[Path]]


class MappedDataLoader:
    """
    BLIND doorkeeper for mapped statements directory.

    Discovers mapped filing folders and provides paths to all statement files.
    Does NOT load file contents - that's for MappedReader.

    NO ASSUMPTIONS about directory structure - searches recursively.

    Example:
        loader = MappedDataLoader(config)
        filings = loader.discover_all_mapped_filings()
        for filing in filings:
            print(f"{filing.company} | {filing.form} | {filing.date}")
    """

    MAX_DEPTH = MAX_DIRECTORY_DEPTH

    def __init__(self, config):
        """
        Initialize mapped data loader.

        Args:
            config: ConfigLoader instance with mapper_output_dir
        """
        self.config = config
        self.mapper_output_dir = Path(self.config.get('mapper_output_dir'))
        self.logger = logging.getLogger('input.mapped_data')

        if not self.mapper_output_dir:
            raise ValueError(
                "Mapper output directory not configured. "
                "Check MAT_ACC_MAPPER_OUTPUT_DIR in .env"
            )

        self.logger.info(f"MappedDataLoader initialized: {self.mapper_output_dir}")

    def discover_all_mapped_filings(self) -> list[MappedFilingEntry]:
        """
        Discover all mapped filing folders in mapper output directory.

        BLIND SEARCH: Does not assume any directory structure.
        Searches recursively for directories containing statement marker files.

        Returns:
            List of MappedFilingEntry objects with paths to all files
        """
        if not self.mapper_output_dir.exists():
            self.logger.warning(f"Mapper output directory not found: {self.mapper_output_dir}")
            return []

        self.logger.info(f"Discovering mapped filings in: {self.mapper_output_dir}")

        entries = []
        processed_folders = set()

        # Strategy 1: Find directories with marker files
        for marker in MAPPED_STATEMENT_MARKERS:
            for marker_file in self.mapper_output_dir.rglob(marker):
                depth = len(marker_file.relative_to(self.mapper_output_dir).parts)
                if depth > self.MAX_DEPTH:
                    continue

                filing_folder = marker_file.parent
                if filing_folder.name == 'json':
                    filing_folder = filing_folder.parent

                if filing_folder in processed_folders:
                    continue
                processed_folders.add(filing_folder)

                entry = self._build_filing_entry(filing_folder)
                if entry:
                    entries.append(entry)

        # Strategy 2: Find directories with output subdirectories
        for subdir in MAPPED_OUTPUT_SUBDIRS:
            for output_dir in self.mapper_output_dir.rglob(subdir):
                if not output_dir.is_dir():
                    continue

                depth = len(output_dir.relative_to(self.mapper_output_dir).parts)
                if depth > self.MAX_DEPTH:
                    continue

                filing_folder = output_dir.parent
                if filing_folder in processed_folders:
                    continue
                processed_folders.add(filing_folder)

                entry = self._build_filing_entry(filing_folder)
                if entry:
                    entries.append(entry)

        self.logger.info(f"Discovered {len(entries)} mapped filing entries")
        entries.sort(key=lambda e: (e.company, e.form, e.date))

        return entries

    def _build_filing_entry(self, filing_folder: Path) -> Optional[MappedFilingEntry]:
        """Build filing entry from folder structure."""
        try:
            try:
                rel_path = filing_folder.relative_to(self.mapper_output_dir)
                parts = rel_path.parts
            except ValueError:
                parts = filing_folder.parts

            metadata = self._extract_metadata_from_path(parts, filing_folder)

            json_folder = filing_folder / 'json'
            csv_folder = filing_folder / 'csv'
            excel_folder = filing_folder / 'excel'

            available_files = self._discover_files(filing_folder)

            if not available_files:
                self.logger.debug(f"No statement files found in {filing_folder}")
                return None

            return MappedFilingEntry(
                market=metadata['market'],
                company=metadata['company'],
                form=metadata['form'],
                date=metadata['date'],
                filing_folder=filing_folder,
                json_folder=json_folder if json_folder.exists() else None,
                csv_folder=csv_folder if csv_folder.exists() else None,
                excel_folder=excel_folder if excel_folder.exists() else None,
                available_files=available_files
            )

        except Exception as e:
            self.logger.error(f"Error building entry for {filing_folder}: {e}")
            return None

    def _extract_metadata_from_path(
        self,
        parts: tuple,
        filing_folder: Path
    ) -> dict[str, str]:
        """Extract metadata from path parts flexibly."""
        metadata = {
            'market': 'unknown',
            'company': 'unknown',
            'form': 'unknown',
            'date': 'unknown',
        }

        if not parts:
            return metadata

        parts_list = list(parts)
        market_indicators = ['sec', 'esef', 'edgar', 'uk', 'eu', 'jp', 'cn']
        skip_folders = ['filings', 'output', 'data', 'reports', 'statements']

        filtered_parts = [
            p for p in parts_list
            if p.lower() not in skip_folders + MAPPED_OUTPUT_SUBDIRS
        ]

        if len(filtered_parts) >= 4:
            metadata['date'] = filtered_parts[-1]
            metadata['form'] = filtered_parts[-2]
            metadata['company'] = filtered_parts[-3]
            metadata['market'] = filtered_parts[-4]
        elif len(filtered_parts) == 3:
            last_part = filtered_parts[-1].lower()
            if any(c.isdigit() for c in last_part):
                metadata['date'] = filtered_parts[-1]
                metadata['form'] = filtered_parts[-2]
                metadata['company'] = filtered_parts[-3]
            else:
                metadata['form'] = filtered_parts[-1]
                metadata['company'] = filtered_parts[-2]
                metadata['market'] = filtered_parts[-3]
        elif len(filtered_parts) == 2:
            metadata['form'] = filtered_parts[-1]
            metadata['company'] = filtered_parts[-2]
        elif len(filtered_parts) == 1:
            metadata['company'] = filtered_parts[0]

        if metadata['market'] == 'unknown':
            for part in parts_list:
                if part.lower() in market_indicators:
                    metadata['market'] = part.lower()
                    break

        return metadata

    def _discover_files(self, filing_folder: Path) -> dict[str, list[Path]]:
        """Discover all statement files in filing folder."""
        files = {
            'json': [],
            'csv': [],
            'excel': [],
        }

        for format_name in MAPPED_OUTPUT_SUBDIRS:
            format_dir = filing_folder / format_name
            if format_dir.exists() and format_dir.is_dir():
                for file_path in format_dir.rglob('*'):
                    if file_path.is_file():
                        files[format_name].append(file_path)

        for file_path in filing_folder.iterdir():
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext == '.json':
                    files['json'].append(file_path)
                elif ext == '.csv':
                    files['csv'].append(file_path)
                elif ext in ['.xlsx', '.xlsm']:
                    files['excel'].append(file_path)

        return files

    def get_json_files(self, filing: MappedFilingEntry) -> list[Path]:
        """Get all JSON files for a filing."""
        return filing.available_files.get('json', [])

    def get_csv_files(self, filing: MappedFilingEntry) -> list[Path]:
        """Get all CSV files for a filing."""
        return filing.available_files.get('csv', [])

    def get_main_statements_file(self, filing: MappedFilingEntry) -> Optional[Path]:
        """Get the main statements JSON file."""
        json_files = filing.available_files.get('json', [])

        for marker in MAPPED_STATEMENT_MARKERS:
            for json_file in json_files:
                if json_file.name == marker:
                    return json_file

        return json_files[0] if json_files else None

    def find_mapped_filing(
        self,
        market: str,
        company: str,
        form: str,
        date: str = None
    ) -> Optional[MappedFilingEntry]:
        """
        Find specific mapped filing using flexible search.

        Args:
            market: Market identifier
            company: Company name
            form: Form type
            date: Filing date (optional)

        Returns:
            MappedFilingEntry or None if not found
        """
        self.logger.info(
            f"Searching for mapped filing: market={market}, company={company}, "
            f"form={form}, date={date}"
        )

        all_filings = self.discover_all_mapped_filings()
        company_normalized = normalize_name(company)
        form_variations = [f.lower() for f in get_form_variations(form)]

        candidates = []
        for filing in all_filings:
            filing_company_normalized = normalize_name(filing.company)
            if company_normalized not in filing_company_normalized and \
               filing_company_normalized not in company_normalized:
                continue

            filing_form_normalized = normalize_form_name(filing.form)
            if filing_form_normalized not in form_variations and \
               filing.form.lower() not in form_variations:
                continue

            if date and date not in filing.date and filing.date not in date:
                continue

            candidates.append(filing)

        if not candidates:
            self.logger.warning(f"No mapped filing found for {company}/{form}/{date or 'any'}")
            return None

        candidates.sort(key=lambda f: f.date, reverse=True)
        return candidates[0]

    def get_filing_statistics(self) -> dict:
        """Get statistics about available mapped filings."""
        filings = self.discover_all_mapped_filings()

        stats = {
            'total_filings': len(filings),
            'by_market': {},
            'by_form': {},
            'companies': set(),
        }

        for filing in filings:
            if filing.market not in stats['by_market']:
                stats['by_market'][filing.market] = 0
            stats['by_market'][filing.market] += 1

            if filing.form not in stats['by_form']:
                stats['by_form'][filing.form] = 0
            stats['by_form'][filing.form] += 1

            stats['companies'].add(f"{filing.market}/{filing.company}")

        stats['unique_companies'] = len(stats['companies'])
        stats['companies'] = list(stats['companies'])

        return stats


__all__ = ['MappedDataLoader', 'MappedFilingEntry']
