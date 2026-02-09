# Path: mapping/statement/hierarchy_builder.py
"""
Hierarchy Builder

Builds presentation hierarchy from XBRL linkbase arcs.
Handles locator mapping and depth calculation.
"""

import logging
from typing import Optional
from collections import defaultdict


class HierarchyBuilder:
    """
    Builds presentation hierarchy from XBRL arcs.
    
    Responsibilities:
    - Map locator IDs to concept names
    - Build parent-child relationships
    - Calculate hierarchy depth
    - Track presentation order
    """
    
    def __init__(self):
        """Initialize hierarchy builder."""
        self.logger = logging.getLogger('mapping.hierarchy_builder')
    
    def build_locator_map(
        self,
        arcs: list[any],
        get_attr_func
    ) -> dict[str, str]:
        """
        Build map from locator IDs to concept names.
        
        Args:
            arcs: List of presentation arcs
            get_attr_func: Function to safely get attributes from arcs
            
        Returns:
            Dictionary mapping locator IDs to concept QNames
        """
        locator_map = {}
        
        for arc in arcs:
            # Arc dict keys are 'from'/'to', NOT 'from_concept'/'to_concept'
            from_locator = get_attr_func(arc, 'from_locator')
            from_concept = get_attr_func(arc, 'from')
            to_locator = get_attr_func(arc, 'to_locator')
            to_concept = get_attr_func(arc, 'to')
            
            if from_locator and from_concept:
                locator_map[from_locator] = from_concept
            if to_locator and to_concept:
                locator_map[to_locator] = to_concept
        
        return locator_map
    
    def build_hierarchy(
        self,
        arcs: list[any],
        locator_map: dict[str, str],
        get_attr_func
    ) -> dict[str, any]:
        """
        Build hierarchy structure from presentation arcs.
        
        Args:
            arcs: List of presentation arcs
            locator_map: Map from locator IDs to concepts
            get_attr_func: Function to safely get attributes
            
        Returns:
            Hierarchy dictionary with roots, children, parents, and order
        """
        children = defaultdict(list)
        parents = {}
        order_map = {}
        
        for arc in arcs:
            from_locator = get_attr_func(arc, 'from_locator')
            to_locator = get_attr_func(arc, 'to_locator')
            
            from_concept = locator_map.get(from_locator)
            to_concept = locator_map.get(to_locator)
            
            if from_concept and to_concept:
                children[from_concept].append(to_concept)
                parents[to_concept] = from_concept
                
                # Track order
                order = get_attr_func(arc, 'order', 0)
                if order:
                    order_map[to_concept] = order
        
        # Find roots (concepts with no parents)
        all_concepts = set(children.keys()) | set(parents.keys())
        roots = [c for c in all_concepts if c not in parents]
        
        hierarchy = {
            'roots': roots,
            'children': dict(children),
            'parents': parents,
            'order': order_map
        }
        
        return hierarchy
    
    def calculate_max_depth(self, hierarchy: dict[str, any]) -> int:
        """
        Calculate maximum depth of hierarchy.
        
        Core statements are typically shallow (2-4 levels).
        Detail schedules are deep (5-10+ levels).
        
        Args:
            hierarchy: Hierarchy dict with roots and children
            
        Returns:
            Maximum depth (0 if empty, 1 for roots only)
        """
        if not hierarchy or not hierarchy.get('roots'):
            return 0
        
        def get_depth(concept: str, children: dict, visited: set) -> int:
            """Recursively calculate depth from this concept."""
            if concept in visited:  # Prevent infinite loops
                return 0
            
            visited.add(concept)
            
            if concept not in children or not children[concept]:
                return 1
            
            child_depths = [
                get_depth(child, children, visited.copy())
                for child in children[concept]
            ]
            
            return 1 + max(child_depths) if child_depths else 1
        
        # Calculate depth from each root, take maximum
        children = hierarchy.get('children', {})
        max_depth = 0
        
        for root in hierarchy['roots']:
            depth = get_depth(root, children, set())
            max_depth = max(max_depth, depth)
        
        return max_depth