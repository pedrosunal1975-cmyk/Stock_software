# Path: verification/engine/checks_v2/tools/hierarchy/__init__.py
"""
Hierarchy Tools for XBRL Verification

Provides binding checking for calculation hierarchies.

Modules:
- binding_result: Data structures for binding results
- binding_checker: Check if calculations should bind

BINDING RULES (from XBRL spec):
A calculation binds (is checked) ONLY when:
1. The summation item (parent/total) EXISTS in the context
2. At least one contributing item (child) EXISTS in the same context
3. NO inconsistent duplicate facts exist for parent or children
4. All items are c-equal (same context_id)
5. All items are u-equal (same unit)
6. COMPLETENESS: At least threshold % of children found

Usage:
    from verification.engine.checks_v2.tools.hierarchy import (
        BindingChecker,
        BindingResult,
    )

    checker = BindingChecker()
    result = checker.check_binding(
        context_group=context,
        parent_concept='assets',
        children=[('liabilities', 1.0), ('equity', 1.0)]
    )
"""

from .binding_result import BindingResult
from .binding_checker import BindingChecker


__all__ = [
    'BindingResult',
    'BindingChecker',
]
