# Path: core/ui/cli.py
"""
Mapping CLI - Filing Selection Interface

Simple CLI for selecting parsed filings to map.
Displays only company, form, and date - no file type clutter.
"""

import logging
from typing import Optional

from ...loaders.parsed_data import ParsedDataLoader, ParsedFilingEntry
from ...core.config_loader import ConfigLoader


class MappingCLI:
    """
    Interactive CLI for selecting parsed filings.
    
    Displays available filings (company, form, date) for user selection.
    Loader provides file access - CLI just displays choices.
    
    Example:
        cli = MappingCLI()
        filing = cli.run()
        if filing:
            # Orchestrator will get the files it needs from filing.available_files
            process_filing(filing)
    """
    
    def __init__(self):
        """Initialize CLI with loader."""
        self.config = ConfigLoader()
        self.loader = ParsedDataLoader(self.config)
        self.filings: list[ParsedFilingEntry] = []
        self.logger = logging.getLogger('input.cli')
        self.logger.info("MappingCLI initialized")
    
    def run(self) -> Optional[ParsedFilingEntry]:
        """
        Run interactive filing selection.
        
        Returns:
            Selected ParsedFilingEntry or None if cancelled
        """
        # Discover available filings using loader
        self.filings = self.loader.discover_all_parsed_filings()
        
        if not self.filings:
            raise RuntimeError(
                f"No parsed filings found in {self.loader.parser_output_dir}. "
                "Please run the parser first."
            )
        
        # Display filings
        self._display_filings()
        
        # Get user selection
        selected = self._get_user_selection()
        
        if selected:
            self.logger.info(f"Selected: {selected.company} | {selected.form} | {selected.date}")
        
        return selected
    
    def _display_filings(self) -> None:
        """Display available parsed filings."""
        print("\n" + "=" * 100)
        print("AVAILABLE PARSED FILINGS")
        print("=" * 100)
        print(f"   # | {'COMPANY':<45} | {'FORM':<10} | {'DATE':<12}")
        print("-" * 100)
        
        for idx, filing in enumerate(self.filings, 1):
            # Display folder name as-is (with underscores)
            print(f"   {idx}. {filing.company:<45} | {filing.form:<10} | {filing.date:<12}")
        
        print("=" * 100)
        print(f"Total: {len(self.filings)} parsed filings")
        print("=" * 100)
    
    def _get_user_selection(self) -> Optional[ParsedFilingEntry]:
        """
        Get user's filing selection.
        
        Returns:
            Selected filing or None if cancelled
        """
        while True:
            try:
                choice = input(f"Select filing number: ").strip()
                
                if choice.lower() == 'q':
                    return None
                
                idx = int(choice)
                
                if 1 <= idx <= len(self.filings):
                    return self.filings[idx - 1]
                else:
                    print(f"Invalid selection. Please enter 1-{len(self.filings)}")
                    
            except ValueError:
                print("Invalid input. Please enter a number or 'q' to quit")
            except KeyboardInterrupt:
                print("\nCancelled")
                return None


__all__ = ['MappingCLI']