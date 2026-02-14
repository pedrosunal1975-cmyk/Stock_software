# Path: mat_acc/ratio_check/filing_menu.py
"""
Filing Menu - Company Selection Interface

Simple CLI for selecting filings to analyze.
Displays only company, form, and date - no file type clutter.
Source discovery is the engine's job, not the user's concern.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from config_loader import ConfigLoader

# Import IPO logging (INPUT layer for user input/menu)
from core.logger.ipo_logging import get_input_logger

from loaders import MappedDataLoader, MappedFilingEntry


# Use IPO-aware logger (INPUT layer - user interaction)
logger = get_input_logger('filing_menu')


@dataclass
class FilingSelection:
    """
    Selected filing for analysis.

    Attributes:
        index: Selection index
        company: Company name
        market: Market identifier
        form: Form type
        date: Filing date
        mapped_entry: The underlying MappedFilingEntry
    """
    index: int
    company: str
    market: str
    form: str
    date: str
    mapped_entry: MappedFilingEntry


class FilingMenu:
    """
    CLI menu for company/filing selection.

    Discovers available mapped statements and presents them
    as a simple numbered menu. Source availability is the engine's
    concern, not displayed to the user.

    Example:
        menu = FilingMenu(config)
        selection = menu.run()

        if selection:
            # Engine will figure out which sources to use
            process_filing(selection)
    """

    def __init__(self, config: ConfigLoader):
        """
        Initialize filing menu.

        Args:
            config: ConfigLoader instance
        """
        self.config = config
        self.logger = get_input_logger('filing_menu')
        self._loader = MappedDataLoader(config)
        self._filings: list[MappedFilingEntry] = []
        self._options: list[FilingSelection] = []

    def discover_filings(self) -> list[FilingSelection]:
        """
        Discover all available filings.

        Returns:
            List of FilingSelection options
        """
        self._filings = self._loader.discover_all_mapped_filings()
        self._options = []

        if not self._filings:
            self.logger.warning("No mapped filings found")
            return []

        for i, filing in enumerate(self._filings, 1):
            self._options.append(FilingSelection(
                index=i,
                company=filing.company,
                market=filing.market,
                form=filing.form,
                date=filing.date,
                mapped_entry=filing,
            ))

        self.logger.info(f"Discovered {len(self._options)} filings")
        return self._options

    def display_menu(self) -> None:
        """Display the filing selection menu."""
        if not self._options:
            self.discover_filings()

        print()
        print("=" * 100)
        print("  AVAILABLE FILINGS FOR RATIO ANALYSIS")
        print("=" * 100)

        if not self._options:
            print("\n  No mapped filings found.")
            mapper_dir = self.config.get('mapper_output_dir')
            print(f"\n  Expected location: {mapper_dir}")
            print("=" * 100)
            return

        # Header
        print(f"   {'#':>3} | {'MARKET':<8} | {'COMPANY':<40} | {'FORM':<10} | {'DATE':<12}")
        print("-" * 100)

        # Group by market for cleaner display
        by_market = {}
        for opt in self._options:
            if opt.market not in by_market:
                by_market[opt.market] = []
            by_market[opt.market].append(opt)

        for market in sorted(by_market.keys()):
            for opt in by_market[market]:
                print(f"   {opt.index:3d} | {opt.market:<8} | {opt.company:<40} | {opt.form:<10} | {opt.date:<12}")

        print("=" * 100)
        print(f"  Total: {len(self._options)} filings")
        print("=" * 100)

    def get_selection(self) -> Optional[FilingSelection]:
        """
        Get user selection.

        Returns:
            FilingSelection or None (quit)
        """
        while True:
            try:
                choice = input("\n  Select filing number (or 'q' to quit): ").strip().lower()

                if choice == 'q':
                    return None

                idx = int(choice)
                for opt in self._options:
                    if opt.index == idx:
                        return opt

                print(f"  [!] Please enter a valid number (1-{len(self._options)})")

            except ValueError:
                print("  [!] Invalid input. Enter a number or 'q' to quit.")
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
                return None

    def run(self) -> Optional[FilingSelection]:
        """
        Run the interactive menu.

        Returns:
            Selected FilingSelection or None if quit
        """
        self.display_menu()

        if not self._options:
            return None

        return self.get_selection()


__all__ = ['FilingMenu', 'FilingSelection']
