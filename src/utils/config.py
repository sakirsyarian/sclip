"""Config file management for SmartClip AI.

Handles loading, saving, and managing configuration from ~/.sclip/config.json.
Supports cross-platform paths and environment variable overrides.

Configuration Priority (highest to lowest):
    1. CLI arguments (--groq-api-key, --openai-api-key, etc.)
    2. Environment variables (GROQ_API_KEY, OPENAI_API_KEY, etc.)
    3. Config file (~/.sclip/config.json)
    4. Default values

Security:
    - Config file permissions are set to 600 (owner read/write only) on Unix
    - API keys are never logged or exposed in output
    - Config directory permissions are set to 700 (owner only) on Unix

Usage:
    from src.utils.config import load_config, save_config, get_groq_api_key
    
    # Load configuration
    config = load_config()
    
    # Get API key with priority resolution
    api_key = get_groq_api_key(cli_key=args.groq_api_key)
    
    # Save updated configuration
    config.groq_api_key = "new_key"
    save_config(config)
"""

import json
import os
import stat
from pathlib import Path
from typing import Any

from src.types import Config, AspectRatio, CaptionStyle, TranscriberProvider, AnalyzerProvider


# Config file name and directory constants
CONFIG_FILENAME = "config.json"
CONFIG_DIR_NAME = ".sclip"  # Hidden directory in user's home

# Environment variable names for configuration overrides
ENV_GROQ_API_KEY = "GROQ_API_KEY"
ENV_OPENAI_API_KEY = "OPENAI_API_KEY"
ENV_GEMINI_API_KEY = "GEMINI_API_KEY"
ENV_DEEPGRAM_API_KEY = "DEEPGRAM_API_KEY"
ENV_DEEPSEEK_API_KEY = "DEEPSEEK_API_KEY"
ENV_ELEVENLABS_API_KEY = "ELEVENLABS_API_KEY"
ENV_MISTRAL_API_KEY = "MISTRAL_API_KEY"
ENV_OLLAMA_HOST = "OLLAMA_HOST"
ENV_FFMPEG_PATH = "FFMPEG_PATH"

# Legacy environment variable (deprecated)
ENV_API_KEY = "GEMINI_API_KEY"  # Kept for backward compatibility


def get_config_dir() -> Path:
    """Get the config directory path (~/.sclip/).
    
    Creates the directory if it doesn't exist.
    
    Returns:
        Path to the config directory
    """
    home = Path.home()
    config_dir = home / CONFIG_DIR_NAME
    
    if not config_dir.exists():
        config_dir.mkdir(parents=True, exist_ok=True)
        # Set directory permissions to 700 (owner only) on Unix systems
        if os.name != "nt":  # Not Windows
            config_dir.chmod(stat.S_IRWXU)
    
    return config_dir


def get_config_path() -> Path:
    """Get the config file path (~/.sclip/config.json).
    
    Returns:
        Path to the config file
    """
    return get_config_dir() / CONFIG_FILENAME


def _config_to_dict(config: Config) -> dict[str, Any]:
    """Convert Config dataclass to dictionary for JSON serialization.
    
    Args:
        config: Config object to convert
        
    Returns:
        Dictionary representation of the config
    """
    return {
        # API Keys
        "groq_api_key": config.groq_api_key,
        "openai_api_key": config.openai_api_key,
        "gemini_api_key": config.gemini_api_key,
        "deepgram_api_key": config.deepgram_api_key,
        "deepseek_api_key": config.deepseek_api_key,
        "elevenlabs_api_key": config.elevenlabs_api_key,
        "mistral_api_key": config.mistral_api_key,
        # Provider defaults
        "default_transcriber": config.default_transcriber,
        "default_analyzer": config.default_analyzer,
        "default_transcriber_model": config.default_transcriber_model,
        "default_analyzer_model": config.default_analyzer_model,
        "ollama_host": config.ollama_host,
        # FFmpeg
        "ffmpeg_path": config.ffmpeg_path,
        # Output defaults
        "default_output_dir": config.default_output_dir,
        "default_aspect_ratio": config.default_aspect_ratio,
        "default_caption_style": config.default_caption_style,
        "default_language": config.default_language,
        # Clip settings
        "max_clips": config.max_clips,
        "min_duration": config.min_duration,
        "max_duration": config.max_duration,
    }


def _dict_to_config(data: dict[str, Any]) -> Config:
    """Convert dictionary to Config dataclass.
    
    Handles missing keys by using defaults from Config dataclass.
    
    Args:
        data: Dictionary with config values
        
    Returns:
        Config object with values from dict merged with defaults
    """
    defaults = Config()
    
    return Config(
        # API Keys
        groq_api_key=data.get("groq_api_key", defaults.groq_api_key),
        openai_api_key=data.get("openai_api_key", defaults.openai_api_key),
        gemini_api_key=data.get("gemini_api_key", defaults.gemini_api_key),
        deepgram_api_key=data.get("deepgram_api_key", defaults.deepgram_api_key),
        deepseek_api_key=data.get("deepseek_api_key", defaults.deepseek_api_key),
        elevenlabs_api_key=data.get("elevenlabs_api_key", defaults.elevenlabs_api_key),
        mistral_api_key=data.get("mistral_api_key", defaults.mistral_api_key),
        # Provider defaults
        default_transcriber=_validate_transcriber(
            data.get("default_transcriber", defaults.default_transcriber)
        ),
        default_analyzer=_validate_analyzer(
            data.get("default_analyzer", defaults.default_analyzer)
        ),
        default_transcriber_model=data.get("default_transcriber_model", defaults.default_transcriber_model),
        default_analyzer_model=data.get("default_analyzer_model", defaults.default_analyzer_model),
        ollama_host=data.get("ollama_host", defaults.ollama_host),
        # FFmpeg
        ffmpeg_path=data.get("ffmpeg_path", defaults.ffmpeg_path),
        # Output defaults
        default_output_dir=data.get("default_output_dir", defaults.default_output_dir),
        default_aspect_ratio=_validate_aspect_ratio(
            data.get("default_aspect_ratio", defaults.default_aspect_ratio)
        ),
        default_caption_style=_validate_caption_style(
            data.get("default_caption_style", defaults.default_caption_style)
        ),
        default_language=data.get("default_language", defaults.default_language),
        # Clip settings
        max_clips=data.get("max_clips", defaults.max_clips),
        min_duration=data.get("min_duration", defaults.min_duration),
        max_duration=data.get("max_duration", defaults.max_duration),
    )


def _validate_aspect_ratio(value: str) -> AspectRatio:
    """Validate and return aspect ratio value."""
    valid_ratios: list[AspectRatio] = ["9:16", "1:1", "16:9"]
    if value in valid_ratios:
        return value  # type: ignore
    return "9:16"


def _validate_caption_style(value: str) -> CaptionStyle:
    """Validate and return caption style value."""
    valid_styles: list[CaptionStyle] = ["default", "bold", "minimal", "karaoke"]
    if value in valid_styles:
        return value  # type: ignore
    return "default"


def _validate_transcriber(value: str) -> TranscriberProvider:
    """Validate and return transcriber provider value."""
    valid_providers: list[TranscriberProvider] = ["groq", "openai", "deepgram", "elevenlabs", "local"]
    if value in valid_providers:
        return value  # type: ignore
    return "groq"


def _validate_analyzer(value: str) -> AnalyzerProvider:
    """Validate and return analyzer provider value."""
    valid_providers: list[AnalyzerProvider] = ["groq", "deepseek", "gemini", "openai", "mistral", "ollama"]
    if value in valid_providers:
        return value  # type: ignore
    return "groq"


def load_config() -> Config:
    """Load config from file, merge with defaults.
    
    If config file doesn't exist, returns default Config.
    If config file is invalid JSON, returns default Config.
    
    Returns:
        Config object with loaded values or defaults
    """
    config_path = get_config_path()
    
    if not config_path.exists():
        return Config()
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _dict_to_config(data)
    except (json.JSONDecodeError, IOError, OSError):
        # Return defaults if file is corrupted or unreadable
        return Config()


def save_config(config: Config) -> None:
    """Save config to file.
    
    Creates the config directory if it doesn't exist.
    Sets file permissions to 600 (owner read/write only) on Unix systems
    to protect the API key from being read by other users.
    
    Args:
        config: Config object to save
        
    Raises:
        IOError: If unable to write config file
        OSError: If unable to set file permissions
    """
    config_path = get_config_path()
    
    # Ensure directory exists with proper permissions
    get_config_dir()
    
    # Convert config to JSON-serializable dict
    data = _config_to_dict(config)
    
    # Write config file with pretty formatting
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    # Set restrictive file permissions on Unix systems
    if os.name != "nt":  # Not Windows
        config_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 600 = rw-------


# API Key getters with priority: CLI > environment > config

def get_groq_api_key(cli_key: str | None = None) -> str | None:
    """Get Groq API key with priority: CLI > environment > config."""
    if cli_key:
        return cli_key
    env_key = os.environ.get(ENV_GROQ_API_KEY)
    if env_key:
        return env_key
    config = load_config()
    return config.groq_api_key


def get_openai_api_key(cli_key: str | None = None) -> str | None:
    """Get OpenAI API key with priority: CLI > environment > config."""
    if cli_key:
        return cli_key
    env_key = os.environ.get(ENV_OPENAI_API_KEY)
    if env_key:
        return env_key
    config = load_config()
    return config.openai_api_key


def get_gemini_api_key(cli_key: str | None = None) -> str | None:
    """Get Gemini API key with priority: CLI > environment > config."""
    if cli_key:
        return cli_key
    env_key = os.environ.get(ENV_GEMINI_API_KEY)
    if env_key:
        return env_key
    config = load_config()
    return config.gemini_api_key


def get_deepgram_api_key(cli_key: str | None = None) -> str | None:
    """Get Deepgram API key with priority: CLI > environment > config."""
    if cli_key:
        return cli_key
    env_key = os.environ.get(ENV_DEEPGRAM_API_KEY)
    if env_key:
        return env_key
    config = load_config()
    return config.deepgram_api_key


def get_deepseek_api_key(cli_key: str | None = None) -> str | None:
    """Get DeepSeek API key with priority: CLI > environment > config."""
    if cli_key:
        return cli_key
    env_key = os.environ.get(ENV_DEEPSEEK_API_KEY)
    if env_key:
        return env_key
    config = load_config()
    return config.deepseek_api_key


def get_elevenlabs_api_key(cli_key: str | None = None) -> str | None:
    """Get ElevenLabs API key with priority: CLI > environment > config."""
    if cli_key:
        return cli_key
    env_key = os.environ.get(ENV_ELEVENLABS_API_KEY)
    if env_key:
        return env_key
    config = load_config()
    return config.elevenlabs_api_key


def get_mistral_api_key(cli_key: str | None = None) -> str | None:
    """Get Mistral API key with priority: CLI > environment > config."""
    if cli_key:
        return cli_key
    env_key = os.environ.get(ENV_MISTRAL_API_KEY)
    if env_key:
        return env_key
    config = load_config()
    return config.mistral_api_key


def get_ollama_host(cli_host: str | None = None) -> str:
    """Get Ollama host with priority: CLI > environment > config."""
    if cli_host:
        return cli_host
    env_host = os.environ.get(ENV_OLLAMA_HOST)
    if env_host:
        return env_host
    config = load_config()
    return config.ollama_host


def get_ffmpeg_path(cli_path: str | None = None) -> str | None:
    """Get FFmpeg path with priority: CLI > environment > config."""
    if cli_path:
        return cli_path
    env_path = os.environ.get(ENV_FFMPEG_PATH)
    if env_path:
        return env_path
    config = load_config()
    return config.ffmpeg_path


# Legacy function for backward compatibility
def get_api_key(cli_key: str | None = None) -> str | None:
    """Get API key (legacy - returns Gemini API key for backward compatibility)."""
    return get_gemini_api_key(cli_key)


__all__ = [
    "get_config_dir",
    "get_config_path",
    "load_config",
    "save_config",
    "get_groq_api_key",
    "get_openai_api_key",
    "get_gemini_api_key",
    "get_deepgram_api_key",
    "get_deepseek_api_key",
    "get_elevenlabs_api_key",
    "get_mistral_api_key",
    "get_ollama_host",
    "get_ffmpeg_path",
    "get_api_key",  # Legacy
    "CONFIG_FILENAME",
    "CONFIG_DIR_NAME",
    "ENV_GROQ_API_KEY",
    "ENV_OPENAI_API_KEY",
    "ENV_GEMINI_API_KEY",
    "ENV_DEEPGRAM_API_KEY",
    "ENV_DEEPSEEK_API_KEY",
    "ENV_ELEVENLABS_API_KEY",
    "ENV_MISTRAL_API_KEY",
    "ENV_OLLAMA_HOST",
    "ENV_FFMPEG_PATH",
    "ENV_API_KEY",  # Legacy
]
