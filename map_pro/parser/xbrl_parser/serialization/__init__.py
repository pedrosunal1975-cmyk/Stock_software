# Path: xbrl_parser/serialization/__init__.py
"""
Serialization Module

Components for serializing XBRL parsed data.

This module provides:
- JSON serialization (full, compact, debug, anonymized)
- Checkpoint system (save/resume parsing state)
- Schema migration (version compatibility)
- Constants (formats, versions, settings)

Example:
    from ..serialization import (
        JSONSerializer,
        CheckpointManager,
        SchemaMigrator
    )
    
    # Serialize to JSON
    serializer = JSONSerializer()
    json_str = serializer.serialize(parsed_filing)
    serializer.save(parsed_filing, "output.json")
    
    # Use checkpoints
    checkpoint_mgr = CheckpointManager()
    if checkpoint_mgr.should_checkpoint(fact_count):
        checkpoint_mgr.save(filing, phase="extraction")
    
    # Migrate schema versions
    migrator = SchemaMigrator()
    if migrator.needs_migration(data):
        result = migrator.migrate(data)
"""

from ..serialization.json_serializer import (
    JSONSerializer,
    JSONEncoder
)
from ..serialization.checkpoint import CheckpointManager
from ..serialization.migration import (
    SchemaMigrator,
    MigrationResult
)
from ..serialization import constants


__all__ = [
    # JSON Serialization
    'JSONSerializer',
    'JSONEncoder',
    
    # Checkpoints
    'CheckpointManager',
    
    # Migration
    'SchemaMigrator',
    'MigrationResult',
    
    # Constants
    'constants'
]
