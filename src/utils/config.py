"""Config file management for SmartClip AI.

Handles loading, saving, and managing configuration from ~/.sclip/config.json.
Supports cross-platform paths and environment variable overrides.

Configuration Priority (highest to lowest):
    1. CLI arguments (--api-key, --ffmpeg-path)
    2. Environment variables (GEMINI_API_KEY, FFMPEG_PATH)
    3. Config file (~/.sclip/config.json)
    4. Default values

Security:
    - Config file permissions are set to 600 (owner read/write only) on Unix
    - API keys are never logged or exposed in output
    - Config directory permissions are set to 700 (owner only) on Unix

Usage:
    from src.utils.config import load_config, save_config, get_api_key
    
    # Load configuration
    config = load_config()
    
    # Get API key with priority resolution
    api_key = get_api_key(cli_key=args.api_key)
    
    # Save updated configuration
    config.gemini_api_key = "new_key"
    save_config(config)
"""

import json
import os
import stat
from pathlib import Path
from typing import Any

from src.types import Config, AspectRatio, CaptionStyle


# Config file name and directory constants
CONFIG_FILENAME = "config.json"
CONFIG_DIR_NAME = ".sclip"  # Hidden directory in user's home

# Environment variable names for configuration overrides
ENV_API_KEY = "GEMINI_API_KEY"      # Gemini API key
ENV_FFMPEG_PATH = "FFMPEG_PATH"     # Custom FFmpeg path


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
        "gemini_api_key": config.gemini_api_key,
        "default_model": config.default_model,
        "ffmpeg_path": config.ffmpeg_path,
        "default_output_dir": config.default_output_dir,
        "default_aspect_ratio": config.default_aspect_ratio,
        "default_caption_style": config.default_caption_style,
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
        gemini_api_key=data.get("gemini_api_key", defaults.gemini_api_key),
        default_model=data.get("default_model", defaults.default_model),
        ffmpeg_path=data.get("ffmpeg_path", defaults.ffmpeg_path),
        default_output_dir=data.get("default_output_dir", defaults.default_output_dir),
        default_aspect_ratio=_validate_aspect_ratio(
            data.get("default_aspect_ratio", defaults.default_aspect_ratio)
        ),
        default_caption_style=_validate_caption_style(
            data.get("default_caption_style", defaults.default_caption_style)
        ),
        max_clips=data.get("max_clips", defaults.max_clips),
        min_duration=data.get("min_duration", defaults.min_duration),
        max_duration=data.get("max_duration", defaults.max_duration),
    )


def _validate_aspect_ratio(value: str) -> AspectRatio:
    """Validate and return aspect ratio value.
    
    Args:
        value: Aspect ratio string to validate
        
    Returns:
        Valid AspectRatio value, defaults to "9:16" if invalid
    """
    valid_ratios: list[AspectRatio] = ["9:16", "1:1", "16:9"]
    if value in valid_ratios:
        return value  # type: ignore
    return "9:16"


def _validate_caption_style(value: str) -> CaptionStyle:
    """Validate and return caption style value.
    
    Args:
        value: Caption style string to validate
        
    Returns:
        Valid CaptionStyle value, defaults to "default" if invalid
    """
    valid_styles: list[CaptionStyle] = ["default", "bold", "minimal", "karaoke"]
    if value in valid_styles:
        return value  # type: ignore
    return "default"


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
    # This protects the API key from being read by other users
    # Windows handles file permissions differently (ACLs)
    if os.name != "nt":  # Not Windows
        config_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 600 = rw-------


def get_api_key(cli_key: str | None = None) -> str | None:
    """Get API key with priority: CLI > environment > config.
    
    Args:
        cli_key: API key provided via CLI argument (highest priority)
        
    Returns:
        API key string or None if not found anywhere
    """
    # Priority 1: CLI argument
    if cli_key:
        return cli_key
    
    # Priority 2: Environment variable
    env_key = os.environ.get(ENV_API_KEY)
    if env_key:
        return env_key
    
    # Priority 3: Config file
    config = load_config()
    return config.gemini_api_key


def get_ffmpeg_path(cli_path: str | None = None) -> str | None:
    """Get FFmpeg path with priority: CLI > environment > config.
    
    Args:
        cli_path: FFmpeg path provided via CLI argument (highest priority)
        
    Returns:
        FFmpeg path string or None if not specified
    """
    # Priority 1: CLI argument
    if cli_path:
        return cli_path
    
    # Priority 2: Environment variable
    env_path = os.environ.get(ENV_FFMPEG_PATH)
    if env_path:
        return env_path
    
    # Priority 3: Config file
    config = load_config()
    return config.ffmpeg_path


__all__ = [
    "get_config_dir",
    "get_config_path",
    "load_config",
    "save_config",
    "get_api_key",
    "get_ffmpeg_path",
    "CONFIG_FILENAME",
    "CONFIG_DIR_NAME",
    "ENV_API_KEY",
    "ENV_FFMPEG_PATH",
]
