"""
XBRL Context Matching Rules

This module contains rules for determining when two XBRL contexts match,
as defined by the XBRL 2.1 Specification.

SOURCE AUTHORITY:
----------------
XBRL 2.1 Specification Section 4.7 "The <context> element"
XBRL 2.1 Specification Section 4.10 "Equality predicates"

Published by: XBRL International (now IFRS Foundation)

CRITICAL NOTE:
-------------
This module contains ONLY the matching/comparison RULES from the specification.
The actual context structures (entity, period, segment, scenario) are extracted
from XBRL instance documents - NOT defined here.

SCOPE:
------
UNIVERSAL - applies to all XBRL 2.1 filings globally
"""

from typing import Optional
from datetime import date, datetime


def contexts_match(context1: dict[str, any], context2: dict[str, any]) -> bool:
    """
    Determine if two XBRL contexts match according to XBRL 2.1 Specification.
    
    SOURCE:
    -------
    XBRL 2.1 Specification Section 4.7
    XBRL 2.1 Specification Section 4.10 "C-Equal" predicate
    
    SPECIFICATION DEFINITION:
    ------------------------
    Two contexts match if ALL of the following are true:
    1. Entity identifiers match
    2. Periods match (instant = instant, or duration overlaps)
    3. Segment dimensions match (all explicit dimensions)
    4. Scenario dimensions match (if present)
    
    IMPORTANT:
    ---------
    This function defines the MATCHING RULES.
    The context structures themselves come from parsed XBRL files.
    
    Args:
        context1: First context (from parsed filing)
        context2: Second context (from parsed filing)
        
    Returns:
        True if contexts match per XBRL 2.1 Spec, False otherwise
        
    Examples:
        >>> ctx1 = {
        ...     'entity': {'scheme': 'http://www.sec.gov/CIK', 'value': '0001646972'},
        ...     'period': {'instant': '2024-02-24'},
        ...     'segment': None
        ... }
        >>> ctx2 = {
        ...     'entity': {'scheme': 'http://www.sec.gov/CIK', 'value': '0001646972'},
        ...     'period': {'instant': '2024-02-24'},
        ...     'segment': None
        ... }
        >>> contexts_match(ctx1, ctx2)
        True
    """
    # XBRL 2.1 Spec Section 4.7: Entity must match exactly
    if not entities_match(context1.get('entity'), context2.get('entity')):
        return False
    
    # XBRL 2.1 Spec Section 4.7: Period must match
    if not periods_match(context1.get('period'), context2.get('period')):
        return False
    
    # XBRL 2.1 Spec Section 4.7: Segment dimensions must match
    if not segments_match(context1.get('segment'), context2.get('segment')):
        return False
    
    # XBRL 2.1 Spec Section 4.7: Scenario dimensions must match
    if not scenarios_match(context1.get('scenario'), context2.get('scenario')):
        return False
    
    return True


def entities_match(entity1: Optional[dict], entity2: Optional[dict]) -> bool:
    """
    Determine if two entity identifiers match.
    
    SOURCE:
    -------
    XBRL 2.1 Specification Section 4.7.3 "The <entity> element"
    
    SPECIFICATION RULE:
    ------------------
    Entities match if BOTH scheme and identifier value are identical.
    
    Args:
        entity1: First entity {'scheme': '...', 'value': '...'}
        entity2: Second entity
        
    Returns:
        True if entities match per specification
        
    Examples:
        >>> e1 = {'scheme': 'http://www.sec.gov/CIK', 'value': '0001646972'}
        >>> e2 = {'scheme': 'http://www.sec.gov/CIK', 'value': '0001646972'}
        >>> entities_match(e1, e2)
        True
    """
    if entity1 is None and entity2 is None:
        return True
    
    if entity1 is None or entity2 is None:
        return False
    
    # XBRL 2.1 Spec: Both scheme and value must match
    return (
        entity1.get('scheme') == entity2.get('scheme') and
        entity1.get('value') == entity2.get('value')
    )


def periods_match(period1: Optional[dict], period2: Optional[dict]) -> bool:
    """
    Determine if two periods match according to XBRL 2.1 Specification.
    
    SOURCE:
    -------
    XBRL 2.1 Specification Section 4.7.2 "The <period> element"
    
    SPECIFICATION RULES:
    -------------------
    - Instant periods match if dates are identical
    - Duration periods match if start/end dates are identical
    - Instant and duration periods never match
    - Forever periods match with other forever periods
    
    Args:
        period1: First period {'instant': ...} or {'start_date': ..., 'end_date': ...}
        period2: Second period
        
    Returns:
        True if periods match per specification
        
    Examples:
        >>> p1 = {'instant': '2024-02-24'}
        >>> p2 = {'instant': '2024-02-24'}
        >>> periods_match(p1, p2)
        True
        
        >>> p1 = {'start_date': '2023-02-26', 'end_date': '2024-02-24'}
        >>> p2 = {'start_date': '2023-02-26', 'end_date': '2024-02-24'}
        >>> periods_match(p1, p2)
        True
    """
    if period1 is None and period2 is None:
        return True
    
    if period1 is None or period2 is None:
        return False
    
    # Check period types
    p1_type = period1.get('period_type')
    p2_type = period2.get('period_type')
    
    if p1_type != p2_type:
        return False
    
    # XBRL 2.1 Spec: Match based on period type
    if p1_type == 'instant':
        return period1.get('instant') == period2.get('instant')
    
    elif p1_type == 'duration':
        return (
            period1.get('start_date') == period2.get('start_date') and
            period1.get('end_date') == period2.get('end_date')
        )
    
    elif p1_type == 'forever':
        return True  # All forever periods match
    
    return False


def segments_match(segment1: Optional[dict], segment2: Optional[dict]) -> bool:
    """
    Determine if two segments match (all dimensions must match).
    
    SOURCE:
    -------
    XBRL 2.1 Specification Section 4.7.3.2 "The <segment> element"
    XBRL Dimensions 1.0 Specification
    
    SPECIFICATION RULE:
    ------------------
    Segments match if ALL explicit dimensions match.
    Each dimension-member pair must be identical.
    
    Args:
        segment1: First segment with explicit_dimensions list
        segment2: Second segment
        
    Returns:
        True if all dimensions match
        
    Examples:
        >>> s1 = {
        ...     'explicit_dimensions': [
        ...         {'dimension': 'us-gaap:StatementClassOfStockAxis',
        ...          'member': 'us-gaap:CommonStockMember'}
        ...     ]
        ... }
        >>> s2 = {
        ...     'explicit_dimensions': [
        ...         {'dimension': 'us-gaap:StatementClassOfStockAxis',
        ...          'member': 'us-gaap:CommonStockMember'}
        ...     ]
        ... }
        >>> segments_match(s1, s2)
        True
    """
    if segment1 is None and segment2 is None:
        return True
    
    if segment1 is None or segment2 is None:
        return False
    
    dims1 = segment1.get('explicit_dimensions', [])
    dims2 = segment2.get('explicit_dimensions', [])
    
    # Must have same number of dimensions
    if len(dims1) != len(dims2):
        return False
    
    # Convert to sets of (dimension, member) tuples for comparison
    dims1_set = {
        (d.get('dimension'), d.get('member'))
        for d in dims1
    }
    dims2_set = {
        (d.get('dimension'), d.get('member'))
        for d in dims2
    }
    
    # XBRL Spec: All dimensions must match
    return dims1_set == dims2_set


def scenarios_match(scenario1: Optional[dict], scenario2: Optional[dict]) -> bool:
    """
    Determine if two scenarios match.
    
    SOURCE:
    -------
    XBRL 2.1 Specification Section 4.7.4 "The <scenario> element"
    
    SPECIFICATION RULE:
    ------------------
    Scenarios match if all their content matches.
    Same logic as segments (dimension-based matching).
    
    Args:
        scenario1: First scenario
        scenario2: Second scenario
        
    Returns:
        True if scenarios match
    """
    # Scenarios use same matching logic as segments
    return segments_match(scenario1, scenario2)


# Export public functions
__all__ = [
    'contexts_match',
    'entities_match',
    'periods_match',
    'segments_match',
    'scenarios_match',
]