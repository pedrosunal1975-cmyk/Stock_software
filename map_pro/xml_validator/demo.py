#!/usr/bin/env python3
"""
Quick Demo of XML Validator
============================

Run this script to see the validator in action with sample data.
"""

import tempfile
from pathlib import Path
from xml_validator import XMLValidator, ValidationError, ValidationLevel

def create_sample_files(tmp_dir):
    """Create sample XML files for demonstration."""
    
    # Valid XML
    valid_xml = tmp_dir / "valid.xml"
    valid_xml.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<company>
    <n>Acme Corporation</n>
    <ticker>ACME</ticker>
    <founded>1990</founded>
    <revenue currency="USD">1000000</revenue>
</company>""")
    
    # Invalid XML (syntax error)
    invalid_xml = tmp_dir / "invalid_syntax.xml"
    invalid_xml.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<company>
    <n>Broken Corp</n>
    <ticker>BRKN
    <founded>2000</founded>
</company>""")
    
    # Valid XML for schema test
    for_schema = tmp_dir / "for_schema.xml"
    for_schema.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<company>
    <n>Schema Test Corp</n>
    <ticker>STC</ticker>
</company>""")
    
    # Simple XSD schema
    schema = tmp_dir / "schema.xsd"
    schema.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
    <xs:element name="company">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="name" type="xs:string"/>
                <xs:element name="ticker" type="xs:string"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
</xs:schema>""")
    
    # XBRL-like document
    xbrl_like = tmp_dir / "xbrl_like.xml"
    xbrl_like.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
      xmlns:link="http://www.xbrl.org/2003/linkbase"
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
    
    <us-gaap:Assets contextRef="current_year" unitRef="USD" decimals="-3">5000000</us-gaap:Assets>
    <us-gaap:Liabilities contextRef="current_year" unitRef="USD" decimals="-3">2000000</us-gaap:Liabilities>
    
</xbrl>""")
    
    return {
        'valid': valid_xml,
        'invalid': invalid_xml,
        'for_schema': for_schema,
        'schema': schema,
        'xbrl_like': xbrl_like
    }


def demo_basic_validation(files):
    """Demo 1: Basic well-formedness validation."""
    print("\n" + "="*70)
    print("DEMO 1: Basic Well-formedness Validation")
    print("="*70)
    
    validator = XMLValidator()
    
    print("\n1. Validating VALID XML:")
    result = validator.validate_file(files['valid'])
    print(result.summary())
    
    print("\n2. Validating INVALID XML:")
    result = validator.validate_file(files['invalid'])
    print(result.summary())


def demo_schema_validation(files):
    """Demo 2: Schema validation."""
    print("\n" + "="*70)
    print("DEMO 2: Schema Validation")
    print("="*70)
    
    validator = XMLValidator(schema_path=files['schema'])
    
    print("\nValidating XML against XSD schema:")
    result = validator.validate_file(files['for_schema'])
    print(result.summary())


def demo_custom_rules(files):
    """Demo 3: Custom validation rules."""
    print("\n" + "="*70)
    print("DEMO 3: Custom Validation Rules")
    print("="*70)
    
    validator = XMLValidator()
    
    # Rule 1: Check for required namespaces
    def check_namespaces(xml_tree):
        """Check for XBRL namespaces."""
        errors = []
        nsmap = xml_tree.nsmap
        
        if 'xbrli' not in nsmap:
            errors.append(ValidationError(
                level=ValidationLevel.CUSTOM,
                line=None,
                column=None,
                message="Missing XBRL instance namespace (xbrli)",
                error_type="MissingNamespace"
            ))
        
        return errors
    
    # Rule 2: Check context references
    def check_context_refs(xml_tree):
        """Check that contexts have IDs."""
        errors = []
        
        # Find contexts without IDs
        contexts = xml_tree.xpath('//xbrli:context[not(@id)]', namespaces={
            'xbrli': 'http://www.xbrl.org/2003/instance'
        })
        
        for ctx in contexts:
            errors.append(ValidationError(
                level=ValidationLevel.CUSTOM,
                line=ctx.sourceline,
                column=None,
                message="Context element missing 'id' attribute",
                error_type="MissingContextId"
            ))
        
        return errors
    
    # Rule 3: Business rule - check for minimum data
    def check_minimum_facts(xml_tree):
        """Ensure minimum number of facts."""
        errors = []
        
        # Count fact elements (elements with contextRef)
        facts = xml_tree.xpath('//*[@contextRef]')
        
        if len(facts) < 2:
            errors.append(ValidationError(
                level=ValidationLevel.CUSTOM,
                line=None,
                column=None,
                message=f"Document contains only {len(facts)} fact(s), minimum 2 required",
                error_type="InsufficientFacts"
            ))
        
        return errors
    
    # Add rules
    validator.add_custom_rule(check_namespaces, "Namespace Check")
    validator.add_custom_rule(check_context_refs, "Context ID Check")
    validator.add_custom_rule(check_minimum_facts, "Minimum Facts Check")
    
    print("\nValidating XBRL-like document with custom rules:")
    result = validator.validate_file(files['xbrl_like'])
    print(result.summary())


def demo_fail_fast_comparison(files):
    """Demo 4: Fail-fast vs continue-on-error."""
    print("\n" + "="*70)
    print("DEMO 4: Fail-Fast vs Continue-On-Error")
    print("="*70)
    
    print("\n1. With fail_fast=True (stops at first error):")
    validator1 = XMLValidator(fail_fast=True)
    result1 = validator1.validate_file(files['invalid'])
    print(f"   Levels completed: {[l.value for l in result1.levels_completed]}")
    
    print("\n2. With fail_fast=False (continues through all stages):")
    validator2 = XMLValidator(fail_fast=False)
    result2 = validator2.validate_file(files['invalid'])
    print(f"   Levels completed: {[l.value for l in result2.levels_completed]}")


def demo_string_validation():
    """Demo 5: Validate from string."""
    print("\n" + "="*70)
    print("DEMO 5: String Validation")
    print("="*70)
    
    validator = XMLValidator()
    
    xml_string = """<?xml version="1.0" encoding="UTF-8"?>
<message>
    <from>Alice</from>
    <to>Bob</to>
    <content>Hello, World!</content>
</message>"""
    
    print("\nValidating XML from string:")
    result = validator.validate_string(xml_string)
    print(result.summary())


def main():
    """Run all demos."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║                   XML VALIDATOR - INTERACTIVE DEMO                   ║
║                                                                      ║
║  This demo shows the validator in action with sample XML documents  ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    # Create temporary directory with sample files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        files = create_sample_files(tmp_path)
        
        print(f"\nCreated sample files in: {tmp_path}")
        print("Files created:")
        for name, path in files.items():
            print(f"  - {name}: {path.name}")
        
        # Run demos
        demo_basic_validation(files)
        demo_schema_validation(files)
        demo_custom_rules(files)
        demo_fail_fast_comparison(files)
        demo_string_validation()
    
    print("\n" + "="*70)
    print("DEMO COMPLETE!")
    print("="*70)
    print("\nNext steps:")
    print("1. Check out examples.py for more detailed examples")
    print("2. Read README.md for complete documentation")
    print("3. Try: python xml_validator_cli.py validate your_file.xml")
    print("4. Run tests: pytest test_xml_validator.py -v")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted. Goodbye!")
    except Exception as e:
        print(f"\n\nError running demo: {e}")
        print("Make sure lxml is installed: pip install lxml")
