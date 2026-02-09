# XML Document Validator

A robust, standalone XML validation tool designed for pre-XBRL validation and general XML document verification.

## 🎯 Purpose

Before processing XBRL documents, you need to ensure that the underlying XML structure is valid. This tool provides a **layered validation approach**:

1. **Well-formedness Check** - Is it valid XML?
2. **Schema Validation** - Does it conform to XSD?
3. **Custom Rules** - Does it meet business requirements?

**Fail fast principle**: Stop at the first layer that fails, saving processing time and providing clear feedback.

## ✨ Features

- ✅ **Multi-stage validation pipeline**
- ✅ **XSD schema validation support**
- ✅ **Custom rule engine** for business logic
- ✅ **Batch processing** for multiple files
- ✅ **Rich CLI interface** with beautiful output
- ✅ **Detailed error reporting** with line/column numbers
- ✅ **Fail-fast or continue-on-error** modes
- ✅ **Integration-ready** for XBRL pipelines
- ✅ **Comprehensive test coverage**

## 📋 Requirements

All dependencies are already in your `requirements.txt`:

```
lxml>=4.9.0          # XML parsing and validation
pydantic>=2.0.0      # Data validation (future use)
rich>=13.5.0         # CLI formatting
```

Python 3.12+ required.

## 🚀 Installation

Since you already have the required dependencies in your XBRL parser environment:

```bash
# Just place the files in your project
cp xml_validator.py your_project/
cp xml_validator_cli.py your_project/
cp examples.py your_project/
cp test_xml_validator.py your_project/tests/
```

Or integrate into your package structure:

```
your_project/
├── xbrl_parser/
│   ├── __init__.py
│   └── ...
├── validation/           # New module
│   ├── __init__.py
│   ├── xml_validator.py
│   └── cli.py
├── tests/
│   └── test_xml_validator.py
└── examples.py
```

## 📖 Quick Start

### Command Line Usage

```bash
# Validate a single file
python xml_validator_cli.py validate document.xml

# Validate with schema
python xml_validator_cli.py validate document.xml --schema schema.xsd

# Batch validate directory
python xml_validator_cli.py batch ./filings --pattern "*.xml"

# Generate report
python xml_validator_cli.py batch ./filings --output report.txt

# Verbose mode with debug info
python xml_validator_cli.py validate document.xml --verbose

# Don't stop on first error
python xml_validator_cli.py validate document.xml --no-fail-fast
```

### Python API Usage

#### Basic Validation

```python
from pathlib import Path
from xml_validator import XMLValidator

# Create validator
validator = XMLValidator()

# Validate a file
result = validator.validate_file("document.xml")

if result.is_valid:
    print("✓ Valid XML!")
else:
    print(f"✗ Found {len(result.errors)} errors")
    for error in result.errors:
        print(f"  Line {error.line}: {error.message}")
```

#### With Schema Validation

```python
from pathlib import Path
from xml_validator import XMLValidator

validator = XMLValidator(
    schema_path=Path("schemas/xbrl-instance-2003.xsd"),
    fail_fast=True
)

result = validator.validate_file("xbrl_document.xml")
print(result.summary())
```

#### With Custom Rules

```python
from xml_validator import XMLValidator, ValidationError, ValidationLevel

validator = XMLValidator()

# Define custom rule
def check_required_elements(xml_tree):
    """Ensure required elements are present."""
    errors = []
    
    required = ['context', 'unit']
    for elem_name in required:
        elements = xml_tree.xpath(f'//{elem_name}')
        if not elements:
            errors.append(ValidationError(
                level=ValidationLevel.CUSTOM,
                line=None,
                column=None,
                message=f"Missing required element: {elem_name}",
                error_type="MissingElement"
            ))
    
    return errors

# Add rule
validator.add_custom_rule(check_required_elements, "Required Elements Check")

# Validate
result = validator.validate_file("document.xml")
```

#### Batch Processing

```python
from pathlib import Path
from xml_validator import XMLValidator, validate_batch

# Get all XML files
xml_files = list(Path("filings").glob("*.xml"))

# Create validator
validator = XMLValidator(
    schema_path=Path("schemas/xbrl.xsd"),
    fail_fast=False
)

# Validate batch
results = validate_batch(
    xml_files,
    validator,
    output_report=Path("validation_report.txt")
)

# Process results
valid_files = [f for f, r in results.items() if r.is_valid]
invalid_files = [f for f, r in results.items() if not r.is_valid]

print(f"Valid: {len(valid_files)}, Invalid: {len(invalid_files)}")
```

## 🔗 Integration with XBRL Parser

### Pre-validation Pattern

```python
from pathlib import Path
from xml_validator import XMLValidator

def process_xbrl_filing(filing_path: Path):
    """Process XBRL filing with XML pre-validation."""
    
    # STEP 1: Validate XML structure
    validator = XMLValidator(
        schema_path=Path("schemas/xbrl-instance-2003.xsd"),
        fail_fast=True
    )
    
    validation_result = validator.validate_file(filing_path)
    
    if not validation_result.is_valid:
        # Reject invalid XML
        raise ValueError(f"XML validation failed: {filing_path}")
    
    # STEP 2: Parse XBRL (only if XML is valid)
    xbrl_doc = your_xbrl_parser.parse(filing_path)
    
    # STEP 3: XBRL-specific validation
    validate_xbrl_semantics(xbrl_doc)
    
    return xbrl_doc
```

### Pipeline Integration

```python
from pathlib import Path
from xml_validator import XMLValidator

class XBRLPipeline:
    """XBRL processing pipeline with validation."""
    
    def __init__(self, schema_path: Path):
        self.xml_validator = XMLValidator(
            schema_path=schema_path,
            fail_fast=True
        )
    
    def process_batch(self, filing_paths: list[Path]):
        """Process multiple filings with validation."""
        
        # Pre-filter invalid XML
        valid_files = []
        rejected_files = []
        
        for filing_path in filing_paths:
            result = self.xml_validator.validate_file(filing_path)
            
            if result.is_valid:
                valid_files.append(filing_path)
            else:
                rejected_files.append((filing_path, result))
        
        # Log rejections
        if rejected_files:
            self.log_rejections(rejected_files)
        
        # Process valid files
        for filing_path in valid_files:
            try:
                self.process_filing(filing_path)
            except Exception as e:
                self.handle_error(filing_path, e)
    
    def process_filing(self, filing_path: Path):
        """Process a single validated filing."""
        # Your XBRL processing logic
        pass
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest test_xml_validator.py -v

# Run with coverage
pytest test_xml_validator.py --cov=xml_validator --cov-report=html

# Run specific test class
pytest test_xml_validator.py::TestXMLValidator -v
```

## 📊 Validation Stages

### Stage 1: Well-formedness

Checks if the document is valid XML:
- Proper nesting of elements
- Balanced tags
- Valid attribute syntax
- Proper escaping

**Example Error:**
```
Line 15, Column 8: Opening and ending tag mismatch: name line 14 and ticker
```

### Stage 2: Schema Validation

Validates against XSD schema:
- Element presence
- Element order
- Data types
- Required attributes
- Cardinality constraints

**Example Error:**
```
Line 42: Element 'ticker': This element is not expected. Expected is ( name ).
```

### Stage 3: Custom Rules

Your business logic:
- XBRL-specific checks
- Context reference validation
- Unit reference validation
- Custom business rules

**Example Error:**
```
Line 67: Fact references non-existent context: ctx_2023_Q4
```

## 🎨 CLI Output Examples

### Successful Validation

```
════════════════════════════════════════════════════════════════════════
                        Validation Result                              
════════════════════════════════════════════════════════════════════════
✓ PASSED
File: company_2023.xml
Errors: 0 | Warnings: 0
Completed: wellformedness, schema, custom
════════════════════════════════════════════════════════════════════════
```

### Failed Validation

```
════════════════════════════════════════════════════════════════════════
                        Validation Result                              
════════════════════════════════════════════════════════════════════════
✗ FAILED
File: company_2023.xml
Errors: 2 | Warnings: 1
Completed: wellformedness, schema
════════════════════════════════════════════════════════════════════════

┏━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ #  ┃ Level         ┃ Location ┃ Message                      ┃
┡━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1  │ schema        │ L42:C5   │ Element 'ticker': Missing... │
│ 2  │ schema        │ L67:C8   │ Invalid context reference    │
└────┴───────────────┴──────────┴──────────────────────────────┘
```

## 🔧 Configuration

### Validator Options

```python
validator = XMLValidator(
    schema_path=Path("schema.xsd"),  # Optional XSD schema
    fail_fast=True,                   # Stop on first error
    logger=custom_logger              # Custom logger instance
)
```

### Custom Logger

```python
import logging
from xml_validator import XMLValidator

logger = logging.getLogger("my_validator")
logger.setLevel(logging.DEBUG)

validator = XMLValidator(logger=logger)
```

## 📝 Custom Rules Examples

### XBRL Namespace Check

```python
def check_xbrl_namespaces(xml_tree):
    """Ensure XBRL namespaces are declared."""
    errors = []
    
    required_namespaces = {
        'xbrli': 'http://www.xbrl.org/2003/instance',
        'link': 'http://www.xbrl.org/2003/linkbase',
    }
    
    nsmap = xml_tree.nsmap
    
    for prefix, uri in required_namespaces.items():
        if prefix not in nsmap:
            errors.append(ValidationError(
                level=ValidationLevel.CUSTOM,
                line=None,
                column=None,
                message=f"Missing namespace: {prefix}",
                error_type="MissingNamespace"
            ))
    
    return errors

validator.add_custom_rule(check_xbrl_namespaces, "XBRL Namespaces")
```

### Context Reference Validation

```python
def validate_context_references(xml_tree):
    """Ensure all facts reference valid contexts."""
    errors = []
    
    # Get all context IDs
    context_ids = set(xml_tree.xpath('//xbrli:context/@id', namespaces={
        'xbrli': 'http://www.xbrl.org/2003/instance'
    }))
    
    # Check fact references
    for elem in xml_tree.iter():
        if 'contextRef' in elem.attrib:
            ctx_ref = elem.attrib['contextRef']
            if ctx_ref not in context_ids:
                errors.append(ValidationError(
                    level=ValidationLevel.CUSTOM,
                    line=elem.sourceline,
                    column=None,
                    message=f"Invalid context reference: {ctx_ref}",
                    error_type="InvalidContextRef"
                ))
    
    return errors

validator.add_custom_rule(validate_context_references, "Context References")
```

## 🐛 Error Handling

### Graceful Degradation

```python
from xml_validator import XMLValidator

validator = XMLValidator(fail_fast=False)

try:
    result = validator.validate_file("document.xml")
    
    if result.is_valid:
        # Process document
        pass
    else:
        # Log errors and skip
        for error in result.errors:
            logger.error(f"{error}")

except Exception as e:
    # Handle unexpected errors
    logger.critical(f"Validation system error: {e}")
```

### File Access Errors

```python
from pathlib import Path

file_path = Path("document.xml")

if not file_path.exists():
    logger.error(f"File not found: {file_path}")
else:
    result = validator.validate_file(file_path)
```

## 📈 Performance Tips

1. **Use fail_fast=True** for production pipelines (faster)
2. **Cache schema validators** for batch processing
3. **Pre-filter files** by size before validation
4. **Use batch processing** for multiple files

```python
# Efficient batch processing
validator = XMLValidator(schema_path=schema, fail_fast=True)

# Reuse validator instance
for file_path in large_file_list:
    result = validator.validate_file(file_path)
    # Process result
```

## 🤝 Contributing

When contributing custom rules or enhancements:

1. Follow the existing code style
2. Add comprehensive tests
3. Update documentation
4. Use type hints
5. Add docstrings

## 📄 License

This tool integrates with your XBRL parser project.

## 🙏 Acknowledgments

Built with:
- **lxml** - The most feature-rich and easy-to-use library for processing XML
- **rich** - Beautiful terminal formatting
- **pytest** - Comprehensive testing framework

---

## 💡 Why This Architecture?

### Separation of Concerns
- Each validator handles one responsibility
- Easy to test independently
- Simple to extend

### Fail Fast Principle
- Stop at first error by default
- Save processing time
- Clear feedback on what needs fixing

### Layered Validation
- Like a security checkpoint system
- Each layer validates a different aspect
- Progressive validation stages

### Integration Ready
- Drop-in replacement for ad-hoc validation
- Clean API for programmatic use
- Designed for pipeline integration

---

**Ready to validate?** Start with the examples:

```bash
python examples.py
```

Or jump straight into the CLI:

```bash
python xml_validator_cli.py validate your_file.xml
```
