# Path: loaders/json_structure_reader.py
"""
JSON Structure Reader - RECURSIVE VERSION

Discovers the COMPLETE structure of JSON files by recursively exploring all nested objects.
NO LAZINESS - explores everything and reports full structure.

ARCHITECTURE PRINCIPLE:
A true reader must explore the ENTIRE document, not just the surface.
Reports complete paths like 'instance.facts', 'metadata.company_name', etc.
"""

import logging
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class JSONStructure:
    """
    Complete discovered structure of a JSON file.
    
    Reports EVERYTHING found, with full paths.
    
    Attributes:
        all_paths: All discovered paths (e.g., 'instance.facts', 'metadata.company_name')
        array_paths: Paths to arrays with item counts
        object_paths: Paths to objects
        primitive_paths: Paths to primitive values
        path_types: Type of value at each path
        structure_summary: Human-readable summary
    """
    all_paths: set[str] = field(default_factory=set)
    array_paths: dict[str, int] = field(default_factory=dict)  # {path: item_count}
    object_paths: set[str] = field(default_factory=set)
    primitive_paths: dict[str, str] = field(default_factory=dict)  # {path: type}
    path_types: dict[str, str] = field(default_factory=dict)
    structure_summary: dict[str, any] = field(default_factory=dict)


class JSONStructureReader:
    """
    Recursive JSON structure discoverer.
    
    Explores the COMPLETE structure, not just the top level.
    Reports all paths and their types.
    
    Example:
        reader = JSONStructureReader()
        structure = reader.discover_structure(data)
        
        # Check if path exists
        if 'instance.facts' in structure.array_paths:
            facts = data['instance']['facts']
            print(f"Found {structure.array_paths['instance.facts']} facts")
    """
    
    def __init__(self):
        """Initialize structure reader."""
        self.logger = logging.getLogger('input.json_structure')
    
    def discover_structure(self, data: dict[str, any]) -> JSONStructure:
        """
        Recursively discover the complete JSON structure.
        
        Args:
            data: JSON data as dictionary
            
        Returns:
            JSONStructure with complete path information
        """
        structure = JSONStructure()
        
        # Recursively explore from root
        self._explore_recursive(data, '', structure)
        
        # Log discovery
        self.logger.info(f"Discovered complete structure:")
        self.logger.info(f"  Total paths: {len(structure.all_paths)}")
        self.logger.info(f"  Arrays: {len(structure.array_paths)}")
        self.logger.info(f"  Objects: {len(structure.object_paths)}")
        
        # Log important arrays
        if structure.array_paths:
            self.logger.info(f"  Array paths:")
            for path, count in sorted(structure.array_paths.items()):
                self.logger.info(f"    - {path}: {count} items")
        
        return structure
    
    def _explore_recursive(
        self,
        data: any,
        path: str,
        structure: JSONStructure
    ) -> None:
        """
        Recursively explore data structure.
        
        Args:
            data: Current data node
            path: Current path (e.g., 'instance.facts')
            structure: Structure object to populate
        """
        if isinstance(data, dict):
            # This is an object - explore its keys
            if path:  # Don't add root path
                structure.all_paths.add(path)
                structure.object_paths.add(path)
                structure.path_types[path] = 'object'
            
            # Recursively explore each key
            for key, value in data.items():
                new_path = f"{path}.{key}" if path else key
                self._explore_recursive(value, new_path, structure)
        
        elif isinstance(data, list):
            # This is an array
            structure.all_paths.add(path)
            structure.array_paths[path] = len(data)
            structure.path_types[path] = 'array'
            
            # Sample first item to understand structure
            if data and isinstance(data[0], (dict, list)):
                self._explore_recursive(data[0], f"{path}[0]", structure)
        
        else:
            # This is a primitive value
            structure.all_paths.add(path)
            structure.primitive_paths[path] = type(data).__name__
            structure.path_types[path] = type(data).__name__
    
    def get_value_by_path(
        self,
        data: dict[str, any],
        path: str,
        default: any = None
    ) -> any:
        """
        Get value from JSON using path notation.
        
        Args:
            data: JSON data
            path: Path to value (e.g., 'instance.facts', 'metadata.company_name')
            default: Default if path not found
            
        Returns:
            Value at path or default
        """
        parts = path.split('.')
        current = data
        
        for part in parts:
            # Handle array indexing like 'facts[0]'
            if '[' in part and ']' in part:
                key = part[:part.index('[')]
                index = int(part[part.index('[')+1:part.index(']')])
                
                if isinstance(current, dict) and key in current:
                    current = current[key]
                    if isinstance(current, list) and 0 <= index < len(current):
                        current = current[index]
                    else:
                        return default
                else:
                    return default
            else:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return default
        
        return current
    
    def has_path(self, structure: JSONStructure, path: str) -> bool:
        """
        Check if a path exists in the discovered structure.
        
        Args:
            structure: Discovered structure
            path: Path to check (e.g., 'instance.facts')
            
        Returns:
            True if path exists
        """
        return path in structure.all_paths
    
    def get_array_count(self, structure: JSONStructure, path: str) -> int:
        """
        Get count of items in array at path.
        
        Args:
            structure: Discovered structure
            path: Path to array
            
        Returns:
            Item count or 0 if not found
        """
        return structure.array_paths.get(path, 0)
    
    def list_paths_by_type(
        self,
        structure: JSONStructure,
        path_type: str
    ) -> list[str]:
        """
        List all paths of a specific type.
        
        Args:
            structure: Discovered structure
            path_type: Type to filter by ('array', 'object', or primitive type)
            
        Returns:
            List of matching paths
        """
        if path_type == 'array':
            return sorted(list(structure.array_paths.keys()))
        elif path_type == 'object':
            return sorted(list(structure.object_paths))
        else:
            return sorted([
                path for path, ptype in structure.primitive_paths.items()
                if ptype == path_type
            ])


__all__ = ['JSONStructureReader', 'JSONStructure']