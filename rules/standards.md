"""
Python Coding Standards & Project Instructions - Complete Reference
===================================================================

This file contains:
1. Coding standards and thresholds from 13 production analyzers
2. XBRL Parser project-specific instructions and principles

Can be imported and used programmatically or as a quick reference.

Usage:
    from standards import THRESHOLDS, PROJECT_PRINCIPLES, check_function_complexity
    from standards import validate_no_hardcode, validate_output_location
"""

# ============================================================================
# PROJECT-SPECIFIC PRINCIPLES (CRITICAL - READ FIRST!)
# ============================================================================

PROJECT_PRINCIPLES = {
    'no_hardcode': {
        'rule': 'NO HARDCODE: Nowhere and on no subject',
        'description': 'No URI/URL will be written in any code. No other type of hardcode should be seen in any code.',
        'applies_to': ['urls', 'paths', 'constants', 'configuration'],
        'solution': 'Use configuration files, environment variables, or config_loader.py',
        'forbidden_patterns': [
            'https://',
            'http://',
            '/home/',
            'C:\\',
            'localhost',
            '127.0.0.1',
            # Add more as needed
        ],
        'allowed_exceptions': [
            'Comments and docstrings',
            'Test fixtures with clearly marked test data',
        ]
    },
    
    'market_agnostic': {
        'rule': 'MARKET AGNOSTIC: Only market specific code is allowed in "market" directory',
        'description': 'For the rest of the system no market specific code is allowed',
        'allowed_location': 'xbrl_parser/market/',
        'forbidden_locations': [
            'xbrl_parser/foundation/',
            'xbrl_parser/taxonomy/',
            'xbrl_parser/instance/',
            'xbrl_parser/validation/',  # Except registry that calls market validators
            'xbrl_parser/models/',
        ],
        'market_keywords': [
            'us-gaap', 'us_gaap', 'sec', 'edgar',
            'ifrs', 
            'uk-gaap', 'uk_gaap', 'frc', 'companies_house',
            'esef', 'esma',
        ],
        'solution': 'Use market detector and registry pattern. Call market-specific logic through registry.'
    },
    
    'taxonomy_agnostic': {
        'rule': 'TAXONOMY AGNOSTIC: System should be open and ready to read any taxonomy',
        'description': 'Not only designated market or industry specific taxonomies',
        'applies_to': 'All taxonomy loading and parsing components',
        'forbidden': [
            'Hardcoded taxonomy namespaces',
            'Hardcoded concept names',
            'Taxonomy-specific parsing logic outside market/',
        ],
        'required': [
            'Generic taxonomy loading',
            'Namespace-based detection',
            'Extensible taxonomy support',
        ]
    },
    
    'output_location': {
        'rule': 'NEVER EVER WRITE ANY REPORT UNDER PROJECT FILES, ALWAYS UNDER DATA CENTRE',
        'description': 'User has clean division: 1. Program files, 2. Data partition',
        'program_files': [
            'py files',
            '.env files', 
            'config files',
            '__init__.py',
            'All source code',
        ],
        'data_files': [
            'json reports',
            'xml reports',
            'htm reports',
            'txt reports',
            'Any extracted data',
            'Any generated output',
        ],
        'action_required': 'Whenever a report to be produced, ask user to identify a relevant place under data partition',
        'never_write_to': [
            'xbrl_parser/',
            'core/',
            'loaders/',
            'tests/',  # Except test fixtures
            'examples/',
        ],
        'allowed_write_to': [
            'output/',
            'User-specified data directories',
            'Configured output paths from .env',
        ]
    },
    
    'folder_tree': {
        'rule': 'ALWAYS ASKS FOR THE CURRENT FOLDER TREE FROM USER\'S COMPUTER',
        'description': 'Claude uploaded project files section does not accept folder structure',
        'problem': 'User uploads files as flat, Claude sees all files under /mnt/user/ as flat',
        'solution': 'Claude agent must ask for the up to date project folder tree and create a virtual copy',
        'critical': 'Do not forget or exclude __init__.py files; always include them on virtual folder tree',
        'when_to_ask': [
            'At start of any coding session',
            'Before writing any new files',
            'When file locations are ambiguous',
        ]
    },

    'path_regime_check': {
        'rule': 'BEFORE WRITING ANY PATH CHECK THE CONTENT OF CURRENT .env, core/data_paths.py and core/config_loader.py files',
        'description': 'Check the existing path regime to prevent duplication and ensure consistency',
        'critical': 'MUST check these three files before adding any new path',
        'required_files_to_check': [
            '.env - All environment variables and path definitions',
            'core/data_paths.py - Path construction and auto-creation logic',
            'core/config_loader.py - Configuration loading and validation',
        ],
        'workflow': [
            '1. Read current .env file completely',
            '2. Read core/data_paths.py to understand path construction',
            '3. Read core/config_loader.py to see how paths are loaded',
            '4. Check if required path already exists',
            '5. If exists: use existing path (stop creating duplicate)',
            '6. If not exists: add to appropriate file following existing patterns',
        ],
        'objectives': [
            'Stop creating a path that already exists/is usable',
            'Prevent duplication of path definitions',
            'Make necessary updates to existing path regime if new path needed',
            'Maintain consistency across .env, data_paths.py, and config_loader.py',
        ],
        'validation_steps': {
            'before_adding_path': [
                'Search .env for similar path names',
                'Check if path can be derived from existing base paths',
                'Verify path not already constructed in data_paths.py',
                'Confirm path not already loaded in config_loader.py',
            ],
            'when_adding_new_path': [
                'Add to .env using variable interpolation from base paths',
                'Update config_loader.py to load the new path',
                'Update data_paths.py if directory auto-creation needed',
                'Maintain alphabetical/logical grouping in all three files',
            ]
        },
        'examples': {
            'bad_duplicate': {
                'scenario': 'Adding PARSER_LOGS_DIR when PARSER_LOG_DIR already exists',
                'problem': 'Creates confusion and duplication',
                'solution': 'Use existing PARSER_LOG_DIR instead',
            },
            'bad_recreate': {
                'scenario': 'Creating PARSER_CACHE_PATH when it can be derived from PARSER_DATA_ROOT',
                'problem': 'Unnecessary new variable, breaks interpolation pattern',
                'solution': 'Use ${PARSER_DATA_ROOT}/cache pattern in .env',
            },
            'good_addition': {
                'scenario': 'Need new PARSER_ARCHIVE_DIR that does not exist',
                'steps': [
                    '1. Checked .env - no archive path exists',
                    '2. Checked data_paths.py - no archive construction',
                    '3. Added to .env: PARSER_ARCHIVE_DIR=${PARSER_DATA_ROOT}/archive',
                    '4. Added to config_loader.py: self._get_path("PARSER_ARCHIVE_DIR")',
                    '5. Added to data_paths.py: ensure_directory(config.archive_dir)',
                ],
            }
        },
        'enforcement': 'Always read all three files before proposing any path-related changes'
    },

    'test_location': {
        'rule': 'TEST FILES TO BE WRITTEN AS THEY WILL BE EXECUTED UNDER /parser/tests/ directory',
        'description': 'Do not produce test files randomly',
        'structure': {
            'unit_tests': 'tests/unit/test_<component>/',
            'integration_tests': 'tests/integration/',
            'regression_tests': 'tests/regression/',
            'fixtures': 'tests/fixtures/',
        },
        'naming_convention': 'test_<functionality>.py',
        'never_create_in': [
            'Root directory',
            'xbrl_parser/ (main package)',
            'Random locations',
        ]
    },
    
    'file_header_path': {
        'rule': 'ALWAYS MAKE SURE THAT THE PATH INFO COMMENT AT THE TOP OF THE PY FILE SCRIPT',
        'description': 'Every Python file must have a path comment starting from project root directory',
        'critical': 'Add this path comment when writing a new file',
        'requirement': 'If any previously created file does not have this info, add it',
        'format': {
            'single_line': '# Path: xbrl_parser/foundation/xml_parser.py',
            'multi_line_docstring': '''"""
Path: xbrl_parser/foundation/xml_parser.py

Module description here.
"""''',
            'preferred': 'Single line comment before module docstring',
        },
        'examples': {
            'correct_format': '''# Path: xbrl_parser/models/config.py
"""
Configuration models for XBRL Parser.

This module defines the ParserConfig dataclass and related configuration structures.
"""

from dataclasses import dataclass
from typing import Optional
''',
            'core_module': '''# Path: core/config_loader.py
"""
Configuration Loader

Centralized configuration management for the XBRL Parser.
"""

import os
from pathlib import Path
''',
            'test_file': '''# Path: tests/unit/test_foundation/test_xml_parser.py
"""
Unit tests for XML parser component.
"""

import pytest
from xbrl_parser.foundation import XMLParser
''',
        },
        'placement': [
            '1. Very first line of the file (line 1)',
            '2. Before any imports',
            '3. Before module docstring',
            '4. Format: # Path: relative/path/from/project/root.py',
        ],
        'path_format_rules': {
            'start_from': 'Project root directory (parser/)',
            'use_forward_slashes': 'Always use / (not backslash)',
            'no_leading_slash': 'Do not start with /',
            'include_filename': 'Must include the .py extension',
            'examples': [
                'xbrl_parser/foundation/xml_parser.py',
                'core/config_loader.py',
                'tests/unit/test_models/test_config.py',
                'xbrl_parser/taxonomy/linkbase_loader.py',
            ],
        },
        'when_to_add': [
            'When creating any new Python file',
            'When refactoring existing files that lack this header',
            'When reviewing code - add if missing',
        ],
        'benefits': [
            'Immediately know file location in project structure',
            'Helps with navigation in flat file listings',
            'Aids in debugging and code review',
            'Essential when files are uploaded flat to Claude',
        ],
        'enforcement': 'Check every Python file has this path comment as first line'
    },

    'phase_instructions': {
        'rule': 'FOLLOW THE PHASE INSTRUCTIONS FOR THE RELEVANT SECTION',
        'description': 'Read the implementation_phases.txt to understand the general plan and structure',
        'reference_files': [
            'COMPLETE_PARSER_ROADMAP_CONCISE.md',
            'implementation_phases.txt',
        ],
        'approach': 'Phase-by-phase implementation',
        'order': [
            'Phase 1: Foundation',
            'Phase 2: Components', 
            'Phase 3: Data Models',
            # ... etc
        ]
    },

    'ascii_only': {
        'rule': 'ALWAYS USE ASCII CODES ON ALL CODING AND OUTPUT',
        'description': 'No emoji should be used at any point on any part of this project',
        'applies_to': [
            'Code scripts',
            'Code lines',
            'Comments',
            'Docstrings',
            'Console output',
            'Log files',
            'Error messages',
            'User-facing messages',
            'Debug output',
            'Reports',
            'Documentation',
        ],
        'forbidden': [
            'Emoji characters (U+1F300 to U+1F9FF)',
            'Unicode symbols beyond ASCII',
            'Special characters like: [OK] [FAIL] [WARNING] ★ ►',
        ],
        'allowed': [
            'ASCII characters (0x00 to 0x7F)',
            'Standard punctuation',
            'Letters a-z, A-Z',
            'Numbers 0-9',
            'Common symbols: + - * / = ( ) [ ] { } < > ! ? . , : ; @ # $ % & _',
        ],
        'rationale': 'Ensures compatibility across all systems, terminals, and log viewers',
        'replacement_guide': {
            'checkmark': '[OK]', 'success': '[SUCCESS]', 'done': '[DONE]',
            'cross': '[FAIL]', 'error': '[ERROR]', 'x': '[X]',
            'warning': '[WARN]', 'caution': '[!]',
            'arrow_right': '->',
            'bullet': '*' or '-',
            'star': '*',
        },
        'enforcement': 'All output must use ASCII-safe alternatives'
    }
}

# ============================================================================
# DESIGN PRINCIPLES (PROJECT-SPECIFIC)
# ============================================================================

DESIGN_PRINCIPLES = {
    'modular': {
        'description': 'Each package is independently importable',
        'requirement': 'Components can work standalone',
        'benefit': 'Reusability in other projects',
    },
    
    'reusable': {
        'description': 'Components can be used in other projects (e.g., mapper)',
        'requirement': 'Clear interfaces, minimal dependencies',
        'example': 'Mapper project should be able to import and use parser components',
    },
    
    'testable': {
        'description': 'Clear boundaries enable unit testing',
        'requirement': 'Each component testable in isolation',
        'target': '95%+ code coverage',
    },
    
    'typed': {
        'description': 'All modules use type hints',
        'requirement': 'Type hints on all public APIs',
        'tool': 'mypy for static type checking',
    },
    
    'documented': {
        'description': 'Each module has docstrings',
        'requirement': 'Comprehensive docstrings for all public APIs',
        'format': 'Google or NumPy style docstrings',
    },
    
    'standards_compliant': {
        'description': 'Follows Python packaging standards',
        'requirements': [
            'PEP 8 compliance',
            'setup.py or pyproject.toml',
            'Proper package structure',
            'Version management',
        ]
    }
}


# ============================================================================
# VALIDATION FUNCTIONS FOR PROJECT PRINCIPLES
# ============================================================================

def validate_no_hardcode(code_line: str, filepath: str = "") -> tuple[bool, list[str]]:
    """
    Check if code line contains hardcoded values.
    
    Args:
        code_line: Line of code to check
        filepath: Path to file (for context)
    
    Returns:
        (is_valid, violations) tuple
    """
    violations = []
    line_lower = code_line.lower()
    
    # Check for hardcoded URLs/URIs
    for pattern in PROJECT_PRINCIPLES['no_hardcode']['forbidden_patterns']:
        if pattern.lower() in line_lower:
            # Check if it's in a comment or docstring
            if '#' in code_line and code_line.index('#') < code_line.lower().index(pattern.lower()):
                continue  # It's in a comment
            if '"""' in code_line or "'''" in code_line:
                continue  # It's in a docstring
            
            violations.append(f"Hardcoded pattern '{pattern}' found. Use config_loader.py or environment variables.")
    
    return (len(violations) == 0, violations)


def validate_market_agnostic(code: str, filepath: str) -> tuple[bool, list[str]]:
    """
    Check if market-specific code is in correct location.
    
    Args:
        code: Code to check
        filepath: Path to file
    
    Returns:
        (is_valid, violations) tuple
    """
    violations = []
    code_lower = code.lower()
    
    # Check if file is in market directory
    is_market_dir = 'xbrl_parser/market/' in filepath or '/market/' in filepath
    
    if not is_market_dir:
        # Check for market-specific keywords
        for keyword in PROJECT_PRINCIPLES['market_agnostic']['market_keywords']:
            if keyword in code_lower:
                # Check if it's just in a comment/docstring
                if f'# {keyword}' in code_lower or f'"""{keyword}' in code_lower:
                    continue
                
                violations.append(
                    f"Market-specific keyword '{keyword}' found in non-market file. "
                    f"Move to xbrl_parser/market/ or use market registry."
                )
    
    return (len(violations) == 0, violations)


def validate_output_location(filepath: str) -> tuple[bool, str]:
    """
    Check if output file is in correct location.
    
    Args:
        filepath: Path where output will be written
    
    Returns:
        (is_valid, message) tuple
    """
    # Check if it's a data file extension
    data_extensions = ['.json', '.xml', '.htm', '.html', '.txt', '.csv']
    is_data_file = any(filepath.endswith(ext) for ext in data_extensions)
    
    if not is_data_file:
        return (True, "Not a data file")
    
    # Check if writing to forbidden location
    forbidden = PROJECT_PRINCIPLES['output_location']['never_write_to']
    for forbidden_dir in forbidden:
        if forbidden_dir in filepath:
            return (
                False, 
                f"VIOLATION: Attempting to write data file to program directory '{forbidden_dir}'. "
                f"Ask user for data partition location."
            )
    
    # Check if writing to allowed location
    allowed = PROJECT_PRINCIPLES['output_location']['allowed_write_to']
    is_allowed = any(allowed_dir in filepath for allowed_dir in allowed)
    
    if not is_allowed:
        return (
            False,
            f"VIOLATION: Output location not in allowed directories. "
            f"Allowed: {allowed}. Ask user for correct data partition location."
        )
    
    return (True, "Output location valid")


def validate_test_location(filepath: str) -> tuple[bool, str]:
    """
    Check if test file is in correct location.
    
    Args:
        filepath: Path to test file
    
    Returns:
        (is_valid, message) tuple
    """
    if not filepath.startswith('test_') and 'test_' not in filepath:
        return (True, "Not a test file")
    
    correct_location = filepath.startswith('tests/') or '/tests/' in filepath
    
    if not correct_location:
        return (
            False,
            f"VIOLATION: Test file not in tests/ directory. "
            f"Structure: {PROJECT_PRINCIPLES['test_location']['structure']}"
        )
    
    return (True, "Test location valid")

def validate_ascii_only(text: str, context: str = "") -> tuple[bool, list[str]]:
    """
    Check if text contains only ASCII characters (no emojis).
    
    Args:
        text: Text to check
        context: Context for error message (e.g., "line 42")
    
    Returns:
        (is_valid, violations) tuple
    """
    violations = []
    
    for i, char in enumerate(text):
        # Check if character is outside ASCII range (0x00 to 0x7F)
        if ord(char) > 127:
            violations.append(
                f"Non-ASCII character '{char}' (U+{ord(char):04X}) found at position {i}"
                + (f" in {context}" if context else "")
            )
    
    return (len(violations) == 0, violations)

def validate_path_addition(path_name: str, files_content: dict) -> tuple[bool, list[str]]:
    """
    Check if a path already exists in the configuration regime.
    
    Args:
        path_name: Name of the path to add (e.g., 'PARSER_ARCHIVE_DIR')
        files_content: Dict with keys '.env', 'data_paths.py', 'config_loader.py'
    
    Returns:
        (is_duplicate, suggestions) tuple
    """
    suggestions = []
    
    # Check .env
    if path_name in files_content.get('.env', ''):
        suggestions.append(f"Path '{path_name}' already defined in .env")
        return (True, suggestions)
    
    # Check for similar names
    similar_patterns = [
        path_name.lower(),
        path_name.replace('_DIR', '').replace('_PATH', ''),
    ]
    
    for pattern in similar_patterns:
        if pattern in files_content.get('.env', '').lower():
            suggestions.append(f"Similar path containing '{pattern}' found in .env")
    
    # Check if it can be derived
    base_paths = ['PARSER_DATA_ROOT', 'PARSER_PROGRAM_DIR', 'PARSER_LOADERS_ROOT']
    for base in base_paths:
        if base in files_content.get('.env', ''):
            suggestions.append(f"Consider deriving from ${{{base}}}/... instead of new variable")
    
    if suggestions:
        return (True, suggestions)
    
    return (False, ["Path appears to be new - proceed with addition"])

def check_project_compliance(code: str, filepath: str) -> dict:
    """
    Run all project compliance checks.
    
    Args:
        code: Code to check
        filepath: Path to file
    
    Returns:
        dict with results of all checks
    """
    results = {
        'valid': True,
        'violations': []
    }
    
    # Check each line for hardcoded values
    for i, line in enumerate(code.split('\n'), 1):
        is_valid, violations = validate_no_hardcode(line, filepath)
        if not is_valid:
            results['valid'] = False
            for v in violations:
                results['violations'].append(f"Line {i}: {v}")
    
    # Check market agnostic
    is_valid, violations = validate_market_agnostic(code, filepath)
    if not is_valid:
        results['valid'] = False
        results['violations'].extend(violations)
    
    # Check output location if applicable
    is_valid, message = validate_output_location(filepath)
    if not is_valid:
        results['valid'] = False
        results['violations'].append(message)
    
    # Check test location if applicable
    is_valid, message = validate_test_location(filepath)
    if not is_valid:
        results['valid'] = False
        results['violations'].append(message)
    
    return results


# ============================================================================
# PROJECT CHECKLIST (IN ADDITION TO CODE REVIEW CHECKLIST)
# ============================================================================

PROJECT_CHECKLIST = [
    "[OK] No hardcoded URLs, paths, or constants (use config_loader.py)",
    "[OK] ASCII-only output (no emojis in code, comments, or output),"
    "[OK] Checked .env, data_paths.py, config_loader.py before adding any path",
    "[OK] File header path comment added (# Path: module/file.py)",
    "[OK] No market-specific code outside xbrl_parser/market/",
    "[OK] No taxonomy-specific logic (system is taxonomy agnostic)",
    "[OK] Output files written to data partition, not program files",
    "[OK] Test files in tests/ directory with proper structure",
    "[OK] Following current phase instructions from roadmap",
    "[OK] All modules independently importable",
    "[OK] Components reusable in other projects",
    "[OK] Clear boundaries for testing",
    "[OK] Type hints on all public APIs",
    "[OK] Comprehensive docstrings",
    "[OK] PEP 8 and packaging standards followed",
]


def print_project_checklist():
    """Print project-specific checklist."""
    print("=" * 70)
    print("PROJECT-SPECIFIC CHECKLIST")
    print("=" * 70)
    for i, item in enumerate(PROJECT_CHECKLIST, 1):
        print(f"{i:2d}. [ ] {item}")
    print("=" * 70)


# ============================================================================
# CRITICAL THRESHOLDS - Memorize these!
# ============================================================================

THRESHOLDS = {
    # Function Complexity
    'function': {
        'cyclomatic_warning': 10,
        'cyclomatic_error': 15,
        'cyclomatic_obvious_simple': 5,
        'cyclomatic_acceptable': 10,
        
        'parameters_obvious_simple': 4,
        'parameters_acceptable': 6,
        
        'nesting_obvious_simple': 3,
        'nesting_acceptable': 5,
        
        'length_obvious_simple': 20,  # statements
        'length_acceptable': 40,
    },
    
    # Class Design
    'class': {
        'max_public_methods_warning': 15,
        'max_public_methods_error': 25,
        'max_methods_total': 10,
        'max_responsibilities': 1,  # 2-3 warning, >3 error
    },
    
    # Interface Segregation
    'interface': {
        'max_methods_warning': 7,
        'max_methods_error': 12,
    },
    
    # Coupling & Cohesion
    'lchc': {
        'lcom_excellent': 0.3,
        'lcom_good': 0.5,
        'lcom_critical': 0.7,
        
        'coupling_excellent': 5,
        'coupling_good': 10,
        'coupling_critical': 15,
    },
    
    # Dependency Inversion
    'dip': {
        'max_concrete_deps_high_level': 2,
        'max_concrete_deps_mid_level': 5,
        'min_abstraction_ratio': 0.6,
    },
    
    # File Structure
    'file': {
        'max_line_length': 88,
        'max_lines_warning': 300,
        'max_lines_error': 500,
    },
    
    # Architecture
    'architecture': {
        'max_distance_main_sequence': 0.5,
        'max_distance_critical': 0.7,
        'max_distance_excellent': 0.2,
        'unstable_depends_stable_threshold': 0.3,
        'co_change_threshold': 5,
    }
}


# ============================================================================
# RESPONSIBILITY DETECTION KEYWORDS
# ============================================================================

RESPONSIBILITY_KEYWORDS = {
    'data_access': [
        'database', 'db', 'query', 'sql', 'select', 'insert', 'update', 
        'delete', 'repository', 'dao', 'fetch', 'store', 'persist', 'crud'
    ],
    'presentation': [
        'render', 'display', 'view', 'template', 'html', 'format', 
        'print', 'show', 'present', 'ui', 'gui'
    ],
    'validation': [
        'validate', 'check', 'verify', 'ensure', 'assert', 
        'is_valid', 'validator', 'sanitize'
    ],
    'logging': [
        'log', 'logger', 'debug', 'info', 'warn', 'error', 'trace'
    ],
    'communication': [
        'send', 'receive', 'email', 'http', 'request', 'response', 
        'api', 'client', 'webhook', 'notify', 'message', 'publish', 'subscribe'
    ],
    'file_io': [
        'file', 'read', 'write', 'open', 'close', 'path', 
        'directory', 'save_to', 'load_from'
    ],
    'serialization': [
        'serialize', 'deserialize', 'json', 'xml', 'yaml', 
        'parse', 'encode', 'decode', 'marshal', 'unmarshal'
    ],
    'authentication': [
        'auth', 'login', 'logout', 'token', 'password', 
        'credential', 'authenticate', 'authorize', 'permission'
    ],
    'caching': [
        'cache', 'redis', 'memcache', 'cached', 'memoize'
    ],
    'configuration': [
        'config', 'setting', 'environment', 'env', 'configure'
    ]
}


# ============================================================================
# MODULE LEVEL CLASSIFICATION
# ============================================================================

MODULE_LEVELS = {
    'high_level': [
        'service', 'usecase', 'use_case', 'handler', 'controller', 
        'manager', 'coordinator', 'processor', 'orchestrator', 'workflow'
    ],
    'low_level': [
        'database', 'db', 'sql', 'mysql', 'postgres', 'mongo',
        'file', 'filesystem', 'io', 'stream',
        'http', 'rest', 'api', 'client', 'request',
        'email', 'smtp', 'mail',
        'cache', 'redis', 'memcache',
        'logger', 'log',
        'config', 'setting', 'environment'
    ],
    'abstraction_indicators': [
        'ABC', 'Abstract', 'Interface', 'Protocol', 'Base'
    ]
}


# ============================================================================
# SECURITY PATTERNS
# ============================================================================

SECURITY = {
    'dangerous_functions': ['eval(', 'exec(', 'compile(', '__import__('],
    'credential_keywords': [
        'password', 'passwd', 'pwd', 'secret', 'token', 
        'api_key', 'apikey', 'access_key', 'private_key'
    ],
    'hardcoded_path_patterns': ['/home/', 'C:\\', '/usr/', '/var/'],
}


# ============================================================================
# CODE QUALITY MARKERS
# ============================================================================

CODE_QUALITY = {
    'compound_verbs': ['and', 'then', 'also', 'plus', 'with', 'after', 'before'],
    'actor_indicators': {
        'admin': 'Administrator',
        'user': 'End User',
        'customer': 'Customer',
        'manager': 'Manager',
        'finance': 'Finance',
        'marketing': 'Marketing',
        'report': 'Reporting',
        'audit': 'Audit',
        'analytics': 'Analytics',
        'billing': 'Billing'
    },
    'comment_markers': {
        'TODO': 'todo',       # INFO
        'FIXME': 'fixme',     # WARNING
        'HACK': 'hack',       # WARNING
        'XXX': 'xxx',         # WARNING
        'BUG': 'bug'          # WARNING
    },
    'code_keywords': [
        'import ', 'def ', 'class ', 'if ', 'for ', 'return ', '= '
    ],
    'common_numbers': [0, 1, -1, 2, 10, 100, 1000],
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_function_complexity(cyclomatic: int, length: int, 
                              nesting: int, params: int) -> tuple[str, str]:
    """
    Check function against Hoare's simplicity thresholds.
    
    Args:
        cyclomatic: Cyclomatic complexity
        length: Number of statements
        nesting: Maximum nesting depth
        params: Number of parameters
    
    Returns:
        (severity, message) tuple
        severity: 'error', 'warning', 'info', or 'ok'
    """
    t = THRESHOLDS['function']
    
    # Check if acceptably clear
    if (cyclomatic > t['cyclomatic_acceptable'] or
        length > t['length_acceptable'] or
        nesting > t['nesting_acceptable'] or
        params > t['parameters_acceptable']):
        return ('error', 
                f"Dangerously complex: cyclomatic={cyclomatic}, "
                f"length={length}, nesting={nesting}, params={params}")
    
    # Check if obviously simple
    if (cyclomatic <= t['cyclomatic_obvious_simple'] and
        length <= t['length_obvious_simple'] and
        nesting <= t['nesting_obvious_simple'] and
        params <= t['parameters_obvious_simple']):
        return ('info', 
                f"Obviously simple: cyclomatic={cyclomatic}, "
                f"length={length}, nesting={nesting}, params={params}")
    
    # Between obvious and acceptable
    return ('warning',
            f"Acceptably clear but not obviously simple: "
            f"cyclomatic={cyclomatic}, length={length}, "
            f"nesting={nesting}, params={params}")


def check_class_methods(public_methods: int, is_interface: bool = False) -> tuple[str, str]:
    """
    Check class/interface against ISP thresholds.
    
    Args:
        public_methods: Number of public methods
        is_interface: Whether this is an interface
    
    Returns:
        (severity, message) tuple
    """
    if is_interface:
        t = THRESHOLDS['interface']
        if public_methods > t['max_methods_error']:
            return ('error', f"Interface has {public_methods} methods (critical >12)")
        elif public_methods > t['max_methods_warning']:
            return ('warning', f"Interface has {public_methods} methods (recommend <7)")
    else:
        t = THRESHOLDS['class']
        if public_methods > t['max_public_methods_error']:
            return ('error', f"Class has {public_methods} methods (critical >25)")
        elif public_methods > t['max_public_methods_warning']:
            return ('warning', f"Class has {public_methods} methods (recommend <15)")
    
    return ('ok', f"Method count acceptable: {public_methods}")


def check_lcom(lcom: float, num_methods: int) -> tuple[str, str]:
    """
    Check LCOM (Lack of Cohesion of Methods) value.
    
    Args:
        lcom: LCOM value (0.0 to 1.0)
        num_methods: Number of methods in class
    
    Returns:
        (severity, message) tuple
    """
    t = THRESHOLDS['lchc']
    
    if lcom > t['lcom_critical']:
        return ('error', 
                f"Very low cohesion (LCOM={lcom:.2f}). "
                f"Methods don't share instance variables.")
    
    if lcom > t['lcom_good']:
        return ('warning', f"Low cohesion (LCOM={lcom:.2f})")
    
    if lcom <= t['lcom_excellent'] and num_methods >= 3:
        return ('info', f"Excellent cohesion (LCOM={lcom:.2f})")
    
    return ('ok', f"Acceptable cohesion (LCOM={lcom:.2f})")


def check_coupling(efferent_coupling: int) -> tuple[str, str]:
    """
    Check efferent coupling (outgoing dependencies).
    
    Args:
        efferent_coupling: Number of classes this class depends on
    
    Returns:
        (severity, message) tuple
    """
    t = THRESHOLDS['lchc']
    
    if efferent_coupling > t['coupling_critical']:
        return ('error', f"Very high coupling (Ce={efferent_coupling})")
    
    if efferent_coupling > t['coupling_good']:
        return ('warning', f"High coupling (Ce={efferent_coupling})")
    
    if efferent_coupling <= t['coupling_excellent']:
        return ('info', f"Low coupling (Ce={efferent_coupling})")
    
    return ('ok', f"Acceptable coupling (Ce={efferent_coupling})")


def detect_responsibilities(class_name: str, method_names: list[str]) -> list[str]:
    """
    Detect what responsibilities a class has based on naming.
    
    Args:
        class_name: Name of the class
        method_names: List of method names
    
    Returns:
        List of detected responsibility types
    """
    text = (class_name + ' ' + ' '.join(method_names)).lower()
    
    responsibilities = []
    for resp_type, keywords in RESPONSIBILITY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                responsibilities.append(resp_type)
                break
    
    return responsibilities if responsibilities else ['business_logic']


def is_security_risk(code_line: str) -> tuple[bool, str]:
    """
    Check if code line contains security risks.
    
    Args:
        code_line: Line of code to check
    
    Returns:
        (is_risk, risk_type) tuple
    """
    line_lower = code_line.lower()
    
    # Check dangerous functions
    for func in SECURITY['dangerous_functions']:
        if func in code_line:
            return (True, f"Dangerous function: {func}")
    
    # Check hardcoded credentials
    if '=' in code_line:
        for keyword in SECURITY['credential_keywords']:
            if keyword in line_lower:
                return (True, "Possible hardcoded credential")
    
    # Check shell injection
    if 'shell=True' in code_line:
        return (True, "Command injection risk")
    
    # Check pickle
    if 'pickle.load' in code_line:
        return (True, "Unsafe deserialization")
    
    return (False, "")


# ============================================================================
# DESIGN PATTERNS
# ============================================================================

DESIGN_PATTERNS = {
    'facade': {
        'required_evidence': [
            'SRP violation',
            'Excellent cohesion (LCOM < 0.3)',
            'High delegation ratio (>70%)',
            'Multiple imports (>3)'
        ],
        'justifies_violations': ['srp_violation', 'high_complexity'],
    },
    'repository': {
        'name_indicators': ['repository', 'repo'],
        'justifies_violations': ['srp_violation'],
    },
    'coordinator': {
        'name_indicators': ['coordinator', 'orchestrator', 'manager', 'controller'],
        'justifies_violations': ['srp_violation', 'lchc_violation', 'high_coupling'],
    }
}


# ============================================================================
# DECISION TREE
# ============================================================================

def class_design_decision_tree(class_info: dict) -> list[tuple[str, str]]:
    """
    Run class through design decision tree.
    
    Args:
        class_info: Dictionary with keys:
            - responsibilities: int
            - public_methods: int
            - lcom: float
            - coupling: int
            - is_high_level: bool
            - concrete_deps: int
    
    Returns:
        List of (severity, message) tuples for all violations
    """
    issues = []
    
    # 1. Check SRP
    if class_info.get('responsibilities', 1) > 1:
        issues.append(('warning', f"Multiple responsibilities: {class_info['responsibilities']}"))
    
    # 2. Check DIP
    if class_info.get('is_high_level') and class_info.get('concrete_deps', 0) > 2:
        issues.append(('error', "High-level depends on too many concrete classes"))
    
    # 3. Check ISP
    if class_info.get('public_methods', 0) > 15:
        issues.append(('warning', f"Too many public methods: {class_info['public_methods']}"))
    
    # 4. Check Cohesion
    if class_info.get('lcom', 0) > 0.5:
        issues.append(('warning', f"Low cohesion: LCOM={class_info['lcom']:.2f}"))
    
    # 5. Check Coupling
    if class_info.get('coupling', 0) > 10:
        issues.append(('warning', f"High coupling: {class_info['coupling']} dependencies"))
    
    return issues if issues else [('ok', "Class design is good")]


# ============================================================================
# CODE REVIEW CHECKLIST
# ============================================================================

CODE_REVIEW_CHECKLIST = [
    "No function has cyclomatic complexity >10",
    "No function has >4 parameters",
    "No function is >40 lines",
    "No class has >15 public methods",
    "Each class has single responsibility",
    "High-level classes depend on abstractions",
    "No eval/exec/shell=True without justification",
    "No hardcoded credentials or paths",
    "No mutable default arguments",
    "No bare except clauses",
    "No star imports",
    "All public APIs have docstrings",
    "No TODO/FIXME older than sprint",
    "No magic numbers",
    "PEP 8 naming conventions followed",
    "File <300 lines",
    "Lines <88 characters",
]


def print_checklist():
    """Print code review checklist."""
    print("=" * 70)
    print("CODE REVIEW CHECKLIST")
    print("=" * 70)
    for i, item in enumerate(CODE_REVIEW_CHECKLIST, 1):
        print(f"{i:2d}. [ ] {item}")
    print("=" * 70)


def print_all_checklists():
    """Print both project and code review checklists."""
    print_project_checklist()
    print()
    print_checklist()


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("XBRL Parser - Python Coding Standards & Project Instructions")
    print("=" * 70)
    print()
    
    # Example 1: Check function complexity
    print("Example 1: Function Complexity Check")
    severity, msg = check_function_complexity(
        cyclomatic=12,
        length=45,
        nesting=4,
        params=5
    )
    print(f"  Severity: {severity.upper()}")
    print(f"  Message: {msg}")
    print()
    
    # Example 2: Check class methods
    print("Example 2: Class Method Count Check")
    severity, msg = check_class_methods(public_methods=20, is_interface=False)
    print(f"  Severity: {severity.upper()}")
    print(f"  Message: {msg}")
    print()
    
    # Example 3: Check LCOM
    print("Example 3: Cohesion Check")
    severity, msg = check_lcom(lcom=0.65, num_methods=8)
    print(f"  Severity: {severity.upper()}")
    print(f"  Message: {msg}")
    print()
    
    # Example 4: Detect responsibilities
    print("Example 4: Responsibility Detection")
    responsibilities = detect_responsibilities(
        class_name="UserDatabaseEmailManager",
        method_names=["get_user", "save_user", "send_email", "validate_email"]
    )
    print(f"  Detected: {', '.join(responsibilities)}")
    if len(responsibilities) > 1:
        print("  WARNING: Multiple responsibilities detected!")
    print()
    
    # Example 5: Security check
    print("Example 5: Security Risk Check")
    test_lines = [
        "result = eval(user_input)",
        "PASSWORD = 'secret123'",
        "subprocess.run(cmd, shell=True)"
    ]
    for line in test_lines:
        is_risk, risk_type = is_security_risk(line)
        if is_risk:
            print(f"  RISK in '{line}'")
            print(f"    Type: {risk_type}")
    print()
    
    # Example 6: Project compliance check
    print("Example 6: Project Compliance Check")
    test_code = '''
def fetch_data():
    url = "https://xbrl.sec.gov/taxonomy.xsd"  # HARDCODE!
    response = requests.get(url)
    return response.text
'''
    result = check_project_compliance(test_code, "xbrl_parser/foundation/loader.py")
    print(f"  Valid: {result['valid']}")
    if result['violations']:
        print("  Violations:")
        for v in result['violations']:
            print(f"    - {v}")
    print()
    
    # Example 7: Output location validation
    print("Example 7: Output Location Validation")
    test_paths = [
        "output/parsed_report/filing_123.json",  # Good
        "xbrl_parser/models/report.json",        # Bad!
    ]
    for path in test_paths:
        is_valid, message = validate_output_location(path)
        status = "[OK] VALID" if is_valid else "[FAIL] INVALID"
        print(f"  {status}: {path}")
        if not is_valid:
            print(f"    {message}")
    print()
    
    # Print all checklists
    print()
    print_all_checklists()
