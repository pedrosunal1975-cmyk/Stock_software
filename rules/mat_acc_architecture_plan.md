# mat_acc: Mathematical Accountancy Software
## Detailed Architecture & Implementation Plan

**Version:** 1.0  
**Date:** February 3, 2026  
**Purpose:** Financial analysis software for verified XBRL statements

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Architecture Principles](#architecture-principles)
4. [Data Inputs](#data-inputs)
5. [Database Schema](#database-schema)
6. [Processing Pipeline](#processing-pipeline)
7. [Module Specifications](#module-specifications)
8. [Output Specifications](#output-specifications)
9. [Implementation Roadmap](#implementation-roadmap)

---

## Executive Summary

**mat_acc** is a financial analysis system that performs ratio analysis on verified XBRL financial statements. The system follows a strict hierarchy-first approach, building structural understanding before semantic mapping, ensuring accurate calculations regardless of company-specific presentation variations.

### Core Philosophy

1. **Hierarchy First**: Build the complete structural map of statements before attempting any normalization
2. **Company Filing as Ground Truth**: The XBRL filing defines the authoritative structure
3. **Verification Integration**: Only calculate ratios on verified data
4. **Separation of Concerns**: Structure → Semantics → Calculations → Display

### Success Criteria

- Accurately map 100% of concepts from verified statements into hierarchical database
- Calculate standard financial ratios with traceable lineage to source facts
- Handle both US SEC and ESEF filings
- Maintain audit trail from ratio back to original XBRL fact

---

## System Overview

### IPO Architecture (Input → Process → Output)

```
┌─────────────────────────────────────────────────────────────────┐
│                            INPUTS                                │
├─────────────────────────────────────────────────────────────────┤
│ • Mapped statements (JSON/Excel/CSV - PRIMARY INPUT)            │
│ • Verification report (verification_report.json)                │
│ • Parsed data (parsed.json - for taxonomy refs ONLY)            │
│ • Taxonomy libraries (already built engine needs integration)   │
│ • XBRL linkbases (presentation, calculation, definition)        │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                           PROCESS                                │
├─────────────────────────────────────────────────────────────────┤
│ Module 1: Hierarchy Builder                                     │
│   - Extract statement structures from presentation linkbase     │
│   - Generate concept IDs with positional encoding               │
│   - Build parent-child relationships                            │
│                                                                  │
│ Module 2: Database Populator                                    │
│   - Insert concepts into SQL database                           │
│   - Store calculation relationships                             │
│   - Link to verification results                                │
│                                                                  │
│ Module 3: Taxonomy Enricher                                     │
│   - Add standard taxonomy labels as metadata                    │
│   - Preserve company-specific extensions                        │
│                                                                  │
│ Module 4: Role Mapper                                           │
│   - Apply contextual mapping rules                              │
│   - Generate normalized semantic names                          │
│   - Categorize concepts for ratio calculations                  │
│                                                                  │
│ Module 5: Financial Data Accessor                               │
│   - Provide semantic query interface                            │
│   - Abstract away structural variations                         │
│   - Handle missing data gracefully                              │
│                                                                  │
│ Module 6: Ratio Calculation Engine                              │
│   - Execute ratio formulas                                      │
│   - Validate against verification results                       │
│   - Cross-check calculations                                    │
│   - Track calculation lineage                                   │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                           OUTPUT                                 │
├─────────────────────────────────────────────────────────────────┤
│ • Normalized financial statements                               │
│ • Comprehensive ratio analysis report                           │
│ • Calculation audit trail                                       │
│ • Data quality metrics                                          │
│ • Human-readable formatted reports                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Architecture Principles

### 1. Hierarchy-First Approach

**Problem Statement:**  
The same XBRL concept (e.g., `us-gaap:AssetsCurrent`) can appear in multiple contexts with different meanings. Traditional name-based mapping creates ambiguity.

**Solution:**  
Build complete hierarchical structure first. A concept's position in the calculation tree defines its identity more definitively than its label.

**Implementation:**  
Each concept gets a unique positional identifier that encodes:
- Statement type (BS, IS, CF, EQ, OT)
- Hierarchy level (nesting depth)
- Sibling position (order among peers)
- Context reference (period/dimension)

**Example:**
```
Concept: us-gaap:AssetsCurrent
Context: c-4
Position in BS: Level 2, Sibling 1
Generated ID: BS-002-001-c4

Same Concept in different calculation:
Context: c-5
Position in BS: Level 3, Sibling 2
Generated ID: BS-003-002-c5
```

### 2. Company Filing as Ground Truth

**Principle:**  
The company's XBRL presentation and calculation linkbases define the authoritative structure. Standard taxonomy labels are descriptive metadata, NOT prescriptive structure builders.

**Implication:**
- Do NOT reorganize company-provided hierarchy
- Do NOT override company calculation relationships
- Extension taxonomies follow company-defined positions
- Taxonomy labels are helpers, not builders

### 3. Verification Integration

**Principle:**  
mat_acc processes only **verified companies** (companies whose filings passed verification), but does NOT require every individual fact to be verified.

**Critical Distinction:**
- **Verified Company:** Filing passed overall verification with acceptable score
- **Verified Fact:** Individual concept was checked by verification engine

**Why This Matters:**
The verification engine checks approximately 1/3 of all facts:
- Example: Mapper processes 9,426 paths/arrays/objects
- Example: Verification performs 639 checks (577 passed, 0 failed)
- Ratio: ~1/3 of facts are verified, 2/3 are not checked

**Verification Scope:**
- Focuses on horizontal/vertical calculation checks
- Validates main aggregations (Assets, Liabilities, Equity, etc.)
- Does NOT verify every detailed line item

**mat_acc Requirements:**

1. **Company-Level Verification (REQUIRED):**
   - Check overall verification score before processing
   - Reject companies with critical calculation failures
   - Accept companies with score ≥ 95.0

2. **Fact-Level Verification (OPTIONAL/PREFERRED):**
   - Prefer verified facts when available
   - Use unverified facts when needed for ratios
   - DO NOT reject facts just because they weren't verified
   - Use verification status for confidence scoring only

3. **Quality Scoring:**
   - High confidence: Verified company + verified fact
   - Medium confidence: Verified company + unverified fact
   - Low confidence: Data issues or inconsistencies

**Implementation:**
- ✅ Check company-level verification score
- ✅ Use verification metadata to enhance confidence
- ✅ Calculate ratios using all available facts
- ✅ Flag ratio confidence based on input verification status
- ❌ DO NOT refuse ratios due to unverified facts
- ❌ DO NOT skip valid numeric facts

**Rationale:**
Many valid facts needed for detailed ratio analysis (expense breakdowns, investment categories) are not checked by verification because they're not part of main aggregation calculations. mat_acc's comprehensive financial analysis requires broader fact coverage.

### 4. Separation of Concerns

**Layer 1: Structure**  
Where are concepts positioned? (Hierarchy Builder)

**Layer 2: Semantics**  
What do concepts mean? (Role Mapper)

**Layer 3: Calculations**  
How do concepts compute? (Ratio Engine)

**Layer 4: Display**  
How do concepts appear to humans? (Report Generator)

Each layer is independent and testable.

---

## Data Inputs

### Input Overview & Critical Distinctions

**IMPORTANT:** This section clarifies the difference between raw parsed data and mapped statements.

**Two Primary Data Sources:**

1. **parsed.json** = Raw facts + metadata (NOT the primary input)
   - Contains: All raw XBRL facts before statement organization
   - Contains: Taxonomy namespaces and library references
   - Contains: Metadata about filing
   - **mat_acc Use:** Extract taxonomy library list ONLY
   - **Alternative:** Can skip if taxonomy list obtainable from XBRL filing directly

2. **Mapped Statements** = Organized hierarchical statements (PRIMARY INPUT)
   - File examples: `consolidatedbalancesheet.json`, `fairvaluemeasurements.json`
   - Formats: JSON, Excel (.xlsx), CSV
   - Contains: Facts organized into statement hierarchies
   - Contains: level, order, parent_concept pre-computed
   - **mat_acc Use:** THIS is the main source for hierarchy building

**Why This Matters:**
- Parser creates parsed.json from XBRL → lists all facts
- Mapper creates statement files from XBRL → organizes facts into statements
- Both come from same XBRL filing but serve different purposes
- mat_acc primarily needs mapped statements, optionally uses parsed.json for taxonomy info

---

### Input 1: Parsed XBRL Data (parsed.json)

**Source:** Your existing XBRL parser  
**Contains:** Raw facts data and taxonomy/namespace information (NOT mapped statements)

**Purpose for mat_acc:**
- Provides list of standard taxonomy libraries used (e.g., us-gaap, dei, srt)
- Contains namespace mappings
- Lists all raw facts before statement mapping
- Optional input - can be replaced by direct XBRL filing analysis if needed

**Structure Example (from actual parsed.json):**
```json
{
  "metadata": {
    "filing_id": "aci-20250222",
    "document_type": "10-K",
    "filing_date": "2025-04-21",
    "period_end_date": "2025-10-13T00:00:00",
    "company_name": "Albertsons Companies, Inc.",
    "entity_identifier": "0001646972",
    "market": "sec"
  },
  "instance": {
    "facts": [
      {
        "concept": "dei:EntityCentralIndexKey",
        "value": "1646972",
        "context_ref": "c-1",
        "fact_type": "NUMERIC",
        "period_type": "duration",
        "period_start": "2024-02-25",
        "period_end": "2025-02-22"
      }
    ],
    "units": {
      "usd": { ... },
      "shares": { ... }
    },
    "namespaces": {
      "us-gaap": "http://fasb.org/us-gaap/2024",
      "dei": "http://xbrl.sec.gov/dei/2024",
      "aci": "http://www.albertsons.com/20250222"
    }
  },
  "statistics": {
    "total_duration_ms": 0.0
  }
}
```

**What mat_acc Uses from parsed.json:**
- `namespaces`: To identify which taxonomy libraries to load
- `metadata.market`: To determine filing type (SEC vs ESEF)
- `metadata.entity_identifier`: Company identification
- **Note:** Facts array is NOT used - mat_acc uses mapped statements instead

**Alternative:** If mat_acc can deduce taxonomy library list from XBRL filing directly, parsed.json is optional.

### Input 1b: Mapped Statements (Primary Input)

**Source:** Your existing XBRL mapper/statement generator  
**Contains:** Complete hierarchical financial statements with fact metadata  
**Formats Available:** JSON, Excel (.xlsx), CSV

**File Examples:**
- `consolidatedbalancesheet.json`
- `consolidatedstatementsofstockholders.json`
- `fairvaluemeasurements.json`
- `leasestables.json`
- `consolidatedstatementsofincome.json`
- `consolidatedstatementsofcashflows.json`
- ... (can be 107+ statements for some SEC companies)

**Key Characteristics:**
- **SEC Companies:** Can produce 100+ small/medium specialized statements
- **ESEF Companies:** Fewer statement files, more consolidated
- **Statement Types:** All map to main categories: BS, IS, CF, Equity, Other
- **mat_acc Goal:** Consolidate all these statements into 4-6 main categories without losing information

**Mapped Statement Structure (Example):**
```json
{
  "statement_name": "Consolidated Balance Sheet",
  "statement_type": "Balance Sheet",
  "role_uri": "http://www.albertsons.com/role/ConsolidatedBalanceSheet",
  "facts": [
    {
      "concept": "us-gaap_CommonStockValue",
      "value": "6.0",
      "context_ref": "c-13",
      "unit_ref": "usd",
      "decimals": "-5",
      "level": 5,
      "order": "2",
      "parent_concept": "us-gaap_StockholdersEquityAbstract",
      "period_type": "instant",
      "period_start": null,
      "period_end": "2025-02-22",
      "dimensions": {
        "us-gaap:StatementClassOfStockAxis": "us-gaap:CommonClassAMember"
      },
      "sign": null,
      "scale": null,
      "format": null,
      "is_nil": false,
      "fact_id": "f-139",
      "display_value": "600000.0",
      "formatted_value": "$600,000",
      "scaling_factor": 100000
    }
  ]
}
```

**Key Fields for mat_acc:**
- `concept`: XBRL concept name
- `value`: Numeric value (scaled)
- `context_ref`: Period/dimension identifier
- `level`: Hierarchy depth (pre-computed by mapper)
- `order`: Sibling position (pre-computed by mapper)
- `parent_concept`: Direct parent in hierarchy
- `period_type`: instant or duration
- `period_end`: Date for instant facts
- `dimensions`: Dimensional breakdowns
- `fact_id`: Unique identifier
- `display_value`: Unscaled numeric value
- `scaling_factor`: Value multiplier
- `statement_type`: Which main statement category this belongs to

**Format Selection for mat_acc:**
- **JSON:** Recommended for programmatic processing
- **Excel:** Alternative if easier to parse hierarchical structure
- **CSV:** Alternative for simpler data structures

**Critical Point:** These mapped statements ARE the primary input for mat_acc's hierarchy builder, NOT parsed.json. The mapper has already processed the XBRL and organized facts into statement structures.

### Input 2: Verification Report (verification_report.json)

**Source:** Your existing verification module  
**Contains:** Calculation validation results

**Report Structure (Example):**
```json
{
  "filing_id": "sec/Albertsons_Companies_Inc/10_K/2025-10-13",
  "market": "sec",
  "company": "Albertsons_Companies_Inc",
  "form": "10_K",
  "date": "2025-10-13",
  "verified_at": "2026-02-02T00:48:03.729820",
  "processing_time_ms": 10.411,
  "summary": {
    "score": 100.0,
    "total_checks": 639,
    "passed": 577,
    "failed": 0,
    "skipped": 62,
    "critical_issues": 0,
    "warning_issues": 0,
    "info_issues": 0
  },
  "checks": [
    {
      "check_name": "calculation_consistency",
      "check_type": "horizontal",
      "passed": true,
      "severity": "info",
      "message": "us-gaap:LiabilitiesCurrent: expected 7,251, found 7,251 OK",
      "expected_value": 7251.0,
      "actual_value": 7251.0,
      "difference": 0.0,
      "concept": "us-gaap:LiabilitiesCurrent",
      "context_id": "c-4",
      "details": {
        "source": "company",
        "children_count": 7,
        "missing_children": [],
        "sign_corrections": 0,
        "children": [
          {
            "concept": "us-gaap_AccountsPayableCurrent",
            "value": 4092.7,
            "weight": 1.0,
            "contribution": 4092.7
          }
        ]
      }
    }
  ]
}
```

**Key Fields for mat_acc:**
- `summary.score`: Overall data quality
- `checks[].passed`: Whether calculation verified
- `checks[].concept`: Which concept was checked
- `checks[].context_id`: Period/dimension
- `checks[].expected_value`: Calculated value
- `checks[].actual_value`: Reported value
- `checks[].difference`: Discrepancy
- `checks[].details.children`: Component breakdown

**Usage in mat_acc:**
- Only calculate ratios using concepts where `passed = true`
- Use `children` data to understand calculation components
- Use `difference` to assess data reliability
- Flag ratios calculated from concepts with warnings

### Input 3: Taxonomy Libraries

**Source:** Your existing taxonomy manager  
**Contains:** Standard taxonomy definitions (US GAAP, IFRS, etc.)

**Data Needed:**
- Concept labels (standard, terse, verbose)
- Concept documentation
- Balance type (debit/credit)
- Period type (instant/duration)
- Data type (monetary, shares, pure)

**Note:** mat_acc does NOT need to download taxonomies—your existing system handles this.

### Input 4: XBRL Linkbases

**From parsed XBRL filing:**
- **Presentation Linkbase**: Statement structure, display order
- **Calculation Linkbase**: Parent-child calculation relationships, weights
- **Definition Linkbase**: Dimensional relationships (if needed)

**Usage:**
- Presentation linkbase: Build hierarchy
- Calculation linkbase: Validate calculations, understand aggregations
- Definition linkbase: Handle dimensional data (segments, scenarios)

---

## Database Schema

### Design Principles

1. **Relational SQL Database**: PostgreSQL recommended for JSON support and advanced queries
2. **Normalized Structure**: Separate tables for concepts, relationships, metadata
3. **Audit Trail**: Every calculation traceable to source facts
4. **Temporal Handling**: Support multi-period analysis
5. **Extensibility**: Easy to add new ratio formulas

### Core Tables

#### Table 1: `companies`

```sql
CREATE TABLE companies (
    company_id SERIAL PRIMARY KEY,
    cik VARCHAR(10) UNIQUE NOT NULL,           -- SEC CIK or equivalent
    company_name VARCHAR(500),
    market VARCHAR(10),                        -- 'sec', 'esef', etc.
    industry_code VARCHAR(20),                 -- SIC, NAICS
    fiscal_year_end_month INT,                 -- 1-12
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_companies_cik ON companies(cik);
```

#### Table 2: `filings`

```sql
CREATE TABLE filings (
    filing_id SERIAL PRIMARY KEY,
    company_id INT REFERENCES companies(company_id),
    
    filing_identifier VARCHAR(200) UNIQUE,     -- e.g., "sec/Albertsons/10_K/2025-10-13"
    form_type VARCHAR(20),                     -- '10-K', '10-Q', etc.
    filing_date DATE,
    fiscal_period_end DATE,
    fiscal_year INT,
    fiscal_period VARCHAR(10),                 -- 'FY', 'Q1', 'Q2', etc.
    
    -- Taxonomy info
    taxonomy_name VARCHAR(100),                -- 'us-gaap-2024', etc.
    taxonomy_version VARCHAR(50),
    
    -- Processing metadata
    parsed_at TIMESTAMP,
    verified_at TIMESTAMP,
    verification_score DECIMAL(5,2),           -- 0-100
    
    -- File references
    parsed_json_path VARCHAR(500),
    verification_report_path VARCHAR(500),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_filings_company ON filings(company_id);
CREATE INDEX idx_filings_date ON filings(filing_date);
CREATE INDEX idx_filings_identifier ON filings(filing_identifier);
```

#### Table 3: `statements`

```sql
CREATE TABLE statements (
    statement_id SERIAL PRIMARY KEY,
    filing_id INT REFERENCES filings(filing_id),
    
    statement_code CHAR(2),                    -- 'BS', 'IS', 'CF', 'EQ', 'OT'
    statement_name VARCHAR(500),               -- Full name from filing
    role_uri VARCHAR(1000),                    -- XBRL role URI
    statement_order INT,                       -- Display order
    
    -- Metadata
    is_consolidated BOOLEAN DEFAULT true,
    is_parenthetical BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_statements_filing ON statements(filing_id);
CREATE INDEX idx_statements_code ON statements(statement_code);
```

#### Table 4: `concepts` (Core Table)

```sql
CREATE TABLE concepts (
    concept_id SERIAL PRIMARY KEY,
    filing_id INT REFERENCES filings(filing_id),
    statement_id INT REFERENCES statements(statement_id),
    
    -- Positional Identifier
    mat_acc_id VARCHAR(50) UNIQUE NOT NULL,    -- e.g., 'BS-002-001-c4'
    
    -- XBRL Source Data
    xbrl_name VARCHAR(500) NOT NULL,           -- e.g., 'us-gaap:AssetsCurrent'
    fact_id VARCHAR(50),                       -- Original fact ID from parser
    context_ref VARCHAR(100),                  -- 'c-4', 'c-13', etc.
    
    -- Hierarchy Position
    hierarchy_level INT,                       -- 0 = root, 1 = child, etc.
    sibling_position INT,                      -- Position among siblings
    parent_concept_id INT REFERENCES concepts(concept_id),
    
    -- Value Data
    value DECIMAL(20,4),                       -- Numeric value
    display_value VARCHAR(100),                -- Formatted display
    unit_ref VARCHAR(50),                      -- 'usd', 'shares', etc.
    decimals VARCHAR(20),
    scaling_factor BIGINT,
    
    -- Temporal Data
    period_type VARCHAR(20),                   -- 'instant', 'duration'
    period_start DATE,
    period_end DATE,
    
    -- Type Information
    is_abstract BOOLEAN DEFAULT false,         -- Non-numeric header
    is_nil BOOLEAN DEFAULT false,
    data_type VARCHAR(50),                     -- 'monetary', 'shares', 'pure'
    balance_type VARCHAR(20),                  -- 'debit', 'credit'
    
    -- Dimensional Data (JSON)
    dimensions JSONB,                          -- Store dimension breakdown
    
    -- Taxonomy Metadata
    taxonomy_label VARCHAR(500),               -- From standard taxonomy
    taxonomy_doc TEXT,
    
    -- Verification Status
    verified BOOLEAN DEFAULT false,
    verification_passed BOOLEAN,
    verification_difference DECIMAL(20,4),
    verification_message TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_concepts_filing ON concepts(filing_id);
CREATE INDEX idx_concepts_mat_acc_id ON concepts(mat_acc_id);
CREATE INDEX idx_concepts_xbrl_name ON concepts(xbrl_name);
CREATE INDEX idx_concepts_context ON concepts(context_ref);
CREATE INDEX idx_concepts_parent ON concepts(parent_concept_id);
CREATE INDEX idx_concepts_statement ON concepts(statement_id);
CREATE INDEX idx_concepts_dimensions ON concepts USING GIN(dimensions);
```

#### Table 5: `calculation_relationships`

```sql
CREATE TABLE calculation_relationships (
    relationship_id SERIAL PRIMARY KEY,
    filing_id INT REFERENCES filings(filing_id),
    
    parent_concept_id INT REFERENCES concepts(concept_id),
    child_concept_id INT REFERENCES concepts(concept_id),
    
    calculation_weight DECIMAL(5,2),           -- Usually 1 or -1
    calculation_order INT,                     -- Order in calculation
    
    -- From linkbase
    arc_role VARCHAR(500),
    linkbase_source VARCHAR(50),               -- 'calculation', 'presentation'
    
    -- Verification
    verified BOOLEAN DEFAULT false,
    expected_contribution DECIMAL(20,4),
    actual_contribution DECIMAL(20,4),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(parent_concept_id, child_concept_id)
);

CREATE INDEX idx_calc_parent ON calculation_relationships(parent_concept_id);
CREATE INDEX idx_calc_child ON calculation_relationships(child_concept_id);
```

#### Table 6: `presentation_relationships`

```sql
CREATE TABLE presentation_relationships (
    relationship_id SERIAL PRIMARY KEY,
    filing_id INT REFERENCES filings(filing_id),
    statement_id INT REFERENCES statements(statement_id),
    
    parent_concept_id INT REFERENCES concepts(concept_id),
    child_concept_id INT REFERENCES concepts(concept_id),
    
    presentation_order INT,
    preferred_label_role VARCHAR(200),         -- How to display
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(parent_concept_id, child_concept_id)
);

CREATE INDEX idx_pres_parent ON presentation_relationships(parent_concept_id);
CREATE INDEX idx_pres_statement ON presentation_relationships(statement_id);
```

#### Table 7: `semantic_mappings`

```sql
CREATE TABLE semantic_mappings (
    mapping_id SERIAL PRIMARY KEY,
    
    -- Source
    xbrl_name VARCHAR(500),
    
    -- Condition Logic
    condition_type VARCHAR(50),                -- 'parent_is', 'statement_is', etc.
    condition_value VARCHAR(500),
    
    -- Result
    semantic_name VARCHAR(200),                -- 'current_assets', 'net_income'
    normalized_label VARCHAR(500),             -- Display name
    category VARCHAR(100),                     -- For grouping in ratios
    subcategory VARCHAR(100),
    
    -- Metadata
    priority INT DEFAULT 100,                  -- Lower = higher priority
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_semantic_xbrl ON semantic_mappings(xbrl_name);
CREATE INDEX idx_semantic_name ON semantic_mappings(semantic_name);
```

#### Table 8: `ratio_definitions`

```sql
CREATE TABLE ratio_definitions (
    ratio_id SERIAL PRIMARY KEY,
    
    ratio_code VARCHAR(50) UNIQUE NOT NULL,    -- 'current_ratio', 'roe', etc.
    ratio_name VARCHAR(200),                   -- Display name
    ratio_category VARCHAR(100),               -- 'liquidity', 'profitability', etc.
    
    -- Formula
    formula_text TEXT,                         -- Human-readable formula
    formula_code TEXT,                         -- Python/SQL executable
    
    -- Input Requirements
    required_inputs JSONB,                     -- List of semantic names needed
    
    -- Validation
    valid_range_min DECIMAL(20,4),
    valid_range_max DECIMAL(20,4),
    industry_specific BOOLEAN DEFAULT false,
    
    -- Metadata
    description TEXT,
    interpretation_guide TEXT,
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ratio_code ON ratio_definitions(ratio_code);
CREATE INDEX idx_ratio_category ON ratio_definitions(ratio_category);
```

#### Table 9: `calculated_ratios`

```sql
CREATE TABLE calculated_ratios (
    calculation_id SERIAL PRIMARY KEY,
    filing_id INT REFERENCES filings(filing_id),
    ratio_id INT REFERENCES ratio_definitions(ratio_id),
    
    -- Result
    ratio_value DECIMAL(20,4),
    
    -- Input Lineage
    input_concepts JSONB,                      -- Array of concept_ids used
    calculation_details JSONB,                 -- Step-by-step breakdown
    
    -- Quality Metrics
    data_completeness DECIMAL(5,2),            -- % of required inputs available
    calculation_verified BOOLEAN,
    confidence_score DECIMAL(5,2),             -- 0-100
    
    -- Flags
    is_outlier BOOLEAN DEFAULT false,
    needs_review BOOLEAN DEFAULT false,
    review_notes TEXT,
    
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_calc_ratios_filing ON calculated_ratios(filing_id);
CREATE INDEX idx_calc_ratios_ratio ON calculated_ratios(ratio_id);
```

---

## Processing Pipeline

### Module 1: Hierarchy Builder

**Purpose:** Extract and build the complete hierarchical structure from XBRL linkbases

**Inputs:**
- Parsed XBRL data (parsed.json)
- Presentation linkbase
- Calculation linkbase

**Process:**

1. **Identify Statement Roots**
   - Parse presentation linkbase to find statement-level roles
   - Map role URIs to statement types (BS, IS, CF, EQ, OT)
   - Create statement records in database

2. **Traverse Presentation Tree**
   - For each statement root, recursively traverse presentation relationships
   - Track hierarchy level (depth) and sibling position
   - Build parent-child relationships
   - Assign `mat_acc_id` to each concept position

3. **Integrate Calculation Relationships**
   - Parse calculation linkbase
   - Match calculation relationships to presentation hierarchy
   - Store calculation weights and order
   - Flag discrepancies between presentation and calculation

4. **Generate Positional IDs**
   - Format: `{STATEMENT_CODE}-{LEVEL:03d}-{SIBLING:03d}-{CONTEXT_REF}`
   - Example: `BS-002-001-c4`
   - Ensure uniqueness within filing

**Output:**
- Populated `statements` table
- Populated `concepts` table (structure only, values come next)
- Populated `calculation_relationships` table
- Populated `presentation_relationships` table

**Implementation Notes:**

```python
class HierarchyBuilder:
    def __init__(self, parsed_data, linkbases):
        self.parsed_data = parsed_data
        self.presentation_linkbase = linkbases['presentation']
        self.calculation_linkbase = linkbases['calculation']
        self.statement_type_map = self._build_statement_map()
    
    def build_hierarchy(self, filing_id):
        """Main execution method"""
        # Step 1: Create statements
        statements = self._create_statements(filing_id)
        
        # Step 2: For each statement, build hierarchy
        for statement in statements:
            root_concepts = self._find_root_concepts(statement.role_uri)
            
            for root in root_concepts:
                self._traverse_and_build(
                    concept=root,
                    statement_id=statement.statement_id,
                    filing_id=filing_id,
                    level=0,
                    sibling_position=0,
                    parent_id=None
                )
        
        # Step 3: Add calculation relationships
        self._add_calculation_relationships(filing_id)
        
        return True
    
    def _traverse_and_build(self, concept, statement_id, filing_id, 
                           level, sibling_position, parent_id):
        """Recursive traversal of presentation tree"""
        # Generate mat_acc_id
        statement_code = self._get_statement_code(statement_id)
        context_ref = self._get_context_ref(concept)
        mat_acc_id = f"{statement_code}-{level:03d}-{sibling_position:03d}-{context_ref}"
        
        # Create concept record
        concept_id = self._create_concept_record(
            mat_acc_id=mat_acc_id,
            xbrl_name=concept['name'],
            statement_id=statement_id,
            filing_id=filing_id,
            level=level,
            sibling_position=sibling_position,
            parent_id=parent_id,
            context_ref=context_ref
        )
        
        # Recursively process children
        children = self._get_presentation_children(concept)
        for idx, child in enumerate(children):
            self._traverse_and_build(
                concept=child,
                statement_id=statement_id,
                filing_id=filing_id,
                level=level + 1,
                sibling_position=idx + 1,
                parent_id=concept_id
            )
```

### Module 2: Database Populator

**Purpose:** Populate the hierarchy with actual fact values and metadata

**Inputs:**
- Hierarchy structure (from Module 1)
- Parsed facts data (from parsed.json)
- Verification results (from verification_report.json)

**Process:**

1. **Match Facts to Hierarchy Positions**
   - For each fact in parsed.json, find corresponding concept record
   - Match on: xbrl_name + context_ref + statement position
   - Update concept record with value data

2. **Add Verification Metadata**
   - For each verification check, find corresponding concept
   - Update `verified`, `verification_passed`, `verification_difference`
   - Store calculation component details

3. **Handle Dimensions**
   - Store dimensional data as JSONB
   - Enable queries by dimension (e.g., all facts for specific segment)

4. **Data Quality Checks**
   - Ensure all non-abstract concepts have values
   - Flag missing critical data
   - Validate data types

**Output:**
- Fully populated `concepts` table with values
- Updated verification status on each concept

**Implementation Notes:**

```python
class DatabasePopulator:
    def __init__(self, db_connection):
        self.db = db_connection
    
    def populate_values(self, filing_id, parsed_facts, verification_report):
        """Populate concept values and verification data"""
        
        # Step 1: Add fact values
        for fact in parsed_facts:
            concept = self._find_concept_by_position(
                filing_id=filing_id,
                xbrl_name=fact['concept'],
                context_ref=fact['context_ref'],
                level=fact['level'],
                order=fact['order']
            )
            
            if concept:
                self._update_concept_values(concept.concept_id, fact)
            else:
                # Log missing concept - shouldn't happen if hierarchy built correctly
                self._log_orphan_fact(fact)
        
        # Step 2: Add verification results
        for check in verification_report['checks']:
            if check['check_type'] == 'calculation_consistency':
                self._update_verification_status(
                    filing_id=filing_id,
                    concept_name=check['concept'],
                    context_id=check['context_id'],
                    passed=check['passed'],
                    difference=check['difference'],
                    details=check['details']
                )
    
    def _update_concept_values(self, concept_id, fact):
        """Update a concept record with fact values"""
        self.db.execute("""
            UPDATE concepts
            SET value = %s,
                display_value = %s,
                unit_ref = %s,
                decimals = %s,
                scaling_factor = %s,
                period_type = %s,
                period_start = %s,
                period_end = %s,
                dimensions = %s,
                is_nil = %s,
                fact_id = %s
            WHERE concept_id = %s
        """, (
            fact['value'],
            fact['display_value'],
            fact['unit_ref'],
            fact['decimals'],
            fact['scaling_factor'],
            fact['period_type'],
            fact['period_start'],
            fact['period_end'],
            json.dumps(fact['dimensions']),
            fact['is_nil'],
            fact['fact_id'],
            concept_id
        ))
```

### Module 3: Taxonomy Enricher

**Purpose:** Add standard taxonomy labels and documentation as metadata

**Inputs:**
- Populated concepts table
- Taxonomy libraries (via existing taxonomy manager)

**Process:**

1. **For Each Concept**
   - Look up concept in standard taxonomy
   - Extract: label, terse label, documentation
   - Extract: balance type, period type, data type

2. **Handle Extensions**
   - Company extensions won't be in standard taxonomy
   - Use company-provided labels
   - Note base taxonomy references if available

3. **Store as Metadata**
   - DO NOT override company structure
   - Labels are informational only
   - Used for human readability, not calculations

**Output:**
- Updated `concepts` table with taxonomy metadata

**Implementation Notes:**

```python
class TaxonomyEnricher:
    def __init__(self, taxonomy_manager, db_connection):
        self.taxonomy = taxonomy_manager  # Your existing system
        self.db = db_connection
    
    def enrich_concepts(self, filing_id):
        """Add taxonomy metadata to all concepts"""
        
        # Get taxonomy info for this filing
        filing = self.db.get_filing(filing_id)
        taxonomy_lib = self.taxonomy.load_taxonomy(filing.taxonomy_name)
        
        # Process each concept
        concepts = self.db.get_concepts_for_filing(filing_id)
        
        for concept in concepts:
            taxonomy_data = taxonomy_lib.get_concept(concept.xbrl_name)
            
            if taxonomy_data:
                # Standard taxonomy concept
                self.db.execute("""
                    UPDATE concepts
                    SET taxonomy_label = %s,
                        taxonomy_doc = %s,
                        balance_type = %s,
                        data_type = %s
                    WHERE concept_id = %s
                """, (
                    taxonomy_data.get('terseLabel') or taxonomy_data.get('label'),
                    taxonomy_data.get('documentation'),
                    taxonomy_data.get('balance'),
                    taxonomy_data.get('type'),
                    concept.concept_id
                ))
            else:
                # Extension concept - use company label or generate from name
                readable_label = self._generate_label_from_name(concept.xbrl_name)
                self.db.execute("""
                    UPDATE concepts
                    SET taxonomy_label = %s
                    WHERE concept_id = %s
                """, (readable_label, concept.concept_id))
    
    def _generate_label_from_name(self, xbrl_name):
        """Convert extension name to readable label"""
        # Remove namespace prefix
        name = xbrl_name.split(':')[-1]
        # Split on camel case
        words = self._split_camel_case(name)
        return ' '.join(words)
```

### Module 4: Role Mapper

**Purpose:** Apply contextual mapping rules to generate semantic names for ratio calculations

**Inputs:**
- Populated concepts with taxonomy metadata
- Semantic mapping rules (from `semantic_mappings` table)

**Process:**

1. **Load Mapping Rules**
   - Rules define: IF conditions THEN semantic_name
   - Conditions: parent_is, statement_is, has_sibling, etc.
   - Priority-ordered rule evaluation

2. **Apply Rules to Concepts**
   - For each concept, evaluate applicable rules
   - First matching rule wins (by priority)
   - Fallback to taxonomy label if no rule matches

3. **Generate Semantic Index**
   - Create mapping: semantic_name → [concept_ids]
   - One semantic name may map to multiple concepts (across companies/periods)
   - Store in database or in-memory cache

**Output:**
- Updated `concepts` table with semantic names
- Semantic index for ratio calculations

**Implementation Notes:**

```python
class RoleMapper:
    def __init__(self, db_connection):
        self.db = db_connection
        self.rules = self._load_mapping_rules()
    
    def apply_semantic_mapping(self, filing_id):
        """Apply mapping rules to all concepts"""
        concepts = self.db.get_concepts_for_filing(filing_id)
        
        for concept in concepts:
            # Skip abstract concepts
            if concept.is_abstract:
                continue
            
            # Find applicable rules for this XBRL name
            applicable_rules = [r for r in self.rules 
                               if r['xbrl_name'] == concept.xbrl_name]
            
            # Sort by priority
            applicable_rules.sort(key=lambda r: r['priority'])
            
            # Evaluate rules
            for rule in applicable_rules:
                if self._evaluate_condition(rule, concept):
                    # Rule matches - apply mapping
                    self.db.execute("""
                        UPDATE concepts
                        SET semantic_name = %s,
                            normalized_label = %s,
                            category = %s,
                            subcategory = %s
                        WHERE concept_id = %s
                    """, (
                        rule['semantic_name'],
                        rule['normalized_label'],
                        rule['category'],
                        rule['subcategory'],
                        concept.concept_id
                    ))
                    break  # First match wins
            else:
                # No rule matched - use taxonomy label as fallback
                self._apply_default_mapping(concept)
    
    def _evaluate_condition(self, rule, concept):
        """Evaluate if rule condition matches concept"""
        if rule['condition_type'] == 'parent_is':
            parent = self.db.get_parent_concept(concept.concept_id)
            return parent and parent.xbrl_name == rule['condition_value']
        
        elif rule['condition_type'] == 'statement_is':
            statement = self.db.get_statement(concept.statement_id)
            return statement.statement_code == rule['condition_value']
        
        elif rule['condition_type'] == 'always':
            return True
        
        # Add more condition types as needed
        return False
```

**Example Mapping Rules:**

```sql
-- Rule 1: Current Assets on Balance Sheet
INSERT INTO semantic_mappings (
    xbrl_name, 
    condition_type, 
    condition_value,
    semantic_name,
    normalized_label,
    category,
    subcategory,
    priority
) VALUES (
    'us-gaap:AssetsCurrent',
    'statement_is',
    'BS',
    'current_assets',
    'Current Assets',
    'Balance Sheet',
    'Assets',
    10
);

-- Rule 2: Revenue (multiple XBRL names map to same semantic)
INSERT INTO semantic_mappings (
    xbrl_name,
    condition_type,
    condition_value,
    semantic_name,
    normalized_label,
    category,
    subcategory,
    priority
) VALUES 
    ('us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax', 'always', NULL, 'total_revenue', 'Total Revenue', 'Income Statement', 'Revenue', 10),
    ('us-gaap:Revenues', 'always', NULL, 'total_revenue', 'Total Revenue', 'Income Statement', 'Revenue', 20),
    ('us-gaap:SalesRevenueNet', 'always', NULL, 'total_revenue', 'Total Revenue', 'Income Statement', 'Revenue', 30);

-- Rule 3: Context-dependent mapping
INSERT INTO semantic_mappings (
    xbrl_name,
    condition_type,
    condition_value,
    semantic_name,
    normalized_label,
    category,
    subcategory,
    priority
) VALUES (
    'us-gaap:OtherAssets',
    'parent_is',
    'us-gaap:AssetsCurrent',
    'other_current_assets',
    'Other Current Assets',
    'Balance Sheet',
    'Current Assets',
    10
);

INSERT INTO semantic_mappings (
    xbrl_name,
    condition_type,
    condition_value,
    semantic_name,
    normalized_label,
    category,
    subcategory,
    priority
) VALUES (
    'us-gaap:OtherAssets',
    'parent_is',
    'us-gaap:AssetsNoncurrent',
    'other_noncurrent_assets',
    'Other Noncurrent Assets',
    'Balance Sheet',
    'Noncurrent Assets',
    10
);
```

### Module 5: Financial Data Accessor

**Purpose:** Provide semantic query interface for ratio calculations

**Inputs:**
- Database with semantically mapped concepts

**Process:**

1. **Semantic Query Interface**
   - Accept queries like: "get current_assets for company X, period Y"
   - Abstract away structural differences between companies
   - Handle missing data gracefully

2. **Multi-Candidate Resolution**
   - One semantic name may map to multiple XBRL concepts
   - Try each candidate until value found
   - Document which concept was actually used

3. **Data Quality Reporting**
   - Return not just value, but metadata (verification status, confidence)
   - Flag when using fallback/approximation

**Output:**
- Clean API for ratio calculations
- Data lineage for each retrieved value

**Implementation Notes:**

```python
class FinancialDataAccessor:
    def __init__(self, db_connection):
        self.db = db_connection
    
    def get_value(self, semantic_name, filing_id, period_end=None, 
                  require_verified=True):
        """
        Retrieve value by semantic name
        
        Returns: {
            'value': decimal,
            'concept_id': int,
            'xbrl_name': str,
            'verified': bool,
            'confidence': float,
            'period_end': date
        }
        """
        # Build query
        query = """
            SELECT c.concept_id, c.xbrl_name, c.value, c.verified,
                   c.verification_passed, c.period_end, c.mat_acc_id
            FROM concepts c
            WHERE c.filing_id = %s
                AND c.semantic_name = %s
                AND c.is_nil = false
        """
        params = [filing_id, semantic_name]
        
        # Add period filter if specified
        if period_end:
            query += " AND c.period_end = %s"
            params.append(period_end)
        
        # Add verification requirement
        if require_verified:
            query += " AND c.verification_passed = true"
        
        # Execute query
        results = self.db.execute(query, params)
        
        if not results:
            # No data found - try fallback strategies
            return self._try_fallback_strategies(semantic_name, filing_id, period_end)
        
        # Multiple results - need disambiguation
        if len(results) > 1:
            result = self._disambiguate_results(results, semantic_name)
        else:
            result = results[0]
        
        return {
            'value': result['value'],
            'concept_id': result['concept_id'],
            'xbrl_name': result['xbrl_name'],
            'verified': result['verification_passed'],
            'confidence': self._calculate_confidence(result),
            'period_end': result['period_end'],
            'mat_acc_id': result['mat_acc_id']
        }
    
    def _try_fallback_strategies(self, semantic_name, filing_id, period_end):
        """Attempt alternative approaches when primary lookup fails"""
        
        # Strategy 1: Try alternative semantic names
        alternatives = self._get_semantic_alternatives(semantic_name)
        for alt_name in alternatives:
            try:
                return self.get_value(alt_name, filing_id, period_end, 
                                     require_verified=False)
            except DataNotAvailableError:
                continue
        
        # Strategy 2: Calculate from components
        if self._can_calculate_from_components(semantic_name):
            return self._calculate_from_components(semantic_name, filing_id, period_end)
        
        # All strategies failed
        raise DataNotAvailableError(
            f"No data available for {semantic_name} in filing {filing_id}"
        )
    
    def _disambiguate_results(self, results, semantic_name):
        """Choose best result when multiple candidates exist"""
        # Prefer verified over unverified
        verified = [r for r in results if r['verification_passed']]
        if verified:
            results = verified
        
        # If still multiple, prefer most recent period
        if len(results) > 1:
            results.sort(key=lambda r: r['period_end'], reverse=True)
        
        return results[0]
    
    def _calculate_confidence(self, result):
        """Calculate confidence score for returned value"""
        confidence = 100.0
        
        # Reduce confidence if not verified
        if not result['verification_passed']:
            confidence -= 30.0
        
        # Could add more factors
        
        return confidence
```

### Module 6: Ratio Calculation Engine

**Purpose:** Execute multi-level ratio formulas and produce comprehensive financial analysis

**mat_acc's Core Mission:**
mat_acc is a **numerical financial analyzer** (Mathematical Accountancy), NOT primarily a verification tool. While it validates its own calculations, the main focus is comprehensive financial analysis across 4 calculation levels.

**4-Level Calculation Hierarchy:**

#### Level 1: Basic Aggregation Checks (Foundation)
**Source:** Company XBRL filing calculation linkbases  
**Already Done By:** Verification engine  
**mat_acc Use:** Include in final report as "basics" (not for checking, but for completeness)

**Examples:**
- Total Assets = Current Assets + Noncurrent Assets
- Total Liabilities = Current Liabilities + Noncurrent Liabilities
- Stockholders' Equity = Total Assets - Total Liabilities

**mat_acc Implementation:**
```python
# Include Level 1 from verification report
level_1_results = {
    'total_assets': verification_report.get_check('us-gaap:Assets'),
    'total_liabilities': verification_report.get_check('us-gaap:Liabilities'),
    'stockholders_equity': verification_report.get_check('us-gaap:StockholdersEquity')
}
```

#### Level 2: Standard Financial Ratios (Core Analysis)
**Source:** Hardcoded formulas - universally accepted by accounting standards  
**Formula Count:** 20-30 core ratios  
**Validation:** Must be approved by financial textbooks and authoritative sources

**Examples:**
- Current Ratio = Current Assets / Current Liabilities
- ROE = Net Income / Average Stockholders' Equity
- Debt-to-Equity = Total Liabilities / Stockholders' Equity
- Gross Profit Margin = (Revenue - COGS) / Revenue

**Formula Requirements:**
- Must have universal acceptance across:
  - Academic textbooks (Accounting, Corporate Finance)
  - CFA Institute standards
  - Industry practice
- No controversial interpretations
- Clear, unambiguous calculations

**Implementation:**
```python
# Level 2 ratios are stored in ratio_definitions table
# with formula_source = 'STANDARD' and is_approved = true
```

#### Level 3: Detailed Component Analysis (Deep Dive)
**Source:** Hardcoded formulas - specialized and detailed ratios  
**Formula Count:** 50-100+ ratios  
**Purpose:** Reveal fine details and component relationships

**Examples:**
- Expense Component Ratios:
  - R&D / Total Operating Expenses
  - SG&A / Revenue
  - Marketing Expense / Revenue
  - Administrative Costs / Total Expenses
  
- Investment Breakdown Ratios:
  - Short-term Investments / Total Investments
  - Equity Investments / Total Investments
  - Real Estate Holdings / Total Assets
  
- Detailed Liquidity Metrics:
  - Cash / Current Assets
  - Receivables / Current Assets
  - Inventory Quality Metrics

- Operational Efficiency:
  - Revenue per Employee (if employee count available)
  - Asset Utilization by Category
  - Working Capital Components Analysis

**Challenge:** These facts may NOT be verified by verification engine

**Solution:** Use all available facts from verified company; mark confidence accordingly

**Implementation:**
```python
# Level 3 ratios with formula_source = 'DETAILED'
# May require more sophisticated fact discovery:

def calculate_expense_breakdown(filing_id):
    # Find all expense categories
    expense_facts = find_concepts_by_pattern(
        filing_id=filing_id,
        pattern='*Expense*',
        statement_type='IS'
    )
    
    # Calculate ratios between expense components
    total_expenses = get_value('operating_expenses', filing_id)
    
    breakdown = {}
    for expense in expense_facts:
        breakdown[expense.semantic_name] = {
            'value': expense.value,
            'ratio_to_total': expense.value / total_expenses,
            'verified': expense.verified
        }
    
    return breakdown
```

#### Level 4: Industry-Specific Contextual Analysis (Advanced)
**Source:** Hardcoded formulas WITH industry classification rules  
**Formula Count:** 100-500+ (depends on industry coverage)  
**Purpose:** Interpret facts in industry context

**Key Principle:** Same fact, different meaning by industry

**Examples:**

**Example 1: Capital Expenditure Interpretation**
```python
capex = get_value('capital_expenditure', filing_id)
industry = get_company_industry(filing_id)

if industry == 'Technology':
    interpretation = 'equipment_expense'  # Likely maintenance/replacement
    quality_score = 'neutral_to_negative'
    
elif industry == 'Transportation':
    interpretation = 'fleet_expansion'  # Growth signal
    quality_score = 'positive'
    
elif industry == 'Manufacturing':
    interpretation = 'capacity_investment'
    quality_score = 'positive_if_revenue_growing'
```

**Example 2: Inventory Analysis**
```python
inventory_ratio = inventory / current_assets

if industry == 'Retail':
    optimal_range = (0.30, 0.50)  # 30-50% is normal
    
elif industry == 'Services':
    optimal_range = (0.0, 0.10)  # Should be minimal
    
elif industry == 'Manufacturing':
    optimal_range = (0.25, 0.45)  # Raw materials + finished goods
```

**Implementation Approach:**

1. **Industry Classification System:**
```sql
CREATE TABLE industry_classifications (
    classification_id SERIAL PRIMARY KEY,
    classification_system VARCHAR(20),  -- 'SIC', 'NAICS', 'GICS'
    code VARCHAR(20),
    industry_name VARCHAR(200),
    industry_group VARCHAR(100),
    mat_acc_category VARCHAR(50)  -- Simplified grouping for analysis
);

CREATE TABLE company_industries (
    company_id INT REFERENCES companies(company_id),
    classification_id INT REFERENCES industry_classifications(classification_id),
    is_primary BOOLEAN DEFAULT true
);
```

2. **Industry-Specific Ratio Rules:**
```sql
CREATE TABLE industry_ratio_rules (
    rule_id SERIAL PRIMARY KEY,
    ratio_id INT REFERENCES ratio_definitions(ratio_id),
    industry_category VARCHAR(50),  -- From mat_acc_category
    
    -- Industry-specific interpretation
    optimal_range_min DECIMAL(20,4),
    optimal_range_max DECIMAL(20,4),
    interpretation_positive TEXT,
    interpretation_negative TEXT,
    
    -- Context rules
    context_conditions JSONB,  -- Additional factors to consider
    
    is_active BOOLEAN DEFAULT true
);
```

3. **Formula Selection Engine:**
```python
class IndustryAwareCalculator:
    def select_applicable_ratios(self, filing_id):
        """Select ratios based on company industry and data availability"""
        
        company = self.db.get_company_for_filing(filing_id)
        industry = company.primary_industry_category
        
        # Level 1: Always include (from verification)
        selected = self.get_level_1_checks()
        
        # Level 2: Always include (universal ratios)
        selected += self.get_level_2_ratios()
        
        # Level 3: Filter by data availability
        level_3 = self.get_level_3_ratios()
        for ratio in level_3:
            if self.has_required_data(ratio, filing_id):
                selected.append(ratio)
        
        # Level 4: Filter by industry relevance + data availability
        level_4 = self.get_level_4_ratios(industry_filter=industry)
        for ratio in level_4:
            if self.has_required_data(ratio, filing_id):
                if self.is_relevant_for_industry(ratio, industry):
                    selected.append(ratio)
        
        return selected
    
    def interpret_ratio(self, ratio_value, ratio_def, industry):
        """Provide industry-specific interpretation"""
        
        # Get industry-specific rules
        industry_rule = self.db.get_industry_rule(
            ratio_id=ratio_def.ratio_id,
            industry=industry
        )
        
        if industry_rule:
            # Industry-specific interpretation
            if industry_rule.optimal_range_min <= ratio_value <= industry_rule.optimal_range_max:
                return industry_rule.interpretation_positive
            else:
                return industry_rule.interpretation_negative
        else:
            # Generic interpretation
            return ratio_def.interpretation_guide
```

**Formula Sources & Validation:**

**Level 2 Sources (Must Have):**
- CFA Institute Standards
- US GAAP Framework
- Academic textbooks (Brigham, Ross-Westerfield-Jaffe)
- Industry standards (Robert Morris Associates)

**Level 3 Sources:**
- Industry analyst reports
- Financial statement analysis guides
- Specialized accounting texts

**Level 4 Sources:**
- Industry-specific benchmarking data
- Sector analysis frameworks
- Regulatory guidelines (industry-dependent)
- Academic research on industry-specific metrics

**Inputs:**
- Ratio definitions (from `ratio_definitions` table)
- Industry-specific rules (from `industry_ratio_rules` table)
- Financial Data Accessor (Module 5)
- Company industry classification
- Verification results (for Level 1 inclusion)

**Process:**

1. **Load Ratio Definitions**
   - All active ratios from database
   - Parse formula requirements

2. **For Each Ratio**
   - Check if required inputs available
   - Retrieve input values via Data Accessor
   - Execute calculation
   - Validate result (range checks, sanity tests)
   - Cross-validate if alternative calculation exists

3. **Store Results**
   - Save calculated ratio
   - Store input lineage (which concepts used)
   - Record calculation details for audit

4. **Quality Scoring**
   - Data completeness (% of inputs available)
   - Verification status of inputs
   - Outlier detection
   - Confidence score

**Output:**
- Populated `calculated_ratios` table
- Calculation audit trail

**Implementation Notes:**

```python
class RatioCalculator:
    def __init__(self, data_accessor, db_connection):
        self.data = data_accessor
        self.db = db_connection
        self.ratio_defs = self._load_ratio_definitions()
    
    def calculate_all_ratios(self, filing_id):
        """Calculate all applicable ratios for a filing"""
        results = []
        
        for ratio_def in self.ratio_defs:
            try:
                result = self.calculate_ratio(ratio_def, filing_id)
                results.append(result)
                self._save_result(result, filing_id, ratio_def['ratio_id'])
            
            except DataNotAvailableError as e:
                # Log missing data, continue
                self._log_missing_data(ratio_def, filing_id, str(e))
            
            except Exception as e:
                # Log unexpected error
                self._log_error(ratio_def, filing_id, str(e))
        
        return results
    
    def calculate_ratio(self, ratio_def, filing_id):
        """Calculate a single ratio"""
        
        # Step 1: Gather inputs
        inputs = {}
        input_concepts = {}
        
        for input_name in ratio_def['required_inputs']:
            data = self.data.get_value(input_name, filing_id)
            inputs[input_name] = data['value']
            input_concepts[input_name] = data['concept_id']
        
        # Step 2: Execute formula
        ratio_value = self._execute_formula(ratio_def['formula_code'], inputs)
        
        # Step 3: Validate result
        validation = self._validate_result(ratio_value, ratio_def)
        
        # Step 4: Cross-validate if possible
        cross_check = self._cross_validate(ratio_def, inputs, ratio_value)
        
        # Step 5: Calculate quality metrics
        data_completeness = self._calculate_data_completeness(inputs, ratio_def)
        confidence = self._calculate_confidence_score(
            inputs, validation, cross_check, data_completeness
        )
        
        return {
            'ratio_code': ratio_def['ratio_code'],
            'value': ratio_value,
            'inputs': inputs,
            'input_concepts': input_concepts,
            'validation': validation,
            'cross_check': cross_check,
            'data_completeness': data_completeness,
            'confidence': confidence,
            'calculation_details': {
                'formula': ratio_def['formula_text'],
                'inputs_used': inputs,
                'result': ratio_value
            }
        }
    
    def _execute_formula(self, formula_code, inputs):
        """Safely execute ratio formula"""
        # Create safe execution context
        context = inputs.copy()
        
        # Execute formula (Python eval with restricted globals)
        # In production, use safer alternatives like simpleeval
        try:
            result = eval(formula_code, {"__builtins__": {}}, context)
            return result
        except ZeroDivisionError:
            return None
        except Exception as e:
            raise CalculationError(f"Formula execution failed: {e}")
    
    def _validate_result(self, value, ratio_def):
        """Validate ratio value against expected ranges"""
        if value is None:
            return {'valid': False, 'reason': 'Calculation returned None'}
        
        # Check defined ranges
        if ratio_def['valid_range_min'] is not None:
            if value < ratio_def['valid_range_min']:
                return {
                    'valid': False,
                    'reason': f'Below minimum ({ratio_def["valid_range_min"]})',
                    'is_outlier': True
                }
        
        if ratio_def['valid_range_max'] is not None:
            if value > ratio_def['valid_range_max']:
                return {
                    'valid': False,
                    'reason': f'Above maximum ({ratio_def["valid_range_max"]})',
                    'is_outlier': True
                }
        
        return {'valid': True, 'reason': None, 'is_outlier': False}
    
    def _cross_validate(self, ratio_def, inputs, calculated_value):
        """Cross-check calculation using alternative method if available"""
        # Example: ROE can be calculated as Net Income / Equity
        # OR as ROA × Asset Multiplier
        
        # This would be ratio-specific logic
        # Return None if no cross-check available
        return None
```

**Example Ratio Definitions:**

```sql
-- Current Ratio
INSERT INTO ratio_definitions (
    ratio_code,
    ratio_name,
    ratio_category,
    formula_text,
    formula_code,
    required_inputs,
    valid_range_min,
    valid_range_max,
    description,
    interpretation_guide
) VALUES (
    'current_ratio',
    'Current Ratio',
    'Liquidity',
    'Current Assets / Current Liabilities',
    'current_assets / current_liabilities',
    '["current_assets", "current_liabilities"]',
    0.0,
    10.0,
    'Measures ability to pay short-term obligations',
    'Generally, >1.0 indicates sufficient liquidity. Very high ratios (>3.0) may indicate inefficient use of assets.'
);

-- Return on Equity
INSERT INTO ratio_definitions (
    ratio_code,
    ratio_name,
    ratio_category,
    formula_text,
    formula_code,
    required_inputs,
    valid_range_min,
    valid_range_max,
    description
) VALUES (
    'roe',
    'Return on Equity',
    'Profitability',
    'Net Income / Average Stockholders Equity',
    'net_income / ((stockholders_equity_current + stockholders_equity_prior) / 2)',
    '["net_income", "stockholders_equity_current", "stockholders_equity_prior"]',
    -1.0,
    1.0,
    'Measures profitability relative to shareholder equity'
);

-- Debt to Equity
INSERT INTO ratio_definitions (
    ratio_code,
    ratio_name,
    ratio_category,
    formula_text,
    formula_code,
    required_inputs,
    valid_range_min,
    valid_range_max,
    description
) VALUES (
    'debt_to_equity',
    'Debt-to-Equity Ratio',
    'Leverage',
    'Total Liabilities / Stockholders Equity',
    'total_liabilities / stockholders_equity',
    '["total_liabilities", "stockholders_equity"]',
    0.0,
    10.0,
    'Measures financial leverage and capital structure'
);
```

---

## Output Specifications

### Output 1: Normalized Statements

**Format:** JSON or structured database export

**Content:**
- Hierarchical financial statements with standardized names
- Full calculation tree showing parent-child relationships
- Verification status for each line item

**Example Structure:**
```json
{
  "filing_id": "sec/Albertsons/10_K/2025-10-13",
  "company": "Albertsons Companies Inc",
  "period_end": "2025-02-22",
  "statements": {
    "balance_sheet": {
      "statement_code": "BS",
      "line_items": [
        {
          "mat_acc_id": "BS-001-001-c4",
          "semantic_name": "current_assets",
          "label": "Current Assets",
          "value": 5432.1,
          "verified": true,
          "children": [
            {
              "mat_acc_id": "BS-002-001-c4",
              "semantic_name": "cash_and_equivalents",
              "label": "Cash and Cash Equivalents",
              "value": 345.6,
              "verified": true
            }
          ]
        }
      ]
    }
  }
}
```

### Output 2: Ratio Analysis Report

**Format:** JSON, HTML, or PDF

**Content:**
- All calculated ratios grouped by category
- Input values and calculation details
- Confidence scores and data quality metrics
- Interpretation guides
- Trend analysis (if multi-period)
- Peer comparison (if benchmark data available)

**Example Structure:**
```json
{
  "filing_id": "sec/Albertsons/10_K/2025-10-13",
  "company": "Albertsons Companies Inc",
  "period_end": "2025-02-22",
  "analysis_date": "2026-02-03",
  
  "data_quality": {
    "verification_score": 100.0,
    "data_completeness": 95.2,
    "critical_issues": 0,
    "warnings": 0
  },
  
  "ratios": {
    "liquidity": {
      "current_ratio": {
        "value": 1.82,
        "confidence": 100.0,
        "components": {
          "current_assets": 5432.1,
          "current_liabilities": 2984.7
        },
        "verified": true,
        "interpretation": "Strong liquidity position. Company can cover short-term obligations 1.82 times.",
        "industry_benchmark": {
          "median": 1.5,
          "quartile": "upper"
        }
      },
      "quick_ratio": {
        "value": 0.87,
        "confidence": 100.0,
        "components": {
          "current_assets": 5432.1,
          "inventory": 2734.2,
          "current_liabilities": 2984.7
        },
        "verified": true
      }
    },
    "profitability": {
      "roe": {
        "value": 0.145,
        "confidence": 95.0,
        "components": {
          "net_income": 567.8,
          "stockholders_equity_current": 3912.4,
          "stockholders_equity_prior": 3911.6
        },
        "verified": true,
        "interpretation": "14.5% return on equity indicates moderate profitability."
      }
    },
    "leverage": {
      "debt_to_equity": {
        "value": 2.34,
        "confidence": 100.0,
        "components": {
          "total_liabilities": 9156.2,
          "stockholders_equity": 3912.4
        },
        "verified": true,
        "interpretation": "High leverage ratio. Company uses $2.34 of debt for every $1 of equity."
      }
    }
  },
  
  "calculation_audit_trail": [
    {
      "ratio": "current_ratio",
      "formula": "current_assets / current_liabilities",
      "input_lineage": {
        "current_assets": {
          "mat_acc_id": "BS-001-001-c4",
          "xbrl_name": "us-gaap:AssetsCurrent",
          "value": 5432.1,
          "verified": true,
          "verification_check_id": 42
        },
        "current_liabilities": {
          "mat_acc_id": "BS-001-015-c4",
          "xbrl_name": "us-gaap:LiabilitiesCurrent",
          "value": 2984.7,
          "verified": true,
          "verification_check_id": 67
        }
      },
      "calculation_steps": [
        "Retrieve current_assets: 5432.1",
        "Retrieve current_liabilities: 2984.7",
        "Calculate: 5432.1 / 2984.7 = 1.82"
      ],
      "result": 1.82
    }
  ]
}
```

### Output 3: Human-Readable Report (HTML/PDF)

**Content:**
- Executive summary
- Company overview
- Financial statements (normalized, readable format)
- Ratio analysis with charts/graphs
- Interpretation and insights
- Data quality disclaimer

**Template Structure:**

```html
<!DOCTYPE html>
<html>
<head>
    <title>Financial Analysis Report - {Company Name}</title>
    <style>
        /* Professional styling */
    </style>
</head>
<body>
    <header>
        <h1>Financial Analysis Report</h1>
        <h2>{Company Name}</h2>
        <p>Period Ending: {Period End}</p>
        <p>Report Generated: {Date}</p>
    </header>
    
    <section class="executive-summary">
        <h2>Executive Summary</h2>
        <div class="key-metrics">
            <div class="metric">
                <h3>Liquidity</h3>
                <p>Current Ratio: {value}</p>
                <p class="interpretation">{interpretation}</p>
            </div>
            <!-- More metrics -->
        </div>
    </section>
    
    <section class="financial-statements">
        <h2>Consolidated Balance Sheet</h2>
        <table>
            <thead>
                <tr>
                    <th>Line Item</th>
                    <th>Amount (in millions)</th>
                    <th>Verified</th>
                </tr>
            </thead>
            <tbody>
                <!-- Statement lines -->
            </tbody>
        </table>
    </section>
    
    <section class="ratio-analysis">
        <h2>Ratio Analysis</h2>
        
        <div class="ratio-category">
            <h3>Liquidity Ratios</h3>
            <div class="ratio">
                <h4>Current Ratio: {value}</h4>
                <p>Formula: Current Assets / Current Liabilities</p>
                <p>Calculation: {current_assets} / {current_liabilities} = {result}</p>
                <div class="chart">
                    <!-- Visualization -->
                </div>
                <p class="interpretation">{interpretation}</p>
            </div>
        </div>
        
        <!-- More categories -->
    </section>
    
    <section class="data-quality">
        <h2>Data Quality Statement</h2>
        <p>Verification Score: {score}%</p>
        <p>Data Completeness: {completeness}%</p>
        <p>Critical Issues: {critical_count}</p>
    </section>
    
    <footer>
        <p>Generated by mat_acc v1.0</p>
        <p>This report is based on XBRL filings and automated analysis.</p>
    </footer>
</body>
</html>
```

### Output 4: Graphical Representation Data (CSV/Excel)

**Purpose:** Provide data in formats optimized for visualization software and further analysis

**Formats:**
- **CSV:** Simple, widely compatible
- **Excel (.xlsx):** Multi-sheet, formatted, with formulas
- **JSON (structured for viz):** For programmatic chart generation

**Design Principle:**  
Future graphical representation software should easily detect, transfer, and use mat_acc output to generate tables, graphs, and dashboards.

**CSV Output Structure:**

**File 1: `ratio_results.csv`**
```csv
Category,Ratio Name,Ratio Code,Value,Confidence,Level,Components,Interpretation
Liquidity,Current Ratio,current_ratio,1.82,100,2,"CA:5432.1|CL:2984.7",Strong liquidity
Liquidity,Quick Ratio,quick_ratio,0.87,100,2,"CA:5432.1|INV:2734.2|CL:2984.7",Adequate
Profitability,ROE,roe,0.145,95,2,"NI:567.8|EQ_AVG:3912.0",Moderate profitability
Leverage,Debt-to-Equity,debt_to_equity,2.34,100,2,"TL:9156.2|EQ:3912.4",High leverage
```

**File 2: `statement_summary.csv`**
```csv
Statement,Line Item,Semantic Name,Value,Unit,Verified,Period End
Balance Sheet,Current Assets,current_assets,5432.1,USD millions,true,2025-02-22
Balance Sheet,Cash and Equivalents,cash_and_equivalents,345.6,USD millions,true,2025-02-22
Balance Sheet,Current Liabilities,current_liabilities,2984.7,USD millions,true,2025-02-22
Income Statement,Total Revenue,total_revenue,78234.5,USD millions,true,2025-02-22
Income Statement,Net Income,net_income,567.8,USD millions,true,2025-02-22
```

**File 3: `time_series.csv`** (for multi-period analysis)
```csv
Metric,2023-Q1,2023-Q2,2023-Q3,2023-Q4,2024-Q1,2024-Q2,2024-Q3,2024-Q4
Current Ratio,1.65,1.72,1.68,1.75,1.78,1.80,1.82,1.82
ROE,0.132,0.138,0.141,0.142,0.143,0.144,0.145,0.145
Debt-to-Equity,2.45,2.42,2.38,2.36,2.35,2.34,2.34,2.34
```

**Excel Output Structure:**

**Multi-sheet workbook: `financial_analysis.xlsx`**

**Sheet 1: "Summary"**
- Company overview
- Key metrics dashboard
- Data quality indicators
- Period information

**Sheet 2: "Balance Sheet"**
- Hierarchical statement with indentation
- All line items with values
- Verification status column
- Calculation formulas in Excel

**Sheet 3: "Income Statement"**
- Similar structure to Balance Sheet

**Sheet 4: "Cash Flow"**
- Similar structure

**Sheet 5: "Ratios - Level 1"**
- Basic aggregation checks
- From verification engine

**Sheet 6: "Ratios - Level 2"**
- Standard financial ratios
- With formulas pointing to statement sheets

**Sheet 7: "Ratios - Level 3"**
- Detailed component analysis

**Sheet 8: "Ratios - Level 4"**
- Industry-specific analysis
- Contextual interpretations

**Sheet 9: "Visualizations"**
- Pre-built charts and graphs
- Trend lines (if multi-period)
- Comparison charts

**Sheet 10: "Data Lineage"**
- Audit trail
- Concept mappings
- Verification details

**JSON for Visualization (structured)**

```json
{
  "metadata": {
    "company": "Albertsons Companies Inc",
    "period_end": "2025-02-22",
    "currency": "USD",
    "unit": "millions"
  },
  
  "visualization_ready": {
    "categories": [
      {
        "category": "Liquidity",
        "ratios": [
          {
            "name": "Current Ratio",
            "value": 1.82,
            "benchmark": 1.5,
            "status": "above_benchmark",
            "trend": [1.65, 1.72, 1.78, 1.82],
            "chart_type": "bar_with_benchmark"
          }
        ]
      }
    ],
    
    "statements": {
      "balance_sheet": {
        "chart_type": "waterfall",
        "sections": [
          {
            "section": "Current Assets",
            "total": 5432.1,
            "components": [
              {"label": "Cash", "value": 345.6},
              {"label": "Receivables", "value": 1234.5},
              {"label": "Inventory", "value": 2734.2}
            ]
          }
        ]
      }
    },
    
    "trends": {
      "chart_type": "line",
      "metrics": [
        {
          "metric": "Current Ratio",
          "data": [
            {"period": "2023-Q1", "value": 1.65},
            {"period": "2023-Q2", "value": 1.72},
            {"period": "2024-Q1", "value": 1.78},
            {"period": "2024-Q2", "value": 1.82}
          ]
        }
      ]
    },
    
    "component_breakdowns": {
      "chart_type": "pie",
      "datasets": [
        {
          "title": "Current Assets Composition",
          "total": 5432.1,
          "slices": [
            {"label": "Cash", "value": 345.6, "percentage": 6.4},
            {"label": "Receivables", "value": 1234.5, "percentage": 22.7},
            {"label": "Inventory", "value": 2734.2, "percentage": 50.3}
          ]
        }
      ]
    }
  }
}
```

**Visualization Guidance Metadata:**

Each output file should include metadata suggesting appropriate visualizations:

```json
{
  "visualization_hints": {
    "ratios": {
      "current_ratio": {
        "suggested_charts": ["bar", "gauge"],
        "benchmark_line": 1.5,
        "healthy_range": [1.5, 3.0]
      },
      "roe": {
        "suggested_charts": ["line_trend", "comparison_bar"],
        "industry_benchmark": 0.12,
        "format": "percentage"
      }
    },
    "statements": {
      "balance_sheet": {
        "suggested_charts": ["waterfall", "stacked_bar"],
        "hierarchical": true
      }
    }
  }
}
```

**Report Generation Technology:**

**For CSV/Excel:**
- Python `pandas`: DataFrame manipulation
- `openpyxl`: Excel file generation with formatting
- `xlsxwriter`: Advanced Excel features (charts, formulas)

**For Visualization-Ready JSON:**
- Structure optimized for:
  - D3.js
  - Chart.js
  - Plotly
  - Tableau
  - Power BI
  - Custom dashboards

**For HTML/PDF (as previously described):**
- Jinja2: HTML templates
- matplotlib/plotly: Static charts embedded in reports
- weasyprint: PDF generation from HTML

**Output File Organization:**

```
/mnt/user-data/outputs/
└── sec/
    └── Albertsons_Companies_Inc/
        └── 10_K/
            └── 2025-10-13/
                ├── ratio_analysis_report.json        # Complete analysis
                ├── ratio_results.csv                 # Simple CSV
                ├── statement_summary.csv             # Normalized statements
                ├── time_series.csv                   # Trend data
                ├── financial_analysis.xlsx           # Complete Excel workbook
                ├── visualization_data.json           # For graphing software
                ├── analysis_report.html              # Human-readable
                ├── analysis_report.pdf               # Printable
                └── audit_trail.json                  # Full lineage
```

**Graphical Software Integration Points:**

1. **CSV Import:** Standard delimiter, headers in row 1, numeric values without formatting
2. **Excel Import:** Named ranges for key metrics, formulas preserved, charts embedded
3. **JSON API:** RESTful endpoints serving visualization_data.json
4. **Direct DB Access:** SQL views exposing ratio results for BI tools

**Example: Tableau Integration**
```python
# Export to Tableau-friendly format
def export_for_tableau(filing_id):
    ratios = get_all_ratios(filing_id)
    
    tableau_export = pd.DataFrame([
        {
            'Company': ratio.company_name,
            'Period': ratio.period_end,
            'Category': ratio.category,
            'Metric': ratio.ratio_name,
            'Value': ratio.value,
            'Benchmark': ratio.industry_benchmark,
            'Dimension1': ratio.level,  # Calculation level
            'Dimension2': ratio.confidence  # Data quality
        }
        for ratio in ratios
    ])
    
    tableau_export.to_csv('tableau_export.csv', index=False)
```

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-3)

**Goal:** Build core data pipeline from XBRL to database

**Week 1: Database Setup**
- Design and create database schema
- Set up PostgreSQL database
- Create initial table structures
- Write database migration scripts
- Set up database connection layer

**Week 2: Hierarchy Builder**
- Implement linkbase parsers
- Build statement identification logic
- Implement tree traversal algorithm
- Create concept ID generation
- Test with 3-5 sample filings

**Week 3: Database Populator**
- Implement fact-to-concept matching
- Add value population logic
- Integrate verification results
- Add data validation
- Test end-to-end pipeline

**Deliverable:** Working system that can take parsed XBRL and build hierarchical database

### Phase 2: Semantic Layer (Weeks 4-5)

**Goal:** Add semantic mapping and query capabilities

**Week 4: Taxonomy Enricher + Role Mapper**
- Integrate taxonomy manager
- Implement label extraction
- Create semantic mapping rules (initial set)
- Build rule evaluation engine
- Test semantic mappings on sample data

**Week 5: Financial Data Accessor**
- Build semantic query API
- Implement fallback strategies
- Add data quality reporting
- Create confidence scoring
- Write comprehensive tests

**Deliverable:** API that can retrieve values by semantic name across different company structures

### Phase 3: Ratio Engine (Weeks 6-8)

**Goal:** Calculate and validate financial ratios

**Week 6: Ratio Calculator Core**
- Define initial ratio set (20-30 core ratios)
- Implement formula execution engine
- Add validation logic
- Create result storage
- Build calculation audit trail

**Week 7: Quality & Validation**
- Implement cross-validation logic
- Add outlier detection
- Create confidence scoring
- Build error handling
- Add calculation verification checks

**Week 8: Testing & Refinement**
- Test on diverse companies
- Validate ratio calculations manually
- Refine semantic mappings based on errors
- Performance optimization
- Bug fixes

**Deliverable:** Fully functional ratio calculation engine with quality controls

### Phase 4: Output Generation (Weeks 9-10)

**Goal:** Produce human-readable reports

**Week 9: Report Generator**
- Create JSON output formatter
- Build HTML report templates
- Add visualization components (charts)
- Implement PDF generation
- Create interpretation text generator

**Week 10: Polish & Documentation**
- User-friendly report styling
- Add interpretation guides for all ratios
- Create user documentation
- Write technical documentation
- Final testing

**Deliverable:** Complete reporting system

### Phase 5: Production Readiness (Weeks 11-12)

**Goal:** Prepare for production use

**Week 11: Integration & Performance**
- Integrate with existing XBRL parser workflow
- Performance optimization
- Batch processing capabilities
- Error handling and logging
- Monitoring setup

**Week 12: Testing & Deployment**
- End-to-end testing with real filings
- Edge case handling
- Deployment preparation
- Create deployment documentation
- Initial production run

**Deliverable:** Production-ready mat_acc system

---

## Technical Stack Recommendations

### Core Technologies

**Database:**
- PostgreSQL 14+ (JSON support, robust querying)
- SQLAlchemy for ORM (if using Python)

**Backend Language:**
- Python 3.10+ (matches existing XBRL parser)
- Libraries:
  - pandas: Data manipulation
  - numpy: Numerical calculations
  - psycopg2: PostgreSQL connector
  - lxml: XML parsing (for linkbases)
  - jinja2: Template rendering

**Report Generation:**
- Jinja2: HTML templates
- matplotlib/plotly: Charts
- weasyprint: PDF generation from HTML

**Testing:**
- pytest: Unit and integration tests
- coverage: Test coverage tracking

**Documentation:**
- Sphinx: Technical documentation
- Markdown: User guides

### Development Tools

- Git: Version control
- Docker: Containerization for deployment
- GitHub Actions / GitLab CI: Continuous integration
- Black/flake8: Code formatting and linting

---

## Critical Success Factors

1. **Hierarchy Accuracy**: The foundation must be rock-solid. Any errors in hierarchy building cascade through the entire system.

2. **Verification Integration**: Never calculate on unverified data. Trust the verification module.

3. **Data Lineage**: Every calculated value must trace back to source facts. Audit trail is non-negotiable.

4. **Graceful Degradation**: Handle missing data elegantly. Report what's unavailable rather than failing.

5. **Extensibility**: Make it easy to add new ratios, mapping rules, and output formats.

6. **Performance**: Process filings in reasonable time (<5 minutes per filing).

7. **Testing**: Comprehensive test coverage with real-world XBRL filings.

---

## Appendix A: Key Design Decisions

### Why Hierarchy-First?

**Problem:** Name-based mapping is ambiguous.  
**Solution:** Position in structure is definitive.  
**Benefit:** Works across different company presentations.

### Why SQL Database?

**Problem:** Complex relationships (parent-child, calculations, temporal).  
**Solution:** Relational database with JSONB for flexibility.  
**Benefit:** Powerful queries, data integrity, scalability.

### Why Semantic Layer?

**Problem:** Ratio formulas can't hardcode company-specific XBRL names.  
**Solution:** Abstract semantic names (current_assets, net_income).  
**Benefit:** Ratio code works across all companies.

### Why Separate Verification?

**Problem:** Can't trust company data blindly.  
**Solution:** Depend on existing verification module.  
**Benefit:** Quality assurance, confidence scoring.

---

## Appendix B: Sample Semantic Names

### Balance Sheet
- `cash_and_equivalents`
- `short_term_investments`
- `accounts_receivable_net`
- `inventory`
- `prepaid_expenses`
- `other_current_assets`
- `current_assets`
- `property_plant_equipment_net`
- `goodwill`
- `intangible_assets_net`
- `long_term_investments`
- `other_noncurrent_assets`
- `noncurrent_assets`
- `total_assets`
- `accounts_payable`
- `accrued_expenses`
- `short_term_debt`
- `current_portion_long_term_debt`
- `other_current_liabilities`
- `current_liabilities`
- `long_term_debt`
- `deferred_tax_liabilities`
- `other_noncurrent_liabilities`
- `noncurrent_liabilities`
- `total_liabilities`
- `common_stock`
- `additional_paid_in_capital`
- `retained_earnings`
- `treasury_stock`
- `accumulated_other_comprehensive_income`
- `stockholders_equity`

### Income Statement
- `total_revenue`
- `cost_of_revenue`
- `gross_profit`
- `research_development`
- `selling_general_administrative`
- `operating_expenses`
- `operating_income`
- `interest_income`
- `interest_expense`
- `other_income_expense`
- `income_before_tax`
- `income_tax_expense`
- `net_income`
- `earnings_per_share_basic`
- `earnings_per_share_diluted`

### Cash Flow Statement
- `net_cash_operating_activities`
- `net_cash_investing_activities`
- `net_cash_financing_activities`
- `net_change_cash`
- `cash_beginning_period`
- `cash_end_period`

---

## Appendix C: Initial Ratio List

### Liquidity Ratios
1. Current Ratio
2. Quick Ratio (Acid Test)
3. Cash Ratio
4. Working Capital

### Profitability Ratios
5. Gross Profit Margin
6. Operating Profit Margin
7. Net Profit Margin
8. Return on Assets (ROA)
9. Return on Equity (ROE)
10. Return on Invested Capital (ROIC)

### Leverage Ratios
11. Debt-to-Equity
12. Debt-to-Assets
13. Interest Coverage
14. Debt Service Coverage

### Efficiency Ratios
15. Asset Turnover
16. Inventory Turnover
17. Receivables Turnover
18. Payables Turnover
19. Days Sales Outstanding (DSO)
20. Days Inventory Outstanding (DIO)
21. Days Payable Outstanding (DPO)
22. Cash Conversion Cycle

### Market Ratios (if price data available)
23. Price-to-Earnings (P/E)
24. Price-to-Book (P/B)
25. Price-to-Sales (P/S)
26. Dividend Yield
27. Payout Ratio

### Advanced Ratios
28. DuPont Analysis (ROE decomposition)
29. Altman Z-Score (bankruptcy prediction)
30. Free Cash Flow
31. Economic Value Added (EVA)

---

## End of Document

**Document Version:** 1.0  
**Last Updated:** February 3, 2026  
**Status:** Architecture Plan - Ready for Implementation

---

## Next Steps

1. Review and approve architecture
2. Set up development environment
3. Create project repository
4. Begin Phase 1 implementation
5. Schedule regular progress reviews

**Contact:** [Your contact information]