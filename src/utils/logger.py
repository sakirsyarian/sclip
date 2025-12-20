"""Logger utility for SmartClip AI with rich console output.

This module provides a centralized logging system with rich formatting
support for consistent, user-friendly console output throughout the
application.

Features:
    - Styled log levels (info, success, warning, error, debug)
    - Spinner animations for async operations
    - Progress bars for long-running tasks
    - Formatted boxes for structured output (dry-run results)
    - Verbose/quiet mode support
    - Global logger instance with setup function

Usage:
    from src.utils.logger import setup_logger, get_logger
    
    # Setup at application start
    logger = setup_logger(verbose=True, quiet=False)
    
    # Use throughout the application
    logger = get_logger()
    logger.info("Processing video...")
    logger.success("Done!")
    
    # Spinner for async operations
    with logger.spinner("Uploading...") as status:
        do_upload()
        status.update("Almost done...")
    
    # Progress bar for iterations
    with logger.progress(100, "Rendering") as progress:
        for i in range(100):
            do_step()
            progress.advance(progress.task_id)
"""

from contextlib import contextmanager
from typing import Generator

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.status import Status
from rich.theme import Theme


# Custom theme for consistent styling across the application
# Maps semantic names to rich style strings for easy customization
SCLIP_THEME = Theme({
    "info": "cyan",           # Informational messages
    "success": "green",       # Success/completion messages
    "warning": "yellow",      # Warning messages (non-fatal issues)
    "error": "red bold",      # Error messages (always shown)
    "debug": "dim",           # Debug messages (verbose mode only)
})


class Logger:
    """Console logger with rich formatting support.
    
    Provides styled console output with support for:
    - Different log levels (info, success, warning, error, debug)
    - Spinners for async operations
    - Progress bars for long-running tasks
    - Formatted boxes for structured output
    """
    
    def __init__(self, verbose: bool = False, quiet: bool = False):
        """Initialize logger with verbosity settings.
        
        Args:
            verbose: If True, show debug messages
            quiet: If True, suppress all output except errors
        """
        self._verbose = verbose
        self._quiet = quiet
        self._console = Console(theme=SCLIP_THEME)
        self._err_console = Console(theme=SCLIP_THEME, stderr=True)
    
    @property
    def console(self) -> Console:
        """Get the underlying rich Console instance."""
        return self._console
    
    def info(self, message: str) -> None:
        """Print an info message.
        
        Args:
            message: The message to display
        """
        if not self._quiet:
            self._console.print(f"[info]ℹ[/info] {message}")
    
    def success(self, message: str) -> None:
        """Print a success message.
        
        Args:
            message: The message to display
        """
        if not self._quiet:
            self._console.print(f"[success]✓[/success] {message}")
    
    def warning(self, message: str) -> None:
        """Print a warning message.
        
        Args:
            message: The message to display
        """
        if not self._quiet:
            self._console.print(f"[warning]⚠[/warning] {message}")
    
    def error(self, message: str) -> None:
        """Print an error message (always shown, even in quiet mode).
        
        Args:
            message: The message to display
        """
        self._err_console.print(f"[error]✗[/error] {message}")
    
    def debug(self, message: str) -> None:
        """Print a debug message (only in verbose mode).
        
        Args:
            message: The message to display
        """
        if self._verbose and not self._quiet:
            self._console.print(f"[debug]⋯ {message}[/debug]")

    @contextmanager
    def spinner(self, message: str) -> Generator[Status, None, None]:
        """Create a spinner for async operations.
        
        Args:
            message: The message to display alongside the spinner
            
        Yields:
            Status object that can be updated
            
        Example:
            with logger.spinner("Processing...") as status:
                do_work()
                status.update("Almost done...")
        """
        if self._quiet:
            # In quiet mode, yield a dummy status that does nothing
            yield _DummyStatus()
        else:
            with self._console.status(f"[info]{message}[/info]", spinner="dots") as status:
                yield status
    
    @contextmanager
    def progress(
        self,
        total: int,
        description: str = "Processing"
    ) -> Generator[Progress, None, None]:
        """Create a progress bar for long-running tasks.
        
        Args:
            total: Total number of steps
            description: Description to show alongside progress
            
        Yields:
            Progress object with a task_id attribute for updating
            
        Example:
            with logger.progress(100, "Rendering") as progress:
                for i in range(100):
                    do_step()
                    progress.advance(progress.task_id)
        """
        if self._quiet:
            # In quiet mode, yield a dummy progress that does nothing
            dummy = _DummyProgress(total)
            yield dummy
        else:
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console=self._console,
            )
            with progress:
                task_id = progress.add_task(description, total=total)
                progress.task_id = task_id  # type: ignore
                yield progress
    
    def box(self, title: str, content: list[str]) -> None:
        """Display content in a formatted box.
        
        Useful for dry-run output and structured information display.
        
        Args:
            title: Title for the box
            content: List of lines to display inside the box
        """
        if not self._quiet:
            text = "\n".join(content)
            panel = Panel(text, title=f"[info]{title}[/info]", border_style="info")
            self._console.print(panel)
    
    def newline(self) -> None:
        """Print an empty line."""
        if not self._quiet:
            self._console.print()


class _DummyStatus:
    """Dummy status object for quiet mode."""
    
    def update(self, message: str) -> None:
        """No-op update."""
        pass


class _DummyProgress:
    """Dummy progress object for quiet mode."""
    
    def __init__(self, total: int):
        self.task_id = 0
        self._total = total
        self._completed = 0
    
    def advance(self, task_id: int = 0, advance: int = 1) -> None:
        """No-op advance."""
        self._completed += advance
    
    def update(self, task_id: int = 0, **kwargs) -> None:
        """No-op update."""
        pass


# Global logger instance (can be reconfigured)
_logger: Logger | None = None


def get_logger() -> Logger:
    """Get the global logger instance.
    
    Returns:
        The global Logger instance
    """
    global _logger
    if _logger is None:
        _logger = Logger()
    return _logger


def setup_logger(verbose: bool = False, quiet: bool = False) -> Logger:
    """Setup and return the global logger with specified settings.
    
    Args:
        verbose: If True, show debug messages
        quiet: If True, suppress all output except errors
        
    Returns:
        The configured Logger instance
    """
    global _logger
    _logger = Logger(verbose=verbose, quiet=quiet)
    return _logger


__all__ = [
    "Logger",
    "get_logger",
    "setup_logger",
]
