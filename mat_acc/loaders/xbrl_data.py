# Path: mat_acc/loaders/xbrl_data.py
"""
XBRL Filings Loader for mat_acc

BLIND recursive file accessor for XBRL filing files.

DESIGN PRINCIPLES:
- Uses ConfigLoader for path resolution (NO hardcoded paths)
- Recursive file discovery (up to 25 levels deep)
- NO hardcoded file types, patterns, or directory structures
- NO parsing or processing - just file access
- Market-agnostic, naming-convention-agnostic
- Searches EVERYTHING, lets caller decide what to use

RESPONSIBILITY: Provide access to XBRL files. That's it.
The loader is BLIND - it doesn't know or care about naming conventions.

Adapted from map_pro/verification/loaders/xbrl_filings.py
"""

import logging
from pathlib import Path
from typing import Optional

from .constants import (
    get_form_variations,
    names_match_flexible,
    MAX_DIRECTORY_DEPTH,
)


class XBRLDataLoader:
    """
    Provides BLIND recursive access to XBRL filing files.

    NO assumptions about directory structure.
    NO assumptions about naming conventions.
    Just discovers and lists files recursively.

    DOORKEEPER: All XBRL filing file access must go through this class.

    Example:
        loader = XBRLDataLoader(config)
        filing_dir = loader.find_filing_for_company('sec', 'Apple', '10-K')
        if filing_dir:
            files = loader.discover_all_files(filing_dir)
    """

    MAX_DEPTH = MAX_DIRECTORY_DEPTH
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB

    def __init__(self, config):
        """
        Initialize XBRL filings loader.

        Args:
            config: ConfigLoader instance with xbrl_filings_path
        """
        self.config = config
        self.logger = logging.getLogger('input.xbrl_data')

        # Try multiple config keys for compatibility
        xbrl_path = self.config.get('xbrl_filings_dir') or self.config.get('xbrl_filings_path')

        if not xbrl_path:
            raise ValueError(
                "XBRL filings path not configured. "
                "Check MAT_ACC_XBRL_FILINGS_DIR in .env"
            )
        self.xbrl_path = Path(xbrl_path)

        self.logger.info(f"XBRLDataLoader initialized: {self.xbrl_path}")

    def discover_all_files(
        self,
        subdirectory: str = None,
        max_depth: int = None
    ) -> list[Path]:
        """
        Recursively discover ALL files in XBRL filing directory.

        NO filtering - returns everything. Caller decides what to use.

        Args:
            subdirectory: Optional subdirectory to search in
            max_depth: Optional depth limit (default: 25)

        Returns:
            List of all file paths found
        """
        search_dir = self.xbrl_path / subdirectory if subdirectory else self.xbrl_path

        if not search_dir.exists():
            self.logger.warning(f"Directory not found: {search_dir}")
            return []

        depth = max_depth if max_depth is not None else self.MAX_DEPTH

        self.logger.info(f"File discovery started: {search_dir} (max depth: {depth})")

        files = self._recursive_discover(search_dir, current_depth=0, max_depth=depth)

        self.logger.info(f"File discovery completed: {len(files)} files found")

        return files

    def discover_all_directories(
        self,
        subdirectory: str = None,
        max_depth: int = None
    ) -> list[Path]:
        """
        Recursively discover ALL directories.

        Args:
            subdirectory: Optional subdirectory to search in
            max_depth: Optional depth limit (default: 25)

        Returns:
            List of all directory paths found
        """
        search_dir = self.xbrl_path / subdirectory if subdirectory else self.xbrl_path

        if not search_dir.exists():
            self.logger.warning(f"Directory not found: {search_dir}")
            return []

        depth = max_depth if max_depth is not None else self.MAX_DEPTH

        return self._recursive_discover_dirs(search_dir, current_depth=0, max_depth=depth)

    def get_filing_directory(self, relative_path: str) -> Path:
        """
        Get filing directory path.

        Args:
            relative_path: Path relative to XBRL filings root

        Returns:
            Absolute Path to filing directory

        Raises:
            FileNotFoundError: If directory doesn't exist
        """
        filing_dir = self.xbrl_path / relative_path

        if not filing_dir.exists():
            raise FileNotFoundError(f"Filing directory not found: {filing_dir}")

        if not filing_dir.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {filing_dir}")

        return filing_dir

    def find_filing_for_company(
        self,
        market: str,
        company: str,
        form: str,
        date: str = None
    ) -> Optional[Path]:
        """
        Find XBRL filing directory for a specific company filing.

        BLIND SEARCH: Does not assume any directory structure.
        Searches recursively for directories matching the criteria.

        Args:
            market: Market identifier (e.g., 'sec', 'esef')
            company: Company name/identifier
            form: Form type (e.g., '10-K', '10_K', 'AFR')
            date: Optional specific date or accession number

        Returns:
            Path to filing directory or None if not found
        """
        self.logger.info(
            f"Searching for filing: market={market}, company={company}, "
            f"form={form}, date={date}"
        )

        search_base = self.xbrl_path / market
        if not search_base.exists():
            search_base = self.xbrl_path
            self.logger.debug("Market directory not found, searching from root")

        form_variations = get_form_variations(form)
        self.logger.debug(f"Form variations to search: {form_variations}")

        company_dir = self._find_company_directory(search_base, company)
        if not company_dir:
            self.logger.warning(f"Company directory not found for: {company}")
            return None

        self.logger.debug(f"Found company directory: {company_dir}")

        filing_dir = self._find_filing_in_company(company_dir, form_variations, date)

        if filing_dir:
            self.logger.info(f"Found filing directory: {filing_dir}")
        else:
            self.logger.warning(
                f"Filing not found for {company}/{form}/{date or 'latest'}"
            )

        return filing_dir

    def _find_company_directory(
        self,
        search_base: Path,
        company: str
    ) -> Optional[Path]:
        """Find company directory by searching recursively."""
        if search_base.exists():
            for item in search_base.iterdir():
                if item.is_dir():
                    if names_match_flexible(company, item.name):
                        return item

        for item in self._recursive_discover_dirs(search_base, 0, 5):
            if names_match_flexible(company, item.name):
                return item

        return None

    def _find_filing_in_company(
        self,
        company_dir: Path,
        form_variations: list[str],
        date: str = None
    ) -> Optional[Path]:
        """Find filing directory within company directory."""
        form_dirs = []

        for dir_path in self._recursive_discover_dirs(company_dir, 0, 10):
            dir_name_lower = dir_path.name.lower()

            for form_var in form_variations:
                if form_var.lower() in dir_name_lower or dir_name_lower in form_var.lower():
                    form_dirs.append(dir_path)
                    break

        if not form_dirs:
            return self._find_latest_filing_dir(company_dir, date)

        candidates = []
        for form_dir in form_dirs:
            for sub in form_dir.iterdir():
                if sub.is_dir():
                    if self._is_filing_directory(sub):
                        candidates.append(sub)

            if self._is_filing_directory(form_dir):
                candidates.append(form_dir)

        if not candidates:
            return None

        if date:
            for candidate in candidates:
                if date in str(candidate) or date in candidate.name:
                    return candidate

        candidates.sort(key=lambda p: p.name, reverse=True)
        return candidates[0]

    def _find_latest_filing_dir(
        self,
        parent_dir: Path,
        date: str = None
    ) -> Optional[Path]:
        """Find the latest filing directory in a parent directory."""
        candidates = []

        for item in parent_dir.rglob('*'):
            if item.is_dir() and self._is_filing_directory(item):
                if date:
                    if date in str(item) or date in item.name:
                        candidates.append(item)
                else:
                    candidates.append(item)

        if not candidates:
            return None

        candidates.sort(key=lambda p: p.name, reverse=True)
        return candidates[0]

    def _is_filing_directory(self, directory: Path) -> bool:
        """Check if a directory appears to be an XBRL filing directory."""
        if not directory.is_dir():
            return False

        has_xsd = False
        has_linkbase = False

        try:
            for file_path in directory.iterdir():
                if not file_path.is_file():
                    continue

                name_lower = file_path.name.lower()

                if name_lower.endswith('.xsd'):
                    has_xsd = True
                elif '_cal.xml' in name_lower or '_pre.xml' in name_lower or '_def.xml' in name_lower:
                    has_linkbase = True

                if has_xsd or has_linkbase:
                    return True

        except PermissionError:
            pass

        return False

    def _recursive_discover(
        self,
        directory: Path,
        current_depth: int,
        max_depth: int
    ) -> list[Path]:
        """Recursively discover files with depth limit."""
        if current_depth > max_depth:
            return []

        discovered = []

        try:
            for item in directory.iterdir():
                if item.is_symlink():
                    continue

                if item.is_dir():
                    discovered.extend(
                        self._recursive_discover(item, current_depth + 1, max_depth)
                    )
                elif item.is_file():
                    try:
                        if item.stat().st_size > self.MAX_FILE_SIZE:
                            self.logger.warning(f"Skipping large file: {item}")
                            continue
                    except OSError:
                        continue

                    discovered.append(item)

        except PermissionError:
            self.logger.warning(f"Permission denied: {directory}")
        except Exception as e:
            self.logger.error(f"Error in {directory}: {e}")

        return discovered

    def _recursive_discover_dirs(
        self,
        directory: Path,
        current_depth: int,
        max_depth: int
    ) -> list[Path]:
        """Recursively discover directories with depth limit."""
        if current_depth > max_depth:
            return []

        discovered = []

        try:
            for item in directory.iterdir():
                if item.is_symlink():
                    continue

                if item.is_dir():
                    discovered.append(item)
                    discovered.extend(
                        self._recursive_discover_dirs(item, current_depth + 1, max_depth)
                    )

        except PermissionError:
            pass
        except Exception as e:
            self.logger.debug(f"Error scanning {directory}: {e}")

        return discovered

    def get_filing_statistics(self) -> dict:
        """Get statistics about available XBRL filings."""
        if not self.xbrl_path.exists():
            return {'total_filings': 0, 'by_market': {}, 'companies': []}

        stats = {
            'total_filings': 0,
            'by_market': {},
            'companies': set(),
        }

        # Count top-level market directories
        for market_dir in self.xbrl_path.iterdir():
            if not market_dir.is_dir():
                continue

            market_name = market_dir.name
            stats['by_market'][market_name] = 0

            for company_dir in market_dir.iterdir():
                if not company_dir.is_dir():
                    continue

                stats['companies'].add(f"{market_name}/{company_dir.name}")

                # Count filings in company
                for item in company_dir.rglob('*'):
                    if item.is_dir() and self._is_filing_directory(item):
                        stats['total_filings'] += 1
                        stats['by_market'][market_name] += 1

        stats['unique_companies'] = len(stats['companies'])
        stats['companies'] = list(stats['companies'])

        return stats


__all__ = ['XBRLDataLoader']
