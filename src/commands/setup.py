"""Setup wizard for SmartClip AI.

Interactive setup wizard that guides users through configuring SmartClip AI.
Handles API keys for all providers (Groq, OpenAI, Gemini), FFmpeg, and yt-dlp.

Default provider is Groq (FREE) for both transcription and analysis.

Usage:
    sclip --setup
"""

import shutil
import sys
from typing import Optional

from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel

from src.types import ExitCode, Config, TranscriberProvider, AnalyzerProvider
from src.utils.config import (
    load_config,
    save_config,
    get_config_path,
    get_groq_api_key,
    get_openai_api_key,
    get_gemini_api_key,
    ENV_GROQ_API_KEY,
    ENV_OPENAI_API_KEY,
    ENV_GEMINI_API_KEY,
)
from src.utils.ffmpeg import check_dependencies, find_ffmpeg, find_ffprobe
from src.utils.logger import get_logger


# API URLs
GROQ_API_URL = "https://console.groq.com/keys"
OPENAI_API_URL = "https://platform.openai.com/api-keys"
GEMINI_API_URL = "https://aistudio.google.com/app/apikey"
OLLAMA_URL = "https://ollama.ai/download"


def _get_platform_name() -> str:
    """Get human-readable platform name."""
    if sys.platform == "win32":
        return "Windows"
    elif sys.platform == "darwin":
        return "macOS"
    return "Linux"


def _mask_key(key: str) -> str:
    """Mask API key for display."""
    if len(key) > 8:
        return key[:4] + "..." + key[-4:]
    return "***"


def _get_ffmpeg_install_instructions() -> list[str]:
    """Get platform-specific FFmpeg installation instructions."""
    platform = sys.platform
    if platform.startswith("linux"):
        platform = "linux"
    
    if platform == "win32":
        return [
            "Option 1: Using Chocolatey:",
            "  choco install ffmpeg",
            "",
            "Option 2: Using Scoop:",
            "  scoop install ffmpeg",
            "",
            "Option 3: Manual download:",
            "  https://www.gyan.dev/ffmpeg/builds/",
        ]
    elif platform == "darwin":
        return [
            "Using Homebrew (recommended):",
            "  brew install ffmpeg",
        ]
    else:
        return [
            "Ubuntu/Debian: sudo apt install ffmpeg",
            "Fedora: sudo dnf install ffmpeg",
            "Arch: sudo pacman -S ffmpeg",
        ]


def _get_ytdlp_install_instructions() -> list[str]:
    """Get yt-dlp installation instructions."""
    return [
        "Using pip (recommended):",
        "  pip install yt-dlp",
    ]


def _check_current_status() -> dict:
    """Check current status of all dependencies and API keys."""
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
    }
    
    # Check yt-dlp
    ytdlp_path = shutil.which("yt-dlp")
    status["ytdlp"] = {"found": ytdlp_path is not None, "path": ytdlp_path}
    
    # Check API keys
    groq_key = get_groq_api_key()
    openai_key = get_openai_api_key()
    gemini_key = get_gemini_api_key()
    
    status["groq_api_key"] = {
        "configured": groq_key is not None,
        "masked": _mask_key(groq_key) if groq_key else None,
    }
    status["openai_api_key"] = {
        "configured": openai_key is not None,
        "masked": _mask_key(openai_key) if openai_key else None,
    }
    status["gemini_api_key"] = {
        "configured": gemini_key is not None,
        "masked": _mask_key(gemini_key) if gemini_key else None,
    }
    
    # Check Ollama
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=2)
        status["ollama"] = {"running": response.status_code == 200}
    except Exception:
        status["ollama"] = {"running": False}
    
    # Check faster-whisper
    try:
        import faster_whisper
        status["faster_whisper"] = {"installed": True}
    except ImportError:
        status["faster_whisper"] = {"installed": False}
    
    # Python version
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    status["python"] = {"version": py_version, "ok": sys.version_info >= (3, 10)}
    
    return status


def _display_status_table(status: dict) -> None:
    """Display current status as a table."""
    logger = get_logger()
    console = logger.console
    
    table = Table(title="Current Status", show_header=True, header_style="bold cyan")
    table.add_column("Component", style="cyan")
    table.add_column("Status")
    table.add_column("Details", style="dim")
    
    # Python
    py_ok = status["python"]["ok"]
    table.add_row(
        "Python",
        f"[green]✓ OK[/green]" if py_ok else "[red]✗ Outdated[/red]",
        f"v{status['python']['version']} (requires 3.10+)"
    )
    
    # FFmpeg
    if status["ffmpeg"]["found"]:
        table.add_row("FFmpeg", "[green]✓ Found[/green]", f"v{status['ffmpeg']['version'] or 'unknown'}")
    else:
        table.add_row("FFmpeg", "[red]✗ Not found[/red]", "Required for video processing")
    
    # yt-dlp
    if status["ytdlp"]["found"]:
        table.add_row("yt-dlp", "[green]✓ Found[/green]", "YouTube downloads enabled")
    else:
        table.add_row("yt-dlp", "[yellow]○ Not found[/yellow]", "Optional - for YouTube URLs")
    
    console.print()
    console.print(table)
    
    # API Keys table
    api_table = Table(title="API Keys", show_header=True, header_style="bold cyan")
    api_table.add_column("Provider", style="cyan")
    api_table.add_column("Status")
    api_table.add_column("Details", style="dim")
    
    # Groq (default - FREE)
    if status["groq_api_key"]["configured"]:
        api_table.add_row("Groq [bold](DEFAULT)[/bold]", "[green]✓ Configured[/green]", status["groq_api_key"]["masked"])
    else:
        api_table.add_row("Groq [bold](DEFAULT)[/bold]", "[red]✗ Not configured[/red]", "FREE - Recommended!")
    
    # OpenAI
    if status["openai_api_key"]["configured"]:
        api_table.add_row("OpenAI", "[green]✓ Configured[/green]", status["openai_api_key"]["masked"])
    else:
        api_table.add_row("OpenAI", "[dim]○ Not configured[/dim]", "Optional - Paid")
    
    # Gemini
    if status["gemini_api_key"]["configured"]:
        api_table.add_row("Gemini", "[green]✓ Configured[/green]", status["gemini_api_key"]["masked"])
    else:
        api_table.add_row("Gemini", "[dim]○ Not configured[/dim]", "Optional - Free tier")
    
    # Ollama
    if status["ollama"]["running"]:
        api_table.add_row("Ollama", "[green]✓ Running[/green]", "localhost:11434")
    else:
        api_table.add_row("Ollama", "[dim]○ Not running[/dim]", "Optional - Local LLM")
    
    # Local Whisper
    if status["faster_whisper"]["installed"]:
        api_table.add_row("Local Whisper", "[green]✓ Installed[/green]", "faster-whisper")
    else:
        api_table.add_row("Local Whisper", "[dim]○ Not installed[/dim]", "Optional - Offline")
    
    console.print()
    console.print(api_table)
    console.print()


def _setup_groq_api_key(current_config: Config) -> Optional[str]:
    """Setup Groq API key (default provider - FREE)."""
    logger = get_logger()
    console = logger.console
    
    console.print("\n[bold cyan]━━━ Groq API Key (FREE - Recommended) ━━━[/bold cyan]\n")
    console.print("[green]Groq is the default provider - completely FREE![/green]")
    console.print("Used for both transcription (Whisper) and analysis (Llama 3.3)")
    console.print()
    
    existing_key = get_groq_api_key()
    if existing_key:
        console.print(f"[green]✓[/green] Already configured: {_mask_key(existing_key)}")
        if not Confirm.ask("Update Groq API key?", default=False):
            return None
    
    console.print("To get a FREE Groq API key:")
    console.print(f"  1. Visit: [link={GROQ_API_URL}]{GROQ_API_URL}[/link]")
    console.print("  2. Sign up / Sign in")
    console.print("  3. Create API key")
    console.print()
    
    api_key = Prompt.ask("Enter Groq API key (or Enter to skip)", default="", password=True)
    
    if api_key.strip():
        return api_key.strip()
    
    console.print(f"[yellow]⚠[/yellow] Skipped. Set {ENV_GROQ_API_KEY} env var or run setup again.")
    return None


def _setup_openai_api_key(current_config: Config) -> tuple[Optional[str], Optional[str]]:
    """Setup OpenAI API key and custom base URL (optional - paid or custom endpoint)."""
    logger = get_logger()
    console = logger.console
    
    console.print("\n[bold cyan]━━━ OpenAI / Custom Endpoint Setup ━━━[/bold cyan]\n")
    console.print("OpenAI provides high-quality transcription and analysis.")
    console.print("You can also use OpenAI-compatible APIs like:")
    console.print("  • Together AI (https://api.together.xyz/v1)")
    console.print("  • OpenRouter (https://openrouter.ai/api/v1)")
    console.print("  • LM Studio (http://localhost:1234/v1)")
    console.print("  • vLLM (http://localhost:8000/v1)")
    console.print()
    
    existing_key = get_openai_api_key()
    existing_url = current_config.openai_base_url
    
    if existing_key:
        console.print(f"[green]✓[/green] API Key: {_mask_key(existing_key)}")
    if existing_url:
        console.print(f"[green]✓[/green] Base URL: {existing_url}")
    
    if existing_key or existing_url:
        if not Confirm.ask("Update OpenAI settings?", default=False):
            return None, None
    
    if not Confirm.ask("Configure OpenAI / Custom endpoint?", default=False):
        return None, None
    
    # API Key
    console.print()
    console.print("Enter API key from your provider:")
    console.print(f"  OpenAI: [link={OPENAI_API_URL}]{OPENAI_API_URL}[/link]")
    console.print("  Together AI: https://api.together.xyz/settings/api-keys")
    console.print("  OpenRouter: https://openrouter.ai/keys")
    console.print()
    
    api_key = Prompt.ask("API key", default="", password=True)
    api_key = api_key.strip() if api_key.strip() else None
    
    # Base URL
    console.print()
    console.print("Custom base URL (leave empty for official OpenAI):")
    console.print("  Together AI: https://api.together.xyz/v1")
    console.print("  OpenRouter: https://openrouter.ai/api/v1")
    console.print("  LM Studio: http://localhost:1234/v1")
    console.print()
    
    base_url = Prompt.ask("Base URL", default=existing_url or "")
    base_url = base_url.strip() if base_url.strip() else None
    
    return api_key, base_url


def _setup_gemini_api_key(current_config: Config) -> Optional[str]:
    """Setup Gemini API key (optional - free tier)."""
    logger = get_logger()
    console = logger.console
    
    console.print("\n[bold cyan]━━━ Gemini API Key (Optional - Free Tier) ━━━[/bold cyan]\n")
    console.print("Google Gemini for analysis (large context window).")
    console.print("[yellow]Note: Only supports English transcription.[/yellow]")
    console.print()
    
    existing_key = get_gemini_api_key()
    if existing_key:
        console.print(f"[green]✓[/green] Already configured: {_mask_key(existing_key)}")
        if not Confirm.ask("Update Gemini API key?", default=False):
            return None
    
    if not Confirm.ask("Configure Gemini API key?", default=False):
        return None
    
    console.print(f"  Get key at: [link={GEMINI_API_URL}]{GEMINI_API_URL}[/link]")
    console.print()
    
    api_key = Prompt.ask("Enter Gemini API key", default="", password=True)
    return api_key.strip() if api_key.strip() else None


def _setup_default_providers(current_config: Config) -> tuple[Optional[TranscriberProvider], Optional[AnalyzerProvider], Optional[str], Optional[str]]:
    """Setup default transcriber and analyzer providers with models."""
    logger = get_logger()
    console = logger.console
    
    console.print("\n[bold cyan]━━━ Default Providers ━━━[/bold cyan]\n")
    
    console.print("Available transcribers:")
    console.print("  [green]1. openai[/green] - OpenAI Whisper (default, high quality)")
    console.print("  2. groq   - Groq Whisper (free, fast)")
    console.print("  3. deepgram - Deepgram Nova ($200 free credit)")
    console.print("  4. elevenlabs - ElevenLabs Scribe (99 languages)")
    console.print("  5. local  - faster-whisper (offline, slower)")
    console.print()
    
    transcriber_choice = Prompt.ask(
        "Default transcriber",
        choices=["openai", "groq", "deepgram", "elevenlabs", "local", ""],
        default=current_config.default_transcriber
    )
    
    console.print()
    console.print("Available analyzers:")
    console.print("  [green]1. openai[/green] - OpenAI GPT-4 (default, high quality)")
    console.print("  2. groq   - Groq Llama 3.3 (free, fast)")
    console.print("  3. deepseek - DeepSeek (very affordable)")
    console.print("  4. gemini - Google Gemini (free tier)")
    console.print("  5. mistral - Mistral AI (free tier)")
    console.print("  6. ollama - Local LLM (offline)")
    console.print()
    
    analyzer_choice = Prompt.ask(
        "Default analyzer",
        choices=["openai", "groq", "deepseek", "gemini", "mistral", "ollama", ""],
        default=current_config.default_analyzer
    )
    
    transcriber = transcriber_choice if transcriber_choice else None
    analyzer = analyzer_choice if analyzer_choice else None
    
    # Setup default models
    transcriber_model = None
    analyzer_model = None
    
    if Confirm.ask("\nConfigure default models?", default=False):
        console.print()
        console.print("[bold]Transcriber Models:[/bold]")
        console.print("  OpenAI: whisper-1")
        console.print("  Groq: whisper-large-v3, whisper-large-v3-turbo")
        console.print("  Deepgram: nova-3, nova-2")
        console.print("  Local: tiny, base, small, medium, large-v3")
        console.print()
        
        current_t_model = current_config.default_transcriber_model or ""
        t_model = Prompt.ask("Default transcriber model (Enter to skip)", default=current_t_model)
        if t_model.strip():
            transcriber_model = t_model.strip()
        
        console.print()
        console.print("[bold]Analyzer Models:[/bold]")
        console.print("  OpenAI: gpt-4o, gpt-4o-mini, gpt-4-turbo")
        console.print("  Groq: openai/gpt-oss-120b, llama-3.3-70b-versatile")
        console.print("  DeepSeek: deepseek-chat, deepseek-reasoner")
        console.print("  Gemini: gemini-2.0-flash, gemini-1.5-pro")
        console.print("  Mistral: mistral-small-latest, mistral-large-latest")
        console.print("  Custom endpoint: any model supported by your provider")
        console.print()
        
        current_a_model = current_config.default_analyzer_model or ""
        a_model = Prompt.ask("Default analyzer model (Enter to skip)", default=current_a_model)
        if a_model.strip():
            analyzer_model = a_model.strip()
    
    return transcriber, analyzer, transcriber_model, analyzer_model


def _setup_ffmpeg(current_config: Config) -> Optional[str]:
    """Setup FFmpeg path."""
    logger = get_logger()
    console = logger.console
    
    console.print("\n[bold cyan]━━━ FFmpeg Setup ━━━[/bold cyan]\n")
    
    deps = check_dependencies()
    
    if deps.ffmpeg_found and deps.ffprobe_found:
        console.print(f"[green]✓[/green] FFmpeg found: {deps.ffmpeg_path}")
        console.print(f"[green]✓[/green] FFprobe found: {deps.ffprobe_path}")
        
        if not Confirm.ask("Use a different FFmpeg path?", default=False):
            return None
    else:
        console.print("[yellow]⚠[/yellow] FFmpeg not found")
        console.print()
        console.print(f"[bold]Installation for {_get_platform_name()}:[/bold]")
        for line in _get_ffmpeg_install_instructions():
            console.print(f"  {line}")
        console.print()
    
    if Confirm.ask("Specify custom FFmpeg path?", default=False):
        custom_path = Prompt.ask("FFmpeg directory path")
        if custom_path.strip():
            test_ffmpeg = find_ffmpeg(custom_path.strip())
            test_ffprobe = find_ffprobe(custom_path.strip())
            if test_ffmpeg and test_ffprobe:
                console.print(f"[green]✓[/green] Found FFmpeg at: {test_ffmpeg}")
                return custom_path.strip()
            console.print("[red]✗[/red] FFmpeg not found at that path")
    
    return None


def _setup_ytdlp() -> None:
    """Show yt-dlp installation guidance."""
    logger = get_logger()
    console = logger.console
    
    console.print("\n[bold cyan]━━━ yt-dlp Setup (Optional) ━━━[/bold cyan]\n")
    
    ytdlp_path = shutil.which("yt-dlp")
    
    if ytdlp_path:
        console.print(f"[green]✓[/green] yt-dlp found: {ytdlp_path}")
        return
    
    console.print("[yellow]○[/yellow] yt-dlp not found (optional)")
    console.print("  Only needed for YouTube URL downloads")
    console.print()
    
    if Confirm.ask("Show installation instructions?", default=False):
        for line in _get_ytdlp_install_instructions():
            console.print(f"  {line}")


def _setup_local_options(current_config: Config) -> tuple[Optional[str], bool]:
    """Setup local/offline options (Ollama, faster-whisper)."""
    logger = get_logger()
    console = logger.console
    
    console.print("\n[bold cyan]━━━ Local/Offline Options ━━━[/bold cyan]\n")
    
    ollama_host = None
    install_whisper = False
    
    # Ollama
    console.print("[bold]Ollama[/bold] - Local LLM for analysis (offline)")
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            console.print("[green]✓[/green] Ollama is running on localhost:11434")
        else:
            console.print("[yellow]○[/yellow] Ollama not responding")
    except Exception:
        console.print("[yellow]○[/yellow] Ollama not running")
        console.print(f"  Install from: [link={OLLAMA_URL}]{OLLAMA_URL}[/link]")
    
    if Confirm.ask("Use custom Ollama host?", default=False):
        host = Prompt.ask("Ollama host URL", default=current_config.ollama_host)
        if host.strip():
            ollama_host = host.strip()
    
    console.print()
    
    # faster-whisper
    console.print("[bold]faster-whisper[/bold] - Local transcription (offline)")
    try:
        import faster_whisper
        console.print("[green]✓[/green] faster-whisper is installed")
    except ImportError:
        console.print("[yellow]○[/yellow] faster-whisper not installed")
        console.print("  Install with: pip install faster-whisper")
        if Confirm.ask("Show installation command?", default=False):
            console.print()
            console.print("  [bold]pip install faster-whisper[/bold]")
            console.print()
            console.print("  Note: First run will download the model (~150MB for 'base')")
    
    return ollama_host, install_whisper


def _setup_defaults(current_config: Config) -> dict:
    """Setup default output settings."""
    logger = get_logger()
    console = logger.console
    
    console.print("\n[bold cyan]━━━ Default Settings ━━━[/bold cyan]\n")
    
    if not Confirm.ask("Configure default settings?", default=False):
        return {}
    
    settings = {}
    
    # Language
    console.print()
    console.print("Default language for transcription:")
    console.print("  id = Indonesian, en = English, etc.")
    lang = Prompt.ask("Language code", default=current_config.default_language)
    if lang.strip():
        settings["language"] = lang.strip()
    
    # Aspect ratio
    console.print()
    console.print("Default aspect ratio:")
    console.print("  9:16 = TikTok/Reels, 1:1 = Instagram, 16:9 = YouTube")
    ratio = Prompt.ask(
        "Aspect ratio",
        choices=["9:16", "1:1", "16:9"],
        default=current_config.default_aspect_ratio
    )
    settings["aspect_ratio"] = ratio
    
    # Caption style
    console.print()
    console.print("Default caption style:")
    console.print("  default, bold, minimal, karaoke")
    style = Prompt.ask(
        "Caption style",
        choices=["default", "bold", "minimal", "karaoke"],
        default=current_config.default_caption_style
    )
    settings["caption_style"] = style
    
    # Max clips
    console.print()
    max_clips = Prompt.ask("Max clips per video", default=str(current_config.max_clips))
    try:
        settings["max_clips"] = int(max_clips)
    except ValueError:
        pass
    
    # Min duration
    console.print()
    console.print("Minimum clip duration (seconds):")
    min_dur = Prompt.ask("Min duration", default=str(current_config.min_duration))
    try:
        settings["min_duration"] = int(min_dur)
    except ValueError:
        pass
    
    # Max duration
    console.print()
    console.print("Maximum clip duration (seconds):")
    max_dur = Prompt.ask("Max duration", default=str(current_config.max_duration))
    try:
        settings["max_duration"] = int(max_dur)
    except ValueError:
        pass
    
    # Output directory
    console.print()
    console.print("Default output directory:")
    output_dir = Prompt.ask("Output directory", default=current_config.default_output_dir)
    if output_dir.strip():
        settings["output_dir"] = output_dir.strip()
    
    return settings


def _save_setup_config(
    current_config: Config,
    groq_key: Optional[str],
    openai_key: Optional[str],
    gemini_key: Optional[str],
    openai_base_url: Optional[str],
    transcriber: Optional[TranscriberProvider],
    analyzer: Optional[AnalyzerProvider],
    transcriber_model: Optional[str],
    analyzer_model: Optional[str],
    ffmpeg_path: Optional[str],
    ollama_host: Optional[str],
    defaults: dict,
) -> bool:
    """Save configuration from setup wizard."""
    logger = get_logger()
    console = logger.console
    
    # Build new config
    new_config = Config(
        # API Keys
        groq_api_key=groq_key if groq_key else current_config.groq_api_key,
        openai_api_key=openai_key if openai_key else current_config.openai_api_key,
        gemini_api_key=gemini_key if gemini_key else current_config.gemini_api_key,
        # Providers
        default_transcriber=transcriber if transcriber else current_config.default_transcriber,
        default_analyzer=analyzer if analyzer else current_config.default_analyzer,
        default_transcriber_model=transcriber_model if transcriber_model else current_config.default_transcriber_model,
        default_analyzer_model=analyzer_model if analyzer_model else current_config.default_analyzer_model,
        ollama_host=ollama_host if ollama_host else current_config.ollama_host,
        openai_base_url=openai_base_url if openai_base_url else current_config.openai_base_url,
        # FFmpeg
        ffmpeg_path=ffmpeg_path if ffmpeg_path else current_config.ffmpeg_path,
        # Defaults
        default_language=defaults.get("language", current_config.default_language),
        default_aspect_ratio=defaults.get("aspect_ratio", current_config.default_aspect_ratio),
        default_caption_style=defaults.get("caption_style", current_config.default_caption_style),
        max_clips=defaults.get("max_clips", current_config.max_clips),
        min_duration=defaults.get("min_duration", current_config.min_duration),
        max_duration=defaults.get("max_duration", current_config.max_duration),
        default_output_dir=defaults.get("output_dir", current_config.default_output_dir),
    )
    
    try:
        save_config(new_config)
        config_path = get_config_path()
        console.print(f"\n[green]✓[/green] Configuration saved to: {config_path}")
        return True
    except Exception as e:
        console.print(f"\n[red]✗[/red] Failed to save: {e}")
        return False


def run_setup_wizard() -> int:
    """Run the interactive setup wizard.
    
    Returns:
        Exit code indicating success or failure
    """
    logger = get_logger()
    console = logger.console
    
    # Header
    console.print()
    console.print(Panel.fit(
        "[bold cyan]SmartClip AI - Setup Wizard[/bold cyan]\n"
        "[dim]Configure API keys, providers, and settings[/dim]",
        border_style="cyan"
    ))
    console.print()
    
    # Check and display current status
    status = _check_current_status()
    _display_status_table(status)
    
    # Load current config
    current_config = load_config()
    
    # Track changes
    groq_key = None
    openai_key = None
    gemini_key = None
    transcriber = None
    analyzer = None
    ffmpeg_path = None
    ollama_host = None
    defaults = {}
    
    # Step 1: Groq API Key (default - FREE)
    groq_key = _setup_groq_api_key(current_config)
    
    # Step 2: Other API Keys (optional)
    openai_key = None
    openai_base_url = None
    if Confirm.ask("\nConfigure other API providers?", default=False):
        openai_key, openai_base_url = _setup_openai_api_key(current_config)
        gemini_key = _setup_gemini_api_key(current_config)
    
    # Step 3: Default providers
    transcriber_model = None
    analyzer_model = None
    if Confirm.ask("\nConfigure default providers?", default=False):
        transcriber, analyzer, transcriber_model, analyzer_model = _setup_default_providers(current_config)
    
    # Step 4: FFmpeg
    if not status["ffmpeg"]["found"] or Confirm.ask("\nConfigure FFmpeg?", default=False):
        ffmpeg_path = _setup_ffmpeg(current_config)
    
    # Step 5: yt-dlp (informational)
    if not status["ytdlp"]["found"]:
        _setup_ytdlp()
    
    # Step 6: Local/Offline options
    if Confirm.ask("\nConfigure local/offline options (Ollama, faster-whisper)?", default=False):
        ollama_host, _ = _setup_local_options(current_config)
    
    # Step 7: Default settings
    defaults = _setup_defaults(current_config)
    
    # Save configuration
    _save_setup_config(
        current_config,
        groq_key, openai_key, gemini_key, openai_base_url,
        transcriber, analyzer, transcriber_model, analyzer_model,
        ffmpeg_path, ollama_host,
        defaults
    )
    
    # Final summary
    console.print("\n[bold cyan]━━━ Setup Complete ━━━[/bold cyan]\n")
    
    final_status = _check_current_status()
    
    # Check if ready
    ready = (
        final_status["python"]["ok"] and
        final_status["ffmpeg"]["found"] and
        final_status["groq_api_key"]["configured"]
    )
    
    if ready:
        console.print("[green]✓ SmartClip AI is ready to use![/green]")
        console.print()
        console.print("Try it out:")
        console.print("  [bold]sclip -i video.mp4[/bold]")
        console.print("  [bold]sclip -u 'https://youtube.com/...'[/bold]")
    else:
        console.print("[yellow]⚠ Some components are missing:[/yellow]")
        if not final_status["ffmpeg"]["found"]:
            console.print("  • FFmpeg needs to be installed")
        if not final_status["groq_api_key"]["configured"]:
            console.print("  • Groq API key not configured (FREE at console.groq.com)")
        console.print()
        console.print("Run [bold]sclip --setup[/bold] again after fixing")
    
    console.print()
    return ExitCode.SUCCESS


__all__ = ["run_setup_wizard"]
