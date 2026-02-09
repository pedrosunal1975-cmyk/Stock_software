# Integration Guide: XML Validator with XBRL Parser

This guide shows you exactly how to integrate the XML validator into your existing XBRL parser project.

## 📁 Project Structure

### Current Structure (Assumed)
```
your_xbrl_project/
├── requirements.txt
├── xbrl_parser/
│   ├── __init__.py
│   ├── parser.py
│   ├── mapper.py
│   └── ...
├── tests/
│   └── test_parser.py
└── ...
```

### Recommended Structure After Integration
```
your_xbrl_project/
├── requirements.txt          # Already has lxml, rich
├── xbrl_parser/
│   ├── __init__.py
│   ├── parser.py
│   ├── mapper.py
│   └── ...
├── validation/               # NEW MODULE
│   ├── __init__.py          # Export main classes
│   ├── xml_validator.py     # Core validator
│   ├── cli.py               # CLI interface
│   └── xbrl_rules.py        # XBRL-specific rules
├── tests/
│   ├── test_parser.py
│   └── test_validation.py   # NEW
├── scripts/
│   └── validate_batch.py    # NEW - Utility scripts
└── examples/
    └── validation_examples.py
```

## 🔧 Installation Steps

### Step 1: Copy Files

```bash
# Create validation module
mkdir -p validation

# Copy core files
cp xml_validator.py validation/
cp xml_validator_cli.py validation/cli.py

# Copy tests
cp test_xml_validator.py tests/test_validation.py

# Copy examples
mkdir -p examples
cp examples.py examples/validation_examples.py
cp demo.py examples/
```

### Step 2: Create Module Init

Create `validation/__init__.py`:

```python
"""
XML Validation Module
=====================

Pre-validation for XBRL documents.
"""

from .xml_validator import (
    XMLValidator,
    ValidationResult,
    ValidationError,
    ValidationLevel,
    ValidationStatus,
    WellFormednessValidator,
    SchemaValidator,
    CustomRulesValidator,
    validate_batch
)

__all__ = [
    'XMLValidator',
    'ValidationResult',
    'ValidationError',
    'ValidationLevel',
    'ValidationStatus',
    'WellFormednessValidator',
    'SchemaValidator',
    'CustomRulesValidator',
    'validate_batch'
]

__version__ = '1.0.0'
```

### Step 3: Create XBRL-Specific Rules Module

Create `validation/xbrl_rules.py`:

```python
"""
XBRL-Specific Validation Rules
===============================

Custom validation rules for XBRL documents.
"""

from lxml import etree
from .xml_validator import ValidationError, ValidationLevel


def create_xbrl_validator(schema_path=None):
    """
    Create a validator configured for XBRL documents.
    
    Args:
        schema_path: Path to XBRL schema (optional)
        
    Returns:
        Configured XMLValidator with XBRL rules
    """
    from .xml_validator import XMLValidator
    
    validator = XMLValidator(schema_path=schema_path, fail_fast=True)
    
    # Add XBRL-specific rules
    validator.add_custom_rule(check_xbrl_namespaces, "XBRL Namespaces")
    validator.add_custom_rule(check_contexts, "Context Validation")
    validator.add_custom_rule(check_units, "Unit Validation")
    validator.add_custom_rule(check_fact_references, "Fact References")
    
    return validator


def check_xbrl_namespaces(xml_tree):
    """Ensure required XBRL namespaces are declared."""
    errors = []
    
    required_namespaces = {
        'xbrli': 'http://www.xbrl.org/2003/instance',
        'link': 'http://www.xbrl.org/2003/linkbase',
    }
    
    nsmap = xml_tree.nsmap or {}
    
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


def check_contexts(xml_tree):
    """Validate context elements."""
    errors = []
    
    contexts = xml_tree.xpath('//xbrli:context', namespaces={
        'xbrli': 'http://www.xbrl.org/2003/instance'
    })
    
    for ctx in contexts:
        # Check for ID attribute
        if 'id' not in ctx.attrib:
            errors.append(ValidationError(
                level=ValidationLevel.CUSTOM,
                line=ctx.sourceline,
                column=None,
                message="Context missing required 'id' attribute",
                error_type="MissingContextId"
            ))
        
        # Check for entity
        entity = ctx.xpath('.//xbrli:entity', namespaces={
            'xbrli': 'http://www.xbrl.org/2003/instance'
        })
        if not entity:
            errors.append(ValidationError(
                level=ValidationLevel.CUSTOM,
                line=ctx.sourceline,
                column=None,
                message="Context missing entity element",
                error_type="MissingEntity"
            ))
        
        # Check for period
        period = ctx.xpath('.//xbrli:period', namespaces={
            'xbrli': 'http://www.xbrl.org/2003/instance'
        })
        if not period:
            errors.append(ValidationError(
                level=ValidationLevel.CUSTOM,
                line=ctx.sourceline,
                column=None,
                message="Context missing period element",
                error_type="MissingPeriod"
            ))
    
    return errors


def check_units(xml_tree):
    """Validate unit elements."""
    errors = []
    
    units = xml_tree.xpath('//xbrli:unit', namespaces={
        'xbrli': 'http://www.xbrl.org/2003/instance'
    })
    
    for unit in units:
        # Check for ID attribute
        if 'id' not in unit.attrib:
            errors.append(ValidationError(
                level=ValidationLevel.CUSTOM,
                line=unit.sourceline,
                column=None,
                message="Unit missing required 'id' attribute",
                error_type="MissingUnitId"
            ))
        
        # Check for measure
        measures = unit.xpath('.//xbrli:measure', namespaces={
            'xbrli': 'http://www.xbrl.org/2003/instance'
        })
        if not measures:
            errors.append(ValidationError(
                level=ValidationLevel.CUSTOM,
                line=unit.sourceline,
                column=None,
                message="Unit missing measure element",
                error_type="MissingMeasure"
            ))
    
    return errors


def check_fact_references(xml_tree):
    """Validate that facts reference valid contexts and units."""
    errors = []
    
    # Collect valid IDs
    context_ids = set(xml_tree.xpath('//xbrli:context/@id', namespaces={
        'xbrli': 'http://www.xbrl.org/2003/instance'
    }))
    
    unit_ids = set(xml_tree.xpath('//xbrli:unit/@id', namespaces={
        'xbrli': 'http://www.xbrl.org/2003/instance'
    }))
    
    # Check fact references
    for elem in xml_tree.iter():
        # Check context reference
        if 'contextRef' in elem.attrib:
            ctx_ref = elem.attrib['contextRef']
            if ctx_ref not in context_ids:
                errors.append(ValidationError(
                    level=ValidationLevel.CUSTOM,
                    line=elem.sourceline,
                    column=None,
                    message=f"Fact references non-existent context: {ctx_ref}",
                    error_type="InvalidContextRef"
                ))
        
        # Check unit reference
        if 'unitRef' in elem.attrib:
            unit_ref = elem.attrib['unitRef']
            if unit_ref not in unit_ids:
                errors.append(ValidationError(
                    level=ValidationLevel.CUSTOM,
                    line=elem.sourceline,
                    column=None,
                    message=f"Fact references non-existent unit: {unit_ref}",
                    error_type="InvalidUnitRef"
                ))
    
    return errors
```

## 🔗 Integration Patterns

### Pattern 1: Pre-validation in Parser

Modify your existing parser to validate before processing:

```python
# In xbrl_parser/parser.py

from pathlib import Path
from validation import XMLValidator

class XBRLParser:
    """Your existing XBRL parser with XML validation."""
    
    def __init__(self, schema_path=None):
        self.xml_validator = XMLValidator(
            schema_path=schema_path,
            fail_fast=True
        )
        # Your existing initialization...
    
    def parse(self, filing_path: Path):
        """Parse XBRL filing with pre-validation."""
        
        # STEP 1: Validate XML structure
        validation_result = self.xml_validator.validate_file(filing_path)
        
        if not validation_result.is_valid:
            raise ValueError(
                f"XML validation failed for {filing_path}. "
                f"Errors: {len(validation_result.errors)}"
            )
        
        # STEP 2: Your existing XBRL parsing logic
        return self._parse_xbrl(filing_path)
    
    def _parse_xbrl(self, filing_path: Path):
        """Your existing parsing logic."""
        # ... your code here ...
        pass
```

### Pattern 2: Batch Processing with Validation

```python
# In scripts/validate_batch.py

from pathlib import Path
from validation import XMLValidator, validate_batch
from validation.xbrl_rules import create_xbrl_validator

def process_filings_with_validation(
    filings_dir: Path,
    schema_path: Path,
    output_dir: Path
):
    """Process XBRL filings with validation."""
    
    # Get all XML files
    filing_paths = list(filings_dir.glob("*.xml"))
    
    print(f"Found {len(filing_paths)} filings")
    
    # Create XBRL validator
    validator = create_xbrl_validator(schema_path)
    
    # Validate all files
    results = validate_batch(
        filing_paths,
        validator,
        output_report=output_dir / "validation_report.txt"
    )
    
    # Separate valid and invalid
    valid_files = [f for f, r in results.items() if r.is_valid]
    invalid_files = [f for f, r in results.items() if not r.is_valid]
    
    print(f"\nValidation complete:")
    print(f"  ✓ Valid: {len(valid_files)}")
    print(f"  ✗ Invalid: {len(invalid_files)}")
    
    # Process only valid files
    for filing_path in valid_files:
        try:
            process_single_filing(filing_path, output_dir)
        except Exception as e:
            print(f"Error processing {filing_path}: {e}")
    
    return valid_files, invalid_files


def process_single_filing(filing_path: Path, output_dir: Path):
    """Process a single validated filing."""
    # Your XBRL processing logic here
    pass


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 4:
        print("Usage: python validate_batch.py <filings_dir> <schema_path> <output_dir>")
        sys.exit(1)
    
    filings_dir = Path(sys.argv[1])
    schema_path = Path(sys.argv[2])
    output_dir = Path(sys.argv[3])
    
    process_filings_with_validation(filings_dir, schema_path, output_dir)
```

### Pattern 3: Pipeline Integration

```python
# In xbrl_parser/pipeline.py

from pathlib import Path
from typing import List
from validation import XMLValidator
from validation.xbrl_rules import create_xbrl_validator

class XBRLPipeline:
    """Complete XBRL processing pipeline with validation."""
    
    def __init__(self, schema_path: Path, config: dict):
        self.validator = create_xbrl_validator(schema_path)
        self.config = config
    
    def process_batch(self, filing_paths: List[Path]):
        """Process batch of filings."""
        
        # Stage 1: XML Validation (pre-filter)
        validated = self._validate_stage(filing_paths)
        
        # Stage 2: XBRL Parsing
        parsed = self._parse_stage(validated)
        
        # Stage 3: Mapping
        mapped = self._map_stage(parsed)
        
        # Stage 4: Output
        self._output_stage(mapped)
    
    def _validate_stage(self, filing_paths: List[Path]) -> List[Path]:
        """Validate all filings, return valid ones."""
        valid_files = []
        
        for filing_path in filing_paths:
            result = self.validator.validate_file(filing_path)
            
            if result.is_valid:
                valid_files.append(filing_path)
            else:
                self._log_validation_failure(filing_path, result)
        
        return valid_files
    
    def _parse_stage(self, valid_files: List[Path]):
        """Parse valid files."""
        # Your parsing logic
        pass
    
    def _map_stage(self, parsed_docs):
        """Map parsed documents."""
        # Your mapping logic
        pass
    
    def _output_stage(self, mapped_docs):
        """Output results."""
        # Your output logic
        pass
    
    def _log_validation_failure(self, filing_path: Path, result):
        """Log validation failures."""
        print(f"Validation failed: {filing_path}")
        for error in result.errors:
            print(f"  - {error}")
```

## 🧪 Testing Integration

Add tests to verify integration:

```python
# In tests/test_integration.py

import pytest
from pathlib import Path
from validation import XMLValidator
from validation.xbrl_rules import create_xbrl_validator
from xbrl_parser import XBRLParser  # Your parser

class TestXBRLParserIntegration:
    """Test integration of validator with parser."""
    
    def test_parser_rejects_invalid_xml(self, invalid_xml_file):
        """Parser should reject invalid XML."""
        parser = XBRLParser()
        
        with pytest.raises(ValueError, match="XML validation failed"):
            parser.parse(invalid_xml_file)
    
    def test_parser_accepts_valid_xml(self, valid_xbrl_file):
        """Parser should accept valid XML."""
        parser = XBRLParser()
        
        # Should not raise
        result = parser.parse(valid_xbrl_file)
        assert result is not None
    
    def test_validator_with_xbrl_rules(self, xbrl_file):
        """Test XBRL-specific validation rules."""
        validator = create_xbrl_validator()
        result = validator.validate_file(xbrl_file)
        
        # Should validate XBRL-specific requirements
        assert ValidationLevel.CUSTOM in result.levels_completed
```

## 📋 Configuration

### Create Configuration File

Create `config/validation_config.yaml`:

```yaml
validation:
  # Schema paths
  schemas:
    xbrl_instance: "schemas/xbrl-instance-2003.xsd"
    xbrl_linkbase: "schemas/xbrl-linkbase-2003.xsd"
  
  # Validation settings
  fail_fast: true
  
  # Custom rules to enable
  rules:
    - check_xbrl_namespaces
    - check_contexts
    - check_units
    - check_fact_references
  
  # Logging
  logging:
    level: INFO
    file: "logs/validation.log"
```

### Load Configuration

```python
# In validation/config.py

import yaml
from pathlib import Path

def load_validation_config(config_path: Path = None):
    """Load validation configuration."""
    if config_path is None:
        config_path = Path("config/validation_config.yaml")
    
    with open(config_path) as f:
        return yaml.safe_load(f)
```

## 🚀 Usage Examples

### Example 1: Simple Integration

```python
from validation import XMLValidator

# In your existing code
validator = XMLValidator()
result = validator.validate_file("filing.xml")

if result.is_valid:
    # Proceed with XBRL processing
    xbrl_doc = parse_xbrl(filing_path)
else:
    # Log and skip
    logger.error(f"Invalid XML: {result.errors}")
```

### Example 2: With XBRL Rules

```python
from validation.xbrl_rules import create_xbrl_validator

validator = create_xbrl_validator(schema_path="schemas/xbrl.xsd")
result = validator.validate_file("filing.xml")

if not result.is_valid:
    for error in result.errors:
        print(f"Error at line {error.line}: {error.message}")
```

### Example 3: CLI Usage

```bash
# Validate before processing
python -m validation.cli validate filings/company_2023.xml \
    --schema schemas/xbrl-instance-2003.xsd

# Batch validation
python -m validation.cli batch filings/ \
    --pattern "*.xml" \
    --output validation_report.txt
```

## 🔍 Troubleshooting

### Import Errors

If you get import errors:

```python
# Make sure validation is in your PYTHONPATH
import sys
sys.path.insert(0, '/path/to/your/project')

from validation import XMLValidator
```

### Lxml Not Found

```bash
# Already in your requirements.txt, but if needed:
pip install lxml>=4.9.0
```

### Performance Issues

```python
# Use fail_fast for better performance
validator = XMLValidator(fail_fast=True)

# Reuse validator instance in loops
for file_path in many_files:
    result = validator.validate_file(file_path)
```

## ✅ Verification Checklist

- [ ] Files copied to `validation/` directory
- [ ] `validation/__init__.py` created
- [ ] Tests running: `pytest tests/test_validation.py -v`
- [ ] Demo working: `python examples/demo.py`
- [ ] CLI accessible: `python -m validation.cli --help`
- [ ] Integrated with existing parser
- [ ] Batch processing script created
- [ ] Configuration file set up
- [ ] Documentation updated

## 📚 Next Steps

1. **Customize XBRL Rules**: Modify `validation/xbrl_rules.py` for your specific needs
2. **Add More Tests**: Expand `tests/test_validation.py` with your use cases
3. **Performance Tuning**: Profile and optimize for your file sizes
4. **CI/CD Integration**: Add validation to your pipeline
5. **Documentation**: Document your specific validation requirements

---

**Need help?** Check out:
- `README.md` - Full documentation
- `examples/validation_examples.py` - Usage examples
- `examples/demo.py` - Interactive demo
- `tests/test_validation.py` - Test examples
