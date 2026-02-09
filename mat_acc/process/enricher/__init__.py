# Path: mat_acc/process/enricher/__init__.py
"""
Enricher Package

Enriches hierarchy nodes with standard taxonomy labels.
Uses TaxonomyReader to look up official labels from standard taxonomies.

Architecture:
- TaxonomyEnricher: Main enrichment logic
- Preserves company-specific labels while adding standard labels
- Market agnostic (works with US-GAAP, IFRS, UK-GAAP, etc.)

Example:
    from process.enricher import TaxonomyEnricher

    enricher = TaxonomyEnricher()

    # Enrich a single filing
    enricher.enrich_filing(filing_id)

    # Enrich all filings
    enricher.enrich_all_filings()
"""

from .taxonomy_enricher import TaxonomyEnricher

__all__ = ['TaxonomyEnricher']
