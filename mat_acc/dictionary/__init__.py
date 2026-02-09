# Path: mat_acc/dictionary/__init__.py
"""
Dictionary Module - Component and Formula Definitions

The dictionary is the heart of mat_acc's dynamic concept matching system.
It contains YAML definitions that describe financial concepts by their
characteristics, enabling market-agnostic matching.

Structure:
    dictionary/
    ├── schema/           # JSON Schema for validation
    ├── components/       # Component definitions (what to match)
    │   ├── balance_sheet/
    │   ├── income_statement/
    │   ├── cash_flow/
    │   └── per_share/
    └── formulas/         # Ratio formula definitions
        ├── liquidity/
        ├── leverage/
        ├── profitability/
        ├── efficiency/
        └── valuation/

Adding New Ratios:
    1. Create component definitions for any new concepts needed
    2. Create formula definition in appropriate category
    3. No code changes required - just add YAML files

Example:
    # Load all component definitions
    from dictionary import ComponentLoader

    loader = ComponentLoader()
    components = loader.load_all()

    # Get specific component
    current_assets = components['current_assets']
"""

from pathlib import Path

# Dictionary root path
DICTIONARY_ROOT = Path(__file__).parent

# Subdirectory paths
SCHEMA_DIR = DICTIONARY_ROOT / 'schema'
COMPONENTS_DIR = DICTIONARY_ROOT / 'components'
FORMULAS_DIR = DICTIONARY_ROOT / 'formulas'

__all__ = [
    'DICTIONARY_ROOT',
    'SCHEMA_DIR',
    'COMPONENTS_DIR',
    'FORMULAS_DIR',
]
