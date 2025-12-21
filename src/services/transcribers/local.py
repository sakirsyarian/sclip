"""Local Whisper transcription service using faster-whisper.

Uses faster-whisper for local speech-to-text with word-level timestamps.
Runs entirely offline, no API key needed.

Requirements: pip install faster-whisper
"""

import asyncio
import os
from typing import Callable

from .base import (
    BaseTranscriber,
    TranscriptionResult,
    WordTimestamp,
    TranscriptionError,
    TranscriptionFileError,
)


class LocalTranscriber(BaseTranscriber):
    """Local Whisper transcription using faster-whisper.
    
    Features:
    - Runs entirely offline
    - No API key needed
    - Word-level timestamps
    - Multi-language support
    - GPU acceleration (CUDA) if available
    
    Models (downloaded automatically):
    - tiny: Fastest, lowest accuracy (~1GB VRAM)
    - base: Fast, decent accuracy (~1GB VRAM)
    - small: Good balance (~2GB VRAM)
    - medium: High accuracy (~5GB VRAM)
    - large-v3: Best accuracy (~10GB VRAM)
    """
    
    SUPPORTED_MODELS = [
        "tiny",
        "base", 
        "small",
        "medium",
        "large-v3",
    ]
    
    @property
    def name(self) -> str:
        return "Local Whisper (faster-whisper)"
    
    @property
    def default_model(self) -> str:
        return "base"  # Good balance for CPU
    
    def is_available(self) -> bool:
        """Check if faster-whisper is installed."""
        try:
            import faster_whisper
            return True
        except ImportError:
            return False
    
    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        progress_callback: Callable[[str], None] | None = None
    ) -> TranscriptionResult:
        """Transcribe audio using local faster-whisper.
        
        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'id', 'en')
            progress_callback: Optional callback for progress updates
            
        Returns:
            TranscriptionResult with text and word timestamps
        """
        def update_progress(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)
        
        # Validate file
        if not os.path.exists(audio_path):
            raise TranscriptionFileError(f"Audio file not found: {audio_path}")
        
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise TranscriptionError(
                "faster-whisper not installed. Install with: pip install faster-whisper"
            )
        
        model_name = self.get_model()
        update_progress(f"Loading Whisper model: {model_name}...")
        
        # Determine compute type based on available hardware
        device, compute_type = self._get_device_config()
        update_progress(f"Using device: {device} ({compute_type})")
        
        # Run in thread pool to not block
        loop = asyncio.get_event_loop()
        
        try:
            result = await loop.run_in_executor(
                None,
                lambda: self._do_transcribe(
                    model_name, device, compute_type, 
                    audio_path, language, update_progress
                )
            )
            return result
        except Exception as e:
            raise TranscriptionError(f"Local transcription failed: {e}")
    
    def _get_device_config(self) -> tuple[str, str]:
        """Determine best device and compute type."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda", "float16"
        except ImportError:
            pass
        
        # CPU fallback
        return "cpu", "int8"
    
    def _do_transcribe(
        self,
        model_name: str,
        device: str,
        compute_type: str,
        audio_path: str,
        language: str | None,
        update_progress: Callable[[str], None]
    ) -> TranscriptionResult:
        """Perform the actual transcription (synchronous)."""
        from faster_whisper import WhisperModel
        
        # Load model
        model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type
        )
        
        update_progress("Transcribing audio...")
        
        # Transcribe with word timestamps
        segments, info = model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True,
            vad_filter=True,  # Filter out silence
        )
        
        # Collect results
        full_text = []
        words: list[WordTimestamp] = []
        duration = 0.0
        
        for segment in segments:
            full_text.append(segment.text.strip())
            duration = max(duration, segment.end)
            
            if segment.words:
                for word in segment.words:
                    words.append(WordTimestamp(
                        word=word.word.strip(),
                        start=word.start,
                        end=word.end
                    ))
        
        return TranscriptionResult(
            text=" ".join(full_text),
            words=words,
            language=info.language if hasattr(info, 'language') else (language or ""),
            duration=duration
        )
