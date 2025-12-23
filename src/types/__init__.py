"""Type definitions for SmartClip AI.

This module contains all type definitions, dataclasses, TypedDicts, and enums
used throughout the SmartClip AI application. Centralizing types here ensures
consistency and makes it easy to understand the data structures used.

Types defined:
    - ExitCode: CLI exit codes for different error conditions
    - AspectRatio: Supported video aspect ratios
    - CaptionStyle: Available caption style presets
    - CLIOptions: All command-line arguments
    - VideoInfo: Video metadata from ffprobe analysis
    - CaptionSegment: Single caption with timing
    - ClipData: AI-identified clip with metadata
    - GeminiResponse: Response structure from Gemini API
    - ValidationResult: Result of validation operations
    - Config: Application configuration settings
"""

from dataclasses import dataclass
from typing import TypedDict, Literal
from enum import IntEnum


class ExitCode(IntEnum):
    """Exit codes for CLI operations.
    
    These codes follow Unix conventions where 0 indicates success
    and non-zero values indicate various error conditions.
    
    Attributes:
        SUCCESS: Operation completed successfully (0)
        DEPENDENCY_ERROR: Missing required dependency like FFmpeg (1)
        INPUT_ERROR: Invalid input file or URL (2)
        OUTPUT_ERROR: Cannot write to output directory (3)
        API_ERROR: Gemini API error (rate limit, auth, etc.) (4)
        PROCESSING_ERROR: Error during video processing (5)
        VALIDATION_ERROR: Invalid CLI options or configuration (6)
        INTERRUPT: User interrupted with Ctrl+C (130, standard Unix convention)
    """
    SUCCESS = 0
    DEPENDENCY_ERROR = 1
    INPUT_ERROR = 2
    OUTPUT_ERROR = 3
    API_ERROR = 4
    PROCESSING_ERROR = 5
    VALIDATION_ERROR = 6
    INTERRUPT = 130  # Standard Unix exit code for SIGINT (128 + 2)


# Type aliases for constrained string literals
# These ensure type safety when working with aspect ratios and caption styles

AspectRatio = Literal["9:16", "1:1", "16:9"]
"""Supported video aspect ratios.
- "9:16": Vertical/portrait (TikTok, Reels, Shorts)
- "1:1": Square (Instagram feed)
- "16:9": Horizontal/landscape (YouTube, standard video)
"""

CaptionStyle = Literal["default", "bold", "minimal", "karaoke"]
"""Available caption style presets.
- "default": White text with black outline, bottom position
- "bold": Large yellow Impact font, centered
- "minimal": Small subtle text, bottom position
- "karaoke": Word-by-word highlight effect
"""


# Type aliases for provider options
TranscriberProvider = Literal["groq", "openai", "deepgram", "elevenlabs", "local"]
"""Supported transcription providers.
- "groq": Groq Whisper API (fast, free tier) - default
- "openai": OpenAI Whisper API
- "deepgram": Deepgram Nova API ($200 free credit)
- "elevenlabs": ElevenLabs Scribe (99 languages)
- "local": Local faster-whisper (offline)
"""

AnalyzerProvider = Literal["groq", "deepseek", "gemini", "openai", "mistral", "ollama"]
"""Supported analysis providers.
- "groq": Groq LLMs (fast, free tier) - default
- "deepseek": DeepSeek LLMs (very affordable)
- "gemini": Google Gemini
- "openai": OpenAI GPT-4
- "mistral": Mistral AI (free tier available)
- "ollama": Local LLMs (offline)
"""


@dataclass
class CLIOptions:
    """Options parsed from CLI arguments.
    
    This dataclass holds all command-line options passed to sclip.
    Default values match the CLI defaults defined in main.py.
    
    Attributes:
        url: YouTube URL to download and process (mutually exclusive with input)
        input: Path to local video file (mutually exclusive with url)
        output: Output directory for generated clips
        subtitle: Path to external subtitle file (.srt or .vtt) to skip transcription
        max_clips: Maximum number of clips to generate (1-10 recommended)
        min_duration: Minimum clip duration in seconds
        max_duration: Maximum clip duration in seconds
        aspect_ratio: Target aspect ratio for output clips
        caption_style: Caption style preset to use
        language: Language code for captions (ISO 639-1, e.g., 'en', 'id')
        force: If True, overwrite existing output files
        verbose: If True, show debug output
        quiet: If True, suppress all output except errors
        dry_run: If True, analyze without rendering
        no_captions: If True, skip caption burn-in
        no_metadata: If True, skip metadata file generation
        keep_temp: If True, keep temporary files for debugging
        ffmpeg_path: Custom path to FFmpeg executable
        
        # Provider options (new architecture)
        transcriber: Transcription provider (groq, openai, local)
        analyzer: Analysis provider (groq, gemini, openai, ollama)
        groq_api_key: Groq API key
        openai_api_key: OpenAI API key
        gemini_api_key: Gemini API key
        transcriber_model: Model for transcription
        analyzer_model: Model for analysis
        ollama_host: Ollama server host URL
    """
    url: str | None = None
    input: str | None = None
    output: str = "./output"
    subtitle: str | None = None  # External subtitle file path
    max_clips: int = 5
    min_duration: int = 60
    max_duration: int = 180
    aspect_ratio: AspectRatio = "9:16"
    caption_style: CaptionStyle = "default"
    language: str = "id"  # Default to Indonesian
    force: bool = False
    verbose: bool = False
    quiet: bool = False
    dry_run: bool = False
    no_captions: bool = False
    no_metadata: bool = False
    keep_temp: bool = False
    ffmpeg_path: str | None = None
    
    # Provider options (new architecture)
    transcriber: TranscriberProvider = "openai"
    analyzer: AnalyzerProvider = "openai"
    groq_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    deepgram_api_key: str | None = None
    deepseek_api_key: str | None = None
    elevenlabs_api_key: str | None = None
    mistral_api_key: str | None = None
    transcriber_model: str | None = None
    analyzer_model: str | None = None
    ollama_host: str = "http://localhost:11434"
    
    # Custom OpenAI-compatible endpoint
    openai_base_url: str | None = None  # Custom base URL for OpenAI-compatible APIs
    
    # Legacy options (deprecated, kept for backward compatibility)
    api_key: str | None = None  # Deprecated: use gemini_api_key
    model: str = "gemini-2.0-flash"  # Deprecated: use analyzer_model
    audio_only: bool = False  # Deprecated: new architecture always uses audio


@dataclass
class VideoInfo:
    """Information about a video file extracted via ffprobe.
    
    Contains technical metadata about a video file that is used
    for validation, rendering decisions, and user display.
    
    Attributes:
        path: Absolute or relative path to the video file
        duration: Video duration in seconds (float for precision)
        width: Video width in pixels
        height: Video height in pixels
        codec: Video codec name (e.g., 'h264', 'vp9')
        audio_codec: Audio codec name (e.g., 'aac', 'opus', 'none')
        bitrate: Video bitrate in bits per second (0 if unknown)
        fps: Frame rate as float (e.g., 29.97, 30.0)
    """
    path: str
    duration: float
    width: int
    height: int
    codec: str
    audio_codec: str
    bitrate: int
    fps: float


class CaptionSegment(TypedDict):
    """A single caption segment with timing information.
    
    Represents one phrase or word in the caption track.
    Used for word-level or phrase-level caption synchronization.
    
    Attributes:
        start: Start time in seconds (relative to video start)
        end: End time in seconds (relative to video start)
        text: The caption text to display
    """
    start: float
    end: float
    text: str


class ClipData(TypedDict):
    """Data for a single clip identified by AI analysis.
    
    Contains all information needed to render a clip and generate
    its metadata files. Returned by Gemini API analysis.
    
    Attributes:
        start_time: Clip start time in seconds (relative to source video)
        end_time: Clip end time in seconds (relative to source video)
        title: Catchy, clickbait-style title (max 60 chars)
        description: SEO-optimized description (max 200 chars)
        captions: List of caption segments with word-level timing
    """
    start_time: float
    end_time: float
    title: str
    description: str
    captions: list[CaptionSegment]


class GeminiResponse(TypedDict):
    """Response structure from Gemini API video analysis.
    
    The Gemini API returns JSON that is parsed into this structure.
    Contains a list of identified viral-worthy clips.
    
    Attributes:
        clips: List of ClipData objects for identified moments
    """
    clips: list[ClipData]


@dataclass
class ValidationResult:
    """Result of a validation operation.
    
    Used throughout the codebase to return validation status
    with optional error details. Enables consistent error handling.
    
    Attributes:
        valid: True if validation passed, False otherwise
        error: Human-readable error message (None if valid)
        error_code: Exit code to use if validation failed (None if valid)
    
    Example:
        result = validate_input_file("video.mp4")
        if not result.valid:
            print(result.error)
            sys.exit(result.error_code)
    """
    valid: bool
    error: str | None = None
    error_code: ExitCode | None = None


@dataclass
class Config:
    """Application configuration stored in ~/.sclip/config.json.
    
    Persists user preferences and credentials between sessions.
    Values can be overridden by environment variables or CLI arguments.
    
    Attributes:
        # API Keys
        groq_api_key: Groq API key (for transcription + analysis, default provider)
        openai_api_key: OpenAI API key (for transcription + analysis)
        gemini_api_key: Gemini API key (for analysis only)
        
        # Provider defaults
        default_transcriber: Default transcription provider
        default_analyzer: Default analysis provider
        default_transcriber_model: Default model for transcription
        default_analyzer_model: Default model for analysis
        ollama_host: Ollama server URL for local LLM
        openai_base_url: Custom base URL for OpenAI-compatible APIs
        
        # FFmpeg
        ffmpeg_path: Custom FFmpeg path (if not in PATH)
        
        # Output defaults
        default_output_dir: Default output directory for clips
        default_aspect_ratio: Default aspect ratio for clips
        default_caption_style: Default caption style preset
        default_language: Default language for transcription
        
        # Clip settings
        max_clips: Default maximum clips to generate
        min_duration: Default minimum clip duration
        max_duration: Default maximum clip duration
    """
    # API Keys (Groq is default/recommended - free!)
    groq_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    deepgram_api_key: str | None = None
    deepseek_api_key: str | None = None
    elevenlabs_api_key: str | None = None
    mistral_api_key: str | None = None
    
    # Provider defaults
    default_transcriber: TranscriberProvider = "openai"
    default_analyzer: AnalyzerProvider = "openai"
    default_transcriber_model: str | None = None
    default_analyzer_model: str | None = None
    ollama_host: str = "http://localhost:11434"
    openai_base_url: str | None = None  # Custom base URL for OpenAI-compatible APIs
    
    # FFmpeg
    ffmpeg_path: str | None = None
    
    # Output defaults
    default_output_dir: str = "./output"
    default_aspect_ratio: AspectRatio = "9:16"
    default_caption_style: CaptionStyle = "default"
    default_language: str = "id"  # Indonesian default
    
    # Clip settings
    max_clips: int = 5
    min_duration: int = 60
    max_duration: int = 180
    
    # Legacy (deprecated, kept for backward compatibility)
    default_model: str = "gemini-2.0-flash"


# Export all types
__all__ = [
    "ExitCode",
    "AspectRatio",
    "CaptionStyle",
    "TranscriberProvider",
    "AnalyzerProvider",
    "CLIOptions",
    "VideoInfo",
    "CaptionSegment",
    "ClipData",
    "GeminiResponse",
    "ValidationResult",
    "Config",
]
