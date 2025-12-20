"""Dependency setup wizard for SmartClip AI.

This module provides an interactive setup wizard that guides users through
configuring SmartClip AI for first use. It handles:

Setup Steps:
    1. Display current dependency status
    2. Configure Gemini API key (with instructions to get one)
    3. FFmpeg installation guidance (platform-specific)
    4. yt-dlp installation guidance (optional, for YouTube)
    5. Save configuration to ~/.sclip/config.json

Platform Support:
    The wizard provides platform-specific installation instructions for:
    - Windows: Chocolatey, Scoop, manual download
    - macOS: Homebrew, MacPorts, manual download
    - Linux: apt, dnf, pacman, manual download

API Key Setup:
    Users are guided to:
    1. Visit Google AI Studio (https://aistudio.google.com/app/apikey)
    2. Sign in with Google account
    3. Create and copy API key
    4. Enter key in wizard (stored securely in config)

Usage:
    # From CLI
    sclip --setup
    
    # Programmatically
    from src.commands.setup import run_setup_wizard
    exit_code = run_setup_wizard()
"""

import shutil
import sys
from typing import Optional

from rich.prompt import Prompt, Confirm
from rich.table import Table

from src.types import ExitCode, Config
from src.utils.config import (
    load_config,
    save_config,
    get_api_key,
    get_config_path,
    ENV_API_KEY,
)
from src.utils.ffmpeg import check_dependencies, find_ffmpeg, find_ffprobe
from src.utils.logger import get_logger


# Installation URLs for dependencies
# These are the official/recommended sources for each platform
FFMPEG_URLS = {
    "win32": "https://www.gyan.dev/ffmpeg/builds/",      # Gyan.dev builds (recommended for Windows)
    "darwin": "https://formulae.brew.sh/formula/ffmpeg", # Homebrew formula
    "linux": "https://ffmpeg.org/download.html#build-linux",  # Official FFmpeg downloads
}

# yt-dlp installation command and documentation URL
YTDLP_INSTALL_CMD = "pip install yt-dlp"
YTDLP_URL = "https://github.com/yt-dlp/yt-dlp#installation"

# Google AI Studio URL for getting Gemini API key
GEMINI_API_URL = "https://aistudio.google.com/app/apikey"


def _get_platform_name() -> str:
    """Get human-readable platform name."""
    if sys.platform == "win32":
        return "Windows"
    elif sys.platform == "darwin":
        return "macOS"
    else:
        return "Linux"


def _get_ffmpeg_install_instructions() -> list[str]:
    """Get platform-specific FFmpeg installation instructions."""
    platform = sys.platform
    if platform.startswith("linux"):
        platform = "linux"
    
    instructions = []
    
    if platform == "win32":
        instructions = [
            "Option 1: Download from https://www.gyan.dev/ffmpeg/builds/",
            "  - Download 'ffmpeg-release-essentials.zip'",
            "  - Extract to C:\\ffmpeg",
            "  - Add C:\\ffmpeg\\bin to your PATH",
            "",
            "Option 2: Using Chocolatey:",
            "  choco install ffmpeg",
            "",
            "Option 3: Using Scoop:",
            "  scoop install ffmpeg",
        ]
    elif platform == "darwin":
        instructions = [
            "Option 1: Using Homebrew (recommended):",
            "  brew install ffmpeg",
            "",
            "Option 2: Using MacPorts:",
            "  sudo port install ffmpeg",
            "",
            "Option 3: Download from https://evermeet.cx/ffmpeg/",
        ]
    else:  # Linux
        instructions = [
            "Ubuntu/Debian:",
            "  sudo apt update && sudo apt install ffmpeg",
            "",
            "Fedora:",
            "  sudo dnf install ffmpeg",
            "",
            "Arch Linux:",
            "  sudo pacman -S ffmpeg",
            "",
            "Or download from: https://ffmpeg.org/download.html",
        ]
    
    return instructions


def _get_ytdlp_install_instructions() -> list[str]:
    """Get yt-dlp installation instructions."""
    instructions = [
        "Option 1: Using pip (recommended):",
        "  pip install yt-dlp",
        "",
        "Option 2: Using pipx:",
        "  pipx install yt-dlp",
    ]
    
    if sys.platform == "win32":
        instructions.extend([
            "",
            "Option 3: Using Chocolatey:",
            "  choco install yt-dlp",
            "",
            "Option 4: Using Scoop:",
            "  scoop install yt-dlp",
        ])
    elif sys.platform == "darwin":
        instructions.extend([
            "",
            "Option 3: Using Homebrew:",
            "  brew install yt-dlp",
        ])
    else:
        instructions.extend([
            "",
            "Option 3: Using your package manager (may be outdated):",
            "  sudo apt install yt-dlp  # Debian/Ubuntu",
        ])
    
    return instructions


def _check_current_status() -> dict:
    """Check current status of all dependencies.
    
    Returns:
        Dictionary with status of each dependency
    """
    status = {}
    
    # Check FFmpeg/FFprobe
    deps = check_dependencies()
    status["ffmpeg"] = {
        "found": deps.ffmpeg_found,
        "path": deps.ffmpeg_path,
        "version": deps.ffmpeg_version,
    }
    status["ffprobe"] = {
        "found": deps.ffprobe_found,
        "path": deps.ffprobe_path,
        "version": deps.ffprobe_version,
    }
    
    # Check yt-dlp
    ytdlp_path = shutil.which("yt-dlp")
    status["ytdlp"] = {
        "found": ytdlp_path is not None,
        "path": ytdlp_path,
    }
    
    # Check API key
    api_key = get_api_key()
    status["api_key"] = {
        "configured": api_key is not None,
        "masked": _mask_key(api_key) if api_key else None,
    }
    
    # Check Python version
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    status["python"] = {
        "version": py_version,
        "ok": sys.version_info >= (3, 10),
    }
    
    return status


def _mask_key(key: str) -> str:
    """Mask API key for display."""
    if len(key) > 8:
        return key[:4] + "..." + key[-4:]
    return "***"


def _display_status_table(status: dict) -> None:
    """Display current status as a table."""
    logger = get_logger()
    console = logger.console
    
    table = Table(title="Current Status", show_header=True, header_style="bold cyan")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Details", style="dim")
    
    # Python
    py_status = "✓ OK" if status["python"]["ok"] else "✗ Outdated"
    py_style = "green" if status["python"]["ok"] else "red"
    table.add_row(
        "Python",
        f"[{py_style}]{py_status}[/{py_style}]",
        f"v{status['python']['version']} (requires 3.10+)"
    )
    
    # FFmpeg
    if status["ffmpeg"]["found"]:
        ffmpeg_status = "✓ Found"
        ffmpeg_style = "green"
        ffmpeg_details = f"v{status['ffmpeg']['version'] or 'unknown'}"
    else:
        ffmpeg_status = "✗ Not found"
        ffmpeg_style = "red"
        ffmpeg_details = "Required for video processing"
    table.add_row(
        "FFmpeg",
        f"[{ffmpeg_style}]{ffmpeg_status}[/{ffmpeg_style}]",
        ffmpeg_details
    )
    
    # FFprobe
    if status["ffprobe"]["found"]:
        ffprobe_status = "✓ Found"
        ffprobe_style = "green"
        ffprobe_details = f"v{status['ffprobe']['version'] or 'unknown'}"
    else:
        ffprobe_status = "✗ Not found"
        ffprobe_style = "red"
        ffprobe_details = "Required for video analysis"
    table.add_row(
        "FFprobe",
        f"[{ffprobe_style}]{ffprobe_status}[/{ffprobe_style}]",
        ffprobe_details
    )
    
    # yt-dlp
    if status["ytdlp"]["found"]:
        ytdlp_status = "✓ Found"
        ytdlp_style = "green"
        ytdlp_details = "YouTube downloads enabled"
    else:
        ytdlp_status = "○ Not found"
        ytdlp_style = "yellow"
        ytdlp_details = "Optional - for YouTube URLs"
    table.add_row(
        "yt-dlp",
        f"[{ytdlp_style}]{ytdlp_status}[/{ytdlp_style}]",
        ytdlp_details
    )
    
    # API Key
    if status["api_key"]["configured"]:
        api_status = "✓ Configured"
        api_style = "green"
        api_details = status["api_key"]["masked"]
    else:
        api_status = "✗ Not configured"
        api_style = "red"
        api_details = "Required for AI analysis"
    table.add_row(
        "Gemini API Key",
        f"[{api_style}]{api_status}[/{api_style}]",
        api_details
    )
    
    console.print()
    console.print(table)
    console.print()


def _setup_api_key(current_config: Config) -> Optional[str]:
    """Interactive API key setup.
    
    Args:
        current_config: Current configuration
        
    Returns:
        New API key or None if skipped
    """
    logger = get_logger()
    console = logger.console
    
    console.print("\n[bold cyan]━━━ Gemini API Key Setup ━━━[/bold cyan]\n")
    
    # Check if already configured
    existing_key = get_api_key()
    if existing_key:
        console.print(f"[green]✓[/green] API key already configured: {_mask_key(existing_key)}")
        if not Confirm.ask("Do you want to update it?", default=False):
            return None
    
    console.print("To get a Gemini API key:")
    console.print(f"  1. Visit: [link={GEMINI_API_URL}]{GEMINI_API_URL}[/link]")
    console.print("  2. Sign in with your Google account")
    console.print("  3. Click 'Create API key'")
    console.print("  4. Copy the generated key")
    console.print()
    
    # Prompt for API key
    api_key = Prompt.ask(
        "Enter your Gemini API key (or press Enter to skip)",
        default="",
        password=True
    )
    
    if api_key.strip():
        return api_key.strip()
    
    console.print("[yellow]⚠[/yellow] Skipped API key setup")
    console.print(f"  You can set it later via {ENV_API_KEY} environment variable")
    console.print(f"  or by running 'sclip --setup' again")
    return None


def _setup_ffmpeg() -> Optional[str]:
    """Interactive FFmpeg setup guidance.
    
    Returns:
        Custom FFmpeg path if provided, None otherwise
    """
    logger = get_logger()
    console = logger.console
    
    console.print("\n[bold cyan]━━━ FFmpeg Setup ━━━[/bold cyan]\n")
    
    # Check current status
    deps = check_dependencies()
    
    if deps.ffmpeg_found and deps.ffprobe_found:
        console.print(f"[green]✓[/green] FFmpeg found: {deps.ffmpeg_path}")
        console.print(f"[green]✓[/green] FFprobe found: {deps.ffprobe_path}")
        
        if Confirm.ask("FFmpeg is already installed. Do you want to use a different path?", default=False):
            custom_path = Prompt.ask("Enter custom FFmpeg directory path", default="")
            if custom_path.strip():
                # Verify the path
                test_ffmpeg = find_ffmpeg(custom_path.strip())
                test_ffprobe = find_ffprobe(custom_path.strip())
                if test_ffmpeg and test_ffprobe:
                    console.print(f"[green]✓[/green] Found FFmpeg at: {test_ffmpeg}")
                    return custom_path.strip()
                else:
                    console.print("[red]✗[/red] FFmpeg not found at that path")
        return None
    
    # FFmpeg not found - show installation instructions
    console.print("[yellow]⚠[/yellow] FFmpeg not found on your system")
    console.print()
    
    platform_name = _get_platform_name()
    console.print(f"[bold]Installation instructions for {platform_name}:[/bold]")
    console.print()
    
    for line in _get_ffmpeg_install_instructions():
        console.print(f"  {line}")
    
    console.print()
    
    # Ask if they want to provide a custom path
    if Confirm.ask("Do you have FFmpeg installed at a custom location?", default=False):
        custom_path = Prompt.ask("Enter FFmpeg directory path")
        if custom_path.strip():
            test_ffmpeg = find_ffmpeg(custom_path.strip())
            test_ffprobe = find_ffprobe(custom_path.strip())
            if test_ffmpeg and test_ffprobe:
                console.print(f"[green]✓[/green] Found FFmpeg at: {test_ffmpeg}")
                return custom_path.strip()
            else:
                console.print("[red]✗[/red] FFmpeg not found at that path")
    
    console.print()
    console.print("[dim]After installing FFmpeg, run 'sclip --check-deps' to verify[/dim]")
    return None


def _setup_ytdlp() -> None:
    """Interactive yt-dlp setup guidance."""
    logger = get_logger()
    console = logger.console
    
    console.print("\n[bold cyan]━━━ yt-dlp Setup (Optional) ━━━[/bold cyan]\n")
    
    # Check current status
    ytdlp_path = shutil.which("yt-dlp")
    
    if ytdlp_path:
        console.print(f"[green]✓[/green] yt-dlp found: {ytdlp_path}")
        console.print("  YouTube URL downloads are enabled")
        return
    
    console.print("[yellow]○[/yellow] yt-dlp not found (optional)")
    console.print("  yt-dlp is only needed if you want to process YouTube URLs")
    console.print()
    
    if Confirm.ask("Do you want to see installation instructions?", default=True):
        console.print()
        console.print("[bold]Installation instructions:[/bold]")
        console.print()
        
        for line in _get_ytdlp_install_instructions():
            console.print(f"  {line}")
        
        console.print()
        console.print(f"  More info: [link={YTDLP_URL}]{YTDLP_URL}[/link]")


def _save_setup_config(
    current_config: Config,
    api_key: Optional[str],
    ffmpeg_path: Optional[str]
) -> bool:
    """Save configuration from setup wizard.
    
    Args:
        current_config: Current configuration
        api_key: New API key (if provided)
        ffmpeg_path: Custom FFmpeg path (if provided)
        
    Returns:
        True if config was saved, False otherwise
    """
    logger = get_logger()
    console = logger.console
    
    # Check if there's anything to save
    if api_key is None and ffmpeg_path is None:
        return False
    
    # Update config
    new_config = Config(
        gemini_api_key=api_key if api_key else current_config.gemini_api_key,
        default_model=current_config.default_model,
        ffmpeg_path=ffmpeg_path if ffmpeg_path else current_config.ffmpeg_path,
        default_output_dir=current_config.default_output_dir,
        default_aspect_ratio=current_config.default_aspect_ratio,
        default_caption_style=current_config.default_caption_style,
        max_clips=current_config.max_clips,
        min_duration=current_config.min_duration,
        max_duration=current_config.max_duration,
    )
    
    try:
        save_config(new_config)
        config_path = get_config_path()
        console.print(f"\n[green]✓[/green] Configuration saved to: {config_path}")
        return True
    except Exception as e:
        console.print(f"\n[red]✗[/red] Failed to save configuration: {e}")
        return False


def run_setup_wizard() -> int:
    """Run the interactive setup wizard.
    
    Guides users through:
    1. Display current status
    2. API key configuration
    3. FFmpeg installation check/guidance
    4. yt-dlp installation check/guidance
    5. Saving configuration
    
    Returns:
        Exit code indicating success or failure
    """
    logger = get_logger()
    console = logger.console
    
    # Header
    console.print()
    console.print("[bold cyan]╔══════════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║      SmartClip AI - Setup Wizard         ║[/bold cyan]")
    console.print("[bold cyan]╚══════════════════════════════════════════╝[/bold cyan]")
    console.print()
    
    console.print("This wizard will help you configure SmartClip AI.")
    console.print("You can skip any step by pressing Enter.")
    
    # Check and display current status
    status = _check_current_status()
    _display_status_table(status)
    
    # Load current config
    current_config = load_config()
    
    # Track what was configured
    new_api_key = None
    new_ffmpeg_path = None
    
    # Step 1: API Key
    if Confirm.ask("Configure Gemini API key?", default=not status["api_key"]["configured"]):
        new_api_key = _setup_api_key(current_config)
    
    # Step 2: FFmpeg
    if Confirm.ask(
        "Configure FFmpeg?",
        default=not (status["ffmpeg"]["found"] and status["ffprobe"]["found"])
    ):
        new_ffmpeg_path = _setup_ffmpeg()
    
    # Step 3: yt-dlp (informational only)
    if not status["ytdlp"]["found"]:
        _setup_ytdlp()
    
    # Save configuration
    config_saved = _save_setup_config(current_config, new_api_key, new_ffmpeg_path)
    
    # Final summary
    console.print("\n[bold cyan]━━━ Setup Complete ━━━[/bold cyan]\n")
    
    # Re-check status
    final_status = _check_current_status()
    
    # Determine if ready to use
    ready = (
        final_status["python"]["ok"] and
        final_status["ffmpeg"]["found"] and
        final_status["ffprobe"]["found"] and
        final_status["api_key"]["configured"]
    )
    
    if ready:
        console.print("[green]✓[/green] SmartClip AI is ready to use!")
        console.print()
        console.print("Try it out:")
        console.print("  sclip -i your_video.mp4")
        console.print("  sclip -u 'https://youtube.com/watch?v=...'")
    else:
        console.print("[yellow]⚠[/yellow] Some components are still missing:")
        
        if not final_status["ffmpeg"]["found"] or not final_status["ffprobe"]["found"]:
            console.print("  • FFmpeg needs to be installed")
        
        if not final_status["api_key"]["configured"]:
            console.print("  • Gemini API key needs to be configured")
        
        console.print()
        console.print("Run 'sclip --check-deps' to verify your setup")
        console.print("Run 'sclip --setup' again after installing missing components")
    
    console.print()
    
    return ExitCode.SUCCESS


__all__ = ["run_setup_wizard"]
