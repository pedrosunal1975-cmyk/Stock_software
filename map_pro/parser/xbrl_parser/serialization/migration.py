# Path: xbrl_parser/serialization/migration.py
"""
Schema Version Migration

Migrate serialized data between schema versions.

This module provides:
- Schema version detection
- Automatic migration
- Migration validation
- Version history tracking

Example:
    from ..serialization import SchemaMigrator
    
    migrator = SchemaMigrator()
    
    # Detect schema version
    version = migrator.detect_version(data)
    
    # Migrate to current version
    migrated_data = migrator.migrate(data, target_version="1.0")
"""

import logging
from typing import Optional

from ...core.config_loader import ConfigLoader
from ..serialization.constants import (
    CURRENT_SCHEMA_VERSION,
    SUPPORTED_SCHEMA_VERSIONS,
    MIGRATION_STATUS_SUCCESS,
    MIGRATION_STATUS_FAILED,
    MIGRATION_STATUS_PARTIAL,
    MIGRATION_VERSIONS,
    MSG_MIGRATION_FAILED,
    MSG_INVALID_SCHEMA_VERSION
)


class MigrationResult:
    """
    Result of schema migration.
    
    Attributes:
        status: Migration status (success/failed/partial)
        source_version: Original schema version
        target_version: Target schema version
        errors: list of migration errors
        warnings: list of migration warnings
    """
    
    def __init__(
        self,
        status: str,
        source_version: str,
        target_version: str,
        errors: list[str] = None,
        warnings: list[str] = None
    ):
        self.status = status
        self.source_version = source_version
        self.target_version = target_version
        self.errors = errors or []
        self.warnings = warnings or []
    
    def is_success(self) -> bool:
        """Check if migration was successful."""
        return self.status == MIGRATION_STATUS_SUCCESS
    
    def has_errors(self) -> bool:
        """Check if migration had errors."""
        return len(self.errors) > 0


class SchemaMigrator:
    """
    Schema version migrator for serialized data.
    
    Handles migration between different schema versions,
    ensuring backward compatibility.
    
    Example:
        config = ConfigLoader()
        migrator = SchemaMigrator(config)
        
        # Check if migration needed
        if migrator.needs_migration(data):
            result = migrator.migrate(data)
            if result.is_success():
                print("Migration successful")
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize schema migrator.
        
        Args:
            config: Configuration loader
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger(__name__)
        
        # Current version
        self.current_version = self.config.get(
            'output_schema_version',
            CURRENT_SCHEMA_VERSION
        )
        
        # Migration functions registry
        self.migration_functions: dict[str, dict[str, Callable]] = {}
        self._register_migrations()
        
        self.logger.debug(f"SchemaMigrator initialized: version={self.current_version}")
    
    def detect_version(self, data: dict[str, any]) -> Optional[str]:
        """
        Detect schema version from data.
        
        Args:
            data: Serialized data dictionary
            
        Returns:
            Schema version string or None if not found
            
        Example:
            version = migrator.detect_version(json_data)
        """
        # Check metadata section
        if '_meta' in data:
            return data['_meta'].get('schema_version')
        
        # Check top-level
        if 'schema_version' in data:
            return data['schema_version']
        
        # Try to infer from structure
        return self._infer_version(data)
    
    def needs_migration(self, data: dict[str, any]) -> bool:
        """
        Check if data needs migration.
        
        Args:
            data: Serialized data dictionary
            
        Returns:
            True if migration is needed
        """
        version = self.detect_version(data)
        
        if not version:
            return True  # Unknown version needs migration
        
        return version != self.current_version
    
    def migrate(
        self,
        data: dict[str, any],
        target_version: Optional[str] = None
    ) -> MigrationResult:
        """
        Migrate data to target schema version.
        
        Args:
            data: Serialized data dictionary
            target_version: Target version (None = current version)
            
        Returns:
            Migration result
            
        Example:
            result = migrator.migrate(old_data)
            if result.is_success():
                migrated_data = result.data
        """
        if target_version is None:
            target_version = self.current_version
        
        try:
            # Detect source version
            source_version = self.detect_version(data)
            
            if not source_version:
                self.logger.error(MSG_INVALID_SCHEMA_VERSION)
                return MigrationResult(
                    status=MIGRATION_STATUS_FAILED,
                    source_version="unknown",
                    target_version=target_version,
                    errors=[MSG_INVALID_SCHEMA_VERSION]
                )
            
            # Check if migration needed
            if source_version == target_version:
                self.logger.debug("No migration needed")
                return MigrationResult(
                    status=MIGRATION_STATUS_SUCCESS,
                    source_version=source_version,
                    target_version=target_version
                )
            
            # Validate versions
            if source_version not in SUPPORTED_SCHEMA_VERSIONS:
                return MigrationResult(
                    status=MIGRATION_STATUS_FAILED,
                    source_version=source_version,
                    target_version=target_version,
                    errors=[f"Unsupported source version: {source_version}"]
                )
            
            # Perform migration
            self.logger.info(
                f"Migrating from {source_version} to {target_version}"
            )
            
            migrated_data, warnings = self._perform_migration(
                data,
                source_version,
                target_version
            )
            
            # Update version in data
            if '_meta' not in migrated_data:
                migrated_data['_meta'] = {}
            migrated_data['_meta']['schema_version'] = target_version
            migrated_data['_meta']['migrated_from'] = source_version
            
            self.logger.info("Migration completed successfully")
            return MigrationResult(
                status=MIGRATION_STATUS_SUCCESS,
                source_version=source_version,
                target_version=target_version,
                warnings=warnings
            )
            
        except Exception as e:
            self.logger.error(f"{MSG_MIGRATION_FAILED}: {e}", exc_info=True)
            return MigrationResult(
                status=MIGRATION_STATUS_FAILED,
                source_version=source_version if 'source_version' in locals() else "unknown",
                target_version=target_version,
                errors=[str(e)]
            )
    
    def get_version_info(self, version: str) -> Optional[dict[str, any]]:
        """
        Get information about a schema version.
        
        Args:
            version: Schema version string
            
        Returns:
            Version information dictionary
        """
        return MIGRATION_VERSIONS.get(version)
    
    def list_supported_versions(self) -> list[str]:
        """
        list all supported schema versions.
        
        Returns:
            list of version strings
        """
        return SUPPORTED_SCHEMA_VERSIONS.copy()
    
    def _register_migrations(self):
        """Register migration functions."""
        # Currently only version 1.0 exists
        # Future versions will add migration functions here
        pass
    
    def _infer_version(self, data: dict[str, any]) -> Optional[str]:
        """
        Infer schema version from data structure.
        
        Args:
            data: Serialized data
            
        Returns:
            Inferred version or None
        """
        # Check for version 1.0 structure
        if 'metadata' in data and 'instance' in data:
            return "1.0"
        
        return None
    
    def _perform_migration(
        self,
        data: dict[str, any],
        source_version: str,
        target_version: str
    ) -> tuple:
        """
        Perform actual migration.
        
        Args:
            data: Data to migrate
            source_version: Source version
            target_version: Target version
            
        Returns:
            tuple of (migrated_data, warnings)
        """
        warnings = []
        
        # For now, 1.0 is the only version
        # Future: implement migration path logic here
        
        # Example migration path logic:
        # if source_version == "1.0" and target_version == "2.0":
        #     data = self._migrate_1_0_to_2_0(data)
        
        return data, warnings


__all__ = ['SchemaMigrator', 'MigrationResult']
