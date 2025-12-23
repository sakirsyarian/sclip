# AGENTS.md - AI Context for SmartClip AI

This document provides context for AI assistants working with the SmartClip AI codebase.

## Project Overview

SmartClip AI (`sclip`) is a Python CLI tool that transforms long-form videos (podcasts, interviews, webinars) into viral-ready short clips using AI. It supports multiple AI providers for transcription and analysis, with OpenAI as the default option.

## Tech Stack

- **Language**: Python 3.10+
- **CLI Framework**: Click
- **Transcription**: OpenAI Whisper (default), Groq Whisper, Deepgram Nova, ElevenLabs Scribe, Local faster-whisper
- **Analysis**: OpenAI GPT (default), Groq LLMs, DeepSeek, Gemini, Mistral, Ollama
- **Video Processing**: FFmpeg (external dependency)
- **YouTube Downloads**: yt-dlp
- **Console Output**: Rich library
- **Package Management**: pip / pyproject.toml

## Architecture (v2)

```
src/
├── main.py              # CLI entry point (Click commands)
├── commands/            # Command handlers
│   ├── clip.py          # Main workflow orchestration
│   └── setup.py         # Setup wizard
├── services/            # Core business logic
│   ├── audio.py         # Audio extraction from video
│   ├── downloader.py    # YouTube download (yt-dlp wrapper)
│   ├── renderer.py      # FFmpeg video rendering
│   ├── transcribers/    # Transcription providers
│   │   ├── __init__.py  # Factory function get_transcriber()
│   │   ├── base.py      # BaseTranscriber abstract class
│   │   ├── groq.py      # Groq Whisper API
│   │   ├── openai.py    # OpenAI Whisper API
│   │   ├── deepgram.py  # Deepgram Nova API
│   │   ├── elevenlabs.py # ElevenLabs Scribe API
│   │   └── local.py     # Local faster-whisper
│   └── analyzers/       # Analysis providers
│       ├── __init__.py  # Factory function get_analyzer()
│       ├── base.py      # BaseAnalyzer abstract class
│       ├── groq.py      # Groq LLMs (Llama 3.3, etc.)
│       ├── deepseek.py  # DeepSeek LLMs
│       ├── gemini.py    # Google Gemini
│       ├── openai.py    # OpenAI GPT-4
│       ├── mistral.py   # Mistral AI
│       └── ollama.py    # Local Ollama
├── utils/               # Utility modules
│   ├── captions.py      # ASS subtitle generation
│   ├── cleanup.py       # Temp file management
│   ├── config.py        # Config file (~/.sclip/config.json)
│   ├── ffmpeg.py        # FFmpeg detection & execution
│   ├── logger.py        # Rich console output
│   ├── srt_parser.py    # SRT/VTT subtitle parser
│   ├── validation.py    # Input validation
│   └── video.py         # Video analysis (ffprobe)
└── types/               # Type definitions
    └── __init__.py      # Dataclasses, TypedDicts, Enums
```

## Key Data Flow (v2)

```
User Input (URL/File)
    ↓
Input Validation → Exit if invalid
    ↓
Download (if YouTube URL) → yt-dlp
    ↓
Video Analysis → ffprobe (duration, resolution, codec)
    ↓
[If --subtitle provided]
├── Parse Subtitle File → SRT/VTT parser
└── Skip to Analysis
    ↓
[If no subtitle]
├── Audio Extraction → FFmpeg (mp3, 16kHz, mono)
└── Transcription → Whisper (Groq/OpenAI/Local)
    ↓
Analysis → LLM (Groq/Gemini/OpenAI/Ollama)
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
TranscriberProvider = Literal["groq", "openai", "deepgram", "elevenlabs", "local"]
AnalyzerProvider = Literal["groq", "deepseek", "gemini", "openai", "mistral", "ollama"]

# Main dataclasses
@dataclass
class CLIOptions:
    # Input/Output
    url: str | None
    input: str | None
    output: str
    # Clip settings
    max_clips: int
    min_duration: int
    max_duration: int
    aspect_ratio: AspectRatio
    caption_style: CaptionStyle
    language: str
    # Provider options
    transcriber: TranscriberProvider  # default: "openai"
    analyzer: AnalyzerProvider        # default: "openai"
    groq_api_key: str | None
    openai_api_key: str | None
    gemini_api_key: str | None
    deepgram_api_key: str | None
    deepseek_api_key: str | None
    elevenlabs_api_key: str | None
    mistral_api_key: str | None
    transcriber_model: str | None
    analyzer_model: str | None
    ollama_host: str
    ...

# TypedDicts
class CaptionSegment(TypedDict): ...  # {start, end, text}
class ClipData(TypedDict): ...        # {start_time, end_time, title, description, captions}
```


## Key Services

### Transcribers (src/services/transcribers/)

Factory: `get_transcriber(provider, api_key, model) -> BaseTranscriber`

| Provider | Class | Default Model | Features |
|----------|-------|---------------|----------|
| openai | OpenAITranscriber | whisper-1 | Default, high quality, 25MB limit |
| groq | GroqTranscriber | whisper-large-v3-turbo | Free, fast, 25MB limit |
| deepgram | DeepgramTranscriber | nova-3 | $200 free credit, very fast |
| elevenlabs | ElevenLabsTranscriber | scribe_v1 | 99 languages, word timestamps |
| local | LocalTranscriber | base | Offline, no limit |

```python
from src.services.transcribers import get_transcriber

transcriber = get_transcriber("groq", api_key="...")
result = await transcriber.transcribe("audio.mp3", language="id")
# result.text, result.words (with timestamps), result.duration
```

### Analyzers (src/services/analyzers/)

Factory: `get_analyzer(provider, api_key, model, **kwargs) -> BaseAnalyzer`

| Provider | Class | Default Model | Features |
|----------|-------|---------------|----------|
| openai | OpenAIAnalyzer | gpt-4o-mini | Default, high quality, custom base URL |
| groq | GroqAnalyzer | openai/gpt-oss-120b | Free, very fast |
| deepseek | DeepSeekAnalyzer | deepseek-chat | Very affordable |
| gemini | GeminiAnalyzer | gemini-2.0-flash | Free tier, large context |
| mistral | MistralAnalyzer | mistral-small-latest | Free tier available |
| ollama | OllamaAnalyzer | llama3.2 | Offline, local |

```python
from src.services.analyzers import get_analyzer

analyzer = get_analyzer("groq", api_key="...")
result = await analyzer.analyze(transcription, video_duration, max_clips=5)
# result.clips: list[ClipData]
```

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
# Main workflow (default: OpenAI for both)
sclip -i video.mp4              # Process local file
sclip -u "youtube.com/..."      # Process YouTube URL
sclip -i video.mp4 --dry-run    # Preview without rendering

# External subtitle (skip transcription - faster!)
sclip -i video.mp4 --subtitle subtitle.srt
sclip -i video.mp4 --subtitle captions.vtt --analyzer gemini

# Provider options
sclip -i video.mp4 --transcriber openai --analyzer openai  # Default
sclip -i video.mp4 --transcriber groq --analyzer groq      # Free alternative
sclip -i video.mp4 --transcriber local --analyzer ollama   # Offline
sclip -i video.mp4 --analyzer gemini                       # Use Gemini

# Custom OpenAI-compatible endpoint
sclip -i video.mp4 --analyzer openai --openai-base-url https://api.together.xyz/v1 --analyzer-model meta-llama/Llama-3-70b-chat-hf
sclip -i video.mp4 --analyzer openai --openai-base-url http://localhost:1234/v1 --analyzer-model local-model

# Utility commands
sclip --check-deps              # Check dependencies
sclip --setup                   # Interactive setup wizard
sclip -i video.mp4 --info       # Show video info only

# Common options
-n, --max-clips N               # Max clips to generate (default: 5)
--min-duration N                # Min clip duration (default: 60)
--max-duration N                # Max clip duration (default: 180)
-a, --aspect-ratio RATIO        # 9:16, 1:1, or 16:9
-s, --caption-style STYLE       # default, bold, minimal, karaoke
--no-captions                   # Skip caption burn-in
--no-metadata                   # Skip metadata files
-v, --verbose                   # Debug output
-q, --quiet                     # Errors only
```

## Configuration

Config file: `~/.sclip/config.json`

API key priority: CLI flag → Environment variable → Config file

```json
{
  "openai_api_key": "sk-xxx",
  "openai_base_url": "https://api.together.xyz/v1",
  "default_transcriber": "openai",
  "default_analyzer": "openai",
  "default_transcriber_model": "whisper-1",
  "default_analyzer_model": "gpt-4o-mini",
  "default_language": "id",
  "min_duration": 60,
  "max_duration": 180
}
```

Environment variables:
- `OPENAI_API_KEY` - OpenAI API key (default provider)
- `OPENAI_BASE_URL` - Custom OpenAI-compatible API URL (Together AI, OpenRouter, etc.)
- `GROQ_API_KEY` - Groq API key (free alternative)
- `DEEPGRAM_API_KEY` - Deepgram API key ($200 free credit)
- `ELEVENLABS_API_KEY` - ElevenLabs API key (99 languages)
- `DEEPSEEK_API_KEY` - DeepSeek API key (very affordable)
- `GEMINI_API_KEY` - Google Gemini API key
- `MISTRAL_API_KEY` - Mistral API key (free tier available)
- `OLLAMA_HOST` - Ollama server URL (default: http://localhost:11434)

## Common Development Tasks

### Adding a new transcription provider
1. Create `src/services/transcribers/newprovider.py`
2. Extend `BaseTranscriber` class
3. Implement `transcribe()`, `is_available()`, `name`, `default_model`
4. Register in `src/services/transcribers/__init__.py`

### Adding a new analysis provider
1. Create `src/services/analyzers/newprovider.py`
2. Extend `BaseAnalyzer` class
3. Implement `analyze()`, `is_available()`, `name`, `default_model`
4. Register in `src/services/analyzers/__init__.py`

### Modifying analysis prompt
Edit `ANALYSIS_PROMPT` in `src/services/analyzers/base.py`

### Adding a caption style
Add to `CAPTION_STYLES` dict in `src/utils/captions.py`

### Changing video encoding settings
Modify FFmpeg args in `VideoRenderer.render_clip()` in `src/services/renderer.py`

## Error Handling Patterns

- All validation returns `ValidationResult` with `valid`, `error`, `error_code`
- Transcribers raise `TranscriptionError`, `TranscriptionAPIError`, `TranscriptionFileError`
- Analyzers raise `AnalysisError`, `AnalysisAPIError`, `AnalysisParseError`
- Cleanup context ensures temp files are removed on any exit
- Signal handlers (SIGINT/SIGTERM) trigger graceful cleanup

## Dependencies

Required:
- Python 3.10+
- FFmpeg 5.0+ (external)
- click, rich, groq

Optional:
- yt-dlp (for YouTube support)
- deepgram-sdk (for Deepgram transcriber)
- elevenlabs (for ElevenLabs transcriber)
- google-genai (for Gemini analyzer)
- openai (for OpenAI/DeepSeek transcriber/analyzer)
- mistralai (for Mistral analyzer)
- faster-whisper (for local transcription)
- httpx (for Ollama analyzer)

## Supported Formats

Input: `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.m4v`, `.mpeg`, `.mpg`, `.flv`
Output: `.mp4` (H.264 video + AAC audio)

## Important Constraints

- Videos must be >= 60 seconds
- Groq Whisper: 25MB audio file limit (free tier)
- OpenAI Whisper: 25MB audio file limit
- Local Whisper: No limit, but slower on CPU
- FFmpeg must be installed and in PATH (or specified via --ffmpeg-path)
