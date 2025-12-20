"""Cleanup utility for managing temporary files and signal handling.

This module provides robust cleanup functionality to ensure temporary
files are removed on success, failure, or interrupt (Ctrl+C). This is
critical for preventing disk space leaks from downloaded videos and
intermediate processing files.

Key Features:
    - CleanupContext: Track and clean up temporary files
    - Signal handlers: Graceful cleanup on SIGINT/SIGTERM
    - Skip cleanup option: For debugging with --keep-temp
    - Context manager support: Automatic cleanup on scope exit

Usage:
    # Basic usage with context manager
    with CleanupContext() as cleanup:
        cleanup.register("/tmp/video.mp4")
        cleanup.register("/tmp/subtitle.ass")
        # Files are automatically cleaned up on exit
    
    # Global cleanup context
    cleanup = setup_cleanup_context(skip_cleanup=False)
    setup_signal_handlers(cleanup)
    
    # Register files for cleanup
    register_temp_file("/tmp/downloaded.mp4")
"""

import atexit
import os
import signal
import sys
from pathlib import Path
from typing import Callable

from src.utils.logger import get_logger


class CleanupContext:
    """Context manager for tracking and cleaning up temporary files.
    
    Provides a way to register temporary files that should be cleaned up
    on success, failure, or interrupt (Ctrl+C). Supports skipping cleanup
    for debugging purposes via --keep-temp flag.
    
    Example:
        cleanup = CleanupContext()
        cleanup.register("/tmp/video.mp4")
        cleanup.register("/tmp/subtitle.ass")
        
        # On exit or error:
        removed = cleanup.cleanup()
    """
    
    def __init__(self):
        """Initialize the cleanup context."""
        self._files: list[str] = []
        self._skip_cleanup: bool = False
        self._cleaned: bool = False
    
    def register(self, path: str) -> None:
        """Register a file or directory for cleanup.
        
        Args:
            path: Path to the file or directory to clean up
        """
        if path and path not in self._files:
            self._files.append(path)
    
    def unregister(self, path: str) -> None:
        """Remove a file from the cleanup list.
        
        Useful when a temp file becomes a permanent output.
        
        Args:
            path: Path to remove from cleanup list
        """
        if path in self._files:
            self._files.remove(path)
    
    def cleanup(self) -> list[str]:
        """Remove all registered files and directories.
        
        Iterates through all registered paths and removes them.
        Handles both files and directories (recursively).
        Logs debug messages for each removal.
        
        Returns:
            List of paths that were successfully removed
        """
        # Prevent double cleanup (important for signal handlers + atexit)
        if self._cleaned:
            return []
        
        # Honor --keep-temp flag for debugging
        if self._skip_cleanup:
            logger = get_logger()
            logger.debug(f"Skipping cleanup of {len(self._files)} temp files (--keep-temp)")
            return []
        
        removed: list[str] = []
        logger = get_logger()
        
        for path in self._files:
            try:
                p = Path(path)
                if p.exists():
                    if p.is_file():
                        p.unlink()
                        removed.append(path)
                        logger.debug(f"Removed temp file: {path}")
                    elif p.is_dir():
                        # Remove directory and all contents recursively
                        import shutil
                        shutil.rmtree(path)
                        removed.append(path)
                        logger.debug(f"Removed temp directory: {path}")
            except OSError as e:
                # Log but don't fail - cleanup is best-effort
                logger.debug(f"Failed to remove {path}: {e}")
        
        self._files.clear()
        self._cleaned = True
        return removed
    
    def set_skip(self, skip: bool) -> None:
        """Set whether to skip cleanup.
        
        Args:
            skip: If True, cleanup() will not remove files
        """
        self._skip_cleanup = skip
    
    @property
    def files(self) -> list[str]:
        """Get list of registered files.
        
        Returns:
            Copy of the list of registered file paths
        """
        return self._files.copy()
    
    def __len__(self) -> int:
        """Return number of registered files."""
        return len(self._files)
    
    def __enter__(self) -> "CleanupContext":
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager, performing cleanup."""
        self.cleanup()


# Global cleanup context
_cleanup_context: CleanupContext | None = None


def get_cleanup_context() -> CleanupContext:
    """Get the global cleanup context.
    
    Returns:
        The global CleanupContext instance
    """
    global _cleanup_context
    if _cleanup_context is None:
        _cleanup_context = CleanupContext()
    return _cleanup_context


def setup_cleanup_context(skip_cleanup: bool = False) -> CleanupContext:
    """Setup and return the global cleanup context.
    
    Args:
        skip_cleanup: If True, cleanup will be skipped (--keep-temp)
        
    Returns:
        The configured CleanupContext instance
    """
    global _cleanup_context
    _cleanup_context = CleanupContext()
    _cleanup_context.set_skip(skip_cleanup)
    return _cleanup_context


def setup_signal_handlers(cleanup_ctx: CleanupContext | None = None) -> None:
    """Setup signal handlers for graceful cleanup on interrupt.
    
    Registers handlers for SIGINT (Ctrl+C) and SIGTERM to ensure
    temporary files are cleaned up even when the process is interrupted.
    Also registers cleanup on normal exit via atexit.
    
    This is critical for preventing orphaned temp files when users
    cancel long-running operations like video downloads or rendering.
    
    Args:
        cleanup_ctx: CleanupContext to use, or None to use global context
    
    Note:
        Exit codes follow Unix conventions:
        - 130 for SIGINT (128 + signal number 2)
        - 143 for SIGTERM (128 + signal number 15)
    """
    ctx = cleanup_ctx or get_cleanup_context()
    
    def signal_handler(signum: int, frame) -> None:
        """Handle interrupt signals by cleaning up and exiting."""
        logger = get_logger()
        
        # Map signal number to name for user-friendly message
        signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        logger.warning(f"\nReceived {signal_name}, cleaning up...")
        
        ctx.cleanup()
        
        # Exit with standard Unix interrupt codes
        exit_code = 130 if signum == signal.SIGINT else 143
        sys.exit(exit_code)
    
    # Register signal handlers for graceful interrupt handling
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Also register cleanup on normal exit (belt and suspenders)
    atexit.register(ctx.cleanup)


def register_temp_file(path: str) -> None:
    """Convenience function to register a temp file with global context.
    
    Args:
        path: Path to the temporary file
    """
    get_cleanup_context().register(path)


def unregister_temp_file(path: str) -> None:
    """Convenience function to unregister a temp file from global context.
    
    Args:
        path: Path to remove from cleanup list
    """
    get_cleanup_context().unregister(path)


__all__ = [
    "CleanupContext",
    "get_cleanup_context",
    "setup_cleanup_context",
    "setup_signal_handlers",
    "register_temp_file",
    "unregister_temp_file",
]
