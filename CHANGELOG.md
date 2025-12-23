# Changelog

All notable changes to SmartClip AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.5] - 2024-12-23

### Added
- **Custom OpenAI-Compatible Base URL** (`--openai-base-url`)
  - Use any OpenAI-compatible API endpoint (Together AI, OpenRouter, Fireworks, LM Studio, vLLM, etc.)
  - Combine with `--analyzer openai` and `--analyzer-model` for full flexibility
  - Supports local LLM servers with OpenAI-compatible API
  - CLI option: `--openai-base-url <URL>`
  - Saved to config via `sclip --setup`

### Changed
- **Default provider changed from Groq to OpenAI** for both transcription and analysis
- **Default min_duration changed from 45 to 60 seconds**
- OpenAI analyzer now shows custom endpoint domain in provider name
- Improved error messages for custom endpoint authentication
- Setup wizard now includes all settings:
  - API keys (OpenAI, Groq, Gemini, etc.)
  - Custom OpenAI base URL
  - Default transcriber & analyzer
  - **Default transcriber model** (new)
  - **Default analyzer model** (new)
  - Min/max duration
  - Output directory
  - Language, aspect ratio, caption style

### Usage Examples
```bash
# Default (OpenAI for both)
sclip -i video.mp4

# Free alternative with Groq
sclip -i video.mp4 --transcriber groq --analyzer groq

# Together AI
sclip -i video.mp4 --analyzer openai --openai-base-url https://api.together.xyz/v1 \
  --openai-api-key $TOGETHER_API_KEY --analyzer-model meta-llama/Llama-3-70b-chat-hf

# OpenRouter
sclip -i video.mp4 --analyzer openai --openai-base-url https://openrouter.ai/api/v1 \
  --openai-api-key $OPENROUTER_API_KEY --analyzer-model anthropic/claude-3-haiku

# Local LM Studio
sclip -i video.mp4 --analyzer openai --openai-base-url http://localhost:1234/v1 \
  --openai-api-key lm-studio --analyzer-model local-model
```

## [0.2.4] - 2024-12-23

### Added
- **External Subtitle Support** (`--subtitle`)
  - Upload external subtitle file (.srt or .vtt) to skip transcription
  - Faster processing (skip 2-5 min transcription step)
  - No transcription API cost when using external subtitles
  - More accurate captions from professional subtitles
  - Supports both SRT (SubRip) and VTT (WebVTT) formats
  - Word timestamps estimated from segment timing
  - CLI option: `--subtitle path/to/subtitle.srt`

### Changed
- Transcription step is now optional when subtitle file is provided
- API key validation skips transcriber check when using external subtitle
- Dry-run mode shows subtitle source info when using external file

### Usage Examples
```bash
# Use external SRT subtitle (skip transcription)
sclip -i video.mp4 --subtitle subtitle.srt

# Use VTT subtitle with Gemini analyzer
sclip -i video.mp4 --subtitle captions.vtt --analyzer gemini

# Combine with other options
sclip -i podcast.mp4 --subtitle podcast.srt -n 5 -a 9:16 -s bold
```

## [0.2.3] - 2024-12-21

### Added
- **New Transcription Provider: ElevenLabs Scribe**
  - ElevenLabs Scribe API support for speech-to-text
  - 99 language support with high accuracy
  - Word-level timestamps
  - CLI option: `--transcriber elevenlabs`
  - Environment variable: `ELEVENLABS_API_KEY`

- **New Analysis Provider: Mistral AI**
  - Mistral API support for viral moment analysis
  - Free tier available
  - Multiple models: `mistral-small-latest`, `mistral-large-latest`, `open-mistral-nemo`
  - Good multilingual support
  - CLI option: `--analyzer mistral`
  - Environment variable: `MISTRAL_API_KEY`

### Changed
- Updated CLI to support new providers
- Updated config system with new API key getters
- Updated documentation with new provider options

### Provider Summary
**Transcription:**
| Provider | Cost | Speed |
|----------|------|-------|
| Groq (default) | Free | ⚡ Very Fast |
| Deepgram | $200 free credit | ⚡ Very Fast |
| ElevenLabs | Paid | Fast |
| OpenAI | Paid | Fast |
| Local | Free | Depends on HW |

**Analysis:**
| Provider | Cost | Speed |
|----------|------|-------|
| Groq (default) | Free | ⚡ Very Fast |
| DeepSeek | Very affordable | Fast |
| Gemini | Free tier | Fast |
| OpenAI | Paid | Fast |
| Mistral | Free tier | Fast |
| Ollama | Free | Depends on HW |

## [0.2.2] - 2024-12-21

### Added
- **New Transcription Provider: Deepgram Nova**
  - Deepgram Nova-3 API support for speech-to-text
  - $200 free credit for new accounts
  - Very fast transcription with word-level timestamps
  - Multi-language support including Indonesian
  - CLI option: `--transcriber deepgram`
  - Environment variable: `DEEPGRAM_API_KEY`

- **New Analysis Provider: DeepSeek**
  - DeepSeek API support for viral moment analysis
  - Very affordable pricing ($0.028-0.28/M tokens)
  - OpenAI-compatible API
  - Models: `deepseek-chat` (V3), `deepseek-reasoner` (R1)
  - CLI option: `--analyzer deepseek`
  - Environment variable: `DEEPSEEK_API_KEY`

### Changed
- Updated CLI to support new providers
- Updated config system with new API key getters
- Updated documentation with new provider options

### Provider Summary
**Transcription:**
| Provider | Cost | Speed |
|----------|------|-------|
| Groq (default) | Free | ⚡ Very Fast |
| Deepgram | $200 free credit | ⚡ Very Fast |
| OpenAI | Paid | Fast |
| Local | Free | Depends on HW |

**Analysis:**
| Provider | Cost | Speed |
|----------|------|-------|
| Groq (default) | Free | ⚡ Very Fast |
| DeepSeek | Very affordable | Fast |
| Gemini | Free tier | Fast |
| OpenAI | Paid | Fast |
| Ollama | Free | Depends on HW |

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

[0.2.0]: https://github.com/sakirsyarian/sclip/releases/tag/v0.2.0
[0.1.0]: https://github.com/sakirsyarian/sclip/releases/tag/v0.1.0
