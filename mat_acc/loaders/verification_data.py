# Path: mat_acc/loaders/verification_data.py
"""
Verification Data Loader for mat_acc

BLIND doorkeeper for verification reports directory.
Discovers and provides paths to verification report files.
Does NOT load or interpret contents - that's for verification_reader.py.

DESIGN PRINCIPLES:
- NO hardcoded directory structure assumptions
- Recursive file discovery (up to 25 levels deep)
- Detects verified filings by marker files (verification_report.json)
- Market-agnostic, naming-convention-agnostic
- Searches EVERYTHING, lets caller decide what to use

ARCHITECTURE:
- Discovers all verification report folders
- Provides paths to report files
- Extracts metadata from folder structure (flexible depth)
- Other components (verification_reader) load and interpret files
"""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from config_loader import ConfigLoader


# ==============================================================================
# CONSTANTS
# ==============================================================================
VERIFICATION_REPORT_MARKERS = [
    'verification_report.json',
]

MAX_SEARCH_DEPTH = 25


@dataclass
class VerifiedFilingEntry:
    """
    Entry for a verified filing.

    Contains only paths and folder-derived metadata.
    Does NOT contain file contents - that's for verification_reader.

    Attributes:
        market: Market name (e.g., 'sec', 'esef') - extracted from path
        company: Company name (from folder name)
        form: Document type/form (from folder name)
        date: Filing date (from folder name)
        report_folder: Path to verification report folder
        report_path: Path to verification_report.json file
    """
    market: str
    company: str
    form: str
    date: str
    report_folder: Path
    report_path: Path


class VerificationDataLoader:
    """
    BLIND doorkeeper for verification reports directory.

    Discovers verification report folders and provides paths to all report files.
    Does NOT load file contents - that's for VerificationReader.

    NO ASSUMPTIONS about directory structure - searches recursively.

    SINGLE ENTRY POINT: All verification report path discovery goes through this class.

    Example:
        loader = VerificationDataLoader()

        # Discover all verified filings
        filings = loader.discover_all_verified_filings()

        # Get paths for a specific filing
        for filing in filings:
            print(f"{filing.company} | {filing.form} | {filing.date}")
            print(f"  Report: {filing.report_path}")
    """

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize verification data loader.

        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self.verification_reports_dir = self.config.get('verification_reports_dir')
        self.logger = logging.getLogger('input.verification_data')

        if not self.verification_reports_dir:
            raise ValueError(
                "Verification reports directory not configured. "
                "Check MAT_ACC_VERIFICATION_REPORTS_DIR in .env"
            )

        self.logger.info(
            f"VerificationDataLoader initialized: {self.verification_reports_dir}"
        )

    def discover_all_verified_filings(self) -> list[VerifiedFilingEntry]:
        """
        Discover all verification report folders in reports directory.

        BLIND SEARCH: Does not assume any directory structure.
        Searches recursively for directories containing verification_report.json.

        Returns:
            List of VerifiedFilingEntry objects with paths to all files
        """
        if not self.verification_reports_dir.exists():
            self.logger.warning(
                f"Verification reports directory not found: "
                f"{self.verification_reports_dir}"
            )
            return []

        self.logger.info(
            f"Discovering verified filings in: {self.verification_reports_dir}"
        )

        entries = []
        processed_folders = set()

        # Find directories with verification_report.json
        for marker in VERIFICATION_REPORT_MARKERS:
            for marker_file in self.verification_reports_dir.rglob(marker):
                depth = len(
                    marker_file.relative_to(self.verification_reports_dir).parts
                )
                if depth > MAX_SEARCH_DEPTH:
                    continue

                report_folder = marker_file.parent

                if report_folder in processed_folders:
                    continue
                processed_folders.add(report_folder)

                entry = self._build_filing_entry(report_folder, marker_file)
                if entry:
                    entries.append(entry)

        self.logger.info(f"Discovered {len(entries)} verified filings")
        return entries

    def _build_filing_entry(
        self,
        report_folder: Path,
        report_path: Path
    ) -> Optional[VerifiedFilingEntry]:
        """
        Build VerifiedFilingEntry from folder path.

        Attempts to extract metadata from directory structure.
        Uses flexible depth detection to handle various structures.

        Expected pattern:
        /reports/{market}/{company}/{form}/{date}/verification_report.json

        Args:
            report_folder: Path to verification report folder
            report_path: Path to verification_report.json

        Returns:
            VerifiedFilingEntry or None if cannot extract metadata
        """
        try:
            # Calculate relative path from base
            rel_path = report_folder.relative_to(self.verification_reports_dir)
            parts = rel_path.parts

            # Need at least 4 parts: market/company/form/date
            if len(parts) < 4:
                # Try to extract what we can
                if len(parts) >= 1:
                    return VerifiedFilingEntry(
                        market='unknown',
                        company=parts[-1] if len(parts) >= 1 else 'unknown',
                        form='unknown',
                        date='unknown',
                        report_folder=report_folder,
                        report_path=report_path,
                    )
                return None

            # Standard 4-level structure: market/company/form/date
            market = parts[0]
            company = parts[1]
            form = parts[2]
            date = parts[3]

            return VerifiedFilingEntry(
                market=market,
                company=company,
                form=form,
                date=date,
                report_folder=report_folder,
                report_path=report_path,
            )

        except Exception as e:
            self.logger.warning(f"Failed to build entry from {report_folder}: {e}")
            return None

    def get_filing(
        self,
        market: str,
        company: str,
        form: str,
        date: str
    ) -> Optional[VerifiedFilingEntry]:
        """
        Get specific filing by identifiers.

        Args:
            market: Market identifier (e.g., 'sec')
            company: Company name
            form: Form type (e.g., '10_K')
            date: Filing date

        Returns:
            VerifiedFilingEntry if found, None otherwise
        """
        # Construct expected path
        expected_path = (
            self.verification_reports_dir / market / company / form / date
        )
        report_path = expected_path / 'verification_report.json'

        if report_path.exists():
            return VerifiedFilingEntry(
                market=market,
                company=company,
                form=form,
                date=date,
                report_folder=expected_path,
                report_path=report_path,
            )

        # If not found at expected path, search
        self.logger.info(
            f"Filing not at expected path, searching... "
            f"{market}/{company}/{form}/{date}"
        )

        all_filings = self.discover_all_verified_filings()
        for filing in all_filings:
            if (
                filing.market == market
                and filing.company == company
                and filing.form == form
                and filing.date == date
            ):
                return filing

        return None

    def get_filings_for_company(self, company: str) -> list[VerifiedFilingEntry]:
        """
        Get all filings for a specific company.

        Args:
            company: Company name

        Returns:
            List of VerifiedFilingEntry for the company
        """
        all_filings = self.discover_all_verified_filings()
        return [f for f in all_filings if f.company == company]

    def get_filings_for_market(self, market: str) -> list[VerifiedFilingEntry]:
        """
        Get all filings for a specific market.

        Args:
            market: Market identifier (e.g., 'sec')

        Returns:
            List of VerifiedFilingEntry for the market
        """
        all_filings = self.discover_all_verified_filings()
        return [f for f in all_filings if f.market == market]

    def get_available_markets(self) -> list[str]:
        """
        Get list of available markets.

        Returns:
            List of unique market identifiers
        """
        all_filings = self.discover_all_verified_filings()
        return sorted(set(f.market for f in all_filings))

    def get_available_companies(self, market: Optional[str] = None) -> list[str]:
        """
        Get list of available companies.

        Args:
            market: Optional market filter

        Returns:
            List of unique company names
        """
        if market:
            filings = self.get_filings_for_market(market)
        else:
            filings = self.discover_all_verified_filings()

        return sorted(set(f.company for f in filings))


__all__ = [
    'VerificationDataLoader',
    'VerifiedFilingEntry',
]
