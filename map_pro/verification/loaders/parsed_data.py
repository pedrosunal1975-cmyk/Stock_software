# Path: verification/loaders/parsed_data.py
"""
Parsed Data Loader for Verification Module

BLIND doorkeeper for parser output directory.
Discovers and provides paths to files in parser output directory.
Does NOT load or parse files - other components decide how to use them.

DESIGN PRINCIPLES:
- NO hardcoded directory structure assumptions
- Recursive file discovery (up to 25 levels deep)
- Detects parsed filings by marker file (parsed.json)
- Market-agnostic, naming-convention-agnostic
- Searches EVERYTHING, lets caller decide what to use

ARCHITECTURE:
- Discovers all filing folders by parsed.json marker
- Provides paths to any file within folders
- Extracts metadata from folder names (flexible depth)
- Other components load files themselves
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..core.config_loader import ConfigLoader
from .constants import (
    PARSED_JSON_FILE,
    normalize_form_name,
    get_form_variations,
    normalize_name,
    dates_match_flexible,
    DEFAULT_DATE_MATCH_LEVEL,
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
        loader = ParsedDataLoader()

        # Discover all filing folders
        filings = loader.discover_all_parsed_filings()

        # Get path to specific file
        json_path = loader.get_file_path(filing, 'json')
    """

    MAX_DEPTH = 25

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize parsed data loader.

        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self.parser_output_dir = self.config.get('parser_output_dir')
        self.logger = logging.getLogger('input.parsed_data')

        if not self.parser_output_dir:
            raise ValueError(
                "Parser output directory not configured. "
                "Check VERIFICATION_PARSER_OUTPUT_DIR in .env"
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

        # Find all parsed.json files
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
        """
        Build filing entry from folder structure.

        FLEXIBLE EXTRACTION: Extracts metadata from path parts without
        assuming exact depth. Works with any nesting level.
        """
        try:
            # Get path relative to parser output directory
            try:
                rel_path = filing_folder.relative_to(self.parser_output_dir)
                parts = rel_path.parts
            except ValueError:
                # Folder is not under parser_output_dir
                parts = filing_folder.parts

            # Extract metadata based on available path parts
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
        """
        Extract metadata from path parts flexibly.

        Works with various directory structures:
        - market/company/form/date
        - company/form/date
        - market/company/filings/form/accession_number
        - etc.

        Returns:
            Dictionary with market, company, form, date keys
        """
        # Default values
        metadata = {
            'market': 'unknown',
            'company': 'unknown',
            'form': 'unknown',
            'date': 'unknown',
        }

        if not parts:
            return metadata

        parts_list = list(parts)

        # Common patterns to identify path components
        market_indicators = ['sec', 'esef', 'edgar', 'uk', 'eu', 'jp', 'cn']

        # Skip common intermediate folder names
        skip_folders = ['filings', 'output', 'data', 'reports', 'parsed']

        # Filter out skip folders
        filtered_parts = [
            p for p in parts_list
            if p.lower() not in skip_folders
        ]

        if len(filtered_parts) >= 4:
            # Assume: market/company/form/date
            metadata['date'] = filtered_parts[-1]
            metadata['form'] = filtered_parts[-2]
            metadata['company'] = filtered_parts[-3]
            metadata['market'] = filtered_parts[-4]
        elif len(filtered_parts) == 3:
            # Assume: company/form/date or market/company/form
            last_part = filtered_parts[-1].lower()

            # Check if last part looks like a date (contains digits)
            if any(c.isdigit() for c in last_part):
                metadata['date'] = filtered_parts[-1]
                metadata['form'] = filtered_parts[-2]
                metadata['company'] = filtered_parts[-3]
            else:
                metadata['form'] = filtered_parts[-1]
                metadata['company'] = filtered_parts[-2]
                metadata['market'] = filtered_parts[-3]
        elif len(filtered_parts) == 2:
            # Assume: company/form or form/date
            metadata['form'] = filtered_parts[-1]
            metadata['company'] = filtered_parts[-2]
        elif len(filtered_parts) == 1:
            # Just use the folder name
            metadata['company'] = filtered_parts[0]

        # Try to identify market from any part if still unknown
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

        BLIND SEARCH: Does not assume directory structure.
        Searches for company and form with configurable date matching.

        Date matching levels (from constants.DEFAULT_DATE_MATCH_LEVEL):
        - 'any': Ignore dates entirely (default - most permissive)
        - 'year': Only years need to match
        - 'contains': One date contains the other (substring)
        - 'exact': Normalized dates must match exactly

        Args:
            market: Market identifier
            company: Company name
            form: Form type
            date: Filing date (optional - used based on date_match_level)
            date_match_level: How strict date matching should be
                              (default: DEFAULT_DATE_MATCH_LEVEL from constants)

        Returns:
            ParsedFilingEntry or None if not found
        """
        # Use default date match level if not specified
        if date_match_level is None:
            date_match_level = DEFAULT_DATE_MATCH_LEVEL

        self.logger.info(
            f"Searching for parsed filing: market={market}, company={company}, "
            f"form={form}, date={date or 'any'}, match_level={date_match_level}"
        )

        # Get all filings
        all_filings = self.discover_all_parsed_filings()

        # Normalize search terms
        company_normalized = normalize_name(company)
        form_variations = [f.lower() for f in get_form_variations(form)]

        # Search for matching filing
        candidates = []
        for filing in all_filings:
            # Check company match (fuzzy - substring in either direction)
            filing_company_normalized = normalize_name(filing.company)
            if company_normalized not in filing_company_normalized and \
               filing_company_normalized not in company_normalized:
                continue

            # Check form match (using form variations)
            filing_form_normalized = normalize_form_name(filing.form)
            if filing_form_normalized not in form_variations and \
               filing.form.lower() not in form_variations:
                continue

            # Check date using flexible matching
            if not dates_match_flexible(date, filing.date, date_match_level):
                continue

            candidates.append(filing)

        if not candidates:
            self.logger.warning(f"No parsed filing found for {company}/{form}/{date or 'any'}")
            return None

        # Return most recent if multiple found
        candidates.sort(key=lambda f: f.date, reverse=True)
        return candidates[0]


__all__ = ['ParsedDataLoader', 'ParsedFilingEntry']
