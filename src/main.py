"""Entry point & CLI setup for SmartClip AI.

This module provides the main CLI interface using Click, handling:
- Argument parsing for all CLI options
- Routing to appropriate commands (clip, setup, check-deps, info)
- Global error handling and cleanup
- Version and help display

CLI Structure:
    sclip [OPTIONS]
    
    Main options:
        -i, --input FILE      Process local video file
        -u, --url URL         Process YouTube video
        -o, --output DIR      Output directory (default: ./output)
        -n, --max-clips N     Maximum clips to generate (default: 5)
        
    Special commands:
        --check-deps          Check dependency status
        --setup               Run interactive setup wizard
        --info                Display video information only
        --dry-run             Analyze without rendering
        
    See 'sclip --help' for full option list.

Exit Codes:
    0: Success
    1: Dependency error (FFmpeg missing, etc.)
    2: Input error (file not found, invalid URL)
    3: Output error (cannot write to directory)
    4: API error (Gemini API issues)
    5: Processing error (rendering failed)
    6: Validation error (invalid options)
    130: User interrupt (Ctrl+C)

Usage:
    # Process local video
    sclip -i podcast.mp4
    
    # Process YouTube video
    sclip -u "https://youtube.com/watch?v=..."
    
    # Preview without rendering
    sclip -i video.mp4 --dry-run
    
    # Custom settings
    sclip -i video.mp4 -n 3 -a 1:1 -s bold
"""

import sys
from typing import Optional

import click

from src.types import CLIOptions, ExitCode, AspectRatio, CaptionStyle, TranscriberProvider, AnalyzerProvider
from src.utils.cleanup import setup_cleanup_context, setup_signal_handlers
from src.utils.config import get_api_key, get_ffmpeg_path, get_groq_api_key, get_openai_api_key, get_gemini_api_key, get_deepgram_api_key, get_deepseek_api_key, get_elevenlabs_api_key, get_mistral_api_key, get_openai_base_url, get_default_transcriber_model, get_default_analyzer_model, load_config
from src.utils.logger import setup_logger, get_logger


# Version info - follows semantic versioning
__version__ = "0.2.0"
__app_name__ = "SmartClip AI"


def version_callback(ctx: click.Context, param: click.Parameter, value: bool) -> None:
    """Display version information and exit.
    
    Called when --version flag is provided. Shows app name, version,
    and a brief description.
    """
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"{__app_name__} v{__version__}")
    click.echo("Transform long-form videos into viral-ready short clips using Google Gemini AI")
    ctx.exit(0)


@click.command(
    name="sclip",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option(
    "-u", "--url",
    type=str,
    default=None,
    help="YouTube URL to download and process",
)
@click.option(
    "-i", "--input",
    "input_file",  # Rename to avoid shadowing builtin
    type=click.Path(exists=False),
    default=None,
    help="Path to local video file",
)
@click.option(
    "-o", "--output",
    type=click.Path(),
    default="./output",
    show_default=True,
    help="Output directory for generated clips",
)
@click.option(
    "--subtitle",
    type=click.Path(exists=True),
    default=None,
    help="External subtitle file (.srt or .vtt) to skip transcription",
)
@click.option(
    "-n", "--max-clips",
    type=int,
    default=5,
    show_default=True,
    help="Maximum number of clips to generate",
)
@click.option(
    "--min-duration",
    type=int,
    default=60,
    show_default=True,
    help="Minimum clip duration in seconds",
)
@click.option(
    "--max-duration",
    type=int,
    default=180,
    show_default=True,
    help="Maximum clip duration in seconds",
)
@click.option(
    "-a", "--aspect-ratio",
    type=click.Choice(["9:16", "1:1", "16:9"]),
    default="9:16",
    show_default=True,
    help="Output aspect ratio for clips",
)
@click.option(
    "-s", "--caption-style",
    type=click.Choice(["default", "bold", "minimal", "karaoke"]),
    default="default",
    show_default=True,
    help="Caption style preset",
)
@click.option(
    "-l", "--language",
    type=str,
    default="id",
    show_default=True,
    help="Language code for captions and analysis (e.g., 'id' for Indonesian, 'en' for English)",
)
@click.option(
    "-f", "--force",
    is_flag=True,
    default=False,
    help="Overwrite existing output files",
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose debug output",
)
@click.option(
    "-q", "--quiet",
    is_flag=True,
    default=False,
    help="Suppress all output except errors",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Analyze video and show clips without rendering",
)
@click.option(
    "--no-captions",
    is_flag=True,
    default=False,
    help="Skip caption burn-in",
)
@click.option(
    "--no-metadata",
    is_flag=True,
    default=False,
    help="Skip metadata file generation",
)
@click.option(
    "--keep-temp",
    is_flag=True,
    default=False,
    help="Keep temporary files (for debugging)",
)
@click.option(
    "--api-key",
    type=str,
    default=None,
    envvar="GEMINI_API_KEY",
    help="Gemini API key (or set GEMINI_API_KEY env var)",
)
@click.option(
    "--model",
    type=str,
    default="gemini-2.0-flash",
    show_default=True,
    help="Gemini model to use for analysis",
)
@click.option(
    "--ffmpeg-path",
    type=click.Path(),
    default=None,
    help="Custom path to FFmpeg executable",
)
@click.option(
    "--transcriber",
    type=click.Choice(["groq", "openai", "deepgram", "elevenlabs", "local"]),
    default="openai",
    show_default=True,
    help="Transcription provider (openai=OpenAI Whisper, groq=free Whisper API, deepgram=Deepgram Nova, elevenlabs=ElevenLabs Scribe, local=faster-whisper)",
)
@click.option(
    "--analyzer",
    type=click.Choice(["groq", "deepseek", "gemini", "openai", "mistral", "ollama"]),
    default="openai",
    show_default=True,
    help="Analysis provider for viral moment detection",
)
@click.option(
    "--groq-api-key",
    type=str,
    default=None,
    envvar="GROQ_API_KEY",
    help="Groq API key (or set GROQ_API_KEY env var)",
)
@click.option(
    "--openai-api-key",
    type=str,
    default=None,
    envvar="OPENAI_API_KEY",
    help="OpenAI API key (or set OPENAI_API_KEY env var)",
)
@click.option(
    "--gemini-api-key",
    type=str,
    default=None,
    envvar="GEMINI_API_KEY",
    help="Gemini API key (or set GEMINI_API_KEY env var)",
)
@click.option(
    "--deepgram-api-key",
    type=str,
    default=None,
    envvar="DEEPGRAM_API_KEY",
    help="Deepgram API key (or set DEEPGRAM_API_KEY env var) - $200 free credit",
)
@click.option(
    "--deepseek-api-key",
    type=str,
    default=None,
    envvar="DEEPSEEK_API_KEY",
    help="DeepSeek API key (or set DEEPSEEK_API_KEY env var) - very affordable",
)
@click.option(
    "--elevenlabs-api-key",
    type=str,
    default=None,
    envvar="ELEVENLABS_API_KEY",
    help="ElevenLabs API key (or set ELEVENLABS_API_KEY env var) - 99 languages",
)
@click.option(
    "--mistral-api-key",
    type=str,
    default=None,
    envvar="MISTRAL_API_KEY",
    help="Mistral API key (or set MISTRAL_API_KEY env var) - free tier available",
)
@click.option(
    "--transcriber-model",
    type=str,
    default=None,
    help="Model for transcription (default: whisper-large-v3-turbo for Groq)",
)
@click.option(
    "--analyzer-model",
    type=str,
    default=None,
    help="Model for analysis (default: openai/gpt-oss-120b for Groq)",
)
@click.option(
    "--ollama-host",
    type=str,
    default="http://localhost:11434",
    show_default=True,
    help="Ollama server host URL",
)
@click.option(
    "--openai-base-url",
    type=str,
    default=None,
    help="Custom base URL for OpenAI-compatible APIs (e.g., https://api.together.xyz, http://localhost:1234/v1)",
)
@click.option(
    "--info",
    "show_info",  # Rename to avoid confusion with info() method
    is_flag=True,
    default=False,
    help="Display video information only (no processing)",
)
@click.option(
    "--check-deps",
    is_flag=True,
    default=False,
    help="Check and display dependency status",
)
@click.option(
    "--setup",
    "run_setup",  # Rename to avoid confusion
    is_flag=True,
    default=False,
    help="Run interactive setup wizard",
)
@click.option(
    "--version",
    is_flag=True,
    callback=version_callback,
    expose_value=False,
    is_eager=True,
    help="Show version and exit",
)
def main(
    url: Optional[str],
    input_file: Optional[str],
    output: str,
    subtitle: Optional[str],
    max_clips: int,
    min_duration: int,
    max_duration: int,
    aspect_ratio: str,
    caption_style: str,
    language: str,
    force: bool,
    verbose: bool,
    quiet: bool,
    dry_run: bool,
    no_captions: bool,
    no_metadata: bool,
    keep_temp: bool,
    api_key: Optional[str],
    model: str,
    ffmpeg_path: Optional[str],
    transcriber: str,
    analyzer: str,
    groq_api_key: Optional[str],
    openai_api_key: Optional[str],
    gemini_api_key: Optional[str],
    deepgram_api_key: Optional[str],
    deepseek_api_key: Optional[str],
    elevenlabs_api_key: Optional[str],
    mistral_api_key: Optional[str],
    transcriber_model: Optional[str],
    analyzer_model: Optional[str],
    ollama_host: str,
    openai_base_url: Optional[str],
    show_info: bool,
    check_deps: bool,
    run_setup: bool,
) -> None:
    """SmartClip AI - Transform long-form videos into viral-ready short clips.
    
    \b
    Examples:
      sclip -i podcast.mp4                    # Process local video (default: Groq)
      sclip -u "https://youtu.be/xxxxx"       # Process YouTube video
      sclip -i video.mp4 --dry-run            # Preview without rendering
      sclip -i video.mp4 -n 3 -a 1:1          # 3 clips, square format
      sclip -i video.mp4 --subtitle sub.srt   # Use external subtitle (skip transcription)
      sclip -i video.mp4 --analyzer gemini    # Use Gemini for analysis
      sclip -i video.mp4 --analyzer deepseek  # Use DeepSeek (very affordable)
      sclip -i video.mp4 --analyzer mistral   # Use Mistral (free tier)
      sclip -i video.mp4 --transcriber elevenlabs  # Use ElevenLabs (99 languages)
      sclip -i video.mp4 --transcriber deepgram  # Use Deepgram ($200 free)
      sclip -i video.mp4 --transcriber local --analyzer ollama  # Fully offline
      sclip --check-deps                      # Check dependencies
      sclip --setup                           # Run setup wizard
    
    \b
    Custom OpenAI-Compatible Endpoints:
      # Use any OpenAI-compatible API with --openai-base-url
      sclip -i video.mp4 --analyzer openai --openai-base-url https://api.together.xyz/v1 --analyzer-model meta-llama/Llama-3-70b-chat-hf
      sclip -i video.mp4 --analyzer openai --openai-base-url http://localhost:1234/v1 --analyzer-model local-model
      sclip -i video.mp4 --analyzer openai --openai-base-url https://openrouter.ai/api/v1 --analyzer-model anthropic/claude-3-haiku
    
    \b
    Provider Options:
      --transcriber groq      Groq Whisper API (free, fast) [DEFAULT]
      --transcriber openai    OpenAI Whisper API
      --transcriber deepgram  Deepgram Nova ($200 free credit)
      --transcriber elevenlabs ElevenLabs Scribe (99 languages)
      --transcriber local     Local faster-whisper (offline)
      
      --analyzer groq         Groq LLMs (free, fast) [DEFAULT]
      --analyzer deepseek     DeepSeek LLMs (very affordable)
      --analyzer gemini       Google Gemini
      --analyzer openai       OpenAI GPT-4
      --analyzer mistral      Mistral AI (free tier available)
      --analyzer ollama       Local Ollama (offline)
    
    \b
    For more information, visit: https://github.com/sakirsyarian/sclip
    """
    # Setup logger first
    logger = setup_logger(verbose=verbose, quiet=quiet)
    
    # Setup cleanup context and signal handlers
    cleanup_ctx = setup_cleanup_context(skip_cleanup=keep_temp)
    setup_signal_handlers(cleanup_ctx)
    
    try:
        # Handle special commands first
        if check_deps:
            exit_code = handle_check_deps(ffmpeg_path, api_key, verbose)
            sys.exit(exit_code)
        
        if run_setup:
            exit_code = handle_setup()
            sys.exit(exit_code)
        
        # Handle --info command (requires input)
        if show_info:
            exit_code = handle_info(input_file, url, ffmpeg_path, keep_temp)
            sys.exit(exit_code)
        
        # Build CLI options
        # Resolve API keys: CLI > env var > config
        resolved_groq_key = get_groq_api_key(groq_api_key)
        resolved_openai_key = get_openai_api_key(openai_api_key)
        resolved_gemini_key = get_gemini_api_key(gemini_api_key or api_key)
        resolved_deepgram_key = get_deepgram_api_key(deepgram_api_key)
        resolved_deepseek_key = get_deepseek_api_key(deepseek_api_key)
        resolved_elevenlabs_key = get_elevenlabs_api_key(elevenlabs_api_key)
        resolved_mistral_key = get_mistral_api_key(mistral_api_key)
        resolved_openai_base_url = get_openai_base_url(openai_base_url)
        resolved_transcriber_model = get_default_transcriber_model(transcriber_model)
        resolved_analyzer_model = get_default_analyzer_model(analyzer_model)
        
        options = CLIOptions(
            url=url,
            input=input_file,
            output=output,
            subtitle=subtitle,
            max_clips=max_clips,
            min_duration=min_duration,
            max_duration=max_duration,
            aspect_ratio=aspect_ratio,  # type: ignore
            caption_style=caption_style,  # type: ignore
            language=language,
            force=force,
            verbose=verbose,
            quiet=quiet,
            dry_run=dry_run,
            no_captions=no_captions,
            no_metadata=no_metadata,
            keep_temp=keep_temp,
            ffmpeg_path=get_ffmpeg_path(ffmpeg_path),
            # New provider options
            transcriber=transcriber,  # type: ignore
            analyzer=analyzer,  # type: ignore
            groq_api_key=resolved_groq_key,
            openai_api_key=resolved_openai_key,
            gemini_api_key=resolved_gemini_key,
            deepgram_api_key=resolved_deepgram_key,
            deepseek_api_key=resolved_deepseek_key,
            elevenlabs_api_key=resolved_elevenlabs_key,
            mistral_api_key=resolved_mistral_key,
            transcriber_model=resolved_transcriber_model,
            analyzer_model=resolved_analyzer_model,
            ollama_host=ollama_host,
            openai_base_url=resolved_openai_base_url,
            # Legacy (for backward compatibility)
            api_key=resolved_gemini_key,
            model=model,
        )
        
        # Route to clip command
        exit_code = handle_clip(options)
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.warning("\nOperation cancelled by user")
        sys.exit(ExitCode.INTERRUPT)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(ExitCode.PROCESSING_ERROR)


def handle_check_deps(
    ffmpeg_path: Optional[str],
    api_key: Optional[str],
    verbose: bool
) -> int:
    """Handle --check-deps command.
    
    Args:
        ffmpeg_path: Custom FFmpeg path
        api_key: API key from CLI (legacy)
        verbose: Whether to show verbose output
        
    Returns:
        Exit code
    """
    from src.utils.ffmpeg import check_dependencies
    import shutil
    import os
    
    logger = get_logger()
    
    logger.info("Checking dependencies...\n")
    
    all_ok = True
    
    # Check Python version
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 10)
    if py_ok:
        logger.success(f"Python: {py_version}")
    else:
        logger.error(f"Python: {py_version} (requires 3.10+)")
        all_ok = False
    
    # Check FFmpeg/FFprobe
    deps = check_dependencies(ffmpeg_path)
    
    if deps.ffmpeg_found:
        logger.success(f"FFmpeg: {deps.ffmpeg_version or 'found'} ({deps.ffmpeg_path})")
    else:
        logger.error("FFmpeg: not found")
        all_ok = False
    
    if deps.ffprobe_found:
        logger.success(f"FFprobe: {deps.ffprobe_version or 'found'} ({deps.ffprobe_path})")
    else:
        logger.error("FFprobe: not found")
        all_ok = False
    
    # Check yt-dlp (optional)
    ytdlp_path = shutil.which("yt-dlp")
    if ytdlp_path:
        logger.success(f"yt-dlp: found ({ytdlp_path})")
    else:
        logger.warning("yt-dlp: not found (required for YouTube downloads)")
    
    logger.newline()
    logger.info("API Keys:")
    
    # Check Groq API key (default - FREE)
    groq_key = get_groq_api_key()
    if groq_key:
        masked = groq_key[:4] + "..." + groq_key[-4:] if len(groq_key) > 8 else "***"
        logger.success(f"  GROQ_API_KEY: configured ({masked}) [DEFAULT - FREE]")
    else:
        logger.warning("  GROQ_API_KEY: not configured (get free key at console.groq.com)")
    
    # Check OpenAI API key
    openai_key = get_openai_api_key()
    if openai_key:
        masked = openai_key[:4] + "..." + openai_key[-4:] if len(openai_key) > 8 else "***"
        logger.success(f"  OPENAI_API_KEY: configured ({masked})")
    else:
        logger.warning("  OPENAI_API_KEY: not configured (optional - paid)")
    
    # Check Gemini API key
    gemini_key = get_gemini_api_key(api_key)
    if gemini_key:
        masked = gemini_key[:4] + "..." + gemini_key[-4:] if len(gemini_key) > 8 else "***"
        logger.success(f"  GEMINI_API_KEY: configured ({masked})")
    else:
        logger.warning("  GEMINI_API_KEY: not configured (optional - free tier)")
    
    logger.newline()
    logger.info("Local Providers:")
    
    # Check faster-whisper (for local transcription)
    try:
        import faster_whisper
        logger.success("  faster-whisper: installed")
    except ImportError:
        logger.warning("  faster-whisper: not installed (pip install faster-whisper)")
    
    # Check Ollama
    try:
        import httpx
        try:
            response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                logger.success(f"  Ollama: running ({len(models)} models available)")
            else:
                logger.warning("  Ollama: not responding")
        except Exception:
            logger.warning("  Ollama: not running (start with 'ollama serve')")
    except ImportError:
        logger.warning("  Ollama check: httpx not installed")
    
    logger.newline()
    
    if all_ok:
        logger.success("All required dependencies are available!")
        logger.info("\nDefault setup (100% free):")
        logger.info("  --transcriber groq --analyzer groq")
        logger.info("\nOffline setup:")
        logger.info("  --transcriber local --analyzer ollama")
        return ExitCode.SUCCESS
    else:
        logger.error("Some required dependencies are missing. Run 'sclip --setup' for help.")
        return ExitCode.DEPENDENCY_ERROR


def handle_setup() -> int:
    """Handle --setup command.
    
    Returns:
        Exit code
    """
    # Import here to avoid circular imports
    from src.commands.setup import run_setup_wizard
    return run_setup_wizard()


def handle_info(
    input_file: Optional[str],
    url: Optional[str],
    ffmpeg_path: Optional[str],
    keep_temp: bool
) -> int:
    """Handle --info command to display video information.
    
    Args:
        input_file: Path to local video file
        url: YouTube URL (will be downloaded to temp)
        ffmpeg_path: Custom FFmpeg path
        keep_temp: Whether to keep temp files
        
    Returns:
        Exit code
    """
    from src.utils.video import (
        analyze_video, 
        VideoAnalysisError, 
        format_duration, 
        format_resolution, 
        format_bitrate
    )
    from src.utils.validation import validate_input_file, validate_youtube_url
    from src.utils.cleanup import get_cleanup_context
    
    logger = get_logger()
    
    # Validate that we have an input source
    if not input_file and not url:
        logger.error("--info requires either --input or --url")
        return ExitCode.INPUT_ERROR
    
    video_path: Optional[str] = None
    cleanup_downloaded = False
    
    try:
        # Handle YouTube URL - download first
        if url:
            result = validate_youtube_url(url)
            if not result.valid:
                logger.error(result.error or "Invalid YouTube URL")
                return result.error_code or ExitCode.INPUT_ERROR
            
            # Download video to get info
            from src.services.downloader import download_youtube
            
            logger.info("Downloading video to analyze...")
            
            try:
                video_path = download_youtube(url)
                cleanup_downloaded = not keep_temp
            except Exception as e:
                logger.error(f"Failed to download video: {e}")
                return ExitCode.INPUT_ERROR
        else:
            # Local file
            result = validate_input_file(input_file)
            if not result.valid:
                logger.error(result.error or "Invalid input file")
                return result.error_code or ExitCode.INPUT_ERROR
            video_path = input_file
        
        if not video_path:
            logger.error("No video path available")
            return ExitCode.INPUT_ERROR
        
        # Analyze video
        logger.info("Analyzing video...")
        
        try:
            video_info = analyze_video(video_path, ffmpeg_path)
        except FileNotFoundError as e:
            logger.error(str(e))
            return ExitCode.DEPENDENCY_ERROR
        except VideoAnalysisError as e:
            logger.error(str(e))
            return e.error_code
        
        # Display video information in a nice box
        import os
        filename = os.path.basename(video_path)
        
        info_lines = [
            f"File:       {filename}",
            f"Duration:   {format_duration(video_info.duration)} ({video_info.duration:.2f}s)",
            f"Resolution: {format_resolution(video_info.width, video_info.height)}",
            f"Codec:      {video_info.codec}",
            f"Audio:      {video_info.audio_codec}",
            f"Bitrate:    {format_bitrate(video_info.bitrate)}",
            f"FPS:        {video_info.fps:.2f}",
        ]
        
        # Add aspect ratio info
        if video_info.width > 0 and video_info.height > 0:
            aspect = video_info.width / video_info.height
            if abs(aspect - 16/9) < 0.1:
                aspect_str = "16:9 (Landscape)"
            elif abs(aspect - 9/16) < 0.1:
                aspect_str = "9:16 (Portrait)"
            elif abs(aspect - 1) < 0.1:
                aspect_str = "1:1 (Square)"
            elif abs(aspect - 4/3) < 0.1:
                aspect_str = "4:3 (Standard)"
            else:
                aspect_str = f"{aspect:.2f}:1"
            info_lines.append(f"Aspect:     {aspect_str}")
        
        logger.newline()
        logger.box("Video Information", info_lines)
        logger.newline()
        
        return ExitCode.SUCCESS
        
    finally:
        # Cleanup downloaded file if needed
        if cleanup_downloaded and video_path:
            import os
            if os.path.exists(video_path):
                try:
                    os.remove(video_path)
                    logger.debug(f"Cleaned up temp file: {video_path}")
                except OSError:
                    pass


def handle_clip(options: CLIOptions) -> int:
    """Handle main clip command.
    
    Args:
        options: CLI options
        
    Returns:
        Exit code
    """
    from src.utils.validation import validate_options, validate_input_file, validate_youtube_url
    
    logger = get_logger()
    
    # Validate options first
    result = validate_options(options)
    if not result.valid:
        logger.error(result.error or "Invalid options")
        return result.error_code or ExitCode.VALIDATION_ERROR
    
    # Validate input source
    if options.url:
        result = validate_youtube_url(options.url)
        if not result.valid:
            logger.error(result.error or "Invalid YouTube URL")
            return result.error_code or ExitCode.INPUT_ERROR
    elif options.input:
        result = validate_input_file(options.input)
        if not result.valid:
            logger.error(result.error or "Invalid input file")
            return result.error_code or ExitCode.INPUT_ERROR
    
    # Import and execute clip command
    from src.commands.clip import execute_clip
    return execute_clip(options)


# Entry point for direct execution
if __name__ == "__main__":
    main()
