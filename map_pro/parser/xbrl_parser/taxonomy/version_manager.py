# Path: xbrl_parser/taxonomy/version_manager.py
"""
Version Manager

Handles taxonomy versioning and compatibility.

Features:
- Version detection from namespace URIs
- Version compatibility checking
- Migration path identification
- Deprecation tracking

Example:
    from ..taxonomy import VersionManager
    
    manager = VersionManager()
    version = manager.extract_version("http://fasb.org/us-gaap/2023")
"""

import logging
import re
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from ..taxonomy.constants import TAXONOMY_DETECTION_PATTERNS


class TaxonomyFamily(Enum):
    """Standard taxonomy families."""
    US_GAAP = "US-GAAP"
    IFRS = "IFRS"
    UK_GAAP = "UK-GAAP"
    ESEF = "ESEF"
    DEI = "DEI"
    CUSTOM = "CUSTOM"


@dataclass
class TaxonomyVersion:
    """
    Taxonomy version information.
    
    Extracted from namespace URI or taxonomy metadata.
    """
    family: TaxonomyFamily
    year: Optional[int] = None
    month: Optional[int] = None
    version: Optional[str] = None
    namespace: Optional[str] = None
    is_deprecated: bool = False


@dataclass
class VersionCompatibility:
    """
    Version compatibility assessment.
    
    Indicates whether two taxonomy versions are compatible.
    """
    compatible: bool
    source_version: TaxonomyVersion
    target_version: TaxonomyVersion
    issues: list[str]
    migration_required: bool = False


class VersionManager:
    """
    Manages taxonomy versions and compatibility.
    
    Extracts version information from namespaces and assesses compatibility.
    
    Example:
        manager = VersionManager()
        
        version = manager.extract_version("http://fasb.org/us-gaap/2023")
        print(f"Family: {version.family}, Year: {version.year}")
        
        compat = manager.check_compatibility(version1, version2)
        if not compat.compatible:
            print(f"Issues: {compat.issues}")
    """
    
    # Version patterns for common taxonomies
    VERSION_PATTERNS = {
        TaxonomyFamily.US_GAAP: [
            r'us-gaap/(\d{4})',
            r'us-gaap-(\d{4})',
        ],
        TaxonomyFamily.IFRS: [
            r'taxonomy/(\d{4})',                    # Matches taxonomy/2023
            r'ifrs/(\d{4})-(\d{2})-(\d{2})',       # Matches ifrs/2023-03-15
            r'ifrs-(\d{4})',                        # Matches ifrs-2023
            r'ifrs.*?/(\d{4})',                     # Matches any ifrs.*/2023
        ],
        TaxonomyFamily.DEI: [
            r'dei/(\d{4})',
            r'dei-(\d{4})',
        ],
    }
    
    def __init__(self):
        """Initialize version manager."""
        self.logger = logging.getLogger(__name__)
    
    def extract_version(self, namespace: str) -> TaxonomyVersion:
        """
        Extract version information from namespace URI.
        
        Args:
            namespace: Namespace URI
            
        Returns:
            TaxonomyVersion object
            
        Example:
            version = manager.extract_version("http://fasb.org/us-gaap/2023")
            assert version.year == 2023
            assert version.family == TaxonomyFamily.US_GAAP
        """
        self.logger.debug(f"Extracting version from namespace: {namespace}")
        
        # Detect taxonomy family
        family = self._detect_family(namespace)
        
        # Extract version using patterns
        year, month, version_str = self._extract_version_components(namespace, family)
        
        return TaxonomyVersion(
            family=family,
            year=year,
            month=month,
            version=version_str,
            namespace=namespace
        )
    
    def check_compatibility(
        self,
        source: TaxonomyVersion,
        target: TaxonomyVersion
    ) -> VersionCompatibility:
        """
        Check compatibility between two taxonomy versions.
        
        Args:
            source: Source taxonomy version
            target: Target taxonomy version
            
        Returns:
            VersionCompatibility assessment
            
        Example:
            compat = manager.check_compatibility(version_2022, version_2023)
            if compat.migration_required:
                print("Migration needed!")
        """
        issues = []
        
        # Must be same family
        if source.family != target.family:
            issues.append(f"Different taxonomy families: {source.family} vs {target.family}")
            return VersionCompatibility(
                compatible=False,
                source_version=source,
                target_version=target,
                issues=issues,
                migration_required=True
            )
        
        # Check year difference
        if source.year and target.year:
            year_diff = abs(target.year - source.year)
            
            # Compatible within 2 years
            if year_diff <= 2:
                compatible = True
                migration_required = False
            else:
                compatible = False
                migration_required = True
                issues.append(f"Year difference too large: {year_diff} years")
        else:
            # Unknown years - assume compatible
            compatible = True
            migration_required = False
        
        return VersionCompatibility(
            compatible=compatible,
            source_version=source,
            target_version=target,
            issues=issues,
            migration_required=migration_required
        )
    
    def _detect_family(self, namespace: str) -> TaxonomyFamily:

        namespace_lower = namespace.lower()
        
        # Check each taxonomy family's patterns
        for family_name, patterns in TAXONOMY_DETECTION_PATTERNS.items():
            # Check if any pattern matches the namespace
            for pattern in patterns:
                if pattern.lower() in namespace_lower:
                    # Return the matching TaxonomyFamily enum
                    try:
                        return TaxonomyFamily[family_name]
                    except KeyError:
                        # Pattern exists in constants but not in enum
                        self.logger.warning(
                            f"Pattern '{family_name}' found in TAXONOMY_DETECTION_PATTERNS "
                            f"but not in TaxonomyFamily enum"
                        )
                        continue
        
        # No match found - return CUSTOM
        return TaxonomyFamily.CUSTOM
    
    def _extract_version_components(
        self,
        namespace: str,
        family: TaxonomyFamily
    ) -> tuple:
        """
        Extract version components from namespace.
        
        Args:
            namespace: Namespace URI
            family: Detected taxonomy family
            
        Returns:
            tuple of (year, month, version_string)
        """
        year = None
        month = None
        version_str = None
        
        # Try patterns for this family
        patterns = self.VERSION_PATTERNS.get(family, [])
        
        for pattern in patterns:
            match = re.search(pattern, namespace)
            if match:
                groups = match.groups()
                
                # Extract year (first group)
                if len(groups) >= 1:
                    try:
                        year = int(groups[0])
                    except ValueError:
                        pass
                
                # Extract month (second group if exists)
                if len(groups) >= 2:
                    try:
                        month = int(groups[1])
                    except ValueError:
                        pass
                
                # Build version string
                version_str = '-'.join(groups)
                break
        
        return year, month, version_str


__all__ = ['VersionManager', 'TaxonomyVersion', 'TaxonomyFamily', 'VersionCompatibility']
