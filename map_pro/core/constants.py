"""
Workflow Orchestrator Constants

Progress percentages and configuration values for workflow coordination.
"""

# ============================================================================
# Progress Tracking Constants
# ============================================================================

# Progress percentages for each phase
PROGRESS_DATABASE_INIT = 2
PROGRESS_SEARCH_START = 10
PROGRESS_DOWNLOAD_START = 30
PROGRESS_PARSE_START = 60
PROGRESS_MAP_START = 85
PROGRESS_COMPLETE = 100

# Progress ranges for each phase (for reference)
PROGRESS_RANGE_DATABASE = (0, 5)      # 0-5%
PROGRESS_RANGE_SEARCH = (5, 20)       # 5-20%
PROGRESS_RANGE_DOWNLOAD = (20, 50)    # 20-50%
PROGRESS_RANGE_PARSE = (50, 75)       # 50-75%
PROGRESS_RANGE_MAP = (75, 100)        # 75-100%

# ============================================================================
# Display Constants
# ============================================================================

SEPARATOR_WIDTH = 80
SEPARATOR_CHAR = "="

# ============================================================================
# Path Components
# ============================================================================

# Directory structure components
FILINGS_DIR_NAME = "filings"
PARSED_JSON_FILENAME = "parsed.json"
GLOB_PATTERN_PARSED_FILES = "*/*/*/parsed.json"

# ============================================================================
# Status Values
# ============================================================================

PARSE_STATUS_PENDING = "pending"
PARSE_STATUS_COMPLETED = "completed"
PARSE_STATUS_FAILED = "failed"

# ============================================================================
# Configuration Keys
# ============================================================================

CONFIG_KEY_OUTPUT_PARSED_DIR = "output_parsed_dir"
CONFIG_KEY_OUTPUT_DIR = "output_dir"
