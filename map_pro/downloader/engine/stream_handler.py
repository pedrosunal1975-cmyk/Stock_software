# Path: downloader/engine/stream_handler.py
"""
Stream Handler

Memory-efficient streaming for large file downloads.
Writes directly to disk without loading entire file into memory.

Architecture:
- Chunk-based streaming (8KB default)
- Progress tracking
- Resume capability support
- Async I/O for efficiency
"""

import asyncio
from pathlib import Path
from typing import Optional, AsyncIterator, BinaryIO
import aiofiles

from downloader.core.logger import get_logger
from downloader.core.config_loader import ConfigLoader
from downloader.constants import (
    DEFAULT_CHUNK_SIZE,
    LOG_PROCESS,
)

logger = get_logger(__name__, 'engine')


class StreamHandler:
    """
    Handles streaming download to disk.
    
    Features:
    - Memory-efficient chunk-based writing
    - Progress tracking
    - Async file I/O
    - Resume support (partial downloads)
    
    Example:
        handler = StreamHandler(chunk_size=8192)
        
        async for chunk in response_stream:
            await handler.write_chunk(file_handle, chunk)
            progress = handler.get_progress()
    """
    
    def __init__(
        self,
        chunk_size: Optional[int] = None,
        config: Optional[ConfigLoader] = None
    ):
        """
        Initialize stream handler.
        
        Args:
            chunk_size: Size of chunks to read/write (bytes)
            config: Optional ConfigLoader instance
        """
        self.config = config if config else ConfigLoader()
        
        self.chunk_size = chunk_size if chunk_size is not None else \
            self.config.get('chunk_size', DEFAULT_CHUNK_SIZE)
        
        self.bytes_written = 0
        self.chunks_written = 0
    
    async def stream_to_file(
        self,
        response_stream: AsyncIterator[bytes],
        output_path: Path,
        total_size: Optional[int] = None,
        resume_from: int = 0
    ) -> int:
        """
        Stream response to file.
        
        Args:
            response_stream: Async iterator of byte chunks
            output_path: Path where file will be written
            total_size: Total expected size (for progress)
            resume_from: Byte offset to resume from
            
        Returns:
            Total bytes written
        """
        logger.info(f"{LOG_PROCESS} Streaming to: {output_path.name}")
        
        # Determine write mode
        mode = 'ab' if resume_from > 0 else 'wb'
        
        self.bytes_written = resume_from
        self.chunks_written = 0
        
        try:
            async with aiofiles.open(output_path, mode) as f:
                async for chunk in response_stream:
                    if chunk:
                        await f.write(chunk)
                        self.bytes_written += len(chunk)
                        self.chunks_written += 1
                        
                        # Log progress periodically
                        if self.chunks_written % 100 == 0:
                            if total_size:
                                progress = (self.bytes_written / total_size) * 100
                                logger.debug(
                                    f"{LOG_PROCESS} Progress: {progress:.1f}% "
                                    f"({self.bytes_written}/{total_size} bytes)"
                                )
                            else:
                                logger.debug(
                                    f"{LOG_PROCESS} Downloaded: {self.bytes_written} bytes"
                                )
        
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            raise
        
        logger.info(
            f"{LOG_PROCESS} Stream complete: {self.bytes_written} bytes "
            f"in {self.chunks_written} chunks"
        )
        
        return self.bytes_written
    
    async def write_chunk(
        self,
        file_handle: BinaryIO,
        chunk: bytes
    ) -> int:
        """
        Write single chunk to file.
        
        Args:
            file_handle: Open file handle
            chunk: Bytes to write
            
        Returns:
            Number of bytes written
        """
        bytes_written = await file_handle.write(chunk)
        self.bytes_written += bytes_written
        self.chunks_written += 1
        
        return bytes_written
    
    def get_progress(self, total_size: Optional[int] = None) -> dict:
        """
        Get current progress statistics.
        
        Args:
            total_size: Total expected size (optional)
            
        Returns:
            Dictionary with progress stats
        """
        progress = {
            'bytes_written': self.bytes_written,
            'chunks_written': self.chunks_written,
            'mb_written': self.bytes_written / (1024 * 1024),
        }
        
        if total_size:
            progress['percent_complete'] = (self.bytes_written / total_size) * 100
            progress['bytes_remaining'] = total_size - self.bytes_written
        
        return progress
    
    def reset(self):
        """Reset progress counters."""
        self.bytes_written = 0
        self.chunks_written = 0


class ChunkIterator:
    """
    Async iterator for reading file in chunks.
    
    Used for streaming uploads or processing large files.
    
    Example:
        async for chunk in ChunkIterator(file_path, chunk_size=8192):
            process_chunk(chunk)
    """
    
    def __init__(self, file_path: Path, chunk_size: int = DEFAULT_CHUNK_SIZE):
        """
        Initialize chunk iterator.
        
        Args:
            file_path: Path to file to read
            chunk_size: Size of chunks to read
        """
        self.file_path = file_path
        self.chunk_size = chunk_size
        self._file_handle = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._file_handle = await aiofiles.open(self.file_path, 'rb')
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._file_handle:
            await self._file_handle.close()
    
    async def __aiter__(self):
        """Async iterator."""
        return self
    
    async def __anext__(self) -> bytes:
        """Read next chunk."""
        if not self._file_handle:
            raise RuntimeError("File not opened. Use async context manager.")
        
        chunk = await self._file_handle.read(self.chunk_size)
        
        if not chunk:
            raise StopAsyncIteration
        
        return chunk


__all__ = ['StreamHandler', 'ChunkIterator']