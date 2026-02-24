# Path: mat_acc/ratio_check/concept_builder.py
"""
Concept Builder

Builds rich ConceptMetadata objects from actual source files.
Combines data from:
- Mapped statements (physical JSON files)
- Parsed filing (parsed.json) via ConceptEnricher
- Database HierarchyNode records via ConceptEnricher
- Taxonomy labels and definitions

Provides enriched concepts to the matching engine.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any

from config_loader import ConfigLoader
from core.logger.ipo_logging import get_process_logger
from core.qname import parse_qname

from process.matcher.models.concept_metadata import (
    ConceptMetadata, ConceptIndex,
)

from loaders import (
    MappedDataLoader,
    ParsedDataLoader,
    MappedFilingEntry,
    ParsedFilingEntry,
)

from .input.concept_enricher import ConceptEnricher
from .input.concept_inference import (
    local_name_to_label,
    infer_balance_type,
    infer_period_type,
)


logger = get_process_logger('concept_builder')


class ConceptBuilder:
    """
    Builds ConceptMetadata from multiple sources.

    Delegates enrichment (parsed.json, database) to ConceptEnricher.
    Inference (balance type, period type) uses shared functions
    from concept_inference.
    """

    def __init__(self, config: ConfigLoader):
        self.config = config
        self.logger = get_process_logger('concept_builder')
        self._mapped_loader = MappedDataLoader(config)
        self._parsed_loader = ParsedDataLoader(config)
        self._enricher = ConceptEnricher(config)

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
        """
        index = ConceptIndex()
        added_concepts: Dict[str, ConceptMetadata] = {}

        # 1. Build from mapped statements
        self._build_from_mapped(mapped_entry, added_concepts)

        # 2. Enrich from parsed.json if available
        if parsed_entry:
            self._enricher.enrich_from_parsed(
                parsed_entry, added_concepts,
            )

        # 3. Enrich from database if available
        if use_database:
            self._enricher.enrich_from_database(
                company=mapped_entry.company,
                market=mapped_entry.market,
                added_concepts=added_concepts,
            )

        for concept in added_concepts.values():
            index.add_concept(concept)

        self.logger.info(
            f"Built {len(index)} concepts for "
            f"{mapped_entry.company}"
        )
        return index

    def _build_from_mapped(
        self,
        mapped_entry: MappedFilingEntry,
        added_concepts: Dict[str, ConceptMetadata],
    ) -> None:
        """Build concepts from mapped statement files."""
        json_files = mapped_entry.available_files.get('json', [])
        for json_file in json_files:
            data = self._load_json(json_file)
            if data:
                self._extract_from_mapped(data, added_concepts)

    def _extract_from_mapped(
        self,
        data: Dict[str, Any],
        added_concepts: Dict[str, ConceptMetadata],
    ) -> None:
        """Extract concepts from mapped statement data."""
        facts = data.get('facts', [])
        for fact in facts:
            concept_name = fact.get('concept', '')
            if not concept_name:
                continue
            if concept_name in added_concepts:
                self._merge_fact_data(
                    added_concepts[concept_name], fact,
                )
                continue
            concept = self._create_from_fact(fact)
            if concept:
                added_concepts[concept.qname] = concept

        hierarchy = data.get('hierarchy', {})
        if hierarchy:
            self._enrich_from_hierarchy(
                hierarchy, added_concepts,
            )

    def _create_from_fact(
        self, fact: Dict[str, Any],
    ) -> Optional[ConceptMetadata]:
        """Create ConceptMetadata from a mapper fact."""
        concept_name = fact.get('concept', '')
        if not concept_name:
            return None

        prefix, local_name = parse_qname(concept_name)

        labels = {}
        generated_label = local_name_to_label(local_name)
        if generated_label:
            labels['standard'] = generated_label

        metadata = fact.get('metadata', {})
        if metadata:
            if metadata.get('label'):
                labels['standard'] = metadata['label']
            if metadata.get('preferred_label'):
                labels['preferred'] = metadata['preferred_label']

        period_type = infer_period_type(local_name)
        balance_type = infer_balance_type(local_name)
        if not period_type:
            period_type = fact.get('period_type')

        level = fact.get('level') or fact.get('depth') or 0
        parent = (
            fact.get('parent_concept')
            or fact.get('parent')
            or ''
        )
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

    def _merge_fact_data(
        self, concept: ConceptMetadata, fact: Dict[str, Any],
    ) -> None:
        """Merge additional fact data into existing concept."""
        if not concept.period_type:
            inferred = infer_period_type(concept.local_name)
            concept.period_type = inferred or fact.get('period_type')
        if not concept.presentation_parent:
            parent = fact.get('parent_concept')
            if parent:
                concept.presentation_parent = parent

    def _enrich_from_hierarchy(
        self,
        hierarchy: Dict[str, Any],
        added_concepts: Dict[str, ConceptMetadata],
    ) -> None:
        """Enrich concepts with hierarchy parent info."""
        parents_map = hierarchy.get('parents', {})
        for qname, concept in added_concepts.items():
            if qname in parents_map:
                concept.presentation_parent = parents_map[qname]

    def supplement_from_ixbrl(
        self,
        ixbrl_facts: list,
        concept_index: ConceptIndex,
    ) -> int:
        """
        Supplement concept index with concepts from iXBRL facts.

        Ensures ALL concepts with reported values in the filing
        are available as matching candidates.
        """
        added = 0
        for fact in ixbrl_facts:
            qname = fact.concept
            if qname in concept_index:
                continue
            prefix, local_name = parse_qname(qname)
            label = local_name_to_label(local_name)
            balance_type = infer_balance_type(local_name)
            period_type = infer_period_type(local_name)
            concept = ConceptMetadata(
                qname=qname,
                local_name=local_name,
                prefix=prefix,
                labels={'standard': label} if label else {},
                balance_type=balance_type,
                period_type=period_type,
            )
            concept_index.add_concept(concept)
            added += 1
        return added

    def build_empty_index(self) -> ConceptIndex:
        """Create an empty concept index."""
        return ConceptIndex()


__all__ = ['ConceptBuilder']
