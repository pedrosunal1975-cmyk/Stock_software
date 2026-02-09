# Path: xbrl_parser/foundation/taxonomy_cache.py
"""
SQLite-Based Taxonomy Cache

Fast, persistent caching for taxonomy files with LRU eviction.

Features:
- Fast lookups by namespace/version/schema
- Size-based eviction (LRU)
- Access statistics
- Cache invalidation
"""

from pathlib import Path
from typing import Optional
from datetime import datetime
import hashlib
import json
import sqlite3
import logging


class TaxonomyCache:
    """
    SQLite-based taxonomy cache.
    
    Features:
    - Fast lookups by namespace/version/schema
    - Size-based eviction (LRU)
    - Access statistics
    - Cache invalidation
    
    Example:
        cache = TaxonomyCache(cache_dir)
        
        # Try to get from cache
        result = cache.get(namespace, version, schema_location)
        if result:
            content, metadata = result
        else:
            # Fetch and cache
            content = fetch_taxonomy()
            cache.put(namespace, version, schema_location, content, metadata)
    """
    
    def __init__(self, cache_dir: Path, max_size_mb: int = 1024):
        """
        Initialize taxonomy cache.
        
        Args:
            cache_dir: Directory for cache database
            max_size_mb: Maximum cache size in MB (default: 1024)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "taxonomy_cache.db"
        self.max_size_mb = max_size_mb
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self._init_db()
        
        # Statistics
        self.hits = 0
        self.misses = 0
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(str(self.db_path))
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS taxonomy_cache (
                cache_key TEXT PRIMARY KEY,
                namespace TEXT NOT NULL,
                version TEXT,
                schema_location TEXT NOT NULL,
                content BLOB NOT NULL,
                content_hash TEXT NOT NULL,
                metadata TEXT,
                fetch_time TIMESTAMP NOT NULL,
                last_accessed TIMESTAMP NOT NULL,
                access_count INTEGER DEFAULT 1,
                size_bytes INTEGER NOT NULL
            )
        """)
        
        conn.execute("CREATE INDEX IF NOT EXISTS idx_namespace ON taxonomy_cache(namespace)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_version ON taxonomy_cache(version)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_last_accessed ON taxonomy_cache(last_accessed)")
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache_stats (
                stat_date DATE PRIMARY KEY,
                hits INTEGER DEFAULT 0,
                misses INTEGER DEFAULT 0,
                evictions INTEGER DEFAULT 0,
                size_mb REAL DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _generate_cache_key(self, namespace: str, version: Optional[str], schema_location: str) -> str:
        """Generate cache key from taxonomy identifiers."""
        key_parts = [namespace]
        if version:
            key_parts.append(version)
        key_parts.append(schema_location)
        
        key_string = '|'.join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def get(self, namespace: str, version: Optional[str], schema_location: str) -> Optional[tuple[bytes, dict]]:
        """
        Get cached taxonomy.
        
        Args:
            namespace: Taxonomy namespace
            version: Taxonomy version (optional)
            schema_location: Schema location
            
        Returns:
            tuple of (content, metadata) or None if not cached
        """
        cache_key = self._generate_cache_key(namespace, version, schema_location)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT content, metadata, fetch_time
            FROM taxonomy_cache
            WHERE cache_key = ?
        """, (cache_key,))
        
        row = cursor.fetchone()
        
        if row:
            # Cache hit
            content, metadata_json, fetch_time = row
            metadata = json.loads(metadata_json) if metadata_json else {}
            
            # Update access statistics
            cursor.execute("""
                UPDATE taxonomy_cache
                SET last_accessed = ?, access_count = access_count + 1
                WHERE cache_key = ?
            """, (datetime.now().isoformat(), cache_key))
            
            conn.commit()
            
            self.hits += 1
            
            self.logger.debug(
                f"Cache hit: {namespace} v{version} ({cache_key[:8]})"
            )
            
            conn.close()
            return content, metadata
        else:
            # Cache miss
            self.misses += 1
            
            self.logger.debug(f"Cache miss: {namespace} v{version}")
            
            conn.close()
            return None
    
    def put(self, namespace: str, version: Optional[str], schema_location: str,
            content: bytes, metadata: dict):
        """
        Store taxonomy in cache.
        
        Args:
            namespace: Taxonomy namespace
            version: Taxonomy version (optional)
            schema_location: Schema location
            content: Taxonomy content
            metadata: Fetch metadata
        """
        cache_key = self._generate_cache_key(namespace, version, schema_location)
        content_hash = hashlib.sha256(content).hexdigest()
        
        # Check if we need to evict old entries
        self._enforce_size_limit(len(content))
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO taxonomy_cache
            (cache_key, namespace, version, schema_location, content, content_hash,
             metadata, fetch_time, last_accessed, size_bytes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cache_key,
            namespace,
            version or '',
            schema_location,
            content,
            content_hash,
            json.dumps(metadata),
            now,
            now,
            len(content)
        ))
        
        conn.commit()
        conn.close()
        
        self.logger.debug(
            f"Cached taxonomy: {namespace} v{version} ({len(content)} bytes, key={cache_key[:8]})"
        )
    
    def _enforce_size_limit(self, new_entry_size: int):
        """Evict old entries if cache would exceed size limit."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get current cache size
        cursor.execute("SELECT SUM(size_bytes) FROM taxonomy_cache")
        current_size = cursor.fetchone()[0] or 0
        current_size_mb = current_size / (1024 * 1024)
        new_size_mb = (current_size + new_entry_size) / (1024 * 1024)
        
        if new_size_mb > self.max_size_mb:
            # Need to evict
            bytes_to_evict = (new_size_mb - self.max_size_mb) * 1024 * 1024
            
            # Evict least recently accessed entries
            cursor.execute("""
                SELECT cache_key, size_bytes
                FROM taxonomy_cache
                ORDER BY last_accessed ASC
            """)
            
            bytes_evicted = 0
            evicted_count = 0
            
            for cache_key, size_bytes in cursor.fetchall():
                if bytes_evicted >= bytes_to_evict:
                    break
                
                cursor.execute("DELETE FROM taxonomy_cache WHERE cache_key = ?", (cache_key,))
                bytes_evicted += size_bytes
                evicted_count += 1
            
            conn.commit()
            
            self.logger.info(
                f"Cache eviction: {evicted_count} entries ({bytes_evicted / (1024 * 1024):.2f} MB)"
            )
        
        conn.close()
    
    def invalidate(self, namespace: Optional[str] = None):
        """
        Invalidate cache entries.
        
        Args:
            namespace: If provided, only invalidate this namespace. Otherwise, clear all.
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        if namespace:
            cursor.execute("DELETE FROM taxonomy_cache WHERE namespace = ?", (namespace,))
            self.logger.info(f"Invalidated cache for namespace: {namespace}")
        else:
            cursor.execute("DELETE FROM taxonomy_cache")
            self.logger.info("Cleared entire cache")
        
        conn.commit()
        conn.close()
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as entry_count,
                SUM(size_bytes) as total_size,
                AVG(access_count) as avg_access_count,
                MAX(last_accessed) as most_recent_access
            FROM taxonomy_cache
        """)
        
        row = cursor.fetchone()
        entry_count, total_size, avg_access_count, most_recent_access = row
        
        conn.close()
        
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        
        return {
            'entries': entry_count or 0,
            'size_mb': (total_size or 0) / (1024 * 1024),
            'avg_access_count': avg_access_count or 0,
            'most_recent_access': most_recent_access,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate
        }


__all__ = ['TaxonomyCache']