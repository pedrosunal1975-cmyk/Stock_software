# Path: mat_acc/ratio_check/source_checker.py
"""
Source Checker

Verifies physical existence of required source files:
- Mapped statements (from mapper module)
- Parsed JSON (from parser module)
- XBRL filings (raw filing documents)

Uses mat_acc loaders to discover and verify files.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config_loader import ConfigLoader

# Import IPO logging (INPUT layer for source file verification)
from core.logger.ipo_logging import get_input_logger

from loaders import (
    MappedDataLoader, MappedFilingEntry,
    ParsedDataLoader, ParsedFilingEntry,
    XBRLDataLoader,
)


# Use IPO-aware logger (INPUT layer - source verification)
logger = get_input_logger('source_checker')


@dataclass
class SourceAvailability:
    """
    Availability status of source files for a filing.

    Attributes:
        company: Company name
        market: Market identifier
        form: Form type
        date: Filing date
        mapped_available: Whether mapped statements exist
        mapped_entry: MappedFilingEntry if available
        mapped_file_count: Number of mapped statement files
        parsed_available: Whether parsed.json exists
        parsed_entry: ParsedFilingEntry if available
        xbrl_available: Whether XBRL filing exists
        xbrl_path: Path to XBRL filing directory if available
        warnings: List of warning messages
    """
    company: str
    market: str
    form: str
    date: str

    mapped_available: bool = False
    mapped_entry: Optional[MappedFilingEntry] = None
    mapped_file_count: int = 0

    parsed_available: bool = False
    parsed_entry: Optional[ParsedFilingEntry] = None

    xbrl_available: bool = False
    xbrl_path: Optional[Path] = None

    warnings: list[str] = field(default_factory=list)

    @property
    def all_sources_available(self) -> bool:
        """Check if all required sources are available."""
        return self.mapped_available and self.parsed_available and self.xbrl_available

    @property
    def minimum_sources_available(self) -> bool:
        """Check if minimum required sources are available (mapped statements)."""
        return self.mapped_available

    @property
    def status_summary(self) -> str:
        """Get a summary of source availability."""
        parts = []
        parts.append(f"Mapped: {'[OK]' if self.mapped_available else '[--]'}")
        parts.append(f"Parsed: {'[OK]' if self.parsed_available else '[--]'}")
        parts.append(f"XBRL: {'[OK]' if self.xbrl_available else '[--]'}")
        return " | ".join(parts)

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)
        logger.warning(f"{self.company}: {message}")


class SourceChecker:
    """
    Verifies physical existence of source files.

    Uses mat_acc loaders to discover and check file availability.
    Reports warnings for missing sources.

    Example:
        checker = SourceChecker(config)
        availability = checker.check_sources(company, market, form, date)
        if not availability.all_sources_available:
            for warning in availability.warnings:
                print(f"WARNING: {warning}")
    """

    def __init__(self, config: ConfigLoader):
        """
        Initialize source checker.

        Args:
            config: ConfigLoader instance
        """
        self.config = config
        self.logger = get_input_logger('source_checker')

        # Initialize loaders
        self._mapped_loader: Optional[MappedDataLoader] = None
        self._parsed_loader: Optional[ParsedDataLoader] = None
        self._xbrl_loader: Optional[XBRLDataLoader] = None

        # Cache discovered filings
        self._mapped_filings: Optional[list[MappedFilingEntry]] = None
        self._parsed_filings: Optional[list[ParsedFilingEntry]] = None

    def _get_mapped_loader(self) -> Optional[MappedDataLoader]:
        """Get or create mapped data loader."""
        if self._mapped_loader is None:
            try:
                self._mapped_loader = MappedDataLoader(self.config)
            except Exception as e:
                self.logger.warning(f"Could not initialize MappedDataLoader: {e}")
        return self._mapped_loader

    def _get_parsed_loader(self) -> Optional[ParsedDataLoader]:
        """Get or create parsed data loader."""
        if self._parsed_loader is None:
            try:
                self._parsed_loader = ParsedDataLoader(self.config)
            except Exception as e:
                self.logger.warning(f"Could not initialize ParsedDataLoader: {e}")
        return self._parsed_loader

    def _get_xbrl_loader(self) -> Optional[XBRLDataLoader]:
        """Get or create XBRL data loader."""
        if self._xbrl_loader is None:
            try:
                self._xbrl_loader = XBRLDataLoader(self.config)
            except Exception as e:
                self.logger.warning(f"Could not initialize XBRLDataLoader: {e}")
        return self._xbrl_loader

    def discover_all_mapped(self) -> list[MappedFilingEntry]:
        """
        Discover all available mapped filings.

        Returns:
            List of MappedFilingEntry objects
        """
        if self._mapped_filings is not None:
            return self._mapped_filings

        loader = self._get_mapped_loader()
        if loader is None:
            return []

        try:
            self._mapped_filings = loader.discover_all_mapped_filings()
            self.logger.info(f"Discovered {len(self._mapped_filings)} mapped filings")
            return self._mapped_filings
        except Exception as e:
            self.logger.error(f"Error discovering mapped filings: {e}")
            return []

    def discover_all_parsed(self) -> list[ParsedFilingEntry]:
        """
        Discover all available parsed filings.

        Returns:
            List of ParsedFilingEntry objects
        """
        if self._parsed_filings is not None:
            return self._parsed_filings

        loader = self._get_parsed_loader()
        if loader is None:
            return []

        try:
            self._parsed_filings = loader.discover_all_parsed_filings()
            self.logger.info(f"Discovered {len(self._parsed_filings)} parsed filings")
            return self._parsed_filings
        except Exception as e:
            self.logger.error(f"Error discovering parsed filings: {e}")
            return []

    def find_xbrl_path(
        self,
        company: str,
        market: str,
        form: str,
        date: str
    ) -> Optional[Path]:
        """
        Find XBRL filing directory for a specific filing.

        Uses XBRLDataLoader.find_filing_for_company which does
        a blind recursive search for the filing.

        Returns:
            Path to XBRL filing directory or None
        """
        loader = self._get_xbrl_loader()
        if loader is None:
            return None

        try:
            path = loader.find_filing_for_company(market, company, form, date)
            return path
        except Exception as e:
            self.logger.warning(f"Error finding XBRL filing: {e}")
            return None

    def find_mapped_filing(
        self,
        company: str,
        market: str,
        form: str,
        date: str
    ) -> Optional[MappedFilingEntry]:
        """
        Find a specific mapped filing.

        Uses loader's built-in find method - engine adapts to loader's API.
        """
        loader = self._get_mapped_loader()
        if loader is None:
            return None

        try:
            return loader.find_mapped_filing(market, company, form, date)
        except Exception as e:
            self.logger.warning(f"Error finding mapped filing: {e}")
            return None

    def find_parsed_filing(
        self,
        company: str,
        market: str,
        form: str,
        date: str
    ) -> Optional[ParsedFilingEntry]:
        """
        Find a specific parsed filing.

        Uses loader's built-in find method - engine adapts to loader's API.
        """
        loader = self._get_parsed_loader()
        if loader is None:
            return None

        try:
            return loader.find_parsed_filing(market, company, form, date)
        except Exception as e:
            self.logger.warning(f"Error finding parsed filing: {e}")
            return None


    def check_sources(
        self,
        company: str,
        market: str,
        form: str,
        date: str
    ) -> SourceAvailability:
        """
        Check availability of all source files for a filing.

        Args:
            company: Company name
            market: Market identifier
            form: Form type
            date: Filing date

        Returns:
            SourceAvailability with status of all sources
        """
        availability = SourceAvailability(
            company=company,
            market=market,
            form=form,
            date=date,
        )

        # Check mapped statements
        mapped = self.find_mapped_filing(company, market, form, date)
        if mapped:
            availability.mapped_available = True
            availability.mapped_entry = mapped
            availability.mapped_file_count = len(mapped.available_files.get('json', []))
        else:
            availability.add_warning("Mapped statements not found")

        # Check parsed.json
        parsed = self.find_parsed_filing(company, market, form, date)
        if parsed:
            availability.parsed_available = True
            availability.parsed_entry = parsed
        else:
            availability.add_warning("Parsed filing (parsed.json) not found")

        # Check XBRL filing
        xbrl_path = self.find_xbrl_path(company, market, form, date)
        if xbrl_path:
            availability.xbrl_available = True
            availability.xbrl_path = xbrl_path
        else:
            availability.add_warning("XBRL filing not found")

        return availability

    def check_sources_for_entry(
        self,
        mapped_entry: MappedFilingEntry
    ) -> SourceAvailability:
        """
        Check availability of sources for a known mapped filing.

        Args:
            mapped_entry: Known MappedFilingEntry

        Returns:
            SourceAvailability with status of all sources
        """
        return self.check_sources(
            company=mapped_entry.company,
            market=mapped_entry.market,
            form=mapped_entry.form,
            date=mapped_entry.date,
        )

    def refresh_cache(self) -> None:
        """Clear cached filing lists to force rediscovery."""
        self._mapped_filings = None
        self._parsed_filings = None


__all__ = ['SourceChecker', 'SourceAvailability']
