# Path: mat_acc/loaders/parsed_data.py
"""
Parsed Data Loader for mat_acc

BLIND doorkeeper for parser output directory.
Discovers and provides paths to files in parser output directory.
Does NOT load or parse files - other components decide how to use them.

DESIGN PRINCIPLES:
- NO hardcoded directory structure assumptions
- Recursive file discovery (up to 25 levels deep)
- Detects parsed filings by marker file (parsed.json)
- Market-agnostic, naming-convention-agnostic
- Searches EVERYTHING, lets caller decide what to use

Adapted from map_pro/verification/loaders/parsed_data.py
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .constants import (
    PARSED_JSON_FILE,
    normalize_form_name,
    get_form_variations,
    names_match_flexible,
    dates_match_flexible,
    DEFAULT_DATE_MATCH_LEVEL,
    MAX_DIRECTORY_DEPTH,
)


@dataclass
class ParsedFilingEntry:
    """
    Entry for a parsed filing folder.

    Contains only paths and folder-derived metadata.
    Does NOT contain file contents.

    Attributes:
        market: Market name
        company: Company name (from folder name)
        form: Document type/form (from folder name)
        date: Filing date (from folder name)
        filing_folder: Path to filing folder
        available_files: Dict of file types to paths
    """
    market: str
    company: str
    form: str
    date: str
    filing_folder: Path
    available_files: dict[str, Path]


class ParsedDataLoader:
    """
    BLIND doorkeeper for parser output directory.

    Discovers filing folders and provides paths to all files.
    Does NOT load file contents - that's for other components.

    NO ASSUMPTIONS about directory structure - searches recursively.

    Example:
        loader = ParsedDataLoader(config)
        filings = loader.discover_all_parsed_filings()
        for filing in filings:
            json_path = loader.get_file_path(filing, 'json')
    """

    MAX_DEPTH = MAX_DIRECTORY_DEPTH

    def __init__(self, config):
        """
        Initialize parsed data loader.

        Args:
            config: ConfigLoader instance with parser_output_dir
        """
        self.config = config
        self.parser_output_dir = Path(self.config.get('parser_output_dir'))
        self.logger = logging.getLogger('input.parsed_data')

        if not self.parser_output_dir:
            raise ValueError(
                "Parser output directory not configured. "
                "Check MAT_ACC_PARSER_OUTPUT_DIR in .env"
            )

        self.logger.info(f"ParsedDataLoader initialized: {self.parser_output_dir}")

    def discover_all_parsed_filings(self) -> list[ParsedFilingEntry]:
        """
        Discover all filing folders in parser output directory.

        BLIND SEARCH: Does not assume any directory structure.
        Searches recursively for directories containing parsed.json.

        Returns:
            List of ParsedFilingEntry objects with paths to all files
        """
        if not self.parser_output_dir.exists():
            self.logger.warning(f"Parser output directory not found: {self.parser_output_dir}")
            return []

        self.logger.info(f"Discovering filing folders in: {self.parser_output_dir}")

        entries = []

        for json_file in self.parser_output_dir.rglob(PARSED_JSON_FILE):
            depth = len(json_file.relative_to(self.parser_output_dir).parts)
            if depth > self.MAX_DEPTH:
                continue

            filing_folder = json_file.parent
            entry = self._build_filing_entry(filing_folder)
            if entry:
                entries.append(entry)

        self.logger.info(f"Discovered {len(entries)} valid filing entries")
        entries.sort(key=lambda e: (e.company, e.form, e.date))

        return entries

    def _build_filing_entry(self, filing_folder: Path) -> Optional[ParsedFilingEntry]:
        """Build filing entry from folder structure."""
        try:
            try:
                rel_path = filing_folder.relative_to(self.parser_output_dir)
                parts = rel_path.parts
            except ValueError:
                parts = filing_folder.parts

            metadata = self._extract_metadata_from_path(parts, filing_folder)
            available_files = self._discover_files(filing_folder)

            if not available_files:
                self.logger.debug(f"No files found in {filing_folder}")
                return None

            return ParsedFilingEntry(
                market=metadata['market'],
                company=metadata['company'],
                form=metadata['form'],
                date=metadata['date'],
                filing_folder=filing_folder,
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
        skip_folders = ['filings', 'output', 'data', 'reports', 'parsed']

        filtered_parts = [
            p for p in parts_list
            if p.lower() not in skip_folders
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

    def _discover_files(self, filing_folder: Path) -> dict[str, Path]:
        """Discover all files in filing folder."""
        files = {}

        for file_path in filing_folder.iterdir():
            if file_path.is_file():
                ext = file_path.suffix.lower()
                key = ext[1:] if ext.startswith('.') else ext
                files[key] = file_path

        return files

    def get_file_path(self, filing: ParsedFilingEntry, file_type: str) -> Optional[Path]:
        """Get path to specific file type."""
        return filing.available_files.get(file_type)

    def get_parsed_json_path(self, filing: ParsedFilingEntry) -> Optional[Path]:
        """Get path to parsed.json file."""
        return filing.available_files.get('json')

    def find_parsed_filing(
        self,
        market: str,
        company: str,
        form: str,
        date: str = None,
        date_match_level: str = None
    ) -> Optional[ParsedFilingEntry]:
        """
        Find specific parsed filing using flexible search.

        Args:
            market: Market identifier
            company: Company name
            form: Form type
            date: Filing date (optional)
            date_match_level: How strict date matching should be

        Returns:
            ParsedFilingEntry or None if not found
        """
        if date_match_level is None:
            date_match_level = DEFAULT_DATE_MATCH_LEVEL

        self.logger.info(
            f"Searching for parsed filing: market={market}, company={company}, "
            f"form={form}, date={date or 'any'}, match_level={date_match_level}"
        )

        all_filings = self.discover_all_parsed_filings()
        form_variations = [f.lower() for f in get_form_variations(form)]

        candidates = []
        for filing in all_filings:
            # Use flexible matching that handles & vs AND vs nothing
            if not names_match_flexible(company, filing.company):
                continue

            filing_form_normalized = normalize_form_name(filing.form)
            if filing_form_normalized not in form_variations and \
               filing.form.lower() not in form_variations:
                continue

            if not dates_match_flexible(date, filing.date, date_match_level):
                continue

            candidates.append(filing)

        if not candidates:
            self.logger.warning(f"No parsed filing found for {company}/{form}/{date or 'any'}")
            return None

        candidates.sort(key=lambda f: f.date, reverse=True)
        return candidates[0]

    def get_filing_statistics(self) -> dict:
        """Get statistics about available parsed filings."""
        filings = self.discover_all_parsed_filings()

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


__all__ = ['ParsedDataLoader', 'ParsedFilingEntry']
