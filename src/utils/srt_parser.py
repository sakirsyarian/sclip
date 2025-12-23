"""SRT/VTT subtitle parser for SmartClip AI.

This module parses external subtitle files (SRT, VTT) and converts them
to a segment-based format for accurate caption display.

Benefits of using external subtitles:
    - Faster processing (skip 2-5 min transcription)
    - No API cost for transcription
    - More accurate (professional subtitles)
    - Works offline
    - 100% accurate timing (no estimation)

Supported formats:
    - SRT (SubRip): Most common format
    - VTT (WebVTT): Web standard format

Design Decision:
    External subtitles use SEGMENT-BASED captions, not word-by-word.
    This is because SRT/VTT only have per-segment timestamps.
    Trying to estimate word timing would be inaccurate and cause
    caption sync issues, especially with karaoke style.

Usage:
    from src.utils.srt_parser import parse_subtitle_file
    
    result = parse_subtitle_file("subtitle.srt")
    # result.text, result.segments, result.duration
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class WordTiming:
    """Word with timing information (for API transcription results)."""
    word: str
    start: float
    end: float


@dataclass
class SubtitleSegment:
    """A single subtitle segment with accurate timing."""
    index: int
    start: float
    end: float
    text: str


@dataclass
class SubtitleResult:
    """Result from parsing subtitle file.
    
    Uses segment-based approach for accurate timing.
    The 'words' field contains segments (not individual words) for compatibility
    with the analyzer interface, but each "word" is actually a full segment.
    """
    text: str
    segments: list[SubtitleSegment]  # Original segments with accurate timing
    words: list[WordTiming]  # Segments as "words" for analyzer compatibility
    duration: float
    language: str | None = None
    is_segment_based: bool = True  # Flag to indicate segment-based captions


class SubtitleParseError(Exception):
    """Error parsing subtitle file."""
    pass


def parse_srt_timestamp(timestamp: str) -> float:
    """Parse SRT timestamp to seconds.
    
    SRT format: HH:MM:SS,mmm (comma for milliseconds)
    
    Args:
        timestamp: SRT timestamp string (e.g., "00:01:23,456")
        
    Returns:
        Time in seconds as float
        
    Raises:
        ValueError: If timestamp format is invalid
    """
    # Handle both comma (SRT) and period (VTT) separators
    timestamp = timestamp.replace(',', '.')
    
    # Parse HH:MM:SS.mmm or MM:SS.mmm
    parts = timestamp.strip().split(':')
    
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    elif len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    else:
        raise ValueError(f"Invalid timestamp format: {timestamp}")


def parse_srt_content(content: str) -> list[SubtitleSegment]:
    """Parse SRT file content into segments.
    
    SRT format:
        1
        00:00:00,080 --> 00:00:03,080
        Text line 1
        Text line 2 (optional)
        
        2
        00:00:03,080 --> 00:00:05,920
        Next subtitle text
    
    Args:
        content: Raw SRT file content
        
    Returns:
        List of SubtitleSegment objects
        
    Raises:
        SubtitleParseError: If parsing fails
    """
    segments: list[SubtitleSegment] = []
    
    # Split by double newline (segment separator)
    # Handle both \n\n and \r\n\r\n
    content = content.replace('\r\n', '\n')
    blocks = re.split(r'\n\n+', content.strip())
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 2:
            continue
        
        # First line should be index (number)
        try:
            index = int(lines[0].strip())
        except ValueError:
            # Skip blocks that don't start with a number
            continue
        
        # Second line should be timestamp
        timestamp_line = lines[1].strip()
        timestamp_match = re.match(
            r'(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})',
            timestamp_line
        )
        
        if not timestamp_match:
            continue
        
        try:
            start = parse_srt_timestamp(timestamp_match.group(1))
            end = parse_srt_timestamp(timestamp_match.group(2))
        except ValueError:
            continue
        
        # Remaining lines are text
        text_lines = lines[2:]
        text = ' '.join(line.strip() for line in text_lines if line.strip())
        
        # Remove HTML tags if present (some SRT files have them)
        text = re.sub(r'<[^>]+>', '', text)
        
        if text:
            segments.append(SubtitleSegment(
                index=index,
                start=start,
                end=end,
                text=text
            ))
    
    return segments


def parse_vtt_content(content: str) -> list[SubtitleSegment]:
    """Parse VTT (WebVTT) file content into segments.
    
    VTT format:
        WEBVTT
        
        00:00:00.080 --> 00:00:03.080
        Text line 1
        
        00:00:03.080 --> 00:00:05.920
        Next subtitle text
    
    Args:
        content: Raw VTT file content
        
    Returns:
        List of SubtitleSegment objects
    """
    segments: list[SubtitleSegment] = []
    
    # Remove WEBVTT header and metadata
    content = content.replace('\r\n', '\n')
    
    # Skip header lines
    lines = content.split('\n')
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip().upper() == 'WEBVTT':
            start_idx = i + 1
            break
    
    # Skip any metadata after WEBVTT
    while start_idx < len(lines) and lines[start_idx].strip() and ':' in lines[start_idx]:
        start_idx += 1
    
    content = '\n'.join(lines[start_idx:])
    
    # Split by double newline
    blocks = re.split(r'\n\n+', content.strip())
    
    index = 0
    for block in blocks:
        lines = block.strip().split('\n')
        if not lines:
            continue
        
        # Find timestamp line
        timestamp_line = None
        text_start = 0
        
        for i, line in enumerate(lines):
            if '-->' in line:
                timestamp_line = line.strip()
                text_start = i + 1
                break
        
        if not timestamp_line:
            continue
        
        # Parse timestamp (VTT uses period for milliseconds)
        timestamp_match = re.match(
            r'(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})',
            timestamp_line
        )
        
        if not timestamp_match:
            # Try MM:SS.mmm format
            timestamp_match = re.match(
                r'(\d{1,2}:\d{2}[,\.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}[,\.]\d{1,3})',
                timestamp_line
            )
        
        if not timestamp_match:
            continue
        
        try:
            start = parse_srt_timestamp(timestamp_match.group(1))
            end = parse_srt_timestamp(timestamp_match.group(2))
        except ValueError:
            continue
        
        # Get text
        text_lines = lines[text_start:]
        text = ' '.join(line.strip() for line in text_lines if line.strip())
        
        # Remove VTT tags
        text = re.sub(r'<[^>]+>', '', text)
        
        if text:
            index += 1
            segments.append(SubtitleSegment(
                index=index,
                start=start,
                end=end,
                text=text
            ))
    
    return segments


def segments_to_words(segments: list[SubtitleSegment]) -> list[WordTiming]:
    """Convert subtitle segments to WordTiming format for analyzer compatibility.
    
    Each segment becomes a single "word" entry with accurate timing.
    This preserves the original segment timing without estimation.
    
    Args:
        segments: List of subtitle segments
        
    Returns:
        List of WordTiming objects (each representing a full segment)
    """
    words: list[WordTiming] = []
    
    for segment in segments:
        # Each segment becomes one "word" entry with its full text
        # This keeps timing 100% accurate from the original SRT
        words.append(WordTiming(
            word=segment.text,
            start=segment.start,
            end=segment.end
        ))
    
    return words


def parse_subtitle_file(
    file_path: str,
    progress_callback: Callable[[str], None] | None = None
) -> SubtitleResult:
    """Parse subtitle file and return TranscriptionResult-compatible object.
    
    Automatically detects format based on file extension and content.
    
    Args:
        file_path: Path to subtitle file (.srt or .vtt)
        progress_callback: Optional callback for progress updates
        
    Returns:
        SubtitleResult with text, words, and duration
        
    Raises:
        SubtitleParseError: If file cannot be parsed
        FileNotFoundError: If file doesn't exist
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Subtitle file not found: {file_path}")
    
    if progress_callback:
        progress_callback(f"Reading subtitle file: {path.name}")
    
    # Read file content
    try:
        content = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        # Try other encodings
        for encoding in ['utf-8-sig', 'latin-1', 'cp1252']:
            try:
                content = path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise SubtitleParseError(f"Cannot decode subtitle file: {file_path}")
    
    # Detect format
    extension = path.suffix.lower()
    is_vtt = extension == '.vtt' or content.strip().upper().startswith('WEBVTT')
    
    if progress_callback:
        format_name = "VTT" if is_vtt else "SRT"
        progress_callback(f"Parsing {format_name} format...")
    
    # Parse content
    if is_vtt:
        segments = parse_vtt_content(content)
    else:
        segments = parse_srt_content(content)
    
    if not segments:
        raise SubtitleParseError(f"No valid subtitle segments found in: {file_path}")
    
    if progress_callback:
        progress_callback(f"Found {len(segments)} subtitle segments")
    
    # Convert to words
    words = segments_to_words(segments)
    
    # Build full text
    full_text = ' '.join(seg.text for seg in segments)
    
    # Calculate duration (end of last segment)
    duration = max(seg.end for seg in segments)
    
    if progress_callback:
        progress_callback(f"Parsed {len(segments)} segments, duration: {duration:.1f}s")
    
    return SubtitleResult(
        text=full_text,
        segments=segments,
        words=words,
        duration=duration,
        is_segment_based=True
    )


def validate_subtitle_file(file_path: str) -> tuple[bool, str | None]:
    """Validate that a file is a valid subtitle file.
    
    Args:
        file_path: Path to subtitle file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    path = Path(file_path)
    
    if not path.exists():
        return False, f"File not found: {file_path}"
    
    if not path.is_file():
        return False, f"Not a file: {file_path}"
    
    extension = path.suffix.lower()
    if extension not in ['.srt', '.vtt']:
        return False, f"Unsupported subtitle format: {extension}. Use .srt or .vtt"
    
    # Try to parse
    try:
        result = parse_subtitle_file(file_path)
        if len(result.words) == 0:
            return False, "Subtitle file contains no valid segments"
        return True, None
    except SubtitleParseError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Error parsing subtitle: {e}"


__all__ = [
    'SubtitleResult',
    'SubtitleParseError',
    'WordTiming',
    'SubtitleSegment',
    'parse_subtitle_file',
    'validate_subtitle_file',
]
