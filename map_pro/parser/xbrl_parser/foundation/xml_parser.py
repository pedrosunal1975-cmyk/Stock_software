# Path: xbrl_parser/foundation/xml_parser.py
"""
XML Processing Engine

Robust XML parsing with comprehensive error recovery, line tracking,
encoding detection, and security features.

This module provides the core XML parsing infrastructure for XBRL documents.
Handles malformed content gracefully and tracks all errors for reporting.

Features:
- Error recovery mode (parse despite errors)
- Line/column number tracking
- Multi-encoding support with fallbacks
- XXE (XML External Entity) attack protection
- Billion laughs attack prevention
- Namespace preservation
- Well-formedness and validation separation
"""

from lxml import etree
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
import logging

from ...core.config_loader import ConfigLoader
from ..models.error import (
    ParsingError,
    ErrorSeverity,
    ErrorCategory
)


@dataclass
class XMLParseResult:
    """
    Result of XML parsing operation.
    
    Contains parsed tree, errors, warnings, and metadata about
    the parsing process.
    
    Attributes:
        tree: Parsed XML tree (None if fatal error)
        root: Root element (None if fatal error)
        errors: list of errors encountered
        warnings: list of warnings encountered
        encoding: Detected or used encoding
        well_formed: Whether XML is well-formed
        valid: Whether XML is valid against schema (if validated)
        source_file: Path to source file
        recovery_applied: Whether error recovery was used
    """
    tree: Optional[etree._ElementTree]
    root: Optional[etree._Element]
    errors: list[ParsingError] = field(default_factory=list)
    warnings: list[ParsingError] = field(default_factory=list)
    encoding: str = "utf-8"
    well_formed: bool = True
    valid: bool = False
    source_file: Optional[Path] = None
    recovery_applied: bool = False
    
    def has_critical_errors(self) -> bool:
        """Check if result has any critical errors."""
        return any(e.severity == ErrorSeverity.CRITICAL for e in self.errors)
    
    def has_errors(self) -> bool:
        """Check if result has any errors (including critical)."""
        return len(self.errors) > 0
    
    def get_error_count(self) -> int:
        """Get total error count."""
        return len(self.errors)
    
    def get_warning_count(self) -> int:
        """Get total warning count."""
        return len(self.warnings)


class XMLParser:
    """
    XML parser with error recovery and comprehensive tracking.
    
    Provides robust XML parsing for XBRL documents with:
    - Error recovery mode (continue parsing despite errors)
    - Line/column tracking for all elements
    - Multi-encoding support with automatic fallback
    - Security hardening (XXE protection, depth limits)
    - Namespace preservation
    - Detailed error reporting
    
    Example:
        config = ConfigLoader()
        parser = XMLParser(config)
        result = parser.parse_file(Path("filing.xml"))
        
        if result.well_formed:
            root = result.root
            # Process XML...
        else:
            for error in result.errors:
                print(f"Error: {error.message}")
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize XML parser.
        
        Args:
            config: Optional ConfigLoader instance (creates new if not provided)
        """
        self.config = config if config else ConfigLoader()
        self.logger = logging.getLogger(__name__)
        
        # Get configuration
        self.disable_external_entities = self.config.get('disable_external_entities', True)
        self.max_xml_depth = self.config.get('max_xml_depth', 100)
        self.default_encoding = self.config.get('default_encoding', 'utf-8')
        self.auto_detect_encoding = self.config.get('auto_detect_encoding', True)
        
        # Parse encoding fallbacks from config
        fallback_str = self.config.get('encoding_fallbacks', 'utf-8,latin-1,cp1252')
        self.encoding_fallbacks = [e.strip() for e in fallback_str.split(',')]
        
        # Initialize error tracking
        self.errors: list[ParsingError] = []
        self.warnings: list[ParsingError] = []
    
    def parse_file(self, file_path: Path) -> XMLParseResult:
        """
        Parse XML file with comprehensive error tracking.
        
        Uses error recovery mode to parse even malformed XML.
        Tracks all errors and warnings for reporting.
        
        Args:
            file_path: Path to XML file
            
        Returns:
            XMLParseResult with parsed tree and error information
            
        Example:
            result = parser.parse_file(Path("instance.xml"))
            if result.well_formed:
                process_xml(result.root)
            else:
                log_errors(result.errors)
        """
        # Reset error tracking
        self.errors = []
        self.warnings = []
        
        # Verify file exists
        if not file_path.exists():
            error = ParsingError(
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.FILE_NOT_FOUND,
                message=f"File not found: {file_path}",
                source_file=file_path
            )
            self.errors.append(error)
            
            return XMLParseResult(
                tree=None,
                root=None,
                errors=self.errors,
                warnings=self.warnings,
                encoding="unknown",
                well_formed=False,
                valid=False,
                source_file=file_path,
                recovery_applied=False
            )
        
        # Create parser with error recovery and security settings
        parser = self._create_parser()
        
        try:
            # Parse with encoding detection and fallback
            tree, encoding_used = self._parse_with_encoding_fallback(file_path, parser)
            
            root = tree.getroot() if tree is not None else None
            
            # Collect errors from lxml parser error log
            self._collect_parser_errors(parser, file_path)
            
            # Check well-formedness
            well_formed = not any(
                e.category == ErrorCategory.XML_MALFORMED 
                for e in self.errors
            )
            
            # Determine if recovery was applied
            recovery_applied = len(self.errors) > 0 or len(self.warnings) > 0
            
            return XMLParseResult(
                tree=tree,
                root=root,
                errors=self.errors,
                warnings=self.warnings,
                encoding=encoding_used,
                well_formed=well_formed,
                valid=False,  # Validation done separately
                source_file=file_path,
                recovery_applied=recovery_applied
            )
            
        except etree.XMLSyntaxError as e:
            # Fatal XML error - cannot recover
            error = ParsingError(
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.XML_MALFORMED,
                message=f"Fatal XML syntax error: {str(e)}",
                details=f"Exception: {str(e)}, Type: XMLSyntaxError",
                source_file=file_path,
                line_number=e.lineno if hasattr(e, 'lineno') else None
            )
            self.errors.append(error)
            
            return XMLParseResult(
                tree=None,
                root=None,
                errors=self.errors,
                warnings=self.warnings,
                encoding="unknown",
                well_formed=False,
                valid=False,
                source_file=file_path,
                recovery_applied=True
            )
        
        except Exception as e:
            # Unexpected error
            error = ParsingError(
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.UNKNOWN,
                message=f"Unexpected parsing error: {str(e)}",
                details=f"Exception: {str(e)}, Type: {type(e).__name__}",
                source_file=file_path
            )
            self.errors.append(error)
            
            return XMLParseResult(
                tree=None,
                root=None,
                errors=self.errors,
                warnings=self.warnings,
                encoding="unknown",
                well_formed=False,
                valid=False,
                source_file=file_path,
                recovery_applied=True
            )
    
    def parse_string(self, xml_string: str, encoding: str = None) -> XMLParseResult:
        """
        Parse XML from string.
        
        Args:
            xml_string: XML content as string
            encoding: Optional encoding (defaults to config default)
            
        Returns:
            XMLParseResult with parsed tree and error information
        """
        # Reset error tracking
        self.errors = []
        self.warnings = []
        
        encoding_used = encoding if encoding else self.default_encoding
        
        # Create parser
        parser = self._create_parser()
        
        try:
            # Parse string
            if isinstance(xml_string, str):
                xml_bytes = xml_string.encode(encoding_used)
            else:
                xml_bytes = xml_string
            
            tree = etree.fromstring(xml_bytes, parser)
            
            # Collect errors
            self._collect_parser_errors(parser, Path("<string>"))
            
            # Check well-formedness
            well_formed = not any(
                e.category == ErrorCategory.XML_MALFORMED 
                for e in self.errors
            )
            
            return XMLParseResult(
                tree=tree.getroottree() if hasattr(tree, 'getroottree') else None,
                root=tree,
                errors=self.errors,
                warnings=self.warnings,
                encoding=encoding_used,
                well_formed=well_formed,
                valid=False,
                source_file=None,
                recovery_applied=len(self.errors) > 0
            )
            
        except etree.XMLSyntaxError as e:
            error = ParsingError(
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.XML_MALFORMED,
                message=f"Fatal XML syntax error in string: {str(e)}",
                details=f"Exception: {str(e)}",
                line_number=e.lineno if hasattr(e, 'lineno') else None
            )
            self.errors.append(error)
            
            return XMLParseResult(
                tree=None,
                root=None,
                errors=self.errors,
                warnings=self.warnings,
                encoding=encoding_used,
                well_formed=False,
                valid=False,
                source_file=None,
                recovery_applied=True
            )
    
    def validate_against_schema(
        self,
        result: XMLParseResult,
        schema_path: Path
    ) -> list[ParsingError]:
        """
        Validate XML tree against XSD schema.
        
        Note: Returns validation errors but does not modify result.valid.
        Caller should update result based on validation errors.
        
        Args:
            result: XMLParseResult to validate
            schema_path: Path to XSD schema file
            
        Returns:
            list of validation errors
        """
        validation_errors: list[ParsingError] = []
        
        if result.tree is None:
            validation_errors.append(ParsingError(
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.XBRL_INVALID,
                message="Cannot validate - no tree available",
                source_file=result.source_file
            ))
            return validation_errors
        
        try:
            # Load schema
            schema_doc = etree.parse(str(schema_path))
            schema = etree.XMLSchema(schema_doc)
            
            # Validate
            if not schema.validate(result.tree):
                # Collect validation errors
                for error in schema.error_log:
                    validation_errors.append(ParsingError(
                        severity=ErrorSeverity.ERROR,
                        category=ErrorCategory.XBRL_SCHEMA_VIOLATION,
                        message=f"Schema validation error: {error.message}",
                        details=f"Type: {error.type_name}, Domain: {error.domain_name}",
                        source_file=result.source_file,
                        line_number=error.line,
                        column_number=error.column
                    ))
        
        except Exception as e:
            validation_errors.append(ParsingError(
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.XBRL_INVALID,
                message=f"Schema validation failed: {str(e)}",
                details=f"Exception: {str(e)}",
                source_file=result.source_file
            ))
        
        return validation_errors
    
    def get_element_location(self, element: etree._Element) -> tuple[Optional[str], Optional[int]]:
        """
        Get source location for an element.
        
        Args:
            element: XML element
            
        Returns:
            tuple of (file_path, line_number)
        """
        doc = element.getroottree()
        file_path = doc.docinfo.URL if doc and doc.docinfo else None
        line_number = element.sourceline if hasattr(element, 'sourceline') else None
        
        return (file_path, line_number)
    
    def _create_parser(self) -> etree.XMLParser:
        """
        Create lxml parser with security and recovery settings.
        
        Returns:
            Configured XMLParser instance
        """
        return etree.XMLParser(
            recover=True,  # Enable error recovery mode
            remove_blank_text=False,  # Preserve whitespace
            resolve_entities=False if self.disable_external_entities else True,  # XXE protection
            no_network=True if self.disable_external_entities else False,  # No network access
            collect_ids=True,  # Collect ID attributes
            huge_tree=False,  # Prevent billion laughs attack
            remove_comments=False,  # Preserve comments
            remove_pis=False,  # Preserve processing instructions
            strip_cdata=False,  # Preserve CDATA
            encoding=self.default_encoding
        )
    
    def _parse_with_encoding_fallback(
        self,
        file_path: Path,
        parser: etree.XMLParser
    ) -> tuple[etree._ElementTree, str]:
        """
        Parse XML with multiple encoding attempts.
        
        Strategy:
        1. Try declared encoding (from XML declaration)
        2. Try configured fallback encodings
        3. Final fallback: UTF-8 with replacement characters
        
        Args:
            file_path: Path to XML file
            parser: Configured parser
            
        Returns:
            tuple of (parsed tree, encoding used)
        """
        # Try auto-detect encoding if enabled
        if self.auto_detect_encoding:
            detected_encoding = self._detect_encoding(file_path)
            if detected_encoding != self.default_encoding:
                try:
                    with open(file_path, 'r', encoding=detected_encoding) as f:
                        tree = etree.parse(f, parser)
                        return tree, detected_encoding
                except (UnicodeDecodeError, LookupError) as e:
                    self.warnings.append(ParsingError(
                        severity=ErrorSeverity.WARNING,
                        category=ErrorCategory.XML_ENCODING,
                        message=f"Declared encoding '{detected_encoding}' failed, trying fallback",
                        details=f"Exception: {str(e)}",
                        source_file=file_path
                    ))
        
        # Try each fallback encoding
        for encoding in self.encoding_fallbacks:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    tree = etree.parse(f, parser)
                    
                    # Log if not using default
                    if encoding != self.default_encoding:
                        self.warnings.append(ParsingError(
                            severity=ErrorSeverity.WARNING,
                            category=ErrorCategory.XML_ENCODING,
                            message=f"Using fallback encoding: {encoding}",
                            details=f"Encoding: {encoding}",
                            source_file=file_path
                        ))
                    
                    return tree, encoding
                    
            except UnicodeDecodeError:
                continue
            except LookupError:
                # Invalid encoding name
                continue
        
        # Final fallback: UTF-8 with replacement characters
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                tree = etree.parse(f, parser)
                
                self.errors.append(ParsingError(
                    severity=ErrorSeverity.ERROR,
                    category=ErrorCategory.XML_ENCODING,
                    message="Encoding errors - using replacement characters",
                    details="Encoding: utf-8, Errors: replace",
                    source_file=file_path
                ))
                
                return tree, 'utf-8'
        
        except Exception as e:
            # This should rarely happen - UTF-8 with replace should handle anything
            self.errors.append(ParsingError(
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.XML_ENCODING,
                message=f"All encoding attempts failed: {str(e)}",
                details=f"Exception: {str(e)}",
                source_file=file_path
            ))
            raise
    
    def _collect_parser_errors(self, parser: etree.XMLParser, file_path: Path):
        """
        Collect errors from lxml parser error log.
        
        Maps lxml errors to our Error model for consistent reporting.
        
        Args:
            parser: Parser with error log
            file_path: Source file path
        """
        for error in parser.error_log:
            severity = self._map_lxml_level(error.level)
            category = self._categorize_lxml_error(error.type)
            
            error_obj = ParsingError(
                severity=severity,
                category=category,
                message=error.message,
                details=f"Type: {error.type_name}, Domain: {error.domain_name}, Level: {error.level_name}, lxml_type: {error.type}",
                source_file=file_path,
                line_number=error.line,
                column_number=error.column
            )
            
            if severity in (ErrorSeverity.CRITICAL, ErrorSeverity.ERROR):
                self.errors.append(error_obj)
            else:
                self.warnings.append(error_obj)
    
    def _map_lxml_level(self, level: int) -> ErrorSeverity:
        """
        Map lxml error level to our ErrorSeverity.
        
        Args:
            level: lxml error level
            
        Returns:
            Corresponding ErrorSeverity
        """
        if level == etree.ErrorLevels.FATAL:
            return ErrorSeverity.CRITICAL
        elif level == etree.ErrorLevels.ERROR:
            return ErrorSeverity.ERROR
        elif level == etree.ErrorLevels.WARNING:
            return ErrorSeverity.WARNING
        else:
            return ErrorSeverity.INFO
    
    def _categorize_lxml_error(self, error_type: int) -> ErrorCategory:
        """
        Categorize lxml error type to our ErrorCategory.
        
        Args:
            error_type: lxml error type code
            
        Returns:
            Corresponding ErrorCategory
        """
        # Map common lxml error types
        malformed_errors = [
            etree.ErrorTypes.ERR_TAG_NOT_FINISHED,
            etree.ErrorTypes.ERR_TAG_NAME_MISMATCH,
            etree.ErrorTypes.ERR_DOCUMENT_EMPTY,
            etree.ErrorTypes.ERR_DOCUMENT_END,
            etree.ErrorTypes.ERR_EXTRA_CONTENT
        ]
        
        encoding_errors = [
            etree.ErrorTypes.ERR_INVALID_ENCODING
        ]
        
        if error_type in malformed_errors:
            return ErrorCategory.XML_MALFORMED
        elif error_type in encoding_errors:
            return ErrorCategory.XML_INVALID
        else:
            return ErrorCategory.XML_INVALID
    
    def _detect_encoding(self, file_path: Path) -> str:
        """
        Detect XML encoding from declaration.
        
        Reads first line to find <?xml ... encoding="..."?> declaration.
        
        Args:
            file_path: Path to XML file
            
        Returns:
            Detected encoding or default encoding
        """
        try:
            with open(file_path, 'rb') as f:
                # Read first 1024 bytes (should contain XML declaration)
                first_bytes = f.read(1024)
                
                # Look for encoding declaration
                if b'encoding=' in first_bytes:
                    # Find encoding value
                    start = first_bytes.find(b'encoding=')
                    if start == -1:
                        return self.default_encoding
                    
                    # Skip 'encoding=' and quote
                    start += 9
                    quote_char = first_bytes[start:start+1]
                    if quote_char not in (b'"', b"'"):
                        return self.default_encoding
                    
                    start += 1
                    end = first_bytes.find(quote_char, start)
                    
                    if end == -1:
                        return self.default_encoding
                    
                    encoding = first_bytes[start:end].decode('ascii').strip()
                    return encoding if encoding else self.default_encoding
        
        except Exception:
            # If anything goes wrong, use default
            pass
        
        return self.default_encoding


__all__ = ['XMLParser', 'XMLParseResult']
