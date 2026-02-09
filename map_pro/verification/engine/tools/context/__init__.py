# Path: verification/engine/checks_v2/tools/context/__init__.py
"""
Context Tools for XBRL Verification

Provides context classification, matching, and grouping capabilities.

Modules:
- classifier: Classify contexts as dimensional or default
- matcher: Match contexts for compatibility (C-Equal, period, year)
- grouper: Group facts by context_id for verification

These tools are STATELESS (classifier, matcher) or STATEFUL containers (grouper)
that can be used across all processing stages.

Usage:
    from verification.engine.checks_v2.tools.context import (
        ContextClassifier,
        ContextMatcher,
        ContextGrouper,
        ContextGroup,
    )

    # Classify context
    classifier = ContextClassifier()
    is_dim = classifier.is_dimensional('Duration_2024_axis_member')

    # Match contexts
    matcher = ContextMatcher()
    compatible = matcher.is_period_compatible(ctx1, ctx2)

    # Group facts
    grouper = ContextGrouper()
    grouper.add_fact('assets', 1000000, context_id='c-1')
"""

from .classifier import ContextClassifier
from .matcher import ContextMatcher
from .grouper import ContextGroup, ContextGrouper


__all__ = [
    'ContextClassifier',
    'ContextMatcher',
    'ContextGroup',
    'ContextGrouper',
]
