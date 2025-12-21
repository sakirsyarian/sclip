"""Main clipping workflow orchestration.

This module handles the core clip generation workflow, coordinating
all services to transform a video into viral-ready short clips.

Workflow Steps:
    1. Validate output directory
    2. Download video (if YouTube URL)
    3. Analyze video file (duration, resolution, codec)
    4. Validate video duration (>= 60 seconds)
    5. Analyze with Gemini AI (identify viral moments)
    6. Handle dry-run mode (display preview without rendering)
    7. Render clips with captions
    8. Generate metadata files (title.txt, description.txt)

Error Handling:
    - Each step validates its inputs and returns appropriate exit codes
    - Cleanup context ensures temp files are removed on any exit
    - Individual clip render failures don't stop the batch
    - Detailed error messages guide users to solutions

Dry Run Mode:
    When --dry-run is specified, the workflow:
    - Performs full AI analysis
    - Displays identified clips with timestamps
    - Shows estimated output sizes and processing time
    - Does NOT render any clips or create output files

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
    
    Orchestrates: validate → download → analyze → render
    
    Args:
        options: CLI options from user input
        
    Returns:
        Exit code indicating success or failure
    """
    # Run the async workflow
    return asyncio.run(_execute_clip_async(options))


async def _execute_clip_async(options: CLIOptions) -> int:
    """Async implementation of the clip workflow.
    
    Args:
        options: CLI options from user input
        
    Returns:
        Exit code indicating success or failure
    """
    logger = get_logger()
    cleanup_ctx = get_cleanup_context()
    
    video_path: str | None = None
    is_downloaded = False
    
    try:
        # Step 1: Validate output directory
        output_result = validate_output_dir(options.output, options.force)
        if not output_result.valid:
            logger.error(output_result.error or "Invalid output directory")
            return output_result.error_code or ExitCode.OUTPUT_ERROR
        
        # Step 2: Get video (download if URL, or use local file)
        if options.url:
            logger.info(f"Downloading video from YouTube...")
            video_path = await _download_video(options.url, cleanup_ctx)
            if video_path is None:
                return ExitCode.PROCESSING_ERROR
            is_downloaded = True
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
        
        # Step 4: Check API key
        if not options.api_key:
            logger.error("Gemini API key not configured. Set via --api-key, GEMINI_API_KEY env var, or run --setup")
            return ExitCode.API_ERROR
        
        # Step 5: Analyze with Gemini AI
        logger.info("Analyzing video with Gemini AI...")
        clips = await _analyze_with_gemini(
            video_path=video_path,
            video_duration=video_info.duration,
            options=options
        )
        
        if clips is None:
            return ExitCode.API_ERROR
        
        if not clips:
            logger.warning("No viral moments identified in the video")
            return ExitCode.SUCCESS
        
        logger.success(f"Identified {len(clips)} potential clips")
        
        # Step 6: Handle dry-run mode
        if options.dry_run:
            _display_dry_run_results(clips, video_info, options)
            return ExitCode.SUCCESS
        
        # Step 7: Render clips
        logger.info(f"Rendering {len(clips)} clips...")
        output_paths = await _render_clips(
            video_path=video_path,
            clips=clips,
            options=options
        )
        
        if not output_paths:
            logger.error("Failed to render any clips")
            return ExitCode.PROCESSING_ERROR
        
        # Step 8: Generate metadata (if not disabled)
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
    finally:
        # Cleanup is handled by the cleanup context
        pass


async def _download_video(url: str, cleanup_ctx) -> str | None:
    """Download video from YouTube URL.
    
    Args:
        url: YouTube URL to download
        cleanup_ctx: Cleanup context for registering temp files
        
    Returns:
        Path to downloaded video file, or None on failure
    """
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
        
        # Create temp directory for download
        temp_dir = tempfile.mkdtemp(prefix="sclip_")
        cleanup_ctx.register(temp_dir)
        
        downloader = YouTubeDownloader(temp_dir)
        
        # Download with progress callback
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


async def _analyze_with_gemini(
    video_path: str,
    video_duration: float,
    options: CLIOptions
) -> list[ClipData] | None:
    """Analyze video with Gemini AI to identify viral moments.
    
    Args:
        video_path: Path to video file
        video_duration: Duration of video in seconds
        options: CLI options
        
    Returns:
        List of identified clips, or None on failure
    """
    logger = get_logger()
    
    try:
        from src.services.gemini import (
            GeminiClient,
            GeminiError,
            GeminiAPIError,
            GeminiParseError,
            GeminiUploadError,
            with_retry
        )
        
        client = GeminiClient(
            api_key=options.api_key,  # type: ignore (validated above)
            model=options.model
        )
        
        def on_progress(msg: str) -> None:
            logger.debug(msg)
        
        # Use chunked analysis for long videos (> 30 minutes)
        chunk_threshold = 1800  # 30 minutes
        
        # Check if audio-only mode is enabled
        use_audio_only = getattr(options, 'audio_only', False)
        
        if use_audio_only:
            logger.info("Using audio-only mode (faster upload)...")
            
            if video_duration > chunk_threshold:
                logger.info(f"Video is {format_duration(video_duration)}, using chunked audio analysis...")
                
                async def do_analyze():
                    return await client.analyze_audio_chunked(
                        video_path=video_path,
                        video_duration=video_duration,
                        max_clips=options.max_clips,
                        min_duration=options.min_duration,
                        max_duration=options.max_duration,
                        language=options.language,
                        ffmpeg_path=options.ffmpeg_path,
                        progress_callback=on_progress
                    )
                
                response = await with_retry(do_analyze, max_retries=3)
            else:
                async def do_analyze():
                    return await client.analyze_audio(
                        video_path=video_path,
                        max_clips=options.max_clips,
                        min_duration=options.min_duration,
                        max_duration=options.max_duration,
                        language=options.language,
                        ffmpeg_path=options.ffmpeg_path,
                        progress_callback=on_progress
                    )
                
                response = await with_retry(do_analyze, max_retries=3)
        else:
            # Original video upload mode
            if video_duration > chunk_threshold:
                logger.info(f"Video is {format_duration(video_duration)}, using chunked analysis...")
                
                async def do_analyze():
                    return await client.analyze_video_chunked(
                        video_path=video_path,
                        video_duration=video_duration,
                        max_clips=options.max_clips,
                        min_duration=options.min_duration,
                        max_duration=options.max_duration,
                        language=options.language,
                        progress_callback=on_progress
                    )
                
                response = await with_retry(do_analyze, max_retries=3)
            else:
                async def do_analyze():
                    return await client.analyze_video(
                        video_path=video_path,
                        max_clips=options.max_clips,
                        min_duration=options.min_duration,
                        max_duration=options.max_duration,
                        language=options.language,
                        progress_callback=on_progress
                    )
                
                response = await with_retry(do_analyze, max_retries=3)
        
        return response["clips"]
        
    except GeminiUploadError as e:
        logger.error(f"Failed to upload video to Gemini: {e}")
        return None
    except GeminiAPIError as e:
        logger.error(f"Gemini API error: {e}")
        return None
    except GeminiParseError as e:
        logger.error(f"Failed to parse Gemini response: {e}")
        return None
    except GeminiError as e:
        logger.error(f"Gemini error: {e}")
        return None
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return None


async def _render_clips(
    video_path: str,
    clips: list[ClipData],
    options: CLIOptions
) -> list[str]:
    """Render all clips with captions.
    
    Args:
        video_path: Path to source video
        clips: List of clips to render
        options: CLI options
        
    Returns:
        List of paths to successfully rendered clips
    """
    logger = get_logger()
    
    try:
        from src.services.renderer import VideoRenderer, RenderError
        
        renderer = VideoRenderer(ffmpeg_path=options.ffmpeg_path)
        
        # Ensure output directory exists
        output_dir = options.output
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        def on_progress(current: int, total: int) -> None:
            logger.info(f"Rendering clip {current}/{total}...")
        
        # Log hardware acceleration status
        hw_info = renderer.get_hw_acceleration_info()
        if hw_info["encoder"]:
            logger.debug(f"Using hardware encoder: {hw_info['encoder']}")
        else:
            logger.debug("Using software encoding (libx264)")
        
        # Enable parallel rendering for multiple clips
        use_parallel = len(clips) > 1
        if use_parallel:
            logger.debug(f"Parallel rendering enabled with {hw_info['max_workers']} workers")
        
        # Run rendering in thread pool (it's CPU-bound)
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
        
        # Report any errors
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
    """Display dry-run results without rendering.
    
    Shows a formatted preview of identified clips including:
    - Clip details (title, timestamps, description, captions)
    - Estimated output file size for each clip
    - Total estimated output size
    - Estimated processing time
    
    Args:
        clips: List of identified clips
        video_info: Video information (VideoInfo dataclass)
        options: CLI options
    """
    logger = get_logger()
    
    logger.newline()
    logger.box("DRY RUN MODE", [
        "Analysis complete - no clips will be rendered",
        f"Source: {os.path.basename(video_info.path)}",
        f"Duration: {format_duration(video_info.duration)} | Resolution: {format_resolution(video_info.width, video_info.height)}",
    ])
    logger.newline()
    
    total_estimated_size = 0
    total_clip_duration = 0
    
    for i, clip in enumerate(clips, 1):
        duration = clip["end_time"] - clip["start_time"]
        total_clip_duration += duration
        start_fmt = format_duration(clip["start_time"])
        end_fmt = format_duration(clip["end_time"])
        
        # Estimate output size for this clip
        estimated_size = _estimate_clip_size(
            duration=duration,
            video_info=video_info,
            aspect_ratio=options.aspect_ratio,
            has_captions=not options.no_captions and bool(clip.get("captions"))
        )
        total_estimated_size += estimated_size
        
        # Build content for the clip box
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
    
    # Calculate estimated processing time
    # Base: ~1.5x realtime for rendering, plus overhead for captions
    processing_multiplier = 1.5
    if not options.no_captions:
        processing_multiplier += 0.3  # Caption burn-in adds ~30% time
    estimated_time = total_clip_duration * processing_multiplier
    
    # Summary box
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
    """Estimate the output file size for a clip.
    
    Uses the source video bitrate and target resolution to estimate
    the output file size. This is used in dry-run mode to give users
    an idea of disk space requirements.
    
    Estimation factors:
    - Source video bitrate (or estimated from resolution)
    - Target aspect ratio (affects output resolution)
    - Caption burn-in overhead (~10% for re-encoding)
    - H.264 encoding efficiency
    
    Args:
        duration: Clip duration in seconds
        video_info: Source video information (VideoInfo dataclass)
        aspect_ratio: Target aspect ratio (9:16, 1:1, 16:9)
        has_captions: Whether captions will be burned in
        
    Returns:
        Estimated file size in bytes
    
    Note:
        This is a rough estimate. Actual size depends on video content
        complexity, motion, and encoding settings.
    """
    # Base bitrate estimation
    # If source bitrate is available, use it as reference
    # Otherwise, estimate based on resolution (common H.264 bitrates)
    if video_info.bitrate > 0:
        base_bitrate = video_info.bitrate
    else:
        # Estimate bitrate based on resolution (bits per second)
        # These are typical bitrates for H.264 at reasonable quality
        pixels = video_info.width * video_info.height
        if pixels >= 1920 * 1080:
            base_bitrate = 8_000_000  # 8 Mbps for 1080p
        elif pixels >= 1280 * 720:
            base_bitrate = 5_000_000  # 5 Mbps for 720p
        else:
            base_bitrate = 2_500_000  # 2.5 Mbps for lower res
    
    # Adjust for target aspect ratio
    # Vertical (9:16) typically has lower resolution than source
    # Square (1:1) is medium
    # Horizontal (16:9) keeps most of the source
    aspect_multiplier = {
        "9:16": 0.6,   # Vertical crops significantly
        "1:1": 0.75,   # Square crops moderately
        "16:9": 0.9,   # Horizontal keeps most
    }.get(aspect_ratio, 0.75)
    
    adjusted_bitrate = base_bitrate * aspect_multiplier
    
    # Add overhead for caption burn-in (re-encoding adds ~10%)
    if has_captions:
        adjusted_bitrate *= 1.1
    
    # Calculate size: bitrate (bits/sec) * duration (sec) / 8 (bits to bytes)
    estimated_bytes = int((adjusted_bitrate * duration) / 8)
    
    return estimated_bytes


def _format_file_size(size_bytes: int) -> str:
    """Format file size in bytes to human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string like "12.5 MB" or "1.2 GB"
    """
    if size_bytes < 0:
        return "unknown"
    
    if size_bytes >= 1_073_741_824:  # 1 GB
        return f"{size_bytes / 1_073_741_824:.1f} GB"
    elif size_bytes >= 1_048_576:  # 1 MB
        return f"{size_bytes / 1_048_576:.1f} MB"
    elif size_bytes >= 1024:  # 1 KB
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes} bytes"


def _generate_metadata(
    clips: list[ClipData],
    output_paths: list[str],
    output_dir: str
) -> None:
    """Generate metadata files for rendered clips.
    
    Creates {clip_name}_title.txt and {clip_name}_description.txt
    for each successfully rendered clip.
    
    Args:
        clips: List of clip data
        output_paths: List of rendered clip paths
        output_dir: Output directory
    """
    logger = get_logger()
    
    # Match clips to output paths by index
    for i, (clip, output_path) in enumerate(zip(clips, output_paths)):
        try:
            # Get base name without extension
            base_name = os.path.splitext(os.path.basename(output_path))[0]
            
            # Write title file
            title_path = os.path.join(output_dir, f"{base_name}_title.txt")
            with open(title_path, 'w', encoding='utf-8') as f:
                f.write(clip["title"])
            
            # Write description file
            desc_path = os.path.join(output_dir, f"{base_name}_description.txt")
            with open(desc_path, 'w', encoding='utf-8') as f:
                f.write(clip["description"])
            
            logger.debug(f"Generated metadata for {base_name}")
            
        except OSError as e:
            logger.warning(f"Failed to write metadata for clip {i+1}: {e}")


__all__ = ["execute_clip"]
