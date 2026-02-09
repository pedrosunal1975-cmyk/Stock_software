"""
Parse Phase Helper Functions

Helper functions for the parsing phase of workflow orchestration.
Extracted from WorkflowOrchestrator to reduce complexity.
"""

from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def extract_form_type_from_path(filing_path: Path, fallback_form_type: str) -> str:
    """
    Extract actual form type from physical directory structure.

    User may enter "10K" but physical filing is in ".../filings/10-K/..."
    We must use the ACTUAL name from physical files, not user input.

    Structure: .../entities/{market}/{company}/filings/{FORM_TYPE}/{accession}/

    Args:
        filing_path: Path to filing directory
        fallback_form_type: Form type to use if extraction fails

    Returns:
        Actual form type from path, or fallback
    """
    parts = filing_path.parts

    try:
        # Find 'filings' in path and extract next directory as actual form type
        filings_idx = parts.index('filings')
        if filings_idx + 1 < len(parts):
            actual_form_type = parts[filings_idx + 1]
            logger.info(f"Detected actual form type from physical path: {actual_form_type}")
            return actual_form_type
    except (ValueError, IndexError):
        logger.warning(f"Could not extract form type from path, using: {fallback_form_type}")

    return fallback_form_type


def create_output_directory(
    parser_output: Path,
    market_id: str,
    company_name: str,
    form_type: str,
    filing_date: Optional[str]
) -> Path:
    """
    Create output directory for parsed filing.

    Args:
        parser_output: Base parser output directory
        market_id: Market identifier
        company_name: Company name (will be sanitized)
        form_type: Form type
        filing_date: Filing date string (YYYY-MM-DD) or None

    Returns:
        Created output directory path
    """
    # Sanitize company name for filesystem
    company_safe = company_name.replace(" ", "_").replace(",", "").replace(".", "")

    # Use filing date or 'unknown'
    date_str = filing_date if filing_date else "unknown"

    # Build path: {output}/{market}/{company}/{form_type}/{date}/
    output_dir = Path(parser_output) / market_id / company_safe / form_type / date_str
    output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir


def get_parser_output_directory(parser_config) -> Path:
    """
    Get parser output directory from config.

    Tries PARSER_OUTPUT_PARSED_DIR first, then PARSER_OUTPUT_DIR.
    Raises ValueError if neither is configured.

    Args:
        parser_config: Parser ConfigLoader instance

    Returns:
        Parser output directory path

    Raises:
        ValueError: If no output directory is configured
    """
    parser_output = parser_config.get('output_parsed_dir')

    if not parser_output:
        # Fallback to output_dir
        parser_output = parser_config.get('output_dir')

    if not parser_output:
        # FAIL if configuration missing - no hardcoded fallbacks
        raise ValueError(
            "Parser output directory not configured. "
            "Required: PARSER_OUTPUT_PARSED_DIR or PARSER_OUTPUT_DIR in .env"
        )

    return Path(parser_output)


def enrich_metadata(parsed, entity, downloaded_filing, actual_form_type):
    """
    Enrich parsed metadata with database information.

    Only fills in fields that parser couldn't extract from XBRL.
    Parser now extracts metadata from XBRL DEI facts, but we enrich with
    database info if parser couldn't find it (e.g., inline XBRL without DEI).

    Note: period_end_date must come from XBRL facts, not database.

    Args:
        parsed: ParsedFiling object
        entity: Entity database object
        downloaded_filing: DownloadedFiling database object
        actual_form_type: Actual form type from physical path

    Returns:
        None (modifies parsed in place)
    """
    if not parsed.metadata.document_type:
        parsed.metadata.document_type = actual_form_type

    if not parsed.metadata.filing_date:
        parsed.metadata.filing_date = (
            downloaded_filing.filing_search.filing_date
            if downloaded_filing.filing_search
            else None
        )

    # Note: period_end_date must come from XBRL facts, not database

    if not parsed.metadata.company_name:
        parsed.metadata.company_name = entity.company_name

    if not parsed.metadata.entity_identifier:
        parsed.metadata.entity_identifier = entity.market_entity_id

    if not parsed.metadata.market:
        parsed.metadata.market = entity.market_type

    if not parsed.metadata.regulatory_authority:
        parsed.metadata.regulatory_authority = (
            entity.market_type.upper() if entity.market_type else None
        )


def save_parsed_json(parsed, output_dir: Path) -> Path:
    """
    Serialize and save parsed filing as JSON.

    Args:
        parsed: ParsedFiling object
        output_dir: Output directory

    Returns:
        Path to saved JSON file
    """
    from parser.xbrl_parser.serialization.json_serializer import JSONSerializer

    serializer = JSONSerializer()
    json_output = serializer.serialize(parsed)

    json_file = output_dir / "parsed.json"
    json_file.write_text(json_output)

    return json_file
