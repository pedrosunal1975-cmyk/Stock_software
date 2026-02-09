# Path: verification/loaders/xbrl_filings.py
"""
XBRL Filings Loader for Verification Module

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
"""

import logging
from pathlib import Path
from typing import Optional

from ..core.config_loader import ConfigLoader
from .constants import (
    FORM_NAME_VARIATIONS,
    normalize_form_name,
    get_form_variations,
)


class XBRLFilingsLoader:
    """
    Provides BLIND recursive access to XBRL filing files.

    NO assumptions about directory structure.
    NO assumptions about naming conventions.
    Just discovers and lists files recursively.

    DOORKEEPER: All XBRL filing file access must go through this class.
    """

    MAX_DEPTH = 25
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize XBRL filings loader.

        Args:
            config: Optional ConfigLoader instance (creates new if not provided)
        """
        self.config = config if config else ConfigLoader()
        self.xbrl_path = self.config.get('xbrl_filings_path')

        if not self.xbrl_path:
            raise ValueError(
                "xbrl_filings_path not configured. "
                "Check .env for 'VERIFICATION_XBRL_FILINGS_PATH'"
            )

        self.logger = logging.getLogger('input.xbrl_filings')
        self.logger.info(f"XBRLFilingsLoader initialized: {self.xbrl_path}")

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

        # Start from market directory if it exists
        search_base = self.xbrl_path / market
        if not search_base.exists():
            # Try without market prefix
            search_base = self.xbrl_path
            self.logger.debug(f"Market directory not found, searching from root")

        # Get all form name variations to search for
        form_variations = get_form_variations(form)
        self.logger.debug(f"Form variations to search: {form_variations}")

        # Search for company directory first
        company_dir = self._find_company_directory(search_base, company)
        if not company_dir:
            self.logger.warning(f"Company directory not found for: {company}")
            return None

        self.logger.debug(f"Found company directory: {company_dir}")

        # Search for filing within company directory
        filing_dir = self._find_filing_in_company(
            company_dir, form_variations, date
        )

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
        """
        Find company directory by searching recursively.

        Handles various naming conventions (underscores, spaces, etc.)

        Args:
            search_base: Directory to search from
            company: Company name to find

        Returns:
            Path to company directory or None
        """
        # Normalize company name for comparison
        company_lower = company.lower().replace('_', '').replace('-', '').replace(' ', '')

        # First, check direct child directories
        if search_base.exists():
            for item in search_base.iterdir():
                if item.is_dir():
                    item_normalized = item.name.lower().replace('_', '').replace('-', '').replace(' ', '')
                    if item_normalized == company_lower or company.lower() in item.name.lower():
                        return item

        # Recursive search with depth limit
        for item in self._recursive_discover_dirs(search_base, 0, 5):
            item_normalized = item.name.lower().replace('_', '').replace('-', '').replace(' ', '')
            if item_normalized == company_lower or company.lower() in item.name.lower():
                return item

        return None

    def _find_filing_in_company(
        self,
        company_dir: Path,
        form_variations: list[str],
        date: str = None
    ) -> Optional[Path]:
        """
        Find filing directory within company directory.

        Searches recursively for directories matching form type.

        Args:
            company_dir: Company directory to search in
            form_variations: List of form name variations to match
            date: Optional specific date or accession number

        Returns:
            Path to filing directory or None
        """
        # Find all directories that might be form directories
        form_dirs = []

        for dir_path in self._recursive_discover_dirs(company_dir, 0, 10):
            dir_name_lower = dir_path.name.lower()

            # Check if directory name matches any form variation
            for form_var in form_variations:
                if form_var.lower() in dir_name_lower or dir_name_lower in form_var.lower():
                    form_dirs.append(dir_path)
                    break

        if not form_dirs:
            # No form directory found, search for filing directly
            # This handles flat structures where filings are directly under company
            return self._find_latest_filing_dir(company_dir, date)

        # Search within form directories for the actual filing
        candidates = []
        for form_dir in form_dirs:
            # Look for subdirectories (the actual filings)
            for sub in form_dir.iterdir():
                if sub.is_dir():
                    # Check if this looks like a filing directory
                    # (contains XBRL files like .xsd, _cal.xml, etc.)
                    if self._is_filing_directory(sub):
                        candidates.append(sub)

            # Also check if form_dir itself is the filing
            if self._is_filing_directory(form_dir):
                candidates.append(form_dir)

        if not candidates:
            return None

        # Filter by date if provided
        if date:
            for candidate in candidates:
                # Check if date appears in path or directory name
                if date in str(candidate) or date in candidate.name:
                    return candidate

        # Return most recent (sorted by name, descending)
        candidates.sort(key=lambda p: p.name, reverse=True)
        return candidates[0]

    def _find_latest_filing_dir(
        self,
        parent_dir: Path,
        date: str = None
    ) -> Optional[Path]:
        """
        Find the latest filing directory in a parent directory.

        Args:
            parent_dir: Parent directory to search
            date: Optional specific date filter

        Returns:
            Path to filing directory or None
        """
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

        # Return most recent
        candidates.sort(key=lambda p: p.name, reverse=True)
        return candidates[0]

    def _is_filing_directory(self, directory: Path) -> bool:
        """
        Check if a directory appears to be an XBRL filing directory.

        A filing directory typically contains:
        - .xsd schema file
        - _cal.xml calculation linkbase
        - _pre.xml presentation linkbase
        - .htm or .xml instance document

        Args:
            directory: Directory to check

        Returns:
            True if directory looks like a filing directory
        """
        if not directory.is_dir():
            return False

        # Look for characteristic XBRL files
        has_xsd = False
        has_linkbase = False
        has_instance = False

        try:
            for file_path in directory.iterdir():
                if not file_path.is_file():
                    continue

                name_lower = file_path.name.lower()

                if name_lower.endswith('.xsd'):
                    has_xsd = True
                elif '_cal.xml' in name_lower or '_pre.xml' in name_lower or '_def.xml' in name_lower:
                    has_linkbase = True
                elif name_lower.endswith('.htm') or name_lower.endswith('.xml'):
                    # Could be instance document
                    has_instance = True

                # If we found enough indicators, it's a filing directory
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
        """
        Recursively discover files with depth limit.

        Args:
            directory: Directory to search
            current_depth: Current recursion depth
            max_depth: Maximum recursion depth

        Returns:
            List of file paths
        """
        if current_depth > max_depth:
            self.logger.debug(f"Max depth {max_depth} reached at: {directory}")
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
        """
        Recursively discover directories with depth limit.

        Args:
            directory: Directory to search
            current_depth: Current recursion depth
            max_depth: Maximum recursion depth

        Returns:
            List of directory paths
        """
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


__all__ = ['XBRLFilingsLoader']
