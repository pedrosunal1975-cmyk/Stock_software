# Path: verification/engine/checks_v2/tools/sign/sign_parser.py
"""
Sign Parser for iXBRL Documents

Parses sign="-" attributes from iXBRL instance documents.

In iXBRL, negative values are often displayed as positive text with a
sign="-" attribute on the ix:nonFraction element. This parser extracts
these attributes for use in sign correction during verification.
"""

import logging
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from .sign_info import SignInfo
from ...constants.enums import SignSource


@dataclass
class SignParser:
    """
    Parse sign attributes from iXBRL documents.

    Handles various iXBRL namespace prefixes and attribute orderings.
    Stores parsed corrections for later lookup.

    Usage:
        parser = SignParser()
        count = parser.parse_document('/path/to/instance.htm')

        # Get all parsed corrections
        corrections = parser.get_corrections()

        # Check specific correction
        info = parser.get_correction('us-gaap:NetIncome', 'c-1')
    """

    # Parsed sign corrections: (concept, context_id) -> SignInfo
    corrections: dict = field(default_factory=dict)
    # Files that have been parsed
    parsed_files: set = field(default_factory=set)
    # Diagnostic messages
    diagnostics: list = field(default_factory=list)

    def __post_init__(self):
        """Initialize logger."""
        self.logger = logging.getLogger('tools.sign.sign_parser')

    def parse_document(self, instance_file: str | Path) -> int:
        """
        Parse XBRL instance document to extract sign attributes.

        Handles both inline XBRL (iXBRL) and traditional XBRL formats.

        Args:
            instance_file: Path to XBRL instance document (.htm, .xml)

        Returns:
            Number of sign corrections found
        """
        instance_path = Path(instance_file)
        if not instance_path.exists():
            self.logger.warning(f"Instance file not found: {instance_path}")
            return 0

        if str(instance_path) in self.parsed_files:
            return len([k for k in self.corrections if k[0] == str(instance_path)])

        try:
            with open(instance_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Detect if iXBRL or traditional XBRL
            is_ixbrl = '<ix:' in content or 'xmlns:ix=' in content

            if is_ixbrl:
                count = self._parse_ixbrl(content, instance_path)
            else:
                count = self._parse_traditional_xbrl(content, instance_path)

            self.parsed_files.add(str(instance_path))
            self.logger.info(f"Parsed {instance_path.name}: found {count} sign corrections")

            # Log sample of corrections for debugging
            if count > 0:
                sample_keys = list(self.corrections.keys())[:5]
                self.logger.info(f"Sample sign correction keys: {sample_keys}")

            return count

        except Exception as e:
            self.logger.error(f"Error parsing {instance_path}: {e}")
            return 0

    def _parse_ixbrl(self, content: str, source_file: Path) -> int:
        """
        Parse inline XBRL (iXBRL) document for sign attributes.

        iXBRL uses sign="-" attribute to indicate negative values that are
        displayed as positive text in the document.

        Handles various namespace prefixes and attribute orderings.
        """
        count = 0

        # Patterns for finding nonFraction elements with sign attribute
        # Handle various namespace prefixes: ix:, ixbrl:, iXBRL:
        patterns = [
            # Standard ix: prefix
            re.compile(
                r'<ix:nonFraction\s+([^>]*sign\s*=\s*["\'][+-]["\'][^>]*)>',
                re.IGNORECASE
            ),
            # Alternative prefixes
            re.compile(
                r'<(?:ixbrl|iXBRL):nonFraction\s+([^>]*sign\s*=\s*["\'][+-]["\'][^>]*)>',
                re.IGNORECASE
            ),
        ]

        for pattern in patterns:
            for match in pattern.finditer(content):
                attrs = match.group(1)

                # Extract individual attributes
                sign_match = re.search(r'sign\s*=\s*["\']([+-])["\']', attrs)
                name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', attrs)
                context_match = re.search(r'contextRef\s*=\s*["\']([^"\']+)["\']', attrs)

                if sign_match and name_match and context_match:
                    sign_attr = sign_match.group(1)
                    concept = name_match.group(1)
                    context_id = context_match.group(1)

                    # sign="-" means the value should be negated
                    sign_multiplier = -1 if sign_attr == '-' else 1

                    key = (concept, context_id)
                    if key not in self.corrections:
                        self.corrections[key] = SignInfo(
                            concept=concept,
                            context_id=context_id,
                            sign_multiplier=sign_multiplier,
                            source=SignSource.XBRL_ATTRIBUTE,
                            notes=f"sign='{sign_attr}' in {source_file.name}"
                        )
                        count += 1

        return count

    def _parse_traditional_xbrl(self, content: str, source_file: Path) -> int:
        """
        Parse traditional XBRL document.

        Traditional XBRL doesn't use sign attributes - negative values are
        represented with a minus sign in the value itself.
        """
        # Traditional XBRL typically doesn't need sign correction
        return 0

    def get_correction(
        self,
        concept: str,
        context_id: str
    ) -> Optional[SignInfo]:
        """
        Get sign correction for a specific fact.

        Args:
            concept: XBRL concept name
            context_id: XBRL context reference

        Returns:
            SignInfo if correction exists, None otherwise
        """
        key = (concept, context_id)
        return self.corrections.get(key)

    def get_corrections(self) -> dict:
        """Get all parsed corrections."""
        return self.corrections

    def get_concepts_with_corrections(
        self,
        context_filter: str = None
    ) -> list:
        """
        Get list of concepts that have sign corrections.

        Args:
            context_filter: Optional context ID to filter by

        Returns:
            List of concept names with sign corrections
        """
        if context_filter:
            return [
                info.concept for (_, ctx), info in self.corrections.items()
                if ctx == context_filter and info.sign_multiplier == -1
            ]
        return [
            info.concept for info in self.corrections.values()
            if info.sign_multiplier == -1
        ]

    def clear(self):
        """Clear all parsed data."""
        self.corrections.clear()
        self.parsed_files.clear()
        self.diagnostics.clear()

    def parse_sign_attribute(self, sign_value: str) -> int:
        """
        Parse a sign attribute value to get the multiplier.

        Args:
            sign_value: Sign attribute value ('+', '-', or None)

        Returns:
            Sign multiplier: 1 for positive/None, -1 for negative
        """
        if sign_value == '-':
            return -1
        return 1


__all__ = ['SignParser']
