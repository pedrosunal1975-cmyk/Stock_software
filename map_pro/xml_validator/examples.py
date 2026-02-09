"""
Example Usage of XML Validator
===============================

Examples showing how to integrate the XML validator with XBRL processing.
"""

from pathlib import Path
from xml_validator import (
    XMLValidator,
    ValidationError,
    ValidationLevel,
    validate_batch
)


# ============================================================================
# EXAMPLE 1: Basic Validation
# ============================================================================


def example_basic_validation():
    """Simple validation without schema."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Well-Formedness Validation")
    print("="*70)
    
    validator = XMLValidator()
    
    # Test with a sample XML string
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<company>
    <name>Example Corp</name>
    <ticker>EXPL</ticker>
    <founded>2020</founded>
</company>"""
    
    result = validator.validate_string(xml_content)
    print(result.summary())


# ============================================================================
# EXAMPLE 2: Schema Validation
# ============================================================================


def example_schema_validation():
    """Validation with XSD schema."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Schema Validation")
    print("="*70)
    
    # Assuming you have a schema file
    schema_path = Path("schemas/xbrl-instance-2003.xsd")
    
    if schema_path.exists():
        validator = XMLValidator(schema_path=schema_path)
        result = validator.validate_file("sample_xbrl.xml")
        print(result.summary())
    else:
        print(f"Schema not found: {schema_path}")
        print("Skipping this example.")


# ============================================================================
# EXAMPLE 3: Custom Rules for XBRL Preprocessing
# ============================================================================


def example_custom_xbrl_rules():
    """Validation with custom XBRL-specific rules."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Custom XBRL Rules")
    print("="*70)
    
    validator = XMLValidator()
    
    # Define custom rules for XBRL preprocessing
    
    def check_required_namespaces(xml_tree):
        """Ensure XBRL namespaces are declared."""
        errors = []
        
        required_namespaces = {
            'xbrli': 'http://www.xbrl.org/2003/instance',
            'link': 'http://www.xbrl.org/2003/linkbase',
        }
        
        nsmap = xml_tree.nsmap
        
        for prefix, uri in required_namespaces.items():
            if prefix not in nsmap or nsmap[prefix] != uri:
                errors.append(ValidationError(
                    level=ValidationLevel.CUSTOM,
                    line=None,
                    column=None,
                    message=f"Missing or incorrect namespace: {prefix} = {uri}",
                    error_type="MissingNamespace"
                ))
        
        return errors
    
    def check_context_elements(xml_tree):
        """Ensure context elements have required attributes."""
        errors = []
        
        # Find all context elements
        contexts = xml_tree.xpath('//xbrli:context', namespaces={
            'xbrli': 'http://www.xbrl.org/2003/instance'
        })
        
        for ctx in contexts:
            if 'id' not in ctx.attrib:
                errors.append(ValidationError(
                    level=ValidationLevel.CUSTOM,
                    line=ctx.sourceline,
                    column=None,
                    message="Context element missing 'id' attribute",
                    error_type="MissingContextId"
                ))
        
        return errors
    
    def check_unit_elements(xml_tree):
        """Ensure unit elements are properly defined."""
        errors = []
        
        units = xml_tree.xpath('//xbrli:unit', namespaces={
            'xbrli': 'http://www.xbrl.org/2003/instance'
        })
        
        for unit in units:
            if 'id' not in unit.attrib:
                errors.append(ValidationError(
                    level=ValidationLevel.CUSTOM,
                    line=unit.sourceline,
                    column=None,
                    message="Unit element missing 'id' attribute",
                    error_type="MissingUnitId"
                ))
            
            # Check if unit has measure
            measures = unit.xpath('.//xbrli:measure', namespaces={
                'xbrli': 'http://www.xbrl.org/2003/instance'
            })
            
            if not measures:
                errors.append(ValidationError(
                    level=ValidationLevel.CUSTOM,
                    line=unit.sourceline,
                    column=None,
                    message="Unit element missing measure definition",
                    error_type="MissingUnitMeasure"
                ))
        
        return errors
    
    def check_fact_references(xml_tree):
        """Ensure facts reference valid contexts and units."""
        errors = []
        
        # Collect all context IDs
        contexts = xml_tree.xpath('//xbrli:context/@id', namespaces={
            'xbrli': 'http://www.xbrl.org/2003/instance'
        })
        context_ids = set(contexts)
        
        # Collect all unit IDs
        units = xml_tree.xpath('//xbrli:unit/@id', namespaces={
            'xbrli': 'http://www.xbrl.org/2003/instance'
        })
        unit_ids = set(units)
        
        # Check facts for valid references
        # This is a simplified check - you'd want to exclude certain elements
        for element in xml_tree.iter():
            if 'contextRef' in element.attrib:
                ctx_ref = element.attrib['contextRef']
                if ctx_ref not in context_ids:
                    errors.append(ValidationError(
                        level=ValidationLevel.CUSTOM,
                        line=element.sourceline,
                        column=None,
                        message=f"Fact references non-existent context: {ctx_ref}",
                        error_type="InvalidContextReference"
                    ))
            
            if 'unitRef' in element.attrib:
                unit_ref = element.attrib['unitRef']
                if unit_ref not in unit_ids:
                    errors.append(ValidationError(
                        level=ValidationLevel.CUSTOM,
                        line=element.sourceline,
                        column=None,
                        message=f"Fact references non-existent unit: {unit_ref}",
                        error_type="InvalidUnitReference"
                    ))
        
        return errors
    
    # Add custom rules to validator
    validator.add_custom_rule(check_required_namespaces, "XBRL Namespace Check")
    validator.add_custom_rule(check_context_elements, "Context Element Check")
    validator.add_custom_rule(check_unit_elements, "Unit Element Check")
    validator.add_custom_rule(check_fact_references, "Fact Reference Check")
    
    # Sample XBRL-like content
    xbrl_content = """<?xml version="1.0" encoding="UTF-8"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
            xmlns:link="http://www.xbrl.org/2003/linkbase"
            xmlns:xlink="http://www.w3.org/1999/xlink"
            xmlns:iso4217="http://www.xbrl.org/2003/iso4217">
    
    <xbrli:context id="current_year">
        <xbrli:entity>
            <xbrli:identifier scheme="http://www.sec.gov/CIK">0001234567</xbrli:identifier>
        </xbrli:entity>
        <xbrli:period>
            <xbrli:instant>2023-12-31</xbrli:instant>
        </xbrli:period>
    </xbrli:context>
    
    <xbrli:unit id="USD">
        <xbrli:measure>iso4217:USD</xbrli:measure>
    </xbrli:unit>
    
    <!-- This will pass validation -->
    <us-gaap:Assets contextRef="current_year" unitRef="USD" decimals="-3">1000000</us-gaap:Assets>
    
</xbrli:xbrl>"""
    
    result = validator.validate_string(xbrl_content)
    print(result.summary())


# ============================================================================
# EXAMPLE 4: Batch Validation for XBRL Pipeline
# ============================================================================


def example_batch_validation():
    """Batch validation as part of XBRL pipeline."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Batch Validation Pipeline")
    print("="*70)
    
    # In a real scenario, you'd have multiple XBRL instance documents
    xml_files = [
        Path("filings/company_a_2023.xml"),
        Path("filings/company_b_2023.xml"),
        Path("filings/company_c_2023.xml"),
    ]
    
    # Filter to only existing files for this example
    xml_files = [f for f in xml_files if f.exists()]
    
    if not xml_files:
        print("No sample files found. Create some XBRL files to test.")
        return
    
    schema_path = Path("schemas/xbrl-instance-2003.xsd")
    validator = XMLValidator(
        schema_path=schema_path if schema_path.exists() else None,
        fail_fast=False  # Don't stop on first error in batch mode
    )
    
    results = validate_batch(
        xml_files,
        validator,
        output_report=Path("validation_report.txt")
    )
    
    # Separate valid and invalid files
    valid_files = [f for f, r in results.items() if r.is_valid]
    invalid_files = [f for f, r in results.items() if not r.is_valid]
    
    print(f"\nPipeline Results:")
    print(f"Valid files ready for XBRL processing: {len(valid_files)}")
    print(f"Invalid files rejected: {len(invalid_files)}")
    
    if valid_files:
        print("\nProceed to XBRL parsing with these files:")
        for f in valid_files:
            print(f"  ✓ {f.name}")
    
    if invalid_files:
        print("\nReject these files (fix XML first):")
        for f in invalid_files:
            print(f"  ✗ {f.name}")


# ============================================================================
# EXAMPLE 5: Integration with Your XBRL Parser
# ============================================================================


def example_integration_pattern():
    """Show how to integrate with existing XBRL parser."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Integration Pattern")
    print("="*70)
    
    print("""
Integration Pattern for Your XBRL Parser:
-----------------------------------------

def process_xbrl_filing(filing_path: Path) -> XBRLDocument:
    '''Process XBRL filing with pre-validation.'''
    
    # STEP 1: Pre-validate XML structure
    validator = XMLValidator(
        schema_path=XBRL_SCHEMA_PATH,
        fail_fast=True
    )
    
    validation_result = validator.validate_file(filing_path)
    
    if not validation_result.is_valid:
        # Log errors and reject file
        logger.error(f"XML validation failed: {filing_path}")
        for error in validation_result.errors:
            logger.error(f"  {error}")
        raise InvalidXMLError(f"File failed XML validation: {filing_path}")
    
    # STEP 2: Only if XML is valid, proceed to XBRL parsing
    logger.info(f"✓ XML validation passed: {filing_path}")
    
    # Your existing XBRL parser code here
    xbrl_doc = YourXBRLParser.parse(filing_path)
    
    # STEP 3: XBRL-specific validation
    xbrl_validation = validate_xbrl_semantics(xbrl_doc)
    
    return xbrl_doc


def batch_process_filings(filing_paths: List[Path]):
    '''Process multiple filings with validation.'''
    
    # Pre-filter with XML validation
    validator = XMLValidator(schema_path=XBRL_SCHEMA_PATH)
    
    valid_files = []
    invalid_files = []
    
    for filing_path in filing_paths:
        result = validator.validate_file(filing_path)
        if result.is_valid:
            valid_files.append(filing_path)
        else:
            invalid_files.append((filing_path, result))
    
    # Log invalid files
    if invalid_files:
        logger.warning(f"Rejected {len(invalid_files)} files due to XML errors")
        for path, result in invalid_files:
            logger.warning(f"  {path.name}: {len(result.errors)} errors")
    
    # Process only valid files
    logger.info(f"Processing {len(valid_files)} valid files")
    for filing_path in valid_files:
        try:
            xbrl_doc = process_xbrl_filing(filing_path)
            # Continue with mapping, analysis, etc.
        except Exception as e:
            logger.error(f"XBRL processing failed: {filing_path}: {e}")
    """)


# ============================================================================
# RUN ALL EXAMPLES
# ============================================================================


def run_all_examples():
    """Run all examples."""
    print("\n" + "="*70)
    print("XML VALIDATOR - EXAMPLE USAGE")
    print("="*70)
    
    example_basic_validation()
    # example_schema_validation()  # Uncomment when you have schema files
    example_custom_xbrl_rules()
    # example_batch_validation()  # Uncomment when you have sample files
    example_integration_pattern()
    
    print("\n" + "="*70)
    print("Examples completed!")
    print("="*70)


if __name__ == "__main__":
    run_all_examples()
