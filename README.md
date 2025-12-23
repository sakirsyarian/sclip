# SmartClip AI 🎬✨

Transform long-form videos into viral-ready short clips using AI.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

SmartClip AI is a CLI tool that automatically identifies the most engaging moments in your videos (podcasts, interviews, webinars) and transforms them into short-form content ready for TikTok, Instagram Reels, and YouTube Shorts.

**Key Features:**
- 🤖 Multi-provider AI support (Groq, Gemini, OpenAI, Ollama)
- 🎙️ Fast transcription with Whisper (Groq, OpenAI, or local)
- 📝 Automatic word-level caption generation and burn-in
- 🎯 Smart cropping to vertical (9:16), square (1:1), or landscape (16:9)
- � YoOuTube URL support via yt-dlp
- 📊 SEO-optimized titles and descriptions for each clip
- 💰 **100% Free** with Groq (default provider)
- 🔒 **Offline mode** with local Whisper + Ollama

## Architecture (v2)

```
Video → Extract Audio → Transcribe (Whisper) → Analyze (LLM) → Render
```

**Transcription Providers:**
| Provider | Speed | Cost | Offline |
|----------|-------|------|---------|
| OpenAI Whisper (default) | Fast | $0.006/min | ❌ |
| Groq Whisper | ⚡ Very Fast | Free | ❌ |
| Deepgram Nova | ⚡ Very Fast | $200 free credit | ❌ |
| ElevenLabs Scribe | Fast | Paid | ❌ |
| Local (faster-whisper) | Depends on HW | Free | ✅ |

**Analysis Providers:**
| Provider | Speed | Cost | Offline |
|----------|-------|------|---------|
| OpenAI GPT-4 (default) | Fast | Paid | ❌ |
| Groq (Llama 3.3) | ⚡ Very Fast | Free | ❌ |
| DeepSeek | Fast | Very affordable | ❌ |
| Gemini | Fast | Free tier | ❌ |
| Mistral | Fast | Free tier | ❌ |
| Ollama | Depends on HW | Free | ✅ |

## 🚀 Try it on Google Colab (No Installation Required!)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sakirsyarian/sclip/blob/main/smartclip_colab.ipynb)

Tidak perlu install apa-apa! Jalankan SmartClip AI langsung di browser dengan GPU gratis.

👉 **[Panduan Lengkap Google Colab (Bahasa Indonesia)](COLAB_GUIDE.md)**

## Table of Contents

- [Google Colab](#-try-it-on-google-colab-no-installation-required)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
- [CLI Reference](#cli-reference)
- [Caption Styles](#caption-styles)
- [Configuration](#configuration)
- [Output Structure](#output-structure)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## Requirements

- Python 3.10+
- FFmpeg 5.0+
- API Key (one of):
  - Groq API key ([Get free](https://console.groq.com)) - **Recommended**
  - Google Gemini API key ([Get free](https://aistudio.google.com/apikey))
  - OpenAI API key (paid)
- yt-dlp (optional, for YouTube downloads)

## Installation

### 1. Install sclip

```bash
# Clone the repository
git clone https://github.com/sakirsyarian/sclip.git
cd sclip

# Install with pip (recommended)
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

### 2. Install FFmpeg

**Windows:**
```bash
# Using winget
winget install FFmpeg

# Or using Chocolatey
choco install ffmpeg

# Or download from https://ffmpeg.org/download.html
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg
```

### 3. Install yt-dlp (Optional - for YouTube support)

```bash
pip install yt-dlp
```

### 4. Configure API Key

```bash
# Option 1: OpenAI API key (DEFAULT - high quality)
export OPENAI_API_KEY="your-openai-api-key"

# Option 2: Groq API key (free & fast alternative)
export GROQ_API_KEY="your-groq-api-key"

# Option 3: Gemini API key (optional, for Gemini analyzer)
export GEMINI_API_KEY="your-gemini-api-key"

# Or run setup wizard
sclip --setup
```

Get your API keys:
- **OpenAI**: [platform.openai.com](https://platform.openai.com/api-keys) (Default)
- **Groq**: [console.groq.com](https://console.groq.com) (Free alternative)
- **Gemini**: [aistudio.google.com](https://aistudio.google.com/apikey)

### 5. Verify Installation

```bash
sclip --check-deps
```

Expected output:
```
Checking dependencies...
✓ Python: 3.11.0
✓ FFmpeg: 6.0 (/usr/bin/ffmpeg)
✓ FFprobe: 6.0 (/usr/bin/ffprobe)
✓ yt-dlp: found (/usr/bin/yt-dlp)

API Keys:
  ✓ OPENAI_API_KEY: configured (sk-...xxxx) [DEFAULT]
  ⚠ GROQ_API_KEY: not configured (optional - free alternative)
  ⚠ GEMINI_API_KEY: not configured (optional)

Local Providers:
  ⚠ faster-whisper: not installed (pip install faster-whisper)
  ⚠ Ollama: not running (start with 'ollama serve')

All required dependencies are available!

Default setup:
  --transcriber openai --analyzer openai

Free alternative:
  --transcriber groq --analyzer groq

Offline setup:
  --transcriber local --analyzer ollama
```

## Quick Start

```bash
# Process a local video (default: OpenAI transcription + OpenAI analysis)
sclip -i podcast.mp4

# Process a YouTube video
sclip -u "https://youtube.com/watch?v=xxxxx"

# Preview clips without rendering (dry run)
sclip -i video.mp4 --dry-run

# Use Groq for free alternative
sclip -i video.mp4 --transcriber groq --analyzer groq

# Fully offline mode (requires faster-whisper + Ollama)
sclip -i video.mp4 --transcriber local --analyzer ollama
```

## Usage Examples

### Basic Usage

```bash
# Process local video with default settings (5 clips, 9:16 vertical)
sclip -i interview.mp4

# Process YouTube video
sclip -u "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Specify output directory
sclip -i podcast.mp4 -o ./my-clips
```

### Controlling Clip Generation

```bash
# Generate exactly 3 clips
sclip -i video.mp4 -n 3

# Set duration range: 60-120 seconds per clip
sclip -i video.mp4 --min-duration 60 --max-duration 120

# Generate shorter clips (30-90 seconds)
sclip -i webinar.mp4 --min-duration 30 --max-duration 90
```

### Aspect Ratio Options

```bash
# Vertical for TikTok/Reels/Shorts (default)
sclip -i video.mp4 -a 9:16

# Square for Instagram feed
sclip -i video.mp4 -a 1:1

# Landscape for YouTube
sclip -i video.mp4 -a 16:9
```

### Caption Styles

```bash
# Default style (white text, black outline)
sclip -i video.mp4 -s default

# Bold style (large yellow text)
sclip -i video.mp4 -s bold

# Minimal style (subtle, small text)
sclip -i video.mp4 -s minimal

# Karaoke style (word-by-word highlight)
sclip -i video.mp4 -s karaoke

# Skip captions entirely
sclip -i video.mp4 --no-captions
```

### Preview & Debug

```bash
# Dry run - analyze video and show clips without rendering
sclip -i video.mp4 --dry-run

# Show video information only
sclip -i video.mp4 --info

# Verbose mode for debugging
sclip -i video.mp4 -v

# Keep temporary files for inspection
sclip -i video.mp4 --keep-temp
```

### Provider Options

```bash
# Default: OpenAI for both transcription and analysis
sclip -i video.mp4

# Use external subtitle file (skip transcription - faster & free)
sclip -i video.mp4 --subtitle subtitle.srt
sclip -i video.mp4 --subtitle captions.vtt --analyzer gemini

# Use different transcription provider
sclip -i video.mp4 --transcriber groq         # Groq Whisper (free)
sclip -i video.mp4 --transcriber deepgram     # Deepgram Nova ($200 free credit)
sclip -i video.mp4 --transcriber elevenlabs   # ElevenLabs Scribe (99 languages)
sclip -i video.mp4 --transcriber local        # Local faster-whisper (offline)

# Use different analysis provider
sclip -i video.mp4 --analyzer groq            # Groq LLMs (free)
sclip -i video.mp4 --analyzer deepseek        # DeepSeek (very affordable)
sclip -i video.mp4 --analyzer gemini          # Google Gemini
sclip -i video.mp4 --analyzer mistral         # Mistral AI (free tier)
sclip -i video.mp4 --analyzer ollama          # Local Ollama (offline)

# Fully offline mode
sclip -i video.mp4 --transcriber local --analyzer ollama

# Specify models
sclip -i video.mp4 --transcriber-model whisper-large-v3
sclip -i video.mp4 --analyzer-model gpt-4o

# Custom Ollama host
sclip -i video.mp4 --analyzer ollama --ollama-host http://192.168.1.100:11434

# Custom OpenAI-compatible endpoint (Together AI, OpenRouter, LM Studio, etc.)
sclip -i video.mp4 --analyzer openai --openai-base-url https://api.together.xyz/v1 --analyzer-model meta-llama/Llama-3-70b-chat-hf
sclip -i video.mp4 --analyzer openai --openai-base-url http://localhost:1234/v1 --analyzer-model local-model
```

### Advanced Options

```bash
# Force overwrite existing files
sclip -i video.mp4 -f

# Skip metadata generation (title/description files)
sclip -i video.mp4 --no-metadata

# Specify custom FFmpeg path
sclip -i video.mp4 --ffmpeg-path /opt/ffmpeg/bin/ffmpeg

# Quiet mode (errors only)
sclip -i video.mp4 -q
```

### Real-World Workflows

```bash
# Podcast episode → TikTok clips (default OpenAI)
sclip -i "podcast_ep42.mp4" -n 5 -a 9:16 -s bold --min-duration 60 --max-duration 120

# Use existing subtitle file (skip transcription - faster!)
sclip -i "podcast_ep42.mp4" --subtitle "podcast_ep42.srt" -n 5 -a 9:16 -s bold

# Interview → Instagram Reels with Gemini analysis
sclip -u "https://youtube.com/watch?v=xxxxx" -n 3 -a 9:16 -s karaoke --analyzer gemini

# Webinar → LinkedIn clips (square format, minimal captions)
sclip -i "webinar_recording.mp4" -n 4 -a 1:1 -s minimal --min-duration 60 --max-duration 90

# Free alternative with Groq
sclip -i "video.mp4" --transcriber groq --analyzer groq

# Offline processing (no internet required)
sclip -i "confidential_meeting.mp4" --transcriber local --analyzer ollama

# Quick preview before full processing
sclip -i "long_video.mp4" --dry-run -v
```

## CLI Reference

### Command Syntax

```
sclip [OPTIONS]
```

### Input Options (one required)

| Flag | Alias | Description |
|------|-------|-------------|
| `--url` | `-u` | YouTube URL to download and process |
| `--input` | `-i` | Path to local video file |

### Subtitle Options

| Flag | Description |
|------|-------------|
| `--subtitle` | External subtitle file (.srt or .vtt) to skip transcription |

Using `--subtitle` skips the transcription step entirely, making processing faster and free (no transcription API cost). This is useful when you already have accurate subtitles.

### Output Options

| Flag | Alias | Default | Description |
|------|-------|---------|-------------|
| `--output` | `-o` | `./output` | Output directory for clips |
| `--force` | `-f` | `false` | Overwrite existing output files |
| `--no-metadata` | | `false` | Skip metadata file generation |

### Clip Settings

| Flag | Alias | Default | Description |
|------|-------|---------|-------------|
| `--max-clips` | `-n` | `5` | Maximum number of clips to generate |
| `--min-duration` | | `60` | Minimum clip duration (seconds) |
| `--max-duration` | | `180` | Maximum clip duration (seconds) |
| `--aspect-ratio` | `-a` | `9:16` | Output ratio: `9:16`, `1:1`, `16:9` |

### Caption Options

| Flag | Alias | Default | Description |
|------|-------|---------|-------------|
| `--caption-style` | `-s` | `default` | Style: `default`, `bold`, `minimal`, `karaoke` |
| `--no-captions` | | `false` | Skip caption burn-in |
| `--language` | `-l` | `id` | Language code for captions |

### API & Model

| Flag | Alias | Default | Description |
|------|-------|---------|-------------|
| `--transcriber` | | `openai` | Transcription provider: `openai`, `groq`, `deepgram`, `elevenlabs`, `local` |
| `--analyzer` | | `openai` | Analysis provider: `openai`, `groq`, `deepseek`, `gemini`, `mistral`, `ollama` |
| `--groq-api-key` | | env var | Groq API key |
| `--openai-api-key` | | env var | OpenAI API key |
| `--gemini-api-key` | | env var | Gemini API key |
| `--deepgram-api-key` | | env var | Deepgram API key ($200 free credit) |
| `--deepseek-api-key` | | env var | DeepSeek API key (very affordable) |
| `--elevenlabs-api-key` | | env var | ElevenLabs API key (99 languages) |
| `--mistral-api-key` | | env var | Mistral API key (free tier) |
| `--transcriber-model` | | auto | Model for transcription |
| `--analyzer-model` | | auto | Model for analysis |
| `--ollama-host` | | `localhost:11434` | Ollama server URL |
| `--openai-base-url` | | config/env | Custom OpenAI-compatible API URL |

### Utility Options

| Flag | Alias | Description |
|------|-------|-------------|
| `--info` | | Display video information only |
| `--dry-run` | | Preview clips without rendering |
| `--check-deps` | | Check dependency installation |
| `--setup` | | Run interactive setup wizard |
| `--verbose` | `-v` | Show detailed progress |
| `--quiet` | `-q` | Silent mode, only show errors |
| `--keep-temp` | | Keep temporary files |
| `--ffmpeg-path` | | Custom FFmpeg binary path |
| `--version` | | Show version and exit |
| `--help` | `-h` | Show help message |

### Provider Models

**Transcription (Whisper):**
| Provider | Models | Default |
|----------|--------|---------|
| groq | `whisper-large-v3`, `whisper-large-v3-turbo` | `whisper-large-v3-turbo` |
| deepgram | `nova-3`, `nova-2`, `whisper-large` | `nova-3` |
| elevenlabs | `scribe_v1` | `scribe_v1` |
| openai | `whisper-1` | `whisper-1` |
| local | `tiny`, `base`, `small`, `medium`, `large-v3` | `base` |

**Analysis (LLM):**
| Provider | Models | Default |
|----------|--------|---------|
| openai | `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo` | `gpt-4o-mini` |
| groq | `openai/gpt-oss-120b`, `llama-3.3-70b-versatile` | `openai/gpt-oss-120b` |
| deepseek | `deepseek-chat`, `deepseek-reasoner` | `deepseek-chat` |
| gemini | `gemini-2.0-flash`, `gemini-1.5-pro` | `gemini-2.0-flash` |
| mistral | `mistral-small-latest`, `mistral-large-latest`, `open-mistral-nemo` | `mistral-small-latest` |
| ollama | Any installed model | `llama3.2` |

### Flag Conflicts

| Combination | Behavior |
|-------------|----------|
| `--url` + `--input` | Error: Cannot use both |
| `--verbose` + `--quiet` | Error: Cannot use both |
| `--dry-run` + `--force` | Allowed: `--force` ignored |
| `--no-captions` + `--caption-style` | Warning: style ignored |

## Caption Styles

| Style | Preview | Best For |
|-------|---------|----------|
| `default` | White text, black outline, bottom-center | General use |
| `bold` | Large yellow text, heavy shadow, center | High impact, attention-grabbing |
| `minimal` | Small white text, subtle shadow | Professional, clean look |
| `karaoke` | Word-by-word green highlight | Music, dynamic content |

## Configuration

### Config File

Location: `~/.sclip/config.json`

```json
{
  "openai_api_key": "your-openai-api-key",
  "openai_base_url": null,
  "groq_api_key": null,
  "gemini_api_key": null,
  "deepgram_api_key": null,
  "deepseek_api_key": null,
  "elevenlabs_api_key": null,
  "mistral_api_key": null,
  "default_transcriber": "openai",
  "default_analyzer": "openai",
  "default_transcriber_model": null,
  "default_analyzer_model": null,
  "ollama_host": "http://localhost:11434",
  "ffmpeg_path": null,
  "default_output_dir": "./output",
  "default_aspect_ratio": "9:16",
  "default_caption_style": "default",
  "default_language": "id",
  "max_clips": 5,
  "min_duration": 60,
  "max_duration": 180
}
```

### Config Options

| Key | Description | Default |
|-----|-------------|---------|
| `openai_api_key` | OpenAI API key | - |
| `openai_base_url` | Custom OpenAI-compatible API URL | - |
| `groq_api_key` | Groq API key (free alternative) | - |
| `default_transcriber` | Default transcription provider | `openai` |
| `default_analyzer` | Default analysis provider | `openai` |
| `default_transcriber_model` | Default model for transcription | auto |
| `default_analyzer_model` | Default model for analysis | auto |
| `default_language` | Language code for captions | `id` |
| `min_duration` | Minimum clip duration (seconds) | `60` |
| `max_duration` | Maximum clip duration (seconds) | `180` |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key (default provider) |
| `GROQ_API_KEY` | Groq API key (free alternative) |
| `GEMINI_API_KEY` | Google Gemini API key |
| `DEEPGRAM_API_KEY` | Deepgram API key ($200 free credit) |
| `DEEPSEEK_API_KEY` | DeepSeek API key (very affordable) |
| `ELEVENLABS_API_KEY` | ElevenLabs API key (99 languages) |
| `MISTRAL_API_KEY` | Mistral API key (free tier) |
| `OLLAMA_HOST` | Ollama server URL (default: http://localhost:11434) |
| `OPENAI_BASE_URL` | Custom OpenAI-compatible API URL |
| `SCLIP_CONFIG` | Custom config file path |
| `SCLIP_OUTPUT_DIR` | Default output directory |

### Priority Order

API key resolution: CLI flag → Environment variable → Config file

## Output Structure

For each identified clip, sclip generates:

```
output/
├── clip_01_catchy_title.mp4           # Rendered video with captions
├── clip_01_catchy_title_title.txt     # AI-generated title
├── clip_01_catchy_title_description.txt  # SEO description
├── clip_02_another_moment.mp4
├── clip_02_another_moment_title.txt
├── clip_02_another_moment_description.txt
└── ...
```

### Supported Formats

**Input:** `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.m4v`, `.mpeg`, `.mpg`, `.flv`

**Output:** `.mp4` (H.264 video + AAC audio)

## Troubleshooting

### FFmpeg not found

```bash
# Check what's missing
sclip --check-deps

# Run setup wizard for guidance
sclip --setup
```

### API key issues

```bash
# Verify API keys are set
echo $GROQ_API_KEY
echo $GEMINI_API_KEY

# Test with explicit key
sclip -i video.mp4 --groq-api-key "your-key-here"

# Re-run setup
sclip --setup
```

### Rate limit exceeded

- OpenAI: Check your usage at platform.openai.com
- Groq free tier: 30 requests/minute, 14,400 requests/day
- Gemini free tier: 15 requests/minute
- Wait a few minutes and retry
- Use `--dry-run` to preview before full processing

### Offline mode not working

```bash
# Check if faster-whisper is installed
pip install faster-whisper

# Check if Ollama is running
ollama serve

# List available Ollama models
ollama list

# Pull a model if needed
ollama pull llama3.2
```

### Video too long

- New architecture handles any video length (no chunking needed)
- Audio extraction is fast regardless of video size
- For very long videos (2+ hours), transcription may take a few minutes

### No clips found

- Video may not have suitable "viral moments"
- Try adjusting `--min-duration` and `--max-duration`
- Ensure video has clear audio/speech content

### Common Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Dependency error (FFmpeg, yt-dlp missing) |
| 2 | Input error (invalid file/URL) |
| 3 | Output error (directory issues) |
| 4 | API error (key, rate limit) |
| 5 | Processing error (FFmpeg, rendering) |
| 6 | Validation error (invalid options) |
| 130 | User interrupt (Ctrl+C) |

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/sakirsyarian/sclip.git
cd sclip

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install in development mode
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_validation.py
```

### Code Quality

```bash
# Format code
black src/

# Lint code
ruff check src/

# Type checking
mypy src/
```

### Project Structure

```
sclip/
├── src/
│   ├── main.py              # CLI entry point
│   ├── commands/            # Command handlers
│   │   ├── clip.py          # Main clipping workflow
│   │   └── setup.py         # Setup wizard
│   ├── services/            # Core services
│   │   ├── audio.py         # Audio extraction
│   │   ├── downloader.py    # YouTube download
│   │   ├── renderer.py      # Video rendering
│   │   ├── transcribers/    # Transcription providers
│   │   │   ├── base.py      # Base transcriber class
│   │   │   ├── groq.py      # Groq Whisper
│   │   │   ├── openai.py    # OpenAI Whisper
│   │   │   └── local.py     # Local faster-whisper
│   │   └── analyzers/       # Analysis providers
│   │       ├── base.py      # Base analyzer class
│   │       ├── groq.py      # Groq LLMs
│   │       ├── gemini.py    # Google Gemini
│   │       ├── openai.py    # OpenAI GPT
│   │       └── ollama.py    # Local Ollama
│   ├── utils/               # Utilities
│   │   ├── captions.py      # Caption generation
│   │   ├── cleanup.py       # Temp file management
│   │   ├── config.py        # Configuration
│   │   ├── ffmpeg.py        # FFmpeg wrapper
│   │   ├── logger.py        # Console output
│   │   ├── validation.py    # Input validation
│   │   └── video.py         # Video analysis
│   └── types/               # Type definitions
├── tests/                   # Test suite
├── pyproject.toml           # Project config
└── requirements.txt         # Dependencies
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Acknowledgments

- [Groq](https://groq.com/) for fast, free Whisper and LLM APIs
- [Google Gemini](https://ai.google.dev/) for AI-powered analysis
- [OpenAI](https://openai.com/) for Whisper and GPT models
- [Ollama](https://ollama.ai/) for local LLM inference
- [FFmpeg](https://ffmpeg.org/) for video processing
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube downloads
- [Click](https://click.palletsprojects.com/) for CLI framework
- [Rich](https://rich.readthedocs.io/) for beautiful terminal output
