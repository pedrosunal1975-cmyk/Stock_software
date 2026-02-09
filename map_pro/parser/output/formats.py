# Path: xbrl_parser/output/formats.py
"""
Output Format Constants and Utilities

Defines output formats and provides format validation utilities.
"""

from enum import Enum
from pathlib import Path


class OutputFormat(Enum):
    """Supported output formats."""
    JSON = "json"
    CSV = "csv"
    XLSX = "xlsx"
    TXT = "txt"
    HTML = "html"
    
    @classmethod
    def from_extension(cls, path: Path) -> 'OutputFormat':
        """
        Get format from file extension.
        
        Args:
            path: File path
            
        Returns:
            OutputFormat enum value
            
        Raises:
            ValueError: If extension not supported
        """
        ext = path.suffix.lstrip('.').lower()
        try:
            return cls(ext)
        except ValueError:
            raise ValueError(
                f"Unsupported output format: {ext}. "
                f"Supported formats: {', '.join([f.value for f in cls])}"
            )


class ExtractionTarget(Enum):
    """Data extraction targets."""
    FACTS = "facts"
    CONTEXTS = "contexts"
    UNITS = "units"
    CONCEPTS = "concepts"
    RELATIONSHIPS = "relationships"
    METADATA = "metadata"
    SUMMARY = "summary"
    ALL = "all"


# File extensions for each format
FORMAT_EXTENSIONS: dict[OutputFormat, str] = {
    OutputFormat.JSON: ".json",
    OutputFormat.CSV: ".csv",
    OutputFormat.XLSX: ".xlsx",
    OutputFormat.TXT: ".txt",
    OutputFormat.HTML: ".html",
}

# MIME types for each format
FORMAT_MIME_TYPES: dict[OutputFormat, str] = {
    OutputFormat.JSON: "application/json",
    OutputFormat.CSV: "text/csv",
    OutputFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    OutputFormat.TXT: "text/plain",
    OutputFormat.HTML: "text/html",
}

# CSV field size limit (avoid issues with large text blocks)
CSV_FIELD_SIZE_LIMIT = 131072  # 128KB


def validate_output_format(format_str: str) -> OutputFormat:
    """
    Validate and convert output format string.
    
    Args:
        format_str: Format string (e.g., 'json', 'csv')
        
    Returns:
        OutputFormat enum value
        
    Raises:
        ValueError: If format invalid
    """
    try:
        return OutputFormat(format_str.lower())
    except ValueError:
        valid_formats = ", ".join([f.value for f in OutputFormat])
        raise ValueError(
            f"Invalid output format: {format_str}. "
            f"Valid formats: {valid_formats}"
        )


def get_supported_formats() -> set[str]:
    """
    Get set of supported format strings.
    
    Returns:
        set of format strings
    """
    return {f.value for f in OutputFormat}


def get_extension(output_format: OutputFormat) -> str:
    """
    Get file extension for format.
    
    Args:
        output_format: Output format
        
    Returns:
        File extension with leading dot
    """
    return FORMAT_EXTENSIONS[output_format]


def get_mime_type(output_format: OutputFormat) -> str:
    """
    Get MIME type for format.
    
    Args:
        output_format: Output format
        
    Returns:
        MIME type string
    """
    return FORMAT_MIME_TYPES[output_format]


def ensure_extension(path: Path, output_format: OutputFormat) -> Path:
    """
    Ensure path has correct extension for format.
    
    Args:
        path: File path
        output_format: Output format
        
    Returns:
        Path with correct extension
    """
    correct_ext = get_extension(output_format)
    
    if path.suffix.lower() != correct_ext:
        return path.with_suffix(correct_ext)
    
    return path


__all__ = [
    'OutputFormat',
    'ExtractionTarget',
    'FORMAT_EXTENSIONS',
    'FORMAT_MIME_TYPES',
    'CSV_FIELD_SIZE_LIMIT',
    'validate_output_format',
    'get_supported_formats',
    'get_extension',
    'get_mime_type',
    'ensure_extension',
]