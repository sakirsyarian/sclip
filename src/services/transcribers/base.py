"""Base class for transcription services.

This module defines the abstract interface that all transcription
providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class WordTimestamp:
    """A single word with its timestamp."""
    word: str
    start: float  # Start time in seconds
    end: float    # End time in seconds


@dataclass
class TranscriptionResult:
    """Result from a transcription service.
    
    Attributes:
        text: Full transcription text
        words: List of words with timestamps
        language: Detected or specified language
        duration: Audio duration in seconds
    """
    text: str
    words: list[WordTimestamp] = field(default_factory=list)
    language: str = ""
    duration: float = 0.0
    
    def to_caption_segments(self) -> list[dict]:
        """Convert word timestamps to caption segments format.
        
        Returns:
            List of caption segments compatible with ClipData
        """
        return [
            {"start": w.start, "end": w.end, "text": w.word}
            for w in self.words
        ]


class TranscriptionError(Exception):
    """Base exception for transcription errors."""
    pass


class TranscriptionAPIError(TranscriptionError):
    """Error from transcription API."""
    pass


class TranscriptionFileError(TranscriptionError):
    """Error with audio file."""
    pass


class BaseTranscriber(ABC):
    """Abstract base class for transcription services.
    
    All transcription providers must implement this interface.
    """
    
    def __init__(self, api_key: str | None = None, model: str | None = None):
        """Initialize transcriber.
        
        Args:
            api_key: API key for cloud providers (optional for local)
            model: Model name to use
        """
        self.api_key = api_key
        self.model = model
    
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
    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        progress_callback: Callable[[str], None] | None = None
    ) -> TranscriptionResult:
        """Transcribe audio file to text with word timestamps.
        
        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'id', 'en')
            progress_callback: Optional callback for progress updates
            
        Returns:
            TranscriptionResult with text and word timestamps
            
        Raises:
            TranscriptionError: If transcription fails
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this transcriber is available (API key set, etc)."""
        pass
    
    def get_model(self) -> str:
        """Get the model to use."""
        return self.model or self.default_model
