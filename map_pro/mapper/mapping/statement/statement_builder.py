# Path: mapping/statement/statement_builder.py
"""
Statement Builder

Organizes facts according to company-declared presentation structure.

DESIGN PRINCIPLES:
- Follows company's presentation linkbases EXACTLY
- If fact appears in N roles, include it N times
- NO assumptions about what statements should contain
- Preserves complete hierarchy as declared

RESPONSIBILITY:
- Takes discovered presentation networks (from LinkbaseLocator)
- Takes parsed facts (from ParsedFiling)
- Organizes facts into statements following company's declared structure
- Returns statements exactly as company presented them
"""

import logging
from pathlib import Path
from typing import Optional
from collections import defaultdict

from ...loaders.linkbase_locator import LinkbaseSet, PresentationNetwork
from ...loaders.parser_output import ParsedFiling
from ...components.dimension_handler import DimensionHandler
from ...components.relationship_navigator import RelationshipNavigator
from ...components.qname_utils import QNameUtils
from ...mapping.statement.helpers import (
    determine_statement_date,
    determine_period_type,
    build_context_map
)
from ...mapping.statement.statistics import StatementBuildingStatistics
from ...mapping.network_classifier import NetworkClassifier
from ...mapping.statement.models import Statement, StatementSet, StatementFact
from ...mapping.statement.hierarchy_builder import HierarchyBuilder
from ...mapping.statement.fact_extractor import FactExtractor


class StatementBuilder:
    """
    Builds financial statements from company-declared presentation structure.
    
    Workflow:
    1. Initialize components (DimensionHandler, RelationshipNavigator, NetworkClassifier)
    2. For each presentation network:
       a. Build hierarchy from arcs
       b. Extract facts matching concepts in hierarchy
       c. Classify network
       d. Create Statement with facts
    3. Track multi-appearance facts
    4. Return complete StatementSet
    """
    
    def __init__(self):
        """Initialize statement builder."""
        self.logger = logging.getLogger('mapping.statement_builder')
        
        # Components (initialized in build_statements when data is available)
        self.dimension_handler = None
        self.relationship_navigator = None
        self.classifier = None  # Created in build_statements with schema_set
        
        # Extracted components for clean separation
        self.hierarchy_builder = HierarchyBuilder()
        self.fact_extractor = None  # Initialized after we have _get_attr
        
        # Statistics tracker
        self.statistics = None
        
        self.logger.info("StatementBuilder initialized")
    
    def build_statements(
        self,
        linkbase_set: LinkbaseSet,
        parsed_filing: ParsedFiling,
        schema_set=None,  # schema_set for role definitions
        xbrl_filing_path: Optional[Path] = None  # XBRL path for dimension extraction
    ) -> StatementSet:
        """
        Build statements according to company's declared presentation structure.

        Args:
            linkbase_set: Discovered linkbases from filing
            parsed_filing: Parsed facts, contexts, units
            schema_set: Optional schema set with role definitions
            xbrl_filing_path: Optional path to XBRL filing for direct dimension extraction

        Returns:
            StatementSet with all statements as company declared them
        """
        self.logger.info("Building statements from presentation networks...")

        # Initialize statistics tracker
        self.statistics = StatementBuildingStatistics()
        self.statistics.total_facts_in_filing = len(parsed_filing.facts)

        # Create NetworkClassifier with role definition sources
        self.classifier = NetworkClassifier(
            schema_set=schema_set,
            linkbase_set=linkbase_set
        )
        self.logger.info(
            f"NetworkClassifier initialized with "
            f"schema_set={'available' if schema_set else 'None'}, "
            f"linkbase_set={'available' if linkbase_set else 'None'}"
        )

        # Initialize components with actual data and XBRL path for dimensions
        self._initialize_components(linkbase_set, parsed_filing, xbrl_filing_path)
        
        statement_set = StatementSet()
        
        # Build a statement for each presentation network
        for presentation_network in linkbase_set.presentation_networks:
            statement = self._build_statement_from_network(
                presentation_network,
                parsed_filing
            )
            
            statement_set.statements.append(statement)
            statement_set.role_uri_to_statement[statement.role_uri] = statement
        
        # Track which concepts appear in which roles
        self._track_concept_appearances(statement_set)
        
        # Add metadata
        statement_set.metadata['total_facts'] = sum(
            len(s.facts) for s in statement_set.statements
        )
        statement_set.metadata['total_statements'] = len(statement_set.statements)
        
        # Finalize statistics
        self.statistics.total_statements_built = len(statement_set.statements)
        self.statistics.total_facts_mapped = statement_set.metadata['total_facts']
        
        self.logger.info(
            f"Built {len(statement_set.statements)} statements with "
            f"{statement_set.metadata['total_facts']} total fact placements"
        )
        
        # Print statistics summary
        self.statistics.print_summary()
        
        return statement_set
    
    def _initialize_components(
        self,
        linkbase_set: LinkbaseSet,
        parsed_filing: ParsedFiling,
        xbrl_filing_path: Optional[Path] = None
    ) -> None:
        """
        Initialize all components with actual filing data.

        Args:
            linkbase_set: Linkbases from filing
            parsed_filing: Parsed filing data
            xbrl_filing_path: Optional path to XBRL filing directory for dimension extraction
        """
        self.logger.info("Initializing components...")

        self.dimension_handler = DimensionHandler(linkbase_set)
        self.relationship_navigator = RelationshipNavigator(linkbase_set)

        # Initialize fact_extractor with our _get_attr function and XBRL path
        self.fact_extractor = FactExtractor(self._get_attr, xbrl_filing_path)

        if xbrl_filing_path:
            self.logger.info(f"FactExtractor initialized with XBRL path: {xbrl_filing_path}")

        self.logger.info("Components initialized successfully")
    
    def _build_statement_from_network(
        self,
        network: PresentationNetwork,
        parsed_filing: ParsedFiling
    ) -> Statement:
        """
        Build a single statement from a presentation network.
        
        Delegates to:
        - HierarchyBuilder for building presentation structure
        - FactExtractor for extracting facts in hierarchical order
        - NetworkClassifier for categorizing the network
        
        Args:
            network: Presentation network (role with arcs)
            parsed_filing: Parsed filing with facts
            
        Returns:
            Statement with facts organized as declared
        """
        statement = Statement(
            role_uri=network.role_uri,
            role_definition=network.role_definition,
            statement_type=self._detect_statement_type(network.role_uri)
        )
        
        # STEP 1: Build locator map (delegate to HierarchyBuilder)
        locator_map = self.hierarchy_builder.build_locator_map(
            network.arcs,
            self._get_attr
        )
        
        # STEP 2: Build hierarchy from arcs (delegate to HierarchyBuilder)
        hierarchy = self.hierarchy_builder.build_hierarchy(
            network.arcs,
            locator_map,
            self._get_attr
        )
        statement.hierarchy = hierarchy
        
        # STEP 3: Extract facts in hierarchical order (delegate to FactExtractor)
        statement.facts = self.fact_extractor.extract_facts_in_order(
            hierarchy,
            parsed_filing,
            network.role_uri
        )
        
        # STEP 4: Calculate structural metrics with ACTUAL fact count
        network_structure = {
            'fact_count': len(statement.facts),  # Actual facts in THIS network
            'max_depth': self.hierarchy_builder.calculate_max_depth(hierarchy),
            'root_count': len(hierarchy.get('roots', [])),
            'roots': list(hierarchy.get('roots', []))[:5]  # Sample of roots
        }
        
        # STEP 5: Classify network using structural analysis
        classification = self.classifier.classify(
            network.role_uri,
            network.role_definition,
            network_structure
        )
        
        # Log classification results for transparency
        self.logger.info(
            f"Network: {network.role_uri.split('/')[-1][:60]}... | "
            f"Category: {classification.category} | "
            f"Facts: {network_structure['fact_count']} | "
            f"Depth: {network_structure['max_depth']} | "
            f"Roots: {network_structure['root_count']} | "
            f"Source: {classification.source} | "
            f"Signals: {classification.structural_signals.get('structure_score', 'N/A')}"
        )
        
        # Store classification in metadata
        statement.metadata['classification'] = {
            'category': classification.category,
            'statement_type': classification.statement_type,
            'is_primary': classification.is_primary,
            'confidence': classification.confidence,
            'matched_patterns': classification.matched_patterns,
            'structural_signals': classification.structural_signals,
            'source': classification.source,
            'taxonomy_source': classification.taxonomy_source,
            'fallback_used': classification.fallback_used,
        }
        
        # Update legacy statement_type field
        if classification.statement_type:
            statement.statement_type = classification.statement_type
        
        self.logger.debug(
            f"Built statement {network.role_uri}: "
            f"{len(statement.facts)} facts in hierarchy"
        )
        
        return statement
    
    def _detect_statement_type(self, role_uri: str) -> str:
        """
        Detect statement type from role URI.
        
        Args:
            role_uri: Role URI
            
        Returns:
            Statement type string
        """
        role_lower = role_uri.lower()
        
        if 'balancesheet' in role_lower or 'financialposition' in role_lower:
            return 'balance_sheet'
        elif 'income' in role_lower or 'operations' in role_lower or 'earnings' in role_lower:
            return 'income_statement'
        elif 'cashflow' in role_lower or 'cash' in role_lower:
            return 'cash_flow'
        elif 'equity' in role_lower or 'stockholder' in role_lower or 'shareholder' in role_lower:
            return 'equity'
        else:
            return 'other'
    
    def _track_concept_appearances(self, statement_set: StatementSet):
        """
        Track which concepts appear in which statements.
        
        Args:
            statement_set: Statement set to analyze
        """
        concept_to_roles = defaultdict(list)
        
        for statement in statement_set.statements:
            for fact in statement.facts:
                concept_to_roles[fact.concept].append(statement.role_uri)
        
        statement_set.concept_to_roles = dict(concept_to_roles)
    
    @staticmethod
    def _get_attr(data, attr, default=None):
        """
        Universal attribute getter - handles ANY data format.
        
        Supports:
        - Dictionary: data['attr'] or data.get('attr')
        - Object: data.attr or getattr(data, 'attr')
        - Nested dict: data['nested']['attr']
        - None/missing: returns default
        
        Args:
            data: Data in any format (dict, object, etc.)
            attr: Attribute name (supports dot notation for nested: 'parent.child')
            default: Default value if not found
            
        Returns:
            Attribute value or default
            
        Examples:
            _get_attr({'name': 'value'}, 'name') → 'value'
            _get_attr(obj, 'name') → obj.name
            _get_attr({'a': {'b': 1}}, 'a.b') → 1
            _get_attr(None, 'name', 'default') → 'default'
        """
        if data is None:
            return default
        
        # Handle dot notation for nested attributes
        if '.' in attr:
            parts = attr.split('.')
            current = data
            for part in parts:
                current = StatementBuilder._get_attr(current, part, None)
                if current is None:
                    return default
            return current
        
        # Try dictionary access first (most common in XBRL data)
        if isinstance(data, dict):
            return data.get(attr, default)
        
        # Try object attribute access
        if hasattr(data, attr):
            return getattr(data, attr, default)
        
        # Try dictionary-style access on object (some objects support both)
        try:
            return data[attr]
        except (KeyError, TypeError, AttributeError):
            pass
        
        # Nothing worked, return default
        return default


__all__ = [
    'StatementBuilder',
    'Statement',
    'StatementSet',
    'StatementFact',
]