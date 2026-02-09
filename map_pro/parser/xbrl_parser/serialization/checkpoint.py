# Path: xbrl_parser/serialization/checkpoint.py
"""
Checkpoint System

Save and resume parsing state for large or long-running operations.

This module provides:
- Checkpoint creation
- State save/load
- Checkpoint management
- Automatic cleanup

Example:
    from ..serialization import CheckpointManager
    
    manager = CheckpointManager()
    
    # Save checkpoint
    checkpoint_path = manager.save(filing, phase="extraction")
    
    # Load checkpoint
    filing = manager.load(checkpoint_path)
    
    # Clean old checkpoints
    manager.cleanup_old()
"""

import json
import logging
import pickle
import gzip
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta

from ...core.config_loader import ConfigLoader
from ..models.parsed_filing import ParsedFiling
from ..serialization.constants import (
    CHECKPOINT_EXTENSION,
    CHECKPOINT_VERSION,
    CHECKPOINT_COMPRESS,
    MAX_CHECKPOINT_AGE,
    MAX_CHECKPOINT_SIZE,
    CHECKPOINT_FILENAME_PATTERN,
    FILENAME_TIMESTAMP_FORMAT,
    MSG_CHECKPOINT_SAVE_FAILED,
    MSG_CHECKPOINT_LOAD_FAILED
)


class CheckpointManager:
    """
    Manage parsing checkpoints for resumable operations.
    
    Checkpoints allow long-running parsing to be interrupted
    and resumed from the last saved state.
    
    Example:
        config = ConfigLoader()
        manager = CheckpointManager(config)
        
        # During parsing - save checkpoint
        if fact_count % 5000 == 0:
            manager.save(filing, phase="facts", progress=fact_count)
        
        # Resume from checkpoint
        if checkpoint_exists:
            filing = manager.load(checkpoint_path)
    """
    
    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize checkpoint manager.
        
        Args:
            config: Configuration loader
        """
        self.config = config or ConfigLoader()
        self.logger = logging.getLogger(__name__)
        
        # Get configuration
        self.enabled = self.config.get('enable_checkpoints', True)
        self.checkpoint_dir = Path(self.config.get('temp_checkpoints_dir'))
        self.interval = self.config.get('checkpoint_interval', 5000)
        
        # Ensure directory exists
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.debug(
            f"CheckpointManager initialized: enabled={self.enabled}, "
            f"interval={self.interval}"
        )
    
    def should_checkpoint(self, count: int) -> bool:
        """
        Determine if checkpoint should be created.
        
        Args:
            count: Current item count (e.g., facts processed)
            
        Returns:
            True if checkpoint should be created
        """
        if not self.enabled:
            return False
        
        return count > 0 and count % self.interval == 0
    
    def save(
        self,
        filing: ParsedFiling,
        phase: str,
        progress: Optional[dict[str, any]] = None
    ) -> Path:
        """
        Save checkpoint.
        
        Args:
            filing: Current parsed filing state
            phase: Current parsing phase (e.g., "extraction", "validation")
            progress: Optional progress information
            
        Returns:
            Path to checkpoint file
            
        Example:
            checkpoint = manager.save(
                filing,
                phase="extraction",
                progress={'facts_processed': 10000}
            )
        """
        if not self.enabled:
            self.logger.debug("Checkpointing disabled")
            return None
        
        try:
            # Generate filename
            timestamp = datetime.now().strftime(FILENAME_TIMESTAMP_FORMAT)
            filing_id = getattr(filing.metadata, 'filing_id', 'unknown')
            filename = f"{filing_id}_checkpoint_{phase}_{timestamp}{CHECKPOINT_EXTENSION}"
            checkpoint_path = self.checkpoint_dir / filename
            
            # Build checkpoint data
            checkpoint_data = {
                'version': CHECKPOINT_VERSION,
                'timestamp': datetime.now().isoformat(),
                'phase': phase,
                'progress': progress or {},
                'filing': self._serialize_filing(filing)
            }
            
            # Save checkpoint
            if CHECKPOINT_COMPRESS:
                with gzip.open(checkpoint_path, 'wb') as f:
                    pickle.dump(checkpoint_data, f)
            else:
                with open(checkpoint_path, 'wb') as f:
                    pickle.dump(checkpoint_data, f)
            
            # Check size
            size = checkpoint_path.stat().st_size
            if size > MAX_CHECKPOINT_SIZE:
                self.logger.warning(
                    f"Checkpoint size exceeds maximum: {size / 1024 / 1024:.1f}MB"
                )
            
            self.logger.info(
                f"Checkpoint saved: {checkpoint_path.name} "
                f"({size / 1024:.1f}KB, phase={phase})"
            )
            
            return checkpoint_path
            
        except Exception as e:
            self.logger.error(f"{MSG_CHECKPOINT_SAVE_FAILED}: {e}", exc_info=True)
            raise
    
    def load(self, checkpoint_path: Path) -> ParsedFiling:
        """
        Load checkpoint.
        
        Args:
            checkpoint_path: Path to checkpoint file
            
        Returns:
            Restored parsed filing
            
        Example:
            filing = manager.load(Path("checkpoint.checkpoint"))
        """
        try:
            self.logger.info(f"Loading checkpoint: {checkpoint_path}")
            
            # Load checkpoint data
            if checkpoint_path.suffix == '.gz' or CHECKPOINT_COMPRESS:
                with gzip.open(checkpoint_path, 'rb') as f:
                    checkpoint_data = pickle.load(f)
            else:
                with open(checkpoint_path, 'rb') as f:
                    checkpoint_data = pickle.load(f)
            
            # Validate version
            version = checkpoint_data.get('version', '0.0')
            if version != CHECKPOINT_VERSION:
                self.logger.warning(
                    f"Checkpoint version mismatch: {version} != {CHECKPOINT_VERSION}"
                )
            
            # Restore filing
            filing = self._deserialize_filing(checkpoint_data['filing'])
            
            # Log progress info
            phase = checkpoint_data.get('phase', 'unknown')
            progress = checkpoint_data.get('progress', {})
            self.logger.info(
                f"Checkpoint loaded: phase={phase}, progress={progress}"
            )
            
            return filing
            
        except Exception as e:
            self.logger.error(f"{MSG_CHECKPOINT_LOAD_FAILED}: {e}", exc_info=True)
            raise
    
    def list_checkpoints(
        self,
        filing_id: Optional[str] = None
    ) -> list[Path]:
        """
        list available checkpoints.
        
        Args:
            filing_id: Optional filing ID to filter by
            
        Returns:
            list of checkpoint paths
        """
        pattern = f"*{CHECKPOINT_EXTENSION}"
        if filing_id:
            pattern = f"{filing_id}_*{CHECKPOINT_EXTENSION}"
        
        checkpoints = sorted(
            self.checkpoint_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        return checkpoints
    
    def cleanup_old(self, max_age_seconds: int = None) -> int:
        """
        Clean up old checkpoints.
        
        Args:
            max_age_seconds: Maximum age in seconds (None = use default)
            
        Returns:
            Number of checkpoints deleted
        """
        if max_age_seconds is None:
            max_age_seconds = MAX_CHECKPOINT_AGE
        
        cutoff_time = datetime.now() - timedelta(seconds=max_age_seconds)
        deleted = 0
        
        for checkpoint_path in self.checkpoint_dir.glob(f"*{CHECKPOINT_EXTENSION}"):
            mtime = datetime.fromtimestamp(checkpoint_path.stat().st_mtime)
            
            if mtime < cutoff_time:
                try:
                    checkpoint_path.unlink()
                    deleted += 1
                    self.logger.debug(f"Deleted old checkpoint: {checkpoint_path.name}")
                except Exception as e:
                    self.logger.error(f"Failed to delete {checkpoint_path}: {e}")
        
        if deleted > 0:
            self.logger.info(f"Cleaned up {deleted} old checkpoints")
        
        return deleted
    
    def delete(self, checkpoint_path: Path) -> bool:
        """
        Delete specific checkpoint.
        
        Args:
            checkpoint_path: Path to checkpoint to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            if checkpoint_path.exists():
                checkpoint_path.unlink()
                self.logger.debug(f"Deleted checkpoint: {checkpoint_path.name}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete checkpoint: {e}")
            return False
    
    def _serialize_filing(self, filing: ParsedFiling) -> bytes:
        """Serialize filing for checkpoint."""
        return pickle.dumps(filing)
    
    def _deserialize_filing(self, data: bytes) -> ParsedFiling:
        """Deserialize filing from checkpoint."""
        return pickle.loads(data)


__all__ = ['CheckpointManager']
