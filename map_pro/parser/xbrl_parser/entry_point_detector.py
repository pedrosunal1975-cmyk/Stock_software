# Path: parser/xbrl_parser/entry_point_detector.py
"""
Entry Point Detection for XBRL Filings

Universal, market-agnostic algorithm for identifying the main instance document
in XBRL filing packages. Handles both traditional XML and iXBRL HTML formats.

This module implements a robust scoring system that works across:
- SEC filings (US) - both iXBRL and XML
- ESMA/ESEF filings (EU) - iXBRL packages
- FRC filings (UK) - iXBRL
- Traditional XBRL (XML) - older format
- any other market's XBRL format

Key Design Principles:
1. EXCLUDE known non-instance files (exhibits, linkbases, schemas)
2. SCORE remaining candidates using positive indicators
3. SELECT highest-scoring file as main instance

No hardcoded company names, no market-specific logic, no pattern matching
for specific companies. Pure algorithmic detection based on XBRL structure.
"""

import logging
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .constants import (
    EXHIBIT_PATTERNS,
    LINKBASE_SUFFIXES,
    NON_XBRL_EXTENSIONS,
    EXCLUDED_FILENAMES,
    SIZE_LARGE_THRESHOLD,
    SIZE_MEDIUM_THRESHOLD,
    SIZE_SMALL_PENALTY,
    SCORE_IXBRL_FORMAT,
    SCORE_DATE_PATTERN,
    SCORE_SHORT_FILENAME,
    SCORE_SCHEMA_MATCH,
    SCORE_LARGE_FILE,
    SCORE_MEDIUM_FILE,
    SCORE_XML_INSTANCE,
    SCORE_XML_FORMAT,
    SCORE_TICKER_PATTERN,
    SCORE_SIMPLE_FILENAME,
    SCORE_EXTRACTED_DIR,
    PENALTY_SMALL_FILE,
    PENALTY_LONG_FILENAME,
    PENALTY_FORM_TYPE,
    PENALTY_MANY_UNDERSCORES,
    TICKER_PATTERNS,
    MAX_SIMPLE_FILENAME_LENGTH,
    MAX_FILENAME_LENGTH,
    MAX_SIMPLE_HYPHENS,
    MAX_UNDERSCORES_PENALTY,
)


@dataclass
class EntryPointCandidate:
    """
    Represents a candidate instance file with its score.
    
    Attributes:
        path: Path to the file
        score: Calculated score (higher = more likely to be main instance)
        reasons: list of scoring reasons for debugging
    """
    path: Path
    score: int
    reasons: list[str]
    
    def __repr__(self) -> str:
        return f"EntryPointCandidate({self.path.name}, score={self.score})"


class EntryPointDetector:
    """
    Detects the main instance document in XBRL filing packages.
    
    Uses a universal scoring algorithm that works for any market/format.
    """
    
    def __init__(self):
        """Initialize detector."""
        self.logger = logging.getLogger(__name__)
    
    def detect(self, files: list[Path]) -> Optional[Path]:
        """
        Detect main instance file from list of files.
        
        Args:
            files: list of file paths in the filing package
            
        Returns:
            Path to main instance file, or None if not found
            
        Example:
            detector = EntryPointDetector()
            files = list(Path('/filing/').glob('**/*'))
            instance = detector.detect(files)
        """
        if not files:
            self.logger.warning("No files provided for entry point detection")
            return None
        
        # Step 1: Filter out known non-instance files
        candidates = self._filter_non_instances(files)
        
        if not candidates:
            self.logger.warning(f"No candidates after filtering {len(files)} files")
            return None
        
        self.logger.debug(f"Entry point candidates: {len(candidates)} from {len(files)} total")
        
        # Step 2: Score all candidates
        scored_candidates = [self._score_candidate(f) for f in candidates]
        
        # Step 3: Sort by score (highest first)
        scored_candidates.sort(key=lambda x: x.score, reverse=True)
        
        # Step 4: Log top candidates for debugging
        self._log_top_candidates(scored_candidates)
        
        # Step 5: Return best candidate
        if scored_candidates:
            best = scored_candidates[0]
            self.logger.info(f"Selected entry point: {best.path.name} (score: {best.score})")
            return best.path
        
        return None
    
    def _filter_non_instances(self, files: list[Path]) -> list[Path]:
        """
        Filter out files that are definitely NOT instance documents.
        
        Removes:
        - Linkbase files (_def.xml, _cal.xml, etc.)
        - Schema files (.xsd)
        - Exhibit files (multiple patterns)
        - Images and non-XBRL files
        
        Args:
            files: All files in package
            
        Returns:
            Filtered list of potential instance files
        """
        candidates = []
        
        for f in files:
            if self._should_exclude(f):
                continue
            candidates.append(f)
        
        return candidates
    
    def _should_exclude(self, path: Path) -> bool:
        """
        Check if file should be excluded from consideration.
        
        Args:
            path: File path to check
            
        Returns:
            True if file should be excluded, False otherwise
        """
        name = path.name.lower()
        stem = path.stem.lower()
        
        # EXCLUDE: Linkbase files
        if any(stem.endswith(suffix) for suffix in LINKBASE_SUFFIXES):
            return True
        
        # EXCLUDE: Schema files
        if path.suffix.lower() == '.xsd':
            return True
        
        # EXCLUDE: Exhibits - use constants
        for pattern in EXHIBIT_PATTERNS:
            if re.search(pattern, name):
                return True
        
        # EXCLUDE: Images and other non-XBRL files
        if path.suffix.lower() in NON_XBRL_EXTENSIONS:
            return True
        
        # EXCLUDE: Common non-instance filenames
        if any(excluded in stem for excluded in EXCLUDED_FILENAMES):
            return True
        
        return False
    
    def _score_candidate(self, path: Path) -> EntryPointCandidate:
        """
        Score a candidate file as potential instance document.
        
        Uses multiple positive indicators to calculate likelihood.
        Higher score = more likely to be main instance.
        
        Args:
            path: Path to candidate file
            
        Returns:
            EntryPointCandidate with score and reasoning
        """
        name = path.name.lower()
        stem = path.stem.lower()
        score = 0
        reasons = []
        
        # INDICATOR: File in 'extracted' directory
        if 'extracted' in str(path).lower():
            score += SCORE_EXTRACTED_DIR
            reasons.append("in extracted/ directory")
        
        # INDICATOR: iXBRL format
        if path.suffix.lower() in ['.htm', '.html', '.xhtml']:
            score += SCORE_IXBRL_FORMAT
            reasons.append("iXBRL format")
        
        # INDICATOR: Has date pattern YYYYMMDD
        # Examples: aci-20250222.htm, aapl-20250927.htm
        if re.search(r'\d{8}', stem):
            score += SCORE_DATE_PATTERN
            reasons.append("has YYYYMMDD date pattern")
        
        # INDICATOR: Traditional XML instance pattern
        # Examples: company-20231231-ins.xml, instance.xml
        if path.suffix.lower() == '.xml':
            if stem.endswith('-ins'):
                score += SCORE_XML_INSTANCE
                reasons.append("SEC -ins.xml pattern")
            elif stem == 'instance':
                score += SCORE_XML_INSTANCE
                reasons.append("standard instance.xml")
            else:
                score += SCORE_XML_FORMAT
                reasons.append("XML format")
        
        # INDICATOR: Short filename
        # Main instances tend to be shorter than exhibits
        if len(stem) < MAX_SIMPLE_FILENAME_LENGTH:
            score += SCORE_SHORT_FILENAME
            reasons.append("short filename")
        
        # INDICATOR: Common ticker patterns
        # Examples: aapl-20250927.htm, msft-20231231.xml
        for pattern in TICKER_PATTERNS:
            if re.match(pattern, stem):
                score += SCORE_TICKER_PATTERN
                reasons.append("ticker/standard pattern")
                break
        
        # INDICATOR: No hyphens except for date/ticker
        # Clean filenames are more likely to be main instance
        hyphen_count = stem.count('-')
        if hyphen_count <= MAX_SIMPLE_HYPHENS:
            score += SCORE_SIMPLE_FILENAME
            reasons.append("simple filename")
        
        # INDICATOR: Matches schema base name (CRITICAL - NEW)
        # Main instance shares base name with .xsd file
        # Example: v-20250930.htm matches v-20250930.xsd
        parent_dir = path.parent
        schema_files = list(parent_dir.glob('*.xsd'))
        if schema_files:
            for schema in schema_files:
                schema_base = schema.stem  # e.g., "v-20250930"
                if stem == schema_base:
                    score += SCORE_SCHEMA_MATCH
                    reasons.append("matches schema base name")
                    break
        
        # INDICATOR: Large file size (NEW)
        # Main instances are typically large (1-5MB)
        # Exhibits are small (<100KB)
        try:
            size_kb = path.stat().st_size / 1024
            if size_kb > SIZE_LARGE_THRESHOLD:
                score += SCORE_LARGE_FILE
                reasons.append(f"large file ({size_kb:.0f}KB)")
            elif size_kb > SIZE_MEDIUM_THRESHOLD:
                score += SCORE_MEDIUM_FILE
                reasons.append(f"medium file ({size_kb:.0f}KB)")
            elif size_kb < SIZE_SMALL_PENALTY:
                score += PENALTY_SMALL_FILE
                reasons.append(f"PENALTY: small file ({size_kb:.0f}KB)")
        except OSError:
            pass
        
        # PENALTY: Very long filename
        # Exhibits tend to have descriptive long names
        if len(stem) > MAX_FILENAME_LENGTH:
            score += PENALTY_LONG_FILENAME
            reasons.append("PENALTY: very long filename")
        
        # PENALTY: Contains form type in middle of name
        # Examples: a10-kexhibit (form type "10-k" in middle)
        if re.search(r'\d+-[kq]', stem):
            score += PENALTY_FORM_TYPE
            reasons.append("PENALTY: form type in filename")
        
        # PENALTY: Multiple underscores
        # Exhibits often have descriptive names with underscores
        if stem.count('_') > MAX_UNDERSCORES_PENALTY:
            score += PENALTY_MANY_UNDERSCORES
            reasons.append("PENALTY: many underscores")
        
        return EntryPointCandidate(path=path, score=score, reasons=reasons)
    
    def _log_top_candidates(self, candidates: list[EntryPointCandidate]) -> None:
        """
        Log top candidates for debugging.
        
        Args:
            candidates: Sorted list of candidates (highest score first)
        """
        if not candidates:
            return
        
        self.logger.debug("Top entry point candidates:")
        for i, candidate in enumerate(candidates[:5], 1):
            reasons_str = ", ".join(candidate.reasons)
            self.logger.debug(
                f"  {i}. {candidate.path.name} "
                f"(score: {candidate.score}) - {reasons_str}"
            )
    
    def detect_format(self, entry_point: Path) -> str:
        """
        Detect format of entry point file.
        
        Args:
            entry_point: Path to detected entry point
            
        Returns:
            Format string: 'ixbrl', 'xml', or 'unknown'
        """
        suffix = entry_point.suffix.lower()
        
        if suffix in ['.htm', '.html', '.xhtml']:
            return 'ixbrl'
        elif suffix == '.xml':
            return 'xml'
        else:
            return 'unknown'


# Convenience function for simple usage
def detect_entry_point(files: list[Path]) -> Optional[Path]:
    """
    Detect main instance file from list of files.
    
    Convenience function that creates detector and runs detection.
    
    Args:
        files: list of file paths in filing package
        
    Returns:
        Path to main instance file, or None if not found
        
    Example:
        files = list(Path('/filing/').glob('**/*'))
        instance = detect_entry_point(files)
    """
    detector = EntryPointDetector()
    return detector.detect(files)


__all__ = [
    'EntryPointDetector',
    'EntryPointCandidate',
    'detect_entry_point'
]
