# Recursive XML Validator - User Guide

Complete guide for validating XML and XSD files in nested directory structures.

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Usage](#basic-usage)
3. [Command Options](#command-options)
4. [Real-World Examples](#real-world-examples)
5. [Understanding Output](#understanding-output)
6. [Advanced Usage](#advanced-usage)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

---

## 🚀 Quick Start

### Minimum Command

From your project root (`/home/a/Desktop/Stock_software/map_pro/`):

```bash
python -m xml_validator.validate_recursive /mnt/map_pro/
```

This will:
- Search recursively through ALL subdirectories
- Find all `*.xml` files (default pattern)
- Validate each file for well-formedness
- Display results in terminal

### Recommended Command

```bash
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --output ~/Desktop/validation_report_$(date +%Y%m%d_%H%M%S).txt \
    --show-tree \
    --verbose
```

---

## 📖 Basic Usage

### Syntax

```bash
python -m xml_validator.validate_recursive <DIRECTORY> [OPTIONS]
```

### Required Argument

| Argument | Description | Example |
|----------|-------------|---------|
| `DIRECTORY` | Root directory to search | `/mnt/map_pro/` |

### Common Patterns

```bash
# Validate XML files in SEC filings
python -m xml_validator.validate_recursive /mnt/map_pro/

# Validate XSD schema files
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --pattern "*.xsd"

# Validate with schema
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --schema /mnt/map_pro/schemas/xbrl-instance-2003.xsd
```

---

## ⚙️ Command Options

### 1. File Pattern (`-p`, `--pattern`)

**Purpose:** Specify which files to validate

**Default:** `*.xml`

**Syntax:**
```bash
--pattern "PATTERN"
-p "PATTERN"
```

**Examples:**

```bash
# Validate only XML files (default)
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --pattern "*.xml"

# Validate only XSD schema files
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --pattern "*.xsd"

# Validate specific naming pattern
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --pattern "*_instance.xml"

# Validate XBRL linkbase files
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --pattern "*_lab.xml"
```

**Use Cases:**
- `*.xml` - All XML files (default)
- `*.xsd` - Schema files
- `*_instance.xml` - XBRL instance documents
- `*_lab.xml` - XBRL label linkbases
- `*_pre.xml` - XBRL presentation linkbases
- `*_cal.xml` - XBRL calculation linkbases
- `*_def.xml` - XBRL definition linkbases

---

### 2. Schema Validation (`-s`, `--schema`)

**Purpose:** Validate files against an XSD schema

**Default:** None (well-formedness only)

**Syntax:**
```bash
--schema PATH_TO_SCHEMA
-s PATH_TO_SCHEMA
```

**Examples:**

```bash
# Basic schema validation
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --schema /mnt/map_pro/schemas/xbrl-instance-2003.xsd

# Validate with relative path (from project root)
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --schema ./schemas/xbrl-instance.xsd

# Validate taxonomy files
python -m xml_validator.validate_recursive /mnt/map_pro/taxonomies/ \
    --pattern "*.xsd" \
    --schema /mnt/map_pro/schemas/xbrl-schema-2003.xsd
```

**Important Notes:**
- Schema file must exist or command will fail
- Schema validation is performed AFTER well-formedness check
- If well-formedness fails, schema validation is skipped (fail-fast)

---

### 3. Output Report (`-o`, `--output`)

**Purpose:** Save detailed validation report to a file

**Default:** None (console output only)

**Syntax:**
```bash
--output PATH_TO_REPORT
-o PATH_TO_REPORT
```

**Examples:**

```bash
# Save to Desktop with timestamp
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --output ~/Desktop/validation_report_$(date +%Y%m%d_%H%M%S).txt

# Save to specific location
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --output /mnt/map_pro/reports/sec_validation.txt

# Save to home directory
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --output ~/sec_validation.txt

# Save with custom naming
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --output /tmp/validation_$(whoami)_$(date +%Y%m%d).txt
```

**Directory Creation Methods:**

```bash
# Method 1: Use existing directory
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --output ~/Desktop/report.txt

# Method 2: Create reports directory first
mkdir -p ~/validation_reports
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --output ~/validation_reports/sec_$(date +%Y%m%d).txt

# Method 3: Use data partition
mkdir -p /mnt/map_pro/validation_reports
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --output /mnt/map_pro/validation_reports/sec_validation.txt
```

**Report Naming Conventions:**

```bash
# With timestamp
validation_report_20250129_143022.txt

# With date only
validation_report_20250129.txt

# Descriptive names
sec_entities_validation.txt
xbrl_schemas_validation.txt
taxonomy_validation.txt

# By company or ticker
AAPL_10K_2023_validation.txt
```

**Report Contents:**
- Header with directory and statistics
- Summary of total/valid/invalid counts
- Detailed validation results for each file
- Full error messages with line numbers

---

### 4. Maximum Depth (`-d`, `--max-depth`)

**Purpose:** Limit how deep to search in directory tree

**Default:** Unlimited (searches all subdirectories)

**Syntax:**
```bash
--max-depth NUMBER
-d NUMBER
```

**Examples:**

```bash
# Search only immediate subdirectories (depth 1)
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --max-depth 1

# Search 3 levels deep
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --max-depth 3

# Search 5 levels deep (good for XBRL structures)
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --max-depth 5
```

**Understanding Depth:**

```
/mnt/map_pro/          <- Depth 0 (root)
├── company_A/                                  <- Depth 1
│   ├── 10-K/                                   <- Depth 2
│   │   ├── 2023/                               <- Depth 3
│   │   │   ├── filing_12345/                   <- Depth 4
│   │   │   │   ├── instance.xml                <- Depth 5
│   │   │   │   └── calculation.xml             <- Depth 5
```

**Use Cases:**

| Depth | Use Case | Example |
|-------|----------|---------|
| 1 | Top-level directories only | Company folders |
| 2 | Company + Form type | Company → 10-K |
| 3 | Company + Form + Year | Company → 10-K → 2023 |
| 4 | Company + Form + Year + Filing | Company → 10-K → 2023 → filing_id |
| 5+ | Full XBRL structure | All files in filings |

**Performance Impact:**
- Lower depth = Faster search, fewer files
- Higher depth = Slower search, more files
- Use `--max-depth` to limit scope for testing

---

### 5. Show Directory Tree (`--show-tree`)

**Purpose:** Display directory structure before validation

**Default:** Off

**Syntax:**
```bash
--show-tree
```

**Example:**

```bash
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --show-tree
```

**Output Example:**

```
Directory Structure:
  📁 ./
    └─ company_a_10k_2023.xml
  📁 company_A/10-K/2023/filing_12345/
    └─ instance.xml
    └─ calculation.xml
    └─ presentation.xml
  📁 company_B/10-Q/2023/filing_67890/
    └─ instance.xml
```

**Use Cases:**
- Verify search found correct directories
- Understand file organization
- Debug pattern matching
- Document directory structure

---

### 6. Verbose Mode (`-v`, `--verbose`)

**Purpose:** Show detailed progress for each file

**Default:** Off (shows only progress bar)

**Syntax:**
```bash
--verbose
-v
```

**Example:**

```bash
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --verbose
```

**Output Comparison:**

**Without `--verbose`:**
```
Validating files... ████████████████████ 100%
```

**With `--verbose`:**
```
Validating instance.xml...
Validating calculation.xml...
Validating presentation.xml...
...
```

**Use Cases:**
- Debug validation issues
- Monitor long-running validations
- Track which file is being processed
- Identify slow files

---

### 7. Fail-Fast Mode (`--no-fail-fast`)

**Purpose:** Continue validating all stages even after errors

**Default:** Fail-fast enabled (stops at first error per file)

**Syntax:**
```bash
--no-fail-fast
```

**Example:**

```bash
# Default: stop at first error in each file
python -m xml_validator.validate_recursive /mnt/map_pro/

# Continue through all validation stages
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --no-fail-fast
```

**Behavior:**

**With fail-fast (default):**
```
File: instance.xml
  ✗ Well-formedness check failed
  → Stops here, skips schema validation
```

**Without fail-fast (`--no-fail-fast`):**
```
File: instance.xml
  ✗ Well-formedness check failed
  → Continues to schema validation
  ✗ Schema validation also failed
```

**Use Cases:**
- `--no-fail-fast`: Get complete error picture
- Default (fail-fast): Faster validation, immediate feedback

---

## 🎯 Real-World Examples

### Example 1: Quick Check - SEC Entities

**Scenario:** Quickly check if SEC filing XMLs are well-formed

```bash
python -m xml_validator.validate_recursive /mnt/map_pro/
```

**What it does:**
- Finds all `*.xml` files recursively
- Validates well-formedness
- Shows summary in terminal
- No report saved

---

### Example 2: Full Validation with Report

**Scenario:** Comprehensive validation with detailed report

```bash
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --schema /mnt/map_pro/schemas/xbrl-instance-2003.xsd \
    --output ~/Desktop/sec_validation_$(date +%Y%m%d).txt \
    --show-tree \
    --verbose
```

**What it does:**
- Validates against XSD schema
- Shows directory tree
- Detailed progress for each file
- Saves report to Desktop with date

---

### Example 3: Validate Specific Company

**Scenario:** Validate all filings for Apple (AAPL)

```bash
python -m xml_validator.validate_recursive /mnt/map_pro/AAPL/ \
    --output ~/Desktop/AAPL_validation.txt
```

---

### Example 4: Validate Only Instance Documents

**Scenario:** Check only XBRL instance files

```bash
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --pattern "*_instance.xml" \
    --schema /mnt/map_pro/schemas/xbrl-instance-2003.xsd
```

---

### Example 5: Validate Schemas

**Scenario:** Validate all XSD schema files

```bash
python -m xml_validator.validate_recursive /mnt/map_pro/schemas/ \
    --pattern "*.xsd" \
    --output ~/Desktop/schema_validation.txt
```

---

### Example 6: Limited Depth Search

**Scenario:** Only validate files 3 levels deep (for testing)

```bash
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --max-depth 3 \
    --show-tree
```

---

### Example 7: Monthly Audit Report

**Scenario:** Generate monthly validation report for compliance

```bash
# Create reports directory
mkdir -p /mnt/map_pro/compliance/reports/

# Run comprehensive validation
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --schema /mnt/map_pro/schemas/xbrl-instance-2003.xsd \
    --output /mnt/map_pro/compliance/reports/monthly_validation_$(date +%Y_%m).txt \
    --no-fail-fast
```

---

### Example 8: Validate Specific Form Types

**Scenario:** Only validate 10-K filings

```bash
python -m xml_validator.validate_recursive /mnt/map_pro/*/10-K/ \
    --output ~/Desktop/10K_validation.txt
```

---

### Example 9: Debug Failing Files

**Scenario:** Find out why specific files are failing

```bash
python -m xml_validator.validate_recursive /mnt/map_pro/problem_company/ \
    --verbose \
    --show-tree \
    --no-fail-fast \
    --output ~/Desktop/debug_report.txt
```

---

### Example 10: Batch Validation Script

**Scenario:** Create a script to validate multiple directories

Create `validate_all.sh`:

```bash
#!/bin/bash

REPORT_DIR=~/Desktop/validation_reports
mkdir -p "$REPORT_DIR"

# Validate SEC entities
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --output "$REPORT_DIR/sec_$(date +%Y%m%d).txt"

# Validate schemas
python -m xml_validator.validate_recursive /mnt/map_pro/schemas/ \
    --pattern "*.xsd" \
    --output "$REPORT_DIR/schemas_$(date +%Y%m%d).txt"

# Validate taxonomies
python -m xml_validator.validate_recursive /mnt/map_pro/taxonomies/ \
    --output "$REPORT_DIR/taxonomies_$(date +%Y%m%d).txt"

echo "All validations complete! Reports saved to: $REPORT_DIR"
```

Run it:
```bash
chmod +x validate_all.sh
./validate_all.sh
```

---

## 📊 Understanding Output

### Terminal Output Structure

```
╔══════════════════════════════════════════════════════════════════════╗
║                     Recursive XML Validation                         ║
╚══════════════════════════════════════════════════════════════════════╝

Searching for files in: /mnt/map_pro/
Pattern: *.xml

Found 1,247 files

Validating files... ████████████████████ 100%

╔══════════════════════════════════════════════════════════════════════╗
║                        Validation Summary                            ║
╚══════════════════════════════════════════════════════════════════════╝

Overall Statistics
┌──────────────┬────────┐
│ Metric       │  Count │
├──────────────┼────────┤
│ Total Files  │  1,247 │
│ Valid        │  1,189 │
│ Invalid      │     58 │
│ Success Rate │  95.3% │
└──────────────┴────────┘

Errors by Type
┌─────────────────────┬───────┐
│ Error Type          │ Count │
├─────────────────────┼───────┤
│ XMLSyntaxError      │    42 │
│ MissingNamespace    │    10 │
│ InvalidContextRef   │     6 │
└─────────────────────┴───────┘

Directories with Most Errors
┌──────────────────────────────────────────┬────────┐
│ Directory                                │ Errors │
├──────────────────────────────────────────┼────────┤
│ company_abc/10-K/2023/filing_123/        │     12 │
│ company_xyz/10-Q/2023/filing_456/        │      8 │
└──────────────────────────────────────────┴────────┘

Invalid Files
┌─────────────────────────┬────────┬──────────────────────────────┐
│ File                    │ Errors │ Directory                    │
├─────────────────────────┼────────┼──────────────────────────────┤
│ instance.xml            │      3 │ company_abc/10-K/2023/...    │
│ calculation.xml         │      2 │ company_abc/10-K/2023/...    │
└─────────────────────────┴────────┴──────────────────────────────┘
```

### Report File Structure

```
======================================================================
RECURSIVE XML VALIDATION REPORT
======================================================================

Root Directory: /mnt/map_pro/
Total Files: 1,247
Valid: 1,189
Invalid: 58
Success Rate: 95.3%

======================================================================

File: /mnt/map_pro/company_A/10-K/2023/instance.xml
----------------------------------------------------------------------
======================================================================
XML Validation Report: instance.xml
======================================================================
Status: ✗ FAILED
Timestamp: 2025-01-29T14:30:22.123456
Levels Completed: wellformedness

Errors: 1
Warnings: 0

──────────────────────────────────────────────────────────────────────
ERRORS:
1. [WELLFORMEDNESS] Line 42, Column 5: Opening and ending tag mismatch
======================================================================
```

---

## 🔧 Advanced Usage

### Combining Multiple Options

```bash
# Full-featured validation
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --pattern "*.xml" \
    --schema /mnt/map_pro/schemas/xbrl-instance-2003.xsd \
    --output ~/Desktop/full_validation_$(date +%Y%m%d_%H%M%S).txt \
    --max-depth 10 \
    --show-tree \
    --verbose \
    --no-fail-fast
```

### Using with Shell Variables

```bash
# Define variables
DATA_DIR="/mnt/map_pro/sec"
SCHEMA_PATH="/mnt/map_pro/schemas/xbrl-instance-2003.xsd"
REPORT_DIR="$HOME/Desktop/validation_reports"
DATE=$(date +%Y%m%d)

# Create report directory
mkdir -p "$REPORT_DIR"

# Run validation
python -m xml_validator.validate_recursive "$DATA_DIR" \
    --schema "$SCHEMA_PATH" \
    --output "$REPORT_DIR/validation_$DATE.txt"
```

### Filtering Results with Grep

```bash
# Save report and search for specific errors
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --output /tmp/validation.txt

# Find all XMLSyntaxError
grep "XMLSyntaxError" /tmp/validation.txt

# Find all failed files
grep "FAILED" /tmp/validation.txt

# Count errors by type
grep -o "Error Type: [^\"]*" /tmp/validation.txt | sort | uniq -c
```

### Automated Daily Validation

Create a cron job:

```bash
# Edit crontab
crontab -e

# Add daily validation at 2 AM
0 2 * * * cd /home/a/Desktop/Stock_software/map_pro && python -m xml_validator.validate_recursive /mnt/map_pro/ --output /mnt/map_pro/daily_reports/validation_$(date +\%Y\%m\%d).txt
```

---

## 🐛 Troubleshooting

### Error: "Directory not found"

```bash
# Check if directory exists
ls -la /mnt/map_pro/

# Use absolute path
python -m xml_validator.validate_recursive /mnt/map_pro/

# Not relative path like:
python -m xml_validator.validate_recursive ../../../mnt/map_pro/...
```

### Error: "Schema file not found"

```bash
# Verify schema exists
ls -la /mnt/map_pro/schemas/xbrl-instance-2003.xsd

# Use correct path
--schema /mnt/map_pro/schemas/xbrl-instance-2003.xsd
```

### Error: "No files matching pattern found"

```bash
# Check pattern
ls /mnt/map_pro/*.xml

# Try different patterns
--pattern "*.xml"
--pattern "*instance.xml"
--pattern "*.xsd"

# Verify files exist
find /mnt/map_pro/ -name "*.xml" | head -5
```

### Error: "Permission denied" on report output

```bash
# Make sure directory exists
mkdir -p ~/Desktop/reports

# Use directory you have write access to
--output ~/Desktop/report.txt

# Not:
--output /root/report.txt  # No permission
```

### Validation is too slow

```bash
# Limit depth
--max-depth 3

# Test on smaller subset first
python -m xml_validator.validate_recursive /mnt/map_pro/single_company/

# Use fail-fast (default)
# Don't use --no-fail-fast for large batches
```

### Can't see file names during validation

```bash
# Use verbose mode
--verbose
```

---

## ✅ Best Practices

### 1. Start Small, Scale Up

```bash
# First: Test on single company
python -m xml_validator.validate_recursive /mnt/map_pro/AAPL/

# Then: Expand to all
python -m xml_validator.validate_recursive /mnt/map_pro/
```

### 2. Always Save Reports for Audits

```bash
# Create reports directory
mkdir -p /mnt/map_pro/validation_reports

# Always use --output
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --output /mnt/map_pro/validation_reports/validation_$(date +%Y%m%d).txt
```

### 3. Use Descriptive Report Names

```bash
# Good naming
validation_sec_entities_20250129.txt
validation_xbrl_schemas_20250129.txt
validation_AAPL_10K_2023.txt

# Avoid
report.txt
output.txt
validation.txt
```

### 4. Combine with Schema When Available

```bash
# Better: Use schema
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --schema /mnt/map_pro/schemas/xbrl-instance-2003.xsd

# vs. Just well-formedness
python -m xml_validator.validate_recursive /mnt/map_pro/
```

### 5. Use Appropriate Depth for File Structure

```bash
# For XBRL structure (company/form/year/filing/files)
--max-depth 5

# For shallow structures
--max-depth 2
```

### 6. Keep Reports Organized

```bash
# By date
/mnt/map_pro/reports/2025/01/validation_20250129.txt

# By type
/mnt/map_pro/reports/sec/validation_latest.txt
/mnt/map_pro/reports/schemas/validation_latest.txt

# By company
/mnt/map_pro/reports/AAPL/validation_20250129.txt
```

---

## 📝 Quick Reference Card

```bash
# Basic validation
python -m xml_validator.validate_recursive /mnt/map_pro/

# Full options
python -m xml_validator.validate_recursive DIRECTORY \
    --pattern "*.xml" \              # File pattern
    --schema SCHEMA.xsd \            # XSD schema
    --output REPORT.txt \            # Report file
    --max-depth 5 \                  # Search depth
    --show-tree \                    # Show structure
    --verbose \                      # Show progress
    --no-fail-fast                   # Continue on errors

# Common patterns
*.xml          # All XML files
*.xsd          # All schema files
*_instance.xml # Instance documents
*_lab.xml      # Label linkbases
*_pre.xml      # Presentation linkbases
*_cal.xml      # Calculation linkbases
*_def.xml      # Definition linkbases

# Report naming
~/Desktop/report_$(date +%Y%m%d).txt              # Date
~/Desktop/report_$(date +%Y%m%d_%H%M%S).txt       # Date + time
/mnt/map_pro/reports/validation_$(whoami).txt     # Username
```

---

## 🎓 Summary

You now have complete control over recursive XML validation with these options:

| Option | Purpose | When to Use |
|--------|---------|-------------|
| `--pattern` | File type | Always specify (or use default `*.xml`) |
| `--schema` | Schema validation | When you have XSD schemas |
| `--output` | Save report | For audits, documentation |
| `--max-depth` | Limit search | Testing, performance |
| `--show-tree` | See structure | Debugging, documentation |
| `--verbose` | Detailed progress | Long validations, debugging |
| `--no-fail-fast` | Complete errors | Thorough analysis |

**Most Common Command:**
```bash
python -m xml_validator.validate_recursive /mnt/map_pro/ \
    --output ~/Desktop/validation_$(date +%Y%m%d).txt
```

Happy validating! 🎉