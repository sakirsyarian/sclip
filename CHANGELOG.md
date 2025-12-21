# Changelog

All notable changes to SmartClip AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2024-12-21

### Changed
- **Improved Setup Wizard** (`sclip --setup`)
  - Now supports all API keys: Groq (default), OpenAI, Gemini
  - Added default provider selection (transcriber & analyzer)
  - Added local/offline options setup (Ollama, faster-whisper)
  - Added default settings configuration (language, aspect ratio, caption style)
  - Groq highlighted as FREE and recommended
- **Updated Config System**
  - Config now stores all API keys (groq, openai, gemini)
  - Added default provider settings
  - Added language preference
  - New helper functions: `get_groq_api_key()`, `get_openai_api_key()`, `get_gemini_api_key()`, `get_ollama_host()`
- **Improved `--check-deps`**
  - Shows Groq as default with "[DEFAULT - FREE]" label
  - Better messaging for missing API keys

### Fixed
- Setup wizard now asks for Groq API key first (was only asking for Gemini)
- API key resolution now properly checks CLI → env var → config file

## [0.2.0] - 2024-12-21

### Added

#### Multi-Provider Architecture
- **Transcription Providers**: Support for multiple speech-to-text backends
  - Groq Whisper API (default, free, fast)
  - OpenAI Whisper API (paid, high quality)
  - Local faster-whisper (offline, no API needed)
- **Analysis Providers**: Support for multiple LLM backends
  - Groq LLMs (default, free, very fast) - Llama 3.3, Mixtral
  - Google Gemini (free tier available)
  - OpenAI GPT-4 (paid, high quality)
  - Ollama (offline, local LLMs)

#### New CLI Options
- `--transcriber` - Choose transcription provider (groq, openai, local)
- `--analyzer` - Choose analysis provider (groq, gemini, openai, ollama)
- `--groq-api-key` - Groq API key
- `--openai-api-key` - OpenAI API key
- `--gemini-api-key` - Gemini API key
- `--transcriber-model` - Custom model for transcription
- `--analyzer-model` - Custom model for analysis
- `--ollama-host` - Custom Ollama server URL

#### New Services
- `src/services/audio.py` - Audio extraction from video
- `src/services/transcribers/` - Transcription provider modules
- `src/services/analyzers/` - Analysis provider modules

### Changed
- **Default provider changed from Gemini to Groq** (100% free)
- New workflow: Video → Audio → Transcribe → Analyze → Render
- Removed video upload to AI (now uses audio-only approach)
- Removed chunking logic (no longer needed with audio transcription)
- Updated `--check-deps` to show all provider statuses

### Removed
- `--audio-only` flag (now always uses audio extraction)
- `--model` flag (replaced by `--analyzer-model`)
- `--api-key` flag (replaced by provider-specific flags)
- Video chunking for long videos (no longer needed)

### Performance
- Faster processing: Audio extraction is much faster than video upload
- No file size limits for local transcription
- Parallel rendering for multiple clips

### Documentation
- Updated README with new architecture and provider options
- Updated AGENTS.md with new service structure
- Added provider comparison tables

## [Unreleased]

### Added
- Parallel clip rendering using ThreadPoolExecutor for improved performance
- Hardware acceleration detection (NVENC, VideoToolbox, VAAPI, QSV)
- Video analysis caching to avoid redundant ffprobe calls
- Pre-compiled regex patterns in caption generation

### Changed
- VideoRenderer now supports parallel rendering by default for multiple clips
- Video analysis results are cached based on file path and modification time
- Optimized FFmpeg encoding with hardware acceleration when available

### Performance
- Parallel rendering can reduce total render time by up to 4x on multi-core systems
- Hardware acceleration (when available) provides 2-5x faster encoding
- Video info caching eliminates redundant ffprobe calls during batch operations

## [0.1.0] - 2024-12-20

### Added

#### Core Features
- AI-powered viral moment detection using Google Gemini API
- Automatic word-level caption generation with precise timestamps
- Video rendering with caption burn-in using FFmpeg
- Support for multiple aspect ratios: 9:16 (vertical), 1:1 (square), 16:9 (landscape)
- YouTube video download support via yt-dlp integration
- SEO-optimized title and description generation for each clip

#### CLI Interface
- Main command `sclip` with comprehensive options
- Input options: `--url` / `-u` for YouTube URLs, `--input` / `-i` for local files
- Output options: `--output` / `-o`, `--force` / `-f`, `--no-metadata`
- Clip settings: `--max-clips` / `-n`, `--min-duration`, `--max-duration`
- Caption options: `--caption-style` / `-s`, `--no-captions`, `--language` / `-l`
- Utility commands: `--check-deps`, `--setup`, `--info`, `--dry-run`
- Debug options: `--verbose` / `-v`, `--quiet` / `-q`, `--keep-temp`
- Version and help: `--version`, `--help` / `-h`

#### Caption Styles
- `default` - White text with black outline, bottom-center position
- `bold` - Large yellow text with heavy shadow, center position
- `minimal` - Small white text with subtle shadow, clean look
- `karaoke` - Word-by-word green highlight animation

#### Video Processing
- Automatic video analysis using FFprobe
- Smart center cropping for aspect ratio conversion
- H.264 video + AAC audio output encoding
- Support for input formats: `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.m4v`, `.mpeg`, `.mpg`, `.flv`

#### Configuration
- Config file support at `~/.sclip/config.json`
- Environment variable support (`GEMINI_API_KEY`)
- API key priority: CLI flag → Environment variable → Config file
- Interactive setup wizard (`--setup`)

#### Developer Experience
- Comprehensive type definitions with dataclasses and TypedDicts
- Rich console output with spinners and progress bars
- Structured exit codes for different error types
- Automatic temp file cleanup on success, failure, or interrupt (Ctrl+C)
- Signal handlers for graceful shutdown (SIGINT/SIGTERM)

#### Documentation
- Complete README with installation guide and usage examples
- AGENTS.md for AI assistant context
- Inline code documentation

### Technical Details

#### Dependencies
- Python 3.10+ required
- click >= 8.1.0 (CLI framework)
- rich >= 13.0.0 (console output)
- google-genai >= 1.0.0 (Gemini API)
- yt-dlp >= 2024.1.0 (YouTube downloads)
- FFmpeg 5.0+ (external, video processing)

#### Architecture
- Layered architecture: CLI → Commands → Services → Utils
- Multi-provider design: Transcribers (Groq, OpenAI, Local) + Analyzers (Groq, Gemini, OpenAI, Ollama)
- Utility modules: validation, config, logger, cleanup, ffmpeg, captions, video

### Known Limitations
- Videos must be at least 60 seconds long
- Groq/OpenAI Whisper API: 25MB audio file limit
- Free tier providers have rate limits
- No GUI (CLI only for MVP)
- No direct social media posting

---

## Future Releases

### Planned for v1.0.0
- Face tracking and speaker detection
- Direct social media posting
- GUI application
- Batch processing mode
- Custom caption templates

[0.2.0]: https://github.com/sarian/sclip/releases/tag/v0.2.0
[0.1.0]: https://github.com/sarian/sclip/releases/tag/v0.1.0
