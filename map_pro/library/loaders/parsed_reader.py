# Path: library/loaders/parsed_reader.py
"""
Parsed Reader

Reads parsed.json files and extracts taxonomy requirements.
Uses ParsedLoader to find files, then reads content.

Architecture:
- Uses parsed_loader.py to discover files
- Reads JSON content
- Extracts namespace URIs
- Returns required taxonomy information
- Does NOT resolve namespaces to library names (engine's job)
"""

import json
from pathlib import Path
from typing import Set, Dict, Any, List, Optional
from dataclasses import dataclass

from library.core.config_loader import LibraryConfig
from library.core.logger import get_logger
from library.loaders.parsed_loader import ParsedLoader, ParsedFileLocation
from library.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT

logger = get_logger(__name__, 'loaders')


@dataclass
class ParsedFilingInfo:
    """Information extracted from parsed.json file."""
    filing_path: Path
    filing_folder: Path
    namespaces: Set[str]
    namespace_count: int
    success: bool
    error: Optional[str] = None


class ParsedReader:
    """
    Reads parsed.json files and extracts taxonomy requirements.
    
    Uses ParsedLoader for discovery, focuses on content reading.
    """
    
    # Possible paths where namespace declarations might be found
    NAMESPACE_SEARCH_PATHS = [
        'instance.namespaces',
        'namespaces',
        'schema.namespaces',
        'metadata.namespaces',
        'xbrl.namespaces',
        'document.namespaces',
    ]
    
    # Standard namespaces to filter out
    STANDARD_NAMESPACES = {
        'http://www.w3.org/2001/XMLSchema',
        'http://www.w3.org/2001/XMLSchema-instance',
        'http://www.xbrl.org/2003/instance',
        'http://www.xbrl.org/2003/linkbase',
        'http://www.xbrl.org/2003/XLink',
        'http://www.xbrl.org/2006/xbrldi',
        'http://www.w3.org/1999/xlink',
        'http://www.w3.org/1999/xhtml',
        'http://www.w3.org/XML/1998/namespace',
    }
    
    def __init__(self, config: Optional[LibraryConfig] = None):
        """Initialize parsed reader."""
        self.config = config if config else LibraryConfig()
        self.loader = ParsedLoader(self.config)
        
        logger.info(f"{LOG_INPUT} ParsedReader initialized")
    
    def read_all(self) -> List[ParsedFilingInfo]:
        """
        Read all parsed.json files and extract namespaces.
        
        Returns:
            List of ParsedFilingInfo objects
        """
        logger.info(f"{LOG_PROCESS} Reading all parsed.json files")
        
        # Discover files
        locations = self.loader.discover_all()
        
        # Read each file
        results = []
        for location in locations:
            info = self.read_file(location.parsed_json_path)
            results.append(info)
        
        success_count = sum(1 for r in results if r.success)
        logger.info(f"{LOG_OUTPUT} Read {success_count}/{len(results)} files successfully")
        
        return results
    
    def read_file(self, json_path: Path) -> ParsedFilingInfo:
        """
        Read single parsed.json file and extract namespaces.
        
        Args:
            json_path: Path to parsed.json file
            
        Returns:
            ParsedFilingInfo object
        """
        logger.debug(f"{LOG_INPUT} Reading: {json_path}")
        
        try:
            # Load JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract namespaces
            namespaces = self._extract_namespaces(data)
            
            # Filter standard namespaces
            taxonomy_namespaces = self._filter_standard_namespaces(namespaces)
            
            logger.debug(f"{LOG_OUTPUT} Extracted {len(taxonomy_namespaces)} taxonomy namespaces")
            
            return ParsedFilingInfo(
                filing_path=json_path,
                filing_folder=json_path.parent,
                namespaces=taxonomy_namespaces,
                namespace_count=len(taxonomy_namespaces),
                success=True,
                error=None
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {json_path}: {e}")
            return ParsedFilingInfo(
                filing_path=json_path,
                filing_folder=json_path.parent,
                namespaces=set(),
                namespace_count=0,
                success=False,
                error=f"Invalid JSON: {e}"
            )
        except Exception as e:
            logger.error(f"Error reading {json_path}: {e}")
            return ParsedFilingInfo(
                filing_path=json_path,
                filing_folder=json_path.parent,
                namespaces=set(),
                namespace_count=0,
                success=False,
                error=str(e)
            )
    
    def _extract_namespaces(self, data: Dict[str, Any]) -> Set[str]:
        """
        Extract namespace URIs from parsed data.
        
        Searches multiple possible locations.
        
        Args:
            data: Parsed JSON data
            
        Returns:
            Set of namespace URIs
        """
        namespace_uris = set()
        
        # Try configured search paths
        for search_path in self.NAMESPACE_SEARCH_PATHS:
            ns_dict = self._get_value_by_path(data, search_path)
            
            if ns_dict and isinstance(ns_dict, dict):
                for prefix, uri in ns_dict.items():
                    if uri and isinstance(uri, str):
                        namespace_uris.add(uri)
        
        # If no namespaces found, do deep search
        if not namespace_uris:
            namespace_uris = self._deep_search_namespaces(data)
        
        return namespace_uris
    
    def _get_value_by_path(
        self,
        data: Dict[str, Any],
        path: str
    ) -> Optional[Any]:
        """
        Get value from nested dict using dot notation path.
        
        Args:
            data: Source dictionary
            path: Dot-separated path (e.g., 'instance.namespaces')
            
        Returns:
            Value at path or None
        """
        parts = path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def _deep_search_namespaces(self, data: Any) -> Set[str]:
        """
        Deep recursive search for namespace declarations.
        
        Args:
            data: Any JSON data structure
            
        Returns:
            Set of namespace URIs
        """
        namespace_uris = set()
        
        if isinstance(data, dict):
            # Check if this dict looks like a namespace map
            if self._is_namespace_map(data):
                for uri in data.values():
                    if uri and isinstance(uri, str):
                        namespace_uris.add(uri)
            
            # Recursively search nested dicts
            for value in data.values():
                namespace_uris.update(self._deep_search_namespaces(value))
        
        elif isinstance(data, list):
            for item in data:
                namespace_uris.update(self._deep_search_namespaces(item))
        
        return namespace_uris
    
    def _is_namespace_map(self, data: dict) -> bool:
        """
        Check if a dictionary looks like a namespace map.
        
        Args:
            data: Dictionary to check
            
        Returns:
            True if looks like namespace map
        """
        if not isinstance(data, dict) or len(data) == 0:
            return False
        
        # Check if most values are HTTP URIs
        uri_count = 0
        for value in data.values():
            if isinstance(value, str) and (
                value.startswith('http://') or value.startswith('https://')
            ):
                uri_count += 1
        
        return (uri_count / len(data)) > 0.5
    
    def _filter_standard_namespaces(self, namespaces: Set[str]) -> Set[str]:
        """
        Filter out standard XML/XBRL namespaces.
        
        Args:
            namespaces: Set of namespace URIs
            
        Returns:
            Set containing only taxonomy namespaces
        """
        return {
            ns for ns in namespaces
            if ns not in self.STANDARD_NAMESPACES
        }


__all__ = ['ParsedReader', 'ParsedFilingInfo']