"""Base class for analysis services.

This module defines the abstract interface that all analysis
providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable

from src.services.transcribers.base import TranscriptionResult
from src.types import ClipData


@dataclass
class AnalysisResult:
    """Result from an analysis service.
    
    Attributes:
        clips: List of identified viral clips
        model: Model used for analysis
        provider: Provider name
    """
    clips: list[ClipData] = field(default_factory=list)
    model: str = ""
    provider: str = ""


class AnalysisError(Exception):
    """Base exception for analysis errors."""
    pass


class AnalysisAPIError(AnalysisError):
    """Error from analysis API."""
    pass


class AnalysisParseError(AnalysisError):
    """Error parsing analysis response."""
    pass


# Prompt template for viral moment analysis
ANALYSIS_PROMPT = """You are an expert at identifying viral-worthy moments in video content.

Analyze the following transcript and identify the most engaging, viral-worthy moments.

TRANSCRIPT:
{transcript}

VIDEO DURATION: {duration} seconds

REQUIREMENTS:
- Find up to {max_clips} clips
- Each clip should be {min_duration}-{max_duration} seconds long
- Focus on moments with high engagement potential:
  - Surprising statements or revelations
  - Emotional peaks (humor, inspiration, controversy)
  - Quotable soundbites
  - Story climaxes or plot twists
  - Expert insights or unique perspectives

For each clip, provide:
1. start_time: Start timestamp in seconds (must match transcript timestamps)
2. end_time: End timestamp in seconds (must match transcript timestamps)
3. title: A catchy, clickbait-style title (max 60 chars) in {language}
4. description: An SEO-optimized description (max 200 chars) in {language}

IMPORTANT:
- Use the EXACT timestamps from the transcript
- Ensure clips don't overlap
- Prioritize the most engaging moments

Return ONLY valid JSON in this exact format:
{{
  "clips": [
    {{
      "start_time": 125.5,
      "end_time": 185.2,
      "title": "Catchy title here",
      "description": "SEO description here"
    }}
  ]
}}
"""


def build_analysis_prompt(
    transcript: str,
    duration: float,
    max_clips: int,
    min_duration: int,
    max_duration: int,
    language: str
) -> str:
    """Build the analysis prompt.
    
    Args:
        transcript: Full transcript with timestamps
        duration: Video duration in seconds
        max_clips: Maximum clips to find
        min_duration: Minimum clip duration
        max_duration: Maximum clip duration
        language: Language for titles/descriptions
        
    Returns:
        Formatted prompt string
    """
    return ANALYSIS_PROMPT.format(
        transcript=transcript,
        duration=duration,
        max_clips=max_clips,
        min_duration=min_duration,
        max_duration=max_duration,
        language=language
    )


def format_transcript_with_timestamps(transcription: TranscriptionResult) -> str:
    """Format transcription with timestamps for analysis.
    
    Handles both word-by-word (API transcription) and segment-based (external subtitle).
    
    Args:
        transcription: TranscriptionResult with word timestamps
        
    Returns:
        Formatted transcript string with timestamps
    """
    if not transcription.words:
        return transcription.text
    
    # Check if this is segment-based (from external subtitle)
    is_segment_based = getattr(transcription, 'is_segment_based', False)
    
    if is_segment_based:
        # For segment-based: each "word" is already a full segment
        lines = []
        for segment in transcription.words:
            timestamp = f"[{segment.start:.2f}s - {segment.end:.2f}s]"
            lines.append(f"{timestamp} {segment.word}")
        return "\n".join(lines)
    
    # For word-by-word: group into lines
    lines = []
    current_line = []
    current_start = None
    
    for word in transcription.words:
        if current_start is None:
            current_start = word.start
        
        current_line.append(word.word)
        
        # Create a new line every ~10 words or at sentence boundaries
        if len(current_line) >= 10 or word.word.endswith(('.', '!', '?')):
            timestamp = f"[{current_start:.2f}s - {word.end:.2f}s]"
            lines.append(f"{timestamp} {' '.join(current_line)}")
            current_line = []
            current_start = None
    
    # Add remaining words
    if current_line:
        last_word = transcription.words[-1]
        timestamp = f"[{current_start:.2f}s - {last_word.end:.2f}s]"
        lines.append(f"{timestamp} {' '.join(current_line)}")
    
    return "\n".join(lines)


def get_captions_for_range(
    transcription: TranscriptionResult,
    start_time: float,
    end_time: float
) -> list:
    """Extract captions for a specific time range.
    
    Handles both word-by-word and segment-based transcriptions.
    For segment-based (external subtitle): returns full segments as captions.
    For word-by-word (API transcription): returns individual words as captions.
    
    Args:
        transcription: TranscriptionResult with words/segments
        start_time: Clip start time in seconds
        end_time: Clip end time in seconds
        
    Returns:
        List of CaptionSegment dicts
    """
    from src.types import CaptionSegment
    
    captions: list[CaptionSegment] = []
    
    for word in transcription.words:
        # Include items that overlap with the time range
        if word.start < end_time and word.end > start_time:
            # Clamp times to clip boundaries
            caption_start = max(word.start, start_time)
            caption_end = min(word.end, end_time)
            
            captions.append(CaptionSegment(
                start=caption_start - start_time,  # Relative to clip start
                end=caption_end - start_time,
                text=word.word
            ))
    
    return captions


class BaseAnalyzer(ABC):
    """Abstract base class for analysis services.
    
    All analysis providers must implement this interface.
    """
    
    def __init__(self, api_key: str | None = None, model: str | None = None, **kwargs):
        """Initialize analyzer.
        
        Args:
            api_key: API key for cloud providers
            model: Model name to use
            **kwargs: Additional provider-specific arguments
        """
        self.api_key = api_key
        self.model = model
        self.extra_args = kwargs
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for display."""
        pass
    
    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model to use."""
        pass
    
    @abstractmethod
    async def analyze(
        self,
        transcription: TranscriptionResult,
        video_duration: float,
        max_clips: int = 5,
        min_duration: int = 45,
        max_duration: int = 180,
        language: str = "id",
        progress_callback: Callable[[str], None] | None = None
    ) -> AnalysisResult:
        """Analyze transcript to identify viral moments.
        
        Args:
            transcription: TranscriptionResult with text and timestamps
            video_duration: Total video duration in seconds
            max_clips: Maximum clips to identify
            min_duration: Minimum clip duration
            max_duration: Maximum clip duration
            language: Language for titles/descriptions
            progress_callback: Optional callback for progress updates
            
        Returns:
            AnalysisResult with identified clips
            
        Raises:
            AnalysisError: If analysis fails
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this analyzer is available."""
        pass
    
    def get_model(self) -> str:
        """Get the model to use."""
        return self.model or self.default_model
