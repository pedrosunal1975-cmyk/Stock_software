# Path: mat_acc/database/integration/__init__.py
"""
Database Integration Layer

Connects the hierarchy builder with database storage.
Provides methods to build hierarchies and store them automatically.
"""

from database.integration.hierarchy_storage import HierarchyStorage

__all__ = ['HierarchyStorage']
