# Path: mat_acc/core/ui/user_input.py
"""
User Input Module for mat_acc (Mathematical Accountancy)

Handles user interaction for:
- Browsing verified companies (90%+ verification score)
- Selecting filings for analysis
- Triggering library.py to ensure taxonomies are available
- Choosing analysis options

Workflow:
1. Scan verification reports directory
2. Filter for 90%+ verified companies
3. Trigger library.py --scan, --process-manual, and --download to ensure taxonomies
4. Display qualified companies for user selection

Reads from verification reports directory to show available filings.
Only filings that passed verification (90%+) are available for analysis.
"""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config_loader import ConfigLoader
from core.logger import get_input_logger

# Minimum verification score to show in menu (90%)
MIN_DISPLAY_SCORE = 90.0

logger = get_input_logger('user_input')


@dataclass
class VerifiedFiling:
    """
    Represents a verified filing available for analysis.

    Attributes:
        market: Market identifier (e.g., 'sec')
        company: Company name
        form: Form type (e.g., '10_K')
        date: Filing date
        report_path: Path to verification report JSON
        verification_score: Score from verification
    """
    market: str
    company: str
    form: str
    date: str
    report_path: Path
    verification_score: Optional[float] = None


class CompanySelector:
    """
    Interactive selector for verified companies and filings.

    Scans the verification reports directory to find all verified filings.
    Presents them to the user for selection.

    Example:
        selector = CompanySelector()
        filings = selector.get_available_filings()
        selected = selector.select_filing()
    """

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize company selector.

        Args:
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        self.verification_reports_dir = self.config.get('verification_reports_dir')
        self.min_score = MIN_DISPLAY_SCORE  # 90% threshold for display
        self.library_py_path = self._find_library_py()

        if not self.verification_reports_dir:
            raise ValueError(
                "Verification reports directory not configured. "
                "Check MAT_ACC_VERIFICATION_REPORTS_DIR in .env"
            )

        logger.info(f"CompanySelector initialized: {self.verification_reports_dir}")

    def _find_library_py(self) -> Optional[Path]:
        """
        Find the map_pro library.py script from config.

        Returns:
            Path to library.py or None if not found
        """
        # Get library path from config
        library_path = self.config.get('library_script_path')
        if library_path and library_path.exists():
            logger.info(f"Found library.py at: {library_path}")
            return library_path

        # Fallback: relative to this file's location
        relative_path = Path(__file__).parent.parent.parent.parent / 'library/library.py'
        if relative_path.exists():
            logger.info(f"Found library.py at: {relative_path}")
            return relative_path

        logger.warning("library.py not found. Check MAT_ACC_LIBRARY_SCRIPT_PATH in .env")
        return None

    def ensure_taxonomies_available(self) -> bool:
        """
        Trigger library.py to scan and download required taxonomies.

        Runs:
        1. library.py --scan (scan parsed filings for taxonomy requirements)
        2. library.py --process-manual (process any manually downloaded ZIPs)
        3. library.py --download (download any missing taxonomies)

        Returns:
            True if successful, False otherwise
        """
        if not self.library_py_path:
            logger.warning("Cannot ensure taxonomies: library.py not found")
            print("[WARN] library.py not found - taxonomies may not be available")
            return False

        try:
            print("\n[INFO] Scanning for taxonomy requirements...")
            logger.info("Running library.py --scan")

            # Run library.py --scan
            result_scan = subprocess.run(
                [sys.executable, str(self.library_py_path), '--scan'],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result_scan.returncode != 0:
                logger.warning(f"library.py --scan returned {result_scan.returncode}")
                if result_scan.stderr:
                    logger.warning(f"stderr: {result_scan.stderr}")
            else:
                logger.info("library.py --scan completed successfully")

            # Run library.py --process-manual (process any manually downloaded ZIPs)
            print("[INFO] Processing manual taxonomy downloads...")
            logger.info("Running library.py --process-manual")

            result_manual = subprocess.run(
                [sys.executable, str(self.library_py_path), '--process-manual'],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes for extraction
            )

            if result_manual.returncode != 0:
                logger.warning(f"library.py --process-manual returned {result_manual.returncode}")
                if result_manual.stderr:
                    logger.warning(f"stderr: {result_manual.stderr}")
            else:
                logger.info("library.py --process-manual completed successfully")

            print("[INFO] Downloading required taxonomies...")
            logger.info("Running library.py --download")

            # Run library.py --download
            result_download = subprocess.run(
                [sys.executable, str(self.library_py_path), '--download'],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes for downloads
            )

            if result_download.returncode != 0:
                logger.warning(f"library.py --download returned {result_download.returncode}")
                if result_download.stderr:
                    logger.warning(f"stderr: {result_download.stderr}")
                return False
            else:
                logger.info("library.py --download completed successfully")
                print("[OK] Taxonomy libraries ready")
                return True

        except subprocess.TimeoutExpired:
            logger.error("library.py timed out")
            print("[FAIL] Taxonomy operations timed out")
            return False
        except Exception as e:
            logger.error(f"Failed to run library.py: {e}")
            print(f"[FAIL] Could not run library.py: {e}")
            return False

    def get_available_filings(self) -> list[VerifiedFiling]:
        """
        Discover all verified filings in the verification reports directory.

        Recursively searches for verification_report.json files.
        Extracts metadata from directory structure.

        Returns:
            List of VerifiedFiling objects
        """
        if not self.verification_reports_dir.exists():
            logger.warning(
                f"Verification reports directory not found: "
                f"{self.verification_reports_dir}"
            )
            return []

        logger.info(f"Scanning verification reports: {self.verification_reports_dir}")

        filings = []

        # Find all verification_report.json files
        for report_file in self.verification_reports_dir.rglob('verification_report.json'):
            filing = self._build_filing_entry(report_file)
            if filing:
                filings.append(filing)

        # Sort by market, company, form, date
        filings.sort(key=lambda f: (f.market, f.company, f.form, f.date))

        logger.info(f"Found {len(filings)} verified filings")
        return filings

    def _build_filing_entry(self, report_path: Path) -> Optional[VerifiedFiling]:
        """
        Build VerifiedFiling from report path.

        Extracts metadata from directory structure:
        /verification_reports/{market}/{company}/{form}/{date}/verification_report.json

        Args:
            report_path: Path to verification_report.json

        Returns:
            VerifiedFiling or None if invalid
        """
        try:
            # Extract parts from path
            # Expected: .../market/company/form/date/verification_report.json
            parts = report_path.relative_to(self.verification_reports_dir).parts

            if len(parts) < 4:
                logger.warning(f"Unexpected path structure: {report_path}")
                return None

            # date is parts[-2], form is parts[-3], company is parts[-4], market is parts[-5]
            date = parts[-2]
            form = parts[-3]
            company = parts[-4]
            market = parts[-5] if len(parts) >= 5 else 'unknown'

            # Try to read verification score from file
            score = self._read_verification_score(report_path)

            return VerifiedFiling(
                market=market,
                company=company,
                form=form,
                date=date,
                report_path=report_path,
                verification_score=score,
            )

        except Exception as e:
            logger.warning(f"Failed to build filing entry from {report_path}: {e}")
            return None

    def _read_verification_score(self, report_path: Path) -> Optional[float]:
        """
        Read verification score from report JSON.

        Args:
            report_path: Path to verification_report.json

        Returns:
            Verification score or None
        """
        try:
            import json
            with open(report_path) as f:
                data = json.load(f)
            return data.get('summary', {}).get('score')
        except Exception:
            return None

    def select_filing(self) -> Optional[VerifiedFiling]:
        """
        Interactive filing selection.

        Workflow:
        1. Scan verification reports
        2. Filter for 90%+ verification score
        3. Trigger library.py to ensure taxonomies are available
        4. Display qualified filings for selection

        Returns:
            Selected VerifiedFiling or None if cancelled
        """
        # Get all filings and filter by 90%+ score
        all_filings = self.get_available_filings()
        filings = [
            f for f in all_filings
            if f.verification_score is not None and f.verification_score >= MIN_DISPLAY_SCORE
        ]

        if not all_filings:
            print("\nNo verification reports found.")
            print(f"Check directory: {self.verification_reports_dir}")
            print("\nRun map_pro verification module first to generate reports.")
            return None

        if not filings:
            print(f"\nNo filings with verification score >= {MIN_DISPLAY_SCORE}%")
            print(f"Found {len(all_filings)} filings, but none meet the threshold.")
            print("\nLower-score filings:")
            for f in all_filings[:5]:
                score = f.verification_score or 0
                print(f"  - {f.company} | {f.form} | Score: {score:.1f}%")
            return None

        # Trigger library.py to ensure taxonomies are available
        print(f"\n[INFO] Found {len(filings)} filings with 90%+ verification score")
        self.ensure_taxonomies_available()

        # Display menu
        print("\n" + "=" * 70)
        print(f"  Verified Filings (>= {MIN_DISPLAY_SCORE}% score):")
        print("-" * 70)

        for i, filing in enumerate(filings, 1):
            score_str = f"{filing.verification_score:.1f}" if filing.verification_score else "N/A"
            print(f"  {i:3d}. {filing.market:<6} | {filing.company:<20} | {filing.form:<8} | {filing.date} | {score_str}%")

        print("-" * 70)
        print("    0. Exit")
        print("   -1. Analyze ALL filings")
        print("=" * 70)

        # Get selection
        selection = get_user_selection(len(filings))

        if selection == 0:
            return None
        elif selection == -1:
            # Return all filings (caller handles this)
            return filings  # type: ignore
        else:
            return filings[selection - 1]

    def get_filings_above_threshold(
        self,
        min_score: Optional[float] = None
    ) -> list[VerifiedFiling]:
        """
        Get filings with verification score above threshold.

        Args:
            min_score: Minimum verification score (default from config)

        Returns:
            List of filings meeting threshold
        """
        threshold = min_score if min_score is not None else self.min_score
        all_filings = self.get_available_filings()

        qualified = [
            f for f in all_filings
            if f.verification_score is not None and f.verification_score >= threshold
        ]

        logger.info(
            f"Found {len(qualified)}/{len(all_filings)} filings "
            f"with score >= {threshold}"
        )

        return qualified


def display_menu(title: str, options: list[str], show_all: bool = True) -> None:
    """
    Display a numbered menu.

    Args:
        title: Menu title
        options: List of option strings
        show_all: Whether to show "Analyze ALL" option
    """
    print("\n" + "=" * 60)
    print(title)
    print("-" * 60)

    for i, option in enumerate(options, 1):
        print(f"  {i:3d}. {option}")

    print("-" * 60)
    print("    0. Exit")
    if show_all:
        print("   -1. Process ALL")
    print("=" * 60)


def get_user_selection(max_value: int) -> int:
    """
    Get numeric selection from user.

    Args:
        max_value: Maximum valid selection

    Returns:
        User selection (0=exit, -1=all, 1 to max_value=specific)
    """
    while True:
        try:
            choice = input("\nEnter selection: ").strip()
            if not choice:
                continue

            value = int(choice)

            if value == 0:
                return 0
            elif value == -1:
                return -1
            elif 1 <= value <= max_value:
                return value
            else:
                print(f"Invalid selection. Enter 1-{max_value}, 0 to exit, or -1 for all.")

        except ValueError:
            print("Please enter a valid number.")
        except KeyboardInterrupt:
            print("\n[Cancelled]")
            return 0


def confirm_action(prompt: str, default: bool = False) -> bool:
    """
    Prompt user for yes/no confirmation.

    Args:
        prompt: Question to display
        default: Default answer if user just presses Enter

    Returns:
        True for yes, False for no
    """
    suffix = " [Y/n]: " if default else " [y/N]: "

    while True:
        try:
            response = input(prompt + suffix).strip().lower()

            if not response:
                return default

            if response in ('y', 'yes'):
                return True
            elif response in ('n', 'no'):
                return False
            else:
                print("Please enter 'y' or 'n'.")

        except KeyboardInterrupt:
            print("\n[Cancelled]")
            return False


__all__ = [
    'VerifiedFiling',
    'CompanySelector',
    'display_menu',
    'get_user_selection',
    'confirm_action',
]
