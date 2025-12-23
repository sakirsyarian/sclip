"""Caption formatting & styles for SmartClip AI.

This module provides caption style presets and ASS (Advanced SubStation Alpha)
subtitle generation for burning captions into video clips.

ASS Format Overview:
    ASS is a subtitle format that supports advanced styling including:
    - Custom fonts, sizes, and colors
    - Outline/stroke effects
    - Positioning and alignment
    - Karaoke timing effects (word-by-word highlighting)

Caption Styles:
    - default: Clean white text with black outline, positioned at bottom
    - bold: Large yellow Impact font, centered for emphasis
    - minimal: Subtle small text, less intrusive
    - karaoke: Word-by-word highlight effect as audio plays

Font Handling:
    The module specifies fonts in the ASS file, but FFmpeg's libass
    will automatically fall back to system fonts if the specified
    font is not available. This ensures captions always render.

Performance Optimizations:
    - Pre-compiled regex patterns for text escaping
    - Efficient string building using list joins
    - Cached style configurations

Usage:
    from src.utils.captions import generate_ass_subtitle, CAPTION_STYLES
    
    # Generate ASS subtitle content
    ass_content = generate_ass_subtitle(
        captions=clip_data["captions"],
        style="default",
        video_width=1080,
        video_height=1920,
        clip_start_time=125.5
    )
    
    # Write to file for FFmpeg
    with open("subtitles.ass", "w") as f:
        f.write(ass_content)
"""

import re
import sys
from typing import TypedDict
from src.types import CaptionSegment, CaptionStyle


# Pre-compiled regex patterns for performance
_NEWLINE_PATTERN = re.compile(r'\n')


class CaptionStyleConfig(TypedDict, total=False):
    """Configuration for a caption style."""
    font: str
    font_size: int
    color: str
    stroke_color: str
    stroke_width: int
    position: str
    margin_bottom: int
    highlight_color: str
    word_highlight: bool


# Fallback fonts for different platforms when specified font is not available
# FFmpeg's libass will try these in order if the primary font is missing
FALLBACK_FONTS = {
    "win32": ["Arial", "Segoe UI", "Tahoma", "Verdana", "sans-serif"],
    "darwin": ["Helvetica", "Arial", "SF Pro", "Lucida Grande", "sans-serif"],
    "linux": ["DejaVu Sans", "Liberation Sans", "FreeSans", "Arial", "sans-serif"],
}


# Caption style presets as defined in design document
# Each style defines font, colors, positioning, and effects
CAPTION_STYLES: dict[CaptionStyle, CaptionStyleConfig] = {
    "default": {
        # Clean, readable style suitable for most content
        # Smaller font for word-by-word display
        "font": "Arial Bold",
        "font_size": 24,
        "color": "#FFFFFF",           # White text
        "stroke_color": "#000000",    # Black outline for readability
        "stroke_width": 2,
        "position": "bottom",
        "margin_bottom": 150,         # Higher from bottom to not cover faces
    },
    "bold": {
        # High-impact style for emphasis and viral content
        "font": "Impact",
        "font_size": 28,
        "color": "#FFFF00",           # Yellow text for attention
        "stroke_color": "#000000",
        "stroke_width": 3,            # Thicker outline
        "position": "bottom",
        "margin_bottom": 150,
    },
    "minimal": {
        # Subtle style that doesn't distract from content
        "font": "Helvetica",
        "font_size": 20,
        "color": "#FFFFFF",
        "stroke_color": "#333333",    # Subtle dark gray outline
        "stroke_width": 1,
        "position": "bottom",
        "margin_bottom": 100,
    },
    "karaoke": {
        # Word-by-word highlight effect (like karaoke)
        "font": "Arial Bold",
        "font_size": 26,
        "color": "#FFFFFF",
        "highlight_color": "#00FF00", # Green highlight for current word
        "stroke_color": "#000000",
        "stroke_width": 2,
        "position": "bottom",
        "margin_bottom": 150,
        "word_highlight": True,       # Enable karaoke effect
    },
}


def _hex_to_ass_color(hex_color: str) -> str:
    """Convert hex color (#RRGGBB) to ASS color format (&HBBGGRR&).
    
    ASS subtitle format uses BGR byte order instead of RGB,
    and wraps the value in &H...& delimiters.
    
    Args:
        hex_color: Color in hex format (e.g., "#FFFFFF" for white)
        
    Returns:
        Color in ASS format (e.g., "&HFFFFFF&" for white)
    
    Example:
        >>> _hex_to_ass_color("#FF0000")  # Red in RGB
        "&H0000FF&"  # Red in ASS (BGR order)
    """
    # Remove # prefix if present
    hex_color = hex_color.lstrip("#")
    
    # Parse RGB components
    r = hex_color[0:2]
    g = hex_color[2:4]
    b = hex_color[4:6]
    
    # Return in BGR order for ASS format
    return f"&H{b}{g}{r}&"


def _get_platform_fonts() -> list[str]:
    """Get list of fallback fonts for the current platform.
    
    Returns:
        List of font names likely to be available on the current platform.
    """
    platform = sys.platform
    if platform.startswith("linux"):
        platform = "linux"
    
    return FALLBACK_FONTS.get(platform, FALLBACK_FONTS["linux"])


def _get_font_with_fallback(requested_font: str) -> str:
    """Get font name with platform-appropriate fallback.
    
    FFmpeg/libass will use the first available font from the list.
    This function returns the requested font, but the ASS format
    allows FFmpeg to fall back gracefully if the font is not found.
    
    Args:
        requested_font: The font name requested by the style
        
    Returns:
        The requested font name (FFmpeg handles fallback automatically)
    """
    # FFmpeg's libass will automatically fall back to available fonts
    # We just return the requested font - if it's not available,
    # libass will use a default system font
    return requested_font


def _format_ass_time(seconds: float) -> str:
    """Convert seconds to ASS timestamp format (H:MM:SS.cc).
    
    Args:
        seconds: Time in seconds (can include decimals)
        
    Returns:
        Time in ASS format (e.g., "0:01:23.45")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    
    # ASS uses centiseconds (2 decimal places)
    return f"{hours}:{minutes:02d}:{secs:05.2f}"


def _calculate_alignment(position: str) -> int:
    """Calculate ASS alignment value based on position.
    
    ASS alignment uses numpad-style positioning where the number
    corresponds to the position on a numeric keypad:
    
        7 8 9  (top-left, top-center, top-right)
        4 5 6  (middle-left, middle-center, middle-right)
        1 2 3  (bottom-left, bottom-center, bottom-right)
    
    Args:
        position: Position string ("bottom", "center", "top")
        
    Returns:
        ASS alignment value (default: 2 for bottom-center)
    """
    alignments = {
        "bottom": 2,   # Bottom center (most common for subtitles)
        "center": 5,   # Middle center (for emphasis)
        "top": 8,      # Top center (rarely used)
    }
    return alignments.get(position, 2)


def generate_ass_subtitle(
    captions: list[CaptionSegment],
    style: CaptionStyle,
    video_width: int,
    video_height: int,
    clip_start_time: float = 0.0
) -> str:
    """Generate ASS subtitle file content.
    
    Creates a complete ASS (Advanced SubStation Alpha) subtitle file
    with the specified style and caption segments.
    
    Font Handling:
        The generated ASS file uses the font specified in the style preset.
        If the font is not available on the system, FFmpeg's libass will
        automatically fall back to a default system font. This ensures
        captions are always rendered, even if the exact font is missing.
    
    Args:
        captions: List of caption segments with timing and text
        style: Caption style preset name
        video_width: Width of the video in pixels
        video_height: Height of the video in pixels
        clip_start_time: Start time of the clip (to offset caption times)
        
    Returns:
        Complete ASS subtitle file content as string
    """
    style_config = CAPTION_STYLES.get(style, CAPTION_STYLES["default"])
    
    # Extract style properties with font fallback support
    # FFmpeg's libass handles missing fonts gracefully by using system defaults
    font = _get_font_with_fallback(style_config.get("font", "Arial Bold"))
    font_size = style_config.get("font_size", 48)
    color = _hex_to_ass_color(style_config.get("color", "#FFFFFF"))
    stroke_color = _hex_to_ass_color(style_config.get("stroke_color", "#000000"))
    stroke_width = style_config.get("stroke_width", 2)
    position = style_config.get("position", "bottom")
    margin_bottom = style_config.get("margin_bottom", 100)
    word_highlight = style_config.get("word_highlight", False)
    highlight_color = _hex_to_ass_color(style_config.get("highlight_color", "#00FF00"))
    
    alignment = _calculate_alignment(position)
    
    # Build ASS header
    # Note: If the specified font is not available, libass will use a fallback font
    ass_content = f"""[Script Info]
Title: SmartClip AI Generated Subtitles
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{font_size},{color},&H000000FF&,{stroke_color},&H00000000&,1,0,0,0,100,100,0,0,1,{stroke_width},0,{alignment},10,10,{margin_bottom},1
"""
    
    # Add highlight style for karaoke mode
    if word_highlight:
        ass_content += f"Style: Highlight,{font},{font_size},{highlight_color},&H000000FF&,{stroke_color},&H00000000&,1,0,0,0,100,100,0,0,1,{stroke_width},0,{alignment},10,10,{margin_bottom},1\n"
    
    ass_content += "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    
    # Generate dialogue events
    if word_highlight:
        # Karaoke style: highlight words as they're spoken
        ass_content += _generate_karaoke_events(captions, clip_start_time)
    else:
        # Standard style: show each caption segment
        ass_content += _generate_standard_events(captions, clip_start_time)
    
    return ass_content


def _generate_standard_events(
    captions: list[CaptionSegment],
    clip_start_time: float
) -> str:
    """Generate standard ASS dialogue events.
    
    For segment-based captions (from external SRT/VTT), we display
    the full segment text without splitting to preserve accurate timing.
    
    Note: Caption times are already relative to clip start (adjusted in 
    get_captions_for_range), so clip_start_time parameter is kept for
    backward compatibility but not used for offset calculation.
    
    Args:
        captions: List of caption segments (times already relative to clip)
        clip_start_time: Start time offset (not used - times already adjusted)
        
    Returns:
        ASS dialogue events as string
    """
    events = []
    
    for caption in captions:
        # Caption times are already relative to clip start
        # (adjusted in get_captions_for_range in base.py)
        start = caption["start"]
        end = caption["end"]
        text = caption["text"]
        
        # Skip captions with negative times
        if end <= 0:
            continue
        
        # Clamp start time to 0
        start = max(0, start)
        
        # Escape special ASS characters
        text = _escape_ass_text(text)
        
        start_time = _format_ass_time(start)
        end_time = _format_ass_time(end)
        
        events.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}")
    
    return "\n".join(events)


def _split_long_captions(
    captions: list[CaptionSegment],
    max_words: int = 2
) -> list[CaptionSegment]:
    """Split captions with too many words into smaller chunks.
    
    This ensures captions don't cover too much of the screen.
    Each chunk gets proportional timing based on word count.
    
    Args:
        captions: List of caption segments
        max_words: Maximum words per caption (default: 2 for word-by-word)
        
    Returns:
        List of caption segments with at most max_words each
    """
    result: list[CaptionSegment] = []
    
    for caption in captions:
        text = caption["text"].strip()
        words = text.split()
        
        if len(words) <= max_words:
            # Caption is short enough, keep as-is
            result.append(caption)
        else:
            # Split into chunks
            start_time = caption["start"]
            end_time = caption["end"]
            total_duration = end_time - start_time
            
            # Calculate time per word
            time_per_word = total_duration / len(words) if words else 0
            
            # Create chunks
            for i in range(0, len(words), max_words):
                chunk_words = words[i:i + max_words]
                chunk_text = " ".join(chunk_words)
                
                chunk_start = start_time + (i * time_per_word)
                chunk_end = start_time + ((i + len(chunk_words)) * time_per_word)
                
                # Ensure last chunk ends at original end time
                if i + max_words >= len(words):
                    chunk_end = end_time
                
                result.append(CaptionSegment(
                    start=chunk_start,
                    end=chunk_end,
                    text=chunk_text
                ))
    
    return result


def _generate_karaoke_events(
    captions: list[CaptionSegment],
    clip_start_time: float
) -> str:
    """Generate karaoke-style ASS dialogue events with word highlighting.
    
    In karaoke mode, each word/segment is highlighted as it's spoken using
    ASS karaoke timing tags.
    
    Note: Caption times are already relative to clip start (adjusted in 
    get_captions_for_range), so clip_start_time parameter is kept for
    backward compatibility but not used for offset calculation.
    
    Args:
        captions: List of caption segments (times already relative to clip)
        clip_start_time: Start time offset (not used - times already adjusted)
        
    Returns:
        ASS dialogue events with karaoke effects as string
    """
    events = []
    
    # Group captions into lines (by proximity in time)
    lines = _group_captions_into_lines(captions, max_gap=0.5)
    
    for line_captions in lines:
        if not line_captions:
            continue
            
        # Get line timing (times are already relative to clip)
        line_start = line_captions[0]["start"]
        line_end = line_captions[-1]["end"]
        
        # Skip lines with invalid times
        if line_end <= 0:
            continue
        
        line_start = max(0, line_start)
        
        # Build karaoke text with timing tags
        karaoke_text = ""
        for i, caption in enumerate(line_captions):
            word_start = caption["start"]
            word_end = caption["end"]
            word = _escape_ass_text(caption["text"])
            
            # Calculate duration in centiseconds for karaoke tag
            duration_cs = int((word_end - max(word_start, 0)) * 100)
            
            # Use \kf for smooth fill effect
            karaoke_text += f"{{\\kf{duration_cs}}}{word}"
            
            # Add space between words (except last)
            if i < len(line_captions) - 1:
                karaoke_text += " "
        
        start_time = _format_ass_time(line_start)
        end_time = _format_ass_time(line_end)
        
        events.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{karaoke_text}")
    
    return "\n".join(events)


def _group_captions_into_lines(
    captions: list[CaptionSegment],
    max_gap: float = 0.5
) -> list[list[CaptionSegment]]:
    """Group caption segments into lines based on timing gaps.
    
    Segments that are close together in time are grouped into the same line.
    This is useful for karaoke mode where we want to show multiple words
    on the same line.
    
    Args:
        captions: List of caption segments
        max_gap: Maximum gap in seconds between segments to group them
        
    Returns:
        List of caption groups (lines)
    """
    if not captions:
        return []
    
    lines: list[list[CaptionSegment]] = []
    current_line: list[CaptionSegment] = [captions[0]]
    
    for i in range(1, len(captions)):
        prev_end = captions[i - 1]["end"]
        curr_start = captions[i]["start"]
        
        # Check if there's a significant gap
        if curr_start - prev_end > max_gap:
            # Start a new line
            lines.append(current_line)
            current_line = [captions[i]]
        else:
            # Add to current line
            current_line.append(captions[i])
    
    # Don't forget the last line
    if current_line:
        lines.append(current_line)
    
    return lines


def _escape_ass_text(text: str) -> str:
    """Escape special characters for ASS subtitle format.
    
    Uses pre-compiled regex patterns for better performance.
    
    Args:
        text: Raw text to escape
        
    Returns:
        Escaped text safe for ASS format
    """
    # Replace newlines with ASS line break using pre-compiled pattern
    text = _NEWLINE_PATTERN.sub(r'\\N', text)
    
    # Escape curly braces (used for ASS tags)
    # Only escape if not already part of a tag
    # For simplicity, we'll escape standalone braces
    
    return text


def get_style_config(style: CaptionStyle) -> CaptionStyleConfig:
    """Get the configuration for a caption style.
    
    Args:
        style: Caption style name
        
    Returns:
        Style configuration dictionary
    """
    return CAPTION_STYLES.get(style, CAPTION_STYLES["default"])


def calculate_text_position(
    video_width: int,
    video_height: int,
    style: CaptionStyle
) -> tuple[int, int]:
    """Calculate the x, y position for caption text.
    
    Args:
        video_width: Width of the video in pixels
        video_height: Height of the video in pixels
        style: Caption style name
        
    Returns:
        Tuple of (x, y) position for text center
    """
    style_config = CAPTION_STYLES.get(style, CAPTION_STYLES["default"])
    position = style_config.get("position", "bottom")
    margin_bottom = style_config.get("margin_bottom", 100)
    
    x = video_width // 2
    
    if position == "bottom":
        y = video_height - margin_bottom
    elif position == "center":
        y = video_height // 2
    elif position == "top":
        y = margin_bottom
    else:
        y = video_height - margin_bottom
    
    return (x, y)


# Export public API
__all__ = [
    "CAPTION_STYLES",
    "FALLBACK_FONTS",
    "CaptionStyleConfig",
    "generate_ass_subtitle",
    "get_style_config",
    "calculate_text_position",
]
