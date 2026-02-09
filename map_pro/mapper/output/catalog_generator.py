# Path: output/catalog_generator.py
"""
Catalog Generator

Generates catalog metadata for classified financial statements.
Creates index files that organize statements by classification.

DESIGN PRINCIPLES:
- Market agnostic (works with any jurisdiction)
- Preserves all data (never filters out networks)
- Creates navigable index structure
- Links related statements (core + details)

RESPONSIBILITY:
- Generate catalog.json with statement classifications
- Group statements by category and type
- Link detail schedules to related core statements
- Provide summary statistics

Example:
    generator = CatalogGenerator()
    
    catalog = generator.generate_catalog(
        statement_set=statement_set,
        classifications=classifications,
        export_paths=export_paths
    )
    
    # catalog contains:
    # - core_statements: [list of 4-6 core statement files]
    # - details_by_type: {statement_type: [related detail files]}
    # - all_networks: [complete list of all 99 files]
    # - statistics: {counts and summary}
"""

import logging
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from ..mapping.network_classifier import NetworkClassification
from ..mapping.constants import NetworkCategory, StatementType


class CatalogGenerator:
    """
    Generates catalog metadata for classified financial statements.
    
    Creates structured index files that organize statements by:
    - Category (core, detail, table, policy, document)
    - Statement type (balance sheet, income, cash flow, equity)
    - Relationships (which details relate to which core statements)
    
    The catalog enables users and tools to:
    - Quickly find core financial statements
    - Locate related detail schedules
    - Navigate complex filings efficiently
    - Understand statement organization
    
    Example:
        generator = CatalogGenerator()
        
        catalog = generator.generate(
            classifications=[...],
            filenames={role_uri: 'filename.json', ...}
        )
        
        # Save catalog
        generator.save_catalog(catalog, output_folder / '_catalog.json')
    """
    
    def __init__(self):
        """Initialize catalog generator."""
        self.logger = logging.getLogger('output.catalog_generator')
    
    def generate(
        self,
        classifications: list[NetworkClassification],
        filenames: dict[str, str],
        filing_info: Optional[dict[str, any]] = None
    ) -> dict[str, any]:
        """
        Generate catalog from network classifications.
        
        Args:
            classifications: List of NetworkClassification objects
            filenames: Map of role_uri -> filename
            filing_info: Optional filing metadata
            
        Returns:
            Dictionary containing catalog structure
        """
        self.logger.info(f"Generating catalog for {len(classifications)} networks")
        
        catalog = {
            'generated_at': datetime.now().isoformat(),
            'filing_info': filing_info or {},
            'summary': self._generate_summary(classifications),
            'core_statements': self._extract_core_statements(classifications, filenames),
            'details_by_type': self._organize_details_by_type(classifications, filenames),
            'all_networks_by_category': self._organize_by_category(classifications, filenames),
            'network_index': self._build_network_index(classifications, filenames),
        }
        
        self.logger.info(
            f"Catalog generated: {len(catalog['core_statements'])} core statements, "
            f"{len(catalog['network_index'])} total networks"
        )
        
        return catalog
    
    def save_catalog(self, catalog: dict[str, any], output_path: Path) -> None:
        """
        Save catalog to JSON file.
        
        Args:
            catalog: Catalog dictionary
            output_path: Path to save catalog JSON
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Catalog saved to: {output_path}")
    
    def _generate_summary(
        self,
        classifications: list[NetworkClassification]
    ) -> dict[str, any]:
        """Generate summary statistics."""
        category_counts = {}
        type_counts = {}
        confidence_counts = {}
        
        for classification in classifications:
            # Count by category
            category_counts[classification.category] = \
                category_counts.get(classification.category, 0) + 1
            
            # Count by statement type
            type_counts[classification.statement_type] = \
                type_counts.get(classification.statement_type, 0) + 1
            
            # Count by confidence
            confidence_counts[classification.confidence] = \
                confidence_counts.get(classification.confidence, 0) + 1
        
        return {
            'total_networks': len(classifications),
            'core_statements': category_counts.get(NetworkCategory.CORE_STATEMENT, 0),
            'detail_schedules': category_counts.get(NetworkCategory.DETAIL, 0),
            'tables': category_counts.get(NetworkCategory.TABLE, 0),
            'policies': category_counts.get(NetworkCategory.POLICY, 0),
            'documents': category_counts.get(NetworkCategory.DOCUMENT, 0),
            'other': category_counts.get(NetworkCategory.UNKNOWN, 0),
            'by_category': category_counts,
            'by_statement_type': type_counts,
            'by_confidence': confidence_counts,
        }
    
    def _extract_core_statements(
        self,
        classifications: list[NetworkClassification],
        filenames: dict[str, str]
    ) -> list[dict[str, any]]:
        """Extract core financial statements."""
        core_statements = []
        
        for classification in classifications:
            if classification.category == NetworkCategory.CORE_STATEMENT:
                filename = filenames.get(classification.role_uri)
                if filename:
                    core_statements.append({
                        'filename': filename,
                        'role_uri': classification.role_uri,
                        'role_definition': classification.role_definition,
                        'statement_type': classification.statement_type,
                        'confidence': classification.confidence,
                    })
        
        # Sort by statement type for consistent ordering
        type_order = {
            StatementType.BALANCE_SHEET: 1,
            StatementType.INCOME_STATEMENT: 2,
            StatementType.CASH_FLOW: 3,
            StatementType.EQUITY: 4,
            StatementType.OTHER: 5,
        }
        
        core_statements.sort(
            key=lambda x: type_order.get(x['statement_type'], 99)
        )
        
        return core_statements
    
    def _organize_details_by_type(
        self,
        classifications: list[NetworkClassification],
        filenames: dict[str, str]
    ) -> dict[str, list[dict[str, any]]]:
        """Organize detail schedules by related statement type."""
        details_by_type = {
            StatementType.BALANCE_SHEET: [],
            StatementType.INCOME_STATEMENT: [],
            StatementType.CASH_FLOW: [],
            StatementType.EQUITY: [],
            StatementType.OTHER: [],
        }
        
        for classification in classifications:
            if classification.category == NetworkCategory.DETAIL:
                filename = filenames.get(classification.role_uri)
                if filename:
                    detail_entry = {
                        'filename': filename,
                        'role_uri': classification.role_uri,
                        'role_definition': classification.role_definition,
                        'confidence': classification.confidence,
                    }
                    
                    details_by_type[classification.statement_type].append(detail_entry)
        
        # Sort details within each type
        for statement_type in details_by_type:
            details_by_type[statement_type].sort(
                key=lambda x: x['role_definition'] or x['filename']
            )
        
        return details_by_type
    
    def _organize_by_category(
        self,
        classifications: list[NetworkClassification],
        filenames: dict[str, str]
    ) -> dict[str, list[dict[str, any]]]:
        """Organize all networks by category."""
        by_category = {
            NetworkCategory.CORE_STATEMENT: [],
            NetworkCategory.DETAIL: [],
            NetworkCategory.TABLE: [],
            NetworkCategory.POLICY: [],
            NetworkCategory.PARENTHETICAL: [],
            NetworkCategory.DOCUMENT: [],
            NetworkCategory.UNKNOWN: [],
        }
        
        for classification in classifications:
            filename = filenames.get(classification.role_uri)
            if filename:
                entry = {
                    'filename': filename,
                    'role_uri': classification.role_uri,
                    'role_definition': classification.role_definition,
                    'statement_type': classification.statement_type,
                    'confidence': classification.confidence,
                }
                
                by_category[classification.category].append(entry)
        
        return by_category
    
    def _build_network_index(
        self,
        classifications: list[NetworkClassification],
        filenames: dict[str, str]
    ) -> dict[str, dict[str, any]]:
        """Build complete index of all networks."""
        network_index = {}
        
        for classification in classifications:
            filename = filenames.get(classification.role_uri)
            if filename:
                network_index[filename] = {
                    'role_uri': classification.role_uri,
                    'role_definition': classification.role_definition,
                    'category': classification.category,
                    'statement_type': classification.statement_type,
                    'is_primary': classification.is_primary,
                    'confidence': classification.confidence,
                    'matched_patterns': classification.matched_patterns,
                }
        
        return network_index
    
    def generate_aggregated_core(
        self,
        core_classifications: list[NetworkClassification],
        statements: list[any],
        filing_info: Optional[dict[str, any]] = None
    ) -> dict[str, any]:
        """
        Generate aggregated core statements file content.
        
        Combines all core financial statements into a single structure
        for easy access.
        
        Args:
            core_classifications: List of core statement classifications
            statements: List of Statement objects
            filing_info: Optional filing metadata
            
        Returns:
            Dictionary containing all core statements
        """
        # Create map of role_uri to statement
        statement_map = {
            statement.role_uri: statement
            for statement in statements
        }
        
        aggregated = {
            'generated_at': datetime.now().isoformat(),
            'filing_info': filing_info or {},
            'core_statement_count': len(core_classifications),
            'statements': {}
        }
        
        # Group by statement type
        for classification in core_classifications:
            statement = statement_map.get(classification.role_uri)
            if statement:
                # Use statement type as key
                key = classification.statement_type.lower()
                
                aggregated['statements'][key] = {
                    'role_uri': statement.role_uri,
                    'role_definition': statement.role_definition,
                    'statement_type': classification.statement_type,
                    'total_facts': len(statement.facts),
                    'hierarchy': statement.hierarchy,
                    'facts': [
                        {
                            'concept': fact.concept,
                            'value': str(fact.value),
                            'context_ref': fact.context_ref,
                            'unit_ref': fact.unit_ref,
                            'decimals': fact.decimals,
                            'level': fact.level,
                            'order': fact.order,
                            'parent_concept': fact.parent_concept,
                        }
                        for fact in statement.facts
                    ]
                }
        
        self.logger.info(
            f"Generated aggregated core statements: "
            f"{len(aggregated['statements'])} statement types"
        )
        
        return aggregated
    
    def save_aggregated_core(
        self,
        aggregated: dict[str, any],
        output_path: Path
    ) -> None:
        """
        Save aggregated core statements to JSON file.
        
        Args:
            aggregated: Aggregated core statements dictionary
            output_path: Path to save JSON file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(aggregated, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Aggregated core statements saved to: {output_path}")