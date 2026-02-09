# Path: mat_acc/output/__init__.py
"""
Output Module for mat_acc

Generates human-readable and machine-readable outputs from
the mat_acc database. Creates directory structures following
the map_pro pattern: /{market}/{company}/{form}/{period}/

Primary outputs:
- raw_tree.txt: ASCII tree visualization of statement hierarchies
- raw_tree.json: Machine-readable JSON format

Usage:
    from output import RawTreeGenerator

    generator = RawTreeGenerator()
    generator.generate_for_filing(filing_id)
    # Or generate for all filings:
    generator.generate_all()
"""

from .raw_tree import RawTreeGenerator, RawTreeFormatter

__all__ = ['RawTreeGenerator', 'RawTreeFormatter']
