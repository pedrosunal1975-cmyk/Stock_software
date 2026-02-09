# Path: mapping/statement/fact_extractor.py
"""
Fact Extractor

Extracts facts from parsed filing according to presentation hierarchy.
Handles QName normalization and hierarchical traversal.

DIMENSION EXTRACTION:
- Reads dimensional information DIRECTLY from XBRL source files
- Falls back to parsed.json contexts if XBRL path not available
"""

import logging
import re
from pathlib import Path
from typing import Optional
from collections import defaultdict

from ...loaders.parser_output import ParsedFiling
from ...components.qname_utils import QNameUtils
from ...mapping.statement.models import StatementFact
from ...mapping.statement.fact_enricher import FactEnricher


class FactExtractor:
    """
    Extracts facts following presentation hierarchy order.

    Responsibilities:
    - Build concept-to-facts mapping with normalized QNames
    - Traverse hierarchy depth-first
    - Extract facts in presentation order
    - Handle parent-child relationships
    - Extract period and dimension information from XBRL source files
    """

    def __init__(self, get_attr_func, xbrl_filing_path: Optional[Path] = None):
        """
        Initialize fact extractor.

        Args:
            get_attr_func: Function to safely get attributes from data objects
            xbrl_filing_path: Optional path to XBRL filing directory for direct dimension extraction
        """
        self.logger = logging.getLogger('mapping.fact_extractor')
        self._get_attr = get_attr_func
        self.fact_enricher = FactEnricher()  # Initialize enricher
        self._context_cache: dict[str, dict] = {}  # Cache context_id -> period/dimension info

        # XBRL filing path for direct context/dimension extraction
        self._xbrl_filing_path = xbrl_filing_path
        self._xbrl_contexts_loaded = False
    
    def extract_facts_in_order(
        self,
        hierarchy: dict[str, any],
        parsed_filing: ParsedFiling,
        role_uri: str
    ) -> list[StatementFact]:
        """
        Extract facts following hierarchy order.
        
        Uses normalized concept name matching (local names) to handle
        QName variations (us-gaap:Assets vs Assets vs us-gaap_Assets).
        
        Args:
            hierarchy: Hierarchy structure with roots, children, parents, order
            parsed_filing: Parsed filing with facts
            role_uri: Role URI for this statement
            
        Returns:
            List of StatementFacts in hierarchical order
        """
        statement_facts = []

        # Build context cache for period lookup (CRITICAL for calculation verification)
        self._build_context_cache(parsed_filing)

        # Build concept-to-facts map with normalized local names
        concept_facts_map = self._build_concept_facts_map(parsed_filing)
        
        # Traverse hierarchy depth-first
        visited = set()
        
        for root in hierarchy['roots']:
            self._traverse_and_extract(
                root,
                hierarchy,
                concept_facts_map,
                parsed_filing,
                statement_facts,
                visited,
                level=0,
                parent=None
            )
        
        # Count facts with dimensional contexts (useful for verification planning)
        facts_with_dims = sum(1 for f in statement_facts if f.dimensions)
        self.logger.debug(
            f"Extracted {len(statement_facts)} facts "
            f"({facts_with_dims} with dimensions, {len(statement_facts) - facts_with_dims} without)"
        )

        # ENRICH facts with calculated values for verification
        enriched_facts = []
        for fact in statement_facts:
            enriched_fact = self.fact_enricher.enrich_fact(fact)
            enriched_facts.append(enriched_fact)

        self.logger.info(f"Enriched {len(enriched_facts)} facts with calculated values")

        return enriched_facts
    
    def _build_concept_facts_map(self, parsed_filing: ParsedFiling) -> dict[str, list]:
        """
        Build map from normalized concept names to facts.
        
        Normalizes QNames to local names for matching:
        - us-gaap:Assets -> Assets
        - us-gaap_Assets -> Assets
        - Assets -> Assets
        
        Args:
            parsed_filing: Parsed filing with facts
            
        Returns:
            Dictionary mapping local concept names to lists of facts
        """
        concept_facts_map = defaultdict(list)
        
        for fact in parsed_filing.facts:
            concept_name = self._get_attr(fact, 'name')
            if concept_name:
                try:
                    local_name = QNameUtils.get_local_name(concept_name)
                    concept_facts_map[local_name].append(fact)
                except Exception as e:
                    self.logger.debug(f"Failed to normalize concept '{concept_name}': {e}")
        
        return concept_facts_map

    def _build_context_cache(self, parsed_filing: ParsedFiling) -> None:
        """
        Build cache mapping context_id to period and dimension information.

        PRIORITY for dimension extraction:
        1. XBRL source file (direct parsing) - most accurate for dimensions
        2. Parsed filing contexts - fallback

        This is CRITICAL for calculation verification - facts must be grouped
        by period to ensure calculations compare values from the same time.

        Args:
            parsed_filing: Parsed filing with contexts
        """
        # If already loaded from XBRL and cache is populated, reuse it
        # (contexts don't change between statements in the same filing)
        if self._xbrl_contexts_loaded and self._context_cache:
            return

        self._context_cache.clear()

        # PRIORITY 1: Try loading contexts directly from XBRL source file
        if self._xbrl_filing_path and not self._xbrl_contexts_loaded:
            try:
                xbrl_contexts = self._load_contexts_from_xbrl(self._xbrl_filing_path)

                if xbrl_contexts:
                    self._context_cache = xbrl_contexts
                    self._xbrl_contexts_loaded = True

                    # Log dimension statistics
                    contexts_with_dims = sum(
                        1 for ctx in xbrl_contexts.values()
                        if ctx.get('dimensions')
                    )
                    self.logger.info(
                        f"Loaded {len(xbrl_contexts)} contexts from XBRL, "
                        f"{contexts_with_dims} with dimensions"
                    )
                    return
            except Exception as e:
                self.logger.warning(
                    f"Failed to load contexts from XBRL source: {e}. "
                    f"Falling back to parsed filing."
                )

        # PRIORITY 2: Fallback to parsed filing contexts
        try:
            contexts = parsed_filing.contexts
            for context in contexts:
                context_id = context.id
                if not context_id:
                    continue

                # Extract period info based on type
                period_type = context.period_type
                period_start = None
                period_end = None

                if period_type == 'instant':
                    # Instant: only end date (the instant date)
                    if context.instant:
                        period_end = str(context.instant)
                elif period_type == 'duration':
                    # Duration: start and end dates
                    if context.start_date:
                        period_start = str(context.start_date)
                    if context.end_date:
                        period_end = str(context.end_date)

                # Extract dimensional information from segment/scenario
                # Note: This may be empty if parser didn't extract dimensions
                dimensions = self._extract_dimensions_from_context(context)

                self._context_cache[context_id] = {
                    'period_type': period_type,
                    'period_start': period_start,
                    'period_end': period_end,
                    'dimensions': dimensions,
                }

            self.logger.info(
                f"Built context cache from parsed filing: {len(self._context_cache)} contexts"
            )

        except Exception as e:
            self.logger.warning(f"Failed to build context cache: {e}")

    def _load_contexts_from_xbrl(self, filing_path: Path) -> dict[str, dict]:
        """
        Load contexts directly from XBRL instance document.

        Parses the instance document to extract context elements with
        dimensional information that may not be in parsed.json.

        Args:
            filing_path: Path to XBRL filing directory

        Returns:
            Dictionary mapping context_id to context info (period, dimensions)
        """
        # Find the instance document in the filing directory
        instance_file = self._find_instance_document(filing_path)

        if not instance_file:
            self.logger.debug(f"No instance document found in {filing_path}")
            return {}

        # Read the file content
        try:
            with open(instance_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            self.logger.warning(f"Failed to read instance file: {e}")
            return {}

        # Extract contexts using regex (robust for iXBRL/XBRL mixing)
        return self._extract_contexts_from_content(content)

    def _find_instance_document(self, filing_path: Path) -> Optional[Path]:
        """
        Find XBRL instance document in filing directory.

        Priority: iXBRL (.htm) files first, then traditional XBRL (.xml).

        Args:
            filing_path: Filing directory path

        Returns:
            Path to instance document or None
        """
        if not filing_path.is_dir():
            if filing_path.is_file():
                return filing_path
            return None

        # Look for iXBRL files (.htm)
        htm_files = list(filing_path.glob('*.htm')) + list(filing_path.glob('*.html'))

        for htm_file in htm_files:
            name_lower = htm_file.name.lower()
            # Skip exhibit files
            if name_lower.startswith('ex') or 'exhibit' in name_lower:
                continue
            # Check if it looks like an instance document
            if self._is_instance_document(htm_file):
                return htm_file

        # Fallback: traditional XBRL (.xml)
        xml_files = list(filing_path.glob('*.xml'))
        for xml_file in xml_files:
            name_lower = xml_file.name.lower()
            # Skip linkbase files
            if any(s in name_lower for s in ['_cal', '_def', '_lab', '_pre', '_ref']):
                continue
            return xml_file

        # Last resort: largest .htm file
        if htm_files:
            return max(htm_files, key=lambda f: f.stat().st_size)

        return None

    def _is_instance_document(self, file_path: Path) -> bool:
        """Check if file looks like an XBRL instance document."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                header = f.read(4096)
            return 'xbrl' in header.lower() and 'context' in header.lower()
        except Exception:
            return False

    def _extract_contexts_from_content(self, content: str) -> dict[str, dict]:
        """
        Extract contexts from XBRL/iXBRL file content using regex.

        Args:
            content: File content as string

        Returns:
            Dictionary mapping context_id to context info
        """
        contexts = {}

        # Pattern to match context elements
        context_pattern = re.compile(
            r'<(?:xbrli:)?context[^>]*id=["\']([^"\']+)["\'][^>]*>(.*?)</(?:xbrli:)?context>',
            re.DOTALL | re.IGNORECASE
        )

        for match in context_pattern.finditer(content):
            context_id = match.group(1)
            context_body = match.group(2)

            context_info = self._parse_context_body(context_body)
            contexts[context_id] = context_info

        return contexts

    def _parse_context_body(self, body: str) -> dict:
        """
        Parse context element body to extract period and dimensions.

        Args:
            body: Inner XML content of context element

        Returns:
            Dictionary with period_type, period_start, period_end, dimensions
        """
        info = {
            'period_type': None,
            'period_start': None,
            'period_end': None,
            'dimensions': {},
        }

        # Extract period - instant
        instant_match = re.search(
            r'<(?:xbrli:)?instant>([^<]+)</(?:xbrli:)?instant>',
            body, re.IGNORECASE
        )
        if instant_match:
            info['period_type'] = 'instant'
            info['period_end'] = instant_match.group(1).strip()
        else:
            # Extract period - duration
            start_match = re.search(
                r'<(?:xbrli:)?startDate>([^<]+)</(?:xbrli:)?startDate>',
                body, re.IGNORECASE
            )
            end_match = re.search(
                r'<(?:xbrli:)?endDate>([^<]+)</(?:xbrli:)?endDate>',
                body, re.IGNORECASE
            )
            if start_match or end_match:
                info['period_type'] = 'duration'
                if start_match:
                    info['period_start'] = start_match.group(1).strip()
                if end_match:
                    info['period_end'] = end_match.group(1).strip()

        # Extract dimensions from explicitMember elements
        # Pattern: <xbrldi:explicitMember dimension="axis">member</xbrldi:explicitMember>
        dim_pattern = re.compile(
            r'<(?:xbrldi:)?explicitMember[^>]*dimension=["\']([^"\']+)["\'][^>]*>'
            r'([^<]+)</(?:xbrldi:)?explicitMember>',
            re.IGNORECASE
        )

        for dim_match in dim_pattern.finditer(body):
            axis = dim_match.group(1).strip()
            member = dim_match.group(2).strip()
            info['dimensions'][axis] = member

        # Also handle typed dimensions (less common)
        typed_pattern = re.compile(
            r'<(?:xbrldi:)?typedMember[^>]*dimension=["\']([^"\']+)["\'][^>]*>'
            r'(.*?)</(?:xbrldi:)?typedMember>',
            re.DOTALL | re.IGNORECASE
        )

        for typed_match in typed_pattern.finditer(body):
            axis = typed_match.group(1).strip()
            member_content = typed_match.group(2)
            # Extract text value from typed member
            member_value = re.sub(r'<[^>]+>', '', member_content).strip()
            if member_value:
                info['dimensions'][f'{axis}[typed]'] = member_value

        return info

    def _extract_dimensions_from_context(self, context) -> dict[str, str]:
        """
        Extract dimensional qualifiers from context segment/scenario.

        XBRL dimensions are stored as explicit members in the segment or
        scenario elements of a context. The dimension (axis) is the key
        and the member is the value.

        Example context structure:
            <xbrli:segment>
                <xbrldi:explicitMember dimension="us-gaap:StatementEquityComponentsAxis">
                    us-gaap:RetainedEarningsMember
                </xbrldi:explicitMember>
            </xbrli:segment>

        Args:
            context: Context object with segment/scenario attributes

        Returns:
            Dictionary mapping axis QName to member QName
            e.g., {"us-gaap:StatementEquityComponentsAxis": "us-gaap:RetainedEarningsMember"}
        """
        dimensions = {}

        try:
            # Check segment for explicit members
            segment = getattr(context, 'segment', {}) or {}
            if segment:
                self._extract_dimensions_from_segment_or_scenario(segment, dimensions)

            # Check scenario for explicit members
            scenario = getattr(context, 'scenario', {}) or {}
            if scenario:
                self._extract_dimensions_from_segment_or_scenario(scenario, dimensions)

        except Exception as e:
            self.logger.debug(f"Error extracting dimensions from context: {e}")

        return dimensions

    def _extract_dimensions_from_segment_or_scenario(
        self,
        segment_or_scenario: dict,
        dimensions: dict[str, str]
    ) -> None:
        """
        Extract dimensions from a segment or scenario dictionary.

        Handles different possible structures:
        1. Direct axis/member pairs: {"axis": "member"}
        2. Nested explicit_members list: [{"dimension": "axis", "member": "value"}]
        3. Raw explicitMember elements

        Args:
            segment_or_scenario: Segment or scenario dict from context
            dimensions: Dictionary to add extracted dimensions to (modified in place)
        """
        if not isinstance(segment_or_scenario, dict):
            return

        # Structure 1: Direct key-value pairs where key looks like an axis
        for key, value in segment_or_scenario.items():
            if isinstance(value, str):
                # Check if key looks like an axis (contains 'Axis')
                if 'Axis' in key or 'axis' in key.lower():
                    dimensions[key] = value
                # Also handle dimension/member pattern
                elif key in ('dimension', 'axis'):
                    member = segment_or_scenario.get('member', segment_or_scenario.get('value'))
                    if member:
                        dimensions[value] = member

        # Structure 2: List of explicit members
        explicit_members = segment_or_scenario.get('explicit_members', [])
        if not explicit_members:
            explicit_members = segment_or_scenario.get('explicitMember', [])
        if not explicit_members:
            explicit_members = segment_or_scenario.get('members', [])

        if isinstance(explicit_members, list):
            for member in explicit_members:
                if isinstance(member, dict):
                    axis = member.get('dimension') or member.get('axis')
                    value = member.get('member') or member.get('value')
                    if axis and value:
                        dimensions[axis] = value
        elif isinstance(explicit_members, dict):
            # Single explicit member as dict
            axis = explicit_members.get('dimension') or explicit_members.get('axis')
            value = explicit_members.get('member') or explicit_members.get('value')
            if axis and value:
                dimensions[axis] = value

    def _get_period_info(self, context_ref: str) -> dict:
        """
        Get period and dimension information for a context reference.

        Args:
            context_ref: Context ID to look up

        Returns:
            Dictionary with period_type, period_start, period_end, dimensions
        """
        if not context_ref:
            return {
                'period_type': None,
                'period_start': None,
                'period_end': None,
                'dimensions': {},
            }

        return self._context_cache.get(context_ref, {
            'period_type': None,
            'period_start': None,
            'period_end': None,
            'dimensions': {},
        })

    def _traverse_and_extract(
        self,
        concept: str,
        hierarchy: dict[str, any],
        concept_facts_map: dict[str, list],
        parsed_filing: ParsedFiling,
        statement_facts: list[StatementFact],
        visited: set[str],
        level: int,
        parent: Optional[str]
    ):
        """
        Recursively traverse hierarchy and extract facts.
        
        Uses normalized concept matching (local names only).
        
        Args:
            concept: Current concept to process (from hierarchy)
            hierarchy: Hierarchy structure
            concept_facts_map: Map from LOCAL NAMES to their facts
            parsed_filing: Parsed filing
            statement_facts: List to append facts to (modified in place)
            visited: Set of visited concepts (prevents loops)
            level: Current hierarchy level (depth)
            parent: Parent concept
        """
        if concept in visited:
            return
        
        visited.add(concept)
        
        # Normalize concept to local name for lookup
        concept_local = QNameUtils.get_local_name(concept)
        
        # Get facts for this concept using normalized name
        facts = concept_facts_map.get(concept_local, [])
        
        if facts:
            self.logger.debug(
                f"Matched {len(facts)} facts for concept '{concept}' "
                f"(normalized to '{concept_local}')"
            )
        
        # Get order for this concept
        order = hierarchy['order'].get(concept, 0)
        
        # Add facts to statement
        for fact in facts:
            # Get context reference and look up period info
            context_ref = self._get_attr(fact, 'context_ref')
            period_info = self._get_period_info(context_ref)

            # Extract iXBRL-specific attributes from fact metadata
            fact_metadata = self._get_attr(fact, 'metadata') or {}

            statement_fact = StatementFact(
                concept=concept,  # Keep original concept from hierarchy
                value=self._get_attr(fact, 'value'),
                context_ref=context_ref,
                unit_ref=self._get_attr(fact, 'unit_ref'),
                decimals=self._get_attr(fact, 'decimals'),
                precision=self._get_attr(fact, 'precision'),
                order=order,
                level=level,
                parent_concept=parent,
                metadata={},
                # Period information from context (CRITICAL for calculation verification)
                period_type=period_info.get('period_type'),
                period_start=period_info.get('period_start'),
                period_end=period_info.get('period_end'),
                # Dimensional qualifiers from context (CRITICAL for grouping verification)
                dimensions=period_info.get('dimensions', {}),
                # iXBRL-specific attributes (from inline XBRL instance)
                sign=self._get_attr(fact, 'sign') or fact_metadata.get('sign'),
                scale=self._get_attr(fact, 'scale') or fact_metadata.get('scale'),
                format=self._get_attr(fact, 'format') or fact_metadata.get('format'),
                is_nil=self._get_attr(fact, 'is_nil') or fact_metadata.get('is_nil', False),
                fact_id=self._get_attr(fact, 'id') or fact_metadata.get('id'),
            )
            statement_facts.append(statement_fact)
        
        # Recursively process children
        children = hierarchy['children'].get(concept, [])
        
        # Sort children by order
        children_with_order = [
            (child, hierarchy['order'].get(child, 0))
            for child in children
        ]
        children_with_order.sort(key=lambda x: x[1])
        
        for child, _ in children_with_order:
            self._traverse_and_extract(
                child,
                hierarchy,
                concept_facts_map,
                parsed_filing,
                statement_facts,
                visited,
                level + 1,
                concept
            )