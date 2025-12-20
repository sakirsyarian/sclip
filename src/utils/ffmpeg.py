"""FFmpeg detection and execution utilities for SmartClip AI.

Provides functions for:
- Finding FFmpeg and FFprobe executables
- Getting FFmpeg version information
- Checking dependencies status
- Running FFmpeg commands with error handling
"""

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from src.types import ExitCode, ValidationResult


@dataclass
class FFmpegResult:
    """Result of an FFmpeg command execution.
    
    Encapsulates all information about an FFmpeg command run,
    including success status, output streams, and the command itself.
    
    Attributes:
        success: True if command exited with code 0
        returncode: Process exit code (-1 for timeout/error)
        stdout: Standard output from the command
        stderr: Standard error from the command (FFmpeg progress goes here)
        command: The full command that was executed (for debugging)
    """
    success: bool
    returncode: int
    stdout: str
    stderr: str
    command: list[str]


@dataclass
class DependencyStatus:
    """Status of FFmpeg/FFprobe dependencies.
    
    Used by check_dependencies() to report the availability
    and version of FFmpeg and FFprobe.
    
    Attributes:
        ffmpeg_found: True if FFmpeg executable was found
        ffmpeg_path: Full path to FFmpeg executable (None if not found)
        ffmpeg_version: Version string like "6.0" (None if not found)
        ffprobe_found: True if FFprobe executable was found
        ffprobe_path: Full path to FFprobe executable (None if not found)
        ffprobe_version: Version string like "6.0" (None if not found)
    """
    ffmpeg_found: bool
    ffmpeg_path: str | None
    ffmpeg_version: str | None
    ffprobe_found: bool
    ffprobe_path: str | None
    ffprobe_version: str | None
    
    @property
    def all_found(self) -> bool:
        """Check if all required dependencies are found.
        
        Both FFmpeg and FFprobe are required for full functionality.
        """
        return self.ffmpeg_found and self.ffprobe_found


# Common locations to search for FFmpeg on different platforms
# These are checked after PATH and custom path, as fallback locations
FFMPEG_SEARCH_PATHS = {
    "win32": [
        # Common Windows installation locations
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
        r"C:\Program Files (x86)\ffmpeg\bin",
        os.path.expanduser(r"~\ffmpeg\bin"),
        os.path.expanduser(r"~\AppData\Local\ffmpeg\bin"),
    ],
    "darwin": [
        # macOS: Homebrew, MacPorts, and user bin locations
        "/usr/local/bin",           # Intel Homebrew
        "/opt/homebrew/bin",        # Apple Silicon Homebrew
        "/opt/local/bin",           # MacPorts
        os.path.expanduser("~/bin"),
    ],
    "linux": [
        # Linux: Standard system and user locations
        "/usr/bin",                 # System packages
        "/usr/local/bin",           # Manually installed
        "/snap/bin",                # Snap packages
        os.path.expanduser("~/bin"),
        os.path.expanduser("~/.local/bin"),
    ],
}


def _get_executable_name(base_name: str) -> str:
    """Get platform-specific executable name.
    
    Args:
        base_name: Base name of the executable (e.g., 'ffmpeg')
        
    Returns:
        Executable name with .exe extension on Windows
    """
    if sys.platform == "win32":
        return f"{base_name}.exe"
    return base_name


def _is_executable(path: str) -> bool:
    """Check if a path points to an executable file.
    
    Args:
        path: Path to check
        
    Returns:
        True if path is an executable file
    """
    return os.path.isfile(path) and os.access(path, os.X_OK)


def find_ffmpeg(custom_path: str | None = None) -> str | None:
    """Find FFmpeg executable.
    
    Search order:
    1. Custom path (if provided)
    2. System PATH
    3. Platform-specific common locations
    4. Local directory
    
    Args:
        custom_path: Optional custom path to FFmpeg executable or directory
        
    Returns:
        Full path to FFmpeg executable, or None if not found
    """
    exe_name = _get_executable_name("ffmpeg")
    
    # 1. Check custom path first
    if custom_path:
        custom_path = os.path.expanduser(custom_path)
        
        # If it's a directory, look for ffmpeg inside
        if os.path.isdir(custom_path):
            full_path = os.path.join(custom_path, exe_name)
            if _is_executable(full_path):
                return full_path
        # If it's a file, check if it's executable
        elif _is_executable(custom_path):
            return custom_path
        # Maybe they gave us path without .exe on Windows
        elif sys.platform == "win32" and _is_executable(custom_path + ".exe"):
            return custom_path + ".exe"
    
    # 2. Check system PATH using shutil.which
    path_result = shutil.which("ffmpeg")
    if path_result:
        return path_result
    
    # 3. Check platform-specific common locations
    platform = sys.platform
    if platform.startswith("linux"):
        platform = "linux"
    
    search_paths = FFMPEG_SEARCH_PATHS.get(platform, [])
    for search_dir in search_paths:
        if os.path.isdir(search_dir):
            full_path = os.path.join(search_dir, exe_name)
            if _is_executable(full_path):
                return full_path
    
    # 4. Check local directory (current working directory)
    local_path = os.path.join(os.getcwd(), exe_name)
    if _is_executable(local_path):
        return local_path
    
    # Also check ./bin directory
    local_bin_path = os.path.join(os.getcwd(), "bin", exe_name)
    if _is_executable(local_bin_path):
        return local_bin_path
    
    return None


def find_ffprobe(custom_path: str | None = None) -> str | None:
    """Find FFprobe executable.
    
    Search order:
    1. Custom path (if provided)
    2. Same directory as FFmpeg (if FFmpeg was found)
    3. System PATH
    4. Platform-specific common locations
    5. Local directory
    
    Args:
        custom_path: Optional custom path to FFprobe executable or directory
        
    Returns:
        Full path to FFprobe executable, or None if not found
    """
    exe_name = _get_executable_name("ffprobe")
    
    # 1. Check custom path first
    if custom_path:
        custom_path = os.path.expanduser(custom_path)
        
        # If it's a directory, look for ffprobe inside
        if os.path.isdir(custom_path):
            full_path = os.path.join(custom_path, exe_name)
            if _is_executable(full_path):
                return full_path
        # If it's a file, check if it's executable
        elif _is_executable(custom_path):
            return custom_path
        # Maybe they gave us path without .exe on Windows
        elif sys.platform == "win32" and _is_executable(custom_path + ".exe"):
            return custom_path + ".exe"
    
    # 2. Check system PATH using shutil.which
    path_result = shutil.which("ffprobe")
    if path_result:
        return path_result
    
    # 3. Check platform-specific common locations
    platform = sys.platform
    if platform.startswith("linux"):
        platform = "linux"
    
    search_paths = FFMPEG_SEARCH_PATHS.get(platform, [])
    for search_dir in search_paths:
        if os.path.isdir(search_dir):
            full_path = os.path.join(search_dir, exe_name)
            if _is_executable(full_path):
                return full_path
    
    # 4. Check local directory (current working directory)
    local_path = os.path.join(os.getcwd(), exe_name)
    if _is_executable(local_path):
        return local_path
    
    # Also check ./bin directory
    local_bin_path = os.path.join(os.getcwd(), "bin", exe_name)
    if _is_executable(local_bin_path):
        return local_bin_path
    
    return None


def get_ffmpeg_version(ffmpeg_path: str | None = None) -> str | None:
    """Get FFmpeg version string.
    
    Args:
        ffmpeg_path: Path to FFmpeg executable. If None, will try to find it.
        
    Returns:
        Version string (e.g., "6.0"), or None if FFmpeg not found or version
        couldn't be determined
    """
    if ffmpeg_path is None:
        ffmpeg_path = find_ffmpeg()
    
    if ffmpeg_path is None:
        return None
    
    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return None
        
        # Parse version from output like "ffmpeg version 6.0 Copyright..."
        # or "ffmpeg version n6.0-..."
        output = result.stdout
        match = re.search(r"ffmpeg version (?:n)?(\d+\.\d+(?:\.\d+)?)", output)
        if match:
            return match.group(1)
        
        # Try alternative pattern for git builds
        match = re.search(r"ffmpeg version (\S+)", output)
        if match:
            return match.group(1)
        
        return None
        
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        return None


def get_ffprobe_version(ffprobe_path: str | None = None) -> str | None:
    """Get FFprobe version string.
    
    Args:
        ffprobe_path: Path to FFprobe executable. If None, will try to find it.
        
    Returns:
        Version string (e.g., "6.0"), or None if FFprobe not found or version
        couldn't be determined
    """
    if ffprobe_path is None:
        ffprobe_path = find_ffprobe()
    
    if ffprobe_path is None:
        return None
    
    try:
        result = subprocess.run(
            [ffprobe_path, "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return None
        
        # Parse version from output like "ffprobe version 6.0 Copyright..."
        output = result.stdout
        match = re.search(r"ffprobe version (?:n)?(\d+\.\d+(?:\.\d+)?)", output)
        if match:
            return match.group(1)
        
        # Try alternative pattern for git builds
        match = re.search(r"ffprobe version (\S+)", output)
        if match:
            return match.group(1)
        
        return None
        
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        return None


def check_dependencies(custom_ffmpeg_path: str | None = None) -> DependencyStatus:
    """Check FFmpeg and FFprobe dependencies.
    
    Args:
        custom_ffmpeg_path: Optional custom path to FFmpeg/FFprobe directory
        
    Returns:
        DependencyStatus with information about found dependencies
    """
    # Find FFmpeg
    ffmpeg_path = find_ffmpeg(custom_ffmpeg_path)
    ffmpeg_found = ffmpeg_path is not None
    ffmpeg_version = get_ffmpeg_version(ffmpeg_path) if ffmpeg_found else None
    
    # Find FFprobe - check same directory as FFmpeg first
    ffprobe_custom_path = None
    if custom_ffmpeg_path:
        ffprobe_custom_path = custom_ffmpeg_path
    elif ffmpeg_path:
        # Try the same directory as FFmpeg
        ffprobe_custom_path = os.path.dirname(ffmpeg_path)
    
    ffprobe_path = find_ffprobe(ffprobe_custom_path)
    ffprobe_found = ffprobe_path is not None
    ffprobe_version = get_ffprobe_version(ffprobe_path) if ffprobe_found else None
    
    return DependencyStatus(
        ffmpeg_found=ffmpeg_found,
        ffmpeg_path=ffmpeg_path,
        ffmpeg_version=ffmpeg_version,
        ffprobe_found=ffprobe_found,
        ffprobe_path=ffprobe_path,
        ffprobe_version=ffprobe_version,
    )


def validate_ffmpeg_available(custom_path: str | None = None) -> ValidationResult:
    """Validate that FFmpeg is available and usable.
    
    Args:
        custom_path: Optional custom path to FFmpeg
        
    Returns:
        ValidationResult indicating if FFmpeg is available
    """
    status = check_dependencies(custom_path)
    
    if not status.ffmpeg_found:
        return ValidationResult(
            valid=False,
            error="FFmpeg not found. Please install FFmpeg or specify path with --ffmpeg-path. Run 'sclip --setup' for installation guidance.",
            error_code=ExitCode.DEPENDENCY_ERROR
        )
    
    if not status.ffprobe_found:
        return ValidationResult(
            valid=False,
            error="FFprobe not found. FFprobe is usually installed with FFmpeg. Please reinstall FFmpeg.",
            error_code=ExitCode.DEPENDENCY_ERROR
        )
    
    return ValidationResult(valid=True)


def run_ffmpeg(
    args: list[str],
    ffmpeg_path: str | None = None,
    timeout: float | None = None,
    progress_callback: Callable[[str], None] | None = None,
    capture_output: bool = True
) -> FFmpegResult:
    """Run FFmpeg command with error handling.
    
    Args:
        args: List of arguments to pass to FFmpeg (without the ffmpeg executable)
        ffmpeg_path: Path to FFmpeg executable. If None, will try to find it.
        timeout: Optional timeout in seconds
        progress_callback: Optional callback for progress output (receives stderr lines)
        capture_output: If True, capture stdout/stderr. If False, inherit from parent.
        
    Returns:
        FFmpegResult with execution details
        
    Raises:
        FileNotFoundError: If FFmpeg executable not found
        subprocess.TimeoutExpired: If timeout is exceeded
    """
    if ffmpeg_path is None:
        ffmpeg_path = find_ffmpeg()
    
    if ffmpeg_path is None:
        raise FileNotFoundError(
            "FFmpeg not found. Please install FFmpeg or specify path with --ffmpeg-path."
        )
    
    command = [ffmpeg_path] + args
    
    try:
        if progress_callback and capture_output:
            # Run with real-time stderr capture for progress
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout_data = ""
            stderr_data = ""
            
            # Read stderr line by line for progress updates
            if process.stderr:
                for line in process.stderr:
                    stderr_data += line
                    progress_callback(line.strip())
            
            # Get remaining stdout
            if process.stdout:
                stdout_data = process.stdout.read()
            
            process.wait(timeout=timeout)
            
            return FFmpegResult(
                success=process.returncode == 0,
                returncode=process.returncode,
                stdout=stdout_data,
                stderr=stderr_data,
                command=command
            )
        else:
            # Simple execution with captured output
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                timeout=timeout
            )
            
            return FFmpegResult(
                success=result.returncode == 0,
                returncode=result.returncode,
                stdout=result.stdout if capture_output else "",
                stderr=result.stderr if capture_output else "",
                command=command
            )
            
    except subprocess.TimeoutExpired as e:
        return FFmpegResult(
            success=False,
            returncode=-1,
            stdout=e.stdout if e.stdout else "",
            stderr=e.stderr if e.stderr else f"Command timed out after {timeout} seconds",
            command=command
        )
    except OSError as e:
        return FFmpegResult(
            success=False,
            returncode=-1,
            stdout="",
            stderr=str(e),
            command=command
        )


def run_ffprobe(
    args: list[str],
    ffprobe_path: str | None = None,
    timeout: float | None = 30.0
) -> FFmpegResult:
    """Run FFprobe command with error handling.
    
    Args:
        args: List of arguments to pass to FFprobe (without the ffprobe executable)
        ffprobe_path: Path to FFprobe executable. If None, will try to find it.
        timeout: Optional timeout in seconds (default: 30)
        
    Returns:
        FFmpegResult with execution details
        
    Raises:
        FileNotFoundError: If FFprobe executable not found
    """
    if ffprobe_path is None:
        ffprobe_path = find_ffprobe()
    
    if ffprobe_path is None:
        raise FileNotFoundError(
            "FFprobe not found. Please install FFmpeg (includes FFprobe) or specify path."
        )
    
    command = [ffprobe_path] + args
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return FFmpegResult(
            success=result.returncode == 0,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            command=command
        )
        
    except subprocess.TimeoutExpired as e:
        return FFmpegResult(
            success=False,
            returncode=-1,
            stdout=e.stdout if e.stdout else "",
            stderr=e.stderr if e.stderr else f"Command timed out after {timeout} seconds",
            command=command
        )
    except OSError as e:
        return FFmpegResult(
            success=False,
            returncode=-1,
            stdout="",
            stderr=str(e),
            command=command
        )


__all__ = [
    "FFmpegResult",
    "DependencyStatus",
    "find_ffmpeg",
    "find_ffprobe",
    "get_ffmpeg_version",
    "get_ffprobe_version",
    "check_dependencies",
    "validate_ffmpeg_available",
    "run_ffmpeg",
    "run_ffprobe",
]
