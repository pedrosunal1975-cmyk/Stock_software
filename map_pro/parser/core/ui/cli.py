# Path: core/ui/cli.py
"""CLI for XBRL Filing Selection - Uses XBRLFilingsLoader to get filing info."""

from dataclasses import dataclass
from pathlib import Path
import re
from ...loaders import XBRLFilingsLoader
import logging 

@dataclass
class FilingEntry:
    """Filing information: market, company, form, date, path."""
    market: str
    company: str
    form: str
    date: str
    path: Path

class FilingCLI:
    """Interactive filing selector - delegates file discovery to loader."""
    
    def __init__(self):
        self.loader = XBRLFilingsLoader()
        self.filings: list[FilingEntry] = []
        self.logger = logging.getLogger('input.cli') 
        self.logger.info("FilingCLI initialized")  
    
    def discover(self) -> list[FilingEntry]:
        """Use loader to discover filings, then organize them."""
        # Get ALL files from loader
        all_files = self.loader.discover_all_files()
        # Group files by their filing directory
        filing_dirs: set[Path] = set()
        for file_path in all_files:
            # Find the filing directory (traverse up to find structure)
            filing_dir = self._find_filing_directory(file_path)
            if filing_dir:
                filing_dirs.add(filing_dir)
        
        # Build filing entries
        filings = []
        for filing_dir in sorted(filing_dirs):
            entry = self._build_filing_entry(filing_dir)
            if entry:
                filings.append(entry)
        
        # Sort by company
        filings.sort(key=lambda f: (f.company, f.form, f.date))
        self.filings = filings
        self.logger.info(f"Filings discovered: {len(filings)}")
        return filings
    
    def _find_filing_directory(self, file_path: Path) -> Path:
        """Find the filing directory from a file path.
        
        Expected structure: .../market/company/filings/form/accession/...
        Returns the accession directory.
        """
        parts = file_path.parts
        
        # Look for 'filings' in path
        try:
            filings_idx = parts.index('filings')
            # Filing directory should be 2 levels down from 'filings'
            # filings/form/accession
            if len(parts) > filings_idx + 2:
                filing_dir = Path(*parts[:filings_idx + 3])
                return filing_dir
        except (ValueError, IndexError):
            pass
        
        return None
    
    def _build_filing_entry(self, filing_dir: Path) -> FilingEntry:
        """Build filing entry from directory path."""
        parts = filing_dir.parts
        
        try:
            filings_idx = parts.index('filings')
            
            # Extract from path structure
            market = parts[filings_idx - 2]
            company = parts[filings_idx - 1]
            form = parts[filings_idx + 1]
            
            # Get date from instance files in this directory
            date = self._extract_date(filing_dir)
            
            return FilingEntry(
                market=market,
                company=company,
                form=form,
                date=date,
                path=filing_dir
            )
        except (ValueError, IndexError):
            return None
    
    def _extract_date(self, filing_dir: Path) -> str:
        """Extract date from instance file names in this directory."""
        date_pattern = re.compile(r'[-_](\d{8})[._]')
        
        # Look through files in this directory
        for f in filing_dir.rglob('*'):
            if f.is_file() and f.suffix in ['.xml', '.htm', '.html']:
                match = date_pattern.search(f.name)
                if match:
                    d = match.group(1)
                    return f"{d[0:4]}-{d[4:6]}-{d[6:8]}"
        
        return filing_dir.name
    
    def display(self) -> None:
        """Display numbered list of filings."""
        if not self.filings:
            print("No filings found.")
            return
        
        print("\n" + "=" * 100)
        print("AVAILABLE FILINGS")
        print("=" * 100)
        print(f"\n{'#':>4} | {'MARKET':8} | {'COMPANY':40} | {'FORM':10} | DATE")
        print("-" * 100)
        
        for i, f in enumerate(self.filings, 1):
            print(f"{i:4}. {f.market:8} | {f.company:40} | {f.form:10} | {f.date}")
        
        print(f"\nTotal: {len(self.filings)} filings")
        print("=" * 100 + "\n")
    
    def select(self, number: int) -> FilingEntry:
        """Return filing by number (1-indexed)."""
        if number < 1 or number > len(self.filings):
            raise ValueError(f"Invalid selection {number}. Choose 1-{len(self.filings)}.")
        return self.filings[number - 1]
    
    def get_input(self) -> int:
        """Get validated user input."""
        while True:
            try:
                user_input = input("Select filing number: ").strip()
                
                if not user_input:
                    print("[ERROR] Enter a number.\n")
                    continue
                
                number = int(user_input)
                
                if number < 1 or number > len(self.filings):
                    print(f"[ERROR] Choose 1-{len(self.filings)}.\n")
                    continue
                
                return number
                
            except ValueError:
                print(f"[ERROR] '{user_input}' is not a number.\n")
                self.logger.warning(f"User input error: {f"Invalid input: {user_input}"}")
            except KeyboardInterrupt:
                print("\n\nCancelled.")
                raise
    
    def run(self) -> FilingEntry:
        """Run complete selection workflow."""
        self.discover()
        
        if not self.filings:
            raise RuntimeError("No filings found")
        
        self.display()
        number = self.get_input()
        filing = self.select(number)
        
        print(f"\nSelected: {filing.market} | {filing.company} | {filing.form} | {filing.date}")
        print(f"Path: {filing.path}\n")
        
        self.logger.info(f"User selection: {filing.market, filing.company, filing.form, filing.date}")
        
        return filing


__all__ = ['FilingCLI', 'FilingEntry']