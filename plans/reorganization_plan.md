# mat_acc Reorganization Plan

## 1. Current State Assessment

### What We Have
- **133 Python files**, **97 YAML definitions** across 7 packages
- Core pipeline works: 88-100% match rate across 13 companies
- 7-pass value pipeline, MIU sign corrections, identity checks, scale normalization
- 46 financial ratios calculated

### What's Broken
**A. Monolithic files (7 files exceed 300-line limit):**

| File | Lines | Problem |
|------|-------|---------|
| ratio_check/ratio_check.py | 939 | CLI + analysis + MIU + output + source verification |
| ratio_check/concept_builder.py | 813 | JSON reading + concept creation + inference + DB enrichment + iXBRL supplementation |
| ratio_check/fact_value_lookup.py | 649 | Value loading + QName parsing + period detection + correction application |
| ratio_check/ratio_calculator.py | 423 | Matching + display + summary building |
| ratio_check/debug_reporter.py | 422 | Reporting + state tracking |
| ratio_check/data_preparer.py | 431 | Script running + status checking |
| ratio_check/database_checker.py | 397 | DB queries + population |

**B. Code duplication:**
- `_parse_qname()` implemented 3+ times (fact_value_lookup.py, concept_builder.py, scale_normalizer.py)
- `_get_local_name()` in match_verifier.py, sign_analyzer.py, fact_merger.py
- `_alternate_qname()` in fact_value_lookup.py (and implicitly elsewhere)

**C. 21 flat files in ratio_check/ with no organization:**
- No subdirectory structure reflecting the pipeline stages
- Hard to find what you need, hard to understand the flow

**D. Files in process/matcher/ also oversized:**
- coordinator.py (963 lines) - matching + rejection + diagnostics + composites
- component_loader.py (640 lines) - loading + parsing + validation + overlay merging

---

## 2. Design Principles

1. **Pipeline clarity** - Directory structure mirrors the execution pipeline
2. **Single responsibility** - Each file does ONE thing, stays under 300 lines
3. **Shared utilities** - Duplicated logic extracted to one place
4. **Backward compatibility** - Re-exports in __init__.py preserve old import paths
5. **Incremental implementation** - Each step is testable before moving to the next
6. **No behavioral changes** - Pure refactoring, no algorithm modifications

---

## 3. The Pipeline (Execution Order)

```
Step 1: INPUT          - Select filing, discover sources, load data
Step 2: CONCEPTS       - Build concept index from filing data
Step 3: MATCHING       - Match dictionary components against concepts
Step 4: VALUES         - Load numeric values from mapped statements
Step 5: MATH VERIFY    - iXBRL extraction, reconciliation, identities
Step 6: POPULATE       - 7-pass value pipeline
Step 7: MATCH VERIFY   - Post-match plausibility and alternative promotion
Step 8: CALCULATE      - Ratio computation + scale normalization
Step 9: OUTPUT         - Report generation (JSON, CSV, text)
```

---

## 4. Target Directory Structure

```
mat_acc/
  core/
    qname.py              # NEW: shared QName utilities (extracted from 3+ files)
    (rest unchanged)

  dictionary/             # UNCHANGED
  loaders/                # UNCHANGED
  database/               # UNCHANGED

  process/
    matcher/
      engine/
        coordinator.py    # REFACTORED: <300 lines, core matching only
        candidate_filter.py  # EXTRACTED: candidate retrieval + rejection + type compat
        match_diagnostics.py # EXTRACTED: diagnostics logging
        component_loader.py  # REFACTORED: <300 lines
        yaml_parser.py       # EXTRACTED: _parse_* methods from component_loader
      evaluators/         # UNCHANGED (clean, modular)
      models/             # UNCHANGED (stable data models)
      scoring/            # UNCHANGED (clean)
    hierarchy/            # UNCHANGED
    enricher/             # UNCHANGED

  ratio_check/
    __init__.py           # Updated re-exports for backward compat
    __main__.py           # UNCHANGED

    # --- DATA MODELS ---
    ratio_models.py       # UNCHANGED (92 lines, clean)

    # --- INPUT LAYER (Step 1-2) ---
    input/
      __init__.py
      filing_menu.py      # MOVED (183 lines, clean)
      source_checker.py   # MOVED (352 lines, could trim)
      concept_builder.py  # REFACTORED: core build logic only (<300 lines)
      concept_enricher.py # EXTRACTED: DB/parsed/hierarchy enrichment
      concept_supplement.py  # EXTRACTED: iXBRL supplementation

    # --- VALUE LAYER (Step 4, 6) ---
    values/
      __init__.py
      fact_value_lookup.py  # REFACTORED: loading + lookup (<300 lines)
      fact_loading.py       # EXTRACTED: _load_from_mapped, _add_fact, period detection
      value_populator.py    # MOVED (367 lines, currently 7-pass pipeline)

    # --- VERIFICATION LAYER (Step 5, 7) ---
    math_verify/          # KEPT AS-IS (clean subdirectory, 6 files)
      __init__.py
      ixbrl_extractor.py
      context_filter.py
      fact_reconciler.py
      sign_analyzer.py
      identity_validator.py

    match_verify/         # KEPT AS-IS (clean subdirectory, 4 files)
      __init__.py
      match_verifier.py
      plausibility_checks.py
      qualifier_rules.py
      fallback_patterns.py

    # --- CALCULATION LAYER (Step 8) ---
    calculation/
      __init__.py
      ratio_engine.py       # MOVED (223 lines, clean)
      ratio_composites.py   # MOVED (286 lines, clean)
      ratio_definitions.py  # MOVED (300 lines)
      ratio_defs_extended.py  # MOVED (172 lines)
      scale_normalizer.py   # MOVED (269 lines, clean)

    # --- ORCHESTRATION (Step 1-9 coordination) ---
    orchestrator.py       # REFACTORED from ratio_check.py: analysis pipeline only (<300)
    workflow.py           # EXTRACTED from ratio_check.py: CLI interaction + menu flow (<300)
    ratio_calculator.py   # REFACTORED: matching coordination only, display extracted (<300)
    display.py            # EXTRACTED from ratio_calculator.py: all _display_* methods

    # --- INDUSTRY ---
    industry/
      __init__.py
      detector.py         # MOVED from industry_detector.py (197 lines)
      registry.py         # MOVED from industry_registry.py (245 lines)

    # --- SUPPORT (not in main pipeline) ---
    support/
      __init__.py
      database_checker.py # MOVED (397 lines)
      data_preparer.py    # MOVED (431 lines)
      debug_reporter.py   # MOVED (422 lines)

    # --- DIAGNOSTICS (dev tools, not production pipeline) ---
    diagnostics/
      __init__.py
      check_parsed_json.py  # MOVED (110 lines)
      diagnose_parsed.py    # MOVED (226 lines)

  output/                 # UNCHANGED
  scripts/                # UNCHANGED
  tests/                  # Update imports as needed
```

---

## 5. Implementation Phases

### Phase 0: Shared Utilities (LOW RISK)
**Create `core/qname.py`** - Extract duplicated QName parsing into one module.

Contents:
- `parse_qname(qname_str) -> (namespace, local_name)` - from fact_value_lookup.py
- `get_local_name(qname_str) -> str` - convenience wrapper
- `alternate_qname(qname) -> Optional[str]` - colon <-> underscore conversion
- `normalize_qname(qname) -> str` - canonical form

Then update fact_value_lookup.py, concept_builder.py, scale_normalizer.py,
match_verifier.py, sign_analyzer.py to import from `core.qname`.

**Test:** Run ratio_check on Apple. All results must be identical.

---

### Phase 1: Create Subdirectories + Move Clean Files (MEDIUM RISK)
Move files that need NO refactoring into their new subdirectory homes.
Add `__init__.py` re-exports so old import paths still work.

1. Create `ratio_check/input/` - move filing_menu.py, source_checker.py
2. Create `ratio_check/values/` - move value_populator.py
3. Create `ratio_check/calculation/` - move ratio_engine.py, ratio_composites.py,
   ratio_definitions.py, ratio_defs_extended.py, scale_normalizer.py
4. Create `ratio_check/industry/` - move industry_detector.py, industry_registry.py
5. Create `ratio_check/support/` - move database_checker.py, data_preparer.py, debug_reporter.py
6. Create `ratio_check/diagnostics/` - move check_parsed_json.py, diagnose_parsed.py

**Critical:** Update `ratio_check/__init__.py` to re-export from new locations.

**Test:** Run ratio_check on Apple + Cooper Standard. Identical results.

---

### Phase 2: Split concept_builder.py (813 -> 3 files, HIGH RISK)

Split into:
1. `input/concept_builder.py` (<300 lines) - Core: build_from_filing(), build index
2. `input/concept_enricher.py` (<300 lines) - Enrichment: _enrich_from_parsed(),
   _enrich_from_database(), _enrich_from_hierarchy(), _apply_taxonomy_info()
3. `input/concept_supplement.py` (<200 lines) - iXBRL supplementation:
   supplement_from_ixbrl(), inference helpers

Move shared inference helpers (_infer_balance_type, _infer_period_type) to a
methods module or keep in concept_builder.

**Test:** Run ratio_check on Apple + Eli Lilly + SIFCO. Identical results.

---

### Phase 3: Split fact_value_lookup.py (649 -> 2 files, MEDIUM RISK)

Split into:
1. `values/fact_value_lookup.py` (<300 lines) - Public API: get_value(), apply_corrections(),
   _find_values(), _lookup_normalized() + uses core.qname
2. `values/fact_loading.py` (<300 lines) - Loading: load_from_filing(), _load_from_mapped(),
   _add_fact_from_mapped(), _determine_primary_period(), _is_primary_statement()

FactValue dataclass stays in fact_value_lookup.py (or a shared models file).

**Test:** Run ratio_check on Cooper Standard (filing-date period fix must still work).

---

### Phase 4: Split ratio_check.py (939 -> 2 files, HIGH RISK)

Split into:
1. `orchestrator.py` (<300 lines) - Pipeline coordination:
   _run_analysis(), _run_math_verify(), _verify_sources()
2. `workflow.py` (<300 lines) - CLI flow:
   run(), _print_header(), _print_selection(), _save_results(), _offer_save()
   + main() function

The orchestrator exposes a clean API: `analyze(filing_selection) -> AnalysisResult`
The workflow calls the orchestrator and handles user interaction.

**Test:** Run ratio_check interactively. Menu, analysis, display, save all work.

---

### Phase 5: Split ratio_calculator.py (423 -> 2 files, MEDIUM RISK)

Split into:
1. `ratio_calculator.py` (<300 lines) - analyze(), match_components(),
   _build_component_match(), _build_ratio_list(), _build_summary()
2. `display.py` (<200 lines) - display_results(), _display_components(),
   _display_ratios(), _display_summary(), _display_pmfv_corrections()

**Test:** Run ratio_check on any company. Display output identical.

---

### Phase 6: Split process/matcher coordinator.py (963 -> 3 files, HIGH RISK)

Split into:
1. `coordinator.py` (<300 lines) - resolve_all(), resolve_component(),
   _match_component() core loop, get_all_components()
2. `candidate_filter.py` (<300 lines) - _get_candidates(), _check_rejection(),
   _matches_rejection(), _is_exact_name_match(), _qualifier_penalty(),
   _is_type_compatible(), _infer_data_category()
3. `match_diagnostics.py` (<200 lines) - get_match_diagnostics(),
   print_diagnostics_summary(), _log_candidate_diagnostics()

**Test:** Run ratio_check on Apple + SIFCO + Cooper Standard. Matching identical.

---

### Phase 7: Split component_loader.py (640 -> 2 files, MEDIUM RISK)

Split into:
1. `component_loader.py` (<300 lines) - load_all(), load_for_market(),
   load_file(), get_*, validate_all(), cache management
2. `yaml_parser.py` (<300 lines) - _parse_component(), _parse_matching_rules(),
   _parse_scoring(), _parse_composition(), _parse_validation(), _parse_enum()

**Test:** Run ratio_check on any company. Component loading identical.

---

## 6. Risk Mitigation

### Testing Strategy
- After EACH phase: run ratio_check on at least 2 companies
- Compare output line-by-line with pre-refactoring baseline
- Keep old files as .bak until verified (then delete)

### Import Safety
- Every new `__init__.py` re-exports symbols from old paths
- No external code should need to change imports
- The `ratio_check/__init__.py` facade maintains backward compatibility

### Rollback Plan
- Each phase is a separate git commit
- If a phase breaks, revert that commit only
- Phases are independent (except Phase 0 which all others depend on)

---

## 7. What We Are NOT Changing

- **dictionary/** - Clean, well-structured YAML definitions. No changes.
- **loaders/** - Stable data readers. No changes.
- **database/** - Stable DB layer. No changes.
- **output/** - Clean formatter/section architecture. No changes.
- **process/evaluators/** - Clean, modular evaluators. No changes.
- **process/matcher/models/** - Stable data models. No changes.
- **process/matcher/scoring/** - Clean scoring layer. No changes.
- **process/hierarchy/** - Stable hierarchy building. No changes.
- **math_verify/** - Clean MIU implementation. Just move as-is.
- **match_verify/** - Clean PMFV implementation. Just move as-is.

---

## 8. Expected Outcome

After reorganization:
- **ZERO files over 300 lines** in ratio_check/
- **ZERO duplicated _parse_qname()** implementations
- **Clear pipeline structure** visible in directory layout
- **Each file has ONE job** - easy to find, understand, and fix
- **All functionality preserved** - same results, same mechanisms
- **Backward-compatible imports** - scripts/ and tests/ still work

File count change: 33 files -> ~40 files (more files, but each is smaller and focused)
Line count: ~6000 lines -> ~6000 lines (same code, better organized)
