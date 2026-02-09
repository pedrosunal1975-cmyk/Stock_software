# Path: observability/debug_artifacts.py
"""
Debug Artifacts

Generates debug outputs for troubleshooting.
"""

import logging
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from ..mapping.models.mapping_result import MappingResult


class DebugArtifacts:
    """
    Generates debug artifacts.
    
    Creates detailed debug outputs including:
    - Full mapping state dumps
    - Conflict details
    - Intermediate results
    - Error traces
    
    Example:
        debug = DebugArtifacts(output_dir)
        debug.save_mapping_state(mapping_result, 'final_state')
        debug.save_conflicts(mapping_result)
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize debug artifacts generator.
        
        Args:
            output_dir: Output directory for debug files
        """
        self.logger = logging.getLogger('observability.debug_artifacts')
        self.output_dir = output_dir or Path('debug_output')
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def save_mapping_state(
        self,
        mapping_result: MappingResult,
        stage: str
    ) -> Path:
        """
        Save complete mapping state.
        
        Args:
            mapping_result: Mapping result
            stage: Stage name (e.g., 'mapper_a', 'final')
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"mapping_state_{stage}_{timestamp}.json"
        output_path = self.output_dir / filename
        
        # Build debug data
        data = {
            'stage': stage,
            'timestamp': timestamp,
            'statistics': {
                'total_facts': mapping_result.statistics.total_facts,
                'facts_mapped': mapping_result.statistics.facts_mapped,
                'facts_skipped': mapping_result.statistics.facts_skipped,
                'facts_failed': mapping_result.statistics.facts_failed
            },
            'mapped_facts': [
                {
                    'source': fact.source_fact.name,
                    'target': fact.target_field,
                    'value': fact.mapped_value,
                    'confidence': fact.confidence,
                    'mapper': fact.mapper_source
                }
                for fact in mapping_result.mapped_facts
            ],
            'errors': mapping_result.errors,
            'warnings': mapping_result.warnings,
            'metadata': mapping_result.metadata
        }
        
        # Write to file
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        self.logger.info(f"Saved mapping state to {output_path}")
        
        return output_path
    
    def save_conflicts(
        self,
        mapping_result: MappingResult
    ) -> Optional[Path]:
        """
        Save conflict details.
        
        Args:
            mapping_result: Mapping result with conflicts
            
        Returns:
            Path to saved file, or None if no conflicts
        """
        if not mapping_result.comparison_results:
            return None
        
        # Filter for conflicts only
        conflicts = [
            comp for comp in mapping_result.comparison_results
            if comp.has_conflict()
        ]
        
        if not conflicts:
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"conflicts_{timestamp}.json"
        output_path = self.output_dir / filename
        
        # Build conflict data
        data = {
            'timestamp': timestamp,
            'conflict_count': len(conflicts),
            'conflicts': [
                {
                    'fact_id': comp.source_fact_id,
                    'agreement_type': comp.agreement_type.value,
                    'agreement_score': comp.agreement_score,
                    'mapper_a': {
                        'target': comp.mapper_a_result.target_field if comp.mapper_a_result else None,
                        'value': comp.mapper_a_result.mapped_value if comp.mapper_a_result else None,
                        'confidence': comp.mapper_a_result.confidence if comp.mapper_a_result else None
                    },
                    'mapper_b': {
                        'target': comp.mapper_b_result.target_field if comp.mapper_b_result else None,
                        'value': comp.mapper_b_result.mapped_value if comp.mapper_b_result else None,
                        'confidence': comp.mapper_b_result.confidence if comp.mapper_b_result else None
                    },
                    'resolution': comp.resolution
                }
                for comp in conflicts
            ]
        }
        
        # Write to file
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        self.logger.info(f"Saved {len(conflicts)} conflicts to {output_path}")
        
        return output_path
    
    def save_error_trace(
        self,
        error: Exception,
        context: dict[str, any]
    ) -> Path:
        """
        Save error trace with context.
        
        Args:
            error: Exception that occurred
            context: Context information
            
        Returns:
            Path to saved file
        """
        import traceback
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"error_trace_{timestamp}.txt"
        output_path = self.output_dir / filename
        
        # Build error report
        lines = []
        lines.append("=" * 80)
        lines.append("ERROR TRACE")
        lines.append("=" * 80)
        lines.append(f"Timestamp: {timestamp}")
        lines.append(f"Error: {type(error).__name__}: {error}")
        lines.append("")
        lines.append("Traceback:")
        lines.append(traceback.format_exc())
        lines.append("")
        lines.append("Context:")
        for key, value in context.items():
            lines.append(f"  {key}: {value}")
        lines.append("=" * 80)
        
        # Write to file
        output_path.write_text('\n'.join(lines))
        
        self.logger.info(f"Saved error trace to {output_path}")
        
        return output_path


__all__ = ['DebugArtifacts']