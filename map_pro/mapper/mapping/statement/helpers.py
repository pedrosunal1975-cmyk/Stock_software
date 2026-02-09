# Path: mapping/statement/helpers.py
"""
Statement Builder Helpers

Utility functions for statement building.

DESIGN PRINCIPLES:
- Pure functions where possible
- No business logic (just helpers)
- Clear, focused responsibilities
"""

import logging
from typing import Optional
from datetime import date
from collections import Counter

from ...loaders.parser_output import ParsedFiling
from ...mapping.models.context import Context


logger = logging.getLogger('mapping.statement.helpers')


def determine_statement_date(
    parsed_filing: ParsedFiling,
    role_uri: Optional[str] = None
) -> Optional[date]:
    """
    Determine the statement date from contexts.
    
    Finds the most common end_date or instant date in contexts,
    which represents the reporting date.
    
    Args:
        parsed_filing: Parsed filing with contexts
        role_uri: Optional role URI (reserved for future filtering)
        
    Returns:
        Most common date or None
        
    Example:
        >>> date = determine_statement_date(parsed_filing)
        >>> print(date)  # 2024-12-31
    """
    dates = []
    
    for context in parsed_filing.contexts:
        if context.period_type == 'instant' and context.instant:
            dates.append(context.instant)
        elif context.period_type == 'duration' and context.end_date:
            dates.append(context.end_date)
    
    if not dates:
        logger.debug("No dates found in contexts")
        return None
    
    # Return most common date
    date_counts = Counter(dates)
    most_common_date, count = date_counts.most_common(1)[0]
    
    logger.debug(
        f"Statement date determined: {most_common_date} "
        f"(appears in {count}/{len(dates)} contexts)"
    )
    
    return most_common_date


def determine_period_type(
    concept: str,
    parsed_filing: ParsedFiling
) -> Optional[str]:
    """
    Determine expected period type for a concept.
    
    Infers from actual facts with this concept name.
    
    Args:
        concept: Concept QName
        parsed_filing: Parsed filing with facts and contexts
        
    Returns:
        Most common period type ('instant', 'duration', 'forever') or None
        
    Example:
        >>> period_type = determine_period_type('us-gaap:Assets', parsed_filing)
        >>> print(period_type)  # 'instant'
    """
    # Find facts with this concept
    concept_facts = [f for f in parsed_filing.facts if f.name == concept]
    
    if not concept_facts:
        logger.debug(f"No facts found for concept: {concept}")
        return None
    
    # Build context map
    context_map = {c.id: c for c in parsed_filing.contexts}
    
    # Collect period types
    period_types = []
    for fact in concept_facts:
        context = context_map.get(fact.context_ref)
        if context:
            period_types.append(context.period_type)
    
    if not period_types:
        logger.debug(f"No contexts found for concept facts: {concept}")
        return None
    
    # Return most common period type
    type_counts = Counter(period_types)
    most_common_type, count = type_counts.most_common(1)[0]
    
    logger.debug(
        f"Period type for {concept}: {most_common_type} "
        f"({count}/{len(period_types)} facts)"
    )
    
    return most_common_type


def build_context_map(parsed_filing: ParsedFiling) -> dict[str, Context]:
    """
    Build quick lookup map from context ID to Context object.
    
    Args:
        parsed_filing: Parsed filing with contexts
        
    Returns:
        Dictionary mapping context IDs to Context objects
        
    Example:
        >>> context_map = build_context_map(parsed_filing)
        >>> context = context_map.get('c_2024_Q4')
    """
    context_map = {}
    
    for context in parsed_filing.contexts:
        if isinstance(context, Context):
            context_map[context.id] = context
    
    logger.debug(f"Built context map with {len(context_map)} contexts")
    
    return context_map


__all__ = [
    'determine_statement_date',
    'determine_period_type',
    'build_context_map',
]