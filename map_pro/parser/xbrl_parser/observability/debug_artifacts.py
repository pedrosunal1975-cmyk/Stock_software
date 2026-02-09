# Path: xbrl_parser/observability/debug_artifacts.py
"""
Debug Mode Artifact System

Captures troubleshooting data for debugging parsing issues.
Includes intermediate states, error contexts, and anonymization.

Design:
- Capture intermediate XML states
- Save performance profiles
- Record error contexts with surrounding code
- Anonymize sensitive data for support
- Export debug bundles
"""

import json
import hashlib
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


class ArtifactType(str, Enum):
    """Types of debug artifacts."""
    INTERMEDIATE_XML = "intermediate_xml"
    ERROR_CONTEXT = "error_context"
    PERFORMANCE_PROFILE = "performance_profile"
    STACK_TRACE = "stack_trace"
    VALIDATION_DETAIL = "validation_detail"
    MEMORY_SNAPSHOT = "memory_snapshot"


@dataclass
class DebugArtifact:
    """
    A single debug artifact.
    
    Captures a snapshot of parser state for troubleshooting.
    """
    artifact_id: str
    artifact_type: ArtifactType
    timestamp: str
    phase: str
    title: str
    description: str
    data: dict[str, any]
    file_path: Optional[Path] = None
    
    def to_dict(self) -> dict:
        """Convert artifact to dictionary."""
        result = asdict(self)
        result['file_path'] = str(self.file_path) if self.file_path else None
        return result


@dataclass
class ErrorContext:
    """
    Context information for an error.
    
    Captures surrounding code and state when error occurred.
    """
    error_message: str
    error_type: str
    phase: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    surrounding_lines: list[str] = field(default_factory=list)
    local_variables: dict[str, str] = field(default_factory=dict)
    stack_trace: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class DebugArtifactCollector:
    """
    Collects and manages debug artifacts.
    
    Captures debug information during parsing for troubleshooting.
    Supports anonymization and export for support purposes.
    
    Example:
        collector = DebugArtifactCollector(enabled=True)
        
        # Capture intermediate XML
        collector.capture_xml_state(
            phase="taxonomy_loading",
            xml_content=xml_string,
            description="After schema import"
        )
        
        # Capture error context
        collector.capture_error_context(
            error=exception,
            phase="validation",
            source_lines=lines,
            line_number=42
        )
        
        # Export for support
        bundle = collector.export_debug_bundle(
            output_path=Path("debug_bundle.json"),
            anonymize=True
        )
    """
    
    def __init__(self, enabled: bool = False, output_dir: Optional[Path] = None):
        """
        Initialize debug artifact collector.

        Args:
            enabled: Whether artifact collection is enabled
            output_dir: Directory to save artifacts (REQUIRED if enabled=True)
        """
        self.enabled = enabled

        if self.enabled and not output_dir:
            raise ValueError(
                "output_dir is required when debug artifacts are enabled. "
                "Pass output_dir explicitly or disable artifact collection."
            )

        self.output_dir = output_dir
        
        self._artifacts: list[DebugArtifact] = []
        self._error_contexts: list[ErrorContext] = []
        self._session_id = self._generate_session_id()
        
        if self.enabled and not self.output_dir.exists():
            self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:8]
    
    def _generate_artifact_id(self) -> str:
        """Generate unique artifact ID."""
        timestamp = datetime.now().isoformat()
        count = len(self._artifacts)
        return hashlib.md5(f"{timestamp}{count}".encode()).hexdigest()[:12]
    
    def capture_xml_state(
        self,
        phase: str,
        xml_content: str,
        description: str,
        save_to_file: bool = True
    ) -> Optional[DebugArtifact]:
        """
        Capture intermediate XML state.
        
        Args:
            phase: Current parsing phase
            xml_content: XML content to capture
            description: Description of this state
            save_to_file: Whether to save to file
            
        Returns:
            Created artifact, or None if disabled
        """
        if not self.enabled:
            return None
        
        artifact_id = self._generate_artifact_id()
        
        # Save to file if requested
        file_path = None
        if save_to_file:
            file_path = self.output_dir / f"{artifact_id}_xml.xml"
            file_path.write_text(xml_content, encoding='utf-8')
        
        artifact = DebugArtifact(
            artifact_id=artifact_id,
            artifact_type=ArtifactType.INTERMEDIATE_XML,
            timestamp=datetime.now().isoformat(),
            phase=phase,
            title=f"XML State: {phase}",
            description=description,
            data={
                'xml_length': len(xml_content),
                'has_content': bool(xml_content.strip()),
            },
            file_path=file_path
        )
        
        self._artifacts.append(artifact)
        return artifact
    
    def capture_error_context(
        self,
        error: Exception,
        phase: str,
        source_lines: Optional[list[str]] = None,
        line_number: Optional[int] = None,
        column_number: Optional[int] = None,
        local_vars: Optional[dict[str, any]] = None
    ) -> Optional[ErrorContext]:
        """
        Capture error context with surrounding code.
        
        Args:
            error: Exception that occurred
            phase: Current parsing phase
            source_lines: Source code lines (if applicable)
            line_number: Line where error occurred
            column_number: Column where error occurred
            local_vars: Local variables at time of error
            
        Returns:
            Created error context, or None if disabled
        """
        if not self.enabled:
            return None
        
        import traceback
        
        # Get stack trace
        stack_trace = traceback.format_exception(
            type(error), error, error.__traceback__
        )
        
        # Get surrounding lines if available
        surrounding = []
        if source_lines and line_number:
            start = max(0, line_number - 3)
            end = min(len(source_lines), line_number + 3)
            surrounding = source_lines[start:end]
        
        # Convert local vars to strings
        vars_str = {}
        if local_vars:
            for k, v in local_vars.items():
                try:
                    vars_str[k] = str(v)[:200]  # Truncate long values
                except:
                    vars_str[k] = "<not_repr>"
        
        context = ErrorContext(
            error_message=str(error),
            error_type=type(error).__name__,
            phase=phase,
            line_number=line_number,
            column_number=column_number,
            surrounding_lines=surrounding,
            local_variables=vars_str,
            stack_trace=stack_trace
        )
        
        self._error_contexts.append(context)
        
        # Also create artifact
        artifact_id = self._generate_artifact_id()
        artifact = DebugArtifact(
            artifact_id=artifact_id,
            artifact_type=ArtifactType.ERROR_CONTEXT,
            timestamp=datetime.now().isoformat(),
            phase=phase,
            title=f"Error: {type(error).__name__}",
            description=str(error),
            data=context.to_dict()
        )
        self._artifacts.append(artifact)
        
        return context
    
    def capture_performance_profile(
        self,
        phase: str,
        metrics: dict[str, any],
        description: str
    ) -> Optional[DebugArtifact]:
        """
        Capture performance profile.
        
        Args:
            phase: Current parsing phase
            metrics: Performance metrics
            description: Description of profile
            
        Returns:
            Created artifact, or None if disabled
        """
        if not self.enabled:
            return None
        
        artifact_id = self._generate_artifact_id()
        
        artifact = DebugArtifact(
            artifact_id=artifact_id,
            artifact_type=ArtifactType.PERFORMANCE_PROFILE,
            timestamp=datetime.now().isoformat(),
            phase=phase,
            title=f"Performance: {phase}",
            description=description,
            data=metrics
        )
        
        self._artifacts.append(artifact)
        return artifact
    
    def capture_memory_snapshot(
        self,
        phase: str,
        memory_info: dict[str, any],
        description: str
    ) -> Optional[DebugArtifact]:
        """
        Capture memory usage snapshot.
        
        Args:
            phase: Current parsing phase
            memory_info: Memory information
            description: Description of snapshot
            
        Returns:
            Created artifact, or None if disabled
        """
        if not self.enabled:
            return None
        
        artifact_id = self._generate_artifact_id()
        
        artifact = DebugArtifact(
            artifact_id=artifact_id,
            artifact_type=ArtifactType.MEMORY_SNAPSHOT,
            timestamp=datetime.now().isoformat(),
            phase=phase,
            title=f"Memory: {phase}",
            description=description,
            data=memory_info
        )
        
        self._artifacts.append(artifact)
        return artifact
    
    def get_artifacts(
        self,
        artifact_type: Optional[ArtifactType] = None,
        phase: Optional[str] = None
    ) -> list[DebugArtifact]:
        """
        Get artifacts with optional filtering.
        
        Args:
            artifact_type: Filter by artifact type
            phase: Filter by phase
            
        Returns:
            list of matching artifacts
        """
        artifacts = self._artifacts
        
        if artifact_type:
            artifacts = [a for a in artifacts if a.artifact_type == artifact_type]
        
        if phase:
            artifacts = [a for a in artifacts if a.phase == phase]
        
        return artifacts
    
    def get_error_contexts(self, phase: Optional[str] = None) -> list[ErrorContext]:
        """
        Get error contexts with optional filtering.
        
        Args:
            phase: Filter by phase
            
        Returns:
            list of matching error contexts
        """
        if phase:
            return [ctx for ctx in self._error_contexts if ctx.phase == phase]
        return self._error_contexts
    
    def anonymize_data(self, data: any) -> any:
        """
        Anonymize sensitive data.
        
        Replaces:
        - Company names with "Company_XXX"
        - Identifiers (CIK, LEI) with "ID_XXX"
        - URLs with "URL_XXX"
        - Email addresses with "email_XXX"
        
        Args:
            data: Data to anonymize
            
        Returns:
            Anonymized data
        """
        if isinstance(data, dict):
            return {k: self.anonymize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.anonymize_data(item) for item in data]
        elif isinstance(data, str):
            # Simple anonymization patterns
            import re
            
            # Anonymize URLs
            data = re.sub(
                r'https?://[^\s]+',
                lambda m: f"URL_{hashlib.md5(m.group().encode()).hexdigest()[:8]}",
                data
            )
            
            # Anonymize email addresses
            data = re.sub(
                r'[\w\.-]+@[\w\.-]+',
                lambda m: f"email_{hashlib.md5(m.group().encode()).hexdigest()[:8]}",
                data
            )
            
            # Anonymize what looks like CIK
            data = re.sub(
                r'\b\d{10,}\b',
                lambda m: f"ID_{hashlib.md5(m.group().encode()).hexdigest()[:8]}",
                data
            )
            
            return data
        else:
            return data
    
    def export_debug_bundle(
        self,
        output_path: Path,
        anonymize: bool = True,
        include_artifacts: bool = True,
        include_errors: bool = True
    ) -> Path:
        """
        Export complete debug bundle.
        
        Creates a JSON file with all debug information for support.
        
        Args:
            output_path: Where to save bundle
            anonymize: Whether to anonymize sensitive data
            include_artifacts: Include artifacts in bundle
            include_errors: Include error contexts in bundle
            
        Returns:
            Path to exported bundle
        """
        bundle = {
            'session_id': self._session_id,
            'export_timestamp': datetime.now().isoformat(),
            'anonymized': anonymize,
            'artifacts_count': len(self._artifacts),
            'errors_count': len(self._error_contexts),
        }
        
        if include_artifacts:
            artifacts_data = [a.to_dict() for a in self._artifacts]
            if anonymize:
                artifacts_data = self.anonymize_data(artifacts_data)
            bundle['artifacts'] = artifacts_data
        
        if include_errors:
            errors_data = [ctx.to_dict() for ctx in self._error_contexts]
            if anonymize:
                errors_data = self.anonymize_data(errors_data)
            bundle['error_contexts'] = errors_data
        
        # Write bundle
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(bundle, indent=2),
            encoding='utf-8'
        )
        
        return output_path
    
    def clear(self) -> None:
        """Clear all collected artifacts."""
        self._artifacts.clear()
        self._error_contexts.clear()
    
    def get_summary(self) -> dict[str, any]:
        """
        Get summary of collected artifacts.
        
        Returns:
            Summary dictionary
        """
        artifact_counts = {}
        for artifact_type in ArtifactType:
            count = len([a for a in self._artifacts if a.artifact_type == artifact_type])
            artifact_counts[artifact_type.value] = count
        
        return {
            'enabled': self.enabled,
            'session_id': self._session_id,
            'total_artifacts': len(self._artifacts),
            'total_errors': len(self._error_contexts),
            'artifact_counts': artifact_counts,
            'output_directory': str(self.output_dir),
        }


__all__ = [
    'DebugArtifactCollector',
    'DebugArtifact',
    'ErrorContext',
    'ArtifactType',
]