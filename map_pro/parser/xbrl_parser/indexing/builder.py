# Path: xbrl_parser/indexing/builder.py
"""
Index Builder

Builds SQLite indexes from parsed XBRL filings for fast querying.

This module provides:
- Filing indexing
- Fact extraction and storage
- Context and unit indexing
- Batch processing
- Progress tracking

Example:
    from ..indexing import IndexBuilder
    
    builder = IndexBuilder('/path/to/index.db')
    
    # Index single filing
    builder.index_filing(parsed_filing)
    
    # Index multiple filings
    for filing in filings:
        builder.index_filing(filing)
    
    builder.commit()
    builder.close()
"""

import logging
import sqlite3
import json
from pathlib import Path
from datetime import datetime

from ..models.parsed_filing import ParsedFiling
from ..indexing.schema import DatabaseSchema
from ..indexing.constants import (
    DB_TIMEOUT,
    DB_CHECK_SAME_THREAD,
    DEFAULT_BATCH_SIZE,
    COMMIT_FREQUENCY,
    TABLE_FILINGS,
    TABLE_FACTS,
    TABLE_CONTEXTS,
    TABLE_UNITS,
    TABLE_CONCEPTS,
    COMPRESS_LARGE_FIELDS,
    COMPRESSION_THRESHOLD_BYTES
)


class IndexBuilder:
    """
    Build SQLite index from parsed filings.
    
    Extracts data from ParsedFiling objects and stores in SQLite
    database for fast querying across many filings.
    
    Example:
        # Create builder
        builder = IndexBuilder('filings.db')
        
        # Index filings
        for filing in parse_filings(filing_paths):
            builder.index_filing(filing)
            
            if builder.indexed_count % 100 == 0:
                builder.commit()
        
        # Final commit and close
        builder.commit()
        builder.close()
    """
    
    def __init__(
        self,
        database_path: Path,
        batch_size: int = DEFAULT_BATCH_SIZE
    ):
        """
        Initialize index builder.
        
        Args:
            database_path: Path to SQLite database
            batch_size: Number of records per batch
        """
        self.logger = logging.getLogger(__name__)
        self.database_path = Path(database_path)
        self.batch_size = batch_size
        
        # Statistics
        self.indexed_count = 0
        self.facts_indexed = 0
        self.contexts_indexed = 0
        self.insert_count = 0
        
        # Initialize database
        self._init_database()
        
        self.logger.info(f"IndexBuilder initialized: {database_path}")
    
    def _init_database(self) -> None:
        """Initialize database connection and schema."""
        # Create database directory if needed
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to database
        self.conn = sqlite3.connect(
            str(self.database_path),
            timeout=DB_TIMEOUT,
            check_same_thread=DB_CHECK_SAME_THREAD
        )
        
        # Initialize schema
        schema = DatabaseSchema()
        schema.initialize(self.conn)
        
        self.logger.debug("Database initialized")
    
    def index_filing(self, filing: ParsedFiling) -> None:
        """
        Index a parsed filing.
        
        Args:
            filing: Parsed filing to index
        """
        filing_id = filing.metadata.filing_id
        
        if not filing_id:
            self.logger.warning("Filing has no filing_id, skipping")
            return
        
        self.logger.info(f"Indexing filing: {filing_id}")
        
        # Insert filing metadata
        self._index_filing_metadata(filing)
        
        # Index facts
        if filing.instance and filing.instance.facts:
            self._index_facts(filing)
        
        # Index contexts
        if filing.instance and filing.instance.contexts:
            self._index_contexts(filing)
        
        # Index units
        if filing.instance and filing.instance.units:
            self._index_units(filing)
        
        # Index concepts (if available)
        if filing.taxonomy and hasattr(filing.taxonomy, 'concepts'):
            self._index_concepts(filing)
        
        self.indexed_count += 1
        self.insert_count += 1
        
        # Auto-commit based on frequency
        if self.insert_count >= COMMIT_FREQUENCY:
            self.commit()
        
        self.logger.debug(f"Filing indexed: {filing_id}")
    
    def _index_filing_metadata(self, filing: ParsedFiling) -> None:
        """Index filing metadata."""
        metadata = filing.metadata
        
        # Prepare metadata JSON
        metadata_json = json.dumps({
            'source_files': [str(f) for f in metadata.source_files],
            'entry_point': str(metadata.entry_point) if metadata.entry_point else None,
            'market': metadata.market,
            'regulatory_authority': metadata.regulatory_authority
        })
        
        # Insert filing record
        self.conn.execute(f"""
            INSERT OR REPLACE INTO {TABLE_FILINGS}
            (filing_id, entity_identifier, company_name, document_type,
             filing_date, period_end_date, market, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata.filing_id,
            metadata.entity_identifier,
            metadata.company_name,
            metadata.document_type,
            metadata.filing_date.isoformat() if metadata.filing_date else None,
            metadata.period_end_date.isoformat() if metadata.period_end_date else None,
            metadata.market,
            metadata_json
        ))
    
    def _index_facts(self, filing: ParsedFiling) -> None:
        """Index facts."""
        filing_id = filing.metadata.filing_id
        
        facts_data = []
        for fact in filing.instance.facts:
            facts_data.append((
                filing_id,
                fact.concept,
                fact.context_ref,
                fact.unit_ref,
                str(fact.value),
                fact.decimals,
                fact.fact_type.value if fact.fact_type else None
            ))
        
        # Batch insert
        self.conn.executemany(f"""
            INSERT INTO {TABLE_FACTS}
            (filing_id, concept, context_ref, unit_ref, value, decimals, fact_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, facts_data)
        
        self.facts_indexed += len(facts_data)
    
    def _index_contexts(self, filing: ParsedFiling) -> None:
        """Index contexts."""
        filing_id = filing.metadata.filing_id
        
        contexts_data = []
        for context_id, context in filing.instance.contexts.items():
            # Serialize dimensions if present
            dimensions_json = None
            if context.has_dimensions():
                all_dims = context.get_all_dimensions()
                if all_dims:
                    dimensions_json = json.dumps([
                        {
                            'dimension': dim.dimension,
                            'member': dim.member,
                            'is_typed': False  # ExplicitDimension is always explicit
                        }
                        for dim in all_dims
                    ])
            
            contexts_data.append((
                filing_id,
                context_id,
                context.entity.scheme if context.entity else None,
                context.entity.value if context.entity else None,
                context.period.period_type.value if context.period else None,
                context.period.start_date.isoformat() if context.period and context.period.start_date else None,
                context.period.end_date.isoformat() if context.period and context.period.end_date else None,
                context.period.instant.isoformat() if context.period and context.period.instant else None,
                dimensions_json
            ))
        
        # Batch insert
        self.conn.executemany(f"""
            INSERT INTO {TABLE_CONTEXTS}
            (filing_id, context_id, entity_scheme, entity_identifier,
             period_type, period_start, period_end, instant, dimensions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, contexts_data)
        
        self.contexts_indexed += len(contexts_data)
    
    def _index_units(self, filing: ParsedFiling) -> None:
        """Index units."""
        filing_id = filing.metadata.filing_id
        
        units_data = []
        for unit_id, unit in filing.instance.units.items():
            # Serialize measures
            measures_json = json.dumps(unit.measures) if unit.measures else None
            
            units_data.append((
                filing_id,
                unit_id,
                unit.unit_type.value if unit.unit_type else None,
                measures_json
            ))
        
        # Batch insert
        self.conn.executemany(f"""
            INSERT INTO {TABLE_UNITS}
            (filing_id, unit_id, unit_type, measures)
            VALUES (?, ?, ?, ?)
        """, units_data)
    
    def _index_concepts(self, filing: ParsedFiling) -> None:
        """Index concepts from taxonomy."""
        filing_id = filing.metadata.filing_id
        
        if not hasattr(filing.taxonomy, 'concepts'):
            return
        
        concepts_data = []
        for concept_name, concept in filing.taxonomy.concepts.items():
            concepts_data.append((
                filing_id,
                concept_name,
                concept.concept_type if hasattr(concept, 'concept_type') else None,
                concept.period_type if hasattr(concept, 'period_type') else None,
                concept.data_type if hasattr(concept, 'data_type') else None
            ))
        
        # Batch insert
        self.conn.executemany(f"""
            INSERT INTO {TABLE_CONCEPTS}
            (filing_id, concept_name, concept_type, period_type, data_type)
            VALUES (?, ?, ?, ?, ?)
        """, concepts_data)
    
    def commit(self) -> None:
        """Commit pending transactions."""
        self.conn.commit()
        self.insert_count = 0
        self.logger.debug("Committed transactions")
    
    def get_statistics(self) -> dict[str, int]:
        """
        Get indexing statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'filings_indexed': self.indexed_count,
            'facts_indexed': self.facts_indexed,
            'contexts_indexed': self.contexts_indexed
        }
    
    def close(self) -> None:
        """Close database connection."""
        self.commit()
        self.conn.close()
        self.logger.info("IndexBuilder closed")


__all__ = ['IndexBuilder']
