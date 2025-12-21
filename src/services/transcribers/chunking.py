"""Audio chunking utilities for large file transcription.

This module provides utilities to split large audio files into smaller chunks
for transcription services with file size limits (Groq, OpenAI: 25MB).

Strategy:
- Split audio by duration (not size) for predictable chunks
- Use overlap to avoid cutting words at boundaries
- Merge results with deduplication of overlapping segments
"""

import os
import subprocess
import tempfile
from dataclasses import dataclass

from .base import WordTimestamp, TranscriptionResult


@dataclass
class AudioChunk:
    """Represents a chunk of audio."""
    path: str
    start_time: float  # Start time in original audio (seconds)
    end_time: float    # End time in original audio (seconds)
    duration: float    # Chunk duration (seconds)


# Default chunk settings
DEFAULT_CHUNK_DURATION = 600  # 10 minutes per chunk
DEFAULT_OVERLAP = 5  # 5 seconds overlap between chunks
MAX_FILE_SIZE = 24 * 1024 * 1024  # 24MB (safe margin under 25MB limit)


def needs_chunking(audio_path: str, max_size: int = MAX_FILE_SIZE) -> bool:
    """Check if audio file needs to be chunked.
    
    Args:
        audio_path: Path to audio file
        max_size: Maximum file size in bytes
        
    Returns:
        True if file exceeds max_size
    """
    return os.path.getsize(audio_path) > max_size


def get_audio_duration(audio_path: str, ffprobe_path: str | None = None) -> float:
    """Get duration of audio file in seconds."""
    import json
    
    ffprobe = ffprobe_path or "ffprobe"
    
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


def split_audio(
    audio_path: str,
    chunk_duration: float = DEFAULT_CHUNK_DURATION,
    overlap: float = DEFAULT_OVERLAP,
    ffmpeg_path: str | None = None
) -> list[AudioChunk]:
    """Split audio file into chunks with overlap.
    
    Args:
        audio_path: Path to audio file
        chunk_duration: Duration of each chunk in seconds
        overlap: Overlap between chunks in seconds
        ffmpeg_path: Custom FFmpeg path
        
    Returns:
        List of AudioChunk objects with paths to chunk files
    """
    ffmpeg = ffmpeg_path or "ffmpeg"
    
    # Get total duration
    total_duration = get_audio_duration(audio_path)
    if total_duration <= 0:
        raise ValueError(f"Could not determine audio duration: {audio_path}")
    
    chunks: list[AudioChunk] = []
    current_start = 0.0
    chunk_index = 0
    
    # Get file extension
    _, ext = os.path.splitext(audio_path)
    
    while current_start < total_duration:
        # Calculate chunk end time
        chunk_end = min(current_start + chunk_duration, total_duration)
        actual_duration = chunk_end - current_start
        
        # Create temp file for chunk
        fd, chunk_path = tempfile.mkstemp(suffix=ext)
        os.close(fd)
        
        # Extract chunk with FFmpeg
        cmd = [
            ffmpeg,
            "-y",  # Overwrite
            "-i", audio_path,
            "-ss", str(current_start),
            "-t", str(actual_duration),
            "-acodec", "copy",  # Copy codec, no re-encoding
            chunk_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # Cleanup created chunk
            if os.path.exists(chunk_path):
                os.remove(chunk_path)
            raise RuntimeError(f"FFmpeg failed to create chunk: {result.stderr}")
        
        chunks.append(AudioChunk(
            path=chunk_path,
            start_time=current_start,
            end_time=chunk_end,
            duration=actual_duration
        ))
        
        chunk_index += 1
        
        # Move to next chunk with overlap
        # If this is the last chunk, we're done
        if chunk_end >= total_duration:
            break
        
        current_start = chunk_end - overlap
    
    return chunks


def merge_transcription_results(
    results: list[tuple[AudioChunk, TranscriptionResult]],
    overlap: float = DEFAULT_OVERLAP
) -> TranscriptionResult:
    """Merge multiple transcription results into one.
    
    Handles overlap by deduplicating words that appear in both chunks.
    
    Args:
        results: List of (chunk, result) tuples in order
        overlap: Overlap duration used when splitting
        
    Returns:
        Merged TranscriptionResult
    """
    if not results:
        return TranscriptionResult(text="", words=[], language="", duration=0.0)
    
    if len(results) == 1:
        chunk, result = results[0]
        # Adjust timestamps to original audio time
        adjusted_words = [
            WordTimestamp(
                word=w.word,
                start=w.start + chunk.start_time,
                end=w.end + chunk.start_time
            )
            for w in result.words
        ]
        return TranscriptionResult(
            text=result.text,
            words=adjusted_words,
            language=result.language,
            duration=chunk.end_time
        )
    
    # Merge multiple chunks
    all_words: list[WordTimestamp] = []
    all_text_parts: list[str] = []
    language = ""
    
    for i, (chunk, result) in enumerate(results):
        if not language and result.language:
            language = result.language
        
        # Adjust word timestamps to original audio time
        chunk_words = [
            WordTimestamp(
                word=w.word,
                start=w.start + chunk.start_time,
                end=w.end + chunk.start_time
            )
            for w in result.words
        ]
        
        if i == 0:
            # First chunk: add all words
            all_words.extend(chunk_words)
            all_text_parts.append(result.text)
        else:
            # Subsequent chunks: skip words in overlap region
            prev_chunk = results[i - 1][0]
            overlap_start = prev_chunk.end_time - overlap
            
            # Find words that start after the overlap region
            new_words = [w for w in chunk_words if w.start >= overlap_start + (overlap / 2)]
            
            if new_words:
                all_words.extend(new_words)
                
                # For text, try to find where new content starts
                # Simple approach: just append with space
                all_text_parts.append(result.text)
    
    # Calculate total duration from last word or last chunk
    total_duration = 0.0
    if all_words:
        total_duration = all_words[-1].end
    elif results:
        total_duration = results[-1][0].end_time
    
    return TranscriptionResult(
        text=" ".join(all_text_parts),
        words=all_words,
        language=language,
        duration=total_duration
    )


def cleanup_chunks(chunks: list[AudioChunk]) -> None:
    """Remove temporary chunk files."""
    for chunk in chunks:
        if os.path.exists(chunk.path):
            try:
                os.remove(chunk.path)
            except OSError:
                pass


__all__ = [
    "AudioChunk",
    "needs_chunking",
    "get_audio_duration",
    "split_audio",
    "merge_transcription_results",
    "cleanup_chunks",
    "MAX_FILE_SIZE",
    "DEFAULT_CHUNK_DURATION",
    "DEFAULT_OVERLAP",
]
