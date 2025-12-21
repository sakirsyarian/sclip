# SmartClip AI 🎬✨

Transform long-form videos into viral-ready short clips using Google Gemini AI.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

SmartClip AI is a CLI tool that automatically identifies the most engaging moments in your videos (podcasts, interviews, webinars) and transforms them into short-form content ready for TikTok, Instagram Reels, and YouTube Shorts.

**Key Features:**
- 🤖 AI-powered viral moment detection using Google Gemini
- 📝 Automatic word-level caption generation and burn-in
- 🎯 Smart cropping to vertical (9:16), square (1:1), or landscape (16:9)
- 📺 YouTube URL support via yt-dlp
- 📊 SEO-optimized titles and descriptions for each clip

## Table of Contents

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
- Google Gemini API key ([Get one free](https://aistudio.google.com/apikey))
- yt-dlp (optional, for YouTube downloads)

## Installation

### 1. Install sclip

```bash
# Clone the repository
git clone https://github.com/sarian/sclip.git
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
# Option 1: Set environment variable (recommended)
export GEMINI_API_KEY="your-api-key-here"

# Option 2: Run setup wizard
sclip --setup

# Option 3: Pass directly via CLI
sclip -i video.mp4 --api-key "your-api-key-here"
```

Get your free API key from [Google AI Studio](https://aistudio.google.com/apikey).

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
✓ Gemini API key: configured (AIza...xxxx)

All required dependencies are available!
```

## Quick Start

```bash
# Process a local video file
sclip -i podcast.mp4

# Process a YouTube video
sclip -u "https://youtube.com/watch?v=xxxxx"

# Preview clips without rendering (dry run)
sclip -i video.mp4 --dry-run

# Generate 3 clips in square format
sclip -i video.mp4 -n 3 -a 1:1
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

# Set duration range: 45-75 seconds per clip
sclip -i video.mp4 --min-duration 45 --max-duration 75

# Generate longer clips (60-120 seconds)
sclip -i webinar.mp4 --min-duration 60 --max-duration 120
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

### Advanced Options

```bash
# Force overwrite existing files
sclip -i video.mp4 -f

# Skip metadata generation (title/description files)
sclip -i video.mp4 --no-metadata

# Use a specific Gemini model
sclip -i video.mp4 -m gemini-1.5-pro

# Specify custom FFmpeg path
sclip -i video.mp4 --ffmpeg-path /opt/ffmpeg/bin/ffmpeg

# Quiet mode (errors only)
sclip -i video.mp4 -q
```

### Real-World Workflows

```bash
# Podcast episode → TikTok clips
sclip -i "podcast_ep42.mp4" -n 5 -a 9:16 -s bold --min-duration 30 --max-duration 60

# Interview → Instagram Reels
sclip -u "https://youtube.com/watch?v=xxxxx" -n 3 -a 9:16 -s karaoke -o ./reels

# Webinar → LinkedIn clips (square format, minimal captions)
sclip -i "webinar_recording.mp4" -n 4 -a 1:1 -s minimal --min-duration 45 --max-duration 90

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
| `--min-duration` | | `15` | Minimum clip duration (seconds) |
| `--max-duration` | | `60` | Maximum clip duration (seconds) |
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
| `--api-key` | | env var | Gemini API key (overrides env/config) |
| `--model` | `-m` | `gemini-2.0-flash` | Gemini model to use |

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
  "gemini_api_key": "your-api-key",
  "default_model": "gemini-2.0-flash",
  "ffmpeg_path": null,
  "default_output_dir": "./output",
  "default_aspect_ratio": "9:16",
  "default_caption_style": "default",
  "max_clips": 5,
  "min_duration": 15,
  "max_duration": 60
}
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key |
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
# Verify API key is set
echo $GEMINI_API_KEY

# Test with explicit key
sclip -i video.mp4 --api-key "your-key-here"

# Re-run setup
sclip --setup
```

### Rate limit exceeded

- Default model `gemini-2.0-flash` is optimized for free tier
- Wait a few minutes and retry
- Use `--dry-run` to preview before full processing
- Consider upgrading to paid tier for heavy usage

### Video too long

- Videos > 30 minutes are automatically chunked
- For very long videos (2+ hours), consider splitting manually first
- Use `--dry-run` to test analysis before rendering

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
git clone https://github.com/sarian/sclip.git
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
│   │   ├── downloader.py    # YouTube download
│   │   ├── gemini.py        # AI analysis
│   │   └── renderer.py      # Video rendering
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

- [Google Gemini](https://ai.google.dev/) for AI-powered video analysis
- [FFmpeg](https://ffmpeg.org/) for video processing
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube downloads
- [Click](https://click.palletsprojects.com/) for CLI framework
- [Rich](https://rich.readthedocs.io/) for beautiful terminal output
