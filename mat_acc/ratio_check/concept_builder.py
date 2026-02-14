# Path: mat_acc/ratio_check/concept_builder.py
"""
Concept Builder

Builds rich ConceptMetadata objects from actual source files.
Combines data from:
- Mapped statements (physical JSON files)
- Parsed filing (parsed.json)
- Database HierarchyNode records
- Taxonomy labels and definitions

Provides enriched concepts to the matching engine.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any

from config_loader import ConfigLoader

# Import IPO logging (PROCESS layer for concept building work)
from core.logger.ipo_logging import get_process_logger

# Import matcher models
from process.matcher.models.concept_metadata import ConceptMetadata, ConceptIndex

# Import loaders for reading source files
from loaders import (
    MappedDataLoader,
    ParsedDataLoader,
    MappedFilingEntry,
    ParsedFilingEntry,
)


# Database imports for enriched data
from database import (
    initialize_engine,
    session_scope,
    ProcessedFiling,
    StatementHierarchy,
    HierarchyNode,
)


# Use IPO-aware logger (PROCESS layer)
logger = get_process_logger('concept_builder')


class ConceptBuilder:
    """
    Builds ConceptMetadata from multiple sources.

    Combines data from mapped statements, parsed filings, and database
    to create rich ConceptMetadata objects suitable for matching.

    Example:
        builder = ConceptBuilder(config)

        # Build from mapped filing entry
        index = builder.build_from_filing(
            mapped_entry=mapped_entry,
            parsed_entry=parsed_entry,
        )

        # Use with matcher
        for concept in index.get_all_concepts():
            print(f"{concept.qname}: {concept.get_label('standard')}")
    """

    def __init__(self, config: ConfigLoader):
        """
        Initialize concept builder.

        Args:
            config: ConfigLoader instance
        """
        self.config = config
        self.logger = get_process_logger('concept_builder')
        self._db_initialized = False

        # Loaders for path discovery (doorkeepers)
        self._mapped_loader = MappedDataLoader(config)
        self._parsed_loader = ParsedDataLoader(config)

    def _load_json(self, json_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load JSON content from a file.

        Engine responsibility: read content from paths provided by loaders.

        Args:
            json_path: Path to JSON file

        Returns:
            Parsed JSON data or None if loading fails
        """
        try:
            if not json_path or not json_path.exists():
                return None

            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON decode error in {json_path}: {e}")
            return None
        except Exception as e:
            self.logger.warning(f"Error loading {json_path}: {e}")
            return None

    def _ensure_db(self) -> bool:
        """Initialize database connection if needed."""
        if self._db_initialized:
            return True

        try:
            db_url = self.config.get_db_connection_string()
            initialize_engine(db_url)
            self._db_initialized = True
            return True
        except Exception as e:
            self.logger.warning(f"Database not available: {e}")
            return False

    def build_from_filing(
        self,
        mapped_entry: MappedFilingEntry,
        parsed_entry: Optional[ParsedFilingEntry] = None,
        use_database: bool = True,
    ) -> ConceptIndex:
        """
        Build ConceptIndex from a filing.

        Combines multiple data sources:
        1. Mapped statement files (JSON)
        2. Parsed filing (parsed.json) for fact values
        3. Database HierarchyNode for enriched labels

        Args:
            mapped_entry: MappedFilingEntry with file paths
            parsed_entry: Optional ParsedFilingEntry for additional data
            use_database: Whether to use database enrichment

        Returns:
            ConceptIndex with all concepts from the filing
        """
        index = ConceptIndex()

        # Track concepts we've added
        added_concepts: Dict[str, ConceptMetadata] = {}

        # 1. Build from mapped statements
        self._build_from_mapped(mapped_entry, added_concepts)

        # 2. Enrich from parsed.json if available
        if parsed_entry:
            self._enrich_from_parsed(parsed_entry, added_concepts)

        # 3. Enrich from database if available
        if use_database and self._ensure_db():
            self._enrich_from_database(
                company=mapped_entry.company,
                market=mapped_entry.market,
                added_concepts=added_concepts,
            )

        # Add all concepts to index
        for concept in added_concepts.values():
            index.add_concept(concept)

        self.logger.info(
            f"Built {len(index)} concepts for {mapped_entry.company}"
        )
        return index

    def _build_from_mapped(
        self,
        mapped_entry: MappedFilingEntry,
        added_concepts: Dict[str, ConceptMetadata]
    ) -> None:
        """
        Build concepts from mapped statement files.

        Args:
            mapped_entry: Mapped filing entry
            added_concepts: Dictionary to add concepts to
        """
        json_files = mapped_entry.available_files.get('json', [])

        for json_file in json_files:
            # Engine reads content directly; loader only provided the path
            data = self._load_json(json_file)
            if data:
                self._extract_concepts_from_mapped(data, added_concepts)

    def _extract_concepts_from_mapped(
        self,
        data: Dict[str, Any],
        added_concepts: Dict[str, ConceptMetadata]
    ) -> None:
        """
        Extract concepts from mapped statement data.

        Reads the mapper output structure which contains:
        - facts: Array of fact objects with concept, value, level, etc.
        - hierarchy: Parent-child relationships

        Args:
            data: Mapped statement JSON data
            added_concepts: Dictionary to add concepts to
        """
        # Mapper outputs facts array, not nodes
        facts = data.get('facts', [])

        for fact in facts:
            concept_name = fact.get('concept', '')
            if not concept_name:
                continue

            # Skip if already added
            if concept_name in added_concepts:
                # Update with additional data
                self._merge_fact_data(added_concepts[concept_name], fact)
                continue

            # Create new concept from fact
            concept = self._create_concept_from_fact(fact)
            if concept:
                added_concepts[concept.qname] = concept

        # Also check hierarchy for additional concept info
        hierarchy = data.get('hierarchy', {})
        if hierarchy:
            self._enrich_from_hierarchy(hierarchy, added_concepts)

    def _create_concept_from_fact(self, fact: Dict[str, Any]) -> Optional[ConceptMetadata]:
        """
        Create ConceptMetadata from a mapper fact dictionary.

        Args:
            fact: Fact data from mapper output

        Returns:
            ConceptMetadata or None
        """
        concept_name = fact.get('concept', '')
        if not concept_name:
            return None

        # Parse qname using existing utility - handles all formats:
        # "us-gaap:Assets", "us-gaap_Assets", "{namespace}Assets"
        prefix, local_name = self._parse_qname(concept_name)

        # Generate label from local_name (e.g., "AssetsCurrent" -> "Assets Current")
        labels = {}
        generated_label = self._local_name_to_label(local_name)
        if generated_label:
            labels['standard'] = generated_label

        # Check metadata for additional labels
        metadata = fact.get('metadata', {})
        if metadata:
            if metadata.get('label'):
                labels['standard'] = metadata['label']
            if metadata.get('preferred_label'):
                labels['preferred'] = metadata['preferred_label']

        # Get period type directly from fact (mapper provides this)
        period_type = fact.get('period_type')

        # Infer balance type from concept name
        balance_type = self._infer_balance_type(local_name, fact)

        # If period_type not in fact, infer from name
        if not period_type:
            period_type = self._infer_period_type(local_name, fact)

        # Build hierarchy info - mapper uses 'depth' or 'level' interchangeably
        level = fact.get('level') or fact.get('depth') or 0
        parent = fact.get('parent_concept') or fact.get('parent') or ''

        # "root:" prefix = mapper-generated section headers, not XBRL facts
        # Mark as abstract so rejection rules filter them out
        is_abstract = (prefix == 'root')

        return ConceptMetadata(
            qname=concept_name,
            local_name=local_name,
            prefix=prefix,
            labels=labels,
            balance_type=balance_type,
            period_type=period_type,
            is_abstract=is_abstract,
            presentation_level=level,
            presentation_parent=parent,
        )

    def _parse_qname(self, qname_str: str) -> tuple[str, str]:
        """
        Parse QName string - handles MULTIPLE formats.

        Mirrors the logic from mapper/components/qname_utils.py QNameUtils.parse()
        to avoid cross-module import issues.

        Supported formats:
        1. Clark notation: {http://fasb.org/us-gaap/2024}Assets
        2. Prefix format: us-gaap:Assets
        3. Underscore format: us-gaap_Assets
        4. Simple name: Assets

        Args:
            qname_str: QName in any format

        Returns:
            Tuple of (namespace, local_name)
        """
        if not qname_str:
            return ('', '')

        qname_str = str(qname_str).strip()

        # Format 1: Clark notation {namespace}localName
        if qname_str.startswith('{'):
            try:
                parts = qname_str.split('}', 1)
                if len(parts) == 2:
                    namespace = parts[0][1:]  # Remove leading {
                    local_name = parts[1]
                    return (namespace, local_name)
            except:
                pass

        # Format 2: Prefix format namespace:localName
        if ':' in qname_str:
            namespace, local_name = qname_str.split(':', 1)
            return (namespace, local_name)

        # Format 3: Underscore format namespace_LocalName
        # (LocalName typically starts with uppercase)
        if '_' in qname_str:
            parts = qname_str.rsplit('_', 1)
            if len(parts) == 2 and parts[1] and parts[1][0].isupper():
                return (parts[0], parts[1])

        # Format 4: Simple name (no namespace)
        return ('', qname_str)

    def _local_name_to_label(self, local_name: str) -> str:
        """
        Convert local name to human-readable label.

        E.g., "AssetsCurrent" -> "Assets Current"
             "TotalLiabilities" -> "Total Liabilities"
        """
        import re
        # Insert space before uppercase letters
        spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', local_name)
        # Handle consecutive uppercase (e.g., "USGaap" -> "US Gaap")
        spaced = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', spaced)
        return spaced

    def _merge_fact_data(
        self,
        concept: ConceptMetadata,
        fact: Dict[str, Any]
    ) -> None:
        """Merge additional fact data into existing concept."""
        # Update period type if not set
        if not concept.period_type and fact.get('period_type'):
            concept.period_type = fact['period_type']

        # Update parent if not set
        if not concept.presentation_parent and fact.get('parent_concept'):
            concept.presentation_parent = fact['parent_concept']

    def _enrich_from_hierarchy(
        self,
        hierarchy: Dict[str, Any],
        added_concepts: Dict[str, ConceptMetadata]
    ) -> None:
        """Enrich concepts with hierarchy information."""
        # Get parent-child relationships
        children_map = hierarchy.get('children', {})
        parents_map = hierarchy.get('parents', {})

        for qname, concept in added_concepts.items():
            # Add parent info
            if qname in parents_map:
                concept.presentation_parent = parents_map[qname]

    def _create_concept_from_node(self, node: Dict[str, Any]) -> Optional[ConceptMetadata]:
        """
        Create ConceptMetadata from a node dictionary.

        Args:
            node: Node data from mapped statement

        Returns:
            ConceptMetadata or None
        """
        concept_name = node.get('concept', '')
        if not concept_name:
            return None

        # Parse qname using existing utility
        prefix, local_name = self._parse_qname(concept_name)

        # Get labels
        labels = {}
        label = node.get('label', '')
        if label:
            labels['standard'] = label

        standard_label = node.get('standard_label', '')
        if standard_label:
            labels['taxonomy'] = standard_label

        # Get other attributes
        node_type = node.get('node_type', 'line_item')
        is_abstract = node_type == 'abstract'

        # Determine balance/period type from concept name heuristics
        balance_type = self._infer_balance_type(local_name, node)
        period_type = self._infer_period_type(local_name, node)

        # Build hierarchy info - check multiple possible keys
        level = node.get('level') or node.get('depth') or 0
        parent = node.get('parent_mat_acc_id') or node.get('parent_concept') or node.get('parent') or ''

        return ConceptMetadata(
            qname=concept_name,
            local_name=local_name,
            prefix=prefix,
            labels=labels,
            balance_type=balance_type,
            period_type=period_type,
            is_abstract=is_abstract,
            presentation_level=level,
            presentation_parent=parent,
        )

    def _merge_node_data(
        self,
        concept: ConceptMetadata,
        node: Dict[str, Any]
    ) -> None:
        """
        Merge additional node data into existing concept.

        Args:
            concept: Existing concept to update
            node: Node data with additional info
        """
        # Add labels if not present
        label = node.get('label', '')
        if label and 'standard' not in concept.labels:
            concept.labels['standard'] = label

        standard_label = node.get('standard_label', '')
        if standard_label and 'taxonomy' not in concept.labels:
            concept.labels['taxonomy'] = standard_label

    def _enrich_from_parsed(
        self,
        parsed_entry: ParsedFilingEntry,
        added_concepts: Dict[str, ConceptMetadata]
    ) -> None:
        """
        Enrich concepts from parsed.json.

        Adds fact values, context info, and additional metadata.

        Args:
            parsed_entry: Parsed filing entry
            added_concepts: Dictionary of concepts to enrich
        """
        try:
            # Get path from loader, engine reads content directly
            json_path = parsed_entry.available_files.get('json')
            parsed_data = self._load_json(json_path)
            if not parsed_data:
                return

            # Extract facts
            facts = parsed_data.get('facts', [])
            for fact in facts:
                concept_name = fact.get('concept', '')
                if concept_name in added_concepts:
                    self._enrich_concept_from_fact(
                        added_concepts[concept_name],
                        fact
                    )
                elif concept_name:
                    # Create new concept from parsed fact
                    concept = self._create_concept_from_parsed_fact(fact)
                    if concept:
                        added_concepts[concept.qname] = concept

            # Extract taxonomy info
            taxonomy_info = parsed_data.get('taxonomy', {})
            self._apply_taxonomy_info(taxonomy_info, added_concepts)

        except Exception as e:
            self.logger.warning(f"Error enriching from parsed.json: {e}")

    def _create_concept_from_parsed_fact(self, fact: Dict[str, Any]) -> Optional[ConceptMetadata]:
        """Create ConceptMetadata from a parsed.json fact."""
        concept_name = fact.get('concept', '')
        if not concept_name:
            return None

        # Parse qname using existing utility
        prefix, local_name = self._parse_qname(concept_name)

        labels = {}
        label = fact.get('label', '')
        if label:
            labels['standard'] = label
        else:
            # Generate label from local name
            labels['standard'] = self._local_name_to_label(local_name)

        return ConceptMetadata(
            qname=concept_name,
            local_name=local_name,
            prefix=prefix,
            labels=labels,
            period_type='instant' if fact.get('instant') else 'duration',
        )

    def _enrich_concept_from_fact(
        self,
        concept: ConceptMetadata,
        fact: Dict[str, Any]
    ) -> None:
        """Enrich concept with fact data."""
        # Add period type if not set
        if not concept.period_type:
            if fact.get('instant'):
                concept.period_type = 'instant'
            elif fact.get('start_date') and fact.get('end_date'):
                concept.period_type = 'duration'

        # Add unit info to data_type
        unit = fact.get('unit', '')
        if unit and not concept.data_type:
            concept.data_type = unit

    def _apply_taxonomy_info(
        self,
        taxonomy_info: Dict[str, Any],
        added_concepts: Dict[str, ConceptMetadata]
    ) -> None:
        """Apply taxonomy information to concepts."""
        elements = taxonomy_info.get('elements', {})

        for qname, element_info in elements.items():
            if qname in added_concepts:
                concept = added_concepts[qname]

                # Add definition
                definition = element_info.get('definition', '')
                if definition:
                    concept.definition = definition

                # Add balance type
                balance = element_info.get('balance', '')
                if balance:
                    concept.balance_type = balance

                # Add period type
                period = element_info.get('period_type', '')
                if period:
                    concept.period_type = period

                # Add references
                refs = element_info.get('references', [])
                if refs:
                    concept.references = refs

    def _enrich_from_database(
        self,
        company: str,
        market: str,
        added_concepts: Dict[str, ConceptMetadata]
    ) -> None:
        """
        Enrich concepts from database HierarchyNode records.

        Database stores enriched labels and hierarchy relationships.

        Args:
            company: Company name
            market: Market identifier
            added_concepts: Dictionary of concepts to enrich
        """
        try:
            with session_scope() as session:
                # Find the filing
                filing = session.query(ProcessedFiling).filter(
                    ProcessedFiling.company_name.ilike(f"%{company}%"),
                    ProcessedFiling.market == market.lower(),
                ).first()

                if not filing:
                    return

                # Get all hierarchies
                hierarchies = session.query(StatementHierarchy).filter_by(
                    filing_id=filing.filing_id
                ).all()

                # Get all nodes
                for hierarchy in hierarchies:
                    nodes = session.query(HierarchyNode).filter_by(
                        hierarchy_id=hierarchy.hierarchy_id
                    ).all()

                    for node in nodes:
                        self._enrich_from_db_node(node, added_concepts)

        except Exception as e:
            self.logger.warning(f"Error enriching from database: {e}")

    def _enrich_from_db_node(
        self,
        node: HierarchyNode,
        added_concepts: Dict[str, ConceptMetadata]
    ) -> None:
        """Enrich concepts from a database node."""
        if node.concept in added_concepts:
            concept = added_concepts[node.concept]

            # Add standard label from taxonomy
            if node.standard_label:
                concept.labels['taxonomy'] = node.standard_label

            # Add label source info
            if node.label_source:
                concept.labels['source'] = node.label_source

            # Add hierarchy info
            concept.presentation_level = node.level
            if node.parent_mat_acc_id:
                concept.presentation_parent = node.parent_mat_acc_id

            # Add position info
            concept.presentation_order = node.order or 0.0

        elif node.concept:
            # Create new concept from db node using existing utility
            prefix, local_name = self._parse_qname(node.concept)

            labels = {'standard': node.label}
            if node.standard_label:
                labels['taxonomy'] = node.standard_label

            concept = ConceptMetadata(
                qname=node.concept,
                local_name=local_name,
                prefix=prefix,
                labels=labels,
                is_abstract=node.node_type == 'abstract',
                presentation_level=node.level,
                presentation_parent=node.parent_mat_acc_id or '',
                presentation_order=node.order or 0.0,
            )
            added_concepts[node.concept] = concept

    def _infer_balance_type(
        self,
        local_name: str,
        node: Dict[str, Any]
    ) -> Optional[str]:
        """
        Infer balance type from concept name.

        Uses heuristics based on common XBRL naming patterns.
        Priority order prevents misclassification of compound names:
        - "IncomeTaxExpenseBenefit" -> debit (expense overrides income)
        - "NetIncomeLoss" -> credit (income is primary concept)
        - "CostOfGoodsSold" -> debit (cost is primary concept)
        """
        local_lower = local_name.lower()

        # Strong debit indicators - checked FIRST because they override
        # generic credit keywords in compound names like "IncomeTaxExpense"
        strong_debit = [
            'expense', 'cost', 'purchase', 'payment',
            'depreciation', 'amortization', 'prepaid',
        ]
        for pattern in strong_debit:
            if pattern in local_lower:
                return 'debit'

        # Credit indicators - primary accounting concepts
        credit_patterns = [
            'liabilities', 'liability', 'revenue', 'income', 'gain',
            'payable', 'equity', 'capital', 'retained', 'earnings',
            'accumulated', 'provision', 'reserve', 'profit',
        ]
        for pattern in credit_patterns:
            if pattern in local_lower:
                return 'credit'

        # Remaining debit indicators
        debit_patterns = [
            'assets', 'loss', 'receivable',
            'inventory', 'equipment', 'property',
            'dividend',
        ]
        for pattern in debit_patterns:
            if pattern in local_lower:
                return 'debit'

        return None

    def _infer_period_type(
        self,
        local_name: str,
        node: Dict[str, Any]
    ) -> Optional[str]:
        """
        Infer period type from concept name.

        Uses heuristics based on common patterns.
        Priority order prevents misclassification:
        - "PaymentsToAcquirePropertyPlantAndEquipment" -> duration
          (cash flow action word overrides balance sheet noun)
        """
        local_lower = local_name.lower()

        # Strong duration indicators - checked FIRST because cash flow
        # action words override balance sheet nouns in compound names
        # like "PaymentsToAcquirePropertyPlantAndEquipment"
        strong_duration = [
            'payment', 'proceeds', 'purchase', 'repayment',
            'issuance', 'acquisition',
        ]
        for pattern in strong_duration:
            if pattern in local_lower:
                return 'duration'

        # Instant indicators (balance sheet items)
        instant_patterns = [
            'assets', 'liabilities', 'equity', 'balance',
            'receivable', 'payable', 'inventory', 'cash',
            'property', 'equipment', 'accumulated',
        ]
        for pattern in instant_patterns:
            if pattern in local_lower:
                return 'instant'

        # Duration indicators (income statement items)
        duration_patterns = [
            'revenue', 'expense', 'income', 'cost', 'sales',
            'gain', 'loss', 'earnings', 'profit', 'margin',
        ]
        for pattern in duration_patterns:
            if pattern in local_lower:
                return 'duration'

        return None

    def build_empty_index(self) -> ConceptIndex:
        """Create an empty concept index."""
        return ConceptIndex()


__all__ = ['ConceptBuilder']
