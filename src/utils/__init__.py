"""Utility modules for SmartClip AI."""

from src.utils.logger import Logger, get_logger, setup_logger
from src.utils.config import (
    get_config_dir,
    get_config_path,
    load_config,
    save_config,
    get_api_key,
    get_ffmpeg_path,
)
from src.utils.cleanup import (
    CleanupContext,
    get_cleanup_context,
    setup_cleanup_context,
    setup_signal_handlers,
    register_temp_file,
    unregister_temp_file,
)
from src.utils.validation import (
    validate_input_file,
    validate_youtube_url,
    validate_output_dir,
    validate_options,
    validate_duration_range,
    validate_video_duration,
    SUPPORTED_FORMATS,
    MIN_VIDEO_DURATION,
    YOUTUBE_PATTERNS,
)
from src.utils.ffmpeg import (
    FFmpegResult,
    DependencyStatus,
    find_ffmpeg,
    find_ffprobe,
    get_ffmpeg_version,
    get_ffprobe_version,
    check_dependencies,
    validate_ffmpeg_available,
    run_ffmpeg,
    run_ffprobe,
)
from src.utils.video import (
    VideoAnalysisError,
    analyze_video,
    validate_video_file,
    get_video_duration,
    format_duration,
    format_resolution,
    format_bitrate,
)
from src.utils.captions import (
    CAPTION_STYLES,
    CaptionStyleConfig,
    generate_ass_subtitle,
    get_style_config,
    calculate_text_position,
)

__all__ = [
    # Logger
    "Logger",
    "get_logger",
    "setup_logger",
    # Config
    "get_config_dir",
    "get_config_path",
    "load_config",
    "save_config",
    "get_api_key",
    "get_ffmpeg_path",
    # Cleanup
    "CleanupContext",
    "get_cleanup_context",
    "setup_cleanup_context",
    "setup_signal_handlers",
    "register_temp_file",
    "unregister_temp_file",
    # Validation
    "validate_input_file",
    "validate_youtube_url",
    "validate_output_dir",
    "validate_options",
    "validate_duration_range",
    "validate_video_duration",
    "SUPPORTED_FORMATS",
    "MIN_VIDEO_DURATION",
    "YOUTUBE_PATTERNS",
    # FFmpeg
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
    # Video
    "VideoAnalysisError",
    "analyze_video",
    "validate_video_file",
    "get_video_duration",
    "format_duration",
    "format_resolution",
    "format_bitrate",
    # Captions
    "CAPTION_STYLES",
    "CaptionStyleConfig",
    "generate_ass_subtitle",
    "get_style_config",
    "calculate_text_position",
]
