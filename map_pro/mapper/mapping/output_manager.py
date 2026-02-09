# Path: mapping/output_manager.py
"""
Output Manager

Handles output folder structure and file organization.
Uses constants.py for all configuration values.
"""

import logging
import re
from pathlib import Path
from typing import Optional
from datetime import datetime

from ..mapping.constants import (
    OUTPUT_FORMAT_DIRECTORIES,
    DATE_SEPARATORS,
    YEAR_MIN,
    YEAR_MAX,
    MAX_FILENAME_LENGTH,
    MAX_ENTITY_NAME_LENGTH,
    DEFAULT_ENTITY_NAME,
    FILENAME_SPACE_REPLACEMENT,
    FILENAME_DASH_REPLACEMENT,
    DEBUG_SEPARATOR,
)



class OutputManager:
    """
    Manages output folder structure.

    Structure: {market}/{entity}/{filing_type}/{period}/{format}/

    Period extraction:
    - Extracts from period_end in characteristics
    - Uses whatever date format parser provides (market-agnostic)
    - No reformatting, no expectations, no assumptions
    - Each filing instance gets its own directory

    Examples:
    - sec/Albertson_Companies__Inc__/10_K/2025-01-30/json/
    - sec/Albertson_Companies__Inc__/10_Q/2024-07-23/csv/
    - esma/Some_EU_Company/Annual_Report/2023-12-31/excel/
    """
    
    def __init__(self, base_output_dir: Path):
        """
        Initialize output manager.
        
        Args:
            base_output_dir: Base output directory
        """
        self.base_dir = base_output_dir
        self.logger = logging.getLogger('mapping.output_manager')
    
    def create_output_structure(self, characteristics: dict[str, any]) -> Path:
        # Build hierarchical path
        market = self._safe_str(characteristics.get('market', 'unknown'))
        entity = self._safe_str(characteristics.get('entity_name'), max_len=MAX_ENTITY_NAME_LENGTH)
        filing_type = self._safe_str(characteristics.get('filing_type'))
        filing_type = filing_type.replace('-', FILENAME_DASH_REPLACEMENT)
        
        period = self._extract_period(characteristics)
        
        # Create path: market/entity/filing_type/period/
        output_folder = self.base_dir / market / entity / filing_type / period
        output_folder.mkdir(parents=True, exist_ok=True)
        
        # Create format subdirectories
        for format_dir in OUTPUT_FORMAT_DIRECTORIES:
            (output_folder / format_dir).mkdir(exist_ok=True)
        
        self.logger.info(f"Created output structure: {output_folder}")
        
        return output_folder
    
    def _extract_period(self, characteristics: dict[str, any]) -> str:
        """
        Extract period folder name from period_end.

        Returns full date (YYYY-MM-DD) to match parser's directory structure.
        Each filing instance gets its own directory.

        Logic:
        1. If period_end exists → return YYYY-MM-DD
        2. Otherwise → timestamp (indicates extraction error)

        Args:
            characteristics: Filing characteristics

        Returns:
            Period string in YYYY-MM-DD format
        """
        period_end = characteristics.get('period_end')

        # Use period_end (what the report covers)
        if period_end:
            period = self._parse_period_end(period_end)
            if period:
                self.logger.info(f"Using period_end date: {period}")
                return period

        # If no period_end found - this is an ERROR
        fallback = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.logger.error(
            f"PERIOD_END NOT FOUND - Using timestamp fallback: {fallback}. "
            f"This indicates period_end was not extracted from parsed.json."
        )
        return fallback
    
    def _parse_period_end(self, date_str: str) -> Optional[str]:
        """
        MARKET-AGNOSTIC: Uses whatever date format the parser provides.

        No assumptions about date format or structure. Simply:
        1. Strips ISO time component (T...) if present
        2. Replaces filesystem-unsafe characters with dashes
        3. Returns the date as-is

        This ensures compatibility with any market's date format:
        - YYYY-MM-DD (US/ISO)
        - YYYY_MM__DD (underscores)
        - DD-MM-YYYY (European)
        - DDMMYYYY (compact)
        - Or any other format

        The parser determines the format. Mapper just uses it.

        Args:
            date_str: Date string in any format from parser

        Returns:
            Filesystem-safe date string in original format, or None
        """
        if not date_str:
            return None

        try:
            date_str = str(date_str).strip()

            if not date_str:
                return None

            # Only strip ISO time component if present
            if 'T' in date_str:
                date_str = date_str.split('T')[0]

            # Replace filesystem-unsafe characters with dashes
            # (but keep underscores, as they may be part of the format)
            date_str = date_str.replace('/', '-')
            date_str = date_str.replace('\\', '-')
            date_str = date_str.replace(':', '-')

            # Return as-is (no parsing, no reformatting, no expectations)
            return date_str if date_str else None

        except Exception as e:
            self.logger.warning(f"Error processing date string '{date_str}': {e}")
            return None
    
    def _parse_date_to_month(self, date_str: str) -> Optional[str]:
        """Extract year and month from date string (YYYY_MM)."""
        if not date_str:
            return None
        
        try:
            date_str = str(date_str).strip()
            
            if '-' in date_str:
                parts = date_str.split('-')
            elif '/' in date_str:
                parts = date_str.split('/')
            else:
                # YYYYMMDD
                year = date_str[:4]
                month = date_str[4:6]
                parts = [year, month]
            
            if len(parts) >= 2:
                year = parts[0]
                month = parts[1]
                
                if year.isdigit() and month.isdigit():
                    return f"{year}_{month}"
        except Exception as e:
            self.logger.debug(f"Could not parse month from {date_str}: {e}")
        
        return None
    
    @staticmethod
    def _safe_str(value, max_len: int = None) -> str:
        """
        Make string filesystem-safe using constants.
        
        Args:
            value: String to sanitize
            max_len: Maximum length (uses MAX_FILENAME_LENGTH if not specified)
            
        Returns:
            Filesystem-safe string
        """
        if not value:
            return DEFAULT_ENTITY_NAME
        
        # Use default max length if not specified
        if max_len is None:
            max_len = MAX_FILENAME_LENGTH
        
        # Convert to string
        s = str(value)
        
        # Remove invalid characters (keep only word chars, spaces, hyphens)
        s = re.sub(r'[^\w\s-]', '', s)
        
        # Replace spaces and hyphens with underscores
        s = re.sub(r'[-\s]+', FILENAME_SPACE_REPLACEMENT, s)
        
        # Remove consecutive underscores
        s = re.sub(r'_+', '_', s)
        
        # Trim
        s = s.strip('_')
        
        # Limit length
        if len(s) > max_len:
            s = s[:max_len].rstrip('_')
        
        return s if s else DEFAULT_ENTITY_NAME


__all__ = ['OutputManager']