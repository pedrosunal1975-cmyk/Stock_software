"""
XML Document Validator - Standalone Tool
=========================================

A robust, layered XML validation tool designed for pre-XBRL validation.
Validates XML documents through multiple stages before XBRL processing.

Author: XML Validation Tool
Version: 1.0.0
Python: 3.12+
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Union
from datetime import datetime

from lxml import etree
from lxml.etree import XMLSyntaxError, DocumentInvalid


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================


class ValidationLevel(str, Enum):
    """Validation severity levels."""
    
    WELLFORMEDNESS = "wellformedness"
    SCHEMA = "schema"
    CUSTOM = "custom"


class ValidationStatus(str, Enum):
    """Validation result status."""
    
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass
class ValidationError:
    """Represents a single validation error."""
    
    level: ValidationLevel
    line: Optional[int]
    column: Optional[int]
    message: str
    error_type: str
    severity: ValidationStatus = ValidationStatus.FAILED
    
    def __str__(self) -> str:
        """Human-readable error representation."""
        location = f"Line {self.line}, Column {self.column}" if self.line else "Unknown location"
        return f"[{self.level.value.upper()}] {location}: {self.message}"


@dataclass
class ValidationResult:
    """Complete validation result for a document."""
    
    file_path: Path
    is_valid: bool
    status: ValidationStatus
    validation_time: datetime = field(default_factory=datetime.now)
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    levels_completed: list[ValidationLevel] = field(default_factory=list)
    
    def add_error(self, error: ValidationError) -> None:
        """Add an error to the result."""
        if error.severity == ValidationStatus.WARNING:
            self.warnings.append(error)
        else:
            self.errors.append(error)
            self.is_valid = False
            self.status = ValidationStatus.FAILED
    
    def summary(self) -> str:
        """Generate a human-readable summary."""
        status_symbol = "✓" if self.is_valid else "✗"
        lines = [
            f"\n{'='*70}",
            f"XML Validation Report: {self.file_path.name}",
            f"{'='*70}",
            f"Status: {status_symbol} {self.status.value.upper()}",
            f"Timestamp: {self.validation_time.isoformat()}",
            f"Levels Completed: {', '.join(l.value for l in self.levels_completed)}",
            f"\nErrors: {len(self.errors)}",
            f"Warnings: {len(self.warnings)}",
        ]
        
        if self.errors:
            lines.append(f"\n{'─'*70}")
            lines.append("ERRORS:")
            for i, error in enumerate(self.errors, 1):
                lines.append(f"{i}. {error}")
        
        if self.warnings:
            lines.append(f"\n{'─'*70}")
            lines.append("WARNINGS:")
            for i, warning in enumerate(self.warnings, 1):
                lines.append(f"{i}. {warning}")
        
        lines.append(f"{'='*70}\n")
        return "\n".join(lines)


# ============================================================================
# VALIDATORS
# ============================================================================


class WellFormednessValidator:
    """Validates XML well-formedness (Stage 1)."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def validate(self, xml_content: Union[str, bytes, Path]) -> list[ValidationError]:
        """
        Validate XML well-formedness.
        
        Args:
            xml_content: XML content as string, bytes, or file path
            
        Returns:
            List of validation errors (empty if well-formed)
        """
        errors = []
        
        try:
            if isinstance(xml_content, Path):
                self.logger.debug(f"Parsing XML file: {xml_content}")
                parser = etree.XMLParser(recover=False)
                etree.parse(str(xml_content), parser)
            else:
                self.logger.debug("Parsing XML content from string/bytes")
                parser = etree.XMLParser(recover=False)
                if isinstance(xml_content, str):
                    xml_content = xml_content.encode('utf-8')
                etree.fromstring(xml_content, parser)
            
            self.logger.info("✓ XML is well-formed")
            
        except XMLSyntaxError as e:
            self.logger.error(f"✗ XML syntax error: {e}")
            errors.append(ValidationError(
                level=ValidationLevel.WELLFORMEDNESS,
                line=e.lineno,
                column=e.position[0] if e.position else None,
                message=str(e),
                error_type="XMLSyntaxError"
            ))
        except Exception as e:
            self.logger.error(f"✗ Unexpected error during well-formedness check: {e}")
            errors.append(ValidationError(
                level=ValidationLevel.WELLFORMEDNESS,
                line=None,
                column=None,
                message=f"Unexpected error: {str(e)}",
                error_type=type(e).__name__
            ))
        
        return errors


class SchemaValidator:
    """Validates XML against XSD schema (Stage 2)."""
    
    def __init__(self, schema_path: Optional[Path] = None, logger: Optional[logging.Logger] = None):
        self.schema_path = schema_path
        self.logger = logger or logging.getLogger(__name__)
        self._schema: Optional[etree.XMLSchema] = None
    
    def load_schema(self, schema_path: Path) -> None:
        """Load and compile XSD schema."""
        self.schema_path = schema_path
        try:
            self.logger.debug(f"Loading schema: {schema_path}")
            schema_doc = etree.parse(str(schema_path))
            self._schema = etree.XMLSchema(schema_doc)
            self.logger.info(f"✓ Schema loaded: {schema_path.name}")
        except Exception as e:
            self.logger.error(f"✗ Failed to load schema: {e}")
            raise ValueError(f"Invalid schema file: {e}") from e
    
    def validate(self, xml_content: Union[str, bytes, Path]) -> list[ValidationError]:
        """
        Validate XML against loaded schema.
        
        Args:
            xml_content: XML content as string, bytes, or file path
            
        Returns:
            List of validation errors (empty if valid)
        """
        if not self._schema:
            if not self.schema_path:
                return [ValidationError(
                    level=ValidationLevel.SCHEMA,
                    line=None,
                    column=None,
                    message="No schema loaded for validation",
                    error_type="ConfigurationError",
                    severity=ValidationStatus.SKIPPED
                )]
            self.load_schema(self.schema_path)
        
        errors = []
        
        try:
            if isinstance(xml_content, Path):
                doc = etree.parse(str(xml_content))
            else:
                if isinstance(xml_content, str):
                    xml_content = xml_content.encode('utf-8')
                doc = etree.fromstring(xml_content)
            
            is_valid = self._schema.validate(doc)
            
            if is_valid:
                self.logger.info("✓ XML is schema-valid")
            else:
                self.logger.error("✗ XML schema validation failed")
                for error in self._schema.error_log:
                    errors.append(ValidationError(
                        level=ValidationLevel.SCHEMA,
                        line=error.line,
                        column=error.column,
                        message=error.message,
                        error_type=error.type_name
                    ))
        
        except DocumentInvalid as e:
            self.logger.error(f"✗ Document invalid: {e}")
            errors.append(ValidationError(
                level=ValidationLevel.SCHEMA,
                line=None,
                column=None,
                message=str(e),
                error_type="DocumentInvalid"
            ))
        except Exception as e:
            self.logger.error(f"✗ Unexpected error during schema validation: {e}")
            errors.append(ValidationError(
                level=ValidationLevel.SCHEMA,
                line=None,
                column=None,
                message=f"Unexpected error: {str(e)}",
                error_type=type(e).__name__
            ))
        
        return errors


class CustomRulesValidator:
    """Validates custom business rules (Stage 3 - Optional)."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.rules: list = []
    
    def add_rule(self, rule_function, rule_name: str) -> None:
        """Add a custom validation rule."""
        self.rules.append((rule_name, rule_function))
    
    def validate(self, xml_tree: etree._Element) -> list[ValidationError]:
        """
        Apply custom validation rules.
        
        Args:
            xml_tree: Parsed XML tree
            
        Returns:
            List of validation errors
        """
        errors = []
        
        for rule_name, rule_func in self.rules:
            try:
                self.logger.debug(f"Applying rule: {rule_name}")
                rule_errors = rule_func(xml_tree)
                if rule_errors:
                    errors.extend(rule_errors)
                    self.logger.warning(f"Rule '{rule_name}' found {len(rule_errors)} issue(s)")
                else:
                    self.logger.debug(f"✓ Rule '{rule_name}' passed")
            except Exception as e:
                self.logger.error(f"✗ Error applying rule '{rule_name}': {e}")
                errors.append(ValidationError(
                    level=ValidationLevel.CUSTOM,
                    line=None,
                    column=None,
                    message=f"Rule '{rule_name}' failed: {str(e)}",
                    error_type="CustomRuleError"
                ))
        
        return errors


# ============================================================================
# MAIN VALIDATOR ORCHESTRATOR
# ============================================================================


class XMLValidator:
    """
    Main XML validation orchestrator.
    
    Coordinates multi-stage validation pipeline:
    1. Well-formedness check
    2. Schema validation (if schema provided)
    3. Custom rules (if rules added)
    """
    
    def __init__(
        self,
        schema_path: Optional[Path] = None,
        fail_fast: bool = True,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize validator.
        
        Args:
            schema_path: Optional XSD schema file path
            fail_fast: Stop validation on first error
            logger: Optional logger instance
        """
        self.fail_fast = fail_fast
        self.logger = logger or self._setup_logger()
        
        self.wellformedness_validator = WellFormednessValidator(self.logger)
        self.schema_validator = SchemaValidator(schema_path, self.logger) if schema_path else None
        self.custom_validator = CustomRulesValidator(self.logger)
    
    @staticmethod
    def _setup_logger() -> logging.Logger:
        """Setup default logger."""
        logger = logging.getLogger("XMLValidator")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def add_custom_rule(self, rule_function, rule_name: str) -> None:
        """Add a custom validation rule."""
        self.custom_validator.add_rule(rule_function, rule_name)
    
    def validate_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """
        Validate an XML file through all stages.
        
        Args:
            file_path: Path to XML file
            
        Returns:
            ValidationResult object
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            result = ValidationResult(
                file_path=file_path,
                is_valid=False,
                status=ValidationStatus.FAILED
            )
            result.add_error(ValidationError(
                level=ValidationLevel.WELLFORMEDNESS,
                line=None,
                column=None,
                message=f"File not found: {file_path}",
                error_type="FileNotFoundError"
            ))
            return result
        
        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"Starting validation: {file_path.name}")
        self.logger.info(f"{'='*70}")
        
        result = ValidationResult(
            file_path=file_path,
            is_valid=True,
            status=ValidationStatus.PASSED
        )
        
        # Stage 1: Well-formedness
        self.logger.info("\n[STAGE 1] Checking well-formedness...")
        errors = self.wellformedness_validator.validate(file_path)
        for error in errors:
            result.add_error(error)
        
        if errors:
            result.levels_completed.append(ValidationLevel.WELLFORMEDNESS)
            if self.fail_fast:
                self.logger.warning("Stopping validation (fail-fast enabled)")
                return result
        else:
            result.levels_completed.append(ValidationLevel.WELLFORMEDNESS)
        
        # Stage 2: Schema validation
        if self.schema_validator:
            self.logger.info("\n[STAGE 2] Validating against schema...")
            errors = self.schema_validator.validate(file_path)
            for error in errors:
                result.add_error(error)
            
            if errors:
                result.levels_completed.append(ValidationLevel.SCHEMA)
                if self.fail_fast:
                    self.logger.warning("Stopping validation (fail-fast enabled)")
                    return result
            else:
                result.levels_completed.append(ValidationLevel.SCHEMA)
        
        # Stage 3: Custom rules
        if self.custom_validator.rules:
            self.logger.info("\n[STAGE 3] Applying custom rules...")
            try:
                tree = etree.parse(str(file_path))
                errors = self.custom_validator.validate(tree.getroot())
                for error in errors:
                    result.add_error(error)
                result.levels_completed.append(ValidationLevel.CUSTOM)
            except Exception as e:
                self.logger.error(f"Failed to apply custom rules: {e}")
                result.add_error(ValidationError(
                    level=ValidationLevel.CUSTOM,
                    line=None,
                    column=None,
                    message=f"Failed to parse XML for custom rules: {str(e)}",
                    error_type="CustomRuleSetupError"
                ))
        
        return result
    
    def validate_string(self, xml_string: str) -> ValidationResult:
        """
        Validate XML from string.
        
        Args:
            xml_string: XML content as string
            
        Returns:
            ValidationResult object
        """
        result = ValidationResult(
            file_path=Path("(string input)"),
            is_valid=True,
            status=ValidationStatus.PASSED
        )
        
        # Stage 1: Well-formedness
        self.logger.info("\n[STAGE 1] Checking well-formedness...")
        errors = self.wellformedness_validator.validate(xml_string)
        for error in errors:
            result.add_error(error)
        
        if errors and self.fail_fast:
            return result
        result.levels_completed.append(ValidationLevel.WELLFORMEDNESS)
        
        # Stage 2: Schema validation
        if self.schema_validator:
            self.logger.info("\n[STAGE 2] Validating against schema...")
            errors = self.schema_validator.validate(xml_string)
            for error in errors:
                result.add_error(error)
            
            if errors and self.fail_fast:
                return result
            result.levels_completed.append(ValidationLevel.SCHEMA)
        
        # Stage 3: Custom rules
        if self.custom_validator.rules:
            self.logger.info("\n[STAGE 3] Applying custom rules...")
            try:
                tree = etree.fromstring(xml_string.encode('utf-8'))
                errors = self.custom_validator.validate(tree)
                for error in errors:
                    result.add_error(error)
                result.levels_completed.append(ValidationLevel.CUSTOM)
            except Exception as e:
                result.add_error(ValidationError(
                    level=ValidationLevel.CUSTOM,
                    line=None,
                    column=None,
                    message=f"Failed to parse XML for custom rules: {str(e)}",
                    error_type="CustomRuleSetupError"
                ))
        
        return result


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def validate_batch(
    file_paths: list[Path],
    validator: XMLValidator,
    output_report: Optional[Path] = None
) -> dict[Path, ValidationResult]:
    """
    Validate multiple XML files in batch.
    
    Args:
        file_paths: List of XML file paths
        validator: Configured XMLValidator instance
        output_report: Optional path to save combined report
        
    Returns:
        Dictionary mapping file paths to validation results
    """
    results = {}
    
    for file_path in file_paths:
        result = validator.validate_file(file_path)
        results[file_path] = result
        print(result.summary())
    
    if output_report:
        with open(output_report, 'w', encoding='utf-8') as f:
            f.write(f"Batch Validation Report\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Total Files: {len(file_paths)}\n")
            f.write(f"{'='*70}\n\n")
            
            for file_path, result in results.items():
                f.write(result.summary())
                f.write("\n")
    
    return results


# ============================================================================
# EXAMPLE USAGE
# ============================================================================


if __name__ == "__main__":
    # Example: Basic validation
    validator = XMLValidator()
    result = validator.validate_file("example.xml")
    print(result.summary())
