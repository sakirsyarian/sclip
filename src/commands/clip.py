"""Main clipping workflow orchestration.

This module handles the core clip generation workflow, coordinating
all services to transform a video into viral-ready short clips.

New Architecture (v2):
    Video → Extract Audio → Transcribe (Whisper) → Analyze (LLM) → Render

Workflow Steps:
    1. Validate output directory
    2. Download video (if YouTube URL)
    3. Analyze video file (duration, resolution, codec)
    4. Validate video duration (>= 60 seconds)
    5. Extract audio from video
    6. Transcribe audio (Groq/OpenAI/Local Whisper)
    7. Analyze transcript for viral moments (Groq/Gemini/OpenAI/Ollama)
    8. Handle dry-run mode (display preview without rendering)
    9. Render clips with captions
    10. Generate metadata files (title.txt, description.txt)

Provider Options:
    Transcription:
        - groq: Groq Whisper API (free, fast)
        - openai: OpenAI Whisper API
        - local: Local faster-whisper (offline)
    
    Analysis:
        - groq: Groq LLMs (free, fast) - Default
        - gemini: Google Gemini
        - openai: OpenAI GPT-4
        - ollama: Local Ollama (offline)

Usage:
    from src.commands.clip import execute_clip
    
    exit_code = execute_clip(options)
    sys.exit(exit_code)
"""

import asyncio
import os
import tempfile
from pathlib import Path

from src.types import CLIOptions, ExitCode, ClipData
from src.utils.logger import get_logger
from src.utils.cleanup import get_cleanup_context, register_temp_file
from src.utils.validation import validate_output_dir, validate_video_duration
from src.utils.video import analyze_video, format_duration, format_resolution, VideoAnalysisError


def execute_clip(options: CLIOptions) -> int:
    """Execute the main clip generation workflow.
    
    Orchestrates: validate → download → extract audio → transcribe → analyze → render
    
    Args:
        options: CLI options from user input
        
    Returns:
        Exit code indicating success or failure
    """
    return asyncio.run(_execute_clip_async(options))


async def _execute_clip_async(options: CLIOptions) -> int:
    """Async implementation of the clip workflow."""
    logger = get_logger()
    cleanup_ctx = get_cleanup_context()
    
    video_path: str | None = None
    audio_path: str | None = None
    
    try:
        # Step 1: Validate output directory
        output_result = validate_output_dir(options.output, options.force)
        if not output_result.valid:
            logger.error(output_result.error or "Invalid output directory")
            return output_result.error_code or ExitCode.OUTPUT_ERROR
        
        # Step 2: Get video (download if URL, or use local file)
        if options.url:
            logger.info("Downloading video from YouTube...")
            video_path = await _download_video(options.url, cleanup_ctx)
            if video_path is None:
                return ExitCode.PROCESSING_ERROR
            logger.success(f"Downloaded: {os.path.basename(video_path)}")
        else:
            video_path = options.input
            if video_path is None:
                logger.error("No input source provided")
                return ExitCode.INPUT_ERROR
        
        # Step 3: Analyze video file
        logger.info("Analyzing video file...")
        try:
            video_info = analyze_video(video_path, options.ffmpeg_path)
        except (VideoAnalysisError, FileNotFoundError) as e:
            logger.error(f"Failed to analyze video: {e}")
            return ExitCode.PROCESSING_ERROR
        
        # Validate video duration (must be >= 60 seconds)
        duration_result = validate_video_duration(video_info.duration)
        if not duration_result.valid:
            logger.error(duration_result.error or "Video too short")
            return duration_result.error_code or ExitCode.INPUT_ERROR
        
        logger.success(f"Video: {format_duration(video_info.duration)} | {format_resolution(video_info.width, video_info.height)}")
        
        # Step 4: Validate API keys for selected providers
        api_error = _validate_provider_keys(options)
        if api_error:
            logger.error(api_error)
            return ExitCode.API_ERROR
        
        # Step 5: Extract audio from video
        logger.info("Extracting audio...")
        audio_path = await _extract_audio(video_path, options.ffmpeg_path, cleanup_ctx)
        if audio_path is None:
            return ExitCode.PROCESSING_ERROR
        logger.success("Audio extracted")
        
        # Step 6: Transcribe audio
        logger.info(f"Transcribing with {options.transcriber}...")
        transcription = await _transcribe_audio(audio_path, options)
        if transcription is None:
            return ExitCode.API_ERROR
        logger.success(f"Transcription complete ({len(transcription.words)} words)")
        
        # Step 7: Analyze transcript for viral moments
        logger.info(f"Analyzing with {options.analyzer}...")
        clips = await _analyze_transcript(
            transcription=transcription,
            video_duration=video_info.duration,
            options=options
        )
        
        if clips is None:
            return ExitCode.API_ERROR
        
        if not clips:
            logger.warning("No viral moments identified in the video")
            return ExitCode.SUCCESS
        
        logger.success(f"Identified {len(clips)} potential clips")
        
        # Step 8: Handle dry-run mode
        if options.dry_run:
            _display_dry_run_results(clips, video_info, options)
            return ExitCode.SUCCESS
        
        # Step 9: Render clips
        logger.info(f"Rendering {len(clips)} clips...")
        output_paths = await _render_clips(
            video_path=video_path,
            clips=clips,
            options=options
        )
        
        if not output_paths:
            logger.error("Failed to render any clips")
            return ExitCode.PROCESSING_ERROR
        
        # Step 10: Generate metadata (if not disabled)
        if not options.no_metadata:
            _generate_metadata(clips, output_paths, options.output)
        
        # Success!
        logger.newline()
        logger.success(f"Successfully created {len(output_paths)} clips in {options.output}")
        
        for path in output_paths:
            logger.info(f"  → {os.path.basename(path)}")
        
        return ExitCode.SUCCESS
        
    except KeyboardInterrupt:
        logger.warning("\nOperation cancelled by user")
        return ExitCode.INTERRUPT
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if options.verbose:
            import traceback
            traceback.print_exc()
        return ExitCode.PROCESSING_ERROR


def _validate_provider_keys(options: CLIOptions) -> str | None:
    """Validate that required API keys are available for selected providers.
    
    Returns:
        Error message if validation fails, None if OK
    """
    # Check transcriber API key
    if options.transcriber == "groq" and not options.groq_api_key:
        return "Groq API key required for transcription. Set GROQ_API_KEY or use --groq-api-key"
    
    if options.transcriber == "openai" and not options.openai_api_key:
        return "OpenAI API key required for transcription. Set OPENAI_API_KEY or use --openai-api-key"
    
    if options.transcriber == "deepgram" and not options.deepgram_api_key:
        return "Deepgram API key required for transcription. Set DEEPGRAM_API_KEY or use --deepgram-api-key. Get $200 free credit at https://deepgram.com"
    
    if options.transcriber == "elevenlabs" and not options.elevenlabs_api_key:
        return "ElevenLabs API key required for transcription. Set ELEVENLABS_API_KEY or use --elevenlabs-api-key. Get API key at https://elevenlabs.io"
    
    # Check analyzer API key
    if options.analyzer == "groq" and not options.groq_api_key:
        return "Groq API key required for analysis. Set GROQ_API_KEY or use --groq-api-key"
    
    if options.analyzer == "gemini" and not options.gemini_api_key:
        return "Gemini API key required for analysis. Set GEMINI_API_KEY or use --gemini-api-key"
    
    if options.analyzer == "openai" and not options.openai_api_key:
        return "OpenAI API key required for analysis. Set OPENAI_API_KEY or use --openai-api-key"
    
    if options.analyzer == "deepseek" and not options.deepseek_api_key:
        return "DeepSeek API key required for analysis. Set DEEPSEEK_API_KEY or use --deepseek-api-key. Get API key at https://platform.deepseek.com"
    
    if options.analyzer == "mistral" and not options.mistral_api_key:
        return "Mistral API key required for analysis. Set MISTRAL_API_KEY or use --mistral-api-key. Get API key at https://console.mistral.ai"
    
    # Local providers don't need API keys
    # ollama and local transcriber work without keys
    
    return None


async def _download_video(url: str, cleanup_ctx) -> str | None:
    """Download video from YouTube URL."""
    logger = get_logger()
    
    try:
        from src.services.downloader import (
            YouTubeDownloader,
            DownloadError,
            VideoUnavailableError,
            AgeRestrictedError,
            is_yt_dlp_available
        )
        
        if not is_yt_dlp_available():
            logger.error("yt-dlp is not installed. Install with: pip install yt-dlp")
            return None
        
        temp_dir = tempfile.mkdtemp(prefix="sclip_")
        cleanup_ctx.register(temp_dir)
        
        downloader = YouTubeDownloader(temp_dir)
        
        def on_progress(downloaded: int, total: int) -> None:
            if total > 0:
                pct = (downloaded / total) * 100
                logger.debug(f"Download progress: {pct:.1f}%")
        
        video_path = await downloader.download(
            url=url,
            output_dir=temp_dir,
            progress_callback=on_progress,
            register_for_cleanup=True
        )
        
        return video_path
        
    except VideoUnavailableError as e:
        logger.error(f"Video unavailable: {e}")
        return None
    except AgeRestrictedError as e:
        logger.error(f"Age-restricted video: {e}")
        return None
    except DownloadError as e:
        logger.error(f"Download failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None


async def _extract_audio(
    video_path: str,
    ffmpeg_path: str | None,
    cleanup_ctx
) -> str | None:
    """Extract audio from video file."""
    logger = get_logger()
    
    try:
        from src.services.audio import extract_audio, AudioExtractionError
        
        # Create temp file for audio
        fd, audio_path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        cleanup_ctx.register(audio_path)
        
        def on_progress(msg: str) -> None:
            logger.debug(msg)
        
        # Run extraction in thread pool
        loop = asyncio.get_event_loop()
        result_path = await loop.run_in_executor(
            None,
            lambda: extract_audio(
                video_path=video_path,
                output_path=audio_path,
                ffmpeg_path=ffmpeg_path,
                format="mp3",
                sample_rate=16000,
                mono=True,
                progress_callback=on_progress
            )
        )
        
        return result_path
        
    except AudioExtractionError as e:
        logger.error(f"Audio extraction failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Audio extraction error: {e}")
        return None


async def _transcribe_audio(audio_path: str, options: CLIOptions):
    """Transcribe audio using selected provider."""
    logger = get_logger()
    
    try:
        from src.services.transcribers import get_transcriber, TranscriptionResult
        from src.services.transcribers.base import TranscriptionError
        
        # Get API key for provider
        api_key = None
        if options.transcriber == "groq":
            api_key = options.groq_api_key
        elif options.transcriber == "openai":
            api_key = options.openai_api_key
        elif options.transcriber == "deepgram":
            api_key = options.deepgram_api_key
        elif options.transcriber == "elevenlabs":
            api_key = options.elevenlabs_api_key
        
        transcriber = get_transcriber(
            provider=options.transcriber,
            api_key=api_key,
            model=options.transcriber_model
        )
        
        def on_progress(msg: str) -> None:
            logger.debug(msg)
        
        result = await transcriber.transcribe(
            audio_path=audio_path,
            language=options.language,
            progress_callback=on_progress
        )
        
        return result
        
    except TranscriptionError as e:
        logger.error(f"Transcription failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return None


async def _analyze_transcript(
    transcription,
    video_duration: float,
    options: CLIOptions
) -> list[ClipData] | None:
    """Analyze transcript for viral moments using selected provider."""
    logger = get_logger()
    
    try:
        from src.services.analyzers import get_analyzer
        from src.services.analyzers.base import AnalysisError
        
        # Get API key for provider
        api_key = None
        extra_kwargs = {}
        
        if options.analyzer == "groq":
            api_key = options.groq_api_key
        elif options.analyzer == "gemini":
            api_key = options.gemini_api_key
        elif options.analyzer == "openai":
            api_key = options.openai_api_key
        elif options.analyzer == "deepseek":
            api_key = options.deepseek_api_key
        elif options.analyzer == "mistral":
            api_key = options.mistral_api_key
        elif options.analyzer == "ollama":
            extra_kwargs["host"] = options.ollama_host
        
        analyzer = get_analyzer(
            provider=options.analyzer,
            api_key=api_key,
            model=options.analyzer_model,
            **extra_kwargs
        )
        
        def on_progress(msg: str) -> None:
            logger.debug(msg)
        
        result = await analyzer.analyze(
            transcription=transcription,
            video_duration=video_duration,
            max_clips=options.max_clips,
            min_duration=options.min_duration,
            max_duration=options.max_duration,
            language=options.language,
            progress_callback=on_progress
        )
        
        return result.clips
        
    except AnalysisError as e:
        logger.error(f"Analysis failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return None


async def _render_clips(
    video_path: str,
    clips: list[ClipData],
    options: CLIOptions
) -> list[str]:
    """Render all clips with captions."""
    logger = get_logger()
    
    try:
        from src.services.renderer import VideoRenderer, RenderError
        
        renderer = VideoRenderer(ffmpeg_path=options.ffmpeg_path)
        
        output_dir = options.output
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        def on_progress(current: int, total: int) -> None:
            logger.info(f"Rendering clip {current}/{total}...")
        
        hw_info = renderer.get_hw_acceleration_info()
        if hw_info["encoder"]:
            logger.debug(f"Using hardware encoder: {hw_info['encoder']}")
        else:
            logger.debug("Using software encoding (libx264)")
        
        use_parallel = len(clips) > 1
        if use_parallel:
            logger.debug(f"Parallel rendering enabled with {hw_info['max_workers']} workers")
        
        loop = asyncio.get_event_loop()
        output_paths = await loop.run_in_executor(
            None,
            lambda: renderer.render_all_clips(
                input_path=video_path,
                output_dir=output_dir,
                clips=clips,
                options=options,
                progress_callback=on_progress,
                parallel=use_parallel
            )
        )
        
        errors = renderer.get_last_render_errors()
        for idx, title, error in errors:
            logger.warning(f"Failed to render clip {idx} ({title}): {error}")
        
        return output_paths
        
    except RenderError as e:
        logger.error(f"Render error: {e}")
        return []
    except Exception as e:
        logger.error(f"Rendering failed: {e}")
        return []


def _display_dry_run_results(
    clips: list[ClipData],
    video_info,
    options: CLIOptions
) -> None:
    """Display dry-run results without rendering."""
    logger = get_logger()
    
    logger.newline()
    logger.box("DRY RUN MODE", [
        "Analysis complete - no clips will be rendered",
        f"Source: {os.path.basename(video_info.path)}",
        f"Duration: {format_duration(video_info.duration)} | Resolution: {format_resolution(video_info.width, video_info.height)}",
        f"Transcriber: {options.transcriber} | Analyzer: {options.analyzer}",
    ])
    logger.newline()
    
    total_estimated_size = 0
    total_clip_duration = 0
    
    for i, clip in enumerate(clips, 1):
        duration = clip["end_time"] - clip["start_time"]
        total_clip_duration += duration
        start_fmt = format_duration(clip["start_time"])
        end_fmt = format_duration(clip["end_time"])
        
        estimated_size = _estimate_clip_size(
            duration=duration,
            video_info=video_info,
            aspect_ratio=options.aspect_ratio,
            has_captions=not options.no_captions and bool(clip.get("captions"))
        )
        total_estimated_size += estimated_size
        
        content = [
            f"📝 {clip['title']}",
            f"⏱️  {start_fmt} → {end_fmt} ({duration:.1f}s)",
            f"📄 {clip['description'][:80]}{'...' if len(clip['description']) > 80 else ''}",
        ]
        
        if clip.get("captions"):
            content.append(f"💬 {len(clip['captions'])} caption segments")
        else:
            content.append("💬 No captions")
        
        content.append(f"📦 Estimated size: {_format_file_size(estimated_size)}")
        
        logger.box(f"Clip {i}/{len(clips)}", content)
        logger.newline()
    
    processing_multiplier = 1.5
    if not options.no_captions:
        processing_multiplier += 0.3
    estimated_time = total_clip_duration * processing_multiplier
    
    summary_content = [
        f"📊 Total clips: {len(clips)}",
        f"⏱️  Total clip duration: {format_duration(total_clip_duration)}",
        f"📦 Total estimated size: {_format_file_size(total_estimated_size)}",
        f"⏳ Estimated processing time: ~{format_duration(estimated_time)}",
        "",
        f"📁 Output directory: {options.output}",
        f"📐 Aspect ratio: {options.aspect_ratio}",
        f"🎨 Caption style: {options.caption_style if not options.no_captions else 'disabled'}",
    ]
    
    if options.no_metadata:
        summary_content.append("📝 Metadata generation: disabled")
    
    logger.box("Summary", summary_content)
    logger.newline()
    logger.info("Run without --dry-run to render these clips")


def _estimate_clip_size(
    duration: float,
    video_info,
    aspect_ratio: str,
    has_captions: bool
) -> int:
    """Estimate the output file size for a clip."""
    if video_info.bitrate > 0:
        base_bitrate = video_info.bitrate
    else:
        pixels = video_info.width * video_info.height
        if pixels >= 1920 * 1080:
            base_bitrate = 8_000_000
        elif pixels >= 1280 * 720:
            base_bitrate = 5_000_000
        else:
            base_bitrate = 2_500_000
    
    aspect_multiplier = {
        "9:16": 0.6,
        "1:1": 0.75,
        "16:9": 0.9,
    }.get(aspect_ratio, 0.75)
    
    adjusted_bitrate = base_bitrate * aspect_multiplier
    
    if has_captions:
        adjusted_bitrate *= 1.1
    
    estimated_bytes = int((adjusted_bitrate * duration) / 8)
    return estimated_bytes


def _format_file_size(size_bytes: int) -> str:
    """Format file size in bytes to human-readable string."""
    if size_bytes < 0:
        return "unknown"
    
    if size_bytes >= 1_073_741_824:
        return f"{size_bytes / 1_073_741_824:.1f} GB"
    elif size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes} bytes"


def _generate_metadata(
    clips: list[ClipData],
    output_paths: list[str],
    output_dir: str
) -> None:
    """Generate metadata files for rendered clips."""
    logger = get_logger()
    
    for i, (clip, output_path) in enumerate(zip(clips, output_paths)):
        try:
            base_name = os.path.splitext(os.path.basename(output_path))[0]
            
            title_path = os.path.join(output_dir, f"{base_name}_title.txt")
            with open(title_path, 'w', encoding='utf-8') as f:
                f.write(clip["title"])
            
            desc_path = os.path.join(output_dir, f"{base_name}_description.txt")
            with open(desc_path, 'w', encoding='utf-8') as f:
                f.write(clip["description"])
            
            logger.debug(f"Generated metadata for {base_name}")
            
        except OSError as e:
            logger.warning(f"Failed to write metadata for clip {i+1}: {e}")


__all__ = ["execute_clip"]
