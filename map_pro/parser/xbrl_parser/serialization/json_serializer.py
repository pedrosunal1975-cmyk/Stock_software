# Path: xbrl_parser/serialization/json_serializer.py
"""
JSON Serializer

Serialize XBRL parsed data to JSON format with various output options.

This module provides:
- Full JSON export (all data)
- Compact JSON (facts only)
- Debug JSON (with artifacts)
- Anonymized JSON (redacted sensitive data)

Example:
    from ..serialization import JSONSerializer
    
    serializer = JSONSerializer()
    
    # Full export
    json_data = serializer.serialize(parsed_filing)
    
    # Compact export
    compact_data = serializer.serialize(parsed_filing, compact=True)
    
    # Save to file
    serializer.save(parsed_filing, "output.json")
"""

import json
import logging
import gzip
from typing import Optional
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal

from ...core.config_loader import ConfigLoader
from ..models.parsed_filing import ParsedFiling
from ..serialization.constants import (
    CURRENT_SCHEMA_VERSION,
    OUTPUT_FORMAT_JSON,
    OUTPUT_FORMAT_COMPACT_JSON,
    OUTPUT_FORMAT_DEBUG,
    OUTPUT_FORMAT_ANONYMIZED,
    JSON_ENCODING,
    JSON_INDENT,
    MAX_DECIMAL_PLACES,
    ISO_DATE_FORMAT,
    ISO_DATETIME_FORMAT,
    COMPACT_FIELDS,
    COMPACT_EXCLUDE_FIELDS,
    ANONYMIZED_REDACT_FIELDS,
    DEFAULT_COMPRESSION_LEVEL,
    MAX_OUTPUT_SIZE_WARNING,
    MSG_SERIALIZATION_FAILED,
    MSG_OUTPUT_TOO_LARGE
)


class JSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for XBRL data types.
    
    Handles:
    - datetime/date objects
    - Decimal numbers
    - Path objects
    - Enums
    """
    
    def default(self, obj):
        """
        Convert non-serializable objects.
        
        Args:
            obj: Object to convert
            
        Returns:
            Serializable representation
        """
        # Handle datetime
        if isinstance(obj, datetime):
            return obj.strftime(ISO_DATETIME_FORMAT)
        
        # Handle date
        if isinstance(obj, date):
            return obj.strftime(ISO_DATE_FORMAT)
        
        # Handle Decimal
        if isinstance(obj, Decimal):
            # Round to reasonable precision
            return round(float(obj), MAX_DECIMAL_PLACES)
        
        # Handle Path
        if isinstance(obj, Path):
            return str(obj)
        
        # Handle Enum
        if hasattr(obj, 'value'):
            return obj.value
        
        # Handle dataclass
        if hasattr(obj, '__dataclass_fields__'):
            return {
                field: getattr(obj, field)
                for field in obj.__dataclass_fields__
            }
        
        # Default handling
        return super().default(obj)


class JSONSerializer:
    """
    JSON serialization for parsed XBRL filings.
    
    Supports multiple output formats and compression.
    
    Example:
        config = ConfigLoader()
        serializer = JSONSerializer(config)
        
        # Serialize to string
        json_str = serializer.serialize(filing)
        
        # Save to file
        output_path = serializer.save(filing, "output.json")
        
        # Compact format
        compact_json = serializer.serialize(filing, compact=True)
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize JSON serializer.
        
        Args:
            config: Configuration loader
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger(__name__)
        
        # Get configuration
        self.schema_version = self.config.get('output_schema_version', CURRENT_SCHEMA_VERSION)
        self.enable_compression = self.config.get('enable_output_compression', False)
        # self.output_dir = self.config.get('output_exports_dir')  # REMOVED - save() not used
        
        self.logger.debug(
            f"JSONSerializer initialized: version={self.schema_version}, "
            f"compression={self.enable_compression}"
        )
    
    def serialize(
        self,
        filing: ParsedFiling,
        compact: bool = False,
        anonymize: bool = False,
        include_debug: bool = False
    ) -> str:
        """
        Serialize parsed filing to JSON string.
        
        Args:
            filing: Parsed filing to serialize
            compact: If True, only include essential fields
            anonymize: If True, redact sensitive information
            include_debug: If True, include debug artifacts
            
        Returns:
            JSON string
            
        Example:
            json_str = serializer.serialize(filing, compact=True)
        """
        try:
            self.logger.info(
                f"Serializing filing: compact={compact}, anonymize={anonymize}"
            )
            
            # Convert to dict
            data = self._to_dict(
                filing,
                compact=compact,
                anonymize=anonymize,
                include_debug=include_debug
            )
            
            # Add metadata
            data['_meta'] = {
                'schema_version': self.schema_version,
                'export_timestamp': datetime.now().isoformat(),
                'export_format': self._get_format_name(compact, anonymize, include_debug)
            }
            
            # Serialize to JSON
            json_str = json.dumps(
                data,
                cls=JSONEncoder,
                indent=JSON_INDENT,
                ensure_ascii=False
            )
            
            # Check size
            size_bytes = len(json_str.encode(JSON_ENCODING))
            if size_bytes > MAX_OUTPUT_SIZE_WARNING:
                self.logger.warning(
                    f"{MSG_OUTPUT_TOO_LARGE}: {size_bytes / 1024 / 1024:.1f}MB"
                )
            
            self.logger.info(f"Serialization completed: {size_bytes / 1024:.1f}KB")
            return json_str
            
        except Exception as e:
            self.logger.error(f"{MSG_SERIALIZATION_FAILED}: {e}", exc_info=True)
            raise
    
    def save(
        self,
        filing: ParsedFiling,
        filename: str,
        compact: bool = False,
        anonymize: bool = False,
        include_debug: bool = False,
        compress: bool = None
    ) -> Path:
        """
        Save parsed filing to JSON file.
        
        Args:
            filing: Parsed filing to save
            filename: Output filename
            compact: If True, only include essential fields
            anonymize: If True, redact sensitive information
            include_debug: If True, include debug artifacts
            compress: If True, gzip compress output (None = use config)
            
        Returns:
            Path to saved file
            
        Example:
            path = serializer.save(filing, "output.json")
        """
        try:
            # Determine compression
            if compress is None:
                compress = self.enable_compression
            
            # Build output path
            output_path = Path(self.output_dir) / filename
            if compress and not filename.endswith('.gz'):
                output_path = Path(str(output_path) + '.gz')
            
            # Serialize
            json_str = self.serialize(
                filing,
                compact=compact,
                anonymize=anonymize,
                include_debug=include_debug
            )
            
            # Write to file
            if compress:
                with gzip.open(output_path, 'wt', encoding=JSON_ENCODING) as f:
                    f.write(json_str)
            else:
                with open(output_path, 'w', encoding=JSON_ENCODING) as f:
                    f.write(json_str)
            
            self.logger.info(f"Saved to: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to save JSON: {e}", exc_info=True)
            raise
    
    def _to_dict(
        self,
        filing: ParsedFiling,
        compact: bool = False,
        anonymize: bool = False,
        include_debug: bool = False
    ) -> dict[str, any]:
        """
        Convert parsed filing to dictionary.
        
        Args:
            filing: Parsed filing
            compact: Only include essential fields
            anonymize: Redact sensitive data
            include_debug: Include debug artifacts
            
        Returns:
            Dictionary representation
        """
        if compact:
            return self._to_compact_dict(filing, anonymize)
        
        # Full output
        data = {
            'metadata': self._serialize_metadata(filing.metadata, anonymize),
            'instance': self._serialize_instance(filing.instance, anonymize),
            'reliability': filing.reliability.value if filing.reliability else None,
            'quality_score': filing.quality_score
        }
        
        # Optional sections
        if filing.taxonomy and hasattr(filing.taxonomy, 'to_dict'):
            data['taxonomy'] = filing.taxonomy.to_dict()
        
        if filing.validation and hasattr(filing.validation, 'to_dict'):
            data['validation'] = filing.validation.to_dict()
        
        if filing.statistics and hasattr(filing.statistics, 'to_dict'):
            data['statistics'] = filing.statistics.to_dict()
        
        if filing.provenance and hasattr(filing.provenance, 'to_dict'):
            data['provenance'] = filing.provenance.to_dict()
        
        if filing.errors and hasattr(filing.errors, 'to_dict'):
            data['errors'] = filing.errors.to_dict()
        
        # Debug artifacts
        if include_debug:
            data['_debug'] = self._collect_debug_artifacts(filing)
        
        return data
    
    def _to_compact_dict(
        self,
        filing: ParsedFiling,
        anonymize: bool = False
    ) -> dict[str, any]:
        """
        Convert to compact dictionary (facts only).
        
        Args:
            filing: Parsed filing
            anonymize: Redact sensitive data
            
        Returns:
            Compact dictionary
        """
        return {
            'metadata': {
                'filing_id': filing.metadata.filing_id if not anonymize else '[REDACTED]',
                'document_type': filing.metadata.document_type,
                'period_end_date': filing.metadata.period_end_date
            },
            'facts': [
                self._serialize_fact(f, anonymize, filing.instance.contexts, filing.instance.units)
                for f in filing.instance.facts
            ],
            'contexts': {
                cid: self._serialize_context(ctx, anonymize)
                for cid, ctx in filing.instance.contexts.items()
            },
            'units': {
                uid: self._serialize_unit(unit)
                for uid, unit in filing.instance.units.items()
            }
        }
    
    def _serialize_metadata(
        self,
        metadata: any,
        anonymize: bool
    ) -> dict[str, any]:
        """Serialize filing metadata."""
        if hasattr(metadata, 'to_dict'):
            data = metadata.to_dict()
        else:
            data = {}
        
        # Anonymize if requested
        if anonymize:
            for field in ANONYMIZED_REDACT_FIELDS:
                if field in data:
                    data[field] = '[REDACTED]'
        
        return data
    
    def _serialize_instance(
        self,
        instance: any,
        anonymize: bool
    ) -> dict[str, any]:
        """Serialize instance data."""
        return {
            'facts': [
                self._serialize_fact(f, anonymize, instance.contexts, instance.units)
                for f in instance.facts
            ],
            'contexts': {
                cid: self._serialize_context(ctx, anonymize)
                for cid, ctx in instance.contexts.items()
            },
            'units': {
                uid: self._serialize_unit(unit)
                for uid, unit in instance.units.items()
            },
            'namespaces': instance.namespaces if hasattr(instance, 'namespaces') else {},
            'footnotes': instance.footnotes if hasattr(instance, 'footnotes') else {}
        }
    
    def _serialize_fact(self, fact: any, anonymize: bool, contexts: dict = None, units: dict = None) -> dict[str, any]:
        """Serialize a fact with ALL attributes (26 total including denormalized fields)."""
        data = {
            'concept': fact.concept,
            'value': '[REDACTED]' if anonymize else fact.value,
            'context_ref': fact.context_ref,
            'unit_ref': fact.unit_ref,
            'decimals': fact.decimals,
            'precision': fact.precision,
            'id': fact.id if hasattr(fact, 'id') else None,
            'language': fact.language if hasattr(fact, 'language') else None,
            'is_nil': fact.is_nil if hasattr(fact, 'is_nil') else False,
            'fact_type': fact.fact_type.value if hasattr(fact, 'fact_type') and hasattr(fact.fact_type, 'value') else (str(fact.fact_type) if hasattr(fact, 'fact_type') else None),
            'footnote_refs': fact.footnote_refs if hasattr(fact, 'footnote_refs') else [],
            'tuple_parent': fact.tuple_parent if hasattr(fact, 'tuple_parent') else None,
            'tuple_order': fact.tuple_order if hasattr(fact, 'tuple_order') else None,
            'source_file': str(fact.source_file) if hasattr(fact, 'source_file') and fact.source_file else None,
            'source_line': fact.source_line if hasattr(fact, 'source_line') else None,
            'source_element': fact.source_element if hasattr(fact, 'source_element') else None,
            'reliability': fact.reliability.value if hasattr(fact, 'reliability') and hasattr(fact.reliability, 'value') else (str(fact.reliability) if hasattr(fact, 'reliability') else None),
            'source_component': fact.source_component if hasattr(fact, 'source_component') else None,
            'error_count': len(fact.errors) if hasattr(fact, 'errors') and isinstance(fact.errors, list) else 0,
            'warning_count': len(fact.warnings) if hasattr(fact, 'warnings') and isinstance(fact.warnings, list) else 0,
        }
        
        # Add denormalized context fields (matching CSV output)
        if contexts and fact.context_ref and fact.context_ref in contexts:
            context = contexts[fact.context_ref]
            
            # Entity identifier
            if hasattr(context, 'entity') and hasattr(context.entity, 'identifier'):
                data['entity_identifier'] = context.entity.identifier
            else:
                data['entity_identifier'] = None
            
            # Period type and dates
            if hasattr(context, 'period'):
                period = context.period
                
                # Period type (INSTANT or DURATION)
                if hasattr(period, 'period_type'):
                    data['period_type'] = period.period_type.value if hasattr(period.period_type, 'value') else str(period.period_type)
                else:
                    data['period_type'] = None
                
                # Instant
                if hasattr(period, 'instant'):
                    data['period_instant'] = period.instant.isoformat() if period.instant else None
                else:
                    data['period_instant'] = None
                
                # Start date
                if hasattr(period, 'start_date'):
                    data['period_start'] = period.start_date.isoformat() if period.start_date else None
                else:
                    data['period_start'] = None
                
                # End date
                if hasattr(period, 'end_date'):
                    data['period_end'] = period.end_date.isoformat() if period.end_date else None
                else:
                    data['period_end'] = None
            else:
                data['period_type'] = None
                data['period_instant'] = None
                data['period_start'] = None
                data['period_end'] = None
        else:
            data['entity_identifier'] = None
            data['period_type'] = None
            data['period_instant'] = None
            data['period_start'] = None
            data['period_end'] = None
        
        # Add denormalized unit measures (matching CSV output)
        if units and fact.unit_ref and fact.unit_ref in units:
            unit = units[fact.unit_ref]
            
            # Get measures
            if hasattr(unit, 'measures') and unit.measures:
                # Join multiple measures with comma (e.g., "iso4217:USD")
                data['unit_measures'] = ','.join(unit.measures) if isinstance(unit.measures, list) else str(unit.measures)
            else:
                data['unit_measures'] = None
        else:
            data['unit_measures'] = None
        
        return data
    
    def _serialize_context(self, context: any, anonymize: bool) -> dict[str, any]:
        """Serialize a context."""
        if hasattr(context, 'to_dict'):
            data = context.to_dict()
        else:
            data = {'id': context.id if hasattr(context, 'id') else None}
        
        # Anonymize entity
        if anonymize and 'entity' in data:
            data['entity'] = '[REDACTED]'
        
        return data
    
    def _serialize_unit(self, unit: any) -> dict[str, any]:
        """Serialize a unit."""
        if hasattr(unit, 'to_dict'):
            return unit.to_dict()
        return {'id': unit.id if hasattr(unit, 'id') else None}
    
    def _collect_debug_artifacts(self, filing: ParsedFiling) -> dict[str, any]:
        """Collect debug artifacts."""
        return {
            'parse_time_ms': filing.statistics.total_duration_ms if filing.statistics else None,
            'error_count': len(filing.errors.errors) if filing.errors else 0,
            'warning_count': len([e for e in (filing.errors.errors if filing.errors else []) if e.severity.value == 'WARNING'])
        }
    
    def _get_format_name(
        self,
        compact: bool,
        anonymize: bool,
        include_debug: bool
    ) -> str:
        """Get format name based on options."""
        if anonymize:
            return OUTPUT_FORMAT_ANONYMIZED
        if include_debug:
            return OUTPUT_FORMAT_DEBUG
        if compact:
            return OUTPUT_FORMAT_COMPACT_JSON
        return OUTPUT_FORMAT_JSON


__all__ = ['JSONSerializer', 'JSONEncoder']
