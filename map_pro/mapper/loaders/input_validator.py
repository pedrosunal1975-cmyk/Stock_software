# Path: loaders/input_validator.py
"""
Input Validator - Water Paradigm

Validates parsed filing data integrity for extraction.
NO validation of rules or schemas (they don't exist).

Validates:
1. Parsed data integrity (facts, contexts, units present)
2. Taxonomy availability (if needed)
3. Data quality (completeness, consistency)
4. Extension handling

Does NOT validate:
- Mapping rules (don't exist)
- Target schemas (don't exist)
- Transformation requirements (no transformation)
"""

import logging
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from ..loaders.parsed_data import ParsedDataLoader
from ..loaders.parser_output import ParserOutputDeserializer, ParsedFiling
from ..loaders.taxonomy import TaxonomyLoader


@dataclass
class ValidationResult:
    """Result of validation with errors, warnings, and info."""
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    info: list = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0
    
    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
    
    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)
    
    def add_info(self, message: str) -> None:
        """Add an info message."""
        self.info.append(message)


class InputValidator:
    """
    Validates parsed filing inputs for extraction.
    
    Water paradigm: Only validates data integrity, not transformation requirements.
    
    Example:
        validator = InputValidator()
        result = validator.validate_parsed_filing(parsed_json_path)
        
        if not result.is_valid:
            print(f"Validation failed: {result.errors}")
    """
    
    def __init__(self):
        """Initialize input validator."""
        self.logger = logging.getLogger('input.validator')
        self.logger.info("InputValidator initialized (water paradigm)")
        
        # Initialize loaders (NO rules/schema loaders!)
        self.parsed_loader = ParsedDataLoader()
        self.deserializer = ParserOutputDeserializer()
        self.taxonomy_loader = TaxonomyLoader()
    
    @staticmethod
    def _normalize_to_list(collection: any) -> list[any]:
        """
        Normalize any collection format to list.
        
        Handles: dict, list, tuple, set, any iterable, None
        Future-proof for format changes.
        
        Args:
            collection: any collection type
            
        Returns:
            List of items
        """
        if collection is None:
            return []
        elif isinstance(collection, dict):
            return list(collection.values())
        elif isinstance(collection, list):
            return collection
        else:
            # Handle any iterable (tuple, set, generator, etc)
            try:
                return list(collection)
            except (TypeError, AttributeError):
                return []
    
    def validate_parsed_filing(
        self,
        parsed_json_path: Path,
        **kwargs  # Ignore unused args for backward compatibility
    ) -> ValidationResult:
        """
        Validate parsed filing data integrity.
        
        Validates:
        1. Parsed data can be loaded
        2. Facts, contexts, units are present
        3. Data quality (completeness)
        4. Extensions are noted
        
        Args:
            parsed_json_path: Path to parsed.json file
            **kwargs: Ignored (for backward compatibility)
            
        Returns:
            ValidationResult with detailed findings
        """
        result = ValidationResult()
        
        self.logger.info(f"Validating: {parsed_json_path}")
        
        # 1. Load and deserialize parsed data
        try:
            with open(parsed_json_path, 'r', encoding='utf-8') as f:
                parsed_data = json.load(f)
            
            parsed_filing = self.deserializer.deserialize(parsed_data, parsed_json_path)
            result.add_info(f"Loaded filing: {parsed_filing.characteristics.filing_type}")
        except Exception as e:
            result.add_error(f"Failed to load parsed data: {e}")
            return result  # Can't proceed without data
        
        # 2. Validate data integrity
        self._validate_data_integrity(parsed_filing, result)
        
        # 3. Validate data quality
        self._validate_data_quality(parsed_filing, result)
        
        # 4. Check company extensions (just note them, not errors)
        self._validate_extensions(parsed_filing, result)
        
        # Log summary
        if result.is_valid:
            self.logger.info(
                f"âœ“ Validation passed: {len(result.warnings)} warnings, "
                f"{len(result.info)} info"
            )
        else:
            self.logger.error(
                f"âœ— Validation failed: {len(result.errors)} errors, "
                f"{len(result.warnings)} warnings"
            )
        
        return result
    
    def _validate_data_integrity(
        self,
        parsed_filing: ParsedFiling,
        result: ValidationResult
    ) -> None:
        """Validate parsed data integrity."""
        chars = parsed_filing.characteristics
        
        # Check basic data presence
        if not parsed_filing.facts:
            result.add_error("No facts found in parsed filing")
        else:
            result.add_info(f"Found {len(parsed_filing.facts)} facts")
        
        if not parsed_filing.contexts:
            result.add_error("No contexts found in parsed filing")
        else:
            result.add_info(f"Found {len(parsed_filing.contexts)} contexts")
        
        if not parsed_filing.units:
            result.add_warning("No units found in parsed filing")
        else:
            result.add_info(f"Found {len(parsed_filing.units)} units")
        
        # Check filing characteristics
        if not chars.market:
            result.add_warning("Market not identified")
        
        if not chars.filing_type:
            result.add_warning("Filing type not identified")
        
        if not chars.primary_taxonomy:
            result.add_warning("Primary taxonomy not identified")
        
        # Check entity information (from raw_data)
        entity_identifier = self._extract_entity_identifier(parsed_filing)
        entity_name = self._extract_entity_name(parsed_filing)
        
        if not entity_identifier:
            result.add_warning("Entity identifier not found")
        
        if not entity_name:
            result.add_warning("Entity name not found")
    
    def _validate_data_quality(
        self,
        parsed_filing: ParsedFiling,
        result: ValidationResult
    ) -> None:
        """Validate data quality."""
        # Check for facts with values
        facts_with_values = sum(1 for f in parsed_filing.facts if f.value is not None)
        
        if facts_with_values == 0:
            result.add_error("No facts have values")
        elif facts_with_values < len(parsed_filing.facts) * 0.5:
            result.add_warning(
                f"Only {facts_with_values}/{len(parsed_filing.facts)} facts "
                f"have values ({facts_with_values/len(parsed_filing.facts)*100:.1f}%)"
            )
        else:
            result.add_info(
                f"{facts_with_values}/{len(parsed_filing.facts)} facts "
                f"have values ({facts_with_values/len(parsed_filing.facts)*100:.1f}%)"
            )
        
        # Check for contexts with periods
        contexts_list = self._normalize_to_list(parsed_filing.contexts)
        contexts_with_periods = sum(
            1 for c in contexts_list
            if getattr(c, 'period', None) is not None
        )
        
        if contexts_with_periods < len(parsed_filing.contexts) * 0.9:
            result.add_warning(
                f"Only {contexts_with_periods}/{len(parsed_filing.contexts)} contexts "
                f"have periods"
            )
    
    def _validate_extensions(
        self,
        parsed_filing: ParsedFiling,
        result: ValidationResult
    ) -> None:
        """Check for company extensions (just informational)."""
        # Count extension concepts
        extension_count = 0
        extension_namespaces = set()
        
        for fact in parsed_filing.facts:
            if ':' in fact.name:
                namespace = fact.name.split(':')[0]
                # Common standard namespaces
                if namespace not in ['us-gaap', 'dei', 'ifrs', 'uk-gaap', 'gaap']:
                    extension_count += 1
                    extension_namespaces.add(namespace)
        
        if extension_count > 0:
            result.add_info(
                f"Found {extension_count} extension concepts from "
                f"{len(extension_namespaces)} namespace(s): {', '.join(extension_namespaces)}"
            )
            result.add_info("Extensions are normal - company-specific concepts")
    
    def _extract_entity_identifier(self, parsed_filing: ParsedFiling) -> Optional[str]:
        """Extract entity identifier from raw_data."""
        try:
            # Try from instance.entity
            instance = parsed_filing.raw_data.get('instance', {})
            entity = instance.get('entity', {})
            if isinstance(entity, dict):
                identifier = entity.get('identifier') or entity.get('cik')
                if identifier:
                    return str(identifier)
            
            # Try from facts (dei:EntityCentralIndexKey or similar)
            for fact in parsed_filing.facts:
                if 'EntityCentralIndexKey' in fact.name or 'EntityIdentifier' in fact.name:
                    if fact.value:
                        return str(fact.value)
            
            return None
        except:
            return None
    
    def _extract_entity_name(self, parsed_filing: ParsedFiling) -> Optional[str]:
        """Extract entity name from raw_data."""
        try:
            # Try from instance.entity
            instance = parsed_filing.raw_data.get('instance', {})
            entity = instance.get('entity', {})
            if isinstance(entity, dict):
                name = entity.get('name') or entity.get('registrant_name')
                if name:
                    return str(name)
            
            # Try from facts (dei:EntityRegistrantName or similar)
            for fact in parsed_filing.facts:
                if 'EntityRegistrantName' in fact.name or 'EntityName' in fact.name:
                    if fact.value:
                        return str(fact.value)
            
            return None
        except:
            return None


__all__ = ['InputValidator', 'ValidationResult']