# Changelog

All notable changes to SmartClip AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- Service-based design: Downloader, Gemini, Renderer
- Utility modules: validation, config, logger, cleanup, ffmpeg, captions, video

### Known Limitations
- Videos must be at least 60 seconds long
- Videos longer than 30 minutes are automatically chunked for Gemini API
- Gemini free tier has rate limits
- No GUI (CLI only for MVP)
- No direct social media posting
- No face tracking/speaker detection

---

## Future Releases

### Planned for v0.2.0
- Unit tests for utility modules
- Integration tests for services
- CI/CD pipeline setup

### Planned for v1.0.0
- Face tracking and speaker detection
- Direct social media posting
- GUI application
- Batch processing mode
- Custom caption templates

[0.1.0]: https://github.com/sarian/sclip/releases/tag/v0.1.0
