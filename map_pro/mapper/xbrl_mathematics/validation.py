"""
XBRL Validation Formulas

This module contains validation formulas defined in the XBRL 2.1 Specification.

SOURCE AUTHORITY:
----------------
XBRL 2.1 Specification Section 5.2.5 "The <calculationLink> element"
XBRL 2.1 Specification Section 4.10 "Equality predicates"

Published by: XBRL International (now IFRS Foundation)

CRITICAL NOTE:
-------------
This module contains ONLY the validation FORMULAS from the specification.
The actual calculation relationships come from _cal.xml files - NOT here.

SCOPE:
------
UNIVERSAL - applies to all XBRL 2.1 filings globally
"""

from decimal import Decimal


def validate_calculation_arc(
    parent_value: Decimal,
    child_values: list[tuple[Decimal, Decimal]],
    tolerance: Decimal = Decimal('0')
) -> tuple[bool, Decimal]:
    """
    Validate calculation relationship per XBRL 2.1 Specification.
    
    SOURCE:
    -------
    XBRL 2.1 Specification Section 5.2.5
    
    SPECIFICATION FORMULA:
    ---------------------
    parent_value = Σ(child_value × weight)
    
    Where:
    - parent_value = sum concept value
    - child_value = contributor concept value
    - weight = from calculation arc (usually 1.0 or -1.0)
    
    SPECIFICATION QUOTE:
    -------------------
    "The summation-item arc indicates that the numeric concept at its from end
    is equal to the sum of the numeric values of the concepts at its to end,
    where each value is multiplied by the weight attribute value of its arc."
    
    IMPORTANT:
    ---------
    The calculation arcs (parent→child with weights) come from _cal.xml files.
    This function only implements the VALIDATION FORMULA.
    
    Args:
        parent_value: Value of the parent (sum) concept
        child_values: List of (child_value, weight) tuples from _cal.xml
        tolerance: Acceptable rounding difference (default 0)
        
    Returns:
        Tuple of (is_valid, calculated_sum)
        
    Examples:
        >>> # Assets = CurrentAssets + NoncurrentAssets
        >>> parent = Decimal('1000')
        >>> children = [
        ...     (Decimal('600'), Decimal('1.0')),  # CurrentAssets
        ...     (Decimal('400'), Decimal('1.0')),  # NoncurrentAssets
        ... ]
        >>> validate_calculation_arc(parent, children)
        (True, Decimal('1000'))
        
        >>> # With subtraction (weight = -1.0)
        >>> parent = Decimal('300')
        >>> children = [
        ...     (Decimal('500'), Decimal('1.0')),   # Revenue
        ...     (Decimal('200'), Decimal('-1.0')),  # Expenses (subtract)
        ... ]
        >>> validate_calculation_arc(parent, children)
        (True, Decimal('300'))
    """
    # XBRL 2.1 Spec Section 5.2.5 formula:
    # parent_value = Σ(child_value × weight)
    
    calculated_sum = Decimal('0')
    
    for child_value, weight in child_values:
        weighted_value = child_value * weight
        calculated_sum += weighted_value
    
    # Check if parent equals calculated sum (within tolerance)
    difference = abs(parent_value - calculated_sum)
    is_valid = difference <= tolerance
    
    return (is_valid, calculated_sum)


def detect_duplicate_fact(
    fact: dict[str, any],
    existing_facts: list[dict[str, any]]
) -> list[dict[str, any]]:
    """
    Detect duplicate facts according to XBRL 2.1 Specification.
    
    SOURCE:
    -------
    XBRL 2.1 Specification Section 4.10 "Equality predicates"
    XBRL 2.1 Specification Section 4.6 "Items"
    
    SPECIFICATION RULES:
    -------------------
    Facts are duplicates if ALL match:
    1. Same concept (QName)
    2. Same context
    3. Same unit (for numeric facts)
    4. Same parent (if within tuple)
    
    SPECIFICATION QUOTE:
    -------------------
    "Duplicate items are two or more items of the same concept in the same
    context under the same parent."
    
    ACTION PER SPECIFICATION:
    ------------------------
    - If values match → Duplicates allowed (keep one)
    - If values differ → ERROR (inconsistent)
    
    Args:
        fact: The fact to check
        existing_facts: List of facts to check against
        
    Returns:
        List of duplicate facts found
        
    Examples:
        >>> fact = {
        ...     'concept': 'us-gaap:Assets',
        ...     'context_ref': 'c1',
        ...     'unit_ref': 'usd',
        ...     'value': '1000',
        ...     'parent': None
        ... }
        >>> existing = [{
        ...     'concept': 'us-gaap:Assets',
        ...     'context_ref': 'c1',
        ...     'unit_ref': 'usd',
        ...     'value': '1000',
        ...     'parent': None
        ... }]
        >>> duplicates = detect_duplicate_fact(fact, existing)
        >>> len(duplicates)
        1
    """
    duplicates = []
    
    fact_concept = fact.get('concept')
    fact_context = fact.get('context_ref')
    fact_unit = fact.get('unit_ref')
    fact_parent = fact.get('parent')
    
    for existing_fact in existing_facts:
        # XBRL 2.1 Spec: Check all duplicate criteria
        
        # 1. Same concept
        if existing_fact.get('concept') != fact_concept:
            continue
        
        # 2. Same context
        if existing_fact.get('context_ref') != fact_context:
            continue
        
        # 3. Same unit (for numeric facts)
        if fact_unit is not None:
            if existing_fact.get('unit_ref') != fact_unit:
                continue
        
        # 4. Same parent (if in tuple)
        if existing_fact.get('parent') != fact_parent:
            continue
        
        # All criteria match - this is a duplicate
        duplicates.append(existing_fact)
    
    return duplicates


def values_equal_within_precision(
    value1: Decimal,
    value2: Decimal,
    decimals1: int,
    decimals2: int
) -> bool:
    """
    Determine if two values are equal within their declared precision.
    
    SOURCE:
    -------
    XBRL 2.1 Specification Section 4.10 "V-Equal" predicate
    
    SPECIFICATION RULE:
    ------------------
    Values are equal if they are the same when rounded to the
    lesser of their two precision levels.
    
    Args:
        value1: First value
        value2: Second value  
        decimals1: Decimals for first value
        decimals2: Decimals for second value
        
    Returns:
        True if values equal within precision
        
    Examples:
        >>> # Same value, same precision
        >>> values_equal_within_precision(
        ...     Decimal('100.00'), Decimal('100.00'), 2, 2
        ... )
        True
        
        >>> # Different precision - use lesser
        >>> values_equal_within_precision(
        ...     Decimal('100.00'), Decimal('100.01'), 2, 0
        ... )
        True  # Both round to 100 when decimals=0
    """
    # Use lesser (more lenient) precision
    lesser_decimals = min(decimals1, decimals2)
    
    # Round both values to lesser precision
    rounded1 = round(value1, lesser_decimals)
    rounded2 = round(value2, lesser_decimals)
    
    return rounded1 == rounded2


# Export public functions
__all__ = [
    'validate_calculation_arc',
    'detect_duplicate_fact',
    'values_equal_within_precision',
]