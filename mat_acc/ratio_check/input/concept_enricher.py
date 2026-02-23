# Path: mat_acc/ratio_check/input/concept_enricher.py
"""
Concept Enricher

Enriches ConceptMetadata from external sources:
- parsed.json (parser output with additional fact data)
- Database HierarchyNode records (enriched labels, hierarchy)

Separated from core concept building to keep each file focused.
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any

from config_loader import ConfigLoader
from core.logger.ipo_logging import get_process_logger
from core.qname import parse_qname

from process.matcher.models.concept_metadata import ConceptMetadata

from database import (
    initialize_engine,
    session_scope,
    ProcessedFiling,
    StatementHierarchy,
    HierarchyNode,
)

from loaders import ParsedFilingEntry

from .concept_inference import (
    local_name_to_label,
    infer_balance_type,
    infer_period_type,
)


logger = get_process_logger('concept_enricher')


class ConceptEnricher:
    """Enriches concepts from parsed.json and database."""

    def __init__(self, config: ConfigLoader):
        self.config = config
        self.logger = get_process_logger('concept_enricher')
        self._db_initialized = False

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

    def _load_json(self, json_path: Path) -> Optional[Dict]:
        """Load JSON content from a file."""
        try:
            if not json_path or not json_path.exists():
                return None
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            self.logger.warning(f"Error loading {json_path}: {e}")
            return None

    def enrich_from_parsed(
        self,
        parsed_entry: ParsedFilingEntry,
        added_concepts: Dict[str, ConceptMetadata],
    ) -> None:
        """Enrich concepts from parsed.json."""
        try:
            json_path = parsed_entry.available_files.get('json')
            parsed_data = self._load_json(json_path)
            if not parsed_data:
                return

            facts = parsed_data.get('facts', [])
            for fact in facts:
                concept_name = fact.get('concept', '')
                if concept_name in added_concepts:
                    self._enrich_concept_from_fact(
                        added_concepts[concept_name], fact,
                    )
                elif concept_name:
                    concept = self._create_from_parsed_fact(fact)
                    if concept:
                        added_concepts[concept.qname] = concept

            taxonomy_info = parsed_data.get('taxonomy', {})
            self._apply_taxonomy_info(taxonomy_info, added_concepts)

        except Exception as e:
            self.logger.warning(
                f"Error enriching from parsed.json: {e}",
            )

    def _create_from_parsed_fact(
        self, fact: Dict[str, Any],
    ) -> Optional[ConceptMetadata]:
        """Create ConceptMetadata from a parsed.json fact."""
        concept_name = fact.get('concept', '')
        if not concept_name:
            return None
        prefix, local_name = parse_qname(concept_name)
        labels = {}
        label = fact.get('label', '')
        if label:
            labels['standard'] = label
        else:
            labels['standard'] = local_name_to_label(local_name)
        return ConceptMetadata(
            qname=concept_name,
            local_name=local_name,
            prefix=prefix,
            labels=labels,
            period_type=(
                'instant' if fact.get('instant') else 'duration'
            ),
        )

    def _enrich_concept_from_fact(
        self, concept: ConceptMetadata, fact: Dict[str, Any],
    ) -> None:
        """Enrich concept with parsed fact data."""
        if not concept.period_type:
            if fact.get('instant'):
                concept.period_type = 'instant'
            elif fact.get('start_date') and fact.get('end_date'):
                concept.period_type = 'duration'
        unit = fact.get('unit', '')
        if unit and not concept.data_type:
            concept.data_type = unit

    def _apply_taxonomy_info(
        self,
        taxonomy_info: Dict[str, Any],
        added_concepts: Dict[str, ConceptMetadata],
    ) -> None:
        """Apply taxonomy information to concepts."""
        elements = taxonomy_info.get('elements', {})
        for qname, info in elements.items():
            if qname not in added_concepts:
                continue
            concept = added_concepts[qname]
            if info.get('definition'):
                concept.definition = info['definition']
            if info.get('balance'):
                concept.balance_type = info['balance']
            if info.get('period_type'):
                concept.period_type = info['period_type']
            if info.get('references'):
                concept.references = info['references']

    def enrich_from_database(
        self,
        company: str,
        market: str,
        added_concepts: Dict[str, ConceptMetadata],
    ) -> None:
        """Enrich concepts from database HierarchyNode records."""
        if not self._ensure_db():
            return
        try:
            with session_scope() as session:
                filing = session.query(ProcessedFiling).filter(
                    ProcessedFiling.company_name.ilike(
                        f"%{company}%",
                    ),
                    ProcessedFiling.market == market.lower(),
                ).first()
                if not filing:
                    return
                hierarchies = session.query(
                    StatementHierarchy,
                ).filter_by(
                    filing_id=filing.filing_id,
                ).all()
                for hierarchy in hierarchies:
                    nodes = session.query(HierarchyNode).filter_by(
                        hierarchy_id=hierarchy.hierarchy_id,
                    ).all()
                    for node in nodes:
                        self._enrich_from_db_node(
                            node, added_concepts,
                        )
        except Exception as e:
            self.logger.warning(
                f"Error enriching from database: {e}",
            )

    def _enrich_from_db_node(
        self,
        node: HierarchyNode,
        added_concepts: Dict[str, ConceptMetadata],
    ) -> None:
        """Enrich or create concept from a database node."""
        if node.concept in added_concepts:
            concept = added_concepts[node.concept]
            if node.standard_label:
                concept.labels['taxonomy'] = node.standard_label
            if node.label_source:
                concept.labels['source'] = node.label_source
            concept.presentation_level = node.level
            if node.parent_mat_acc_id:
                concept.presentation_parent = (
                    node.parent_mat_acc_id
                )
            concept.presentation_order = node.order or 0.0

        elif node.concept:
            prefix, local_name = parse_qname(node.concept)
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
                presentation_parent=(
                    node.parent_mat_acc_id or ''
                ),
                presentation_order=node.order or 0.0,
            )
            added_concepts[node.concept] = concept


__all__ = ['ConceptEnricher']
