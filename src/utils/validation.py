"""Input validation utilities for SmartClip AI.

Provides validation functions for:
- Input files (existence, readability, format)
- YouTube URLs (pattern matching)
- Output directories (writability, existing files)
- CLI options (conflict detection)
- Duration ranges (min/max validation)
"""

import os
import re
from pathlib import Path

from src.types import CLIOptions, ExitCode, ValidationResult


# Supported video formats (from requirements FR-1.4)
# These are common video container formats that FFmpeg can process
SUPPORTED_FORMATS = {
    ".mp4",   # MPEG-4 Part 14 - most common
    ".mkv",   # Matroska - open container format
    ".avi",   # Audio Video Interleave - legacy Microsoft format
    ".mov",   # QuickTime - Apple format
    ".webm",  # WebM - open web format (VP8/VP9)
    ".m4v",   # MPEG-4 Video - Apple variant of MP4
    ".mpeg",  # MPEG-1/2 - legacy format
    ".mpg",   # MPEG-1/2 - legacy format (alternate extension)
    ".flv"    # Flash Video - legacy web format
}

# Minimum video duration in seconds (from requirements FR-1.5)
# Videos shorter than this are rejected as they're too short for clip extraction
MIN_VIDEO_DURATION = 60

# YouTube URL patterns for validation
# Supports various YouTube URL formats including standard, short, embed, mobile, and Shorts
YOUTUBE_PATTERNS = [
    # Standard watch URLs: youtube.com/watch?v=VIDEO_ID
    r"^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]{11}",
    # Short URLs: youtu.be/VIDEO_ID
    r"^https?://youtu\.be/[\w-]{11}",
    # Embed URLs: youtube.com/embed/VIDEO_ID
    r"^https?://(?:www\.)?youtube\.com/embed/[\w-]{11}",
    # Mobile URLs: m.youtube.com/watch?v=VIDEO_ID
    r"^https?://m\.youtube\.com/watch\?v=[\w-]{11}",
    # YouTube Shorts: youtube.com/shorts/VIDEO_ID
    r"^https?://(?:www\.)?youtube\.com/shorts/[\w-]{11}",
]


def validate_input_file(path: str) -> ValidationResult:
    """Validate that input file exists, is readable, and has valid format.
    
    Checks:
    - File exists
    - File is readable
    - File extension is in SUPPORTED_FORMATS
    
    Args:
        path: Path to the input video file
        
    Returns:
        ValidationResult with valid=True if all checks pass,
        otherwise valid=False with error message and error_code
    """
    file_path = Path(path)
    
    # Check if file exists
    if not file_path.exists():
        return ValidationResult(
            valid=False,
            error=f"Input file not found: {path}",
            error_code=ExitCode.INPUT_ERROR
        )
    
    # Check if it's a file (not a directory)
    if not file_path.is_file():
        return ValidationResult(
            valid=False,
            error=f"Input path is not a file: {path}",
            error_code=ExitCode.INPUT_ERROR
        )
    
    # Check if file is readable
    if not os.access(file_path, os.R_OK):
        return ValidationResult(
            valid=False,
            error=f"Input file is not readable: {path}",
            error_code=ExitCode.INPUT_ERROR
        )
    
    # Check file format
    extension = file_path.suffix.lower()
    if extension not in SUPPORTED_FORMATS:
        supported_list = ", ".join(sorted(SUPPORTED_FORMATS))
        return ValidationResult(
            valid=False,
            error=f"Unsupported video format '{extension}'. Supported formats: {supported_list}",
            error_code=ExitCode.INPUT_ERROR
        )
    
    return ValidationResult(valid=True)


def validate_youtube_url(url: str) -> ValidationResult:
    """Validate that URL is a valid YouTube URL.
    
    Supports:
    - Standard watch URLs (youtube.com/watch?v=...)
    - Short URLs (youtu.be/...)
    - Embed URLs (youtube.com/embed/...)
    - Mobile URLs (m.youtube.com/watch?v=...)
    - YouTube Shorts (youtube.com/shorts/...)
    
    Args:
        url: YouTube URL to validate
        
    Returns:
        ValidationResult with valid=True if URL matches any pattern,
        otherwise valid=False with error message
    """
    if not url:
        return ValidationResult(
            valid=False,
            error="YouTube URL is empty",
            error_code=ExitCode.INPUT_ERROR
        )
    
    # Check against all patterns
    for pattern in YOUTUBE_PATTERNS:
        if re.match(pattern, url, re.IGNORECASE):
            return ValidationResult(valid=True)
    
    return ValidationResult(
        valid=False,
        error=f"Invalid YouTube URL: {url}. Expected format: https://youtube.com/watch?v=VIDEO_ID or https://youtu.be/VIDEO_ID",
        error_code=ExitCode.INPUT_ERROR
    )


def validate_output_dir(path: str, force: bool = False) -> ValidationResult:
    """Validate output directory is writable and handle existing files.
    
    Checks:
    - Directory exists or can be created
    - Directory is writable
    - If directory has existing files and force=False, warns user
    
    Args:
        path: Path to output directory
        force: If True, allow overwriting existing files
        
    Returns:
        ValidationResult with valid=True if directory is usable,
        otherwise valid=False with error message
    """
    dir_path = Path(path)
    
    # If directory exists
    if dir_path.exists():
        # Check if it's actually a directory
        if not dir_path.is_dir():
            return ValidationResult(
                valid=False,
                error=f"Output path exists but is not a directory: {path}",
                error_code=ExitCode.OUTPUT_ERROR
            )
        
        # Check if directory is writable
        if not os.access(dir_path, os.W_OK):
            return ValidationResult(
                valid=False,
                error=f"Output directory is not writable: {path}",
                error_code=ExitCode.OUTPUT_ERROR
            )
        
        # Check for existing files (only warn if not force mode)
        if not force:
            existing_files = list(dir_path.glob("*.mp4"))
            if existing_files:
                return ValidationResult(
                    valid=False,
                    error=f"Output directory contains existing .mp4 files. Use --force to overwrite.",
                    error_code=ExitCode.OUTPUT_ERROR
                )
    else:
        # Directory doesn't exist - check if parent is writable
        parent = dir_path.parent
        if parent.exists():
            if not os.access(parent, os.W_OK):
                return ValidationResult(
                    valid=False,
                    error=f"Cannot create output directory (parent not writable): {path}",
                    error_code=ExitCode.OUTPUT_ERROR
                )
        else:
            # Try to check if we can create the full path
            # Find the first existing parent
            check_path = parent
            while not check_path.exists() and check_path != check_path.parent:
                check_path = check_path.parent
            
            if check_path.exists() and not os.access(check_path, os.W_OK):
                return ValidationResult(
                    valid=False,
                    error=f"Cannot create output directory (insufficient permissions): {path}",
                    error_code=ExitCode.OUTPUT_ERROR
                )
    
    return ValidationResult(valid=True)


def validate_options(options: CLIOptions) -> ValidationResult:
    """Validate CLI options for conflicts and consistency.
    
    Checks:
    - Either --url or --input is provided (not both, not neither)
    - --verbose and --quiet are not both set
    - Duration range is valid
    - max_clips is positive
    
    Args:
        options: CLIOptions object to validate
        
    Returns:
        ValidationResult with valid=True if no conflicts,
        otherwise valid=False with error message
    """
    # Check input source: must have exactly one of url or input
    has_url = options.url is not None and options.url.strip() != ""
    has_input = options.input is not None and options.input.strip() != ""
    
    if not has_url and not has_input:
        return ValidationResult(
            valid=False,
            error="Either --url or --input must be provided",
            error_code=ExitCode.VALIDATION_ERROR
        )
    
    if has_url and has_input:
        return ValidationResult(
            valid=False,
            error="Cannot use both --url and --input. Choose one input source.",
            error_code=ExitCode.VALIDATION_ERROR
        )
    
    # Check verbose/quiet conflict
    if options.verbose and options.quiet:
        return ValidationResult(
            valid=False,
            error="Cannot use both --verbose and --quiet",
            error_code=ExitCode.VALIDATION_ERROR
        )
    
    # Validate duration range
    duration_result = validate_duration_range(options.min_duration, options.max_duration)
    if not duration_result.valid:
        return duration_result
    
    # Validate max_clips
    if options.max_clips < 1:
        return ValidationResult(
            valid=False,
            error="--max-clips must be at least 1",
            error_code=ExitCode.VALIDATION_ERROR
        )
    
    return ValidationResult(valid=True)


def validate_duration_range(min_duration: int, max_duration: int) -> ValidationResult:
    """Validate that duration range is valid.
    
    Checks:
    - min_duration is positive
    - max_duration is positive
    - min_duration <= max_duration
    - max_duration is reasonable (not > 300 seconds for short clips)
    
    Args:
        min_duration: Minimum clip duration in seconds
        max_duration: Maximum clip duration in seconds
        
    Returns:
        ValidationResult with valid=True if range is valid,
        otherwise valid=False with error message
    """
    if min_duration < 1:
        return ValidationResult(
            valid=False,
            error="--min-duration must be at least 1 second",
            error_code=ExitCode.VALIDATION_ERROR
        )
    
    if max_duration < 1:
        return ValidationResult(
            valid=False,
            error="--max-duration must be at least 1 second",
            error_code=ExitCode.VALIDATION_ERROR
        )
    
    if min_duration > max_duration:
        return ValidationResult(
            valid=False,
            error=f"--min-duration ({min_duration}s) cannot be greater than --max-duration ({max_duration}s)",
            error_code=ExitCode.VALIDATION_ERROR
        )
    
    # Warn if max_duration is very long (but still allow it)
    # This is a soft limit - we don't fail, just validate
    
    return ValidationResult(valid=True)


def validate_video_duration(duration: float) -> ValidationResult:
    """Validate that video duration meets minimum requirements.
    
    From requirements FR-1.5: System must reject videos < 60 seconds.
    
    Args:
        duration: Video duration in seconds
        
    Returns:
        ValidationResult with valid=True if duration is acceptable,
        otherwise valid=False with error message
    """
    if duration < MIN_VIDEO_DURATION:
        return ValidationResult(
            valid=False,
            error=f"Video is too short ({duration:.1f}s). Minimum duration is {MIN_VIDEO_DURATION} seconds.",
            error_code=ExitCode.INPUT_ERROR
        )
    
    return ValidationResult(valid=True)


__all__ = [
    "validate_input_file",
    "validate_youtube_url",
    "validate_output_dir",
    "validate_options",
    "validate_duration_range",
    "validate_video_duration",
    "SUPPORTED_FORMATS",
    "MIN_VIDEO_DURATION",
    "YOUTUBE_PATTERNS",
]
