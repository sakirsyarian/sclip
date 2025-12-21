"""Audio extraction utilities for SmartClip AI.

This module provides audio extraction from video files using FFmpeg.
Used by transcription services that require audio input.
"""

import os
import subprocess
import tempfile
from typing import Callable

from src.utils.ffmpeg import find_ffmpeg


class AudioExtractionError(Exception):
    """Error during audio extraction."""
    pass


def extract_audio(
    video_path: str,
    output_path: str | None = None,
    ffmpeg_path: str | None = None,
    format: str = "mp3",
    bitrate: str = "128k",
    sample_rate: int = 16000,
    mono: bool = True,
    progress_callback: Callable[[str], None] | None = None
) -> str:
    """Extract audio from video file.
    
    Args:
        video_path: Path to input video file
        output_path: Path for output audio file (auto-generated if None)
        ffmpeg_path: Custom FFmpeg path
        format: Output audio format (mp3, wav, flac)
        bitrate: Audio bitrate (e.g., "128k", "192k")
        sample_rate: Sample rate in Hz (16000 recommended for Whisper)
        mono: Convert to mono (recommended for speech)
        progress_callback: Optional callback for progress updates
        
    Returns:
        Path to extracted audio file
        
    Raises:
        AudioExtractionError: If extraction fails
    """
    def update_progress(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)
    
    # Validate input
    if not os.path.exists(video_path):
        raise AudioExtractionError(f"Video file not found: {video_path}")
    
    # Get FFmpeg path
    ffmpeg = find_ffmpeg(ffmpeg_path)
    if not ffmpeg:
        raise AudioExtractionError("FFmpeg not found")
    
    # Generate output path if not provided
    if output_path is None:
        # Create temp file with appropriate extension
        fd, output_path = tempfile.mkstemp(suffix=f".{format}")
        os.close(fd)
    
    update_progress(f"Extracting audio to {format}...")
    
    # Build FFmpeg command
    cmd = [
        ffmpeg,
        "-i", video_path,
        "-vn",  # No video
        "-acodec", _get_codec_for_format(format),
        "-ar", str(sample_rate),
        "-b:a", bitrate,
    ]
    
    if mono:
        cmd.extend(["-ac", "1"])
    
    cmd.extend([
        "-y",  # Overwrite output
        output_path
    ])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or "Unknown FFmpeg error"
            raise AudioExtractionError(f"FFmpeg failed: {error_msg}")
        
        # Verify output exists and has content
        if not os.path.exists(output_path):
            raise AudioExtractionError("Output file was not created")
        
        if os.path.getsize(output_path) == 0:
            raise AudioExtractionError("Output file is empty")
        
        update_progress("Audio extraction complete")
        return output_path
        
    except subprocess.TimeoutExpired:
        raise AudioExtractionError("Audio extraction timed out")
    except OSError as e:
        raise AudioExtractionError(f"Failed to run FFmpeg: {e}")


def _get_codec_for_format(format: str) -> str:
    """Get FFmpeg codec name for audio format."""
    codecs = {
        "mp3": "libmp3lame",
        "wav": "pcm_s16le",
        "flac": "flac",
        "aac": "aac",
        "ogg": "libvorbis",
    }
    return codecs.get(format, "libmp3lame")


def get_audio_duration(audio_path: str, ffmpeg_path: str | None = None) -> float:
    """Get duration of audio file in seconds.
    
    Args:
        audio_path: Path to audio file
        ffmpeg_path: Custom FFmpeg path
        
    Returns:
        Duration in seconds
    """
    import json
    
    # Use ffprobe to get duration
    ffprobe = find_ffmpeg(ffmpeg_path)
    if ffprobe:
        ffprobe = ffprobe.replace("ffmpeg", "ffprobe")
    
    if not ffprobe:
        raise AudioExtractionError("FFprobe not found")
    
    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        audio_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data.get("format", {}).get("duration", 0))
    except Exception:
        pass
    
    return 0.0


__all__ = [
    "extract_audio",
    "get_audio_duration",
    "AudioExtractionError",
]
