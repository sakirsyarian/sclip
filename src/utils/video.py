"""Video analysis utilities for SmartClip AI.

This module provides functions for analyzing video files using ffprobe
to extract metadata needed for processing decisions and user display.

Key Features:
    - Extract video metadata (duration, resolution, codec, fps, bitrate)
    - Validate video files before processing
    - Format metadata for human-readable display
    - Handle corrupt/invalid video files gracefully
    - Caching of video analysis results for performance

Metadata Extracted:
    - Duration: Total length in seconds
    - Resolution: Width x height in pixels
    - Video codec: e.g., h264, vp9, hevc
    - Audio codec: e.g., aac, opus, mp3
    - Bitrate: Video bitrate in bits per second
    - FPS: Frame rate (e.g., 29.97, 30, 60)

Usage:
    from src.utils.video import analyze_video, format_duration
    
    # Analyze a video file (results are cached)
    info = analyze_video("video.mp4")
    print(f"Duration: {format_duration(info.duration)}")
    print(f"Resolution: {info.width}x{info.height}")
    
    # Clear cache if needed
    clear_video_cache()
    
    # Validate a video file
    result = validate_video_file("video.mp4")
    if not result.valid:
        print(f"Invalid video: {result.error}")
"""

import json
import os
from typing import Any

from src.types import ExitCode, ValidationResult, VideoInfo
from src.utils.ffmpeg import find_ffprobe, run_ffprobe


# Cache for video analysis results (keyed by path + mtime)
_video_info_cache: dict[tuple[str, float], VideoInfo] = {}


class VideoAnalysisError(Exception):
    """Exception raised when video analysis fails.
    
    This can occur due to:
    - Corrupt or invalid video files
    - Missing video stream
    - Unable to determine duration or dimensions
    - FFprobe execution errors
    
    Attributes:
        error_code: Exit code to use for CLI (default: PROCESSING_ERROR)
    """
    
    def __init__(self, message: str, error_code: ExitCode = ExitCode.PROCESSING_ERROR):
        super().__init__(message)
        self.error_code = error_code


def analyze_video(
    video_path: str,
    ffprobe_path: str | None = None,
    use_cache: bool = True
) -> VideoInfo:
    """Analyze a video file and extract metadata using ffprobe.
    
    Results are cached based on file path and modification time to avoid
    redundant analysis of the same file.
    
    Args:
        video_path: Path to the video file to analyze
        ffprobe_path: Optional custom path to ffprobe executable
        use_cache: Whether to use cached results (default: True)
        
    Returns:
        VideoInfo dataclass with video metadata
        
    Raises:
        VideoAnalysisError: If video cannot be analyzed or is invalid
        FileNotFoundError: If video file or ffprobe not found
    """
    # Validate file exists
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    if not os.path.isfile(video_path):
        raise VideoAnalysisError(
            f"Path is not a file: {video_path}",
            ExitCode.INPUT_ERROR
        )
    
    # Check cache
    if use_cache:
        try:
            mtime = os.path.getmtime(video_path)
            cache_key = (os.path.abspath(video_path), mtime)
            if cache_key in _video_info_cache:
                return _video_info_cache[cache_key]
        except OSError:
            pass  # If we can't get mtime, skip caching
    
    # Find ffprobe
    probe_path = ffprobe_path or find_ffprobe()
    if probe_path is None:
        raise FileNotFoundError(
            "FFprobe not found. Please install FFmpeg or specify path with --ffmpeg-path."
        )
    
    # Run ffprobe to get JSON output with stream and format info
    args = [
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path
    ]
    
    result = run_ffprobe(args, ffprobe_path=probe_path, timeout=30.0)
    
    if not result.success:
        error_msg = result.stderr.strip() if result.stderr else "Unknown error"
        raise VideoAnalysisError(
            f"Failed to analyze video: {error_msg}",
            ExitCode.PROCESSING_ERROR
        )
    
    # Parse JSON output
    try:
        probe_data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise VideoAnalysisError(
            f"Failed to parse ffprobe output: {e}",
            ExitCode.PROCESSING_ERROR
        )
    
    # Extract video and audio stream info
    video_stream = _find_video_stream(probe_data)
    audio_stream = _find_audio_stream(probe_data)
    format_info = probe_data.get("format", {})
    
    if video_stream is None:
        raise VideoAnalysisError(
            "No video stream found in file. The file may be corrupt or not a valid video.",
            ExitCode.INPUT_ERROR
        )
    
    # Extract metadata
    duration = _extract_duration(video_stream, format_info)
    width = _extract_int(video_stream, "width", 0)
    height = _extract_int(video_stream, "height", 0)
    codec = video_stream.get("codec_name", "unknown")
    audio_codec = audio_stream.get("codec_name", "none") if audio_stream else "none"
    bitrate = _extract_bitrate(video_stream, format_info)
    fps = _extract_fps(video_stream)
    
    # Validate essential fields
    if width == 0 or height == 0:
        raise VideoAnalysisError(
            "Could not determine video dimensions. The file may be corrupt.",
            ExitCode.INPUT_ERROR
        )
    
    if duration <= 0:
        raise VideoAnalysisError(
            "Could not determine video duration. The file may be corrupt.",
            ExitCode.INPUT_ERROR
        )
    
    video_info = VideoInfo(
        path=video_path,
        duration=duration,
        width=width,
        height=height,
        codec=codec,
        audio_codec=audio_codec,
        bitrate=bitrate,
        fps=fps
    )
    
    # Cache the result
    if use_cache:
        try:
            mtime = os.path.getmtime(video_path)
            cache_key = (os.path.abspath(video_path), mtime)
            _video_info_cache[cache_key] = video_info
        except OSError:
            pass
    
    return video_info


def clear_video_cache() -> None:
    """Clear the video analysis cache.
    
    Call this if you need to force re-analysis of previously analyzed videos.
    """
    _video_info_cache.clear()


def _find_video_stream(probe_data: dict[str, Any]) -> dict[str, Any] | None:
    """Find the first video stream in ffprobe output.
    
    Args:
        probe_data: Parsed ffprobe JSON output
        
    Returns:
        Video stream dict or None if not found
    """
    streams = probe_data.get("streams", [])
    for stream in streams:
        if stream.get("codec_type") == "video":
            return stream
    return None


def _find_audio_stream(probe_data: dict[str, Any]) -> dict[str, Any] | None:
    """Find the first audio stream in ffprobe output.
    
    Args:
        probe_data: Parsed ffprobe JSON output
        
    Returns:
        Audio stream dict or None if not found
    """
    streams = probe_data.get("streams", [])
    for stream in streams:
        if stream.get("codec_type") == "audio":
            return stream
    return None


def _extract_duration(video_stream: dict[str, Any], format_info: dict[str, Any]) -> float:
    """Extract video duration from stream or format info.
    
    Args:
        video_stream: Video stream dict from ffprobe
        format_info: Format dict from ffprobe
        
    Returns:
        Duration in seconds, or 0.0 if not found
    """
    # Try stream duration first
    duration_str = video_stream.get("duration")
    if duration_str:
        try:
            return float(duration_str)
        except (ValueError, TypeError):
            pass
    
    # Fall back to format duration
    duration_str = format_info.get("duration")
    if duration_str:
        try:
            return float(duration_str)
        except (ValueError, TypeError):
            pass
    
    return 0.0


def _extract_int(data: dict[str, Any], key: str, default: int = 0) -> int:
    """Safely extract an integer value from a dict.
    
    Args:
        data: Dict to extract from
        key: Key to look up
        default: Default value if extraction fails
        
    Returns:
        Extracted integer or default
    """
    value = data.get(key)
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _extract_bitrate(video_stream: dict[str, Any], format_info: dict[str, Any]) -> int:
    """Extract video bitrate from stream or format info.
    
    Args:
        video_stream: Video stream dict from ffprobe
        format_info: Format dict from ffprobe
        
    Returns:
        Bitrate in bits per second, or 0 if not found
    """
    # Try stream bit_rate first
    bitrate_str = video_stream.get("bit_rate")
    if bitrate_str:
        try:
            return int(bitrate_str)
        except (ValueError, TypeError):
            pass
    
    # Fall back to format bit_rate
    bitrate_str = format_info.get("bit_rate")
    if bitrate_str:
        try:
            return int(bitrate_str)
        except (ValueError, TypeError):
            pass
    
    return 0


def _extract_fps(video_stream: dict[str, Any]) -> float:
    """Extract frame rate from video stream.
    
    Args:
        video_stream: Video stream dict from ffprobe
        
    Returns:
        Frame rate as float, or 0.0 if not found
    """
    # Try r_frame_rate first (real frame rate)
    fps_str = video_stream.get("r_frame_rate")
    if fps_str:
        fps = _parse_frame_rate(fps_str)
        if fps > 0:
            return fps
    
    # Fall back to avg_frame_rate
    fps_str = video_stream.get("avg_frame_rate")
    if fps_str:
        fps = _parse_frame_rate(fps_str)
        if fps > 0:
            return fps
    
    return 0.0


def _parse_frame_rate(fps_str: str) -> float:
    """Parse frame rate string (e.g., '30/1' or '29.97').
    
    Args:
        fps_str: Frame rate string from ffprobe
        
    Returns:
        Frame rate as float, or 0.0 if parsing fails
    """
    if not fps_str:
        return 0.0
    
    try:
        # Handle fraction format like "30/1" or "30000/1001"
        if "/" in fps_str:
            num, den = fps_str.split("/")
            numerator = float(num)
            denominator = float(den)
            if denominator == 0:
                return 0.0
            return numerator / denominator
        else:
            return float(fps_str)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0.0


def validate_video_file(video_path: str, ffprobe_path: str | None = None) -> ValidationResult:
    """Validate that a file is a valid, analyzable video.
    
    Args:
        video_path: Path to the video file
        ffprobe_path: Optional custom path to ffprobe
        
    Returns:
        ValidationResult indicating if the video is valid
    """
    try:
        video_info = analyze_video(video_path, ffprobe_path)
        return ValidationResult(valid=True)
    except FileNotFoundError as e:
        return ValidationResult(
            valid=False,
            error=str(e),
            error_code=ExitCode.INPUT_ERROR
        )
    except VideoAnalysisError as e:
        return ValidationResult(
            valid=False,
            error=str(e),
            error_code=e.error_code
        )


def get_video_duration(video_path: str, ffprobe_path: str | None = None) -> float | None:
    """Get just the duration of a video file.
    
    Convenience function when only duration is needed.
    
    Args:
        video_path: Path to the video file
        ffprobe_path: Optional custom path to ffprobe
        
    Returns:
        Duration in seconds, or None if analysis fails
    """
    try:
        video_info = analyze_video(video_path, ffprobe_path)
        return video_info.duration
    except (FileNotFoundError, VideoAnalysisError):
        return None


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string like "1:23:45" or "12:34"
    """
    if seconds < 0:
        return "0:00"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def format_resolution(width: int, height: int) -> str:
    """Format resolution to human-readable string.
    
    Args:
        width: Video width in pixels
        height: Video height in pixels
        
    Returns:
        Formatted string like "1920x1080 (1080p)"
    """
    resolution = f"{width}x{height}"
    
    # Add common resolution names
    if height == 2160 or (width == 3840 and height == 2160):
        resolution += " (4K)"
    elif height == 1440 or (width == 2560 and height == 1440):
        resolution += " (1440p)"
    elif height == 1080 or (width == 1920 and height == 1080):
        resolution += " (1080p)"
    elif height == 720 or (width == 1280 and height == 720):
        resolution += " (720p)"
    elif height == 480 or (width == 854 and height == 480):
        resolution += " (480p)"
    elif height == 360 or (width == 640 and height == 360):
        resolution += " (360p)"
    
    return resolution


def format_bitrate(bitrate: int) -> str:
    """Format bitrate to human-readable string.
    
    Args:
        bitrate: Bitrate in bits per second
        
    Returns:
        Formatted string like "5.2 Mbps" or "800 kbps"
    """
    if bitrate <= 0:
        return "unknown"
    
    if bitrate >= 1_000_000:
        return f"{bitrate / 1_000_000:.1f} Mbps"
    elif bitrate >= 1_000:
        return f"{bitrate / 1_000:.0f} kbps"
    else:
        return f"{bitrate} bps"


__all__ = [
    "VideoAnalysisError",
    "analyze_video",
    "clear_video_cache",
    "validate_video_file",
    "get_video_duration",
    "format_duration",
    "format_resolution",
    "format_bitrate",
]
