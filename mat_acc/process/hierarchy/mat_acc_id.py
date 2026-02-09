# Path: mat_acc/process/hierarchy/mat_acc_id.py
"""
mat_acc ID Generation and Parsing Utilities.

Provides utilities for generating and parsing mat_acc_id identifiers.
The mat_acc_id uniquely identifies a concept's position in the statement
hierarchy AND its context (period/dimension).

Format: {STATEMENT_CODE}-{LEVEL:03d}-{SIBLING:03d}-{CONTEXT_REF}
Example: BS-002-001-c4

Components:
- STATEMENT_CODE: Two-letter code (generated dynamically from statement type)
- LEVEL: Hierarchy level (000 = root)
- SIBLING: Sibling position (001-based)
- CONTEXT_REF: Optional context reference (e.g., c4, c12)

DYNAMIC CODE GENERATION:
Statement codes are NOT hardcoded - they are generated from the statement type
name discovered in the data. This supports any taxonomy/market's statement types.
"""

from typing import Any, Optional

from process.hierarchy.constants import STATEMENT_CODE_LENGTH


# Runtime registry for discovered statement types and their codes
# This is populated as statement types are encountered
_statement_type_registry: dict[str, str] = {}
_code_to_type_registry: dict[str, str] = {}


def generate_statement_code(statement_type: str) -> str:
    """
    Generate a unique two-letter code from a statement type name.

    Uses the first letters of significant words in the statement type.
    If collision occurs, uses alternate letter combinations.

    This is DYNAMIC - works with any statement type from any taxonomy.

    Args:
        statement_type: Statement type name (e.g., 'BALANCE_SHEET', 'INCOME_STATEMENT')

    Returns:
        Two-letter uppercase code (e.g., 'BS', 'IS')

    Example:
        >>> generate_statement_code('BALANCE_SHEET')
        'BS'
        >>> generate_statement_code('SOME_NEW_STATEMENT_TYPE')
        'SN'  # or another unique code
    """
    # Normalize the statement type
    normalized = statement_type.upper().replace('_', ' ').replace('-', ' ')

    # Split into words
    words = normalized.split()

    if not words:
        return 'XX'

    # Strategy 1: First letter of first two words
    if len(words) >= 2:
        code = words[0][0] + words[1][0]
        if code not in _code_to_type_registry or _code_to_type_registry[code] == statement_type.upper():
            return code

    # Strategy 2: First two letters of first word
    if len(words[0]) >= 2:
        code = words[0][:2]
        if code not in _code_to_type_registry or _code_to_type_registry[code] == statement_type.upper():
            return code

    # Strategy 3: First letter + second letter of word(s)
    for i in range(1, min(len(words[0]), 10)):
        code = words[0][0] + words[0][i]
        if code not in _code_to_type_registry or _code_to_type_registry[code] == statement_type.upper():
            return code

    # Strategy 4: Use hash-based approach for uniqueness
    import hashlib
    hash_code = hashlib.md5(statement_type.encode()).hexdigest()[:2].upper()
    return hash_code


def get_statement_code(statement_type: str) -> str:
    """
    Get or generate a statement code for a statement type.

    If the statement type has been seen before, returns the same code.
    Otherwise, generates a new unique code.

    Args:
        statement_type: Statement type name (e.g., 'BALANCE_SHEET')

    Returns:
        Two-letter uppercase code (e.g., 'BS')

    Example:
        >>> get_statement_code('BALANCE_SHEET')
        'BS'
        >>> get_statement_code('INCOME_STATEMENT')
        'IS'
    """
    normalized_type = statement_type.upper()

    # Check if already registered
    if normalized_type in _statement_type_registry:
        return _statement_type_registry[normalized_type]

    # Generate new code
    code = generate_statement_code(normalized_type)

    # Register the mapping
    _statement_type_registry[normalized_type] = code
    _code_to_type_registry[code] = normalized_type

    return code


def get_statement_type(code: str) -> str:
    """
    Get the statement type for a code.

    Returns the statement type if the code has been registered,
    otherwise returns 'UNKNOWN'.

    Args:
        code: Two-letter code (e.g., 'BS', 'IS')

    Returns:
        Statement type string or 'UNKNOWN'

    Example:
        >>> # After get_statement_code('BALANCE_SHEET') was called
        >>> get_statement_type('BS')
        'BALANCE_SHEET'
    """
    return _code_to_type_registry.get(code.upper(), 'UNKNOWN')


def format_mat_acc_id(
    statement_code: str,
    level: int,
    sibling: int,
    context_ref: Optional[str] = None
) -> str:
    """
    Generate a mat_acc_id from components.

    Format: {STATEMENT_CODE}-{LEVEL:03d}-{SIBLING:03d}-{CONTEXT_REF}
    Example: BS-002-001-c4

    Args:
        statement_code: Statement type code (e.g., 'BS', 'IS')
        level: Hierarchy level (0 = root)
        sibling: Sibling position (1-based)
        context_ref: Optional context reference (e.g., 'c-4', 'c4')

    Returns:
        Formatted mat_acc_id string

    Example:
        >>> format_mat_acc_id('BS', 2, 1, 'c4')
        'BS-002-001-c4'
        >>> format_mat_acc_id('IS', 3, 5)
        'IS-003-005'
    """
    position = f"{statement_code}-{level:03d}-{sibling:03d}"

    if context_ref:
        ctx = normalize_context_ref(context_ref)
        return f"{position}-{ctx}"

    return position


def format_position(
    statement_code: str,
    level: int,
    sibling: int
) -> str:
    """
    Generate a mat_acc_position (without context_ref).

    This is the structural position identifier.

    Args:
        statement_code: Statement type code (e.g., 'BS', 'IS')
        level: Hierarchy level (0 = root)
        sibling: Sibling position (1-based)

    Returns:
        Formatted position string

    Example:
        >>> format_position('BS', 2, 1)
        'BS-002-001'
    """
    return f"{statement_code}-{level:03d}-{sibling:03d}"


def parse_mat_acc_id(mat_acc_id: str) -> dict[str, Any]:
    """
    Parse a mat_acc_id into its components.

    Args:
        mat_acc_id: The mat_acc_id to parse (e.g., 'BS-002-001-c4')

    Returns:
        Dictionary with:
            - statement_code: The two-letter code (e.g., 'BS')
            - statement_type: Statement type if known, else 'UNKNOWN'
            - level: Hierarchy level (int)
            - sibling: Sibling position (int)
            - context_ref: Context reference or None
            - position: Position without context (BS-002-001)

    Example:
        >>> parse_mat_acc_id('BS-002-001-c4')
        {
            'statement_code': 'BS',
            'statement_type': 'BALANCE_SHEET',  # if registered
            'level': 2,
            'sibling': 1,
            'context_ref': 'c4',
            'position': 'BS-002-001'
        }
    """
    parts = mat_acc_id.split('-')

    if len(parts) < 3:
        return {
            'statement_code': '',
            'statement_type': 'UNKNOWN',
            'level': 0,
            'sibling': 0,
            'context_ref': None,
            'position': mat_acc_id,
        }

    statement_code = parts[0]
    level = int(parts[1])
    sibling = int(parts[2])
    position = f"{statement_code}-{parts[1]}-{parts[2]}"

    # Context ref is the 4th part if present
    context_ref = parts[3] if len(parts) > 3 else None

    return {
        'statement_code': statement_code,
        'statement_type': get_statement_type(statement_code),
        'level': level,
        'sibling': sibling,
        'context_ref': context_ref,
        'position': position,
    }


def normalize_context_ref(context_ref: str) -> str:
    """
    Normalize a context reference to standard format.

    Removes dashes and underscores for consistent storage.

    Args:
        context_ref: Raw context reference (e.g., 'c-4', 'c_4', 'c4')

    Returns:
        Normalized context reference (e.g., 'c4')

    Example:
        >>> normalize_context_ref('c-4')
        'c4'
        >>> normalize_context_ref('c_4')
        'c4'
    """
    return context_ref.replace('-', '').replace('_', '')


def add_context_to_position(position: str, context_ref: str) -> str:
    """
    Add a context_ref to an existing position to create full mat_acc_id.

    Args:
        position: Structural position (e.g., 'BS-002-001')
        context_ref: Context reference (e.g., 'c4', 'c-4')

    Returns:
        Full mat_acc_id (e.g., 'BS-002-001-c4')

    Example:
        >>> add_context_to_position('BS-002-001', 'c4')
        'BS-002-001-c4'
    """
    ctx = normalize_context_ref(context_ref)
    return f"{position}-{ctx}"


def get_registered_types() -> dict[str, str]:
    """
    Get all registered statement types and their codes.

    Returns:
        Dictionary mapping statement types to their codes
    """
    return _statement_type_registry.copy()


def clear_registry() -> None:
    """
    Clear the statement type registry.

    Useful for testing or resetting state.
    """
    _statement_type_registry.clear()
    _code_to_type_registry.clear()


__all__ = [
    # Functions
    'generate_statement_code',
    'get_statement_code',
    'get_statement_type',
    'format_mat_acc_id',
    'format_position',
    'parse_mat_acc_id',
    'normalize_context_ref',
    'add_context_to_position',
    'get_registered_types',
    'clear_registry',
]
