# Path: loaders/filing_analyzer.py
"""
Filing Analyzer

Helper class for analyzing XBRL filing characteristics.
Extracted from parser_output.py to keep that file focused on deserialization.

This analyzer:
- Detects taxonomies from namespace URIs
- Identifies company extensions
- Analyzes filing structure (facts, contexts, units, dimensions)
"""

import logging
from typing import Optional

from ..loaders.json_structure_reader import JSONStructureReader
from ..loaders.constants import (
    TAXONOMY_RECOGNITION_PATTERNS,
    STANDARD_XBRL_URI_PATTERNS,
    FACT_CONTAINER_PATTERNS,
    CONTEXT_CONTAINER_PATTERNS,
    UNIT_CONTAINER_PATTERNS,
)


class FilingAnalyzer:
    """Analyzes XBRL filing structure and characteristics."""
    
    def __init__(self, structure_reader: JSONStructureReader):
        """
        Initialize analyzer.
        
        Args:
            structure_reader: JSONStructureReader instance for accessing data
        """
        self.structure_reader = structure_reader
        self.logger = logging.getLogger('input.filing_analyzer')
    
    def extract_characteristics(
        self,
        data: dict[str, any],
        structure: any,
        namespace_map: dict[str, str]
    ) -> 'FilingCharacteristics':
        """
        Extract filing characteristics using namespace map.
        
        Args:
            data: Raw JSON data
            structure: Discovered structure
            namespace_map: Prefix â†’ URI mapping
            
        Returns:
            FilingCharacteristics object
        """
        from ..loaders.parser_output import FilingCharacteristics
        
        chars = FilingCharacteristics()
        
        # Extract from metadata
        metadata = self.structure_reader.get_value_by_path(data, 'metadata', {})
        
        if metadata:
            chars.filing_type = metadata.get('document_type', 'UNKNOWN')
            chars.market = metadata.get('market', 'unknown')
            chars.parsing_errors = metadata.get('parsing_errors', [])
            chars.validation_warnings = metadata.get('validation_warnings', [])
        
        # Find facts
        facts_path = self._find_facts_path(structure)
        if facts_path:
            chars.fact_count = structure.array_paths.get(facts_path, 0)
            facts = self.structure_reader.get_value_by_path(data, facts_path, [])
            
            if facts:
                # Detect taxonomy using namespace map
                chars.primary_taxonomy = self._detect_taxonomy_from_facts(facts, namespace_map)
                chars.company_extensions = self._detect_extensions_from_facts(facts, namespace_map)
        
        # Find contexts
        contexts_path = self._find_contexts_path(structure)
        if contexts_path:
            contexts = self.structure_reader.get_value_by_path(data, contexts_path)
            
            if isinstance(contexts, dict):
                chars.context_count = len(contexts)
                chars.has_dimensions = self._check_for_dimensions_in_dict(contexts)
            elif isinstance(contexts, list):
                chars.context_count = len(contexts)
                chars.has_dimensions = self._check_for_dimensions_in_list(contexts)
        
        # Find units
        units_path = self._find_units_path(structure)
        if units_path:
            units = self.structure_reader.get_value_by_path(data, units_path)
            if isinstance(units, (dict, list)):
                chars.unit_count = len(units)
        
        # Find footnotes
        footnotes_path = self._find_footnotes_path(structure)
        if footnotes_path:
            chars.has_footnotes = True
        
        return chars
    
    def extract_extensions(
        self,
        data: dict[str, any],
        structure: any,
        namespace_map: dict[str, str]
    ) -> list[dict[str, any]]:
        """
        Extract company extension facts using patterns from constants.
        
        Args:
            data: Raw JSON data
            structure: Discovered structure
            namespace_map: Prefix â†’ URI mapping
            
        Returns:
            List of extension fact dictionaries
        """
        facts_path = self._find_facts_path(structure)
        if not facts_path:
            return []
        
        facts = self.structure_reader.get_value_by_path(data, facts_path, [])
        
        extensions = []
        for fact in facts:
            concept = fact.get('concept', '')
            if ':' in concept:
                prefix = concept.split(':')[0]
                
                if prefix in namespace_map:
                    uri = namespace_map[prefix]
                    uri_lower = uri.lower()
                    
                    # Check if it's a standard XBRL namespace
                    is_standard_xbrl = any(
                        pattern in uri_lower 
                        for pattern in STANDARD_XBRL_URI_PATTERNS
                    )
                    
                    # Check if it's a known taxonomy
                    is_taxonomy = any(
                        any(pattern in uri_lower for pattern in patterns)
                        for patterns in TAXONOMY_RECOGNITION_PATTERNS.values()
                    )
                    
                    if not is_standard_xbrl and not is_taxonomy:
                        extensions.append(fact)
        
        return extensions
    
    def _find_facts_path(self, structure: any) -> Optional[str]:
        """Find where facts array is located using patterns from constants."""
        # Check configured patterns first
        for path in FACT_CONTAINER_PATTERNS:
            if path in structure.array_paths:
                return path
        
        # Fallback: search for any path containing 'facts'
        for path in structure.array_paths:
            if 'facts' in path.lower():
                return path
        
        return None
    
    def _find_contexts_path(self, structure: any) -> Optional[str]:
        """Find where contexts are located using patterns from constants."""
        # Check configured patterns first
        for path in CONTEXT_CONTAINER_PATTERNS:
            if path in structure.all_paths:
                return path
        
        # Fallback: search for any path containing 'context'
        for path in structure.all_paths:
            if 'context' in path.lower():
                return path
        
        return None
    
    def _find_units_path(self, structure: any) -> Optional[str]:
        """Find where units are located using patterns from constants."""
        # Check configured patterns first
        for path in UNIT_CONTAINER_PATTERNS:
            if path in structure.all_paths:
                return path
        
        # Fallback: search for any path containing 'unit'
        for path in structure.all_paths:
            if 'unit' in path.lower():
                return path
        
        return None
    
    def _find_footnotes_path(self, structure: any) -> Optional[str]:
        """Find where footnotes are located."""
        possible_paths = [
            'instance.footnotes',
            'footnotes',
            'data.footnotes'
        ]
        
        for path in possible_paths:
            if path in structure.all_paths:
                return path
        
        return None
    
    def _detect_taxonomy_from_facts(
        self,
        facts: list[dict[str, any]],
        namespace_map: dict[str, str]
    ) -> str:
        """
        Detect primary taxonomy using namespace map - NO HARDCODING.
        
        Process:
        1. Count prefix usage in facts (e.g., ns0 appears 1000 times)
        2. Look up prefix in namespace map (ns0 â†’ http://fasb.org/us-gaap/2024)
        3. Identify taxonomy from URI (us-gaap)
        """
        if not facts:
            return "unknown"
        
        # Count prefix usage
        prefix_counts = {}
        for fact in facts[:100]:
            concept = fact.get('concept', '')
            
            if ':' in concept:
                prefix = concept.split(':')[0]
                prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
        
        if not prefix_counts:
            return "unknown"
        
        # Get most common prefix
        most_common_prefix = max(prefix_counts, key=prefix_counts.get)
        
        # Look up prefix in namespace map
        if most_common_prefix in namespace_map:
            uri = namespace_map[most_common_prefix]
            
            # Detect taxonomy from URI
            taxonomy = self._identify_taxonomy_from_uri(uri)
            self.logger.debug(f"Resolved {most_common_prefix} â†’ {uri} â†’ {taxonomy}")
            return taxonomy
        else:
            # Prefix not in namespace map - return as-is
            self.logger.warning(f"Prefix '{most_common_prefix}' not found in namespace map")
            return most_common_prefix
    
    def _identify_taxonomy_from_uri(self, uri: str) -> str:
        """
        Identify taxonomy name from namespace URI using recognition patterns.
        
        FALLBACK HEURISTIC - patterns used for friendly naming only.
        Primary source should be schemaRef elements from filing.
        """
        uri_lower = uri.lower()
        
        # Check each taxonomy pattern from constants (fallback only)
        for taxonomy_name, patterns in TAXONOMY_RECOGNITION_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in uri_lower:
                    # Return the taxonomy name (without underscores)
                    return taxonomy_name.replace('_', '-')
        
        # Unknown taxonomy - return URI as identifier
        # Extract meaningful part of URI
        parts = uri.rstrip('/').split('/')
        return parts[-1] if parts else 'unknown'
    
    def _detect_extensions_from_facts(
        self,
        facts: list[dict[str, any]],
        namespace_map: dict[str, str]
    ) -> list[str]:
        """
        Detect company extensions using namespace map and standard patterns from constants.
        """
        extension_prefixes = set()
        
        for fact in facts:
            concept = fact.get('concept', '')
            if ':' in concept:
                prefix = concept.split(':')[0]
                
                # Look up prefix in namespace map
                if prefix in namespace_map:
                    uri = namespace_map[prefix]
                    uri_lower = uri.lower()
                    
                    # Check if it's a standard XBRL namespace
                    is_standard_xbrl = any(
                        pattern in uri_lower 
                        for pattern in STANDARD_XBRL_URI_PATTERNS
                    )
                    
                    # Check if it's a known taxonomy
                    is_taxonomy = any(
                        any(pattern in uri_lower for pattern in patterns)
                        for patterns in TAXONOMY_RECOGNITION_PATTERNS.values()
                    )
                    
                    if not is_standard_xbrl and not is_taxonomy:
                        extension_prefixes.add(prefix)
        
        return sorted(list(extension_prefixes))
    
    def _check_for_dimensions_in_dict(self, contexts: dict[str, any]) -> bool:
        """Check if context dict has dimensions."""
        for context in list(contexts.values())[:50]:
            if isinstance(context, dict) and context.get('dimensions'):
                return True
        return False
    
    def _check_for_dimensions_in_list(self, contexts: list[dict[str, any]]) -> bool:
        """Check if context list has dimensions."""
        for context in contexts[:50]:
            if isinstance(context, dict) and context.get('dimensions'):
                return True
        return False


__all__ = ['FilingAnalyzer']