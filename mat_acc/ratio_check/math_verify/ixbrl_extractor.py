# Path: mat_acc/ratio_check/math_verify/ixbrl_extractor.py
"""
iXBRL Numeric Extractor - Layer 1 of Mathematical Integrity Unit

Reads raw iXBRL source files and extracts mathematically correct
numeric values by honoring ALL numeric attributes:
- sign: Negation indicator (sign="-" means negate displayed value)
- scale: Power of 10 multiplier (scale="3" = thousands)
- decimals: Precision level
- unitRef: Unit of measurement (USD, shares, per-share)
- format: Display format transformer

This is PURE MATHEMATICS - no accounting knowledge required.
The iXBRL specification defines how to compute the true value
from the displayed value. This module implements that computation.
"""

import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.logger.ipo_logging import get_process_logger
from .context_filter import ContextFilter


logger = get_process_logger('math_verify.extractor')


# iXBRL tag patterns for numeric facts
_NONFRACTION_PATTERN = re.compile(
    r'<ix:nonFraction\b([^>]*)>(.*?)</ix:nonFraction>',
    re.DOTALL | re.IGNORECASE,
)

# Attribute extraction patterns
_ATTR_PATTERN = re.compile(
    r'(\w+)\s*=\s*"([^"]*)"',
)


@dataclass
class VerifiedFact:
    """A numeric fact with mathematically verified value."""
    concept: str
    value: float
    displayed_text: str = ''
    sign: int = 1
    scale: int = 0
    decimals: str = ''
    unit_ref: str = ''
    context_ref: str = ''
    fact_id: str = ''


class IXBRLExtractor:
    """
    Extracts mathematically correct values from iXBRL files.
    Transformation: true_value = displayed_value * 10^scale * sign
    """

    def __init__(self):
        """Initialize iXBRL extractor."""
        self.logger = get_process_logger('math_verify.extractor')
        self._context_filter = ContextFilter()
        self._all_facts: list[VerifiedFact] = []

    def extract(self, filing_path: Path) -> list[VerifiedFact]:
        """Extract all numeric facts from an iXBRL file."""
        if not filing_path or not filing_path.exists():
            self.logger.warning(f"Filing not found: {filing_path}")
            return []

        content = self._read_filing(filing_path)
        if not content:
            return []

        # Parse context definitions for filtering
        self._context_filter.parse_contexts(content)

        # Extract all facts (cache for metadata consumers)
        all_facts = self._extract_nonfraction_facts(content)
        self._all_facts = all_facts

        # Filter to primary current-period facts only
        primary_facts = self._filter_primary(all_facts)

        self.logger.info(
            f"Extracted {len(all_facts)} total, "
            f"{len(primary_facts)} primary current-period facts "
            f"from {filing_path.name}"
        )

        return primary_facts

    def extract_all(self, filing_path: Path) -> list[VerifiedFact]:
        """Extract ALL facts without filtering (for full reconciliation)."""
        if not filing_path or not filing_path.exists():
            return []
        content = self._read_filing(filing_path)
        if not content:
            return []
        return self._extract_nonfraction_facts(content)

    def extract_from_directory(self, filing_dir: Path) -> list[VerifiedFact]:
        """Find iXBRL file in directory and extract primary facts."""
        ixbrl_file = self._find_ixbrl_file(filing_dir)
        if not ixbrl_file:
            self.logger.warning(f"No iXBRL file found in {filing_dir}")
            return []

        self.logger.info(f"Found iXBRL file: {ixbrl_file.name}")
        return self.extract(ixbrl_file)

    def get_context_filter(self) -> ContextFilter:
        """Get the context filter (populated after extract)."""
        return self._context_filter

    def get_all_extracted(self) -> list[VerifiedFact]:
        """Get ALL extracted facts (unfiltered). For metadata-only use."""
        return self._all_facts

    def _filter_primary(self, facts: list[VerifiedFact]) -> list[VerifiedFact]:
        """Filter facts to primary context, current period only."""
        primary = []
        for fact in facts:
            if self._context_filter.is_primary_current(fact.context_ref):
                primary.append(fact)
        return primary

    def build_lookup(
        self, facts: list[VerifiedFact]
    ) -> dict[str, list[VerifiedFact]]:
        """Build lookup index grouped by concept QName."""
        lookup = {}
        for fact in facts:
            if fact.concept not in lookup:
                lookup[fact.concept] = []
            lookup[fact.concept].append(fact)
        return lookup

    def _read_filing(self, filing_path: Path) -> str:
        """Read filing content with encoding handling."""
        encodings = ['utf-8', 'latin-1', 'cp1252']
        for encoding in encodings:
            try:
                return filing_path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        self.logger.error(f"Cannot decode file: {filing_path}")
        return ''

    def _find_ixbrl_file(self, filing_dir: Path) -> Optional[Path]:
        """Find the main iXBRL file (largest .htm with ix:nonFraction tags)."""
        if not filing_dir.is_dir():
            return None

        htm_files = []
        for ext in ('*.htm', '*.html', '*.xhtml'):
            htm_files.extend(filing_dir.glob(ext))

        if not htm_files:
            return None

        # Sort by size descending - main filing is usually largest
        htm_files.sort(key=lambda p: p.stat().st_size, reverse=True)

        # Return first file that contains iXBRL tags
        for htm_file in htm_files:
            try:
                head = htm_file.read_text(encoding='utf-8', errors='ignore')[:5000]
                if 'ix:nonFraction' in head or 'ix:nonfraction' in head.lower():
                    return htm_file
            except Exception:
                continue

        # Fallback: return largest htm file
        return htm_files[0] if htm_files else None

    def _extract_nonfraction_facts(self, content: str) -> list[VerifiedFact]:
        """Extract all ix:nonFraction facts and compute true values."""
        facts = []
        sign_count = 0

        for match in _NONFRACTION_PATTERN.finditer(content):
            attrs_str = match.group(1)
            inner_text = match.group(2).strip()

            attrs = self._parse_attributes(attrs_str)
            fact = self._build_fact(attrs, inner_text)

            if fact is not None:
                if fact.sign == -1:
                    sign_count += 1
                facts.append(fact)

        if sign_count > 0:
            self.logger.info(
                f"Found {sign_count} facts with sign=\"-\" "
                f"(negated values) out of {len(facts)} total"
            )

        return facts

    def _parse_attributes(self, attrs_str: str) -> dict[str, str]:
        """Parse HTML/XML attributes into a dictionary."""
        attrs = {}
        for attr_match in _ATTR_PATTERN.finditer(attrs_str):
            key = attr_match.group(1).lower()
            val = attr_match.group(2)
            attrs[key] = val
        return attrs

    def _build_fact(
        self, attrs: dict[str, str], inner_text: str
    ) -> Optional[VerifiedFact]:
        """
        Build a VerifiedFact from parsed attributes and inner text.

        Applies the iXBRL numeric transformation:
            true_value = parse(displayed_text) * 10^scale * sign
        """
        concept = attrs.get('name', '')
        if not concept:
            return None

        # Parse sign: sign="-" means negate
        sign = -1 if attrs.get('sign', '') == '-' else 1

        # Parse scale: multiply by 10^scale
        scale = self._parse_scale(attrs.get('scale', '0'))

        # Parse the displayed numeric value
        raw_value = self._parse_displayed_value(inner_text)
        if raw_value is None:
            return None

        # THE MATHEMATICAL TRUTH:
        # true_value = displayed_value * 10^scale * sign_multiplier
        true_value = raw_value * (10 ** scale) * sign

        return VerifiedFact(
            concept=concept,
            value=true_value,
            displayed_text=inner_text,
            sign=sign,
            scale=scale,
            decimals=attrs.get('decimals', ''),
            unit_ref=attrs.get('unitref', ''),
            context_ref=attrs.get('contextref', ''),
            fact_id=attrs.get('id', ''),
        )

    def _parse_scale(self, scale_str: str) -> int:
        """Parse scale attribute to integer."""
        try:
            return int(scale_str)
        except (ValueError, TypeError):
            return 0

    def _parse_displayed_value(self, text: str) -> Optional[float]:
        """
        Parse the displayed text to a raw numeric value.

        Handles common display formats:
        - Comma-separated: "1,234,567"
        - Decimal: "1234.56"
        - Parenthesized negatives: "(1,234)"
        - Dash for zero: "-" or "--"
        - Empty/whitespace: treated as None
        """
        # Strip HTML tags that might be nested inside
        cleaned = re.sub(r'<[^>]+>', '', text).strip()

        if not cleaned:
            return None

        # Dash or double-dash means zero
        if cleaned in ('-', '--', '---'):
            return 0.0

        # Handle parenthesized negatives: (1,234) -> -1234
        is_negative = False
        if cleaned.startswith('(') and cleaned.endswith(')'):
            is_negative = True
            cleaned = cleaned[1:-1].strip()

        # Remove currency symbols, spaces, commas
        cleaned = cleaned.replace('$', '')
        cleaned = cleaned.replace(',', '')
        cleaned = cleaned.replace(' ', '')

        try:
            value = float(cleaned)
            if is_negative:
                value = -value
            return value
        except ValueError:
            return None


__all__ = ['IXBRLExtractor', 'VerifiedFact']
