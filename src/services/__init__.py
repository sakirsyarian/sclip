"""Service modules for SmartClip AI."""

from src.services.downloader import (
    YouTubeDownloader,
    DownloadError,
    VideoUnavailableError,
    AgeRestrictedError,
    download_youtube,
    get_video_info_from_url,
    validate_youtube_url,
    extract_video_id,
    is_yt_dlp_available,
    check_yt_dlp_installed,
    YT_DLP_AVAILABLE,
)

from src.services.gemini import (
    GeminiClient,
    GeminiError,
    GeminiAPIError,
    GeminiParseError,
    GeminiUploadError,
    build_analysis_prompt,
    parse_response,
    analyze_video,
    with_retry,
)

from src.services.renderer import (
    VideoRenderer,
    RenderError,
    calculate_crop_params,
)

# Face tracking (optional - may not be installed)
try:
    from src.services.face_tracker import (
        FaceTracker,
        FacePosition,
        CropRegion,
        analyze_face_positions,
        calculate_smart_crop,
        is_face_tracking_available,
    )
    FACE_TRACKING_AVAILABLE = True
except ImportError:
    FACE_TRACKING_AVAILABLE = False

__all__ = [
    # Downloader
    "YouTubeDownloader",
    "DownloadError",
    "VideoUnavailableError",
    "AgeRestrictedError",
    "download_youtube",
    "get_video_info_from_url",
    "validate_youtube_url",
    "extract_video_id",
    "is_yt_dlp_available",
    "check_yt_dlp_installed",
    "YT_DLP_AVAILABLE",
    # Gemini
    "GeminiClient",
    "GeminiError",
    "GeminiAPIError",
    "GeminiParseError",
    "GeminiUploadError",
    "build_analysis_prompt",
    "parse_response",
    "analyze_video",
    "with_retry",
    # Renderer
    "VideoRenderer",
    "RenderError",
    "calculate_crop_params",
    # Face Tracking
    "FACE_TRACKING_AVAILABLE",
]

# Add face tracking exports if available
if FACE_TRACKING_AVAILABLE:
    __all__.extend([
        "FaceTracker",
        "FacePosition",
        "CropRegion",
        "analyze_face_positions",
        "calculate_smart_crop",
        "is_face_tracking_available",
    ])
