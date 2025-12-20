# AGENTS.md - AI Context for SmartClip AI

This document provides context for AI assistants working with the SmartClip AI codebase.

## Project Overview

SmartClip AI (`sclip`) is a Python CLI tool that transforms long-form videos (podcasts, interviews, webinars) into viral-ready short clips using Google Gemini AI. It automatically identifies engaging moments, generates word-level captions, and renders clips with customizable aspect ratios and caption styles.

## Tech Stack

- **Language**: Python 3.10+
- **CLI Framework**: Click
- **AI Service**: Google Gemini API (`google-genai` SDK)
- **Video Processing**: FFmpeg (external dependency)
- **YouTube Downloads**: yt-dlp
- **Console Output**: Rich library
- **Package Management**: pip / pyproject.toml

## Architecture

```
src/
├── main.py              # CLI entry point (Click commands)
├── commands/            # Command handlers
│   ├── clip.py          # Main workflow orchestration
│   └── setup.py         # Setup wizard
├── services/            # Core business logic
│   ├── downloader.py    # YouTube download (yt-dlp wrapper)
│   ├── gemini.py        # Gemini AI client for video analysis
│   └── renderer.py      # FFmpeg video rendering
├── utils/               # Utility modules
│   ├── captions.py      # ASS subtitle generation
│   ├── cleanup.py       # Temp file management
│   ├── config.py        # Config file (~/.sclip/config.json)
│   ├── ffmpeg.py        # FFmpeg detection & execution
│   ├── logger.py        # Rich console output
│   ├── validation.py    # Input validation
│   └── video.py         # Video analysis (ffprobe)
└── types/               # Type definitions
    └── __init__.py      # Dataclasses, TypedDicts, Enums
```

## Key Data Flow

```
User Input (URL/File)
    ↓
Input Validation → Exit if invalid
    ↓
Download (if YouTube URL) → yt-dlp
    ↓
Video Analysis → ffprobe (duration, resolution, codec)
    ↓
Chunking → Split if > 30 min (Gemini context limit)
    ↓
Gemini API Call → Transcription + Viral Moment Detection
    ↓
JSON Parsing → Extract clips data
    ↓
Render Pipeline (FFmpeg)
├── Trim to timestamps
├── Crop to aspect ratio (9:16, 1:1, 16:9)
├── Burn-in captions (ASS subtitles)
└── Encode (H.264 + AAC)
    ↓
Metadata Generation → title.txt, description.txt
    ↓
Cleanup → Remove temp files
    ↓
Output Clips
```

## Core Types (src/types/__init__.py)

```python
# Exit codes for CLI
class ExitCode(IntEnum):
    SUCCESS = 0
    DEPENDENCY_ERROR = 1
    INPUT_ERROR = 2
    OUTPUT_ERROR = 3
    API_ERROR = 4
    PROCESSING_ERROR = 5
    VALIDATION_ERROR = 6
    INTERRUPT = 130

# Type aliases
AspectRatio = Literal["9:16", "1:1", "16:9"]
CaptionStyle = Literal["default", "bold", "minimal", "karaoke"]

# Main dataclasses
@dataclass
class CLIOptions: ...      # All CLI arguments
@dataclass
class VideoInfo: ...       # Video metadata from ffprobe
@dataclass
class ValidationResult: ...# Validation results
@dataclass
class Config: ...          # App configuration

# TypedDicts for Gemini response
class CaptionSegment(TypedDict): ...  # {start, end, text}
class ClipData(TypedDict): ...        # {start_time, end_time, title, description, captions}
class GeminiResponse(TypedDict): ...  # {clips: list[ClipData]}
```

## Key Services

### GeminiClient (src/services/gemini.py)
- Uploads video to Gemini API
- Analyzes for "viral moments" with engagement potential
- Returns JSON with timestamps, titles, descriptions, word-level captions
- Supports chunked analysis for videos > 30 minutes
- Implements retry logic with exponential backoff

### VideoRenderer (src/services/renderer.py)
- Trims video to clip timestamps
- Crops to target aspect ratio (center crop)
- Burns in ASS subtitles for captions
- Outputs H.264 + AAC in .mp4 container
- Handles batch rendering with error recovery

### YouTubeDownloader (src/services/downloader.py)
- Wraps yt-dlp for YouTube downloads
- Handles private/unavailable/age-restricted videos
- Progress callback support
- Automatic cleanup on error

## CLI Commands

```bash
# Main workflow
sclip -i video.mp4              # Process local file
sclip -u "youtube.com/..."      # Process YouTube URL
sclip -i video.mp4 --dry-run    # Preview without rendering

# Utility commands
sclip --check-deps              # Check dependencies
sclip --setup                   # Interactive setup wizard
sclip -i video.mp4 --info       # Show video info only

# Common options
-n, --max-clips N               # Max clips to generate (default: 5)
-a, --aspect-ratio RATIO        # 9:16, 1:1, or 16:9
-s, --caption-style STYLE       # default, bold, minimal, karaoke
--no-captions                   # Skip caption burn-in
--no-metadata                   # Skip metadata files
-v, --verbose                   # Debug output
-q, --quiet                     # Errors only
```

## Configuration

Config file: `~/.sclip/config.json`

API key priority: CLI flag → `GEMINI_API_KEY` env var → config file

## Testing

Tests are in `tests/` directory. Run with:
```bash
pytest                    # All tests
pytest --cov=src          # With coverage
pytest tests/test_*.py    # Specific file
```

## Common Development Tasks

### Adding a new CLI option
1. Add to `@click.option()` decorators in `src/main.py`
2. Add to `CLIOptions` dataclass in `src/types/__init__.py`
3. Handle in appropriate command handler

### Modifying Gemini prompt
Edit `ANALYSIS_PROMPT` in `src/services/gemini.py`

### Adding a caption style
Add to `CAPTION_STYLES` dict in `src/utils/captions.py`

### Changing video encoding settings
Modify FFmpeg args in `VideoRenderer.render_clip()` in `src/services/renderer.py`

## Error Handling Patterns

- All validation returns `ValidationResult` with `valid`, `error`, `error_code`
- Services raise specific exceptions (e.g., `GeminiAPIError`, `RenderError`)
- Cleanup context ensures temp files are removed on any exit
- Signal handlers (SIGINT/SIGTERM) trigger graceful cleanup

## Dependencies

Required:
- Python 3.10+
- FFmpeg 5.0+ (external)
- click, rich, google-genai

Optional:
- yt-dlp (for YouTube support)

## Supported Formats

Input: `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.m4v`, `.mpeg`, `.mpg`, `.flv`
Output: `.mp4` (H.264 video + AAC audio)

## Important Constraints

- Videos must be >= 60 seconds
- Videos > 30 minutes are automatically chunked for Gemini
- Gemini free tier has rate limits
- FFmpeg must be installed and in PATH (or specified via --ffmpeg-path)
