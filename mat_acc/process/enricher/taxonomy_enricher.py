# Path: mat_acc/process/enricher/taxonomy_enricher.py
"""
Taxonomy Enricher

Enriches hierarchy nodes with standard taxonomy labels.
Preserves company-specific labels while adding authoritative taxonomy labels.

Architecture:
- Uses TaxonomyReader from loaders to access taxonomy libraries
- Updates hierarchy_nodes with standard_label and taxonomy_namespace
- Market agnostic - works with any taxonomy (US-GAAP, IFRS, UK-GAAP, etc.)
- Batch processing for efficiency

Enrichment Flow:
1. Load taxonomy libraries via TaxonomyReader
2. Query hierarchy nodes from database
3. Match concepts to taxonomy elements
4. Update nodes with standard labels
5. Track enrichment statistics

Example:
    from process.enricher import TaxonomyEnricher

    enricher = TaxonomyEnricher()

    # Enrich all nodes for a filing
    result = enricher.enrich_filing(filing_id)
    print(f"Enriched: {result['enriched_count']}")

    # Enrich all filings in database
    results = enricher.enrich_all_filings()
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from config_loader import ConfigLoader
from loaders import TaxonomyDataLoader, TaxonomyReader, TaxonomyInfo
from loaders.constants import parse_concept
from database.models.base import initialize_engine, session_scope
from database.models.processed_filings import ProcessedFiling
from database.models.statement_hierarchies import StatementHierarchy
from database.models.hierarchy_nodes import HierarchyNode


logger = logging.getLogger('enricher.taxonomy')


# ==============================================================================
# DATA CLASSES
# ==============================================================================

@dataclass
class EnrichmentResult:
    """Result of enrichment operation."""
    filing_id: str
    total_nodes: int = 0
    enriched_count: int = 0
    already_enriched: int = 0
    no_match_count: int = 0
    error_count: int = 0
    errors: list = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate enrichment success rate."""
        if self.total_nodes == 0:
            return 0.0
        return (self.enriched_count / self.total_nodes) * 100


# ==============================================================================
# TAXONOMY ENRICHER
# ==============================================================================

class TaxonomyEnricher:
    """
    Enriches hierarchy nodes with standard taxonomy labels.

    Loads taxonomy libraries and matches concepts to their official labels.
    Preserves company-specific labels in the 'label' column while adding
    standard taxonomy labels to 'standard_label'.

    Example:
        enricher = TaxonomyEnricher()

        # Enrich single filing
        result = enricher.enrich_filing(filing_id)

        # Enrich all filings
        results = enricher.enrich_all_filings()

        # Get enrichment summary
        summary = enricher.get_summary()
    """

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize taxonomy enricher.

        Args:
            config: ConfigLoader instance. If None, creates new instance.
        """
        self.config = config if config else ConfigLoader()

        # Initialize loaders
        self.taxonomy_loader = TaxonomyDataLoader(self.config)
        self.taxonomy_reader = TaxonomyReader(self.config)

        # Cache loaded taxonomy info
        self._taxonomy_cache: dict[str, TaxonomyInfo] = {}

        # Ensure database is initialized
        initialize_engine()

        logger.info("TaxonomyEnricher initialized")

    def enrich_all_filings(self, batch_size: int = 100) -> list[EnrichmentResult]:
        """
        Enrich all filings in the database.

        Args:
            batch_size: Number of nodes to process per batch

        Returns:
            List of EnrichmentResult for each filing
        """
        logger.info("Starting enrichment for all filings")

        results = []

        with session_scope() as session:
            filings = session.query(ProcessedFiling).all()

            for filing in filings:
                try:
                    result = self._enrich_filing_nodes(
                        session,
                        filing.filing_id,
                        batch_size
                    )
                    results.append(result)
                    session.commit()

                    logger.info(
                        f"Enriched {filing.company_name}/{filing.form_type}: "
                        f"{result.enriched_count}/{result.total_nodes} nodes"
                    )

                except Exception as e:
                    logger.error(f"Error enriching {filing.filing_id}: {e}")
                    session.rollback()
                    results.append(EnrichmentResult(
                        filing_id=str(filing.filing_id),
                        errors=[str(e)]
                    ))

        total_enriched = sum(r.enriched_count for r in results)
        logger.info(f"Enrichment complete: {total_enriched} nodes enriched")

        return results

    def enrich_filing(
        self,
        filing_id: str,
        batch_size: int = 100
    ) -> EnrichmentResult:
        """
        Enrich all nodes for a specific filing.

        Args:
            filing_id: UUID of the filing to enrich
            batch_size: Number of nodes to process per batch

        Returns:
            EnrichmentResult with statistics
        """
        logger.info(f"Enriching filing: {filing_id}")

        with session_scope() as session:
            result = self._enrich_filing_nodes(session, filing_id, batch_size)
            session.commit()

        return result

    def _enrich_filing_nodes(
        self,
        session,
        filing_id: str,
        batch_size: int
    ) -> EnrichmentResult:
        """
        Internal method to enrich nodes for a filing.

        Args:
            session: Database session
            filing_id: Filing ID
            batch_size: Batch size for processing

        Returns:
            EnrichmentResult
        """
        result = EnrichmentResult(filing_id=str(filing_id))

        # Get all hierarchies for this filing
        hierarchies = session.query(StatementHierarchy).filter_by(
            filing_id=filing_id
        ).all()

        if not hierarchies:
            logger.warning(f"No hierarchies found for filing: {filing_id}")
            return result

        # Get all nodes for these hierarchies
        hierarchy_ids = [h.hierarchy_id for h in hierarchies]
        nodes = session.query(HierarchyNode).filter(
            HierarchyNode.hierarchy_id.in_(hierarchy_ids)
        ).all()

        result.total_nodes = len(nodes)

        if not nodes:
            return result

        # Collect unique concepts for batch lookup
        concepts = set()
        for node in nodes:
            if node.concept:
                concepts.add(node.concept)

        # Get labels for all concepts at once
        labels_map = self._get_labels_for_concepts(list(concepts))

        # Update nodes
        for node in nodes:
            try:
                if node.standard_label:
                    # Already enriched
                    result.already_enriched += 1
                    continue

                # Skip root structural nodes (not real concepts)
                if node.concept and node.concept.startswith('root:'):
                    result.no_match_count += 1
                    continue

                if node.concept in labels_map:
                    # Found in standard taxonomy
                    label_info = labels_map[node.concept]
                    node.standard_label = label_info['label']
                    node.label_source = label_info['source']
                    node.taxonomy_namespace = label_info['namespace']
                    result.enriched_count += 1
                else:
                    # Company extension - generate label from concept name
                    generated_label = self._generate_label_from_concept(node.concept)
                    if generated_label:
                        node.standard_label = generated_label
                        node.label_source = 'generated'
                        result.enriched_count += 1
                    else:
                        result.no_match_count += 1

            except Exception as e:
                logger.warning(f"Error enriching node {node.node_id}: {e}")
                result.error_count += 1
                result.errors.append(str(e))

        return result

    def _get_labels_for_concepts(
        self,
        concepts: list[str]
    ) -> dict[str, dict]:
        """
        Get labels for a list of concepts from all loaded taxonomies.

        Args:
            concepts: List of concept names (may include namespace prefix)

        Returns:
            Dictionary mapping concept -> {label, source, namespace}
        """
        results = {}

        # Load all available taxonomies
        self._ensure_taxonomies_loaded()

        for concept in concepts:
            # Extract namespace prefix and local name
            prefix, local_name = parse_concept(concept)

            # Try to find label in taxonomies
            for tax_name, tax_info in self._taxonomy_cache.items():
                label = tax_info.get_label(local_name)
                if label:
                    results[concept] = {
                        'label': label,
                        'source': tax_name,  # Taxonomy name as source
                        'namespace': tax_info.namespace or tax_name,
                    }
                    break

        return results

    def _ensure_taxonomies_loaded(self) -> None:
        """Load all available taxonomies into cache if not already loaded."""
        if self._taxonomy_cache:
            return  # Already loaded

        logger.info("Loading taxonomy libraries")

        taxonomies = self.taxonomy_loader.discover_all_taxonomies()

        for tax_entry in taxonomies:
            try:
                tax_info = self.taxonomy_reader.read_taxonomy(tax_entry)
                if tax_info:
                    self._taxonomy_cache[tax_entry.taxonomy_name] = tax_info
                    logger.debug(
                        f"Loaded {tax_entry.taxonomy_name}: "
                        f"{tax_info.element_count} elements, "
                        f"{tax_info.label_count} labels"
                    )
            except Exception as e:
                logger.warning(f"Error loading {tax_entry.taxonomy_name}: {e}")

        logger.info(f"Loaded {len(self._taxonomy_cache)} taxonomies")

    def _generate_label_from_concept(self, concept: str) -> Optional[str]:
        """
        Generate a human-readable label from a concept name.

        Converts camelCase/PascalCase to "Title Case With Spaces".
        Used for company extensions that don't have standard taxonomy labels.

        Examples:
            tescoplc_OwnSharesPurchasedForCancellation -> Own Shares Purchased For Cancellation
            plug_OperatingLeaseLiabilityPayments -> Operating Lease Liability Payments

        Args:
            concept: Concept string with prefix (e.g., 'company_ConceptName')

        Returns:
            Human-readable label or None if concept is invalid
        """
        if not concept:
            return None

        # Extract local name (remove prefix)
        _, local_name = parse_concept(concept)

        if not local_name:
            return None

        # Convert camelCase/PascalCase to spaces
        # Insert space before uppercase letters that follow lowercase
        label = re.sub(r'([a-z])([A-Z])', r'\1 \2', local_name)
        # Insert space before uppercase letters in sequences (e.g., XMLParser -> XML Parser)
        label = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', label)

        return label

    def get_summary(self) -> dict:
        """
        Get summary of enricher state.

        Returns:
            Dictionary with enricher statistics
        """
        self._ensure_taxonomies_loaded()

        total_elements = sum(
            info.element_count for info in self._taxonomy_cache.values()
        )
        total_labels = sum(
            info.label_count for info in self._taxonomy_cache.values()
        )

        return {
            'taxonomies_loaded': len(self._taxonomy_cache),
            'taxonomy_names': list(self._taxonomy_cache.keys()),
            'total_elements': total_elements,
            'total_labels': total_labels,
        }

    def clear_cache(self) -> None:
        """Clear the taxonomy cache."""
        self._taxonomy_cache.clear()
        self.taxonomy_reader.clear_cache()
        logger.info("Enricher cache cleared")


__all__ = ['TaxonomyEnricher', 'EnrichmentResult']
