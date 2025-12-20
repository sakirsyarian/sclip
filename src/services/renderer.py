"""Video rendering service for SmartClip AI.

This module provides the VideoRenderer class for creating video clips
with captions from source videos. It handles all FFmpeg interactions
for video processing.

Key Features:
    - Video trimming based on timestamps
    - Aspect ratio cropping (9:16, 1:1, 16:9) with center alignment
    - ASS subtitle burn-in for captions
    - H.264 + AAC encoding for maximum compatibility
    - Progress reporting during rendering
    - Batch rendering with error recovery
    - Parallel rendering support for improved performance
    - Hardware acceleration detection (NVENC, VideoToolbox, VAAPI)

FFmpeg Pipeline:
    The rendering process uses FFmpeg with the following steps:
    1. Seek to start time (-ss before -i for fast seeking)
    2. Apply crop filter for aspect ratio
    3. Apply subtitle filter for captions (if enabled)
    4. Encode with libx264 (video) and aac (audio)
    5. Add faststart flag for web playback

Output Format:
    - Container: MP4
    - Video: H.264 (libx264), CRF 23, medium preset
    - Audio: AAC, 128kbps
    - Faststart enabled for streaming

Performance Optimizations:
    - Parallel clip rendering using ThreadPoolExecutor
    - Hardware acceleration when available
    - Optimized FFmpeg preset selection
    - Efficient seeking with -ss before -i

Usage:
    from src.services.renderer import VideoRenderer, calculate_crop_params
    
    renderer = VideoRenderer(ffmpeg_path="/usr/local/bin/ffmpeg")
    
    # Render a single clip
    output_path = renderer.render_clip(
        input_path="source.mp4",
        output_path="clip_01.mp4",
        clip_data=clip,
        aspect_ratio="9:16",
        caption_style="default"
    )
    
    # Render all clips from analysis (parallel by default)
    output_paths = renderer.render_all_clips(
        input_path="source.mp4",
        output_dir="./output",
        clips=clips,
        options=cli_options,
        parallel=True  # Enable parallel rendering
    )
"""

import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from src.types import AspectRatio, CaptionStyle, ClipData, CLIOptions, VideoInfo
from src.utils.ffmpeg import find_ffmpeg, run_ffmpeg, FFmpegResult
from src.utils.video import analyze_video
from src.utils.captions import generate_ass_subtitle, CAPTION_STYLES


class RenderError(Exception):
    """Exception raised when video rendering fails.
    
    This can occur due to:
    - FFmpeg execution errors
    - Invalid input files
    - Insufficient disk space
    - Font rendering issues (usually non-fatal)
    """
    pass


# Fallback fonts for different platforms when specified font is not available
# Used when the caption style's font is missing from the system
FALLBACK_FONTS = {
    "win32": ["Arial", "Segoe UI", "Tahoma", "Verdana"],
    "darwin": ["Helvetica", "Arial", "SF Pro", "Lucida Grande"],
    "linux": ["DejaVu Sans", "Liberation Sans", "FreeSans", "Arial"],
}


def _get_fallback_font() -> str:
    """Get a fallback font for the current platform.
    
    Returns:
        A font name that is likely to be available on the current platform.
    """
    platform = sys.platform
    if platform.startswith("linux"):
        platform = "linux"
    
    fonts = FALLBACK_FONTS.get(platform, FALLBACK_FONTS["linux"])
    return fonts[0] if fonts else "sans-serif"


def _detect_hw_acceleration(ffmpeg_path: str | None = None) -> str | None:
    """Detect available hardware acceleration for encoding.
    
    Checks for NVENC (NVIDIA), VideoToolbox (macOS), and VAAPI (Linux).
    Also verifies that the encoder actually works by doing a test encode.
    
    Args:
        ffmpeg_path: Path to FFmpeg executable
        
    Returns:
        Hardware encoder name (e.g., 'h264_nvenc') or None if not available
    """
    from src.utils.ffmpeg import run_ffmpeg
    
    # Check available encoders
    result = run_ffmpeg(["-encoders"], ffmpeg_path=ffmpeg_path, timeout=10)
    if not result.success:
        return None
    
    encoders_output = result.stdout.lower()
    
    # Priority order: NVENC > AMF > VideoToolbox > VAAPI > QSV
    hw_encoders = [
        ("h264_nvenc", "nvenc"),           # NVIDIA
        ("h264_amf", "amf"),               # AMD (Radeon iGPU/dGPU)
        ("h264_videotoolbox", "videotoolbox"),  # macOS
        ("h264_vaapi", "vaapi"),           # Linux VA-API
        ("h264_qsv", "qsv"),               # Intel Quick Sync
    ]
    
    for encoder, keyword in hw_encoders:
        if encoder in encoders_output:
            # Verify the encoder actually works by doing a quick test
            # This catches cases where NVENC is listed but CUDA drivers are missing
            if _test_hw_encoder(encoder, ffmpeg_path):
                return encoder
    
    return None


def _test_hw_encoder(encoder: str, ffmpeg_path: str | None = None) -> bool:
    """Test if a hardware encoder actually works.
    
    Creates a tiny test encode to verify the encoder is functional.
    This catches cases like NVENC being listed but nvcuda.dll missing.
    
    Args:
        encoder: Encoder name (e.g., 'h264_nvenc')
        ffmpeg_path: Path to FFmpeg executable
        
    Returns:
        True if encoder works, False otherwise
    """
    from src.utils.ffmpeg import run_ffmpeg
    import tempfile
    
    try:
        # Create a minimal test: generate 1 frame of black video and encode it
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            tmp_path = tmp.name
        
        # Generate 1 frame of 64x64 black video and encode with the HW encoder
        test_args = [
            "-f", "lavfi",
            "-i", "color=black:s=64x64:d=0.1",
            "-c:v", encoder,
            "-frames:v", "1",
            "-y",
            tmp_path
        ]
        
        result = run_ffmpeg(test_args, ffmpeg_path=ffmpeg_path, timeout=10)
        
        # Clean up test file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        
        # Check if encoding succeeded
        if result.success:
            return True
        
        # Check for common HW encoder failures
        stderr_lower = result.stderr.lower() if result.stderr else ""
        hw_failure_indicators = [
            "cannot load",
            "nvcuda",
            "cuda",
            "error while opening encoder",
            "no capable devices found",
            "device not found",
            "initialization failed",
        ]
        
        for indicator in hw_failure_indicators:
            if indicator in stderr_lower:
                return False
        
        return False
        
    except Exception:
        return False


# Cache for hardware acceleration detection
# Use a version key to invalidate cache when detection logic changes
_hw_accel_cache: dict[str, str | None] = {}
_HW_CACHE_VERSION = "v2"  # Increment this when detection logic changes


def calculate_crop_params(
    source_width: int,
    source_height: int,
    target_ratio: AspectRatio
) -> tuple[int, int, int, int]:
    """Calculate crop parameters for center crop to target aspect ratio.
    
    Calculates the x, y offset and width, height for cropping the source
    video to the target aspect ratio while maintaining center alignment.
    The crop is always centered on the source video.
    
    For example, cropping a 1920x1080 (16:9) video to 9:16:
    - Target aspect is 9/16 = 0.5625
    - Source aspect is 16/9 = 1.778
    - Source is wider, so we crop the width
    - Result: 607x1080 centered crop
    
    Args:
        source_width: Width of source video in pixels
        source_height: Height of source video in pixels
        target_ratio: Target aspect ratio ("9:16", "1:1", or "16:9")
        
    Returns:
        Tuple of (crop_x, crop_y, crop_width, crop_height)
        - crop_x: X offset from left edge
        - crop_y: Y offset from top edge
        - crop_width: Width of cropped region
        - crop_height: Height of cropped region
    
    Note:
        Dimensions are adjusted to be even numbers for video encoding
        compatibility (required by most codecs).
    """
    # Parse target ratio string to numeric values
    ratio_map = {
        "9:16": (9, 16),   # Vertical/portrait
        "1:1": (1, 1),     # Square
        "16:9": (16, 9),   # Horizontal/landscape
    }
    
    target_w, target_h = ratio_map.get(target_ratio, (9, 16))
    target_aspect = target_w / target_h
    source_aspect = source_width / source_height
    
    if source_aspect > target_aspect:
        # Source is wider than target - crop width (letterbox scenario)
        crop_height = source_height
        crop_width = int(source_height * target_aspect)
        # Ensure even dimensions for video encoding compatibility
        crop_width = crop_width - (crop_width % 2)
        # Center horizontally
        crop_x = (source_width - crop_width) // 2
        crop_y = 0
    else:
        # Source is taller than target - crop height (pillarbox scenario)
        crop_width = source_width
        crop_height = int(source_width / target_aspect)
        # Ensure even dimensions for video encoding compatibility
        crop_height = crop_height - (crop_height % 2)
        # Center vertically
        crop_x = 0
        crop_y = (source_height - crop_height) // 2
    
    return (crop_x, crop_y, crop_width, crop_height)


class VideoRenderer:
    """Video rendering service for creating clips with captions.
    
    Handles video trimming, cropping, and caption burn-in using FFmpeg.
    Provides both single-clip and batch rendering capabilities.
    Supports parallel rendering for improved performance.
    
    Attributes:
        _ffmpeg_path: Path to FFmpeg executable
        _last_render_errors: Errors from last batch render (for reporting)
        _hw_encoder: Detected hardware encoder (or None for software)
        _max_workers: Maximum parallel render workers
    
    Example:
        renderer = VideoRenderer()
        
        # Single clip
        path = renderer.render_clip(
            input_path="video.mp4",
            output_path="clip.mp4",
            clip_data=clip,
            aspect_ratio="9:16",
            caption_style="default"
        )
        
        # Batch rendering (parallel by default)
        paths = renderer.render_all_clips(
            input_path="video.mp4",
            output_dir="./output",
            clips=clips,
            options=options,
            parallel=True
        )
        
        # Check for errors
        errors = renderer.get_last_render_errors()
    """
    
    # Default number of parallel workers (based on CPU cores)
    DEFAULT_MAX_WORKERS = min(4, (os.cpu_count() or 2))
    
    def __init__(
        self,
        ffmpeg_path: str | None = None,
        use_hw_accel: bool = True,
        max_workers: int | None = None
    ):
        """Initialize the video renderer.
        
        Args:
            ffmpeg_path: Optional custom path to FFmpeg executable
            use_hw_accel: Whether to attempt hardware acceleration
            max_workers: Maximum parallel render workers (default: min(4, CPU cores))
        """
        self._ffmpeg_path = ffmpeg_path or find_ffmpeg()
        if self._ffmpeg_path is None:
            raise RenderError(
                "FFmpeg not found. Please install FFmpeg or specify path with --ffmpeg-path."
            )
        
        # Detect hardware acceleration
        self._hw_encoder: str | None = None
        if use_hw_accel:
            cache_key = f"{_HW_CACHE_VERSION}:{self._ffmpeg_path or 'default'}"
            if cache_key not in _hw_accel_cache:
                _hw_accel_cache[cache_key] = _detect_hw_acceleration(self._ffmpeg_path)
            self._hw_encoder = _hw_accel_cache[cache_key]
        
        self._max_workers = max_workers or self.DEFAULT_MAX_WORKERS
        self._last_render_errors: list[tuple[int, str, str]] = []
    
    def render_clip(
        self,
        input_path: str,
        output_path: str,
        clip_data: ClipData,
        aspect_ratio: AspectRatio,
        caption_style: CaptionStyle,
        no_captions: bool = False,
        video_info: VideoInfo | None = None,
        progress_callback: Callable[[int], None] | None = None,
        fast_mode: bool = False
    ) -> str:
        """Render a single clip with optional captions.
        
        Trims the video to the specified time range, crops to the target
        aspect ratio, and optionally burns in captions.
        
        Args:
            input_path: Path to source video file
            output_path: Path for output clip file
            clip_data: Clip data with timestamps, title, and captions
            aspect_ratio: Target aspect ratio for the clip
            caption_style: Style preset for captions
            no_captions: If True, skip caption burn-in
            video_info: Optional pre-analyzed video info (avoids re-analysis)
            progress_callback: Optional callback for progress updates (0-100)
            fast_mode: If True, use faster encoding preset (lower quality)
            
        Returns:
            Path to the rendered clip file
            
        Raises:
            RenderError: If rendering fails
            FileNotFoundError: If input file not found
        """
        # Validate input file exists
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video not found: {input_path}")
        
        # Get video info if not provided
        if video_info is None:
            video_info = analyze_video(input_path)
        
        # Calculate timing
        start_time = clip_data["start_time"]
        end_time = clip_data["end_time"]
        duration = end_time - start_time
        
        # Calculate crop parameters
        crop_x, crop_y, crop_width, crop_height = calculate_crop_params(
            video_info.width,
            video_info.height,
            aspect_ratio
        )
        
        # Build filter chain
        filters = []
        
        # Crop filter
        filters.append(f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y}")
        
        # Handle captions
        subtitle_file = None
        if not no_captions and clip_data.get("captions"):
            # Generate ASS subtitle file
            ass_content = generate_ass_subtitle(
                captions=clip_data["captions"],
                style=caption_style,
                video_width=crop_width,
                video_height=crop_height,
                clip_start_time=start_time
            )
            
            # Write to temp file
            subtitle_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.ass',
                delete=False,
                encoding='utf-8'
            )
            subtitle_file.write(ass_content)
            subtitle_file.close()
            
            # Add subtitle filter - escape path for FFmpeg
            # On Windows, FFmpeg filter syntax requires special escaping:
            # - Backslashes must be escaped as \\
            # - Colons must be escaped as \:
            # - The whole path should use forward slashes
            sub_path = subtitle_file.name
            if sys.platform == "win32":
                # Convert to forward slashes and escape colons
                sub_path = sub_path.replace('\\', '/')
                # Escape the colon after drive letter (e.g., C: -> C\:)
                if len(sub_path) >= 2 and sub_path[1] == ':':
                    sub_path = sub_path[0] + '\\:' + sub_path[2:]
            filters.append(f"subtitles='{sub_path}'")
        
        # Build FFmpeg command
        filter_complex = ",".join(filters)
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Select encoder and preset based on hardware acceleration and mode
        if self._hw_encoder:
            # Use hardware encoder
            video_codec = self._hw_encoder
            # Hardware encoders use different quality settings
            quality_args = ["-b:v", "5M"]  # Target bitrate for HW encoders
            preset_args = []
        else:
            # Software encoding
            video_codec = "libx264"
            preset = "fast" if fast_mode else "medium"
            quality_args = ["-crf", "23"]
            preset_args = ["-preset", preset]
        
        args = [
            "-y",  # Overwrite output
            "-ss", str(start_time),  # Seek to start (before input for faster seeking)
            "-i", input_path,
            "-t", str(duration),  # Duration
            "-vf", filter_complex,
            "-c:v", video_codec,  # Video codec
            *preset_args,  # Encoding preset
            *quality_args,  # Quality settings
            "-c:a", "aac",  # AAC audio codec
            "-b:a", "128k",  # Audio bitrate
            "-movflags", "+faststart",  # Enable fast start for web playback
            output_path
        ]
        
        try:
            # Run FFmpeg with timeout based on clip duration
            # Allow 10x realtime + 60 seconds buffer for encoding
            timeout = max(300, int(duration * 10) + 60)
            
            # Run FFmpeg
            result = run_ffmpeg(
                args,
                ffmpeg_path=self._ffmpeg_path,
                timeout=timeout,
                progress_callback=lambda line: self._parse_progress(
                    line, duration, progress_callback
                ) if progress_callback else None
            )
            
            if not result.success:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                
                # Check for font-related warnings (these are usually non-fatal)
                # FFmpeg/libass will use fallback fonts automatically
                font_warnings = [
                    "fontselect:",
                    "Glyph",
                    "font provider",
                    "Fontconfig",
                ]
                
                is_font_warning = any(warn in error_msg for warn in font_warnings)
                
                # If it's just a font warning but output was created with valid size, consider it success
                if is_font_warning and os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    if file_size > 1000:  # At least 1KB - valid video file
                        return output_path
                
                # Clean up empty/invalid output file
                if os.path.exists(output_path):
                    try:
                        os.unlink(output_path)
                    except OSError:
                        pass
                
                raise RenderError(f"FFmpeg failed: {error_msg}")
            
            # Verify output was created AND has valid size
            if not os.path.exists(output_path):
                raise RenderError(f"Output file was not created: {output_path}")
            
            file_size = os.path.getsize(output_path)
            if file_size < 1000:  # Less than 1KB is definitely invalid
                # Clean up invalid file
                try:
                    os.unlink(output_path)
                except OSError:
                    pass
                raise RenderError(f"Output file is empty or corrupted (size: {file_size} bytes). FFmpeg stderr: {result.stderr[:500] if result.stderr else 'No error output'}")
            
            return output_path
            
        finally:
            # Cleanup temp subtitle file
            if subtitle_file and os.path.exists(subtitle_file.name):
                try:
                    os.unlink(subtitle_file.name)
                except OSError:
                    pass
    
    def _parse_progress(
        self,
        line: str,
        total_duration: float,
        callback: Callable[[int], None]
    ) -> None:
        """Parse FFmpeg progress output and call callback with percentage.
        
        Args:
            line: Line of FFmpeg stderr output
            total_duration: Total duration of the clip being rendered
            callback: Callback function to call with progress percentage
        """
        # FFmpeg outputs progress like: "time=00:00:05.23"
        if "time=" in line:
            try:
                time_str = line.split("time=")[1].split()[0]
                # Parse time format HH:MM:SS.cc
                parts = time_str.split(":")
                if len(parts) == 3:
                    hours = float(parts[0])
                    minutes = float(parts[1])
                    seconds = float(parts[2])
                    current_time = hours * 3600 + minutes * 60 + seconds
                    
                    if total_duration > 0:
                        progress = min(100, int((current_time / total_duration) * 100))
                        callback(progress)
            except (IndexError, ValueError):
                pass
    
    def render_all_clips(
        self,
        input_path: str,
        output_dir: str,
        clips: list[ClipData],
        options: CLIOptions,
        progress_callback: Callable[[int, int], None] | None = None,
        parallel: bool = True
    ) -> list[str]:
        """Render all clips with progress reporting.
        
        Processes clips either in parallel (default) or sequentially.
        Parallel rendering significantly improves performance on multi-core systems.
        
        Args:
            input_path: Path to source video file
            output_dir: Directory for output clips
            clips: List of clip data from AI analysis
            options: CLI options with rendering settings
            progress_callback: Optional callback for progress updates (current_clip, total_clips)
            parallel: If True, render clips in parallel (default: True)
            
        Returns:
            List of paths to successfully rendered clips
        """
        if not clips:
            return []
        
        # Ensure output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Get video info once for all clips
        video_info = analyze_video(input_path)
        
        total_clips = len(clips)
        
        if parallel and total_clips > 1:
            return self._render_clips_parallel(
                input_path=input_path,
                output_dir=output_dir,
                clips=clips,
                options=options,
                video_info=video_info,
                progress_callback=progress_callback
            )
        else:
            return self._render_clips_sequential(
                input_path=input_path,
                output_dir=output_dir,
                clips=clips,
                options=options,
                video_info=video_info,
                progress_callback=progress_callback
            )
    
    def _render_clips_sequential(
        self,
        input_path: str,
        output_dir: str,
        clips: list[ClipData],
        options: CLIOptions,
        video_info: VideoInfo,
        progress_callback: Callable[[int, int], None] | None = None
    ) -> list[str]:
        """Render clips sequentially (original behavior).
        
        Args:
            input_path: Path to source video file
            output_dir: Directory for output clips
            clips: List of clip data from AI analysis
            options: CLI options with rendering settings
            video_info: Pre-analyzed video info
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of paths to successfully rendered clips
        """
        successful_outputs: list[str] = []
        errors: list[tuple[int, str, str]] = []
        total_clips = len(clips)
        
        for idx, clip_data in enumerate(clips, start=1):
            # Report progress
            if progress_callback:
                progress_callback(idx, total_clips)
            
            # Generate output filename
            output_filename = self._generate_output_filename(idx, clip_data, output_dir)
            
            try:
                # Render the clip
                output_path = self.render_clip(
                    input_path=input_path,
                    output_path=output_filename,
                    clip_data=clip_data,
                    aspect_ratio=options.aspect_ratio,
                    caption_style=options.caption_style,
                    no_captions=options.no_captions,
                    video_info=video_info,
                    progress_callback=None
                )
                
                successful_outputs.append(output_path)
                
            except (RenderError, FileNotFoundError, OSError) as e:
                clip_title = clip_data.get("title", f"Clip {idx}")
                errors.append((idx, clip_title, str(e)))
                continue
        
        self._last_render_errors = errors
        return successful_outputs
    
    def _render_clips_parallel(
        self,
        input_path: str,
        output_dir: str,
        clips: list[ClipData],
        options: CLIOptions,
        video_info: VideoInfo,
        progress_callback: Callable[[int, int], None] | None = None
    ) -> list[str]:
        """Render clips in parallel using ThreadPoolExecutor.
        
        Args:
            input_path: Path to source video file
            output_dir: Directory for output clips
            clips: List of clip data from AI analysis
            options: CLI options with rendering settings
            video_info: Pre-analyzed video info
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of paths to successfully rendered clips (in original order)
        """
        total_clips = len(clips)
        results: dict[int, str | None] = {}  # idx -> output_path or None
        errors: list[tuple[int, str, str]] = []
        completed_count = 0
        
        def render_single(idx: int, clip_data: ClipData) -> tuple[int, str | None, str | None]:
            """Render a single clip and return (idx, output_path, error)."""
            output_filename = self._generate_output_filename(idx, clip_data, output_dir)
            
            try:
                output_path = self.render_clip(
                    input_path=input_path,
                    output_path=output_filename,
                    clip_data=clip_data,
                    aspect_ratio=options.aspect_ratio,
                    caption_style=options.caption_style,
                    no_captions=options.no_captions,
                    video_info=video_info,
                    progress_callback=None,
                    fast_mode=False  # Use quality mode for final output
                )
                return (idx, output_path, None)
            except (RenderError, FileNotFoundError, OSError) as e:
                return (idx, None, str(e))
        
        # Use ThreadPoolExecutor for parallel rendering
        # FFmpeg is CPU-bound but releases GIL during subprocess execution
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            # Submit all render tasks
            futures = {
                executor.submit(render_single, idx, clip_data): (idx, clip_data)
                for idx, clip_data in enumerate(clips, start=1)
            }
            
            # Process completed tasks
            for future in as_completed(futures):
                idx, clip_data = futures[future]
                completed_count += 1
                
                # Report progress
                if progress_callback:
                    progress_callback(completed_count, total_clips)
                
                try:
                    result_idx, output_path, error = future.result()
                    if output_path:
                        results[result_idx] = output_path
                    elif error:
                        clip_title = clip_data.get("title", f"Clip {result_idx}")
                        errors.append((result_idx, clip_title, error))
                except Exception as e:
                    clip_title = clip_data.get("title", f"Clip {idx}")
                    errors.append((idx, clip_title, str(e)))
        
        self._last_render_errors = errors
        
        # Return results in original order
        successful_outputs = [
            results[idx] for idx in sorted(results.keys())
            if results[idx] is not None
        ]
        
        return successful_outputs
    
    def _generate_output_filename(
        self,
        index: int,
        clip_data: ClipData,
        output_dir: str
    ) -> str:
        """Generate a safe output filename for a clip.
        
        Creates a filename based on clip index and sanitized title.
        
        Args:
            index: Clip index (1-based)
            clip_data: Clip data containing title
            output_dir: Output directory path
            
        Returns:
            Full path for the output file
        """
        # Get title and sanitize it for filename
        title = clip_data.get("title", f"clip_{index}")
        safe_title = self._sanitize_filename(title)
        
        # Limit title length to avoid filesystem issues
        max_title_len = 50
        if len(safe_title) > max_title_len:
            safe_title = safe_title[:max_title_len].rstrip('_')
        
        # Format: clip_01_title.mp4
        filename = f"clip_{index:02d}_{safe_title}.mp4"
        
        return os.path.join(output_dir, filename)
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as a filename.
        
        Removes or replaces characters that are invalid in filenames.
        
        Args:
            name: Original string
            
        Returns:
            Sanitized string safe for use as filename
        """
        # Characters not allowed in filenames on various platforms
        invalid_chars = '<>:"/\\|?*'
        
        result = name
        for char in invalid_chars:
            result = result.replace(char, '')
        
        # Replace spaces and other whitespace with underscores
        result = '_'.join(result.split())
        
        # Remove any leading/trailing underscores or dots
        result = result.strip('_.')
        
        # If empty after sanitization, use default
        if not result:
            result = "clip"
        
        return result
    
    def get_last_render_errors(self) -> list[tuple[int, str, str]]:
        """Get errors from the last render_all_clips call.
        
        Returns:
            List of tuples (clip_index, clip_title, error_message) for failed clips
        """
        return getattr(self, '_last_render_errors', [])
    
    def get_hw_acceleration_info(self) -> dict[str, str | None]:
        """Get information about hardware acceleration status.
        
        Returns:
            Dictionary with hw_encoder name and status
        """
        return {
            "encoder": self._hw_encoder,
            "status": "enabled" if self._hw_encoder else "disabled (using software encoding)",
            "max_workers": self._max_workers
        }
