# Path: mat_acc/process/__init__.py
"""
Process Layer for mat_acc (Mathematical Accountancy)

The PROCESS layer handles all financial analysis operations:
- hierarchy/ - Statement hierarchy building from linkbases
- enricher/ - Taxonomy enrichment with standard labels
- ratios/ - Financial ratio calculations (Levels 1-4)
- normalizer/ - Statement normalization for comparison
- analysis/ - Analysis coordination and aggregation

All components follow the IPO pattern:
- Read from INPUT layer (loaders)
- Process data (calculations, transformations)
- Prepare for OUTPUT layer (reporters, exporters)
"""

from process.hierarchy import HierarchyBuilder, StatementHierarchy, HierarchyNode
from process.enricher import TaxonomyEnricher

__all__ = [
    'HierarchyBuilder',
    'StatementHierarchy',
    'HierarchyNode',
    'TaxonomyEnricher',
]
