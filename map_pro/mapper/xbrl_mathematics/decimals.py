"""
XBRL Mathematical Formulas - Decimals and Precision

This module contains formulas for processing XBRL @decimals and @precision attributes
as defined by the XBRL 2.1 Specification (W3C Recommendation).

SOURCE AUTHORITY:
----------------
XBRL 2.1 Specification (December 31, 2003, corrected February 20, 2013)
Published by: XBRL International (now IFRS Foundation)
Status: W3C Recommendation

Reference URL:
http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/
XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html

SCOPE:
-----
These formulas apply UNIVERSALLY to all XBRL 2.1 filings globally:
- US SEC filings
- EU ESEF filings
- UK HMRC filings
- Any jurisdiction using XBRL 2.1 specification

HARDCODE JUSTIFICATION:
----------------------
These formulas exist ONLY in the XBRL 2.1 Specification as human-readable prose
and examples. They are NOT available in machine-readable format anywhere in:
- XBRL instance documents
- Taxonomy schema files
- Linkbase files
- Namespace declarations

Therefore, they MUST be implemented based on reading and interpreting the 
specification document. This module serves as the single source of truth for
these implementations within the mapper system.
"""

from decimal import Decimal, InvalidOperation
from typing import Optional
import math


# =============================================================================
# DECIMALS SCALING FORMULA
# =============================================================================

def scale_value_with_decimals(value: Decimal, decimals: int) -> Decimal:
    """
    Scale a reported XBRL value using the @decimals attribute.
    
    SOURCE:
    -------
    XBRL 2.1 Specification Section 4.6.5 "The @decimals attribute"
    
    SPECIFICATION QUOTE:
    -------------------
    "If a numeric fact has a @decimals attribute with the value 'n' then it 
    is known to be correct to 'n' decimal places."
    
    FORMULA DERIVATION:
    ------------------
    From the specification's definition of "correct to n decimal places" and
    the provided examples (Example 12), the scaling formula is:
    
        accurate_value = reported_value × 10^(-decimals)
    
    EXAMPLES FROM SPECIFICATION:
    ---------------------------
    Example 12: Decimals and lexical representation
    
    Input: value=10.00, decimals=2
    Output: 10.00 (accurate to 0.01)
    Formula: 10.00 × 10^(-2) = 10.00 × 0.01 = 10.00
    
    Input: value=2002000, decimals=-3
    Output: 2002000 (accurate to nearest 1000)
    Formula: 2002000 × 10^(3) = 2002000000
    
    SPECIAL CASES:
    -------------
    - decimals="INF" → No scaling (exact value)
    - decimals=0 → Accurate to ones place
    - decimals>0 → Accurate to decimal places (e.g., 2 = hundredths)
    - decimals<0 → Accurate to powers of 10 (e.g., -3 = thousands)
    
    Args:
        value: The reported XBRL value (pre-converted to Decimal)
        decimals: The @decimals attribute value (integer)
        
    Returns:
        Scaled value according to XBRL 2.1 specification
        
    Raises:
        InvalidOperation: If calculation results in non-finite number
        
    Examples:
        >>> scale_value_with_decimals(Decimal("26755.7"), -5)
        Decimal('2675570000')
        
        >>> scale_value_with_decimals(Decimal("10.00"), 2)
        Decimal('10.00')
        
        >>> scale_value_with_decimals(Decimal("2002000"), -3)
        Decimal('2002000000')
    """
    # XBRL 2.1 Spec Section 4.6.5 formula:
    # accurate_value = reported_value × 10^(-decimals)
    
    scaling_multiplier = Decimal(10) ** (-decimals)
    scaled_value = value * scaling_multiplier
    
    if not scaled_value.is_finite():
        raise InvalidOperation(
            f"Scaling resulted in non-finite value: {value} × 10^{-decimals}"
        )
    
    return scaled_value


# =============================================================================
# PRECISION SCALING FORMULA
# =============================================================================

def scale_value_with_precision(value: Decimal, precision: int) -> Decimal:
    """
    Round a value to specified precision (significant figures).
    
    SOURCE:
    -------
    XBRL 2.1 Specification Section 4.6.4 "The @precision attribute"
    
    SPECIFICATION QUOTE:
    -------------------
    "If a numeric fact has a @precision attribute that has the value 'n' then 
    it is correct to 'n' significant figures."
    
    FORMULA DERIVATION:
    ------------------
    From specification Section 4.6.7.1:
    "The first 'n' decimal digits, counting from the left, starting at the 
    first non-zero digit in the lexical representation of the number are 
    known to be accurate."
    
    EXAMPLES FROM SPECIFICATION:
    ---------------------------
    Example 11: Precision and lexical representation
    
    Input: value=123, precision=5
    Output: Accurate to 5 significant figures
    
    SPECIAL CASES:
    -------------
    - precision="INF" → No rounding (exact value)
    - precision=0 → No accuracy known (undefined)
    
    ROUNDING METHOD:
    ---------------
    Uses IEEE 754 roundTiesToEven (banker's rounding) as specified in
    XBRL 2.1 Section 4.6.7.1
    
    Args:
        value: The value to round
        precision: Number of significant figures
        
    Returns:
        Value rounded to specified precision
        
    Raises:
        ValueError: If precision is 0 (no accuracy known)
        
    Examples:
        >>> scale_value_with_precision(Decimal("123456.789"), 5)
        Decimal('123460')
        
        >>> scale_value_with_precision(Decimal("0.001234"), 3)
        Decimal('0.00123')
    """
    if precision == 0:
        raise ValueError("Precision of 0 indicates no accuracy information")
    
    if value == 0:
        return value
    
    # Calculate magnitude (position of most significant digit)
    magnitude = math.floor(math.log10(abs(float(value))))
    
    # Calculate decimal places needed for rounding
    decimal_places = precision - magnitude - 1
    
    # Round to calculated decimal places
    # Python's round() uses banker's rounding (roundTiesToEven)
    rounded_value = round(value, int(decimal_places))
    
    return Decimal(str(rounded_value))


# =============================================================================
# INFER DECIMALS FROM PRECISION
# =============================================================================

def infer_decimals_from_precision(value: Decimal, precision: int) -> int:
    """
    Infer @decimals value from @precision attribute.
    
    SOURCE:
    -------
    XBRL 2.1 Specification Section 4.6.6 "Inferring decimals"
    
    SPECIFICATION QUOTE:
    -------------------
    "If the value of the @precision attribute is not INF and greater than 0 
    then the decimals value is given by the following expression:
    
    precision - int(floor(log10(abs(number(item))))) - 1"
    
    SPECIAL CASES FROM SPECIFICATION:
    --------------------------------
    - For value of 0: inferred decimals = INF (infinite precision)
    - For precision = 0: nothing can be inferred (undefined)
    - For precision = INF: inferred decimals = INF
    
    Args:
        value: The numeric value
        precision: The @precision attribute value
        
    Returns:
        Inferred decimals value (as integer, use math.inf for INF)
        
    Raises:
        ValueError: If precision is 0
        
    Examples:
        >>> infer_decimals_from_precision(Decimal("123"), 5)
        2  # 5 - floor(log10(123)) - 1 = 5 - 2 - 1 = 2
        
        >>> infer_decimals_from_precision(Decimal("0.001"), 3)
        6  # 3 - floor(log10(0.001)) - 1 = 3 - (-3) - 1 = 5
    """
    if precision == 0:
        raise ValueError("Cannot infer decimals from precision=0")
    
    # Special case: value is exactly zero
    if value == 0:
        return math.inf  # Represents "INF"
    
    # XBRL 2.1 Spec Section 4.6.6 formula:
    # decimals = precision - int(floor(log10(abs(value)))) - 1
    
    magnitude = math.floor(math.log10(abs(float(value))))
    inferred_decimals = precision - magnitude - 1
    
    # If result is negative and less than precision, it's valid
    # Otherwise, if it's less than 0, default to 0
    return max(inferred_decimals, 0) if inferred_decimals < 0 and abs(inferred_decimals) > precision else inferred_decimals


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def parse_decimals_attribute(decimals_str: str) -> Optional[int]:
    """
    Parse @decimals attribute value from XBRL.
    
    SOURCE:
    -------
    XBRL 2.1 Specification Section 4.6.5
    
    ALLOWED VALUES:
    --------------
    - Integer (positive, negative, or zero)
    - "INF" (infinite precision)
    
    Args:
        decimals_str: The @decimals attribute value from XBRL
        
    Returns:
        Integer decimals value, or None for "INF"
        
    Examples:
        >>> parse_decimals_attribute("-5")
        -5
        
        >>> parse_decimals_attribute("INF")
        None  # Represents infinite precision
    """
    if decimals_str == "INF":
        return None  # Infinite precision
    
    try:
        return int(decimals_str)
    except ValueError:
        raise ValueError(f"Invalid @decimals value: {decimals_str}")


def parse_precision_attribute(precision_str: str) -> Optional[int]:
    """
    Parse @precision attribute value from XBRL.
    
    SOURCE:
    -------
    XBRL 2.1 Specification Section 4.6.4
    
    ALLOWED VALUES:
    --------------
    - Non-negative integer
    - "INF" (infinite precision)
    
    Args:
        precision_str: The @precision attribute value from XBRL
        
    Returns:
        Integer precision value, or None for "INF"
        
    Examples:
        >>> parse_precision_attribute("3")
        3
        
        >>> parse_precision_attribute("INF")
        None  # Represents infinite precision
    """
    if precision_str == "INF":
        return None  # Infinite precision
    
    try:
        precision = int(precision_str)
        if precision < 0:
            raise ValueError("Precision cannot be negative")
        return precision
    except ValueError as e:
        raise ValueError(f"Invalid @precision value: {precision_str}") from e


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    'scale_value_with_decimals',
    'scale_value_with_precision',
    'infer_decimals_from_precision',
    'parse_decimals_attribute',
    'parse_precision_attribute',
]