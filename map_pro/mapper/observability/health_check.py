# Path: observability/health_check.py
"""
Health Check

Monitors system health and dependencies.
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from ..core.config_loader import ConfigLoader
from ..core.data_paths import DataPathsManager


class HealthStatus:
    """Health check status."""
    
    def __init__(self):
        self.is_healthy = True
        self.checks = {}
        self.warnings = []
        self.errors = []
        self.timestamp = datetime.utcnow()
    
    def add_check(self, name: str, passed: bool, message: str = ""):
        """Add check result."""
        self.checks[name] = {
            'passed': passed,
            'message': message
        }
        if not passed:
            self.is_healthy = False
            self.errors.append(f"{name}: {message}")
    
    def add_warning(self, message: str):
        """Add warning."""
        self.warnings.append(message)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'is_healthy': self.is_healthy,
            'timestamp': self.timestamp.isoformat(),
            'checks': self.checks,
            'warnings': self.warnings,
            'errors': self.errors
        }


class HealthCheck:
    """
    System health checker.
    
    Validates:
    - Configuration loaded
    - Required directories exist
    - Dependencies available
    - Loaders functional
    
    Example:
        checker = HealthCheck()
        status = checker.check_all()
        
        if status.is_healthy:
            print("System healthy")
        else:
            print(f"Errors: {status.errors}")
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """Initialize health checker."""
        self.logger = logging.getLogger('observability.health_check')
        self.config = config if config else ConfigLoader()
    
    def check_all(self) -> HealthStatus:
        """
        Run all health checks.
        
        Returns:
            HealthStatus with results
        """
        status = HealthStatus()
        
        # Check configuration
        self._check_configuration(status)
        
        # Check directories
        self._check_directories(status)
        
        # Check dependencies
        self._check_dependencies(status)
        
        # Check data access
        self._check_data_access(status)
        
        return status
    
    def _check_configuration(self, status: HealthStatus):
        """Check configuration loaded."""
        try:
            # Verify critical config keys
            required_keys = [
                'output_mapped_dir',
                'parser_output_dir',
                'log_dir'
            ]
            
            missing = []
            for key in required_keys:
                try:
                    value = self.config.get(key)
                    if not value:
                        missing.append(key)
                except Exception:
                    missing.append(key)
            
            if missing:
                status.add_check(
                    'configuration',
                    False,
                    f"Missing config keys: {missing}"
                )
            else:
                status.add_check('configuration', True, "All required keys present")
        
        except Exception as e:
            status.add_check('configuration', False, str(e))
    
    def _check_directories(self, status: HealthStatus):
        """Check required directories exist."""
        try:
            manager = DataPathsManager(self.config)
            result = manager.ensure_all_directories()
            
            # Check if all directories exist
            if result['created']:
                status.add_warning(
                    f"Created {len(result['created'])} missing directories"
                )
            
            status.add_check(
                'directories',
                True,
                f"{len(result['existing'])} directories verified"
            )
        
        except Exception as e:
            status.add_check('directories', False, str(e))
    
    def _check_dependencies(self, status: HealthStatus):
        """Check Python dependencies."""
        try:
            # Check critical imports
            critical = [
                'lxml',
                'pydantic',
                'yaml'
            ]
            
            missing = []
            for module in critical:
                try:
                    __import__(module)
                except ImportError:
                    missing.append(module)
            
            # Check optional dependencies
            optional = ['openpyxl', 'pandas']
            missing_optional = []
            for module in optional:
                try:
                    __import__(module)
                except ImportError:
                    missing_optional.append(module)
            
            if missing:
                status.add_check(
                    'dependencies',
                    False,
                    f"Missing critical: {missing}"
                )
            else:
                status.add_check(
                    'dependencies',
                    True,
                    "All critical dependencies available"
                )
            
            if missing_optional:
                status.add_warning(
                    f"Optional dependencies missing: {missing_optional}"
                )
        
        except Exception as e:
            status.add_check('dependencies', False, str(e))
    
    def _check_data_access(self, status: HealthStatus):
        """Check data access."""
        try:
            from ..loaders.parsed_data import ParsedDataLoader
            
            loader = ParsedDataLoader(self.config)
            
            # Check if parser output directory exists and is readable
            parser_output = self.config.get('parser_output_dir')
            
            if not parser_output.exists():
                status.add_check(
                    'data_access',
                    False,
                    f"Parser output directory not found: {parser_output}"
                )
            elif not any(parser_output.iterdir()):
                status.add_warning("Parser output directory is empty")
                status.add_check('data_access', True, "Directory accessible but empty")
            else:
                # Count available filings
                filings = loader.discover_all_parsed_filings()
                status.add_check(
                    'data_access',
                    True,
                    f"{len(filings)} parsed filings available"
                )
        
        except Exception as e:
            status.add_check('data_access', False, str(e))


__all__ = ['HealthCheck', 'HealthStatus']
