# Path: mapping/network_classifier.py
"""
Network Classifier - Schema-Driven with Structural Fallback

Classifies XBRL presentation networks by reading role definitions from:
1. Schema files (.xsd) - PRIMARY
2. Linkbase files (.xml) - SECONDARY
3. Structural analysis - FALLBACK

DESIGN PRINCIPLES:
- Read as-is (company's role definitions take precedence)
- Source priority hierarchy (schema > linkbase > structural)
- Market and taxonomy agnostic
- Source tracking for audit trail

CLASSIFICATION ALGORITHM:
1. **Read Role Definition**: Check schema, then linkbase
2. **Structural Analysis**: If no definition, analyze structure
3. **Fallback Pattern**: Last resort if structure unclear
4. **Source Tracking**: Record which source was used
"""

import logging
from dataclasses import dataclass
from typing import Optional

from ..mapping.constants import (
    # Exclusion patterns (universal)
    DETAIL_INDICATORS,
    TABLE_INDICATORS,
    POLICY_INDICATORS,
    PARENTHETICAL_INDICATOR,
    DOCUMENT_INDICATORS,
    
    # Structural thresholds (universal heuristics)
    CORE_STATEMENT_MIN_FACTS,
    CORE_STATEMENT_MAX_DEPTH,
    CORE_STATEMENT_MIN_ROOTS,
    CONFIDENCE_HIGH_THRESHOLD,
    CONFIDENCE_MEDIUM_THRESHOLD,
    
    # Statement type FALLBACK patterns (use only when taxonomy unavailable)
    BALANCE_SHEET_FALLBACK_PATTERNS,
    INCOME_STATEMENT_FALLBACK_PATTERNS,
    CASH_FLOW_FALLBACK_PATTERNS,
    EQUITY_FALLBACK_PATTERNS,
    
    # Enumerations
    NetworkCategory,
    StatementType,
    ConfidenceLevel,
)


@dataclass
class NetworkClassification:
    """
    Classification result for a presentation network.
    
    Attributes:
        category: CORE_STATEMENT, DETAIL, TABLE, POLICY, etc.
        statement_type: BALANCE_SHEET, INCOME_STATEMENT, etc.
        is_primary: True if core financial statement
        confidence: HIGH, MEDIUM, or LOW
        matched_patterns: List of patterns that matched
        structural_signals: Dict of structural analysis results
        role_uri: Original role URI
        role_definition: Original role definition
        source: Which source provided classification
        taxonomy_source: schema/linkbase/taxonomy/fallback
        fallback_used: Was fallback pattern matching used?
    """
    category: str
    statement_type: str
    is_primary: bool
    confidence: str
    matched_patterns: list[str]
    structural_signals: dict[str, any]
    role_uri: str
    role_definition: Optional[str] = None
    source: str = "unknown"
    taxonomy_source: str = "unknown"
    fallback_used: bool = False


class NetworkClassifier:
    """
    Classifies XBRL presentation networks using SOURCE PRIORITY.
    
    PRIORITY ORDER:
    1. Read role definitions from schema files (HIGH confidence)
    2. Read role definitions from linkbase files (HIGH confidence)
    3. Analyze structure (MEDIUM confidence)
    4. Pattern matching fallback (LOW confidence, with warning)
    
    Example:
        classifier = NetworkClassifier(schema_set=schema_set, linkbase_set=linkbase_set)
        
        result = classifier.classify(
            role_uri="http://company.com/role/ConsolidatedBalanceSheets"
        )
        
        print(result.statement_type)  # 'BALANCE_SHEET'
        print(result.source)          # 'schema_definition'
        print(result.confidence)      # 'HIGH'
    """
    
    def __init__(self, schema_set=None, linkbase_set=None):
        """
        Initialize classifier with role definition sources.
        
        Args:
            schema_set: Optional SchemaSet with role definitions from .xsd
            linkbase_set: Optional LinkbaseSet with role definitions from .xml
        """
        self.schema_set = schema_set
        self.linkbase_set = linkbase_set
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _get_role_definition(self, role_uri: str) -> tuple[Optional[str], str]:
        """
        Get role definition with source priority.
        
        SOURCE PRIORITY:
        1. schema_set (from .xsd files) - PRIMARY
        2. linkbase_set (from .xml files) - SECONDARY
        3. None (not found) - UNKNOWN
        
        Args:
            role_uri: Role URI to look up
            
        Returns:
            Tuple of (role_definition_text, source)
            source: "schema_definition", "linkbase_definition", or "not_found"
        """
        # SOURCE 1: Check schema files first (PRIMARY)
        if self.schema_set and hasattr(self.schema_set, 'role_definitions'):
            if role_uri in self.schema_set.role_definitions:
                role_def = self.schema_set.role_definitions[role_uri]
                if role_def.definition:
                    self.logger.debug(f"Found role in schema: {role_uri}")
                    return role_def.definition, "schema_definition"
        
        # SOURCE 2: Check linkbase files second (SECONDARY)
        if self.linkbase_set and hasattr(self.linkbase_set, 'role_definitions'):
            if role_uri in self.linkbase_set.role_definitions:
                role_def = self.linkbase_set.role_definitions[role_uri]
                if role_def.definition:
                    self.logger.debug(f"Found role in linkbase: {role_uri}")
                    return role_def.definition, "linkbase_definition"
        
        # Not found in any source
        self.logger.debug(f"No role definition found: {role_uri}")
        return None, "not_found"
    
    def _classify_from_role_definition(
        self,
        role_definition: str,
        role_uri: str
    ) -> tuple[str, str, list[str]]:
        """
        Classify network from role definition text.
        
        Reads what the company declared, not pattern matching.
        
        Args:
            role_definition: Definition text from roleType
            role_uri: Role URI (for logging)
            
        Returns:
            Tuple of (category, statement_type, reasoning)
        """
        definition_lower = role_definition.lower()
        reasoning = []
        
        # Determine category from definition
        category = NetworkCategory.UNKNOWN
        statement_type = StatementType.OTHER
        
        # Check for category indicators
        if any(kw in definition_lower for kw in ['statement', 'sheet', 'consolidated']):
            if not any(kw in definition_lower for kw in ['detail', 'schedule', 'table']):
                category = NetworkCategory.CORE_STATEMENT
                reasoning.append(f"Contains 'statement' without 'detail/schedule/table'")
        elif any(kw in definition_lower for kw in ['detail', 'schedule']):
            category = NetworkCategory.DETAIL
            reasoning.append(f"Contains 'detail' or 'schedule'")
        elif 'table' in definition_lower:
            category = NetworkCategory.TABLE
            reasoning.append(f"Contains 'table'")
        elif 'polic' in definition_lower:
            category = NetworkCategory.POLICY
            reasoning.append(f"Contains 'policy'")
        
        # Determine statement type from definition
        if any(kw in definition_lower for kw in ['balance sheet', 'financial position', 'balance sheets']):
            statement_type = StatementType.BALANCE_SHEET
            reasoning.append(f"Definition mentions 'balance sheet'")
        elif any(kw in definition_lower for kw in ['income', 'operations', 'earnings', 'profit', 'loss']):
            statement_type = StatementType.INCOME_STATEMENT
            reasoning.append(f"Definition mentions income/operations")
        elif 'cash flow' in definition_lower:
            statement_type = StatementType.CASH_FLOW
            reasoning.append(f"Definition mentions 'cash flow'")
        elif any(kw in definition_lower for kw in ['equity', 'stockholders', 'shareholders', 'capital']):
            statement_type = StatementType.EQUITY
            reasoning.append(f"Definition mentions equity/shareholders")
        
        return category, statement_type, reasoning
    
    def classify(
        self,
        role_uri: str,
        role_definition: Optional[str] = None,
        network_structure: Optional[dict[str, any]] = None
    ) -> NetworkClassification:
        """
        Classify a presentation network using SOURCE PRIORITY.
        
        PRIORITY ORDER:
        1. Read from role definition (schema or linkbase)
        2. Analyze structure
        3. FALLBACK to pattern matching (with warning)
        
        Args:
            role_uri: Role URI from presentation linkbase
            role_definition: Optional role definition (deprecated - now auto-retrieved)
            network_structure: Dict with structural info
            
        Returns:
            NetworkClassification with source tracking
        """
        self.logger.debug(f"Classifying network: {role_uri}")
        
        # Get role definition from sources
        retrieved_definition, definition_source = self._get_role_definition(role_uri)
        
        # Use retrieved definition if available
        if retrieved_definition:
            role_definition = retrieved_definition
        
        # Initialize
        structural_signals = {}
        matched_patterns = []
        fallback_used = False
        
        # TIER 1: Try role definition first (HIGH confidence)
        if role_definition and definition_source != "not_found":
            category, statement_type, reasoning = self._classify_from_role_definition(
                role_definition,
                role_uri
            )
            
            if category != NetworkCategory.UNKNOWN:
                # Successfully classified from definition
                return NetworkClassification(
                    category=category,
                    statement_type=statement_type,
                    is_primary=(category == NetworkCategory.CORE_STATEMENT),
                    confidence=ConfidenceLevel.HIGH,
                    matched_patterns=reasoning,
                    structural_signals={'classification_method': 'role_definition'},
                    role_uri=role_uri,
                    role_definition=role_definition,
                    source=definition_source,
                    taxonomy_source=definition_source,
                    fallback_used=False
                )
        
        # TIER 2: Structural analysis (MEDIUM confidence)
        category = NetworkCategory.UNKNOWN
        
        # Check exclusion indicators
        category, category_patterns = self._determine_category_by_exclusion(role_uri)
        matched_patterns.extend(category_patterns)
        
        # If not excluded, analyze structure
        if category == NetworkCategory.UNKNOWN and network_structure:
            category, signals = self._determine_category_by_structure(
                role_uri,
                network_structure
            )
            structural_signals.update(signals)
        
        # TIER 3: FALLBACK pattern matching (LOW confidence)
        statement_type = StatementType.OTHER
        if category != NetworkCategory.UNKNOWN:
            # Only use pattern matching if we classified category
            statement_type, type_patterns = self._determine_statement_type(role_uri)
            matched_patterns.extend(type_patterns)
            fallback_used = True
            
            self.logger.warning(
                f" Using FALLBACK pattern matching for {role_uri} "
                f"(no role definition available)"
            )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            category,
            statement_type,
            matched_patterns,
            structural_signals,
            role_uri,
            role_definition
        )
        
        return NetworkClassification(
            category=category,
            statement_type=statement_type,
            is_primary=(category == NetworkCategory.CORE_STATEMENT),
            confidence=confidence if not fallback_used else ConfidenceLevel.LOW,
            matched_patterns=matched_patterns,
            structural_signals=structural_signals,
            role_uri=role_uri,
            role_definition=role_definition,
            source="structural_analysis" if category != NetworkCategory.UNKNOWN else "unknown",
            taxonomy_source="fallback_pattern" if fallback_used else "structural",
            fallback_used=fallback_used
        )
    
    def _determine_category_by_exclusion(
        self,
        role_uri: str
    ) -> tuple[str, list[str]]:
        """
        Determine if network is explicitly NOT core using exclusion patterns.
        
        Universal exclusion indicators (work for all markets):
        - Details, Schedule  Supporting detail
        - Tables  Separate data table
        - Policies  Accounting policy disclosure
        - Parenthetical  Supplementary information
        - Document/Cover  Administrative
        
        Args:
            role_uri: Role URI to analyze
            
        Returns:
            Tuple of (category, matched_patterns)
        """
        matched_patterns = []
        
        # Convert to lowercase for case-insensitive matching
        role_uri_lower = role_uri.lower()
        
        # Check document indicators
        for pattern in DOCUMENT_INDICATORS:
            if pattern.lower() in role_uri_lower:
                matched_patterns.append(pattern)
                return NetworkCategory.DOCUMENT, matched_patterns
        
        # Check parenthetical indicator
        if PARENTHETICAL_INDICATOR.lower() in role_uri_lower:
            matched_patterns.append(PARENTHETICAL_INDICATOR)
            return NetworkCategory.PARENTHETICAL, matched_patterns
        
        # Check detail indicators
        for pattern in DETAIL_INDICATORS:
            if pattern.lower() in role_uri_lower:
                matched_patterns.append(pattern)
                return NetworkCategory.DETAIL, matched_patterns
        
        # Check table indicators
        for pattern in TABLE_INDICATORS:
            if pattern.lower() in role_uri_lower:
                matched_patterns.append(pattern)
                return NetworkCategory.TABLE, matched_patterns
        
        # Check policy indicators
        for pattern in POLICY_INDICATORS:
            if pattern.lower() in role_uri_lower:
                matched_patterns.append(pattern)
                return NetworkCategory.POLICY, matched_patterns
        
        # Not excluded - proceed to structural analysis
        return NetworkCategory.UNKNOWN, matched_patterns
    
    def _determine_category_by_structure(
        self,
        role_uri: str,
        network_structure: dict[str, any]
    ) -> tuple[str, dict[str, any]]:
        """
        Determine if network is core using STRUCTURAL ANALYSIS.
        
        Core statements have these universal characteristics:
        1. SUBSTANTIVE - Many facts (15+)
        2. SHALLOW - Low hierarchy depth (4 levels)
        3. BROAD - Multiple root concepts (2+)
        
        Args:
            role_uri: Role URI
            network_structure: Dict with fact_count, max_depth, root_count
            
        Returns:
            Tuple of (category, structural_signals_dict)
        """
        signals = {}
        score = 0
        max_score = 3
        
        # Signal 1: Fact count (substantiality)
        fact_count = network_structure.get('fact_count', 0)
        signals['fact_count'] = fact_count
        if fact_count >= CORE_STATEMENT_MIN_FACTS:
            score += 1
            signals['fact_count_pass'] = True
        else:
            signals['fact_count_pass'] = False
        
        # Signal 2: Hierarchy depth (aggregation level)
        max_depth = network_structure.get('max_depth', 999)
        signals['max_depth'] = max_depth
        if max_depth <= CORE_STATEMENT_MAX_DEPTH:
            score += 1
            signals['depth_pass'] = True
        else:
            signals['depth_pass'] = False
        
        # Signal 3: Root count (breadth)
        root_count = network_structure.get('root_count', 0)
        signals['root_count'] = root_count
        if root_count >= CORE_STATEMENT_MIN_ROOTS:
            score += 1
            signals['root_count_pass'] = True
        else:
            signals['root_count_pass'] = False
        
        # Classification decision
        signals['structure_score'] = f"{score}/{max_score}"
        
        # Require at least 2/3 signals to classify as core
        if score >= 2:
            return NetworkCategory.CORE_STATEMENT, signals
        else:
            return NetworkCategory.UNKNOWN, signals
    
    def _determine_statement_type(
        self,
        role_uri: str
    ) -> tuple[str, list[str]]:
        """
        Determine statement type from role URI.
        
        CASE-INSENSITIVE matching to handle different URI formats.
        
        Statement types (universal):
        - Balance Sheet / Statement of Financial Position
        - Income Statement / Statement of Operations
        - Cash Flow Statement
        - Statement of Changes in Equity
        
        Args:
            role_uri: Role URI to analyze
            
        Returns:
            Tuple of (statement_type, matched_patterns)
        """
        matched_patterns = []
        
        # Convert to lowercase for case-insensitive matching
        role_uri_lower = role_uri.lower()
        
        # Check balance sheet patterns
        for pattern in BALANCE_SHEET_FALLBACK_PATTERNS:
            if pattern.lower() in role_uri_lower:
                matched_patterns.append(pattern)
                return StatementType.BALANCE_SHEET, matched_patterns
        
        # Check income statement patterns
        for pattern in INCOME_STATEMENT_FALLBACK_PATTERNS:
            if pattern.lower() in role_uri_lower:
                matched_patterns.append(pattern)
                return StatementType.INCOME_STATEMENT, matched_patterns
        
        # Check cash flow patterns
        for pattern in CASH_FLOW_FALLBACK_PATTERNS:
            if pattern.lower() in role_uri_lower:
                matched_patterns.append(pattern)
                return StatementType.CASH_FLOW, matched_patterns
        
        # Check equity patterns
        for pattern in EQUITY_FALLBACK_PATTERNS:
            if pattern.lower() in role_uri_lower:
                matched_patterns.append(pattern)
                return StatementType.EQUITY, matched_patterns
        
        # Default to OTHER
        return StatementType.OTHER, matched_patterns
    
    def _calculate_confidence(
        self,
        category: str,
        statement_type: str,
        matched_patterns: list[str],
        structural_signals: dict[str, any],
        role_uri: str,
        role_definition: Optional[str]
    ) -> str:
        """
        Calculate confidence level based on multiple signals.
        
        High confidence: Multiple strong signals
        Medium confidence: Mixed signals
        Low confidence: Weak or conflicting signals
        
        Args:
            category: Determined category
            statement_type: Determined statement type
            matched_patterns: Patterns that matched
            structural_signals: Structural analysis results
            role_uri: Original role URI
            role_definition: Optional role definition
            
        Returns:
            Confidence level string (HIGH, MEDIUM, LOW)
        """
        confidence_score = 0.0
        
        # Pattern matching adds confidence
        if matched_patterns:
            confidence_score += 0.3
        
        # Structural analysis adds confidence
        if structural_signals:
            structure_score = structural_signals.get('structure_score', '0/3')
            numerator, denominator = map(int, structure_score.split('/'))
            confidence_score += (numerator / denominator) * 0.5
        
        # Explicit categorization adds confidence
        if category != NetworkCategory.UNKNOWN:
            confidence_score += 0.2
        
        # Determine confidence level
        if confidence_score >= CONFIDENCE_HIGH_THRESHOLD:
            return ConfidenceLevel.HIGH
        elif confidence_score >= CONFIDENCE_MEDIUM_THRESHOLD:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW