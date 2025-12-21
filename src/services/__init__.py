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

from src.services.audio import (
    extract_audio,
    get_audio_duration,
    AudioExtractionError,
)

from src.services.renderer import (
    VideoRenderer,
    RenderError,
    calculate_crop_params,
)

# Transcribers
from src.services.transcribers import (
    get_transcriber,
    BaseTranscriber,
    TranscriptionResult,
    WordTimestamp,
    GroqTranscriber,
    OpenAITranscriber,
    LocalTranscriber,
)

# Analyzers
from src.services.analyzers import (
    get_analyzer,
    BaseAnalyzer,
    AnalysisResult,
    GroqAnalyzer,
    GeminiAnalyzer,
    OpenAIAnalyzer,
    OllamaAnalyzer,
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
    # Audio
    "extract_audio",
    "get_audio_duration",
    "AudioExtractionError",
    # Transcribers
    "get_transcriber",
    "BaseTranscriber",
    "TranscriptionResult",
    "WordTimestamp",
    "GroqTranscriber",
    "OpenAITranscriber",
    "LocalTranscriber",
    # Analyzers
    "get_analyzer",
    "BaseAnalyzer",
    "AnalysisResult",
    "GroqAnalyzer",
    "GeminiAnalyzer",
    "OpenAIAnalyzer",
    "OllamaAnalyzer",
    # Renderer
    "VideoRenderer",
    "RenderError",
    "calculate_crop_params",
    # Feature flags
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
